# AWS Deployment Engineer

Principal AWS Deployment & Release Engineer: preflight account/VPC/quota discovery, codebase analysis, target architecture selection (ECS Fargate, ECS Express Mode, Lambda/SAM, Elastic Beanstalk, S3/CloudFront, Amplify Hosting, EC2 ASGs, AWS Batch), progressive delivery strategies (Blue/Green, Canary, Linear, Rolling, Immutable, CloudFront Continuous Deployment, AWS AppConfig feature flags), CI/CD pipelines (CodePipeline V2, CodeBuild, CodeDeploy, GitHub/GitLab OIDC), live FinOps cost estimation, cfn-guard-validated IaC synthesis, validated draw.io AWS4 architecture diagrams, and post-deploy CloudWatch verification and rollback.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-deployment-engineer@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/aws-deployment-engineer.toml`](./codex/agents/aws-deployment-engineer.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, command, hook, and MCP server below is bound to the [`aws-deployment-engineer`](./agents/aws-deployment-engineer.md) agent, which the host runtime spawns as a dynamic sub-agent.

- Claude Code: `@agent-aws-deployment-engineer:aws-deployment-engineer` or let Claude delegate based on the agent description
- Headless: `claude --agent aws-deployment-engineer:aws-deployment-engineer`
- Codex: install the custom agent above, then ask Codex to spawn `aws-deployment-engineer`. Codex plugins can't bundle agents, so without it the skills and MCP servers attach to the main agent.

## Skills

| Skill | What it does |
|---|---|
| `aws-architecture-diagram` | Generate validated AWS architecture diagrams as draw.io XML using official AWS4 icon libraries. |
| `aws-deployment` | Configure end-to-end AWS deployment methodologies, progressive delivery (Blue/Green, Canary, Linear, Rolling, Immutable, Feature Flags), and CI/CD pipelines across AWS CodePipeline V2, CodeBuild (buildspec.yml), CodeDep… |
| `container-ecs-deploy` | Containerize applications and deploy to Amazon ECS Fargate, ECS Express Mode, or Amazon ECR. |
| `deploy` | Orchestrate full-stack AWS application deployments, architecture recommendations, real-time FinOps cost estimation, and multi-IaC synthesis (AWS CDK TypeScript/Python, CloudFormation, and Terraform). |
| `elastic-beanstalk` | Deploy, update, or configure applications on AWS Elastic Beanstalk (Single-Instance or Cluster mode). |
| `preflight-discovery` | Read-only AWS brownfield environment discovery and preflight governance check. |
| `serverless-sam-deploy` | Package, validate, and deploy serverless applications using AWS SAM CLI or AWS CDK. |
| `signing-in-to-aws` | Acquire and validate AWS CLI/SDK credentials via `aws login` or IAM Identity Center (`aws sso login`) and verify active session state via `aws sts get-caller-identity`. |
| `verify-and-rollback` | Day-2 post-deployment readiness verification, CloudWatch alarm and log triage, CloudFormation failure root-cause analysis, and safe stack or service rollback. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). In Claude Code they are bound to the agent through its `tools:` allowlist.

| Server | Transport | Launch | Claude Code tool pattern | Notes |
|---|---|---|---|---|
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-deployment-engineer_awsknowledge__*` |  |
| `awsiac` | stdio | `uvx awslabs.aws-iac-mcp-server==1.0.26` | `mcp__plugin_aws-deployment-engineer_awsiac__*` | Pinned to 0.2.14 with fastmcp<4.0.0 to prevent FastMCP 4.0 breaking import crashes (awslabs/mcp#4567). |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server==1.1.1` | `mcp__plugin_aws-deployment-engineer_awspricing__*` |  |
| `awsapi` | stdio | `uvx awslabs.aws-api-mcp-server==1.5.6` | `mcp__plugin_aws-deployment-engineer_awsapi__*` | AWS API MCP Server for CLI execution plans, preflight discovery, and service operations (call_aws, suggest_aws_commands, get_execution_plan). |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server==0.3.1` | `mcp__plugin_aws-deployment-engineer_cloudwatch__*` |  |

AWS credentials are inherited from the host environment (`AWS_PROFILE`, SSO, or instance role). In Claude Code `AWS_REGION` defaults to `us-east-1` when unset; the portable `mcp.json` can't express that default, so set `AWS_REGION` in your environment on other hosts. Codex starts MCP servers with a minimal environment: if a server can't see your profile, set `AWS_PROFILE`/`AWS_REGION` for it in `~/.codex/config.toml`.

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-deployment-engineer_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-deployment-engineer_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`
- **PostToolUse** `Edit|Write` — command: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/validate-drawio.sh"`
- **PostToolUse** `Edit|Write` — command: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/validate-iac.sh"`

## Upstream

Derived from the following open-source sources (see the repository `NOTICE`):

- [`deploy-on-aws`](https://github.com/awslabs/agent-plugins) (awslabs/agent-plugins, Apache-2.0)
- [`aws-core`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
