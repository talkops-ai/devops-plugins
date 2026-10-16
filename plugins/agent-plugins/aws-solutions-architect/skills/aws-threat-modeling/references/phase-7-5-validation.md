# Phase 7.5: Code & IaC Mitigation Validation Checklist

Before marking any STRIDE threat as **`Mitigated`** in `.threatmodel/<workload>-threat-model.md`, verify that the control is deterministically present in the repository's IaC/code and passes `iac` MCP validation (`validate_cloudformation_template` and `check_cloudformation_template_compliance`).

## Verification Matrix

| Claimed Mitigation Control | Required IaC / Code Evidence to Mark `Mitigated` | Status if Missing from Code |
|---|---|---|
| **S3 Bucket Public Access Blocked** | `PublicAccessBlockConfiguration` with all 4 booleans (`BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`, `RestrictPublicBuckets`) set to `true` | `Unmitigated (High)` |
| **Encryption at Rest (KMS / SSE)** | `BucketEncryption` (`aws:kms` + `BucketKeyEnabled: true`), `StorageEncrypted: true` on RDS/Aurora, `Encrypted: true` on EBS, `KmsMasterKeyId` on SQS/SNS/DynamoDB/LogGroup | `Unmitigated (Medium/High)` |
| **Encryption in Transit** | S3 Bucket Policy denying `aws:SecureTransport: "false"`, ALB HTTPS listener (`ELBSecurityPolicy-TLS13-1-2-2021-06`), RDS `rds.force_ssl=1` | `Unmitigated (High)` |
| **Least-Privilege IAM** | Zero `"Action": "*"` + `"Resource": "*"` pairs; `aws:SourceArn` / `aws:SourceAccount` present on service trust policies; separate ECS Execution vs Task Role | `Unmitigated (Critical/High)` |
| **Database Credential Safety** | `ManageMasterUserPassword: true` on RDS/Aurora or `{{resolve:secretsmanager:...}}` dynamic reference; zero hardcoded passwords or `.env` files | `Unmitigated (Critical)` |
| **Network Isolation** | Compute & Database resources placed in private/isolated subnets (`MapPublicIpOnLaunch: false`); Security Group ingress references source SG IDs rather than `0.0.0.0/0` | `Unmitigated (High)` |
| **Poison-Pill / DoS Resilience** | SQS `RedrivePolicy` (`maxReceiveCount: 3..5`) with DLQ, Lambda `ReservedConcurrentExecutions` or API Gateway throttling, WAFv2 WebACL association | `Unmitigated (Medium)` |
| **Audit & Non-Repudiation** | CloudWatch `LogGroup` with explicit `RetentionInDays` and KMS key; X-Ray `Tracing: Active`; ALB/WAF/VPC Flow Logging enabled | `Unmitigated (Medium)` |

## Phase 7.5 Sign-Off Block (Include in `.threatmodel/` Output)

```markdown
### Phase 7.5 IaC Verification Summary
- **Templates Scanned:** `<list of CDK/CFN/TF files>`
- **`cfn-lint` (`validate_cloudformation_template`):** PASS / FAIL (`<N>` errors)
- **`cfn-guard` (`check_cloudformation_template_compliance`):** PASS / FAIL (`<N>` violations)
- **Verified Mitigations:** `<M>` / `<Total>`
- **Open Remediation Items:** `<K>` (listed with exact file/line targets below)
```
