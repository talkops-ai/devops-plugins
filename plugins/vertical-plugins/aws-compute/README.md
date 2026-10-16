# AWS Compute

EC2 and PaaS compute skills for the main agent: instance family selection (Graviton4, compute/memory/GPU), Auto Scaling Groups, EC2 Image Builder golden AMIs, Elastic Beanstalk, instance profiles, and CloudWatch/Compute Optimizer right-sizing.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-compute@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-platform-engineer`](../../agent-plugins/aws-platform-engineer) or [`aws-deployment-engineer`](../../agent-plugins/aws-deployment-engineer) or [`aws-sre-agent`](../../agent-plugins/aws-sre-agent) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-compute:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-compute:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `amazon-ec2-image-builder` | Creates and automates custom image builds with EC2 Image Builder - Linux, Windows, and macOS AMIs, and container images to ECR. |
| `aws-compute` | Provisions, scales, and operates Amazon EC2 virtual-machine workloads: instance-type selection (Graviton/Arm64, burstable T credits, GPU, instance store vs EBS), launch templates, Auto Scaling groups… |
| `elastic-beanstalk` | > |
| `launching-ec2-instance-with-best-practices` | Launches an EC2 instance with secure, cost-efficient defaults including AMI selection, burstable instance sizing, least-privilege IAM roles, hardened security groups, encrypted EBS volumes, and compr… |
| `platform-golden-path-scaffolder` | Translates high-level application developer or QA engineer requests (e.g., "deploy my web app", "spin up a staging environment", "set up a worker queue", "create an internal microservice") into produ… |
| `setting-up-ec2-instance-profiles` | Configures EC2 instances to securely call AWS services by creating and attaching IAM roles via instance profiles, eliminating hardcoded credentials. |

## Commands

| Command | Description |
|---|---|
| `/aws-compute:beanstalk-ops` | Deploy, upgrade platform branches, or troubleshoot an AWS Elastic Beanstalk environment with immutable/rolling updates. |
| `/aws-compute:configure-asg` | Design or tune an EC2 Auto Scaling Group with mixed instances, Predictive/Target Tracking scaling, and warm pools. |
| `/aws-compute:golden-ami-pipeline` | Design an automated EC2 Image Builder pipeline with CIS hardening, Inspector CVE scanning, and cross-account AMI distribution. |
| `/aws-compute:launch-instance` | Design and launch a right-sized, IMDSv2-hardened EC2 instance or Spot/On-Demand configuration. |
| `/aws-compute:rightsize-fleet` | Analyze EC2 utilization with CloudWatch P95/P99 metrics and AWS Pricing to recommend Graviton4 and instance right-sizing. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-compute_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-compute_awsknowledge__*` | Official AWS documentation, Architecture Center, and Well-Architected knowledge base. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-compute_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-compute_awspricing__*` | Real-time AWS service pricing catalog and architecture cost calculation. |
| `awsiac` | stdio | `uvx --with fastmcp<4.0.0 awslabs.aws-iac-mcp-server==0.2.14` | `mcp__plugin_aws-compute_awsiac__*` | CloudFormation & CDK template validation (`cfn-lint`), policy-as-code (`cfn-guard`), and CDK documentation. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-compute_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-compute_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
