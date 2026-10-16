---
name: serverless-architecture-and-cost-advisor
description: Perform workload analysis, serverless pattern selection, architectural trade-off evaluation, and pre-deployment AWS cost estimation before generating IaC or application code. Use whenever a user describes a new serverless system, microservice, API, event pipeline, or migration and needs architecture recommendations and monthly FinOps cost projections.
---

# Serverless Architecture & FinOps Cost Advisor

Enforces the **Analyze -> Recommend -> Estimate -> Validate -> Deploy** lifecycle so every serverless architecture is right-sized for latency, durability, security, and monthly AWS cost before writing code or provisioning cloud resources.

## When to Use

- Designing a new serverless API, web application, event-driven workflow, data pipeline, or AI/code-execution sandbox
- Choosing between Lambda compute paradigms (Standard Event Functions, Durable Functions, MicroVMs, Lambda Managed Instances, Lambda Web Adapter, or Fargate)
- Choosing between API Gateway HTTP API (v2) vs REST API (v1), Step Functions Standard vs Express, SQS vs EventBridge vs Kinesis, or DynamoDB vs Aurora DSQL
- Estimating monthly run-rate costs and identifying FinOps cost traps before deployment

---

## Mandatory 5-Stage Engineering Workflow

Never jump straight from a vague user prompt to `sam_deploy`. Execute these stages in order:

1. **Stage 1 — Workload Analysis**:
   - Clarify traffic profile (requests/second, peak burst factor, daily volume), execution duration (milliseconds vs minutes vs days/months), statefulness/isolation requirements, latency SLAs (p99), and data access patterns.
   - Query `aws-documentation-mcp` (`search_documentation`, `read_documentation`) and `aws-serverless-mcp` (`get_lambda_guidance`, `get_iac_guidance`, `get_serverless_templates`) to verify current quotas and regional availability.
2. **Stage 2 — Pattern Recommendation (Trade-off Matrix)**:
   - Present the recommended AWS serverless architecture alongside explicit trade-offs (latency, cold start behavior, operational complexity, failure recovery).
3. **Stage 3 — Pre-Deployment FinOps Cost Estimation**:
   - Query `aws-billing-cost-mcp` (`aws-pricing`, `free-tier`) to calculate a transparent monthly cost breakdown across compute, API ingress, messaging, state transitions, persistence, networking (VPC/NAT), and CloudWatch logs.
4. **Stage 4 — Local Synthesis & Validation**:
   - Generate production-grade IaC (AWS SAM or CDK) and handler code, validate schemas (`dynamodb_data_model_validation`, `esm_optimize`), and test locally (`sam_build`, `sam_local_invoke`).
5. **Stage 5 — Gated Deployment & Observability**:
   - Present the deployment plan and obtain explicit user approval before executing `sam_deploy`, `deploy_webapp`, or mutating MCP tools.

---

## 1. Serverless Compute Selection Matrix

| Compute Paradigm | Best For | Execution Limit | Isolation & Concurrency Model | Key Trade-Off / Anti-Pattern |
|---|---|---|---|---|
| **Standard Lambda Event Function** (`aws-lambda`) | Stateless APIs, webhook handlers, queue/stream processors, cron jobs | Up to **15 minutes** | 1 concurrent request per execution environment; scales to 1,000 concurrency / 10s per function | Do not use `sleep()` for long waits or run untrusted multi-tenant code across shared warm environments |
| **Lambda Durable Functions** (`aws-lambda-durable-functions`) | Multi-step code-first sagas, human approval callbacks, AI agent tool-use loops, long waits in Python/TypeScript | Up to **1 year** (suspended checkpoints incur **$0 compute**) | Replay-based checkpointing (`ctx.step`, `ctx.wait`, `ctx.wait_for_callback`); requires qualified ARN (`$LATEST` or alias/version) | Code outside `ctx.step` replays on every resume—keep non-deterministic calls (`uuid`, `datetime`, RNG, HTTP) strictly inside steps |
| **Lambda MicroVMs** (`aws-lambda-microvms`) | Multi-tenant SaaS, AI code execution sandboxes, stateful sessions with snapshot/restore | Up to **15 minutes** active per request; persistent memory/disk across `/resume` | Dedicated hardware-isolated MicroVM per `microvmId` (`Runtime: microvm`); up to 64 concurrent requests per MicroVM; HTTP listener on `:8080` | Must reseed CSPRNG (`/dev/urandom`) and refresh short-lived credentials inside `/resume` handler; no outbound internet unless `VpcConfig` (LNCs) is attached |
| **Lambda Managed Instances (LMI)** (`aws-lambda-managed-instances`) | Steady-state, high-volume workloads needing EC2 Compute Savings Plans / RIs and zero cold starts without managing servers | Up to **15 minutes** | Multi-concurrency (`PerExecutionEnvironmentMaxConcurrency`) on customer-specified EC2 instance types via Capacity Provider | Capacity providers take ~15–20 min to scale out; handlers MUST be thread/async-safe (`AWS_LAMBDA_MAX_CONCURRENCY`) and never write unnamespaced files to `/tmp` |
| **Lambda Web Adapter** (`serverless-webapp-lambda-adapter`) | Lift-and-shift or greenfield Express.js, Next.js, FastAPI, Flask, Django, Spring Boot web apps | Up to **15 minutes** (with Function URL `RESPONSE_STREAM`) or 29s (API Gateway) | Runs standard HTTP server (`PORT=8080`) wrapped by the Lambda Web Adapter extension (`deploy_webapp`) | Avoid for pure event/queue workers where native handler events are simpler |
| **AWS Step Functions** (`aws-step-functions`) | Declarative JSON/ASL state machines, direct SDK service integrations (>220 AWS services without Lambda glue), Distributed Map over multi-GB S3 files | **Standard**: up to **1 year**<br>**Express**: up to **5 minutes** | Visual state transitions; Standard bills per state transition ($25 / 1M); Express bills by execution count + duration | Standard Workflows become expensive at >100 RPS high-frequency loops—use Express Workflows or Durable Functions instead |

---

## 2. API Ingress Selection Matrix

| Feature / Dimension | API Gateway HTTP API (v2) | API Gateway REST API (v1) | Lambda Function URL |
|---|---|---|---|
| **Base Price (per 1M requests)** | **~$1.00 / million** (up to **70% cheaper** than REST API) | **~$3.50 / million** | **Free** (included in Lambda request/duration price) |
| **Auth Options** | Native OIDC/JWT (Cognito/Auth0/Okta), IAM, Lambda Authorizer | IAM, Cognito, Lambda Authorizer, API Keys + Usage Plans, Resource Policies, mTLS | IAM (`AWS_IAM`) or `NONE` (custom validation in code) |
| **WAF / Edge Features** | Requires CloudFront in front for AWS WAF | Native AWS WAFv2 association, Private REST APIs (VPC Endpoints), Request Validation, VTL Mapping, Caching | CloudFront OAC + WAF supported; native `RESPONSE_STREAM` up to 20 MB / 15 min |
| **Default Recommendation** | **Default choice** for 80%+ of REST/JSON microservices and JWT-authenticated APIs | Choose when requiring **API Keys/Usage Plans, native WAF, Private VPC-only APIs, VTL direct integrations, or response caching** | Choose for **streaming LLM/SSE responses (`RESPONSE_STREAM`), webhooks, or single-function internal endpoints** |

---

## 3. Eventing & Messaging Selection Matrix

| Pattern | Service | Ordering & Delivery | Best Use Case |
|---|---|---|---|
| **Queue Buffering & Load Leveling** | **Amazon SQS** (Standard / FIFO) | At-least-once (Standard) or Exactly-once per `MessageGroupId` (FIFO) | Protecting downstream Lambda/databases from traffic spikes; retrying failed jobs with DLQs |
| **High-Throughput Pub/Sub Fan-Out** | **Amazon SNS** (+ SQS Fan-Out) | At-least-once fan-out to SQS, Lambda, HTTP, Email, SMS | Broadcasting domain events to multiple independent queues with attribute/payload filter policies |
| **SaaS & Cross-Account Event Routing** | **Amazon EventBridge Event Bus** | Rule-based content filtering, schema registry, archive & replay | Decoupled domain event routing across microservices, AWS services, and SaaS partners (Stripe, Datadog, Auth0) |
| **Point-to-Point Stream Enrichment** | **Amazon EventBridge Pipes** | Strict source ordering preserved; source -> filter -> enrich -> target | Connecting DynamoDB Streams, Kinesis, SQS, or MSK to targets with optional filtering and enrichment without glue code |
| **Cron & Millions of One-Time Timers** | **Amazon EventBridge Scheduler** | 1-minute resolution, timezone-aware + DST, `ActionAfterCompletion: DELETE` | Per-user reminders, delayed order expiration (`at()`), and recurring cron jobs across >270 AWS service APIs |

---

## 4. Persistence Selection Matrix

| Workload Profile | Recommended Database | Why |
|---|---|---|
| **Known key-value & query access patterns at any scale (<10ms p99)** | **Amazon DynamoDB** (`dynamodb-access-pattern-modeling`) | Zero connection management, native HTTP API, single-digit millisecond latency, Streams for CDC, On-Demand pay-per-request |
| **Serverless relational SQL with strict ACID transactions & active-active HA** | **Amazon Aurora DSQL** (`serverless-relational-aurora-dsql`) | PostgreSQL-compatible distributed SQL, zero connection-pool exhaustion, IAM token auth, scale-to-zero compute/storage separation |
| **Legacy relational schema requiring stored procedures, triggers, or PG extensions (`pgvector`, PostGIS)** | **Aurora Serverless v2 + RDS Data API or RDS Proxy** | Full PostgreSQL/MySQL compatibility; always pair with RDS Data API or RDS Proxy so Lambda concurrency spikes do not exhaust DB connections |

---

## 5. Pre-Deployment FinOps Cost Estimation Checklist

When running Stage 3 (`Estimate`), query `aws-billing-cost-mcp` (`aws-pricing`) for the target region and present a table covering:

1. **Compute (`AWSLambda`)**:
   - Requests (`$0.20 per 1M requests` after 1M free tier) + Duration (`GB-seconds` on `arm64` @ `$0.0000133334/GB-s` vs `x86_64` @ `$0.0000166667/GB-s`).
   - Always recommend **`arm64` (Graviton2/3)** by default for **20% lower cost and up to 34% better price-performance**.
2. **Ingress (`AmazonApiGateway`)**:
   - Compare HTTP API (`~$1.00/1M`) vs REST API (`~$3.50/1M`).
3. **Orchestration (`AWSStepFunctions`)**:
   - Compare Standard (`$0.025 per 1,000 state transitions`) vs Express (`$1.00 per 1M requests` + duration) vs Lambda Durable Functions.
4. **Event Source Mappings (`esm_optimize`)**:
   - Account for Kafka/SQSProvisioned Pollers or Kinesis/DynamoDB Streams shard polling costs.
5. **Persistence (`AmazonDynamoDB` / `AuroraDSQL`)**:
   - Run `compute_performances_and_costs` (`aws-dynamodb-mcp`) to model RCU/WCU costs across base tables and GSIs.
6. **Hidden Cost Traps to Flag Proactively**:
   - **NAT Gateways**: `~$32.40/month per AZ` + `$0.045/GB` -> replace with free S3/DynamoDB Gateway Endpoints or IPv6 EIGW.
   - **CloudWatch Logs Ingestion**: `$0.50/GB` ingested -> set explicit `RetentionInDays` (e.g., `14` or `30` days), sample `DEBUG` logs in production (1–5%), and use Embedded Metric Format (EMF).
   - **AWS WAF Bot Control / Unfiltered Regex Rules**: Put cheap IP/Geo/Rate rules at lower priority numbers first and use scope-down statements on expensive rules (`serverless-security-auth-and-waf`).
