# AWS Lambda Optimization (Memory, Graviton `arm64`, SnapStart & Logs)

> **Pricing note:** All prices shown are `us-east-1` approximate as of early 2026. Prices vary by region and may change. Always verify current pricing via `awspricing:get_pricing` or `billing:aws-pricing` before reporting to users.

## Memory-CPU Relationship

Lambda allocates CPU, network bandwidth, and disk I/O strictly proportional to configured memory:

- **1,769 MB = 1 full vCPU**
- **10,240 MB = 6 vCPUs**

Over-provisioning memory on I/O-bound functions wastes GB-seconds; conversely, increasing memory on **CPU-bound** functions (JSON serialization, crypto, image/data processing) gives proportionally more vCPU, which can reduce `Duration` enough to **lower total GB-second cost while improving latency**.
`Cost = Invocations × BilledDuration(ms) × (Memory_MB / 1024) × Price_per_GB_ms + Request_Charges`

## Compute Optimizer & CloudWatch Validation for Lambda

**Compute Optimizer Requirements:** ≥ 50 invocations in the 14-day lookback period.

**Metrics analyzed (`AWS/Lambda`):** `Invocations` (`Sum`), `Duration` (`Average`, `p95`, `p99`, `Maximum`), `Errors` (`Sum`), `Throttles` (`Sum`), `ProvisionedConcurrencyUtilization` (`Maximum`, `p95`), `ProvisionedConcurrencySpilloverInvocations` (`Sum`).

**Findings:** `NotOptimized` (`MemoryOverprovisioned`, `MemoryUnderprovisioned`), `Optimized`, `Unavailable` (insufficient data). Note: Lambda uses `NotOptimized`/`Optimized`/`Unavailable` rather than `Overprovisioned`.

```bash
aws compute-optimizer get-lambda-function-recommendations \
  --filters Name=Finding,Values=NotOptimized
```

### CloudWatch Logs Insights `REPORT` Verification Query
Use `cloudwatch:execute_log_insights_query` against `/aws/lambda/<function-name>` over 14 days to compare actual peak memory (`maxMemoryUsed`) against `memorySize`:

```text
filter @type = "REPORT"
| stats count(*) as invocations,
        avg(@billedDuration) as avgBilledMs,
        pct(@billedDuration, 95) as p95BilledMs,
        max(@memorySize / 1000 / 1000) as provisionedMB,
        max(@maxMemoryUsed / 1000 / 1000) as peakUsedMB,
        avg(@maxMemoryUsed / @memorySize) * 100 as avgMemoryUtilPct
```

- **Safe to reduce memory when:** `peakUsedMB < 50% of provisionedMB` AND the function is I/O-wait bound (e.g., waiting on downstream HTTP/RDS/DynamoDB calls) so reducing memory does not lengthen `@billedDuration`.

## Optimization Levers

| Strategy | Savings | Effort |
|----------|---------|--------|
| **Switch to `arm64` (Graviton2/3)** | **~20% lower GB-s price + ~10–15% faster duration** | Low — config change (`Architectures: ["arm64"]`) |
| **Right-size memory with Compute Optimizer / Power Tuning** | **10–50% GB-s cost** | Low–Medium |
| **Replace idle Provisioned Concurrency with SnapStart** (Java, Python, .NET) | **80–100% of Provisioned Concurrency cost** | Low |
| **SQS / Kinesis Event Filtering** | **50–90% fewer invocations** (filter non-matching events free at the ESM layer before invoking Lambda) | Low |
| **S3 Express / Ephemeral Storage (`/tmp`) right-sizing** | Avoids over-provisioning `/tmp` (> 512 MB free baseline bills per GB-s) | Low |

```bash
# Switch to arm64 (for hand-off to aws-serverless-engineer / aws-iac-engineer)
aws lambda update-function-configuration \
  --function-name my-function --architectures arm64
```

## Gotchas

- `arm64` requires pure interpreted code (Python, Node.js, Java bytecode, .NET) or `linux/arm64` compiled wheels/container images; check `PackageType` and Lambda Layers before switching.
- **Reserved concurrency (FREE throttle cap) ≠ Provisioned concurrency (PAID 24x7 pre-warmed environments)** — the #1 Lambda cost confusion.
- Provisioned concurrency costs **~$0.015/GB-hour (~$10.95/GB-month)** even at 0 invocations. Check `ProvisionedConcurrencyUtilization` in `cloudwatch:get_metric_data`; if P95 utilization `< 30%`, recommend **Lambda SnapStart** or Application Auto Scaling on Provisioned Concurrency.
- Often, **CloudWatch Logs ingestion ($0.50/GB) for a chatty Lambda function costs more than the Lambda execution itself!** Recommend switching verbose Lambda log groups to `INFREQUENT_ACCESS` ($0.25/GB — 50% savings) and setting log level to `WARN`/`INFO`.
- Use `alexcasalboni/aws-lambda-power-tuning` Step Functions state machine for systematic CPU vs. memory empirical tuning.
