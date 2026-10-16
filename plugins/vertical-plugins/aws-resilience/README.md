# AWS Resilience

Resilience engineering, disaster recovery, and chaos testing for the main agent: AWS Resilience Hub assessments, AWS Fault Injection Service (FIS) chaos experiments with CloudWatch stop conditions, Route 53 Application Recovery Controller (ARC) zonal shift/region switch, and multi-region RTO/RPO DR architecture.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-resilience@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-sre-agent`](../../agent-plugins/aws-sre-agent) or [`aws-solutions-architect`](../../agent-plugins/aws-solutions-architect) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-resilience:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-resilience:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `arc-region-switch` | Answers questions about Amazon Application Recovery Controller (ARC) Region switch including architecture, plans, execution blocks, workflows, triggers, active/active vs active/passive, cross-account… |
| `aws-fault-injection-service` | > |
| `aws-resilience-dr-and-migration-architecture` | Architects RTO/RPO-driven Multi-Region Disaster Recovery topologies (Backup & Restore, Pilot Light, Warm Standby, Active-Active), Cell-Based Architectures & Shuffle Sharding, Route 53 ARC (Zonal Auto… |
| `aws-resilience-lifecycle` | > |
| `database-and-cache-reliability` | Diagnose and remediate production stateful data-plane and queue reliability incidents across Amazon RDS/Aurora (DBLoad wait events, max_connections exhaustion, RDS Proxy pinning, replica lag, failove… |
| `recovery-controller-setup` | > |
| `resilience-hub-failure-mode-assessment` | > |
| `resilience-hub-getting-started` | > |
| `resilience-hub-multi-account` | > |
| `resilience-program-design` | > |
| `troubleshooting-application-failures` | Troubleshoots failing applications by discovering and analyzing CloudWatch log groups to identify error patterns, root causes, and actionable solutions. |

## Commands

| Command | Description |
|---|---|
| `/aws-resilience:assess-resilience` | Run an AWS Resilience Hub assessment against target RTO/RPO objectives and uncover single points of failure across compute, data, and networking. |
| `/aws-resilience:chaos-experiment` | Design a safe AWS Fault Injection Service (FIS) chaos experiment with mandatory CloudWatch stop-condition alarms and blast-radius controls. |
| `/aws-resilience:dr-strategy-matrix` | Design a multi-region Disaster Recovery architecture comparing Backup & Restore, Pilot Light, Warm Standby, and Active/Active with cost and failover runbooks. |
| `/aws-resilience:game-day-runbook` | Generate a production GameDay execution runbook combining FIS fault templates, CloudWatch SLI dashboards, and ARC recovery validation. |
| `/aws-resilience:zonal-shift` | Evaluate readiness for or execute an Amazon Route 53 Application Recovery Controller (ARC) zonal shift or region switch. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-resilience_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-resilience_awsknowledge__*` | Official AWS documentation, Architecture Center, and Well-Architected knowledge base. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-resilience_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |
| `appsignals` | stdio | `uvx awslabs.cloudwatch-applicationsignals-mcp-server@latest` | `mcp__plugin_aws-resilience_appsignals__*` | CloudWatch Application Signals service-level objectives (SLOs), traces, and APM dependency maps. |
| `cloudtrail` | stdio | `uvx awslabs.cloudtrail-mcp-server@latest` | `mcp__plugin_aws-resilience_cloudtrail__*` | CloudTrail management and data event lookup for incident forensics and audit trails. |
| `awssupport` | stdio | `uvx awslabs.aws-support-mcp-server@latest` | `mcp__plugin_aws-resilience_awssupport__*` | AWS Support cases and Trusted Advisor checks. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-resilience_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-resilience_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
