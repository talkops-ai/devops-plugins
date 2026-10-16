# CIS AWS Foundations Benchmark v3.0 & AWS FSBP Control Verification Matrix

This reference provides deterministic read-only verification commands and expected states for high-priority **CIS AWS Foundations Benchmark v3.0** and **AWS Foundational Security Best Practices (FSBP)** controls.

---

## 1. Identity & Account Root Controls (CIS Section 1 / FSBP IAM)

| Control ID | Control Requirement | Read-Only Verification API / CLI | Expected Compliant State |
|---|---|---|---|
| **CIS 1.4 / IAM.4** | Ensure no `root` user access key exists | `aws iam get-account-summary --query 'SummaryMap.AccountAccessKeysPresent'` | `0` (Root access keys must never exist) |
| **CIS 1.5 / IAM.9** | Ensure MFA is enabled for the `root` user | `aws iam get-account-summary --query 'SummaryMap.AccountMFAEnabled'` | `1` |
| **CIS 1.6 / IAM.6** | Ensure hardware MFA is enabled for the `root` user | `aws iam list-virtual-mfa-devices --assignment-status Assigned --query 'VirtualMFADevices[?SerialNumber==\`arn:aws:iam::<account-id>:mfa/root-account-mfa-device\`]'` | Empty list `[]` while `AccountMFAEnabled == 1` (proving MFA device is hardware/FIDO2, not single virtual `root-account-mfa-device`) |
| **CIS 1.8–1.9 / IAM.7–IAM.17** | Ensure IAM password policy requires minimum length >= 14 and prevents password reuse (>= 24) | `aws iam get-account-password-policy` | `MinimumPasswordLength >= 14`, `PasswordReusePrevention == 24`, `RequireSymbols == true`, `RequireNumbers == true`, `RequireUppercaseCharacters == true`, `RequireLowercaseCharacters == true` |
| **CIS 1.12 / IAM.3** | Ensure credentials unused for 45 days or greater are disabled | `aws iam generate-credential-report && aws iam get-credential-report` | No active `password_enabled=true` or `access_key_1_active=true`/`access_key_2_active=true` with `last_used_date` > 45 days (or `N/A` if created > 45 days ago) |
| **CIS 1.14 / IAM.3** | Ensure access keys are rotated every 90 days or less | `aws iam list-users` + `aws iam list-access-keys` | All `Status=Active` keys have `CreateDate` within 90 days (prefer migrating to IAM Roles / Identity Center / OIDC) |
| **CIS 1.17 / IAM.18** | Ensure a support role has been created to manage incidents with AWS Support | `aws iam list-entities-for-policy --policy-arn arn:aws:iam::aws:policy/AWSSupportAccess` | At least one dedicated IAM Role or SSO Permission Set attached (`PolicyRoles` non-empty) |
| **CIS 1.20 / IAM.8** | Ensure IAM Access Analyzer is enabled for all active regions | `aws accessanalyzer list-analyzers --region <region>` | At least one analyzer with `status == ACTIVE` per active region (ideally `ORGANIZATION` + `ORGANIZATION_UNUSED_ACCESS` in delegated admin) |

---

## 2. Storage, Database & Compute Baselines (CIS Section 2 / FSBP S3, EC2, RDS)

| Control ID | Control Requirement | Read-Only Verification API / CLI | Expected Compliant State |
|---|---|---|---|
| **CIS 2.1.4 / S3.1** | Ensure S3 Block Public Access is enabled at the **Account** level | `aws s3control get-public-access-block --account-id <account-id>` | `BlockPublicAcls: true`, `IgnorePublicAcls: true`, `BlockPublicPolicy: true`, `RestrictPublicBuckets: true` |
| **CIS 2.1.1 / S3.5** | Ensure all S3 buckets require HTTPS (`aws:SecureTransport`) | `aws s3api get-bucket-policy --bucket <name>` | Policy contains an explicit `Effect: Deny` statement when `Condition.Bool["aws:SecureTransport"] == "false"` |
| **S3.19** | Ensure S3 buckets have Object-level ACLs disabled (`BucketOwnerEnforced`) | `aws s3api get-bucket-ownership-controls --bucket <name>` | `OwnershipControls.Rules[0].ObjectOwnership == "BucketOwnerEnforced"` |
| **CIS 2.2.1 / EC2.7** | Ensure EBS volume encryption is enabled by default in all regions | `aws ec2 get-ebs-encryption-by-default --region <region>` and `aws ec2 get-ebs-default-kms-key-id --region <region>` | `EbsEncryptionByDefault: true` in every enabled region |
| **EC2.1** | Ensure EBS snapshots are not publicly restorable | `aws ec2 describe-snapshots --owner-ids self --restorable-by-user-ids all --region <region>` and `aws ec2 get-snapshot-block-public-access-state --region <region>` | Empty snapshot list `[]` AND `State == "block-all-sharing"` |
| **EC2.8** | Ensure EC2 instances enforce IMDSv2 (`HttpTokens=required`) | `aws ec2 describe-instances --query 'Reservations[].Instances[?MetadataOptions.HttpTokens!=\`required\`].[InstanceId,State.Name,MetadataOptions]'` | Empty list `[]` (all instances require session-oriented IMDSv2 tokens) |
| **CIS 2.3.1 / RDS.3** | Ensure encryption-at-rest is enabled for RDS instances and clusters | `aws rds describe-db-instances --query 'DBInstances[?StorageEncrypted==\`false\`].[DBInstanceIdentifier,Engine]'` | Empty list `[]` |
| **CIS 2.3.3 / RDS.2** | Ensure RDS instances are not publicly accessible | `aws rds describe-db-instances --query 'DBInstances[?PubliclyAccessible==\`true\`].[DBInstanceIdentifier,Endpoint.Address,DBSubnetGroup.VpcId]'` | Empty list `[]` |
| **RDS.1** | Ensure RDS snapshots are not public | `aws rds describe-db-snapshots --snapshot-type manual --include-public` + `describe-db-snapshot-attributes` | `AttributeValues` must never contain `"all"` |

---

## 3. Logging & Continuous Monitoring Controls (CIS Section 3 & 4)

### 3.1 CloudTrail & Config Integrity (CIS 3.1–3.11)

1. **Multi-Region Trail Enabled (CIS 3.1 / CloudTrail.1):**
   ```bash
   aws cloudtrail describe-trails --query 'trailList[?IsMultiRegionTrail==`true`]'
   ```
   Verify `GetTrailStatus` returns `IsLogging: true` and `LatestDeliveryError` is null.
2. **Log File Validation Enabled (CIS 3.2 / CloudTrail.2):**
   Verify `LogFileValidationEnabled == true` on the multi-region/organization trail (enables SHA-256 digest chaining to detect log tampering after delivery).
3. **KMS SSE-KMS Encryption on CloudTrail (CIS 3.5 / CloudTrail.4):**
   Verify `KmsKeyId` is populated on the trail.
4. **CloudWatch Logs Integration (CIS 3.4 / CloudTrail.5):**
   Verify `CloudWatchLogsLogGroupArn` is configured and `LatestCloudWatchLogsDeliveryTime` is within the last 24 hours.
5. **S3 Bucket Access Logging & Object-Level Logging (CIS 3.6, 3.8–3.9):**
   Verify the CloudTrail target S3 bucket has `GetPublicAccessBlock` all `true`, MFA Delete or Object Lock enabled, and S3 Server Access Logging enabled.

### 3.2 Mandatory CIS Section 4 CloudWatch Logs Metric Filters & Alarms

When auditing CIS Section 4, query `logs:DescribeMetricFilters` on the CloudTrail Log Group and `cloudwatch:DescribeAlarmsForMetric` + `sns:ListSubscriptionsByTopic` to ensure an active alarm routes to an active subscriber:

| CIS ID | Threat / Event Monitored | Required CloudWatch Logs Filter Pattern |
|---|---|---|
| **4.1** | Unauthorized API calls (`AccessDenied` / `UnauthorizedOperation`) | `{ ($.errorCode = "*UnauthorizedOperation") \|\| ($.errorCode = "AccessDenied*") \|\| ($.sourceIPAddress = "delivery.logs.amazonaws.com") && ($.eventName = "HeadBucket") }` |
| **4.2** | Management Console sign-in without MFA | `{ ($.eventName = "ConsoleLogin") && ($.additionalEventData.MFAUsed != "Yes") && ($.userIdentity.type = "IAMUser") && ($.responseElements.ConsoleLogin = "Success") }` |
| **4.3** | Usage of the `root` account | `{ $.userIdentity.type = "Root" && $.userIdentity.invokedBy NOT EXISTS && $.eventType != "AwsServiceEvent" }` |
| **4.4** | IAM policy changes | `{ ($.eventName=DeleteGroupPolicy) \|\| ($.eventName=DeleteRolePolicy) \|\| ($.eventName=DeleteUserPolicy) \|\| ($.eventName=PutGroupPolicy) \|\| ($.eventName=PutRolePolicy) \|\| ($.eventName=PutUserPolicy) \|\| ($.eventName=CreatePolicy) \|\| ($.eventName=DeletePolicy) \|\| ($.eventName=CreatePolicyVersion) \|\| ($.eventName=DeletePolicyVersion) \|\| ($.eventName=AttachRolePolicy) \|\| ($.eventName=DetachRolePolicy) \|\| ($.eventName=AttachUserPolicy) \|\| ($.eventName=DetachUserPolicy) \|\| ($.eventName=AttachGroupPolicy) \|\| ($.eventName=DetachGroupPolicy) }` |
| **4.5** | CloudTrail configuration changes | `{ ($.eventName = CreateTrail) \|\| ($.eventName = UpdateTrail) \|\| ($.eventName = DeleteTrail) \|\| ($.eventName = StartLogging) \|\| ($.eventName = StopLogging) }` |
| **4.6** | AWS Management Console authentication failures | `{ ($.eventName = ConsoleLogin) && ($.errorMessage = "Failed authentication") }` |
| **4.7** | Disabling or scheduled deletion of Customer Managed CMKs | `{ ($.eventSource = kms.amazonaws.com) && (($.eventName = DisableKey) \|\| ($.eventName = ScheduleKeyDeletion)) }` |
| **4.8** | S3 bucket policy changes | `{ ($.eventSource = s3.amazonaws.com) && (($.eventName = PutBucketAcl) \|\| ($.eventName = PutBucketPolicy) \|\| ($.eventName = PutBucketCors) \|\| ($.eventName = PutBucketLifecycle) \|\| ($.eventName = PutBucketReplication) \|\| ($.eventName = DeleteBucketPolicy) \|\| ($.eventName = DeleteBucketCors) \|\| ($.eventName = DeleteBucketLifecycle) \|\| ($.eventName = DeleteBucketReplication)) }` |
| **4.9** | AWS Config configuration changes | `{ ($.eventSource = config.amazonaws.com) && (($.eventName=StopConfigurationRecorder) \|\| ($.eventName=DeleteDeliveryChannel) \|\| ($.eventName=PutDeliveryChannel) \|\| ($.eventName=PutConfigurationRecorder)) }` |
| **4.10** | Security Group changes | `{ ($.eventName = AuthorizeSecurityGroupIngress) \|\| ($.eventName = AuthorizeSecurityGroupEgress) \|\| ($.eventName = RevokeSecurityGroupIngress) \|\| ($.eventName = RevokeSecurityGroupEgress) \|\| ($.eventName = CreateSecurityGroup) \|\| ($.eventName = DeleteSecurityGroup) }` |
| **4.11** | Network ACL (NACL) changes | `{ ($.eventName = CreateNetworkAcl) \|\| ($.eventName = CreateNetworkAclEntry) \|\| ($.eventName = DeleteNetworkAcl) \|\| ($.eventName = DeleteNetworkAclEntry) \|\| ($.eventName = ReplaceNetworkAclEntry) \|\| ($.eventName = ReplaceNetworkAclAssociation) }` |
| **4.12** | Network Gateway changes | `{ ($.eventName = CreateCustomerGateway) \|\| ($.eventName = DeleteCustomerGateway) \|\| ($.eventName = AttachInternetGateway) \|\| ($.eventName = CreateInternetGateway) \|\| ($.eventName = DeleteInternetGateway) \|\| ($.eventName = DetachInternetGateway) }` |
| **4.13** | Route Table changes | `{ ($.eventName = CreateRoute) \|\| ($.eventName = CreateRouteTable) \|\| ($.eventName = ReplaceRoute) \|\| ($.eventName = ReplaceRouteTableAssociation) \|\| ($.eventName = DeleteRouteTable) \|\| ($.eventName = DeleteRoute) \|\| ($.eventName = DisassociateRouteTable) }` |
| **4.14** | VPC changes | `{ ($.eventName = CreateVpc) \|\| ($.eventName = DeleteVpc) \|\| ($.eventName = ModifyVpcAttribute) \|\| ($.eventName = AcceptVpcPeeringConnection) \|\| ($.eventName = CreateVpcPeeringConnection) \|\| ($.eventName = DeleteVpcPeeringConnection) \|\| ($.eventName = RejectVpcPeeringConnection) \|\| ($.eventName = AttachClassicLinkVpc) \|\| ($.eventName = DetachClassicLinkVpc) \|\| ($.eventName = DisableVpcClassicLink) \|\| ($.eventName = EnableVpcClassicLink) }` |
| **4.15** | AWS Organizations changes | `{ ($.eventSource = organizations.amazonaws.com) && (($.eventName = "AcceptHandshake") \|\| ($.eventName = "AttachPolicy") \|\| ($.eventName = "CreateAccount") \|\| ($.eventName = "CreateOrganizationalUnit") \|\| ($.eventName = "CreatePolicy") \|\| ($.eventName = "DeclineHandshake") \|\| ($.eventName = "DeleteOrganization") \|\| ($.eventName = "DeleteOrganizationalUnit") \|\| ($.eventName = "DeletePolicy") \|\| ($.eventName = "DetachPolicy") \|\| ($.eventName = "DisablePolicyType") \|\| ($.eventName = "EnablePolicyType") \|\| ($.eventName = "InviteAccountToOrganization") \|\| ($.eventName = "LeaveOrganization") \|\| ($.eventName = "MoveAccount") \|\| ($.eventName = "RemoveAccountFromOrganization") \|\| ($.eventName = "UpdatePolicy") \|\| ($.eventName = "UpdateOrganizationalUnit")) }` |
