# AWS Cost Optimization

Cloud FinOps and cost engineering for the main agent: Cost Explorer & Anomaly Detection, CUR 2.0 Athena SQL analytics, Compute Optimizer P95/P99 right-sizing, Savings Plans & Reserved Instance commitment modeling, Shift-Left IaC cost estimation, AWS Budgets/Invoicing governance, and waste elimination.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-cost-optimization@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-finops-engineer`](../../agent-plugins/aws-finops-engineer) or [`aws-platform-engineer`](../../agent-plugins/aws-platform-engineer) or [`aws-startup-advisor`](../../agent-plugins/aws-startup-advisor) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-cost-optimization:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-cost-optimization:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `aws-billing-and-cost-management` | | |
| `aws-finops-and-cost` | Computes pre-deployment AWS infrastructure cost estimates, monthly cost breakdowns, and architecture cost optimizations across Terraform, Terragrunt, CloudFormation, CDK, Pulumi, and Crossplane using… |
| `aws-finops-and-cost-optimization` | Generates pre-deployment AWS unit price and monthly run-rate estimates via the pricing MCP server, audits existing account spend and idle resources via the billing-cost MCP server (Cost Explorer, Cos… |

## Commands

| Command | Description |
|---|---|
| `/aws-cost-optimization:cost-anomaly` | Investigate AWS cost spikes and Cost Anomaly Detection alerts by service, usage type, linked account, and cost allocation tag. |
| `/aws-cost-optimization:cur-athena-query` | Generate partition-pruned Athena SQL queries against AWS Cost and Usage Report (CUR 2.0) tables for unit-economics and chargeback analysis. |
| `/aws-cost-optimization:estimate-architecture` | Produce a detailed monthly AWS cost estimate using live AWS Pricing API rates, data transfer modeling, and Shift-Left IaC inspection. |
| `/aws-cost-optimization:rightsize-commitment` | Validate Compute Optimizer right-sizing with P95/P99 CloudWatch metrics before modeling Savings Plans or Reserved Instance commitments. |
| `/aws-cost-optimization:waste-hunt-audit` | Scan the AWS account for unattached EBS volumes, idle NAT Gateways/ELBs, old snapshots, gp2 volumes, and unoptimized S3 storage classes. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-cost-optimization_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `billing` | stdio | `uvx awslabs.billing-cost-management-mcp-server@latest` | `mcp__plugin_aws-cost-optimization_billing__*` | Cost Explorer, Budgets, Cost Anomaly Detection, Compute Optimizer, and Savings Plans / RI coverage. |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-cost-optimization_awspricing__*` | Real-time AWS service pricing catalog and architecture cost calculation. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-cost-optimization_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |
| `awsiac` | stdio | `uvx --with fastmcp<4.0.0 awslabs.aws-iac-mcp-server==0.2.14` | `mcp__plugin_aws-cost-optimization_awsiac__*` | CloudFormation & CDK template validation (`cfn-lint`), policy-as-code (`cfn-guard`), and CDK documentation. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-cost-optimization_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-cost-optimization_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-cost-optimization_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/finops-sql-and…`
