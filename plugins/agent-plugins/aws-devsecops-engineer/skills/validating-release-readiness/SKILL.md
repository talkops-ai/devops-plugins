---
name: validating-release-readiness
description: >-
  Executes a comprehensive pre-deployment and pre-merge release-readiness gate on local git
  diffs, pull requests, and IaC change sets: inspects CloudFormation change sets / `cdk diff` /
  `terraform plan` for stateful resource replacement (`Replacement: True`), runs
  `diff-scanning-with-aws-security-agent`, validates IAM policies via Access Analyzer, and checks
  CloudWatch rollback alarms. Use when the user asks "is this PR ready to deploy", "run a release
  readiness review", "check deployment blast radius", or runs `/release-readiness`.
---

# Release-Readiness & Change-Set Blast-Radius Gate

## When to Use
Invoke this skill before merging a pull request or promoting a release to staging/production. It replaces legacy black-box release checks with a deterministic, local+cloud 5-gate verification pipeline across code, Infrastructure-as-Code, IAM permissions, security vulnerabilities, and operational rollback readiness.

## 5-Gate Release Readiness Pipeline

### Gate 1: Git Diff Classification & Risk Scoping
Inspect the candidate release changes in the local workspace:

```bash
git status --short
git diff --stat HEAD~1..HEAD   # or against main / target branch
```

Classify modified files into risk tiers:
- **Stateful Infrastructure**: RDS, Aurora, DynamoDB, S3, KMS, ElastiCache, OpenSearch, VPC/Subnets
- **Identity & Perimeter**: IAM roles/policies, Security Groups, NACLs, WAFv2, OIDC providers
- **Stateless Compute & App Code**: Lambda handlers, ECS task definitions, Dockerfiles, API routes, SDK dependencies
- **Database Migrations**: Alembic, Flyway, Prisma, Liquibase, or raw DDL scripts (verify **Expand-and-Contract** backward compatibility so blue and green tasks can run concurrently)

### Gate 2: Dry-Run Infrastructure Change-Set & Replacement Analysis
Generate a non-executing infrastructure diff against the target AWS environment:
- **AWS CDK**: Run `npx cdk diff`
- **CloudFormation / SAM**: Create a dry-run Change Set (`aws cloudformation create-change-set --change-set-type UPDATE` followed by `aws cloudformation describe-change-set`) and delete the dry-run change set after inspection
- **Terraform**: Run `terraform plan -no-color`

Inspect every resource modification for destructive replacement indicators:
- CloudFormation `Replacement: "True"` or `"Conditional"` (`RequiresRecreation: "Always"`)
- Terraform `must be replaced` (`-/+` or `+/-`)

**Hard Block Condition**: If any stateful resource (`AWS::RDS::*`, `AWS::DynamoDB::Table`, `AWS::S3::Bucket`, `AWS::KMS::Key`) is marked for replacement or deletion, mark the release **NO-GO (BLOCKED)** and explain how to refactor the change without destroying data.

### Gate 3: Security Diff Scan & IAM Policy Validation
1. **Code & IaC Vulnerability Diff Scan**: Invoke `diff-scanning-with-aws-security-agent` on the modified files to detect newly introduced SAST vulnerabilities (SQLi, SSRF, command injection, hardcoded secrets).
2. **IAM Access Analyzer Check**: If any IAM policies or roles changed in the diff, invoke `engineering-iam-least-privilege` (`aws accessanalyzer validate-policy`) to ensure zero `ERROR` or `SECURITY_WARNING` findings.

### Gate 4: Operational & Rollback Readiness Check
Query `aws-cloudwatch` and `aws-mcp` against the target environment before authorizing deployment:
1. **Pre-Existing Incident Check**: Call `get_active_alarms` — do not deploy into an environment that already has active P0/P1 alarms firing unless the release is a targeted hotfix.
2. **Rollback Automation Verification**: Confirm the target stack/service has automated rollback configured:
   - ECS: `deploymentCircuitBreaker: { enable: true, rollback: true }`
   - CodeDeploy: `autoRollbackConfiguration` + `alarmConfiguration`
   - CloudFormation: `RollbackConfiguration` wired to CloudWatch error/latency alarms

### Gate 5: Go / No-Go Release Readiness Scorecard
Output a structured release decision scorecard:

| Gate | Check | Status | Evidence / Action Required |
|---|---|---|---|
| **1. Diff Scope & DB Compatibility** | Expand-and-Contract / Backward-compatible schema | PASS / WARN / FAIL | `<files modified>` |
| **2. IaC Blast Radius** | Zero stateful resource replacements (`Replacement: False`) | PASS / FAIL | `<cdk diff / change-set summary>` |
| **3. Security & IAM Gate** | Diff scan (`0 CRITICAL/HIGH`) + Access Analyzer clean | PASS / FAIL | `<scan job ID & policy check>` |
| **4. Rollback & Alarm Readiness** | Target alarms `OK` + Circuit Breaker / Auto-Rollback wired | PASS / WARN | `<alarm ARNs>` |
| **Overall Verdict** | **GO / CONDITIONAL GO / NO-GO (BLOCKED)** | | |
