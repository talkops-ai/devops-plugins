# AWS Security and Identity

Cloud security, identity governance, and incident forensics for the main agent: IAM least-privilege & Access Analyzer, AWS Organizations SCPs/RCPs, KMS & Secrets Manager, Security Hub CSPM (OCSF), GuardDuty & CloudTrail incident triage, WAF/Network Firewall perimeter hardening, container workload security, and STRIDE threat modeling.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-security-identity@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-cloud-security-engineer`](../../agent-plugins/aws-cloud-security-engineer) or [`aws-devsecops-engineer`](../../agent-plugins/aws-devsecops-engineer) or [`aws-solutions-architect`](../../agent-plugins/aws-solutions-architect) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-security-identity:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-security-identity:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `auditing-cloudtrail-forensics` | >- |
| `aws-auth` | > |
| `aws-iam` | > |
| `aws-secrets-manager` | > |
| `aws-security` | Covers AWS security services and workflows — Security Hub V2 (OCSF) findings, connectors, aggregators, automation rules, and security posture summaries; Security Hub CSPM (V1/ASFF) controls and compl… |
| `aws-threat-modeling` | Executes phased STRIDE threat modeling across business context, trust boundaries, data asset flows, threat actors, OWASP LLM Top 10 / MITRE ATT&CK vectors, and AWS preventative/detective/responsive c… |
| `creating-secrets-using-best-practices` | Creates and manages secrets in AWS Secrets Manager following security best practices. |
| `hardening-iac-and-perimeter` | >- |
| `security-data-protection` | >- |
| `security-identity-governance` | >- |
| `security-incident-triage` | >- |
| `security-network-perimeter` | >- |
| `security-posture-audit` | >- |
| `security-remediation-governance` | >- |
| `security-workload-containers` | >- |

## Commands

| Command | Description |
|---|---|
| `/aws-security-identity:audit-iam` | Audit IAM roles, policies, SCPs/RCPs, and Access Analyzer findings for privilege escalation paths, wildcard actions, and missing condition keys. |
| `/aws-security-identity:audit-kms-and-data-protection` | Audit KMS customer-managed key policies, grants, key rotation, Macie sensitive data discovery, and TLS/ACM certificate posture. |
| `/aws-security-identity:rotate-secrets` | Audit AWS Secrets Manager secrets and design automated rotation workflows with KMS envelope encryption and least-privilege resource policies. |
| `/aws-security-identity:security-posture` | Assess account security posture across Security Hub CSPM (OCSF), GuardDuty, IAM Access Analyzer, KMS, and S3 public access. |
| `/aws-security-identity:threat-model-stride` | Conduct a STRIDE threat model with AWS Threat Composer JSON output and map threats to preventive SCP, IAM, WAF, and KMS controls. |
| `/aws-security-identity:triage-guardduty-incident` | Perform forensic incident triage on GuardDuty findings and CloudTrail events, and produce an immediate containment and credential revocation playbook. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-security-identity_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `iam` | stdio | `uvx awslabs.iam-mcp-server@latest` | `mcp__plugin_aws-security-identity_iam__*` | IAM users, roles, policies, and inline access simulation (read-only). |
| `wa-security` | stdio | `uvx awslabs.well-architected-security-mcp-server@latest` | `mcp__plugin_aws-security-identity_wa-security__*` | Well-Architected Security Pillar assessment, Security Hub, and GuardDuty posture checks. |
| `aws-security-agent` | stdio | `uvx awslabs.security-agent-mcp-server@latest` | `mcp__plugin_aws-security-identity_aws-security-agent__*` | AWS Security Agent application security posture, SAST/DAST findings, and pentest remediation. |
| `cloudtrail` | stdio | `uvx awslabs.cloudtrail-mcp-server@latest` | `mcp__plugin_aws-security-identity_cloudtrail__*` | CloudTrail management and data event lookup for incident forensics and audit trails. |
| `awsiac` | stdio | `uvx --with fastmcp<4.0.0 awslabs.aws-iac-mcp-server==0.2.14` | `mcp__plugin_aws-security-identity_awsiac__*` | CloudFormation & CDK template validation (`cfn-lint`), policy-as-code (`cfn-guard`), and CDK documentation. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-security-identity_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |
| `tm` | stdio | `uvx --from git+https://github.com/awslabs/threat-modeling-mcp-server.git threat-modeling-mcp-server` | `mcp__plugin_aws-security-identity_tm__*` | AWS Threat Composer STRIDE threat modeling and mitigation validation. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-security-identity_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-security-identity_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
