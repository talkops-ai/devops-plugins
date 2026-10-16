---
description: "Construct an atomic Catalog API `StartChangeSet` for a Private Offer or CPPO with custom pricing, Flexible Payment Scheduler (FPS), and SCMP legal terms."
argument-hint: "<product-id> <buyer-account-ids>"
---

# `/aws-marketplace-seller:create-private-offer-workflow` — Construct an atomic Catalog API `StartChangeSet` for a Private Offer or CPPO with custom pricing, Flexible Payment Scheduler (FPS), and SCMP legal terms.

Target / arguments provided by user: `$ARGUMENTS`

## 1. Skills to Activate in Main Agent
Load and follow the domain playbooks and `references/` in these bundled skills:
- `aws-marketplace-private-offers-and-agreements`
- `aws-marketplace-catalog-and-listings`

## 2. MCP Servers & Tooling Sequence
Use the plugin's bound MCP servers (falling back to read-only AWS CLI only when an MCP tool does not cover the API):
- `aws-mcp` (`mcp__plugin_aws-marketplace-seller_aws-mcp__*`) — AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`).
- `awsknowledge` (`mcp__plugin_aws-marketplace-seller_awsknowledge__*`) — Official AWS documentation, Architecture Center, and Well-Architected knowledge base.
- `awspricing` (`mcp__plugin_aws-marketplace-seller_awspricing__*`) — Real-time AWS service pricing catalog and architecture cost calculation.
- `awsiac` (`mcp__plugin_aws-marketplace-seller_awsiac__*`) — CloudFormation & CDK template validation (`cfn-lint`), policy-as-code (`cfn-guard`), and CDK documentation.
- `cloudwatch` (`mcp__plugin_aws-marketplace-seller_cloudwatch__*`) — CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection.

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
- **Approval-Gated Mutation**: Complete all read-only discovery, architecture design, and cost estimation first. Present the exact execution plan (CLI commands, IaC diff, blast radius, rollback procedure, and estimated monthly cost) and **wait for explicit user confirmation** before executing any mutating call.
- Never hardcode secrets, plaintext passwords, or long-lived IAM access keys; enforce KMS encryption, IAM roles, and least-privilege conditions.

## 5. Required Output Structure
Present your response using these structured sections:
1. **Executive Summary & Current State**: What was inspected or designed, with exact resource ARNs/IDs and region.
2. **Findings / Architecture & Implementation**: Detailed root-cause analysis, service selection matrix, or production-grade code/IaC.
3. **Cost, Security & Reliability Impact**: Quantified FinOps estimate, IAM/KMS posture, and HA/DR considerations.
4. **Verification & Rollback Commands**: Exact CLI/MCP checks to verify success and revert safely if needed.
