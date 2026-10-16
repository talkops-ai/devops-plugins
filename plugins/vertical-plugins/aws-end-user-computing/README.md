# AWS End User Computing

AWS End User Computing (EUC) fleet architecture and operations for the main agent: Amazon WorkSpaces Personal & Pools, Active Directory & IAM Identity Center integration, WSP streaming tuning, AutoStop/AlwaysOn cost optimization, Amazon AppStream 2.0 (Elastic, On-Demand, Always-On fleets & Image Builder), WorkSpaces Secure Browser, EUC CloudWatch triage, and WorkSpaces Agent Access.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-end-user-computing@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-platform-engineer`](../../agent-plugins/aws-platform-engineer) or [`aws-sre-agent`](../../agent-plugins/aws-sre-agent) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-end-user-computing:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-end-user-computing:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `amazon-appstream-and-workspaces-web` | Design, deploy, and operate Amazon AppStream 2.0 (Always-On, On-Demand, and Elastic Fleets, Image Builder, Application Entitlements) and Amazon WorkSpaces Secure Browser (WorkSpaces Web) for zero-tru… |
| `amazon-workspaces-administration` | Provision, administer, and optimize Amazon WorkSpaces Personal and WorkSpaces Pools fleets: directory services (AWS Managed Microsoft AD, AD Connector, IAM Identity Center), custom bundles and image… |
| `amazon-workspaces-agent-access` | Connects AI agents to remote Windows desktop applications on Amazon WorkSpaces Applications (AppStream 2.0) through the managed Agent Access MCP server, and guides reliable desktop automation. |
| `euc-observability-and-troubleshooting` | Diagnose and remediate AWS End User Computing (WorkSpaces, AppStream 2.0, WorkSpaces Secure Browser) issues: in-session latency, unhealthy workspace states, Active Directory join and GPO failures, FS… |

## Commands

| Command | Description |
|---|---|
| `/aws-end-user-computing:optimize-euc-costs` | Analyze 30-day WorkSpaces connection telemetry and AppStream utilization to convert AlwaysOn vs AutoStop modes and right-size bundle tiers. |
| `/aws-end-user-computing:provision-workspaces-fleet` | Architect and provision an Amazon WorkSpaces Personal/Pools, AppStream 2.0, or WorkSpaces Secure Browser fleet with AD/IdC, KMS, and VPC endpoints. |
| `/aws-end-user-computing:setup-agent-access` | Configure and verify the Amazon WorkSpaces / AppStream 2.0 Agent Access MCP bridge for desktop automation. |
| `/aws-end-user-computing:troubleshoot-stream` | Diagnose WorkSpaces unhealthy states, high `InSessionLatency`, AD join failures, or AppStream 2.0 `InsufficientCapacityError` events. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-end-user-computing_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-end-user-computing_awsknowledge__*` | Official AWS documentation, Architecture Center, and Well-Architected knowledge base. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-end-user-computing_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-end-user-computing_awspricing__*` | Real-time AWS service pricing catalog and architecture cost calculation. |
| `awsiac` | stdio | `uvx --with fastmcp<4.0.0 awslabs.aws-iac-mcp-server==0.2.14` | `mcp__plugin_aws-end-user-computing_awsiac__*` | CloudFormation & CDK template validation (`cfn-lint`), policy-as-code (`cfn-guard`), and CDK documentation. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-end-user-computing_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-end-user-computing_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
