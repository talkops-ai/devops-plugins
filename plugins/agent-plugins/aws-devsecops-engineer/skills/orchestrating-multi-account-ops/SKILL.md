---
name: orchestrating-multi-account-ops
description: >-
  Coordinates cross-account and multi-region AWS DevSecOps operations across development,
  staging, production, and security/audit accounts using `aws-mcp` dynamic `aws_profile`
  switching and AWS Organizations hierarchy discovery. Use when the user asks to "compare
  staging vs prod", "audit across multiple AWS accounts", "promote changes across environments",
  or runs `/accounts`.
---

# Multi-Account & Cross-Environment DevSecOps Orchestration

## When to Use
Invoke this skill whenever a user operates across multiple AWS accounts or environments (e.g., `dev`, `staging`, `prod`, `security-tooling`, `shared-services`) to compare posture, trace cross-account incidents, validate environment parity, or orchestrate staged promotions. This skill replaces legacy multi-AgentSpace coordination with direct SigV4 profile routing via `aws-mcp`.

## 4-Step Multi-Account Workflow

### Step 1: Discover Local AWS Profiles & Account Topology
1. Enumerate configured local profiles in `~/.aws/config` (never read `~/.aws/credentials`):

```bash
aws configure list-profiles
```

2. Verify caller identity for each target profile using `aws___call_aws` with the `aws_profile` parameter:

```
Tool: aws___call_aws
Arguments:
  cli_command: "aws sts get-caller-identity"
  aws_profile: "staging"
```

```
Tool: aws___call_aws
Arguments:
  cli_command: "aws sts get-caller-identity"
  aws_profile: "prod"
```

If any profile's SSO or login session has expired, invoke `signing-in-to-aws` (`aws login --profile <name>` or `aws sso login --profile <name>`) before proceeding.

### Step 2: Cross-Account Execution Patterns (`aws_profile`)
Both `aws___call_aws` and `aws___run_script` in `aws-mcp` accept an explicit `aws_profile` argument per invocation, allowing seamless switching between accounts within a single conversation turn:

1. **Cross-Environment Configuration & Drift Comparison (`staging` vs. `prod`)**:
   - Compare CloudFormation stack parameters/outputs, ECS task definition revisions, Lambda environment configuration keys (never secret values), and Security Group rules between `staging` and `prod`.
2. **Multi-Account Security Posture Aggregation**:
   - Run `triaging-cloud-security-posture` across each account profile (or from the AWS Organizations delegated Security Hub / GuardDuty administrator account) to build a unified multi-account risk matrix.
3. **Cross-Account IAM & Resource Policy Auditing**:
   - Audit cross-account trust relationships (`Principal.AWS` in IAM role trust policies, S3 bucket policies, KMS key policies, SNS/SQS policies, EventBridge buses) and verify that `aws:PrincipalOrgID` conditions are enforced to prevent confused-deputy and external account access.

### Step 3: Staged Promotion Gate (`dev` → `staging` → `prod`)
When promoting infrastructure or application changes across accounts:
1. Run `validating-release-readiness` against `staging` first.
2. After `staging` deployment, execute `executing-synthetic-release-tests` on `staging` and confirm all canaries and CloudWatch alarms pass.
3. Require an explicit human confirmation gate (`aws-mutation-gate.py`) showing the exact target Account ID (`123456789012`) and profile (`prod`) before executing any mutating operation in production.

### Step 4: Unified Multi-Account Summary Table
Always label every finding, metric, or resource ARN with its **Account ID**, **Profile Name**, and **Region**:

| Account / Profile | Region | Domain | Status / Findings | Action Required |
|---|---|---|---|---|
| `111122223333` (`staging`) | `us-east-1` | Release Readiness / UAT | PASS (0 alarms, canary green) | Ready for prod promotion |
| `444455556666` (`prod`) | `us-east-1` | Security Posture | 1 HIGH (SG `sg-0abc` open on 5432) | Patch in `infra/network.tf` |
