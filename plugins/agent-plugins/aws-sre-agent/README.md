# AWS SRE Agent

Principal AWS Site Reliability & Production Engineer: live-site incident command, root-cause investigations, and Correction of Errors (COE) postmortems; CloudWatch metrics, alarms, and Logs Insights, Application Signals SLOs, X-Ray/ADOT traces, Amazon Managed Prometheus (PromQL), and CloudTrail change forensics; EKS (pods, Karpenter, Auto Mode, VPC CNI, CoreDNS, IRSA/Pod Identity), ECS/Fargate (stopped tasks, circuit breakers, Express Mode), Lambda/API Gateway/Step Functions, EC2/ASG/ALB, RDS/Aurora/DynamoDB/ElastiCache/SQS, and VPC/TGW/Cloud WAN/Network Firewall diagnostics; Resilience Hub, Fault Injection Service (FIS), and Route 53 ARC (Zonal Shift, Region Switch) engineering; CloudFormation/CDK remediation validation (cfn-lint, cfn-guard); observability/compute FinOps right-sizing; and AWS Support escalation.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-sre-agent@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/aws-sre-agent.toml`](./codex/agents/aws-sre-agent.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, command, hook, and MCP server below is bound to the [`aws-sre-agent`](./agents/aws-sre-agent.md) agent, which the host runtime spawns as a dynamic sub-agent.

- Claude Code: `@agent-aws-sre-agent:aws-sre-agent` or let Claude delegate based on the agent description
- Headless: `claude --agent aws-sre-agent:aws-sre-agent`
- Codex: install the custom agent above, then ask Codex to spawn `aws-sre-agent`. Codex plugins can't bundle agents, so without it the skills and MCP servers attach to the main agent.
- **Read-only on AWS.** `aws-mcp` runs with `--read-only`, and the `aws-mutation-gate` hook denies mutating shell/MCP calls from this agent in Claude Code. Pair it with a read-only AWS profile.

## Skills

| Skill | What it does |
|---|---|
| `arc-region-switch` | Answers questions about Amazon Application Recovery Controller (ARC) Region switch including architecture, plans, execution blocks, workflows, triggers, active/active vs active/passive, cross-account support, recovery t… |
| `aws-billing-and-cost-management` | Principal AWS FinOps and Cloud Financial Management (CFM) skill across the full FinOps Foundation lifecycle (Inform, Optimize, Operate, Shift-Left): analyze AWS costs, run 7-stage forensic cost audits, isolate MoM varia… |
| `aws-cloudformation` | Authors, validates, and troubleshoots AWS CloudFormation templates. |
| `aws-compute` | Provisions, scales, and operates Amazon EC2 virtual-machine workloads: instance-type selection (Graviton/Arm64, burstable T credits, GPU, instance store vs EBS), launch templates, Auto Scaling groups (scaling policies,… |
| `aws-deployment` | Configure end-to-end AWS deployment methodologies, progressive delivery (Blue/Green, Canary, Linear, Rolling, Immutable, Feature Flags), and CI/CD pipelines across AWS CodePipeline V2, CodeBuild (buildspec.yml), CodeDep… |
| `aws-fault-injection-service` | Plans, builds, runs, and analyzes fault injection experiments with AWS Fault Injection Service (AWS FIS) to validate application resilience through chaos engineering. |
| `aws-networking` | Routes AWS networking requests to the correct service skill for implementation. |
| `aws-observability` | Builds, configures, debugs, and optimizes AWS observability - operator-symptom questions and detecting Omni vs classic CloudWatch. |
| `aws-resilience-lifecycle` | Guides the end-to-end AWS resilience lifecycle integrating Resilience Hub v2, Fault Injection Service, and Application Recovery Controller. |
| `aws-serverless` | Builds, deploys, manages, debugs, configures, and optimizes serverless applications on AWS using Lambda, API Gateway, Step Functions, EventBridge, and SAM/CDK. |
| `aws-well-architected-review` | Performs a full AWS Well-Architected Framework review evaluating every framework question across all pillars discovered from the live AWS documentation by analyzing code, IaC, and configurations to produce evidence-back… |
| `database-and-cache-reliability` | Diagnose and remediate production stateful data-plane and queue reliability incidents across Amazon RDS/Aurora (DBLoad wait events, max_connections exhaustion, RDS Proxy pinning, replica lag, failover stalls), Amazon Dy… |
| `ecs-container-operations` | Diagnose and remediate Amazon ECS and AWS Fargate production incidents across stopped tasks (OutOfMemoryError, CannotPullContainerError, ResourceInitializationError), ALB target group health check failures, ECS Deployme… |
| `eks-operations-and-troubleshooting` | Diagnose and remediate Amazon EKS production incidents across Pod lifecycle failures (CrashLoopBackOff, OOMKilled, ImagePullBackOff, Pending/Unschedulable), Karpenter and EKS Auto Mode node provisioning, VPC CNI IP exha… |
| `investigating-incidents-with-aws-devops-agent` | Run a deep root-cause investigation on the AWS DevOps Agent. |
| `live-site-incident-postmortem` | Coordinate Sev-1/Sev-2 AWS live-site incident command and author blameless Correction of Errors (COE) / Postmortem documents with UTC timelines, 5-Whys root-cause analysis, blast-radius quantification, and tracked preve… |
| `prometheus-and-grafana-sre` | Query Amazon Managed Service for Prometheus (AMP) using PromQL, design multi-window multi-burn-rate SLO alerting rules, troubleshoot EKS/ECS container and node telemetry, and build Amazon Managed Grafana (AMG) operation… |
| `querying-aws-cloudwatch` | Runs SQL queries on CloudWatch Logs data exported as Apache Iceberg tables in S3 Tables. |
| `recovery-controller-setup` | Configures AWS Application Recovery Controller (ARC) for operational resilience: routing controls with safety rules for cross-Region failover, and zonal shift / zonal autoshift for AZ-impairment recovery. |
| `resilience-hub-failure-mode-assessment` | Runs and interprets AWS Resilience Hub v2 failure mode assessments. |
| `resilience-hub-getting-started` | Sets up AWS Resilience Hub v2 from scratch: creates resilience policies with SLO targets, registers systems and user journeys, onboards services with input sources, and runs a first failure mode assessment. |
| `resilience-hub-multi-account` | Configures AWS Resilience Hub v2 for multi-account resilience management across an AWS Organization. |
| `resilience-program-design` | Designs a resilience program: how to structure and standardize resilience policies across an organization, team, or portfolio (tiered policy model with availability/RTO/RPO targets and DR approach selection), and how of… |
| `setting-up-cloudtrail-multi-region` | Enables a multi-region AWS CloudTrail trail with S3 log storage, CloudWatch Logs integration, and CloudWatch Logs Insights queries for security monitoring and compliance auditing. |
| `setting-up-cloudwatch-alarm-notifications` | Sets up notification channels for CloudWatch alarms using SNS topics and subscriptions. |
| `setting-up-cloudwatch-observability` | Sets up CloudWatch observability for the first time - Omni (CloudWatch Application Observability) and classic CloudWatch. |
| `signing-in-to-aws` | Gets AWS credentials for CLI/SDK access via `aws login`. |
| `troubleshooting-application-failures` | Troubleshoots failing applications by discovering and analyzing CloudWatch log groups to identify error patterns, root causes, and actionable solutions. |
| `vpc-network-path-diagnostics` | Trace and diagnose AWS network connectivity incidents across VPC route tables, Security Groups, NACLs, NAT Gateways, Transit Gateway (TGW), AWS Cloud WAN, AWS Network Firewall, PrivateLink VPC Endpoints, and Route 53 DN… |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). In Claude Code they are bound to the agent through its `tools:` allowlist.

| Server | Transport | Launch | Claude Code tool pattern | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0` `--skip-auth --read-only --metadata` | `mcp__plugin_aws-sre-agent_aws-mcp__*` | Managed AWS MCP Server, read-only: the proxy's --read-only flag drops every tool whose readOnlyHint is not true (aws___call_aws, aws___run_script, aws___get_presigned_url), leaving documentation, regional availability, and skill retrieval. |
| `aws-api` | stdio | `uvx awslabs.aws-api-mcp-server@latest` | `mcp__plugin_aws-sre-agent_aws-api__*` | Read-only AWS API execution engine (call_aws, suggest_aws_commands) for Resilience Hub v2, FIS, ARC, Performance Insights, Route 53, EC2, ALB, RDS, and IAM. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-sre-agent_cloudwatch__*` |  |
| `appsignals` | stdio | `uvx awslabs.cloudwatch-applicationsignals-mcp-server@latest` | `mcp__plugin_aws-sre-agent_appsignals__*` |  |
| `prometheus` | stdio | `uvx awslabs.prometheus-mcp-server@latest` | `mcp__plugin_aws-sre-agent_prometheus__*` |  |
| `cloudtrail` | stdio | `uvx awslabs.cloudtrail-mcp-server@latest` | `mcp__plugin_aws-sre-agent_cloudtrail__*` |  |
| `eks` | stdio | `uvx awslabs.eks-mcp-server@latest` | `mcp__plugin_aws-sre-agent_eks__*` | Read-only by default. Add --allow-write / --allow-sensitive-data-access to enable mutations and pod logs/secrets. |
| `ecs` | stdio | `uvx awslabs-ecs-mcp-server@latest` `--with` | `mcp__plugin_aws-sre-agent_ecs__*` | Read-only by default. Set ALLOW_WRITE / ALLOW_SENSITIVE_DATA to true to enable mutations. fastmcp<4 pin: upstream needs fastmcp>=3.2 and is not yet compatible with fastmcp 4. |
| `network` | stdio | `uvx awslabs.aws-network-mcp-server@latest` | `mcp__plugin_aws-sre-agent_network__*` |  |
| `iac` | stdio | `uvx fastmcp<4.0.0` `--with` | `mcp__plugin_aws-sre-agent_iac__*` | Pinned to 0.2.14 with fastmcp<4.0.0 to prevent FastMCP 4.0 breaking import crashes (awslabs/mcp#4567). |
| `cost-explorer` | stdio | `uvx awslabs.billing-cost-management-mcp-server@latest` | `mcp__plugin_aws-sre-agent_cost-explorer__*` |  |
| `awssupport` | stdio | `uvx awslabs.aws-support-mcp-server@latest` | `mcp__plugin_aws-sre-agent_awssupport__*` |  |

AWS credentials are inherited from the host environment (`AWS_PROFILE`, SSO, or instance role). In Claude Code `AWS_REGION` defaults to `us-east-1` when unset; the portable `mcp.json` can't express that default, so set `AWS_REGION` in your environment on other hosts. Codex starts MCP servers with a minimal environment: if a server can't see your profile, set `AWS_PROFILE`/`AWS_REGION` for it in `~/.codex/config.toml`.

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-sre-agent_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-sre-agent_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`

## Upstream

Derived from the following open-source sources (see the repository `NOTICE`):

- [`aws-core`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`aws-agents-for-devsecops`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`specialized-skills/operations-skills`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`specialized-skills/resilience-skills`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`specialized-skills/system-table-skills`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
