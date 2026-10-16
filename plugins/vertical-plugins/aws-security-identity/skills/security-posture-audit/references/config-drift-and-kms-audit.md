# AWS Config Drift Forensics & KMS Cryptographic Governance

Use this reference when auditing AWS Config recorder coverage, querying AWS Config SQL aggregators, reconstructing resource drift timelines, or auditing KMS Customer Managed Keys (CMKs), key policies, grants, and TLS encryption in transit.

---

## 1. AWS Config Drift & Compliance Forensics

### 1.1 Verifying Config Recorder & Delivery Channel Health Across Regions

In each active region, run:

1. `configservice:DescribeConfigurationRecorders` — Verify `recordingGroup.allSupported == true`. In the primary/home region, verify `recordingGroup.includeGlobalResourceTypes == true` (so IAM users/roles/policies and S3 global settings are tracked).
2. `configservice:DescribeConfigurationRecorderStatus` — Verify `recording == true` and `lastStatus == "SUCCESS"`. Flag any `lastErrorCode` (often caused by S3 bucket policy or KMS permissions breaking delivery).
3. `configservice:DescribeDeliveryChannels` — Verify S3 target bucket encryption and delivery frequency.

### 1.2 High-Value AWS Config Advanced SQL Queries (`select-resource-config` / `select-aggregate-resource-config`)

Use `configservice:SelectResourceConfig` (single account/region) or `configservice:SelectAggregateResourceConfig` (multi-account/multi-region aggregator) to run fast read-only posture sweeps without N+1 API pagination:

**Find all unencrypted EBS volumes across the Organization:**
```sql
SELECT
  accountId,
  awsRegion,
  resourceId,
  configuration.state.value,
  configuration.size
WHERE
  resourceType = 'AWS::EC2::Volume'
  AND configuration.encrypted = false
```

**Find all Security Groups allowing unrestricted ingress (`0.0.0.0/0` or `::/0`) on non-web ports:**
```sql
SELECT
  accountId,
  awsRegion,
  resourceId,
  resourceName,
  configuration.vpcId,
  configuration.ipPermissions
WHERE
  resourceType = 'AWS::EC2::SecurityGroup'
  AND (
    configuration.ipPermissions.ipRanges LIKE '%0.0.0.0/0%'
    OR configuration.ipPermissions.ipv6Ranges LIKE '%::/0%'
  )
```

**Find all S3 buckets without Server-Side Encryption or without BlockPublicAccess:**
```sql
SELECT
  accountId,
  awsRegion,
  resourceName,
  supplementaryConfiguration.PublicAccessBlockConfiguration,
  supplementaryConfiguration.ServerSideEncryptionConfiguration
WHERE
  resourceType = 'AWS::S3::Bucket'
```

**Find all RDS DB instances that are publicly accessible or unencrypted:**
```sql
SELECT
  accountId,
  awsRegion,
  resourceId,
  configuration.dBInstanceIdentifier,
  configuration.publiclyAccessible,
  configuration.storageEncrypted
WHERE
  resourceType = 'AWS::RDS::DBInstance'
  AND (
    configuration.publiclyAccessible = true
    OR configuration.storageEncrypted = false
  )
```

### 1.3 Reconstructing Resource Drift Timelines

When a resource fails a Config rule (`get-compliance-details-by-config-rule` with `ComplianceType=NON_COMPLIANT`):
1. Call `configservice:GetResourceConfigHistory` with `resourceType`, `resourceId`, and `limit=5`.
2. Diff `configuration` between the current `configurationItemCaptureTime` and the previous compliant capture time.
3. Cross-reference `configurationItemCaptureTime` (±10 minutes) in `cloudtrail:LookupEvents` by `ResourceName = <resourceId>` to attribute the exact IAM principal, source IP, and tool (Console vs. Terraform vs. SDK) that introduced the drift.

---

## 2. KMS Cryptographic Governance Audit

Never call `kms:Decrypt` or `kms:GenerateDataKey`. Audit KMS solely through metadata and policy APIs.

### 2.1 Step-by-Step KMS Audit Procedure

1. **Enumerate Keys:** Call `kms:ListKeys` (paginated) in each active region.
2. **Filter Customer Managed Keys (CMKs):** Call `kms:DescribeKey` for each `KeyId`:
   - Skip `KeyManager == "AWS"` (AWS-managed keys rotate automatically every year and have immutable policies, though note they cannot be used for cross-account sharing).
   - For `KeyManager == "CUSTOMER"`, check:
     - `KeyState`: Flag `PendingDeletion` (verify `DeletionDate` wasn't triggered maliciously via CIS 4.7), `Disabled`, or `PendingImport`.
     - `Origin`: Distinguish `AWS_KMS` vs. `EXTERNAL` (BYOK — has no automatic rotation; requires manual key material re-import monitoring) vs. `AWS_CLOUDHSM`.
     - `KeySpec` / `KeyUsage`: Only symmetric `SYMMETRIC_DEFAULT` (`ENCRYPT_DECRYPT`) keys support automatic rotation.
3. **Check Automatic Key Rotation (CIS 3.7 / KMS.4):**
   - For symmetric CMKs with `Origin == "AWS_KMS"` and `KeyState == "Enabled"`, call `kms:GetKeyRotationStatus`.
   - Flag any key where `KeyRotationEnabled == false`.

### 2.2 Auditing KMS Key Policies (`kms:GetKeyPolicy`)

Unlike other AWS resources, **a KMS key policy is the primary root of trust for the key**—even in the same account, IAM identity policies cannot grant access to a KMS key unless the key policy explicitly delegates to the account root (`arn:aws:iam::<account-id>:root`).

Check every statement in `kms:GetKeyPolicy` (`PolicyName="default"`) for these high-risk misconfigurations:

1. **Over-permissive Account Root Delegation Combined with Weak IAM Boundaries:**
   - Standard root delegation (`Principal: {"AWS": "arn:aws:iam::<account-id>:root"}`, `Action: "kms:*"`) allows *any* identity policy in that account with `kms:*` to use or administer the key, **and because the key policy is a resource-based policy in the same account, any direct IAM user/role ARN listed in the key policy bypasses that principal's Permission Boundary!**
   - Best Practice: Separate **Key Administrators** (`kms:Create*`, `kms:Describe*`, `kms:Enable*`, `kms:List*`, `kms:Put*`, `kms:Update*`, `kms:Revoke*`, `kms:Disable*`, `kms:Get*`, `kms:Delete*`, `kms:ScheduleKeyDeletion`, `kms:CancelKeyDeletion`) from **Key Users** (`kms:Encrypt`, `kms:Decrypt`, `kms:ReEncrypt*`, `kms:GenerateDataKey*`).
2. **Wildcard Principal (`"Principal": "*"` or `{"AWS": "*"}`) Without Condition Constraints:**
   - **CRITICAL EXPOSURE:** If a statement has `Principal: "*"` and `Effect: Allow`, it MUST have a restrictive condition such as:
     - `kms:CallerAccount`: restricted to known AWS Account IDs, OR
     - `aws:PrincipalOrgID`: restricted to `o-xxxxxxxxxx`, AND
     - `kms:ViaService`: restricted to the specific regional AWS service (e.g., `s3.us-east-1.amazonaws.com`, `secretsmanager.us-east-1.amazonaws.com`, `ebs.us-east-1.amazonaws.com`), OR
     - `aws:SourceArn` / `aws:SourceAccount` for service principals (`logs.<region>.amazonaws.com`, `cloudtrail.amazonaws.com`, `events.amazonaws.com`).
3. **Missing `kms:EncryptionContext` Conditions:**
   - For high-sensitivity keys (Secrets Manager, S3, DynamoDB), verify whether `kms:EncryptionContext:aws:secretsmanager:arn` or `kms:EncryptionContext:aws:s3:arn` is used to prevent cross-resource ciphertext substitution (confused deputy decryption).

### 2.3 Auditing KMS Grants (`kms:ListGrants`)

Grants are often overlooked during policy audits because they do not appear in `GetKeyPolicy` or IAM policies!
Call `kms:ListGrants` for every CMK and check:
1. **`GranteePrincipal`:** Flag any external account principal not in the organization.
2. **Dangerous `Operations`:** Flag grants that include `"CreateGrant"` (allows the grantee to delegate further grants) or `"Decrypt"` without `Constraints.EncryptionContextSubset` or `EncryptionContextEquals`.
3. **Missing `RetiringPrincipal`:** Grants created by temporary workloads without a `RetiringPrincipal` accumulate as orphaned privilege grants.

---

## 3. Data-in-Transit & TLS Posture (ACM, ALB, CloudFront, API Gateway)

1. **AWS Certificate Manager (`acm:ListCertificates` + `acm:DescribeCertificate`):**
   - Flag certificates where `NotAfter` is < 30 days and `RenewalEligibility == "INELIGIBLE"` or `RenewalSummary.RenewalStatus == "FAILED"`.
   - Flag imported certificates (`Type == "IMPORTED"`) lacking automated rotation alerts.
2. **ALB / NLB HTTPS Listeners (`elbv2:DescribeListeners`):**
   - Flag `Protocol == "HTTP"` listeners that do not exclusively perform a `301` redirect action to `HTTPS:443`.
   - Flag `SslPolicy` older than `ELBSecurityPolicy-TLS13-1-2-2021-06` or `ELBSecurityPolicy-FS-1-2-Res-2020-10` (never allow TLS 1.0/1.1 `ELBSecurityPolicy-2016-08`).
3. **CloudFront Distributions (`cloudfront:ListDistributions` + `cloudfront:GetDistributionConfig`):**
   - Check `ViewerCertificate.MinimumProtocolVersion`: must be `TLSv1.2_2021` or `TLSv1.3_2025`.
   - Check `DefaultCacheBehavior.ViewerProtocolPolicy`: must be `redirect-to-https` or `https-only` (never `allow-all`).
   - Check `Origins.Items[].CustomOriginConfig.OriginProtocolPolicy`: must be `https-only` with `OriginSslProtocols` restricted to `TLSv1.2`.
