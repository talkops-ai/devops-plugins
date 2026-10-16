# S3 Hardening, Object Lock Immutability, Amazon Macie & Snapshot Protection

Use this reference when auditing or hardening S3 buckets, configuring **S3 Object Lock (`COMPLIANCE` vs. `GOVERNANCE` mode)** for ransomware protection and forensic evidence preservation, orchestrating **Amazon Macie** sensitive data discovery, or locking down EBS/RDS snapshots and **AWS Backup Vault Lock**.

---

## 1. S3 Bucket Hardening & Safe Policy Mutation Rules

### 1.1 Mandatory Baseline for Every Production S3 Bucket
1. **Bucket Namespace & Ownership (`BucketOwnerEnforced`):**
   - New buckets must be created with `--bucket-namespace account-regional`.
   - Enforce `ObjectOwnership: BucketOwnerEnforced` (`s3api:GetBucketOwnershipControls`) so legacy S3 ACLs are completely disabled and all objects are owned by the bucket account regardless of uploader.
2. **Account & Bucket Block Public Access (`S3.1` / `CIS 2.1.4`):**
   - Enforce all four flags (`BlockPublicAcls=true`, `IgnorePublicAcls=true`, `BlockPublicPolicy=true`, `RestrictPublicBuckets=true`) at the **account** level (`aws s3control get-public-access-block --account-id <acct>`) and bucket level.
3. **Default Encryption, Bucket Keys & Blocking SSE-C (`S3.4`):**
   - Configure `ServerSideEncryptionByDefault` with `SSEAlgorithm: "aws:kms"` and a **Customer Managed Key (CMK) full ARN** (never the AWS-managed `aws/s3` key or an alias when cross-account access, custom rotation, or strict key-policy isolation is required).
   - Enable **`BucketKeyEnabled: true`** (reduces KMS API call volume and cost by up to 99%).
   - **Block SSE-C (`BlockedEncryptionTypes: ["SSE-C"]`):** Attackers with compromised `s3:PutObject`/`s3:CopyObject` permissions frequently perform in-place S3 ransomware attacks by re-encrypting objects using `SSE-C` (Server-Side Encryption with Customer-Provided Keys) and discarding the key. Blocking `SSE-C` neutralizes this ransomware vector:
     ```bash
     aws s3api put-bucket-encryption --bucket <bucket> --server-side-encryption-configuration '{
       "Rules": [{
         "ApplyServerSideEncryptionByDefault": {
           "SSEAlgorithm": "aws:kms",
           "KMSMasterKeyID": "arn:aws:kms:us-east-1:111122223333:key/12345678-1234-1234-1234-1234567890ab"
         },
         "BucketKeyEnabled": true,
         "BlockedEncryptionTypes": {
           "EncryptionType": ["SSE-C"]
         }
       }]
     }'
     ```

### 1.2 Safe `put-bucket-policy` Backup & Merge Procedure
Because `s3api:PutBucketPolicy` **replaces the entire bucket policy**, never propose a partial policy snippet as a direct `put-bucket-policy` call:
1. Always retrieve the existing policy first (`aws s3api get-bucket-policy --bucket <name> --output text > backup-policy-$(date +%s).json`).
2. Merge new defensive statements (`DenyInsecureTransport`, `DenyIncorrectKMSKey`, `DenyUnencryptedObjectUploads`, `DenyExternalOrgPrincipals`) into the existing `Statement` array.
3. Validate JSON syntax (`python3 -m json.tool`) and run `aws accessanalyzer validate-policy --policy-type RESOURCE_POLICY` before presenting the remediation diff (`approval_required: true`).

### 1.3 Production S3 Defensive Bucket Policy Template

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::prod-sensitive-bucket",
        "arn:aws:s3:::prod-sensitive-bucket/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    },
    {
      "Sid": "DenyUploadsWithExternalOrWrongKMSKey",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::prod-sensitive-bucket/*",
      "Condition": {
        "StringNotEqualsIfExists": {
          "s3:x-amz-server-side-encryption-aws-kms-key-id": "arn:aws:kms:us-east-1:111122223333:key/12345678-1234-1234-1234-1234567890ab"
        }
      }
    }
  ]
}
```
> **Why `DenyUploadsWithExternalOrWrongKMSKey` is critical:** Without this statement, an attacker with `s3:PutObject` can re-encrypt objects in your bucket using an attacker-controlled KMS CMK in an external AWS account and then revoke your account's grant on that KMS key (KMS Ransomware).

---

## 2. S3 Object Lock: Forensic Preservation & Ransomware Immutability

S3 Object Lock enforces **Write-Once-Read-Many (WORM)** immutability at the object-version level (requires Bucket Versioning enabled).

### 2.1 `GOVERNANCE` Mode vs. `COMPLIANCE` Mode vs. `Legal Hold`

| Mechanism | Who Can Delete / Overwrite / Shorten Retention? | Primary Security Engineering Use Case |
|---|---|---|
| **`GOVERNANCE` Mode** | Regular users and roles **cannot** overwrite or delete the object version or shorten retention. Only a break-glass principal explicitly granted `s3:BypassGovernanceRetention` passing `x-amz-bypass-governance-retention: true` can bypass it. | Production application data buckets, database backups, and Terraform state buckets where protection against compromised workload roles is needed while retaining a break-glass SCP-guarded escape hatch. |
| **`COMPLIANCE` Mode** | **NOBODY.** No IAM user, no Organization Admin role, and **not even the AWS Account Root User** can overwrite, delete, or shorten the retention period of a protected object version until `RetainUntilDate` expires. | Regulatory WORM archives (SEC 17a-4, FINRA, HIPAA), **Organization CloudTrail / Security Lake log archive buckets**, and immutable ransomware recovery vaults. |
| **`Legal Hold` (`ON` / `OFF`)** | Independent of retention period; an object version under `LegalHold: Status=ON` cannot be deleted or overwritten even after its retention period expires, until a principal with `s3:PutObjectLegalHold` sets `Status=OFF`. | **Active Incident Response & Digital Forensics:** Immediately place a Legal Hold on compromised S3 objects, memory dumps, or log files during an investigation. |

### 2.2 Auditing & Enabling S3 Object Lock
1. **Read-Only Audit:**
   ```bash
   aws s3api get-object-lock-configuration --bucket <bucket-name>
   ```
   - Note: If `ObjectLockConfigurationNotFoundError` is returned, Object Lock is not enabled (`NOT_CONFIGURED`).
   - Verify `ObjectLockEnabled == "Enabled"` and inspect `Rule.DefaultRetention` (`Mode: "GOVERNANCE" | "COMPLIANCE"`, `Days` or `Years`).
2. **SCP Guardrail for Object Lock:**
   - In the `log-archive` and `backup` accounts, attach an SCP denying `s3:BypassGovernanceRetention`, `s3:PutBucketObjectLockConfiguration` (that weakens retention), and `s3:PutObjectLegalHold` (when setting `OFF`) for all principals.

---

## 3. Amazon Macie: Sensitive Data Discovery & Custom Data Identifiers

### 3.1 Read-Only Macie Posture & Finding Triage
1. **Check Macie Enablement & Automated Discovery:**
   ```bash
   aws macie2 get-macie-session --region <region>
   aws macie2 get-automated-discovery-configuration --region <region>
   aws macie2 get-bucket-statistics --region <region>
   ```
2. **List S3 Buckets with Public Access or Unencrypted Sensitive Data:**
   ```bash
   aws macie2 describe-buckets --criteria '{"publicAccess.effectivePermission":{"eq":["PUBLIC"]}}' --region <region>
   ```
3. **Create Custom Data Identifiers (Advisory Pattern for Proprietary Secrets/PII):**
   - When an organization has proprietary identifier formats (e.g., internal customer IDs `CUST-[0-9]{8}` or internal JWT/API prefixes), recommend defining a Macie Custom Data Identifier (`macie2:CreateCustomDataIdentifier`) with:
     - `regex`: precise pattern
     - `keywords`: required proximity words within `maximumMatchDistance` (e.g., `50` characters) to eliminate false positives
     - `ignoreWords`: test/dummy fixture prefixes to suppress noise

---

## 4. EBS, RDS/Aurora Snapshot Exposure & AWS Backup Vault Lock

1. **Block Public EBS Snapshots Account-Wide (`EC2.1`):**
   - Audit: `aws ec2 get-snapshot-block-public-access-state --region <region>` (must be `"block-all-sharing"`) and `aws ec2 describe-snapshots --owner-ids self --restorable-by-user-ids all --region <region>` (must be `[]`).
   - Remediation proposal:
     ```bash
     aws ec2 enable-snapshot-block-public-access --state block-all-sharing --region <region>
     ```
2. **Audit Public & Cross-Account RDS / Aurora Snapshots (`RDS.1`):**
   - Audit manual DB snapshots and cluster snapshots:
     ```bash
     aws rds describe-db-snapshots --snapshot-type public --region <region>
     aws rds describe-db-cluster-snapshots --snapshot-type public --region <region>
     ```
   - Ensure `AttributeName: "restore"` never includes `"all"` or untrusted external account IDs.
3. **AWS Backup Vault Lock (`backup:DescribeBackupVault`):**
   - Verify critical recovery points are stored in an AWS Backup Vault with **Backup Vault Lock** enabled (`Locked == true`, `MinRetentionDays`, `MaxRetentionDays`) and protected by AWS Backup logically air-gapped vaults for cross-account ransomware recovery.
