# AWS Serverless

Comprehensive serverless engineering skills for the main agent: AWS Lambda (SnapStart, Power Tuning, Durable Functions, Managed Instances), API Gateway, Step Functions, EventBridge (Buses, Scheduler, Pipes), SQS/SNS, Event Source Mappings, DynamoDB single-table modeling, Aurora DSQL, and SAM/CDK deployment.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-serverless@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-serverless-engineer`](../../agent-plugins/aws-serverless-engineer) or [`aws-platform-engineer`](../../agent-plugins/aws-platform-engineer) or [`aws-deployment-engineer`](../../agent-plugins/aws-deployment-engineer) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-serverless:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-serverless:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `amazon-eventbridge-event-bus` | Builds, runs, debugs, and operates event-driven applications using EventBridge Event Bus - a managed, centrally governed publish/subscribe event bus that an organization can share across many teams a… |
| `amazon-eventbridge-scheduler-and-pipes` | Architect and implement time-based serverless jobs using Amazon EventBridge Scheduler (one-time at() timers, timezone-aware cron(), flexible time windows, universal targets, auto-delete) and point-to… |
| `amazon-sqs-sns-async-messaging` | Design, provision, and operate resilient asynchronous messaging pipelines with Amazon SQS and Amazon SNS using aws-sns-sqs-mcp and AWS SAM/CDK. |
| `api-gateway` | > |
| `aws-lambda` | Design, build, deploy, test, and debug serverless applications with AWS Lambda. |
| `aws-lambda-durable-functions` | Builds resilient, long-running, multi-step applications with AWS Lambda durable functions with automatic state persistence, retry logic, and orchestration for long-running executions. |
| `aws-lambda-managed-instances` | Evaluates, configures, and migrates workloads to AWS Lambda Managed Instances (LMI). |
| `aws-lambda-microvms` | Builds, runs, debugs, and operates applications on AWS Lambda MicroVMs — Firecracker-isolated, snapshot-resumable serverless compute environments running inside a container with up to 8 hr lifetimes. |
| `aws-serverless` | Builds, deploys, manages, debugs, configures, and optimizes serverless applications on AWS using Lambda, API Gateway, Step Functions, EventBridge, and SAM/CDK. |
| `aws-serverless-deployment` | AWS SAM and AWS CDK deployment for serverless applications. |
| `aws-step-functions` | Authors and edits AWS Step Functions state machines: writes Amazon States Language (ASL) in JSONata, and chooses and structures state types (Task, Choice, Map, Parallel, Pass, Wait, Succeed, Fail). |
| `connecting-lambda-to-api-gateway` | Connects an existing AWS Lambda function to Amazon API Gateway by creating a REST or HTTP API with resource/method setup, Lambda proxy integration, permissions, and deployment. |
| `connecting-lambda-to-dynamodb` | Connects an AWS Lambda function to DynamoDB with IAM roles, stream event source mapping, and read/write permissions. |
| `creating-api-gateway-stage` | Creates an API Gateway stage with CloudWatch logging, X-Ray tracing, throttling, WAF integration, and IAM roles following AWS best practices. |
| `debugging-lambda-timeouts` | Debugs AWS Lambda function timeout failures by systematically analyzing function configuration, CloudWatch logs and metrics, VPC/networking, cold starts, memory constraints, and downstream dependenci… |
| `deploying-custom-domain-rest-api` | > |
| `dynamodb-access-pattern-modeling` | Design, validate, cost-estimate, and generate code for Amazon DynamoDB data models and relational-to-DynamoDB migrations using aws-dynamodb-mcp (dynamodb_data_modeling, source_db_analyzer, compute_pe… |
| `lambda-event-source-mappings-esm` | Configure, optimize, and troubleshoot AWS Lambda Event Source Mappings (ESMs) across Amazon SQS, Kinesis Data Streams, DynamoDB Streams, Amazon MSK, and self-managed Apache Kafka using aws-serverless… |
| `processing-s3-uploads-with-step-functions` | > |
| `serverless-architecture-and-cost-advisor` | Perform workload analysis, serverless pattern selection, architectural trade-off evaluation, and pre-deployment AWS cost estimation before generating IaC or application code. |
| `serverless-data-and-file-processing` | Architect serverless file upload, event-driven S3 processing, and high-concurrency batch data pipelines. |
| `serverless-observability-and-triage` | Diagnose and resolve production serverless incidents, Lambda timeouts, cold starts, memory-to-CPU right-sizing, API Gateway 502/504/CORS failures, X-Ray traces, CloudWatch Logs Insights queries, and… |
| `serverless-relational-aurora-dsql` | Architect and implement serverless relational SQL databases with Amazon Aurora DSQL and Aurora Serverless v2 (RDS Data API / RDS Proxy). |
| `serverless-security-auth-and-waf` | Design and harden serverless security across Amazon Cognito, API Gateway JWT and Lambda Authorizers, IAM least-privilege execution roles, Secrets Manager Lambda Extension caching, Lambda MicroVM snap… |
| `serverless-vpc-and-private-networking` | Architect, troubleshoot, and cost-optimize VPC networking for AWS Lambda, MicroVMs, API Gateway Private Integrations, and VPC Endpoints. |
| `serverless-webapp-lambda-adapter` | Deploy full-stack, backend, and frontend web applications (Express.js, Next.js, FastAPI, Flask, Django, Spring Boot, React/Vue/Vite) to AWS Lambda, API Gateway, S3, and CloudFront using AWS Lambda We… |

## Commands

| Command | Description |
|---|---|
| `/aws-serverless:api-gateway-design` | Architect an Amazon API Gateway endpoint with Cognito/JWT/Lambda authorizers, WAF, custom domains, and Lambda integration. |
| `/aws-serverless:configure-event-bus` | Design an Amazon EventBridge event bus, Pipes enrichment, or Scheduler workflow with schema validation and DLQs. |
| `/aws-serverless:debug-invocation` | Triage Lambda timeouts, cold starts, OOMs, Event Source Mapping (ESM) poison pills, or API Gateway 5xx errors. |
| `/aws-serverless:optimize-cold-starts` | Analyze Lambda init duration, memory/CPU power tuning, SnapStart, Provisioned Concurrency, and bundle size. |
| `/aws-serverless:orchestrate-workflow` | Design an AWS Step Functions state machine or Lambda Durable Function with compensation (Saga), retries, and Distributed Map. |
| `/aws-serverless:scaffold-function` | Scaffold a production AWS Lambda function (with Powertools, SAM/CDK IaC, least-privilege IAM, and DLQ/destinations). |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-serverless_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `aws-serverless-mcp` | stdio | `uvx awslabs.aws-serverless-mcp-server@latest` | `mcp__plugin_aws-serverless_aws-serverless-mcp__*` | SAM CLI build/deploy/local invoke, Lambda diagnostics, and serverless application lifecycle. |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-serverless_awsknowledge__*` | Official AWS documentation, Architecture Center, and Well-Architected knowledge base. |
| `dynamodb` | stdio | `uvx awslabs.dynamodb-mcp-server>=2.1.6` | `mcp__plugin_aws-serverless_dynamodb__*` | DynamoDB table/index modeling, capacity inspection, and query validation. |
| `sns-sqs` | stdio | `uvx awslabs.amazon-sns-sqs-mcp-server@latest` | `mcp__plugin_aws-serverless_sns-sqs__*` | Amazon SNS topics and SQS queues inspection (read-only). |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-serverless_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |
| `billing` | stdio | `uvx awslabs.billing-cost-management-mcp-server@latest` | `mcp__plugin_aws-serverless_billing__*` | Cost Explorer, Budgets, Cost Anomaly Detection, Compute Optimizer, and Savings Plans / RI coverage. |

## Optional connectors

Connection-bound MCP servers you add yourself (see [CONNECTORS.md](./CONNECTORS.md)): `lambda-tool`, `stepfunctions-tool`.

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-serverless_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-serverless_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
- **PostToolUse** `Write|Edit|MultiEdit` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/iac-post-write…`
