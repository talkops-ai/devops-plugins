---
name: hardening-iac-and-perimeter
description: >-
  Audits and hardens Infrastructure-as-Code templates (Terraform, AWS CDK, CloudFormation, SAM,
  Dockerfiles) and live AWS network, storage, and encryption perimeters (VPC Security Groups,
  NACLs, WAFv2 WebACLs, S3 Block Public Access, KMS CMK rotation, RDS encryption, Secrets Manager)
  against the AWS Well-Architected Security Pillar (`aws-well-architected-security`). Use when
  the user asks to "harden my infrastructure", "audit Terraform/CDK security", "lock down VPC/S3/KMS",
  or runs `/harden`.
---

# Infrastructure-as-Code (IaC) & Cloud Perimeter Hardening

## When to Use
Invoke this skill whenever a user wants to audit or harden local IaC templates (`*.tf`, `*.ts`, `template.yaml`, `*.json`, `Dockerfile`) or live AWS infrastructure across network perimeters (VPC, Security Groups, ALB, CloudFront, WAFv2), data protection (S3, KMS, Secrets Manager, RDS, DynamoDB), and compute isolation.

## 4-Phase IaC & Perimeter Hardening Workflow

### Phase 1: Static IaC & Container Security Audit
Scan the local repository using `Glob` and `Grep` to inspect all IaC and container manifests:
1. **CloudFormation / SAM / CDK Synthesized Templates**:
   - Run `cfn-lint` and `cfn-guard` (if installed locally) or inspect resource properties for security anti-patterns.
   - Verify `DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain` on all stateful resources (`AWS::RDS::DBCluster`, `AWS::DynamoDB::Table`, `AWS::S3::Bucket`, `AWS::KMS::Key`).
2. **Terraform (`*.tf`)**:
   - Audit `aws_security_group_rule`, `aws_s3_bucket_public_access_block`, `aws_kms_key`, `aws_db_instance`, `aws_ecs_task_definition`, and `aws_iam_policy_document`.
3. **Dockerfiles**:
   - Flag `USER root` (or missing non-root `USER`), unpinned `:latest` tags, secrets baked into `ENV`/`ARG`, and unnecessary OS packages; recommend multi-stage distroless/minimal builds.

### Phase 2: Live Perimeter & Data-Protection Audit (`aws-well-architected-security` + `aws-mcp`)
Correlate local IaC with live AWS resource configurations using `aws-well-architected-security` (`CheckNetworkSecurity`, `CheckStorageEncryption`) and `aws___run_script`:

```python
import boto3

session = boto3.Session()
ec2 = session.client("ec2")
s3 = session.client("s3")
kms = session.client("kms")

# 1. Security Groups with unrestricted 0.0.0.0/0 or ::/0 ingress on non-80/443 ports
open_sgs = []
for sg in ec2.describe_security_groups()["SecurityGroups"]:
    for perm in sg.get("IpPermissions", []):
        from_port = perm.get("FromPort")
        ip_ranges = [r["CidrIp"] for r in perm.get("IpRanges", []) if r.get("CidrIp") == "0.0.0.0/0"]
        ipv6_ranges = [r["CidrIpv6"] for r in perm.get("Ipv6Ranges", []) if r.get("CidrIpv6") == "::/0"]
        if (ip_ranges or ipv6_ranges) and from_port not in (80, 443):
            open_sgs.append({"groupId": sg["GroupId"], "groupName": sg["GroupName"], "port": from_port})

# 2. S3 Account-Level Block Public Access
sts = session.client("sts")
account_id = sts.get_caller_identity()["Account"]
s3control = session.client("s3control")
try:
    bpa = s3control.get_public_access_block(AccountId=account_id)["PublicAccessBlockConfiguration"]
except Exception as exc:
    bpa = {"error": str(exc)}

print({"open_security_groups": open_sgs, "account_s3_bpa": bpa})
```

### Phase 3: Mandatory Hardening Controls Checklist

| Domain | Required Hardening Standard |
|---|---|
| **S3 Storage** | Enforce `BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`, `RestrictPublicBuckets = true`; SSE-KMS or SSE-S3 encryption; bucket policy denying `aws:SecureTransport: false` (HTTP) and enforcing minimum `s3:TlsVersion >= 1.2`. |
| **Network & Edge** | Remove `0.0.0.0/0` ingress on SSH (`22`), RDP (`3389`), and database ports; replace bastion hosts with SSM Session Manager / VPC Endpoints; attach AWS WAFv2 WebACLs (`AWSManagedRulesCommonRuleSet`, `AWSManagedRulesKnownBadInputsRuleSet`, rate-based rules) to public ALBs, API Gateways, and CloudFront distributions. |
| **Encryption & KMS** | Enable automatic annual key rotation (`EnableKeyRotation: true`) on customer-managed KMS keys; scope KMS key policies with `kms:ViaService` conditions. |
| **Secrets Management** | Eliminate plaintext credentials in Lambda `Environment.Variables`, ECS `environment`, and `.env` files; migrate to AWS Secrets Manager (`secrets` block with ARN injection) and enable automatic rotation. |
| **Compute & Databases** | Enforce EC2 IMDSv2 (`HttpTokens: required`, `HttpPutResponseHopLimit: 1` or `2` for containers); enable `StorageEncrypted: true`, `DeletionProtection: true`, and `iam_database_authentication_enabled` on RDS/Aurora. |

### Phase 4: Patch Synthesis & Verification
1. Apply the hardening changes directly to the repository's Terraform, CDK, or CloudFormation files.
2. Run `diff-scanning-with-aws-security-agent` or `validating-release-readiness` to confirm the hardened IaC introduces zero breaking replacement risks on stateful resources.
