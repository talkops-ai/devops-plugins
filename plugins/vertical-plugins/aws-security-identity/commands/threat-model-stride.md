---
description: "Conduct a STRIDE threat model with AWS Threat Composer JSON output and map threats to preventive SCP, IAM, WAF, and KMS controls."
argument-hint: "<workload-or-iac-path>"
---

# `/aws-security-identity:threat-model-stride` — Conduct a STRIDE threat model with AWS Threat Composer JSON output and map threats to preventive SCP, IAM, WAF, and KMS controls.

Target / arguments provided by user: `$ARGUMENTS`

## 1. Skills to Activate in Main Agent
Load and follow the domain playbooks and `references/` in these bundled skills:
- `aws-threat-modeling`
- `hardening-iac-and-perimeter`

## 2. MCP Servers & Tooling Sequence
Use the plugin's bound MCP servers (falling back to read-only AWS CLI only when an MCP tool does not cover the API):
- `aws-mcp` (`mcp__plugin_aws-security-identity_aws-mcp__*`) — AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`).
- `iam` (`mcp__plugin_aws-security-identity_iam__*`) — IAM users, roles, policies, and inline access simulation (read-only).
- `wa-security` (`mcp__plugin_aws-security-identity_wa-security__*`) — Well-Architected Security Pillar assessment, Security Hub, and GuardDuty posture checks.
- `aws-security-agent` (`mcp__plugin_aws-security-identity_aws-security-agent__*`) — AWS Security Agent application security posture, SAST/DAST findings, and pentest remediation.
- `cloudtrail` (`mcp__plugin_aws-security-identity_cloudtrail__*`) — CloudTrail management and data event lookup for incident forensics and audit trails.
- `awsiac` (`mcp__plugin_aws-security-identity_awsiac__*`) — CloudFormation & CDK template validation (`cfn-lint`), policy-as-code (`cfn-guard`), and CDK documentation.
- `cloudwatch` (`mcp__plugin_aws-security-identity_cloudwatch__*`) — CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection.
- `tm` (`mcp__plugin_aws-security-identity_tm__*`) — AWS Threat Composer STRIDE threat modeling and mitigation validation.

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
