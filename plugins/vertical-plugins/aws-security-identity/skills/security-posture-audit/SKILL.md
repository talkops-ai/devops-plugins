---
name: security-posture-audit
description: >-
  Performs read-only AWS security posture, compliance, and multi-account governance audits across
  Security Hub CSPM, AWS Config, GuardDuty, Inspector, Macie, IAM Access Analyzer, Detective,
  Security Lake, CloudTrail, AWS Organizations Delegated Administrators, KMS, ACM, and
  Well-Architected Security. Use for CIS AWS Foundations Benchmark, AWS Foundational Security Best
  Practices (FSBP), multi-region service coverage, configuration drift, and CloudTrail log integrity
  validation.
version: 3
---

# Security Posture, Compliance & Multi-Account Governance Audit

Use this skill for **detective and advisory work only**. Never enable, disable, modify, archive, suppress, or resolve a finding or cloud resource from this skill. Every remediation recommendation is emitted as a structured proposal with `approval_required: true`. For deep data-plane protection (S3 Object Lock, Macie custom identifiers, KMS key/grant policies, Secrets Manager rotation, Private CA/mTLS), pair with `security-data-protection`.

## Reference Library (Load On-Demand)

- **[references/cis-fsbp-control-matrix.md](references/cis-fsbp-control-matrix.md)** — Load when auditing CIS AWS Foundations Benchmark v3.0 or AWS Foundational Security Best Practices (FSBP) controls, root account hygiene, account-level S3 Block Public Access, EBS default encryption, RDS exposure, or CIS CloudWatch Logs metric filters and alarms.
- **[references/config-drift-and-kms-audit.md](references/config-drift-and-kms-audit.md)** — Load when querying AWS Config aggregators (`select-aggregate-resource-config`), reconstructing resource drift timelines (`get-resource-config-history`), or auditing KMS Customer Managed Keys (CMKs), key policies, grants, key rotation, S3 Bucket Keys, and ACM/ALB/CloudFront TLS cipher policies.

---

## Operating Cadence

1. **Daily Triage Baseline:**
   - Surface GuardDuty findings with prefix `AttackSequence:` first, followed by Security Hub V2 **Exposure** findings (multi-service attack paths).
   - Surface active `CRITICAL` and `HIGH` findings across GuardDuty, Security Hub, Inspector, and Macie.
   - Hand off active threat indicators to `security-incident-triage` for CloudTrail actor correlation before proposing containment.
2. **Weekly Posture, Multi-Account Delegated Admin & Coverage Drift:**
   - **Verify AWS Organizations Delegated Administrator Architecture (`organizations:ListDelegatedAdministrators`):**
     - Ensure centralized security services (`guardduty.amazonaws.com`, `securityhub.amazonaws.com`, `inspector2.amazonaws.com`, `macie.amazonaws.com`, `access-analyzer.amazonaws.com`, `config.amazonaws.com`, `config-multiaccountsetup.amazonaws.com`, `detective.amazonaws.com`, `securitylake.amazonaws.com`, `cloudtrail.amazonaws.com`) are delegated to a dedicated **Security Tooling / Audit Account** (never operated directly from the Organizations Management Account) with auto-enablement configured for new member accounts.
   - Verify regional enablement across all active regions (`ec2:DescribeRegions` where `OptInStatus != not-opted-in`) for GuardDuty detectors, Security Hub standards, AWS Config configuration recorders, Inspector scan coverage (EC2, ECR, Lambda, Lambda code), and IAM Access Analyzer (external + unused access).
   - **Verify Organization CloudTrail & Digest Integrity:**
     - Check `cloudtrail:DescribeTrails` and `cloudtrail:GetTrailStatus`: ensure at least one multi-region (`IsMultiRegionTrail=true`), organization-wide (`IsOrganizationTrail=true`) trail is actively logging (`IsLogging=true`), encrypts logs with SSE-KMS (`KMSKeyId` present), enables log file integrity validation (`LogFileValidationEnabled=true`), and records S3/Lambda/EBS data events where required.
     - Run `aws cloudtrail validate-logs --trail-arn <arn> --start-time <iso8601>` during compliance audits or forensics to cryptographically verify SHA-256 digest chains and detect log tampering or deletion.
   - Audit AWS Config non-compliant rules (`configservice:GetComplianceSummaryByConfigRule`) and Conformance Packs.
   - Verify account-level S3 Block Public Access (`s3control:GetPublicAccessBlock`) and regional EBS default encryption (`ec2:GetEbsEncryptionByDefault`).
3. **Monthly / Periodic Deep Governance:**
   - Evaluate full CIS AWS Foundations v3.0 and AWS FSBP control pass rates across member accounts.
   - Audit KMS CMK key policies, cross-account grants (`kms:ListGrants`), automatic rotation (`kms:GetKeyRotationStatus`), and keys in `PendingDeletion` (hand off deep cryptographic/PKI/Secrets remediation to `security-data-protection`).
   - Audit TLS termination policies on ALB/NLB (`ELBSecurityPolicy-TLS13-1-2-*`), CloudFront (`TLSv1.2_2021`+), and API Gateway.

---

## Deterministic Evidence Collection Procedure

1. **Scope & Timestamp:** Record `account_ids` (supporting multi-account profile switching via `AWS_MCP_PROXY_PROFILES`), organization/OU context, target regions, and `evidence_timestamp` (ISO-8601 UTC).
2. **Enumerate Active Regions First:**
   - Call `ec2:DescribeRegions` (`AllRegions=false`) to get enabled regions in the account. Never assume posture from `us-east-1` alone—attackers frequently abuse opt-in or secondary regions (`ap-east-1`, `me-central-1`, `eu-south-1`) where Config or GuardDuty was left disabled.
   - Bound multi-region concurrency and paginate all list APIs (`NextToken` / `Marker`).
3. **Prefer Specialized Read-Only MCP Tools First:**
   - Use `wa-security` (`CheckSecurityServices`, `GetSecurityFindings`, `GetStoredSecurityContext`, `CheckStorageEncryption`, `ListServicesInRegion`, `CheckNetworkSecurity`) for rapid Well-Architected Security Pillar snapshots.
   - Use `aws-mcp` (`aws___call_aws`) for granular Security Hub CSPM, AWS Config, Access Analyzer, GuardDuty, Inspector, Macie, KMS, ACM, S3Control, CloudTrail, and Organizations read-only calls.
   - Use `cloudwatch` MCP tools to verify CIS CloudWatch metric filters, alarms, and log group retention/KMS encryption.
4. **Project Findings Compactly:**
   - Never dump raw multi-megabyte `GetAccountAuthorizationDetails`, Config history blobs, or full ASFF/OCSF JSON arrays into context.
   - Project each control check into the standardized audit output contract below.

---

## Required Read-Only API Families

| Domain | Required Read-Only APIs | Key Security Invariants Checked |
|---|---|---|
| **Multi-Account & CloudTrail** | `organizations.list-delegated-administrators`, `cloudtrail.describe-trails`, `cloudtrail.get-trail-status`, `cloudtrail.get-event-selectors`, `cloudtrail.validate-logs` | Security services delegated to dedicated Audit/Security account; multi-region Org Trail active with `LogFileValidationEnabled=true`, KMS CMK encryption, and verified SHA-256 digest chain. |
| **AWS Config** | `describe-configuration-recorders`, `describe-configuration-recorder-status`, `describe-delivery-channels`, `describe-config-rules`, `get-compliance-details-by-config-rule`, `get-resource-config-history`, `select-resource-config` | Recorder recording `allSupported=true`, `includeGlobalResourceTypes=true` in home region; `recording=true` and `lastStatus=SUCCESS`; non-compliant resources and exact configuration diff timestamp. |
| **Security Hub & CSPM** | `get-enabled-standards`, `get-findings`, `describe-standards-controls`, `list-finding-aggregators`, `get-findings-v2` | Cross-region finding aggregator active; FSBP and CIS standards enabled; disabled controls documented; Exposure findings prioritized. |
| **IAM Access Analyzer** | `list-analyzers`, `list-findings`, `get-finding`, `get-analyzed-resource` | Both `ACCOUNT`/`ORGANIZATION` (external access) and `ACCOUNT_UNUSED_ACCESS`/`ORGANIZATION_UNUSED_ACCESS` analyzers active; public or cross-account S3/KMS/IAM/SNS/SQS/Lambda/RDS shares identified. |
| **KMS & Encryption** | `list-keys`, `describe-key`, `get-key-rotation-status`, `get-key-policy`, `list-grants`, `ec2.get-ebs-encryption-by-default`, `s3control.get-public-access-block` | `KeyManager=CUSTOMER` keys have `KeyRotationEnabled=true` (for symmetric keys); key policies avoid open `Principal: "*"` without strict `kms:CallerAccount`/`kms:ViaService` conditions; grants lack unrestricted `CreateGrant` or retiree-less cross-account access. |
| **Threat & Vulnerability Coverage** | `guardduty.list-detectors`, `guardduty.get-detector`, `inspector2.batch-get-account-status`, `inspector2.get-coverage-statistics`, `macie2.get-macie-session` | GuardDuty S3, EKS Audit/Runtime, ECS Runtime, Malware, RDS, and Lambda protection enabled; Inspector scanning EC2, ECR, and Lambda; Macie automated sensitive data discovery active. |

---

## Standardized Audit Output Contract

Every posture or compliance finding MUST conform to this schema:

```json
{
  "scope": {
    "account_ids": ["111122223333"],
    "regions": ["us-east-1", "us-west-2"]
  },
  "evidence_timestamp": "2026-10-14T10:00:00Z",
  "control_framework": "CIS-v3.0 | AWS-FSBP | WA-Security",
  "control_id": "CIS-2.1.4 | S3.1 | KMS.4",
  "finding_type": "CONFIG_DRIFT | CONTROL_FAILURE | COVERAGE_GAP | KMS_EXPOSURE",
  "resource_arn_or_id": "arn:aws:s3:::example-bucket",
  "observed_state": {
    "BlockPublicAcls": false,
    "IgnorePublicAcls": false
  },
  "expected_state": {
    "BlockPublicAcls": true,
    "IgnorePublicAcls": true,
    "BlockPublicPolicy": true,
    "RestrictPublicBuckets": true
  },
  "evidence": [
    "s3control:GetPublicAccessBlock (account 111122223333) -> BlockPublicAcls=false"
  ],
  "recommended_change": "Enable account-level S3 Block Public Access via aws s3control put-public-access-block or aws_s3_account_public_access_block Terraform resource (hand off to security-remediation-governance).",
  "approval_required": true
}
```

## Guardrails

- **Factual Configuration Reporting:** Report missing service coverage or unconfigured controls factually against the target benchmark (CIS, FSBP, Well-Architected) without inventing arbitrary severity scores for configuration state. For active findings from Security Hub, GuardDuty, Inspector, or Macie, preserve the **AWS-provided severity** (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and add separate analyst notes on exploitability and blast radius.
- **No Finding Suppression:** Never recommend archiving, suppressing, or disabling a Security Hub control or GuardDuty finding type to improve a compliance score.
- **No Plaintext Key/Secret Retrieval:** Never invoke `kms:Decrypt`, `kms:GenerateDataKey`, `secretsmanager:GetSecretValue`, or `ssm:GetParameter` (with decryption) during an audit.
