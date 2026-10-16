---
name: serverless-observability-and-triage
description: Diagnose and resolve production serverless incidents, Lambda timeouts, cold starts, memory-to-CPU right-sizing, API Gateway 502/504/CORS failures, X-Ray traces, CloudWatch Logs Insights queries, and Step Functions execution redrives. Use when debugging failing Lambda invocations, elevated latency, HTTP 5xx errors, throttling, out-of-memory crashes, or broken state machine runs.
---

# Serverless Observability, Performance Tuning & Incident Triage

Systematic triage and performance optimization workflow for AWS Lambda, Amazon API Gateway, Amazon EventBridge, Amazon SQS, and AWS Step Functions using `aws-serverless-mcp` (`sam_logs`, `get_metrics`) and `aws-cloudwatch-mcp` (`execute_log_insights_query`, `get_metric_data`, `analyze_log_group`, `get_active_alarms`).

## When to Use

- Lambda invocations fail with `Task timed out after X.XX seconds`, `Runtime.ExitError` (OOM), or high `Init Duration` (cold starts)
- Lambda functions show low memory utilization (~20%) and require CPU/cost right-sizing analysis
- API Gateway returns `502 Bad Gateway`, `504 Gateway Timeout`, `429 Too Many Requests`, or browser CORS errors
- Event-driven pipelines drop messages, trigger DLQ alarms, or suffer consumer lag
- Step Functions executions fail mid-workflow and need state-level diagnosis or execution/Map Run redrives

---

## Core Triage Workflow (Evidence First — Never Guess)

Never increase timeouts, memory, or concurrency blindly. Follow this deterministic sequence:

1. **Check Active Alarms & Service Metrics**:
   - Query `aws-cloudwatch-mcp` (`get_active_alarms`, `get_metric_data`) and `aws-serverless-mcp` (`get_metrics`) over the incident window.
   - Inspect `Invocations`, `Errors`, `Throttles`, `Duration` (p50/p95/p99/Max), `ConcurrentExecutions`, and `IteratorAge` (for stream consumers).
2. **Pull Structured Logs & `REPORT` Lines**:
   - Use `sam_logs` or `execute_log_insights_query` (`aws-cloudwatch-mcp`) to inspect the exact `START`, `REPORT`, and stack trace lines for failing `requestId`s.
3. **Correlate Downstream Latency (X-Ray / Application Signals)**:
   - Differentiate between **Init Duration** (cold start), **Function Code CPU time**, and **Downstream I/O wait** (VPC blackhole, DynamoDB throttling, external API stall, RDS connection saturation).
4. **Apply Targeted Remediation**:
   - Fix the root cause in code/IaC, add client-side timeouts shorter than the remaining Lambda invocation budget (`context.getRemainingTimeInMillis()`), and configure recommended CloudWatch alarms (`get_recommended_metric_alarms`).

---

## 1. Lambda Timeout & Cold-Start Triage

For detailed step-by-step commands, read `references/lambda-timeout-debugging.md`.

### Key Diagnostic Signals in `REPORT` Logs

| Log Signal | Meaning | Primary Remediation |
|---|---|---|
| `Status: timeout` + `Duration >= Configured Timeout` | Handler blocked until hard limit | Check VPC egress, missing SDK `connect_timeout`/`read_timeout`, or unawaited promises |
| High `Init Duration` (> 1,000 ms) | Heavy global imports, SDK init, or large deployment bundle | Lazy-load heavy clients, tree-shake bundles (`esbuild` minify), enable SnapStart (Java/Python/.NET) or Provisioned Concurrency |
| `Max Memory Used == Memory Size` | Out-of-memory crash (`Runtime.ExitError`) | Profile memory leaks (unbounded global caches, buffering multi-GB S3 files in `/tmp` or RAM instead of streaming); increase `MemorySize` if legitimate |
| Silence after `START RequestId` until timeout | Network blackhole (Lambda in private VPC subnet without NAT Gateway or VPC Endpoint) | Add free S3/DynamoDB Gateway Endpoints or move non-VPC functions out of the VPC (see `serverless-vpc-and-private-networking`) |

### CloudWatch Logs Insights Queries (`execute_log_insights_query`)

**Find All Timed-Out & OOM Invocations:**
```sql
fields @timestamp, @requestId, @duration, @billedDuration, @memorySize / 1000000 as memoryAllocatedMB, @maxMemoryUsed / 1000000 as maxMemoryUsedMB, @initDuration
| filter @message like /Task timed out|Process exited before completing|Runtime\.ExitError/ or @type = "REPORT"
| filter @message like /Task timed out|Runtime\.ExitError/ or maxMemoryUsedMB >= memoryAllocatedMB * 0.90
| sort @timestamp desc
| limit 50
```

**Cold Start Frequency & Init Duration Distribution:**
```sql
filter @type = "REPORT"
| stats count(*) as totalInvocations,
        count(@initDuration) as coldStarts,
        (count(@initDuration) / count(*)) * 100 as coldStartPct,
        pct(@initDuration, 50) as p50InitMs,
        pct(@initDuration, 99) as p99InitMs
  by bin(5m)
```

### Mandatory SDK Client Timeout Rule
Default AWS SDK / HTTP client timeouts often exceed Lambda's configured timeout, hiding the failing dependency behind a generic Lambda timeout. Always set explicit connect and read timeouts:
```python
import boto3
from botocore.config import Config

# Always set timeouts shorter than the Lambda function timeout
boto_config = Config(
    connect_timeout=2,
    read_timeout=5,
    retries={"max_attempts": 2, "mode": "standard"},
)
dynamodb = boto3.client("dynamodb", config=boto_config)
```

---

## 2. Lambda Memory-to-CPU Right-Sizing (The "20% Memory Utilization" Nuance)

In AWS Lambda, **CPU, network bandwidth, and disk I/O scale linearly with configured memory (`MemorySize`)**:
- **1,769 MB** = **1 full vCPU**
- **3,538 MB** = **2 vCPUs** (requires multi-threading or multiprocessing to utilize the second core)
- **< 1,769 MB** = Fractional vCPU time-slicing

### How to Analyze Low Memory Utilization (~20% Used)

When a user reports a function using only ~20% of its allocated memory (e.g., `Max Memory Used: 200 MB` on a `1024 MB` function), **do NOT immediately lower `MemorySize`** without checking whether the workload is CPU-bound or I/O-bound:

1. **Run the Memory/Duration Distribution Query (`execute_log_insights_query`)**:
   ```sql
   filter @type = "REPORT"
   | stats avg(@duration) as avgDurationMs,
           pct(@duration, 95) as p95DurationMs,
           max(@maxMemoryUsed / 1000000) as maxMemUsedMB,
           avg(@memorySize / 1000000) as allocatedMemMB,
           avg(@maxMemoryUsed / @memorySize) * 100 as memUtilizationPct
   ```
2. **Differentiate Workload Type**:
   - **I/O-Bound Function** (waiting on DynamoDB, RDS, third-party HTTP APIs, S3):
     - CPU sits idle while waiting on network sockets.
     - Lowering memory from `1024 MB` to `256 MB` barely changes `@duration`, cutting GB-second cost by **up to 75%**.
   - **CPU-Bound Function** (JSON serialization, crypto/hashing, image/PDF processing, Pandas/Polars transforms):
     - Lowering memory halves the vCPU allocation, which can **double `@duration`**—resulting in the exact same GB-second cost (`0.5x memory * 2x duration = 1.0x cost`) with **2x worse user-facing latency**!
     - Conversely, increasing memory to `1769 MB` (1 full vCPU) on a CPU-bound function often halves execution time at nearly zero net cost increase.
   - **Single-Threaded Code Above 1,769 MB**:
     - If a single-threaded Node.js or Python function is configured at `3008 MB` and only uses 20% memory, any allocation above `1,769 MB` provides a second vCPU core that a single-threaded event loop cannot use. Right-size immediately to `1,769 MB` (or lower if I/O-bound) and switch to `arm64` (Graviton2/3) for up to 34% better price-performance.

---

## 3. API Gateway 502 / 504 / CORS Triage

| HTTP Status | Root Cause | Diagnostic Step | Fix |
|---|---|---|---|
| **502 Bad Gateway** (`Execution failed due to configuration error: Malformed Lambda proxy response`) | Lambda returned a raw JSON object instead of the required proxy response envelope, or `body` is an object instead of a JSON-serialized string, or Lambda crashed unhandled | Enable API Gateway Execution Logs or inspect the Lambda response payload via `sam_local_invoke` / CloudWatch Logs | Return `{"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": JSON.stringify(data), "isBase64Encoded": false}` |
| **502 Bad Gateway** (`Invalid permissions on Lambda function`) | Missing `AWS::Lambda::Permission` allowing `apigateway.amazonaws.com` to invoke the function/alias | Check `aws lambda get-policy --function-name <fn>` | Add resource-based policy with `SourceArn` scoped to the API Gateway ARN |
| **504 Gateway Timeout** | Downstream Lambda took longer than API Gateway's integration timeout (**29s default** on REST/HTTP APIs) | Compare API Gateway `$context.integrationLatency` with Lambda `@duration` | Optimize Lambda latency, use asynchronous processing (`202 Accepted` + SQS/Step Functions + status polling/WebSockets), or use REST API integration timeout scaling (or Lambda Function URLs with `RESPONSE_STREAM` up to 15 min) |
| **Browser CORS Error** (Missing `Access-Control-Allow-Origin`) |1. `AWS_PROXY` Lambda handler does not return CORS headers on `2xx` **and** `4xx/5xx` responses<br>2. API Gateway GatewayResponses (`DEFAULT_4XX`, `DEFAULT_5XX`) lack CORS headers when authorizer/throttling rejects before reaching Lambda | Test both `OPTIONS` preflight and actual request (`curl -i -X OPTIONS ...`); check if failure occurred in Authorizer (`$context.authorizer.Error`) | Include `Access-Control-Allow-Origin` in all Lambda proxy responses AND configure `GatewayResponses` for `DEFAULT_4XX`/`DEFAULT_5XX` |

**API Gateway Access Log Insights Query (`execute_log_insights_query`):**
```sql
fields @timestamp, status, integrationStatus, latency, integrationLatency, ip, httpMethod, resourcePath, errorMessage
| filter status >= 500
| sort @timestamp desc
| limit 50
```

---

## 4. Step Functions Failure Diagnosis & Execution Redrive

1. **Inspect Execution History**:
   - Locate the failed event (`ExecutionFailed`, `TaskFailed`, `MapRunFailed`, `States.Timeout`, `States.TaskFailed`).
   - Check the `error` and `cause` fields in the `TaskFailedEventDetails`.
2. **Apply State-Level Retries & Catch Blocks**:
   - Always configure exponential backoff with jitter (`"JitterStrategy": "FULL"`, `"BackoffRate": 2.0`) for transient `Lambda.ServiceException`, `Lambda.AWSLambdaException`, `Lambda.SdkClientException`, and `Lambda.TooManyRequestsException`.
3. **Redrive From Point of Failure (Standard Workflows & Distributed Map)**:
   - Instead of restarting an entire Standard Workflow or 100,000-item Distributed Map from scratch, use **Step Functions Redrive** (`aws stepfunctions redrive-execution --execution-arn <arn>` or `redrive-map-run --map-run-arn <map-run-arn>`), which re-executes only the failed state transitions or failed child Map items while preserving completed steps.

---

## Reference Files

- `references/lambda-timeout-debugging.md` — Deep-dive CLI diagnostic playbooks, VPC blackhole checks, and multi-language SDK timeout patterns.
