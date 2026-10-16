# AWS Observability

Full-stack AWS observability and SRE incident triage for the main agent: CloudWatch (Metrics, Logs Insights, Alarms, SLOs, Synthetics Canaries), Application Signals APM, X-Ray, Amazon Managed Prometheus (PromQL burn rates) & Grafana, CloudTrail multi-region auditing, GenAI observability, and COE postmortems.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-observability@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-sre-agent`](../../agent-plugins/aws-sre-agent) or [`aws-platform-engineer`](../../agent-plugins/aws-platform-engineer) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-observability:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-observability:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `aws-observability` | >- |
| `aws-observability-and-incident-triage` | Diagnoses production and staging incidents, 5xx errors, latency spikes, container crashes, network blackholes, and resource exhaustion across AWS services using CloudWatch Metrics, PromQL, Logs Insig… |
| `investigating-incidents-with-aws-devops-agent` | Run a deep root-cause investigation on the AWS DevOps Agent. |
| `live-site-incident-postmortem` | Coordinate Sev-1/Sev-2 AWS live-site incident command and author blameless Correction of Errors (COE) / Postmortem documents with UTC timelines, 5-Whys root-cause analysis, blast-radius quantificatio… |
| `prometheus-and-grafana-sre` | Query Amazon Managed Service for Prometheus (AMP) using PromQL, design multi-window multi-burn-rate SLO alerting rules, troubleshoot EKS/ECS container and node telemetry, and build Amazon Managed Gra… |
| `querying-aws-cloudwatch` | >- |
| `setting-up-cloudtrail-multi-region` | Enables a multi-region AWS CloudTrail trail with S3 log storage, CloudWatch Logs integration, and CloudWatch Logs Insights queries for security monitoring and compliance auditing. |
| `setting-up-cloudwatch-alarm-notifications` | Sets up notification channels for CloudWatch alarms using SNS topics and subscriptions. |
| `setting-up-cloudwatch-observability` | >- |
| `troubleshooting-application-failures` | Troubleshoots failing applications by discovering and analyzing CloudWatch log groups to identify error patterns, root causes, and actionable solutions. |

## Commands

| Command | Description |
|---|---|
| `/aws-observability:create-canary` | Design a CloudWatch Synthetics canary with multi-step assertions, artifact encryption, and composite alarm routing. |
| `/aws-observability:postmortem-coe` | Generate an AWS Correction of Error (COE) postmortem with 5 Whys root-cause analysis, timeline reconstruction, and tracked action items. |
| `/aws-observability:promql-slo-burnrate` | Author Amazon Managed Prometheus (AMP) multi-window, multi-burn-rate SLO alerting rules and Managed Grafana dashboard panels. |
| `/aws-observability:query-logs` | Author and execute targeted CloudWatch Logs Insights queries for error spikes, latency percentiles, and anomaly detection. |
| `/aws-observability:setup-apm` | Instrument workloads for CloudWatch Application Signals, OpenTelemetry (ADOT), and GenAI token/latency telemetry. |
| `/aws-observability:triage-incident` | Execute a structured SRE incident triage across CloudWatch Alarms, Application Signals SLOs, Logs Insights, X-Ray traces, and recent CloudTrail mutations. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-observability_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-observability_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |
| `appsignals` | stdio | `uvx awslabs.cloudwatch-applicationsignals-mcp-server@latest` | `mcp__plugin_aws-observability_appsignals__*` | CloudWatch Application Signals service-level objectives (SLOs), traces, and APM dependency maps. |
| `cloudtrail` | stdio | `uvx awslabs.cloudtrail-mcp-server@latest` | `mcp__plugin_aws-observability_cloudtrail__*` | CloudTrail management and data event lookup for incident forensics and audit trails. |
| `prometheus` | stdio | `uvx awslabs.prometheus-mcp-server@latest` | `mcp__plugin_aws-observability_prometheus__*` | Amazon Managed Service for Prometheus (AMP) PromQL queries and metric labels. |
| `awssupport` | stdio | `uvx awslabs.aws-support-mcp-server@latest` | `mcp__plugin_aws-observability_awssupport__*` | AWS Support cases and Trusted Advisor checks. |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-observability_awsknowledge__*` | Official AWS documentation, Architecture Center, and Well-Architected knowledge base. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-observability_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-observability_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
