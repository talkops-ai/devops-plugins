# KMS Cryptographic Governance, Secrets Manager Safe-Handling & PKI / mTLS Reference

Use this reference when auditing **KMS Customer Managed Keys (CMKs)** and **KMS Grants**, enforcing **zero-plaintext Secrets Manager handling (`{{resolve:secretsmanager:...}}` with `asm-exec` and 4-step rotation)**, or auditing **AWS Private CA**, **ACM**, **CloudFront/ALB Mutual TLS (mTLS)**, and **MACsec/IPsec** transit encryption.

---

## 1. KMS CMK Key Policies, Grants & Encryption Context Governance

Never call `kms:Decrypt` or `kms:GenerateDataKey`. Audit KMS strictly via control-plane metadata APIs (`kms:ListKeys`, `kms:DescribeKey`, `kms:GetKeyRotationStatus`, `kms:GetKeyPolicy`, `kms:ListGrants`).

### 1.1 Auditing KMS Key Policies (`kms:GetKeyPolicy`)
Unlike other AWS resources, **a KMS Key Policy is the mandatory root of trust**: even within the same AWS account, IAM identity policies cannot access a KMS key unless the key policy explicitly allows the account root (`arn:aws:iam::<account-id>:root`) or the principal.

Check every CMK (`KeyManager == "CUSTOMER"`) for:
1. **Separation of Duties (Key Administrators vs. Key Users):**
   - **Key Administrators** (`kms:Create*`, `kms:Describe*`, `kms:Enable*`, `kms:List*`, `kms:Put*`, `kms:Update*`, `kms:Revoke*`, `kms:Disable*`, `kms:Get*`, `kms:Delete*`, `kms:ScheduleKeyDeletion`, `kms:CancelKeyDeletion`) should **not** hold `kms:Decrypt` or `kms:GenerateDataKey*` on sensitive production data keys.
   - **Key Users** (`kms:Encrypt`, `kms:Decrypt`, `kms:ReEncrypt*`, `kms:GenerateDataKey*`, `kms:DescribeKey`) should be scoped to exact application execution role ARNs—remember that listing an IAM User ARN directly in a same-account KMS key policy **bypasses that user's IAM Permission Boundary**!
2. **Constraining Service & Wildcard Principals (`kms:ViaService` & `kms:CallerAccount`):**
   - If a statement uses `Principal: "*"` (or delegates to an AWS service), it MUST enforce:
     ```json
     "Condition": {
       "StringEquals": {
         "kms:CallerAccount": "111122223333",
         "kms:ViaService": "secretsmanager.us-east-1.amazonaws.com",
         "aws:PrincipalOrgID": "o-exampleorgid"
       }
     }
     ```
   - For direct AWS service principals (`logs.<region>.amazonaws.com`, `cloudtrail.amazonaws.com`, `events.amazonaws.com`, `sns.amazonaws.com`), enforce confused-deputy conditions (`aws:SourceArn` and `aws:SourceAccount`).
3. **Enforcing `kms:EncryptionContext` (Confused Deputy Decryption Defense):**
   - Services like Secrets Manager, S3 (Bucket Keys / SSE-KMS), EBS, and DynamoDB pass deterministic Encryption Context key-value pairs to KMS on every `Encrypt`/`Decrypt` call.
   - Scope high-sensitivity key policies by encryption context so a role authorized to decrypt Secret A cannot use the same CMK directly (`kms:Decrypt`) to decrypt ciphertext stolen from Secret B or S3 Bucket C:
     ```json
     "Condition": {
       "StringLike": {
         "kms:EncryptionContext:aws:secretsmanager:arn": "arn:aws:secretsmanager:us-east-1:111122223333:secret:prod/payments/*"
       }
     }
     ```

### 1.2 Auditing KMS Grants (`kms:ListGrants`)
KMS Grants dynamically delegate permissions on a CMK without modifying the Key Policy, making them a blind spot in static IaC reviews:
- Flag any grant where `GranteePrincipal` belongs to an external or unrecognized AWS account.
- Flag grants allowing `"CreateGrant"` (which permits the grantee to mint further child grants).
- Flag grants allowing `"Decrypt"` without `Constraints.EncryptionContextEquals` or `EncryptionContextSubset`.
- Flag workload grants lacking a `RetiringPrincipal`.

---

## 2. Zero-Trust Secrets Manager & Parameter Store Governance

### 2.1 Non-Negotiable Agent Secret Safety Rules (`secret-safety.py` Hook)
When AI agents or operators work with secrets, credentials, API keys, tokens, or database passwords:
1. **NEVER call `secretsmanager:GetSecretValue`, `secretsmanager:BatchGetSecretValue`, or `ssm:GetParameter --with-decryption`** via AWS CLI, SDK, MCP (`aws___call_aws` / `aws___run_script`), or curl (`localhost:2773/secretsmanager/get`). The plugin's `PreToolUse` `secret-safety.py` hook blocks these calls automatically so plaintext secrets never enter the LLM context window.
2. **Always use runtime dynamic references (`{{resolve:secretsmanager:...}}`) with `asm-exec` or CloudFormation/ECS/Lambda native resolution:**
   ```
   {{resolve:secretsmanager:<secret-id>:<field-type>:<json-key>:<version-stage>}}
   ```
   - Example with `asm-exec` (resolves references inside the child process without writing plaintext to stdout/LLM context):
     ```bash
     asm-exec -- psql \
       "host=mydb.example.com \
        user={{resolve:secretsmanager:prod/db-creds:SecretString:username}} \
        password={{resolve:secretsmanager:prod/db-creds:SecretString:password}}" \
       -c "SELECT current_user;"
     ```
   - Example for **ECS Task Definitions**: use `secrets[].valueFrom` pointing to the full Secret ARN (`arn:aws:secretsmanager:<region>:<acct>:secret:<name>:<json-key>::`) injected via `executionRoleArn`.
   - Example for **AWS Lambda**: use the **AWS Parameters and Secrets Lambda Extension** layer with IAM permission scoped to the specific secret ARN and CMK.
   - Example for **Amazon EKS**: use the **AWS Secrets Store CSI Driver** (`secrets-store-csi-driver-provider-aws`) paired with EKS Pod Identity or IRSA.

### 2.2 Creating & Auditing Production Secrets (Best-Practice Checklist)
When auditing (`secretsmanager:ListSecrets` → `DescribeSecret`, `GetResourcePolicy`) or proposing new secrets:
1. **Dedicated KMS CMK Encryption:** Always specify `--kms-key-id <cmk-arn>` (with `kms:ViaService == "secretsmanager.<region>.amazonaws.com"`).
2. **Automated 4-Step Rotation (`secretsmanager:RotateSecret`):**
   - Verify `RotationEnabled == true` and `AutomaticallyAfterDays <= 30` (or `90`).
   - Verify the rotation Lambda implements all four idempotent version-stage transitions (`AWSPENDING` → `AWSCURRENT` → `AWSPREVIOUS`):
     1. `createSecret`: generates a new high-entropy secret (`secretsmanager:GetRandomPassword`) in `AWSPENDING`.
     2. `setSecret`: updates the target database/service user credential (using the `ALTER USER` / dual-account alternating strategy so active connections never drop).
     3. `testSecret`: connects to the target using the `AWSPENDING` credential to verify read/write health before cutover.
     4. `finishSecret`: moves the `AWSCURRENT` staging label to the new version and demotes the old version to `AWSPREVIOUS`.
3. **Rotation Lambda Network & IAM Hardening:**
   - Place the rotation Lambda in private subnets reaching Secrets Manager solely via the `com.amazonaws.<region>.secretsmanager` Interface VPC Endpoint.
   - Include `"aws:SourceAccount"` on the Lambda's `lambda:InvokeFunction` resource policy granting access to `secretsmanager.amazonaws.com`.

---

## 3. PKI, AWS Private CA, ACM & Mutual TLS (mTLS) Governance

### 3.1 AWS Private Certificate Authority (`acm-pca`)
1. **CA Hierarchy Separation:**
   - Never issue end-entity workload certificates directly from the **Root Private CA**.
   - Keep the Root Private CA restricted to issuing **Subordinate (Intermediate) CAs**, and issue short-lived workload/mTLS client certificates from regional or domain-scoped Subordinate CAs.
2. **Revocation & Cross-Account Sharing Audit:**
   - Call `acm-pca:DescribeCertificateAuthority`: verify `Status == "ACTIVE"`, `KeyStorageSecurityStandard == "FIPS_140_2_LEVEL_3_OR_HIGHER"` (or CloudHSM/FIPS Level 3), and `RevocationConfiguration` has either **OCSP** enabled or **CRL** publishing to a dedicated S3 bucket (with `BlockPublicAccess` configured appropriately if using CloudFront OAC in front of the CRL bucket).
   - Call `acm-pca:ListPermissions` and `ram:GetResourceShares` to audit which member accounts can issue certificates via AWS RAM.

### 3.2 Mutual TLS (mTLS) on ALB, CloudFront & API Gateway
When auditing zero-trust service-to-service or B2B API endpoints:
1. **Application Load Balancer (ALB) mTLS (`elbv2:DescribeListeners` + `elbv2:DescribeTrustStores`):**
   - Verify HTTPS listeners protecting internal/partner APIs use `MutualAuthentication.Mode == "verify"` (not `"passthrough"` unless the backend validates the `X-Amzn-Mtls-Clientcert` header itself).
   - Verify `IgnoreClientCertificateExpiry == false`.
   - Call `elbv2:DescribeTrustStoreRevocations` to confirm a fresh Certificate Revocation List (CRL) is associated with the ALB Trust Store (`TrustStoreArn`).
2. **CloudFront Viewer mTLS & Origin mTLS (`cloudfront:GetDistributionConfig`):**
   - Verify `ViewerMtlsConfig.Mode == "required"` with an associated CloudFront Trust Store (`TrustStoreConfig.TrustStoreId`).
   - When forwarding client certificate metadata headers (`CloudFront-Viewer-TLS-*`), ensure origin security groups are locked to the AWS-managed `com.amazonaws.global.cloudfront.origin-facing` prefix list so attackers cannot spoof mTLS headers directly to the origin.
3. **Layer 2 / Layer 3 Network Transit Encryption:**
   - **Direct Connect (`directconnect:DescribeConnections`):** Verify **MACsec (IEEE 802.1AE)** encryption is active (`portEncryptionStatus == "Encryption Up"`) or an IPsec VPN runs over the transit VIF.
   - **Site-to-Site VPN (`ec2:DescribeVpnConnections`):** Verify both tunnels are `UP`, using **IKEv2**, **AES-256-GCM**, **SHA-2 (SHA256/384/512)**, and **Diffie-Hellman Groups 14–24** (flag weak SHA-1, AES-128-CBC, or DH Group 2).
