# AWS Amplify Engineer

Principal Full-Stack AWS Amplify Gen 2 Engineer: Cognito auth (OAuth/OIDC/SAML/Passkeys/triggers), AppSync/DynamoDB data models (relationships, GSIs, 6 auth modes, custom JS/RDS resolvers), S3 storage (path compiler rules, multi-bucket), Lambda & CDK escape hatches (resourceGroupName, AWS Blocks), Amplify AI Kit on Bedrock (a.conversation, a.generation, RAG), sandboxes, and Amplify Hosting CI/CD.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-amplify-engineer@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/aws-amplify-engineer.toml`](./codex/agents/aws-amplify-engineer.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, command, hook, and MCP server below is bound to the [`aws-amplify-engineer`](./agents/aws-amplify-engineer.md) agent, which the host runtime spawns as a dynamic sub-agent.

- Claude Code: `@agent-aws-amplify-engineer:aws-amplify-engineer` or let Claude delegate based on the agent description
- Headless: `claude --agent aws-amplify-engineer:aws-amplify-engineer`
- Codex: install the custom agent above, then ask Codex to spawn `aws-amplify-engineer`. Codex plugins can't bundle agents, so without it the skills and MCP servers attach to the main agent.

## Skills

| Skill | What it does |
|---|---|
| `amplify-ai-kit` | Architects and implements AWS Amplify AI Kit features in Amplify Gen 2 (TypeScript code-first) backed by Amazon Bedrock, AWS AppSync, Amazon DynamoDB, and AWS Lambda. |
| `amplify-auth-cognito` | Architects and implements Amazon Cognito authentication in AWS Amplify Gen 2 (amplify/auth/resource.ts via defineAuth and referenceAuth). |
| `amplify-data-appsync` | Models, secures, and integrates AWS AppSync GraphQL and Amazon DynamoDB data layers in Amplify Gen 2 (amplify/data/resource.ts via defineData and a.schema). |
| `amplify-functions-cdk` | Builds AWS Lambda functions (defineFunction), resolves CloudFormation nested-stack circular dependencies (resourceGroupName), configures typed environment variables ($amplify/env/*) and SSM secrets (secret()), calls Amp… |
| `amplify-hosting-cicd` | Orchestrates AWS Amplify Gen 2 cloud sandboxes (npx ampx sandbox --once), full-stack branch deployments on AWS Amplify Hosting (amplify.yml and npx ampx pipeline-deploy), monorepo and multi-repo build pipelines (appRoot… |
| `amplify-storage-s3` | Architects and implements Amazon S3 file storage in AWS Amplify Gen 2 (amplify/storage/resource.ts via defineStorage). |
| `amplify-workflow` | Master 4-phase orchestrator (Backend -> Sandbox -> Frontend -> Production) to build and deploy full-stack web and mobile apps with AWS Amplify Gen 2 (TypeScript code-first). |
| `aws-blocks` | Guides building full-stack applications with AWS Blocks — an Infrastructure-from-Code framework. |
| `signing-in-to-aws` | Gets AWS credentials for CLI/SDK access via `aws login`. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). In Claude Code they are bound to the agent through its `tools:` allowlist.

| Server | Transport | Launch | Claude Code tool pattern | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws@latest` | `mcp__plugin_aws-amplify-engineer_aws-mcp__*` | Managed AWS MCP Server via the proxy used by awslabs/agent-plugins. |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-amplify-engineer_awsknowledge__*` |  |
| `appsync` | stdio | `uvx awslabs.aws-appsync-mcp-server@latest` | `mcp__plugin_aws-amplify-engineer_appsync__*` | AWS AppSync APIs, read-only by default. Add --allow-write to create APIs, data sources, and resolvers. |
| `awsiac` | stdio | `uvx fastmcp<4.0.0` `--with` | `mcp__plugin_aws-amplify-engineer_awsiac__*` | Pinned to 0.2.14 with fastmcp<4.0.0 to prevent FastMCP 4.0 breaking import crashes (awslabs/mcp#4567). |
| `dynamodb` | stdio | `uvx awslabs.dynamodb-mcp-server>=2.1.6` | `mcp__plugin_aws-amplify-engineer_dynamodb__*` | Pinned >=2.1.6 to remediate CVE-2026-85654 command injection in CDK resource generation. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-amplify-engineer_cloudwatch__*` |  |

AWS credentials are inherited from the host environment (`AWS_PROFILE`, SSO, or instance role). In Claude Code `AWS_REGION` defaults to `us-east-1` when unset; the portable `mcp.json` can't express that default, so set `AWS_REGION` in your environment on other hosts. Codex starts MCP servers with a minimal environment: if a server can't see your profile, set `AWS_PROFILE`/`AWS_REGION` for it in `~/.codex/config.toml`.

## Hooks

- **PreToolUse** `Bash` — command: `sh -c 'python3 "$0" 2>/dev/null \|\| python "$0" 2>/dev/null \|\| py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `use_aws|mcp__aws.*|mcp__plugin_.*aws-.*mcp.*|mcp__plugin_.*awslocation.*|mcp__.*agentcore.*` — command: `sh -c 'python3 "$0" 2>/dev/null \|\| python "$0" 2>/dev/null \|\| py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `Bash` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`
- **PreToolUse** `use_aws|mcp__aws.*|mcp__plugin_.*aws-.*mcp.*|mcp__plugin_.*awslocation.*|mcp__.*agentcore.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`

## Upstream

Derived from the following open-source sources (see the repository `NOTICE`):

- [`aws-amplify`](https://github.com/awslabs/agent-plugins) (awslabs/agent-plugins, Apache-2.0)
- [`aws-core`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
