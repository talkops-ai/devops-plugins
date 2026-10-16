# AWS Infrastructure as Code

End-to-end AWS IaC and deployment skills for the main agent: AWS CDK, CloudFormation, Terraform/OpenTofu, Pulumi, Crossplane/ACK, brownfield resource import, preflight discovery, deployment verification/rollback, and vibe-coded app migration.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-infrastructure-as-code@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-iac-engineer`](../../agent-plugins/aws-iac-engineer) or [`aws-deployment-engineer`](../../agent-plugins/aws-deployment-engineer) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-infrastructure-as-code:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-infrastructure-as-code:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `aws-blocks` | Guides building full-stack applications with AWS Blocks — an Infrastructure-from-Code framework. |
| `aws-brownfield-migration` | Discovers unmanaged live AWS resources via Cloud Control API (aws-mcp) and CloudFormation IaC Generator, and executes zero-downtime brownfield imports and cross-engine migrations into Terraform/OpenT… |
| `aws-cdk` | Authors, deploys, and troubleshoots AWS infrastructure using CDK with TypeScript or Python. |
| `aws-cloudformation` | Authors, validates, and troubleshoots AWS CloudFormation templates. |
| `aws-crossplane` | Designs, authors, renders, and validates production-grade Crossplane v1.20 / v2 control-plane configurations targeting AWS with the Upbound provider-family-aws ecosystem, IRSA/Pod Identity Deployment… |
| `aws-deployment` | Configures CI/CD and GitOps pipelines for AWS infrastructure and workloads using AWS CodePipeline V2, CodeBuild, CodeDeploy, CodeConnections, and CodeArtifact, as well as GitHub Actions and GitLab CI… |
| `aws-finops-and-cost` | Computes pre-deployment AWS infrastructure cost estimates, monthly cost breakdowns, and architecture cost optimizations across Terraform, Terragrunt, CloudFormation, CDK, Pulumi, and Crossplane using… |
| `aws-iam-and-security` | Authors least-privilege AWS IAM policies, Permission Boundaries, KMS CMK key policies, Secrets Manager dynamic references, and CI/CD OIDC trust relationships across CDK, CloudFormation, Terraform, Pu… |
| `aws-networking-and-compute` | Provides production AWS infrastructure-as-code blueprints for multi-AZ VPCs, VPC Endpoints/PrivateLink, Transit Gateways, EKS/ECS Fargate container platforms, Lambda/EventBridge serverless architectu… |
| `aws-pulumi` | Authors, previews, validates, and troubleshoots AWS infrastructure in TypeScript, Python, or Go using Pulumi ComponentResource abstractions, dual pulumi-aws + pulumi-aws-native providers, Pulumi ESC… |
| `aws-terraform` | Authors, refactors, tests, imports, and validates production AWS Terraform and OpenTofu configurations using the dual hashicorp/aws + hashicorp/awscc provider strategy, S3/HCP state locking, .tftest.… |
| `deploy` | > |
| `iac-architecture-advisor` | Day-0 multi-engine AWS IaC architecture advisor and rapid-prototyping router. |
| `launch-with-aws` | Migrates vibe-coded web applications to AWS. |
| `preflight-discovery` | > |
| `verify-and-rollback` | > |

## Commands

| Command | Description |
|---|---|
| `/aws-infrastructure-as-code:bootstrap-app` | Analyze and migrate a web or full-stack application to deployable AWS IaC using Launch with AWS and AWS Blocks. |
| `/aws-infrastructure-as-code:brownfield-import` | Import existing console-created AWS resources into CloudFormation, AWS CDK (`cdk migrate`), or Terraform `import` blocks without downtime. |
| `/aws-infrastructure-as-code:compare-iac-tools` | Evaluate AWS CDK vs CloudFormation vs Terraform/OpenTofu vs Pulumi vs Crossplane with an architectural decision matrix. |
| `/aws-infrastructure-as-code:generate-iac` | Author production-ready AWS Infrastructure as Code with least-privilege IAM, encryption, and cost estimate. |
| `/aws-infrastructure-as-code:troubleshoot-deploy` | Diagnose a failed CloudFormation, CDK, or Terraform deployment and produce a safe remediation and rollback plan. |
| `/aws-infrastructure-as-code:validate-stack` | Validate CloudFormation, SAM, CDK, or Terraform code for syntax, schema, and security compliance (`cfn-lint` & `cfn-guard`). |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-infrastructure-as-code_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-infrastructure-as-code_awsknowledge__*` | Official AWS documentation, Architecture Center, and Well-Architected knowledge base. |
| `awsiac` | stdio | `uvx --with fastmcp<4.0.0 awslabs.aws-iac-mcp-server==0.2.14` | `mcp__plugin_aws-infrastructure-as-code_awsiac__*` | CloudFormation & CDK template validation (`cfn-lint`), policy-as-code (`cfn-guard`), and CDK documentation. |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-infrastructure-as-code_awspricing__*` | Real-time AWS service pricing catalog and architecture cost calculation. |
| `pulumi` | http | `https://mcp.ai.pulumi.com/mcp` | `mcp__plugin_aws-infrastructure-as-code_pulumi__*` | Pulumi Cloud AI MCP server for Pulumi IaC components and AWS provider schemas. |

## Optional connectors

Connection-bound MCP servers you add yourself (see [CONNECTORS.md](./CONNECTORS.md)): `terraform`.

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-infrastructure-as-code_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-infrastructure-as-code_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
- **PostToolUse** `Write|Edit|MultiEdit` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/iac-post-write…`
