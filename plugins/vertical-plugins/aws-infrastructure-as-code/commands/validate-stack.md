---
description: "Validate CloudFormation, SAM, CDK, or Terraform code for syntax, schema, and security compliance (`cfn-lint` & `cfn-guard`)."
argument-hint: "[path-to-template-or-cdk-app]"
---

# `/aws-infrastructure-as-code:validate-stack` — Validate CloudFormation, SAM, CDK, or Terraform code for syntax, schema, and security compliance (`cfn-lint` & `cfn-guard`).

Target / arguments provided by user: `$ARGUMENTS`

## 1. Skills to Activate in Main Agent
Load and follow the domain playbooks and `references/` in these bundled skills:
- `aws-cloudformation`
- `aws-cdk`
- `aws-terraform`
- `aws-iam-and-security`

## 2. MCP Servers & Tooling Sequence
Use the plugin's bound MCP servers (falling back to read-only AWS CLI only when an MCP tool does not cover the API):
- `aws-mcp` (`mcp__plugin_aws-infrastructure-as-code_aws-mcp__*`) — AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`).
- `awsknowledge` (`mcp__plugin_aws-infrastructure-as-code_awsknowledge__*`) — Official AWS documentation, Architecture Center, and Well-Architected knowledge base.
- `awsiac` (`mcp__plugin_aws-infrastructure-as-code_awsiac__*`) — CloudFormation & CDK template validation (`cfn-lint`), policy-as-code (`cfn-guard`), and CDK documentation.
- `awspricing` (`mcp__plugin_aws-infrastructure-as-code_awspricing__*`) — Real-time AWS service pricing catalog and architecture cost calculation.
- `pulumi` (`mcp__plugin_aws-infrastructure-as-code_pulumi__*`) — Pulumi Cloud AI MCP server for Pulumi IaC components and AWS provider schemas.

## 3. Step-by-Step Operational Workflow

1. **Preflight & Context Verification**:
   - Confirm active AWS account, region (`AWS_REGION`), and caller identity (`sts:GetCallerIdentity`) or inspect local IaC/application files in the workspace if operating offline.
   - Parse `$ARGUMENTS` to identify target resource identifiers, regions, or architectural constraints. If a required identifier is ambiguous, list the discovered candidates first.
2. **Evidence Collection & Domain Analysis**:
   - Query live AWS state, telemetry, or official documentation using the MCP servers above and the decision trees in the activated skills.
   - Cross-check configuration against AWS Well-Architected best practices (Security, Reliability, Performance Efficiency, Cost Optimization, Operational Excellence).
3. **Synthesis, Remediation / Implementation & Verification**:
   - Produce production-ready configurations, IaC/SDK code, or root-cause diagnostic findings with copy-pasteable verification commands.
   - Where pricing or capacity changes are involved, calculate the estimated monthly cost delta using `awspricing` / `billing` before recommending changes.

## 4. Safety & Mutation Policy
- **Read-Only Operation**: Execute only non-destructive discovery, validation, and diagnostic calls (`Describe*`, `Get*`, `List*`, `Query*`). Do **not** create, modify, or delete AWS resources unless the user explicitly asks to apply a remediation and approves the exact command.
- Never hardcode secrets, plaintext passwords, or long-lived IAM access keys; enforce KMS encryption, IAM roles, and least-privilege conditions.

## 5. Required Output Structure
Present your response using these structured sections:
1. **Executive Summary & Current State**: What was inspected or designed, with exact resource ARNs/IDs and region.
2. **Findings / Architecture & Implementation**: Detailed root-cause analysis, service selection matrix, or production-grade code/IaC.
3. **Cost, Security & Reliability Impact**: Quantified FinOps estimate, IAM/KMS posture, and HA/DR considerations.
4. **Verification & Rollback Commands**: Exact CLI/MCP checks to verify success and revert safely if needed.
