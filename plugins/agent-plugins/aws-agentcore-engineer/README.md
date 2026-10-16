# AWS AgentCore Engineer

Principal AWS AgentCore and AIOps engineer: architects, scaffolds, deploys, secures, and operates AI agents on Amazon Bedrock AgentCore across Harness/Runtime, Hybrid LangGraph+Strands orchestration, Gateway and MCP 2026-07-28 tools, Two-Step OBO and Request/Response Interceptors, STM/LTM memory with KMS CMKs, Cedar policy engines, Two-Tier CI/CD evaluations, and Day-2 CloudWatch/X-Ray/Application Signals/CloudTrail AIOps.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-agentcore-engineer@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/aws-agentcore-engineer.toml`](./codex/agents/aws-agentcore-engineer.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, command, hook, and MCP server below is bound to the [`aws-agentcore-engineer`](./agents/aws-agentcore-engineer.md) agent, which the host runtime spawns as a dynamic sub-agent.

- Claude Code: `@agent-aws-agentcore-engineer:aws-agentcore-engineer` or let Claude delegate based on the agent description
- Headless: `claude --agent aws-agentcore-engineer:aws-agentcore-engineer`
- Codex: install the custom agent above, then ask Codex to spawn `aws-agentcore-engineer`. Codex plugins can't bundle agents, so without it the skills and MCP servers attach to the main agent.

## Skills

| Skill | What it does |
|---|---|
| `agents-build` | Use to extend an existing agent project with memory, app integration, VPC, multi-agent, migration, model, browser, code interpreter, payments, or resource removal. |
| `agents-connect` | Use when connecting your agent to external APIs, tools, or services via Gateway, or restricting tool access with Cedar policies. |
| `agents-debug` | Use when your agent or environment is broken — wrong answers, errors, timeouts, tool failures, or CLI issues. |
| `agents-deploy` | Use when deploying your agent to AWS, or when a deploy has failed. |
| `agents-get-started` | Use when a developer wants to create a new agent project or get started with AgentCore. |
| `agents-harden` | Use when preparing your agent for production — IAM scoping, inbound auth (JWT, SigV4), secrets management, cold start optimization, session lifecycle, rate limiting, input validation, and quota guidance. |
| `agents-optimize` | Use when measuring or improving agent quality and performance — set up evaluators, online monitoring, CI/CD quality gates, observability, or cost optimization. |
| `agents-pay` | Use when THIS agent needs to pay for x402-protected content at runtime: hitting a paywall mid-task, settling it via AgentCore Payments, and applying operator-defined spend limits. |
| `signing-in-to-aws` | Gets AWS credentials for CLI/SDK access via `aws login`. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). In Claude Code they are bound to the agent through its `tools:` allowlist.

| Server | Transport | Launch | Claude Code tool pattern | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0` `--skip-auth --metadata` | `mcp__plugin_aws-agentcore-engineer_aws-mcp__*` | Managed AWS MCP Server via the toolkit's pinned proxy (aws___call_aws, aws___search_documentation, aws___retrieve_skill, ...). |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-agentcore-engineer_awsknowledge__*` |  |
| `agentcore` | stdio | `uvx awslabs.amazon-bedrock-agentcore-mcp-server@latest` | `mcp__plugin_aws-agentcore-engineer_agentcore__*` | Amazon Bedrock AgentCore control/data plane and docs (89 active tools; Browser and Code Interpreter sandbox tools disabled by default via AGENTCORE_DISABLE_TOOLS to cut 28% context bloat). |
| `strands-agents` | stdio | `uvx strands-agents-mcp-server@latest` | `mcp__plugin_aws-agentcore-engineer_strands-agents__*` | Strands Agents SDK documentation, @tool decorator specs, multi-agent handoff/swarm patterns, and bidirectional streaming reference. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-agentcore-engineer_cloudwatch__*` |  |
| `appsignals` | stdio | `uvx awslabs.cloudwatch-applicationsignals-mcp-server@latest` | `mcp__plugin_aws-agentcore-engineer_appsignals__*` |  |
| `cloudtrail` | stdio | `uvx awslabs.cloudtrail-mcp-server@latest` | `mcp__plugin_aws-agentcore-engineer_cloudtrail__*` |  |

AWS credentials are inherited from the host environment (`AWS_PROFILE`, SSO, or instance role). In Claude Code `AWS_REGION` defaults to `us-east-1` when unset; the portable `mcp.json` can't express that default, so set `AWS_REGION` in your environment on other hosts. Codex starts MCP servers with a minimal environment: if a server can't see your profile, set `AWS_PROFILE`/`AWS_REGION` for it in `~/.codex/config.toml`.

## Hooks

- **PreToolUse** `Bash` — command: `sh -c 'python3 "$0" 2>/dev/null \|\| python "$0" 2>/dev/null \|\| py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `use_aws|mcp__aws.*|mcp__plugin_.*aws-.*mcp.*|mcp__plugin_.*awslocation.*|mcp__.*agentcore.*` — command: `sh -c 'python3 "$0" 2>/dev/null \|\| python "$0" 2>/dev/null \|\| py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `Bash` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`
- **PreToolUse** `use_aws|mcp__aws.*|mcp__plugin_.*aws-.*mcp.*|mcp__plugin_.*awslocation.*|mcp__.*agentcore.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`

## Upstream

Derived from the following open-source sources (see the repository `NOTICE`):

- [`aws-agents`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`aws-core`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
