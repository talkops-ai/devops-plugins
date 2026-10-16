# AWS IaC Engineer

Principal AWS Infrastructure-as-Code Engineer: architects, authors, validates, estimates cost, deploys, and troubleshoots AWS infrastructure across CDK, CloudFormation, Terraform/OpenTofu (aws + awscc), Pulumi, and Crossplane (Upbound provider-family-aws), with CodePipeline/GitHub Actions/GitLab CI/Atlantis/ArgoCD GitOps delivery and brownfield resource imports.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-iac-engineer@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/aws-iac-engineer.toml`](./codex/agents/aws-iac-engineer.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, command, hook, and MCP server below is bound to the [`aws-iac-engineer`](./agents/aws-iac-engineer.md) agent, which the host runtime spawns as a dynamic sub-agent.

- Claude Code: `@agent-aws-iac-engineer:aws-iac-engineer` or let Claude delegate based on the agent description
- Headless: `claude --agent aws-iac-engineer:aws-iac-engineer`
- Codex: install the custom agent above, then ask Codex to spawn `aws-iac-engineer`. Codex plugins can't bundle agents, so without it the skills and MCP servers attach to the main agent.

## Skills

| Skill | What it does |
|---|---|
| `aws-brownfield-migration` | Discovers unmanaged live AWS resources via Cloud Control API (aws-mcp) and CloudFormation IaC Generator, and executes zero-downtime brownfield imports and cross-engine migrations into Terraform/OpenTofu, AWS CDK, CloudF… |
| `aws-cdk` | Authors, deploys, and troubleshoots AWS infrastructure using CDK with TypeScript or Python. |
| `aws-cloudformation` | Authors, validates, and troubleshoots AWS CloudFormation templates. |
| `aws-crossplane` | Designs, authors, renders, and validates production-grade Crossplane v1.20 / v2 control-plane configurations targeting AWS with the Upbound provider-family-aws ecosystem, IRSA/Pod Identity DeploymentRuntimeConfig, XRDs,… |
| `aws-deployment` | Configures CI/CD and GitOps pipelines for AWS infrastructure and workloads using AWS CodePipeline V2, CodeBuild, CodeDeploy, CodeConnections, and CodeArtifact, as well as GitHub Actions and GitLab CI with AWS OIDC feder… |
| `aws-finops-and-cost` | Computes pre-deployment AWS infrastructure cost estimates, monthly cost breakdowns, and architecture cost optimizations across Terraform, Terragrunt, CloudFormation, CDK, Pulumi, and Crossplane using Infracost, AWS Pric… |
| `aws-iam-and-security` | Authors least-privilege AWS IAM policies, Permission Boundaries, KMS CMK key policies, Secrets Manager dynamic references, and CI/CD OIDC trust relationships across CDK, CloudFormation, Terraform, Pulumi, and Crossplane… |
| `aws-networking-and-compute` | Provides production AWS infrastructure-as-code blueprints for multi-AZ VPCs, VPC Endpoints/PrivateLink, Transit Gateways, EKS/ECS Fargate container platforms, Lambda/EventBridge serverless architectures, and S3/RDS/Dyna… |
| `aws-pulumi` | Authors, previews, validates, and troubleshoots AWS infrastructure in TypeScript, Python, or Go using Pulumi ComponentResource abstractions, dual pulumi-aws + pulumi-aws-native providers, Pulumi ESC OIDC credential brok… |
| `aws-terraform` | Authors, refactors, tests, imports, and validates production AWS Terraform and OpenTofu configurations using the dual hashicorp/aws + hashicorp/awscc provider strategy, S3/HCP state locking, .tftest.hcl test suites, .tf… |
| `iac-architecture-advisor` | Day-0 multi-engine AWS IaC architecture advisor and rapid-prototyping router. |
| `signing-in-to-aws` | Gets AWS credentials for CLI/SDK access via `aws login`. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). In Claude Code they are bound to the agent through its `tools:` allowlist.

| Server | Transport | Launch | Claude Code tool pattern | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0` `--skip-auth --metadata` | `mcp__plugin_aws-iac-engineer_aws-mcp__*` |  |
| `awsiac` | stdio | `uvx fastmcp<4.0.0` `--with` | `mcp__plugin_aws-iac-engineer_awsiac__*` | Pinned to 0.2.14 with fastmcp<4.0.0 to prevent FastMCP 4.0 breaking import crashes (awslabs/mcp#4567). |
| `terraform` | stdio | `docker run hashicorp/terraform-mcp-server:1` | `mcp__plugin_aws-iac-engineer_terraform__*` | Official HashiCorp Terraform MCP Server (Registry docs, modules, policies, and read-only HCP Terraform workspace inspection). |
| `pulumi` | http | `https://mcp.ai.pulumi.com/mcp` | `mcp__plugin_aws-iac-engineer_pulumi__*` | Official Pulumi Cloud remote MCP Server. |

AWS credentials are inherited from the host environment (`AWS_PROFILE`, SSO, or instance role). In Claude Code `AWS_REGION` defaults to `us-east-1` when unset; the portable `mcp.json` can't express that default, so set `AWS_REGION` in your environment on other hosts. Codex starts MCP servers with a minimal environment: if a server can't see your profile, set `AWS_PROFILE`/`AWS_REGION` for it in `~/.codex/config.toml`.

## Hooks

- **PreToolUse** `Bash` — command: `sh -c 'python3 "$0" 2>/dev/null \|\| python "$0" 2>/dev/null \|\| py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `use_aws|mcp__aws.*|mcp__plugin_.*aws-.*mcp.*|mcp__plugin_.*awslocation.*|mcp__.*agentcore.*` — command: `sh -c 'python3 "$0" 2>/dev/null \|\| python "$0" 2>/dev/null \|\| py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `Bash` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`
- **PreToolUse** `use_aws|mcp__aws.*|mcp__plugin_.*aws-.*mcp.*|mcp__plugin_.*awslocation.*|mcp__.*agentcore.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`

## Upstream

Derived from the following open-source sources (see the repository `NOTICE`):

- [`aws-core`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`terraform`](https://github.com/hashicorp/agent-skills) (hashicorp/agent-skills, MPL-2.0)
