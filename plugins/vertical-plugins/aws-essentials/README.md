# AWS Essentials

Foundational AWS skills for the main agent: credential & SSO preflight verification, account baseline security/billing hygiene audits, and SDK best practices for Python (Boto3), JavaScript/TypeScript v3, and Swift.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-essentials@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-solutions-architect`](../../agent-plugins/aws-solutions-architect) or [`aws-startup-advisor`](../../agent-plugins/aws-startup-advisor) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-essentials:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-essentials:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `aws-auth-and-environment-preflight` | Verify AWS credentials, IAM identity, region configuration, and local serverless toolchain readiness (SAM CLI, AWS CDK, Docker daemon, AWS CLI v2). |
| `aws-sdk-js-v3-usage` | | |
| `aws-sdk-python-usage` | | |
| `aws-sdk-swift-usage` | | |
| `signing-in-to-aws` | | |
| `startup-account-audit` | >- |

## Commands

| Command | Description |
|---|---|
| `/aws-essentials:account-baseline-audit` | Audit an AWS account for foundational security, root MFA, CloudTrail, billing alarms, and quota readiness. |
| `/aws-essentials:sdk-snippet` | Generate production-grade AWS SDK code (Boto3, JS SDK v3, or Swift) with retries, pagination, and waiters. |
| `/aws-essentials:setup-auth` | Configure AWS CLI and SDK authentication using IAM Identity Center (SSO) or short-lived role assumption. |
| `/aws-essentials:troubleshoot-auth` | Diagnose AWS authentication, STS AssumeRole, expired SSO token, or IAM AccessDenied errors. |
| `/aws-essentials:whoami` | Verify active AWS caller identity, IAM session context, region, and SSO expiration. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-essentials_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-essentials_awsknowledge__*` | Official AWS documentation, Architecture Center, and Well-Architected knowledge base. |
| `awsapi` | stdio | `uvx awslabs.aws-api-mcp-server@latest` | `mcp__plugin_aws-essentials_awsapi__*` | Structured AWS API inspection with read-only default and mutation consent. |

## Hooks

- **SessionStart** `startup|resume` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/session-aws-pr…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-essentials_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-essentials_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
