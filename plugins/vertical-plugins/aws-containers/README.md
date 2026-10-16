# AWS Containers

Production container operations for the main agent: Amazon EKS (Auto Mode, Karpenter, Pod Identity, VPC CNI, CoreDNS), Amazon ECS (Fargate, Express Mode, circuit breakers, stopped-task triage), ECR build/push, and container runtime security.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-containers@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-platform-engineer`](../../agent-plugins/aws-platform-engineer) or [`aws-sre-agent`](../../agent-plugins/aws-sre-agent) or [`aws-deployment-engineer`](../../agent-plugins/aws-deployment-engineer) or [`aws-cloud-security-engineer`](../../agent-plugins/aws-cloud-security-engineer) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-containers:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-containers:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `aws-containers` | Builds and deploys containerized workloads on Elastic Kubernetes Service (EKS), Elastic Container Service (ECS), Fargate, and ECR (Elastic Container Registry). |
| `container-ecs-deploy` | > |
| `ecs-container-operations` | Diagnose and remediate Amazon ECS and AWS Fargate production incidents across stopped tasks (OutOfMemoryError, CannotPullContainerError, ResourceInitializationError), ALB target group health check fa… |
| `eks-operations-and-troubleshooting` | Diagnose and remediate Amazon EKS production incidents across Pod lifecycle failures (CrashLoopBackOff, OOMKilled, ImagePullBackOff, Pending/Unschedulable), Karpenter and EKS Auto Mode node provision… |
| `security-workload-containers` | >- |

## Commands

| Command | Description |
|---|---|
| `/aws-containers:build-push-image` | Build a multi-stage container image, scan for vulnerabilities, push to Amazon ECR, and deploy to ECS or EKS. |
| `/aws-containers:container-security-audit` | Audit EKS/ECS workloads for Pod Identity/IRSA least privilege, GuardDuty Runtime Monitoring, network policies, and non-root containers. |
| `/aws-containers:ecs-troubleshoot` | Execute the 5-step ECS diagnostic workflow for stopped tasks, ALB health-check failures, capacity providers, and circuit breakers. |
| `/aws-containers:eks-troubleshoot` | Diagnose Amazon EKS control-plane, node, Karpenter, Pod Identity/IRSA, VPC CNI, or CoreDNS issues. |
| `/aws-containers:karpenter-rightsize` | Configure or audit EKS Auto Mode and Karpenter NodePools/EC2NodeClasses for Spot/Graviton consolidation. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-containers_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `eks` | stdio | `uvx awslabs.eks-mcp-server@latest` | `mcp__plugin_aws-containers_eks__*` | Amazon EKS cluster inspection, Kubernetes resources, nodes, and add-on diagnostics. |
| `ecs` | stdio | `uvx --from awslabs-ecs-mcp-server@latest --with fastmcp<4 ecs-mcp-server` | `mcp__plugin_aws-containers_ecs__*` | Amazon ECS cluster, service, task definition, and stopped-task inspection (read-only by default). |
| `finch` | stdio | `uvx awslabs.finch-mcp-server@latest` | `mcp__plugin_aws-containers_finch__*` | Finch local container image build, inspection, and ECR push tooling. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-containers_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-containers_awspricing__*` | Real-time AWS service pricing catalog and architecture cost calculation. |
| `awsiac` | stdio | `uvx --with fastmcp<4.0.0 awslabs.aws-iac-mcp-server==0.2.14` | `mcp__plugin_aws-containers_awsiac__*` | CloudFormation & CDK template validation (`cfn-lint`), policy-as-code (`cfn-guard`), and CDK documentation. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-containers_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-containers_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
