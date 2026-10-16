---
name: security-remediation-governance
description: >-
  Performs AWS Cloud Architectural Threat Modeling (STRIDE across trust boundaries and multi-service
  attack paths) and converts AWS security findings and audit gaps into safe, shift-left validated
  remediation proposals across Terraform/HCL, AWS CDK (cdk-nag), CloudFormation (cfn-guard), and
  AWS CLI. Enforces pre-flight blast-radius verification, IAM Access Analyzer policy validation,
  human-in-the-loop (HITL) approval gates, deterministic rollback payloads, and post-change
  verification queries.
version: 3
---

# Security Remediation Governance, Cloud Threat Modeling & Shift-Left IaC Validation

Use this skill for:
1. **Cloud Architectural Threat Modeling (STRIDE & Attack Path Analysis)** on AWS architecture designs, data flows, and Infrastructure-as-Code (Terraform, CDK, CloudFormation), and
2. **Safe, Approval-Gated Remediation Planning & Shift-Left Policy Validation** after detective audits (`security-posture-audit`, `security-identity-governance`, `security-data-protection`, `security-network-perimeter`, `security-workload-containers`, or `security-incident-triage`).

## Reference Library (Load On-Demand)

- **[references/hitl-remediation-workflows.md](references/hitl-remediation-workflows.md)** — Load when performing AWS STRIDE architectural threat modeling across trust boundaries, designing EventBridge (ASFF/OCSF) + Step Functions (`waitForTaskToken`) human-approved remediation state machines, running pre-remediation blast-radius traffic checks, or authoring/validating shift-left rules across **CloudFormation Guard (`cfn-guard`)**, **AWS CDK (`cdk-nag`)**, and **Terraform/HCL**.

---

## Workflow A: Cloud Architectural Threat Modeling (STRIDE for AWS)

When an engineer presents an architecture diagram, service topology, or IaC stack for design review:

1. **Decompose Trust Boundaries:**
   - **Boundary 1 — Internet & Edge Entry:** Route 53, CloudFront, WAFv2, Shield Advanced, public ALB/API Gateway.
   - **Boundary 2 — VPC & Network Segmentation:** Public vs. Private vs. Isolated Data subnets, Transit Gateway route tables, Network Firewall, VPC Interface/Gateway Endpoints (`aws:PrincipalOrgID`).
   - **Boundary 3 — Compute & Runtime Execution:** EKS Pods (`Pod Identity` / `IRSA`), ECS Tasks (`taskRoleArn` vs. `executionRoleArn`), Lambda MicroVMs (`SnapStart`), EC2 (`IMDSv2 hop limit = 1`), Bedrock Agents/Guardrails.
   - **Boundary 4 — Data & Cryptographic Plane:** S3 (`BlockPublicAccess`, `SSE-KMS`, `Object Lock`), RDS/DynamoDB, KMS CMKs (`kms:ViaService`, `kms:EncryptionContext`), Secrets Manager (`asm-exec`).
   - **Boundary 5 — Identity & Organization Control Plane:** IAM Roles, Confused-Deputy conditions (`aws:SourceArn`, `aws:SourceAccount`), Permission Boundaries, SCPs, RCPs, and CloudTrail/Security Hub audit logging.
2. **Evaluate STRIDE Threats Per Trust Boundary Crossing:**
   - **S — Spoofing:** Missing `aws:SourceArn`/`aws:SourceAccount` confused-deputy guards; direct origin bypass around CloudFront/WAF; unverified OIDC `:sub` wildcard claims; unauthenticated Lambda Function URLs.
   - **T — Tampering:** Missing S3 Object Lock or CloudTrail log file validation; mutable ECR tags; missing KMS encryption context; unguarded S3 bucket policies.
   - **R — Repudiation:** Disabled CloudTrail Data Events, VPC Flow Logs, WAF logs, Route 53 Resolver Query Logs, ECS Exec session logs, or Bedrock Model Invocation Logs; shared IAM roles or static IAM user access keys lacking `sts:SourceIdentity`.
   - **I — Information Disclosure:** Public S3/RDS/EBS snapshots; SSRF -> IMDSv1 credential theft; missing RCP/VPC Endpoint data perimeters (`s3:DataAccessPointAccount`); plaintext secrets in Lambda/ECS environment variables; unredacted PII in Bedrock prompts/logs.
   - **D — Denial of Service:** Public endpoints lacking WAF rate-based rules, Shield Advanced L7 auto-mitigation, API Gateway usage plans/throttling, or Lambda reserved concurrency caps.
   - **E — Elevation of Privilege:** IAM privilege escalation chains (`iam:PassRole` + compute creation, `iam:SetDefaultPolicyVersion`, `sts:AssumeRole` loops); Cognito writable custom attributes; shared ECS `executionRoleArn`/`taskRoleArn`.
3. **Trace Multi-Service Attack Paths:**
   - Map how an initial foothold (e.g., SSRF on a public container -> IMDS/Task Role -> overly permissive `s3:GetObject` or `secretsmanager:GetSecretValue` -> cross-account `sts:AssumeRole`) chains across AWS services, and specify the exact **detective**, **preventive**, and **corrective** controls that sever each link in the chain.

---

## Workflow B: Four-Phase Remediation Lifecycle

1. **Phase 1 — Detective & Pre-Flight Blast-Radius Check (Read-Only):**
   - Preserve the original finding ID, resource ARN, current configuration state (for rollback), and evidence timestamp.
   - **Mandatory Active-Usage Check Before Proposing Restrictive Changes:**
     - Before proposing **IAM Access Key deactivation**, verify `iam:GetAccessKeyLastUsed` and recent `cloudtrail:LookupEvents` so you explicitly warn the operator if a production service is actively authenticating with that key!
     - Before proposing **Security Group rule revocation**, check `ec2:DescribeNetworkInterfaces` (attached ENIs) and query VPC Flow Logs (`cloudwatch` MCP server) for `ACCEPT` traffic on that port so you warn if active production connections will break.
     - Before proposing **S3 Bucket Policy or KMS Key Policy lockdown**, check CloudTrail/Server Access Logs for legitimate internal roles or AWS services accessing the resource, and fetch the existing policy first so statements are merged rather than overwritten.
2. **Phase 2 — Multi-IaC Authoring & Shift-Left Validation (No Cloud Mutation):**
   - Author the minimal **Terraform (HCL)**, **AWS CDK (TypeScript/Python)**, **CloudFormation**, or **AWS CLI** diff matching the user's stack.
   - **Validate IAM Policies Before Proposing:**
     - Run `accessanalyzer:ValidatePolicy` (`IDENTITY_POLICY`, `RESOURCE_POLICY`, or `SERVICE_CONTROL_POLICY`) via the `iam` or `aws-mcp` server to guarantee zero `ERROR` or `SECURITY_WARNING` findings.
   - **Validate CloudFormation / CDK Templates Before Proposing:**
     - Use the `awsiac` MCP server (`validate_cloudformation_template`, `check_cloudformation_template_compliance` with `cfn-guard`) and include `cdk-nag` (`AwsSolutionsChecks` / `NIST80053R5Checks`) or Terraform security invariants where applicable.
3. **Phase 3 — Human Approval Gate (`approval_required: true`):**
   - Present the structured remediation contract below, explicitly detailing affected accounts, regions, resources, required execution permissions, outage/downtime risk, exact rollback command, and required approver role.
   - **Never treat model invocation or tool availability as approval to mutate live AWS state.**
4. **Phase 4 — External Execution & Closed-Loop Verification:**
   - Once an operator or approved Step Functions/CI pipeline applies the change, execute the `verification_query` (`iam:SimulatePrincipalPolicy`, `configservice:GetComplianceDetailsByConfigRule`, `securityhub:GetFindings`, or direct resource `Describe*`) to confirm the finding is resolved and no regression occurred.

---

## Standardized Remediation Proposal Contract

Every remediation proposal MUST include all fields in this contract:

```json
{
  "finding_id": "arn:aws:securityhub:us-east-1:111122223333:security-control/S3.1/finding/...",
  "root_cause": "Account-level S3 Block Public Access has BlockPublicAcls=false and IgnorePublicAcls=false.",
  "affected_resources": [
    "arn:aws:s3:::prod-analytics-bucket"
  ],
  "active_traffic_blast_radius_check": {
    "checked_via": "s3api:GetBucketPolicyStatus + s3api:GetBucketAcl + CloudTrail LookupEvents",
    "active_public_requests_detected": false,
    "impact_assessment": "Low — no bucket policy or ACL currently grants public read/write."
  },
  "validation_performed": {
    "iam_access_analyzer_validate_policy": "PASSED (0 errors, 0 security warnings)",
    "cfn_guard_compliance": "PASSED"
  },
  "proposed_change": {
    "iac_terraform": "resource \"aws_s3_account_public_access_block\" \"main\" {\n  block_public_acls       = true\n  block_public_policy     = true\n  ignore_public_acls      = true\n  restrict_public_buckets = true\n}",
    "cli_command": "aws s3control put-public-access-block --account-id 111122223333 --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
  },
  "permissions_required": [
    "s3:PutAccountPublicAccessBlock"
  ],
  "rollback": {
    "captured_previous_state": {
      "BlockPublicAcls": false,
      "IgnorePublicAcls": false,
      "BlockPublicPolicy": true,
      "RestrictPublicBuckets": true
    },
    "cli_command": "aws s3control put-public-access-block --account-id 111122223333 --public-access-block-configuration BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=true,RestrictPublicBuckets=true"
  },
  "approval_required": true,
  "verification_query": "aws s3control get-public-access-block --account-id 111122223333"
}
```

## Non-Negotiable Safety Guardrails

- Never propose destructive deletions (`DeleteBucket`, `DeleteDBInstance`, `ScheduleKeyDeletion`, `DeleteUser`, `DeleteRole`, `TerminateInstances`) without first proposing a non-destructive quarantine/disable step (`Inactive` access key, quarantine SG, snapshot backup).
- Never purge CloudTrail logs, S3 access logs, or CloudWatch log groups.
- Never propose wildcard `Action: "*"` or unrestricted `iam:PassRole` as a remediation shortcut.
