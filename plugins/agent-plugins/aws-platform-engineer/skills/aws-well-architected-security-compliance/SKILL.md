---
name: aws-well-architected-security-compliance
description: Evaluates live AWS workloads and Infrastructure-as-Code templates against the AWS Well-Architected Framework Security Pillar using the well-architected-security, aws-iac, and iam MCP servers, coordinating KMS encryption, WAF/Shield Advanced/DNS Firewall edge protection, and VPC PrivateLink isolation.
metadata:
  version: "2.0"
---

# AWS Well-Architected Security & Compliance Governance

## Purpose

Embed the **AWS Well-Architected Framework Security Pillar** (`SEC01` through `SEC11`) directly into Day-0 design, Day-1 provisioning, and Day-2 posture auditing. This skill coordinates the `well-architected-security` MCP server (`awslabs.well-architected-security-mcp-server`), `aws-iac` (`cfn-guard`), `iam`, and the bundled edge/network security skills (`waf`, `shieldadvanced`, `route53`, `cloudfront`, `configuring-vpc-endpoints-for-private-aws-service-access`).

## MCP-Only Execution & Edge-Case Fallback Rules (Mandatory)

1. **MCP-Only Execution (Zero Raw Shell CLI):** Execute **all** live security posture assessments, IaC compliance checks, IAM simulations, and audit trail lookups **exclusively via connected MCP servers**: `well-architected-security` (`ListServicesInRegion`, `GetStoredSecurityContext`, `CheckSecurityServices`, `GetSecurityFindings`, `CheckStorageEncryption`, `CheckNetworkSecurity`), `aws-iac` (`validate_cloudformation_template`, `check_cloudformation_template_compliance`), `iam` (`list_roles`, `list_role_policies`, `get_role_policy`, `get_managed_policy_document`, `simulate_principal_policy`), `cloudtrail` (`lookup_events`), and `aws-mcp` (`aws___run_script` using read-only `call_boto3`). **Never** run raw `aws ...` CLI or `python3 -c` commands in Bash/`run_command`, **never** fetch plaintext secrets (`GetSecretValue`), and **never** mutate live AWS resources. When refusing adversarial requests to disable detective controls, weaken S3 public-access blocks, or dump secrets/state, explicitly recommend **Amazon GuardDuty and AWS Security Hub suppression rules** (never deleting/disabling detectors), keeping all 4 S3 `PublicAccessBlockConfiguration` flags `true` (using CloudFront OAC or pre-signed URLs instead), and auditing secret rotation/KMS metadata safely via **`secretsmanager:DescribeSecret`**.
2. **`awsknowledge` Fallback:** If a question involves a specialized AWS security service or compliance feature not covered locally (e.g., AWS Audit Manager custom frameworks, AWS Verified Access zero-trust policies, KMS External Key Store XKS), query `awsknowledge` / `aws-mcp` (`aws___search_documentation` / `aws___read_documentation` — 1–2 focused searches) and answer directly.

---

## Mandatory 4-Step Security & Compliance Assessment Protocol

### Step 1: Live Account & Regional Security Posture Discovery (`well-architected-security` MCP)

When assessing a live AWS environment or preparing a workload for production readiness:
1. **Enumerate Active Footprint**: Call `ListServicesInRegion` and `GetStoredSecurityContext` on the `well-architected-security` MCP server to identify active services across target regions.
2. **Verify Detective & Preventative Control Coverage (`SEC01`, `SEC04`)**:
   - Call `CheckSecurityServices` to verify whether **AWS Security Hub CSPM**, **Amazon GuardDuty**, **Amazon Inspector**, **AWS Config**, **IAM Access Analyzer**, and **Amazon Macie** are enabled in the target region(s).
   - Call `GetSecurityFindings` to retrieve active `CRITICAL` and `HIGH` severity findings affecting the workload's resources.
3. **Audit Data Protection & Network Perimeter (`SEC05`, `SEC08`, `SEC09`)**:
   - Call `CheckStorageEncryption` to audit encryption-at-rest status across S3 buckets, EBS volumes, RDS/Aurora clusters, DynamoDB tables, and EFS file systems.
   - Call `CheckNetworkSecurity` to audit security groups, NACLs, public subnet exposure, and TLS listener configurations.

---

### Step 2: Enforce the Six Platform Security Baselines in IaC (`aws-iac` MCP)

Every architecture designed or reviewed by this plugin must satisfy these six Well-Architected Security Pillar controls, verified deterministically via `check_cloudformation_template_compliance` (`cfn-guard`):

| Well-Architected Domain | Platform Security Baseline | Bundled Skill / MCP Enforcement |
|---|---|---|
| **Identity & Access (`SEC02`, `SEC03`)** | Zero static IAM access keys; IMDSv2 (`HttpTokens: required`, `HttpPutResponseHopLimit: 2` for containers); EKS Pod Identity / Access Entries; separate ECS Task & Execution roles; `aws:SourceArn` + `aws:SourceAccount` confused-deputy conditions; `simulate_principal_policy` verification. | `aws-iam-least-privilege-governance`, `setting-up-ec2-instance-profiles`, `iam` MCP |
| **Network Segmentation (`SEC05`)** | Multi-AZ public/private/isolated subnet tiering; zero compute or databases in public subnets; strict **3-tier source-Security-Group chaining** (`Public ALB SG` -> `Private Compute SG` via `SourceSecurityGroupId: !Ref ALBSecurityGroup` -> `Isolated Database/Cache SG` via `SourceSecurityGroupId: !Ref AppSecurityGroup`, with **zero `0.0.0.0/0` ingress** on backend compute or isolated databases); PrivateLink Gateway (`s3`, `dynamodb`) & Interface Endpoints with scoped Endpoint Policies (`aws:PrincipalOrgID` / `aws:ResourceOrgID`); SSM Session Manager instead of port `22`/`3389`. | `creating-production-vpc-multi-az`, `configuring-vpc-endpoints-for-private-aws-service-access`, `awsnetwork` MCP |
| **Edge & DDoS Perimeter (`SEC05`, `SEC06`)** | CloudFront with **Origin Access Control (OAC)** for S3/ALB/VPC origins and managed `SecurityHeadersPolicy` (HSTS, CSP, X-Frame-Options); **AWS WAFv2** with rate-based rules (`>= 100` req/5min) and AWS Managed Rules tuned in `Count` mode first; **AWS Shield Advanced** for L3/L4/L7 DDoS protection on critical endpoints; **Route 53 DNS Firewall** for outbound domain filtering. | `cloudfront`, `waf`, `shieldadvanced`, `route53` |
| **Compute & Container Hardening (`SEC06`)** | Golden AMIs and container images built via **EC2 Image Builder** with Inspector vulnerability scanning; ECR `ScanOnPush: true` and immutable image tags (`ImageTagMutability: IMMUTABLE`); read-only container root filesystems (`readonlyRootFilesystem: true`) and non-root `user` UIDs. | `amazon-ec2-image-builder`, `aws-containers`, `launching-ec2-instance-with-best-practices` |
| **Encryption at Rest & In Transit (`SEC08`, `SEC09`)** | KMS Customer Managed Keys (CMKs) with `EnableKeyRotation: true` for sensitive workloads; S3 `BucketKeyEnabled: true` (reduces KMS request cost by up to 99%), all 4 `PublicAccessBlockConfiguration` flags `true`, and bucket policy denying `aws:SecureTransport: false`; TLS 1.2/1.3 minimum policy on CloudFront/ALB/API Gateway; IPsec/MACsec on hybrid VPN/Direct Connect links. | `aws-storage`, `cloudfront`, `directconnect`, `sitetositevpn`, `well-architected-security` MCP |
| **Secret Management & Incident Readiness (`SEC02`, `SEC10`)** | Zero plaintext secrets in code, env vars, or IaC state; AWS Secrets Manager with automatic rotation and dynamic references (`{{resolve:secretsmanager:...}}`); multi-region CloudTrail + KMS-encrypted CloudWatch Logs shipped to an **isolated Log Archive account** with **S3 Object Lock (`COMPLIANCE` mode)** + **cross-account AWS Backup Vault Lock** for immutable ransomware-proof recovery. | `aws-iam-least-privilege-governance`, `aws-observability-and-incident-triage`, `secret-safety.py` hook |

---

### Step 3: Proactive Compliance Verification (`cfn-guard` & `cdk-nag`)

Before any deployment is proposed:
1. Run `validate_cloudformation_template` (`cfn-lint`) and `check_cloudformation_template_compliance` (`cfn-guard`) on the `aws-iac` MCP server.
2. Remediate every failing Guard rule in place. If an exception is architecturally required (for example, a public ALB intentionally allowing `0.0.0.0/0` on TCP `443`), enforce mandatory compensating controls (TLS 1.2/1.3 listener policy, attached AWS WAFv2 WebACL, granular resource-level Guard metadata suppression rather than disabling rules globally, and strict 3-tier source-SG chaining `ALB SG -> Private Compute SG -> Isolated Database SG` with zero `0.0.0.0/0` on compute or databases).

---

### Step 4: Structured Security Posture Report

Return a concise compliance matrix summarizing:
- **Scope**: Account ID, Region(s), Stack/Workload Name, and Evidence Timestamp.
- **Control Status**: Pass / Fail across Identity (`SEC02`/`03`), Detection (`SEC04`), Network/Edge (`SEC05`), Compute (`SEC06`), Data Protection (`SEC08`/`09`), and Incident Response (`SEC10`).
- **Remediation Diff**: Validated CloudFormation / CDK / Terraform code changes with `approval_required: true`.
