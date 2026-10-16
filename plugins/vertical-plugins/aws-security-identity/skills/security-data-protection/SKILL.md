---
name: security-data-protection
description: >-
  Audits and designs AWS data protection, cryptographic governance, forensic storage immutability,
  secret management, sensitive data discovery, and PKI/mTLS controls across AWS KMS, Amazon S3
  (Block Public Access, Bucket Policies, SSE-KMS, Object Lock Compliance/Governance mode), AWS
  Secrets Manager (dynamic references with asm-exec and automated rotation), Amazon Macie, AWS
  Certificate Manager (ACM), AWS Private CA, ALB/CloudFront mTLS, EBS/RDS snapshot sharing, and
  AWS Backup Vault Lock.
version: 1
---

# Data Protection, Cryptographic Governance, PKI & Forensic Immutability

Use this skill for **read-only data-protection auditing, cryptographic key/certificate governance, sensitive data discovery, forensic/ransomware storage immutability, and safe secret management**. Never decrypt ciphertext (`kms:Decrypt`), fetch plaintext secrets (`secretsmanager:GetSecretValue`, `ssm:GetParameter --with-decryption`), or directly mutate bucket policies, KMS key policies, or Object Lock configurations without emitting a structured remediation proposal (`approval_required: true`).

## Reference Library (Load On-Demand)

- **[references/s3-object-lock-and-macie.md](references/s3-object-lock-and-macie.md)** — Load when auditing or hardening S3 buckets, authoring safe `put-bucket-policy` merges (`DenyInsecureTransport`, `DenyIncorrectKMSKey`, `BlockedEncryptionTypes: [SSE-C]`), configuring **S3 Object Lock (`COMPLIANCE` vs. `GOVERNANCE` mode and Legal Holds)** for ransomware protection and forensic log archives, orchestrating **Amazon Macie** sensitive data discovery and custom data identifiers, or locking down EBS/RDS snapshots and **AWS Backup Vault Lock**.
- **[references/kms-pki-secrets-governance.md](references/kms-pki-secrets-governance.md)** — Load when auditing **KMS Customer Managed Keys (CMKs)**, key policies, grants (`kms:ListGrants`), and `kms:EncryptionContext` conditions, enforcing **Secrets Manager safe-handling (`{{resolve:secretsmanager:...}}` with `asm-exec` and 4-step rotation Lambdas)**, or governing **AWS Private CA hierarchies**, **ACM certificates**, **CloudFront/ALB Mutual TLS (mTLS) Trust Stores**, and **Direct Connect MACsec / VPN IPsec** transit encryption.

---

## Deterministic 6-Domain Data Protection Audit Workflow

1. **S3 Access Control, Encryption & Ransomware Immutability (`s3control` & `s3api`):**
   - **Account & Bucket Block Public Access:** Verify `s3control:GetPublicAccessBlock` at the account level and `s3api:GetPublicAccessBlock` per bucket (`BlockPublicAcls=true`, `IgnorePublicAcls=true`, `BlockPublicPolicy=true`, `RestrictPublicBuckets=true`).
   - **ACL Disabling (`S3.19`):** Verify `s3api:GetBucketOwnershipControls` has `ObjectOwnership == "BucketOwnerEnforced"`.
   - **Encryption & SSE-C Blocking:** Verify `s3api:GetBucketEncryption` enforces `aws:kms` (with a Customer Managed Key ARN, never the default `aws/s3` alias for sensitive buckets) or `AES256`, `BucketKeyEnabled: true`, and `BlockedEncryptionTypes: ["SSE-C"]` (blocking attacker-supplied client keys used in S3 ransomware attacks).
   - **S3 Object Lock (`s3api:GetObjectLockConfiguration`):**
     - Audit CloudTrail log archives, Security Lake buckets, backup buckets, and forensic evidence buckets for **S3 Object Lock**:
     - Distinguish **`GOVERNANCE` mode** (protects objects from deletion/overwrite by regular users, but principals granted `s3:BypassGovernanceRetention` and the `x-amz-bypass-governance-retention: true` header can bypass it) vs. **`COMPLIANCE` mode** (immutable WORM—no principal, **not even the AWS account root user**, can overwrite or delete an object version or shorten its retention period until `RetainUntilDate` expires).
     - Check **Legal Holds (`s3api:GetObjectLegalHold`)** during active incident response to freeze evidence indefinitely independent of retention periods.
   - **Safe Bucket Policy Auditing (`s3api:GetBucketPolicy`):** Verify `DenyInsecureTransport` (`aws:SecureTransport == "false"`), VPC Endpoint / Data Perimeter conditions (`aws:SourceVpce`, `aws:PrincipalOrgID`), and never overwrite an existing bucket policy without backing up and merging statements first.

2. **KMS Cryptographic Key & Grant Governance (`kms`):**
   - Enumerate CMKs (`kms:ListKeys` → `kms:DescribeKey` where `KeyManager == "CUSTOMER"`).
   - **Rotation & State:** Check `kms:GetKeyRotationStatus` (`KeyRotationEnabled == true` for symmetric `AWS_KMS` keys); flag keys in `PendingDeletion` or `Origin == "EXTERNAL"` (BYOK) with approaching `ValidTo` expiration dates.
   - **Key Policy Root-of-Trust (`kms:GetKeyPolicy`):**
     - Separate **Key Administrators** (`kms:PutKeyPolicy`, `kms:ScheduleKeyDeletion`, `kms:DisableKey`, `kms:RevokeGrant`) from **Key Users** (`kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey*`).
     - Flag any statement with `Principal: "*"` lacking strict `kms:CallerAccount` + `kms:ViaService` + `aws:PrincipalOrgID` conditions.
     - Enforce `kms:EncryptionContext` constraints (`kms:EncryptionContext:aws:secretsmanager:arn`, `kms:EncryptionContext:aws:s3:arn`) to prevent cross-resource ciphertext substitution.
   - **KMS Grants (`kms:ListGrants`):** Flag external account `GranteePrincipal`s, grants containing `"CreateGrant"` (delegation escalation), or temporary grants missing a `RetiringPrincipal`.

3. **Zero-Trust Secrets Manager & Parameter Store Governance (`secretsmanager` & `ssm`):**
   - **Hard Context Guardrail:** Never call `secretsmanager:GetSecretValue`, `secretsmanager:BatchGetSecretValue`, `ssm:GetParameter --with-decryption`, or query the local Secrets Manager Agent (`localhost:2773/secretsmanager/get`). Always reference secrets dynamically via `{{resolve:secretsmanager:<secret-id>:SecretString:<json-key>}}` executed through `asm-exec` (or injected via the AWS Parameters and Secrets Lambda Extension / EKS Secrets Store CSI Driver).
   - **Metadata & Rotation Audit (`secretsmanager:ListSecrets` → `DescribeSecret`):**
     - Verify `KmsKeyId` uses a dedicated Customer Managed Key (not default `aws/secretsmanager` when cross-account or strict separation is required).
     - Verify `RotationEnabled == true`, `LastRotatedDate` is within the compliance window (e.g., <= 30 or 90 days), and `RotationLambdaARN` is valid.
     - Check `secretsmanager:GetResourcePolicy` (or `aws accessanalyzer list-findings`) for cross-account or wildcard `Principal` exposure.

4. **Sensitive Data Discovery & Classification (`macie2`):**
   - Call `macie2:GetMacieSession` and `macie2:GetAutomatedDiscoveryConfiguration` to verify Amazon Macie automated sensitive data discovery is `ENABLED` across organization member accounts.
   - Inspect `macie2:ListClassificationJobs`, `macie2:ListCustomDataIdentifiers` (domain-specific employee IDs, internal API token patterns, tax IDs), and `macie2:GetBucketStatistics` (`BucketCountByEffectivePermission.PubliclyAccessible`, `UnencryptedBucketCount`).
   - Correlate `SensitiveData:S3Object/*` findings (Financial, Credentials/Private Keys, Personal/PII) with bucket exposure to prioritize immediate containment.

5. **PKI, Certificate Lifecycle, mTLS & Transit Encryption (`acm`, `acm-pca`, `elbv2`, `cloudfront`, `ec2`, `directconnect`):**
   - **AWS Private CA (`acm-pca:ListCertificateAuthorities`):** Audit Root vs. Subordinate CA hierarchy, CA status, CRL/OCSP revocation configuration (`RevocationConfiguration`), and cross-account RAM shares (`acm-pca:ListPermissions`).
   - **ACM & TLS Posture (`acm:ListCertificates`):** Flag certificates expiring in < 30 days with `RenewalEligibility == "INELIGIBLE"` or `RenewalStatus == "FAILED"`. Enforce TLS 1.2/1.3 security policies on ALB/NLB (`ELBSecurityPolicy-TLS13-1-2-2021-06`+), CloudFront (`TLSv1.2_2021` / `TLSv1.3_2025`), and API Gateway.
   - **Mutual TLS (mTLS) Enforcement:** Audit ALB Mutual Authentication (`MutualAuthentication.Mode == "verify"`, `TrustStoreArn`, `IgnoreClientCertificateExpiry == false`) and CloudFront Viewer mTLS (`ViewerMtlsConfig`) + Origin mTLS for B2B APIs and zero-trust workload ingress.
   - **Network-Layer Encryption in Transit:** Verify Direct Connect MACsec (`directconnect:DescribeConnections` -> `macSecCapable`, `portEncryptionStatus`) and Site-to-Site VPN IPsec tunnel cipher suites (AES-256-GCM, SHA-2, DH Group 14+, IKEv2).

6. **Block, File & Database Snapshot & Backup Immutability (`ec2`, `rds`, `efs`, `backup`):**
   - **EBS Encryption & Snapshot Block Public Access:** Verify `ec2:GetEbsEncryptionByDefault` is `true` and `ec2:GetSnapshotBlockPublicAccessState` is `"block-all-sharing"` in every active region; audit `ec2:DescribeSnapshots --owner-ids self --restorable-by-user-ids all`.
   - **RDS / Aurora Snapshot & Encryption Audit:** Verify `rds:DescribeDBInstances` / `DescribeDBClusters` have `StorageEncrypted == true`, `PubliclyAccessible == false`, and manual snapshots (`DescribeDBSnapshotAttributes` / `DescribeDBClusterSnapshotAttributes`) do not grant `restore` to `"all"` or untrusted accounts.
   - **AWS Backup Vault Lock (`backup:ListBackupVaults` → `DescribeBackupVault`):** Verify critical backup vaults have **Backup Vault Lock** enabled (`Locked == true`) in compliance mode with `MinRetentionDays`/`MaxRetentionDays` and a `ChangeableForDays` cooling-off window that has locked.

---

## Standardized Output Contract

Emit all data-protection audit findings using the `security-posture-audit` JSON schema (`scope`, `evidence_timestamp`, `control_framework`, `control_id`, `finding_type`, `resource_arn_or_id`, `observed_state`, `expected_state`, `evidence`, `recommended_change`, `approval_required: true`).
