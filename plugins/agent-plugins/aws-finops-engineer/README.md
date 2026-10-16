# AWS FinOps Engineer

Principal AWS FinOps and Cloud Financial Management (CFM) Engineer: 7-stage forensic cost audits, Cost Explorer & Cost Comparison MoM root-cause analysis, Cost Anomaly & CloudTrail correlation, CUR 2.0 and FOCUS 1.0/1.2+ Athena SQL analytics, Two-Key CloudWatch P95/P99 right-sizing validation (EC2, ASG, EBS, RDS/Aurora, Lambda, ECS/EKS), Compute Optimizer Automation rules, NAT Gateway/Cross-AZ/CloudFront data-transfer optimization, S3 Storage Lens & EBS gp3/io2 storage tuning, Savings Plans & RI commitment portfolio engineering (Effective Savings Rate, Purchase Analyzer simulations), GenAI/Bedrock/Containers/Database unit economics, Shift-Left IaC cost estimation (Infracost, CDK/Terraform pricing, BCM Pricing Calculator, cfn-lint/cfn-guard validation), and multi-account billing governance (Billing Views, Billing Conductor, Cost Categories, Budgets, Invoice Units, Credits, Enterprise Support, Free Tier).

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-finops-engineer@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/aws-finops-engineer.toml`](./codex/agents/aws-finops-engineer.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, command, hook, and MCP server below is bound to the [`aws-finops-engineer`](./agents/aws-finops-engineer.md) agent, which the host runtime spawns as a dynamic sub-agent.

- Claude Code: `@agent-aws-finops-engineer:aws-finops-engineer` or let Claude delegate based on the agent description
- Headless: `claude --agent aws-finops-engineer:aws-finops-engineer`
- Codex: install the custom agent above, then ask Codex to spawn `aws-finops-engineer`. Codex plugins can't bundle agents, so without it the skills and MCP servers attach to the main agent.
- **Read-only on AWS.** The `aws-mutation-gate` hook (and `finops-sql-and-cost-gate` where bundled) denies mutating shell/MCP calls from this agent while keeping read-only `aws___call_aws` inspection available. Pair it with a read-only AWS profile (see `examples/`).

## Skills

| Skill | What it does |
|---|---|
| `aws-billing-and-cost-management` | Principal AWS FinOps and Cloud Financial Management (CFM) skill across the full FinOps Foundation lifecycle (Inform, Optimize, Operate, Shift-Left): analyze AWS costs, run 7-stage forensic cost audits, isolate MoM varia… |
| `signing-in-to-aws` | Gets AWS credentials for CLI/SDK access via `aws login`. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). In Claude Code they are bound to the agent through its `tools:` allowlist.

| Server | Transport | Launch | Claude Code tool pattern | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0` `--skip-auth --metadata` | `mcp__plugin_aws-finops-engineer_aws-mcp__*` | Managed AWS MCP Server via the toolkit's pinned proxy (aws___call_aws, aws___search_documentation, aws___retrieve_skill, ...). |
| `billing` | stdio | `uvx awslabs.billing-cost-management-mcp-server@latest` | `mcp__plugin_aws-finops-engineer_billing__*` |  |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-finops-engineer_awspricing__*` |  |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-finops-engineer_cloudwatch__*` |  |
| `awsiac` | stdio | `uvx fastmcp<4.0.0` `--with` | `mcp__plugin_aws-finops-engineer_awsiac__*` | Pinned to 0.2.14 with fastmcp<4.0.0 to prevent FastMCP 4.0 breaking import crashes (awslabs/mcp#4567). |

AWS credentials are inherited from the host environment (`AWS_PROFILE`, SSO, or instance role). In Claude Code `AWS_REGION` defaults to `us-east-1` when unset; the portable `mcp.json` can't express that default, so set `AWS_REGION` in your environment on other hosts. Codex starts MCP servers with a minimal environment: if a server can't see your profile, set `AWS_PROFILE`/`AWS_REGION` for it in `~/.codex/config.toml`.

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-finops-engineer_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-finops-engineer_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-finops-engineer_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/finops-sql-and-cost-gate.py"`

## Upstream

Derived from the following open-source sources (see the repository `NOTICE`):

- [`aws-core`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
