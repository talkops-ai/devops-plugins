# AWS Messaging and Streaming

Event-driven messaging, streaming, and customer communications for the main agent: SQS, SNS, EventBridge (Event Buses, Pipes, Scheduler), Amazon MSK (Kafka), Kinesis Data Streams, Managed Service for Apache Flink, Amazon MQ, and End-User Messaging (SES, SMS, WhatsApp, Push).

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-messaging-and-streaming@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-serverless-engineer`](../../agent-plugins/aws-serverless-engineer) or [`aws-data-engineer`](../../agent-plugins/aws-data-engineer) or [`aws-platform-engineer`](../../agent-plugins/aws-platform-engineer) or [`aws-solutions-architect`](../../agent-plugins/aws-solutions-architect) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-messaging-and-streaming:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-messaging-and-streaming:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `amazon-eventbridge-event-bus` | Builds, runs, debugs, and operates event-driven applications using EventBridge Event Bus - a managed, centrally governed publish/subscribe event bus that an organization can share across many teams a… |
| `amazon-eventbridge-scheduler-and-pipes` | Architect and implement time-based serverless jobs using Amazon EventBridge Scheduler (one-time at() timers, timezone-aware cron(), flexible time windows, universal targets, auto-delete) and point-to… |
| `amazon-ses` | Guides Amazon SES onboarding for domain-based email sending. |
| `amazon-sqs-sns-async-messaging` | Design, provision, and operate resilient asynchronous messaging pipelines with Amazon SQS and Amazon SNS using aws-sns-sqs-mcp and AWS SAM/CDK. |
| `aws-messaging-and-streaming` | >- |
| `aws-sms-voice` | > |
| `aws-social-messaging` | Manages WhatsApp messaging through AWS End User Messaging Social. |
| `developing-applications-on-managed-service-for-apache-flink` | >- |
| `ingesting-streaming-and-cdc-data` | >- |
| `managing-amazon-kinesis-data-streams` | >- |
| `managing-amazon-msk` | > |
| `migrate-to-msk` | >- |

## Commands

| Command | Description |
|---|---|
| `/aws-messaging-and-streaming:choose-messaging` | Select and architect the right AWS messaging/streaming service (SQS, SNS, EventBridge, MSK, Kinesis, Flink, MQ, SES/Pinpoint). |
| `/aws-messaging-and-streaming:eventbridge-routing` | Design or debug EventBridge event patterns, EventBridge Pipes source-to-target enrichment, and EventBridge Scheduler cron jobs. |
| `/aws-messaging-and-streaming:kinesis-stream-ops` | Inspect and optimize Amazon Kinesis Data Streams shard capacity, iterator age lag, enhanced fan-out, and Managed Flink checkpoints. |
| `/aws-messaging-and-streaming:msk-troubleshoot` | Diagnose Amazon MSK broker CPU/disk saturation, under-replicated partitions, consumer group lag, and IAM/mTLS connectivity. |
| `/aws-messaging-and-streaming:queue-health` | Audit Amazon SQS queues and SNS subscriptions for DLQ accumulation, visibility timeout mismatches, redrive policies, and FIFO throughput. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-messaging-and-streaming_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `sns-sqs` | stdio | `uvx awslabs.amazon-sns-sqs-mcp-server@latest` | `mcp__plugin_aws-messaging-and-streaming_sns-sqs__*` | Amazon SNS topics and SQS queues inspection (read-only). |
| `msk` | stdio | `uvx awslabs.aws-msk-mcp-server@latest` | `mcp__plugin_aws-messaging-and-streaming_msk__*` | Amazon MSK cluster, broker, configuration, and topic telemetry (read-only). |
| `mq` | stdio | `uvx awslabs.amazon-mq-mcp-server@latest` | `mcp__plugin_aws-messaging-and-streaming_mq__*` | Amazon MQ (ActiveMQ / RabbitMQ) broker configuration and telemetry inspection. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-messaging-and-streaming_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-messaging-and-streaming_awspricing__*` | Real-time AWS service pricing catalog and architecture cost calculation. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-messaging-and-streaming_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-messaging-and-streaming_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
