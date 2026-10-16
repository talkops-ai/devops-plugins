# Amazon ElastiCache (Valkey / Redis) & Amazon SQS DLQ Reliability Reference

## 1. ElastiCache: `EngineCPUUtilization` vs. `CPUUtilization`

| Metric (`AWS/ElastiCache`) | What It Measures | Alert Threshold |
|---|---|---|
| **`EngineCPUUtilization`** | CPU utilization of the **primary Redis/Valkey command-processing thread**. | **Warning > 75%**, **Critical > 90%** |
| **`CPUUtilization`** | Aggregate host OS CPU across all vCPUs (including background I/O, TLS, replication). | Can appear low (`25%` on a 4-vCPU node) while `EngineCPUUtilization` is at **100%** and timing out every client! |

### Investigating ElastiCache Latency Spikes
1. Query `EngineCPUUtilization`, `Evictions`, `CurrConnections`, `NewConnections`, `DatabaseMemoryUsagePercentage`, and `ReplicationBytes` in `cloudwatch.get_metric_data`.
2. Query the ElastiCache Slow Log log group in CloudWatch Logs Insights (`cloudwatch.execute_log_insights_query`) for `KEYS *`, `SMEMBERS` on million-element sets, or blocking Lua `EVAL` scripts.
3. **Cache Stampede Prevention**:
   - When `Evictions > 0` or a hot key expires, thousands of concurrent application threads miss the cache and hammer RDS/Aurora simultaneously.
   - **Remediation**: Add randomized TTL jitter (`TTL + random(0, 60s)`), implement single-flight / mutex request coalescing in application code, and scale memory or enable Cluster Mode Enabled sharding.

---

## 2. Amazon SQS Backpressure & Dead-Letter Queue (DLQ) Redrive Protocol

### Why `ApproximateAgeOfOldestMessage` Is the Primary Queue SLI
- `ApproximateNumberOfMessagesVisible` (queue depth) alone is misleading: a queue with 50,000 messages processed at 10,000 msg/sec has only a 5-second delay, whereas a queue with 100 messages and 0 active consumers has an infinite delay.
- Always alarm on **`ApproximateAgeOfOldestMessage` > SLA threshold** (e.g., `> 120 seconds`).

### Visibility Timeout vs. Consumer Processing Time Trap
- If a consumer (Lambda or ECS worker) takes up to `60s` to process a message, but the SQS queue `VisibilityTimeout` is `30s`, SQS makes the message visible again at `T+30s`.
- A second consumer picks up the same message, causing duplicate processing, downstream DB contention, and eventually exhausting `maxReceiveCount` into the DLQ!
- **Rule**: Set SQS `VisibilityTimeout >= (6 * Lambda Function Timeout)` or `>= (2 * P99 Worker Processing Time)`.

### Safe DLQ Redrive (`StartMessageMoveTask`)
Never blindly redrive 100,000 DLQ messages at full speed into a recovering production service:
1. Inspect sample DLQ messages first to verify the poison-pill bug or downstream outage is resolved.
2. Propose a **rate-limited** `start-message-move-task` (`--max-number-of-messages-per-second 50`) for human approval:
   ```bash
   aws sqs start-message-move-task \
     --source-arn "arn:aws:sqs:us-east-1:123456789012:orders-dlq" \
     --destination-arn "arn:aws:sqs:us-east-1:123456789012:orders-queue" \
     --max-number-of-messages-per-second 50
   ```
