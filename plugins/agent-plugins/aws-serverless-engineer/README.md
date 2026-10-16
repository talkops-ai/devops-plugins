# AWS Serverless Engineer

Principal AWS Serverless Architect & Engineer: Lambda (Event Functions, Durable Functions, MicroVMs, Managed Instances, Web Adapter), API Gateway (HTTP/REST/WebSocket), Step Functions (Standard/Express/Distributed Map), EventBridge (Buses, Pipes, Scheduler), SQS/SNS async messaging, Event Source Mappings (SQS/Kinesis/DynamoDB/Kafka), DynamoDB access-pattern modeling, Aurora DSQL, Cognito/IAM/WAFv2 security, CloudWatch/X-Ray triage, FinOps cost estimation, and SAM/CDK deployment.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-serverless-engineer@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/aws-serverless-engineer.toml`](./codex/agents/aws-serverless-engineer.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, command, hook, and MCP server below is bound to the [`aws-serverless-engineer`](./agents/aws-serverless-engineer.md) agent, which the host runtime spawns as a dynamic sub-agent.

- Claude Code: `@agent-aws-serverless-engineer:aws-serverless-engineer` or let Claude delegate based on the agent description
- Headless: `claude --agent aws-serverless-engineer:aws-serverless-engineer`
- Codex: install the custom agent above, then ask Codex to spawn `aws-serverless-engineer`. Codex plugins can't bundle agents, so without it the skills and MCP servers attach to the main agent.

## Skills

| Skill | What it does |
|---|---|
| `amazon-eventbridge-event-bus` | Builds, runs, debugs, and operates event-driven applications using EventBridge Event Bus - a managed, centrally governed publish/subscribe event bus that an organization can share across many teams and accounts. |
| `amazon-eventbridge-scheduler-and-pipes` | Architect and implement time-based serverless jobs using Amazon EventBridge Scheduler (one-time at() timers, timezone-aware cron(), flexible time windows, universal targets, auto-delete) and point-to-point streaming int… |
| `amazon-sqs-sns-async-messaging` | Design, provision, and operate resilient asynchronous messaging pipelines with Amazon SQS and Amazon SNS using aws-sns-sqs-mcp and AWS SAM/CDK. |
| `api-gateway` | Build, manage, and operate APIs with Amazon API Gateway (REST, HTTP, and WebSocket). |
| `aws-auth-and-environment-preflight` | Verify AWS credentials, IAM identity, region configuration, and local serverless toolchain readiness (SAM CLI, AWS CDK, Docker daemon, AWS CLI v2). |
| `aws-lambda` | Design, build, deploy, test, and debug serverless applications with AWS Lambda. |
| `aws-lambda-durable-functions` | Builds resilient, long-running, multi-step applications with AWS Lambda durable functions with automatic state persistence, retry logic, and orchestration for long-running executions. |
| `aws-lambda-managed-instances` | Evaluates, configures, and migrates workloads to AWS Lambda Managed Instances (LMI). |
| `aws-lambda-microvms` | Builds, runs, debugs, and operates applications on AWS Lambda MicroVMs — Firecracker-isolated, snapshot-resumable serverless compute environments running inside a container with up to 8 hr lifetimes. |
| `aws-serverless-deployment` | AWS SAM and AWS CDK deployment for serverless applications. |
| `aws-step-functions` | Authors and edits AWS Step Functions state machines: writes Amazon States Language (ASL) in JSONata, and chooses and structures state types (Task, Choice, Map, Parallel, Pass, Wait, Succeed, Fail). |
| `connecting-lambda-to-api-gateway` | Connects an existing AWS Lambda function to Amazon API Gateway by creating a REST or HTTP API with resource/method setup, Lambda proxy integration, permissions, and deployment. |
| `connecting-lambda-to-dynamodb` | Connects an AWS Lambda function to DynamoDB with IAM roles, stream event source mapping, and read/write permissions. |
| `creating-api-gateway-stage` | Creates an API Gateway stage with CloudWatch logging, X-Ray tracing, throttling, WAF integration, and IAM roles following AWS best practices. |
| `deploying-custom-domain-rest-api` | Deploys a Regional REST API with a custom domain name, a Lambda backend function, and a request-based Lambda authorizer using AWS CLI. |
| `dynamodb-access-pattern-modeling` | Design, validate, cost-estimate, and generate code for Amazon DynamoDB data models and relational-to-DynamoDB migrations using aws-dynamodb-mcp (dynamodb_data_modeling, source_db_analyzer, compute_performances_and_costs… |
| `lambda-event-source-mappings-esm` | Configure, optimize, and troubleshoot AWS Lambda Event Source Mappings (ESMs) across Amazon SQS, Kinesis Data Streams, DynamoDB Streams, Amazon MSK, and self-managed Apache Kafka using aws-serverless-mcp (esm_guidance,… |
| `serverless-architecture-and-cost-advisor` | Perform workload analysis, serverless pattern selection, architectural trade-off evaluation, and pre-deployment AWS cost estimation before generating IaC or application code. |
| `serverless-data-and-file-processing` | Architect serverless file upload, event-driven S3 processing, and high-concurrency batch data pipelines. |
| `serverless-observability-and-triage` | Diagnose and resolve production serverless incidents, Lambda timeouts, cold starts, memory-to-CPU right-sizing, API Gateway 502/504/CORS failures, X-Ray traces, CloudWatch Logs Insights queries, and Step Functions execu… |
| `serverless-relational-aurora-dsql` | Architect and implement serverless relational SQL databases with Amazon Aurora DSQL and Aurora Serverless v2 (RDS Data API / RDS Proxy). |
| `serverless-security-auth-and-waf` | Design and harden serverless security across Amazon Cognito, API Gateway JWT and Lambda Authorizers, IAM least-privilege execution roles, Secrets Manager Lambda Extension caching, Lambda MicroVM snapshot/CSPRNG security… |
| `serverless-vpc-and-private-networking` | Architect, troubleshoot, and cost-optimize VPC networking for AWS Lambda, MicroVMs, API Gateway Private Integrations, and VPC Endpoints. |
| `serverless-webapp-lambda-adapter` | Deploy full-stack, backend, and frontend web applications (Express.js, Next.js, FastAPI, Flask, Django, Spring Boot, React/Vue/Vite) to AWS Lambda, API Gateway, S3, and CloudFront using AWS Lambda Web Adapter and aws-se… |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). In Claude Code they are bound to the agent through its `tools:` allowlist.

| Server | Transport | Launch | Claude Code tool pattern | Notes |
|---|---|---|---|---|
| `aws-serverless-mcp` | stdio | `uvx awslabs.aws-serverless-mcp-server@latest` `--allow-write --allow-sensitive-data-access` | `mcp__plugin_aws-serverless-engineer_aws-serverless-mcp__*` | SAM/Lambda/ESM guidance and inspection, read-only. Add --allow-write to deploy and --allow-sensitive-data-access for logs. |
| `aws-documentation-mcp` | stdio | `uvx awslabs.aws-documentation-mcp-server@latest` | `mcp__plugin_aws-serverless-engineer_aws-documentation-mcp__*` | Official AWS Documentation MCP Server (search_documentation, read_documentation, recommend). |
| `aws-dynamodb-mcp` | stdio | `uvx awslabs.dynamodb-mcp-server>=2.1.6` | `mcp__plugin_aws-serverless-engineer_aws-dynamodb-mcp__*` | Pinned >=2.1.6 to remediate CVE-2026-85654 command injection in CDK resource generation. |
| `aws-sns-sqs-mcp` | stdio | `uvx awslabs.amazon-sns-sqs-mcp-server@latest` `--allow-resource-creation` | `mcp__plugin_aws-serverless-engineer_aws-sns-sqs-mcp__*` | Manages SNS topics and SQS queues. Creating topics/queues is off by default (add --allow-resource-creation). |
| `aws-cloudwatch-mcp` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-serverless-engineer_aws-cloudwatch-mcp__*` |  |
| `aws-billing-cost-mcp` | stdio | `uvx awslabs.billing-cost-management-mcp-server@latest` | `mcp__plugin_aws-serverless-engineer_aws-billing-cost-mcp__*` |  |

AWS credentials are inherited from the host environment (`AWS_PROFILE`, SSO, or instance role). In Claude Code `AWS_REGION` defaults to `us-east-1` when unset; the portable `mcp.json` can't express that default, so set `AWS_REGION` in your environment on other hosts. Codex starts MCP servers with a minimal environment: if a server can't see your profile, set `AWS_PROFILE`/`AWS_REGION` for it in `~/.codex/config.toml`.

## Optional connectors

Connection-bound MCP servers you add yourself (see [CONNECTORS.md](./CONNECTORS.md)): `lambda-tool`, `stepfunctions-tool`, `aurora-dsql`.

## Hooks

- **PreToolUse** `Bash` — command: `sh -c 'python3 "$0" 2>/dev/null \|\| python "$0" 2>/dev/null \|\| py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `use_aws|mcp__aws.*|mcp__plugin_.*aws-.*mcp.*|mcp__plugin_.*awslocation.*|mcp__.*agentcore.*` — command: `sh -c 'python3 "$0" 2>/dev/null \|\| python "$0" 2>/dev/null \|\| py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `Bash` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`
- **PreToolUse** `use_aws|mcp__aws.*|mcp__plugin_.*aws-.*mcp.*|mcp__plugin_.*awslocation.*|mcp__.*agentcore.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`
- **PostToolUse** `Edit|Write` — command: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/validate-template.sh"`

## Upstream

Derived from the following open-source sources (see the repository `NOTICE`):

- [`aws-serverless`](https://github.com/awslabs/agent-plugins) (awslabs/agent-plugins, Apache-2.0)
- [`specialized-skills/serverless-skills`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
