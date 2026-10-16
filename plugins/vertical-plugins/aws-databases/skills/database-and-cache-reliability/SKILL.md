---
name: database-and-cache-reliability
description: Diagnose and remediate production stateful data-plane and queue reliability incidents across Amazon RDS/Aurora (DBLoad wait events, max_connections exhaustion, RDS Proxy pinning, replica lag, failover stalls), Amazon DynamoDB (hot partitions, GSI write throttling, Contributor Insights), Amazon ElastiCache for Valkey/Redis (Evictions, EngineCPUUtilization saturation), and Amazon SQS/Kafka backpressure (ApproximateAgeOfOldestMessage, DLQ spikes). Use when the user reports database latency, connection pool exhaustion, DynamoDB throttling, cache evictions, or consumer queue lag.
---

# AWS Database, Cache & Queue Production Reliability Guide

Use this skill when triaging production outages or tail-latency spikes rooted in **Amazon RDS / Aurora**, **Amazon DynamoDB**, **Amazon ElastiCache (Valkey / Redis)**, **Amazon OpenSearch**, or **Amazon SQS / MSK** queues.

---

## 1. Cross-Tier Stateful Triage Matrix (Metrics First)

| Service | Primary Saturation / Failure Metrics (`cloudwatch.get_metric_data`) | Root Cause Signature | Immediate Mitigation & Long-Term Fix |
|---|---|---|---|
| **RDS / Aurora (`AWS/RDS`)** | `DatabaseConnections`, `DBLoad` vs `vCPU`, `FreeableMemory`, `ReadIOPS`/`WriteIOPS`, `AuroraReplicaLag`, `BufferCacheHitRatio` | Connection storm from Lambda/EKS (`FATAL: remaining connection slots are reserved`), missing index (`DBLoad > vCPU` on `IO:DataFileRead`), or row lock contention (`Lock:transactionid`). | Place **RDS Proxy** in front of RDS/Aurora; identify blocking PIDs via Performance Insights (`aws pi get-resource-metrics`); scale reader/writer or add missing index concurrently. |
| **RDS Proxy (`AWS/RDS`)** | `DatabaseConnectionsCurrentlyBorrowed`, `DatabaseConnectionsCurrentlySessionPinned`, `ClientConnections`, `ClientConnectionSetupLatency` | **Session Pinning** (>50% pinned disables connection multiplexing due to `SET` statements, prepared statements, or temp tables). | Remove session-level `SET` statements or move them to parameter group defaults so RDS Proxy can multiplex connections cleanly. |
| **DynamoDB (`AWS/DynamoDB`)** | `ReadThrottleEvents`, `WriteThrottleEvents`, `ThrottledRequests`, `SystemErrors`, `OnlineIndexPercentageProgress`, `SuccessfulRequestLatency` | **Hot Partition Key** (>1,000 WCU or >3,000 RCU on a single physical partition) OR **GSI Write Backpressure** (`OnlineIndexThrottleEvents` throttling the base table!). | Enable **CloudWatch Contributor Insights** on the table/GSI to isolate the exact hot partition key; switch to On-Demand with Warm Throughput or shard keys; scale GSI write capacity >= base table write volume. |
| **ElastiCache (`AWS/ElastiCache`)** | `EngineCPUUtilization` (>90%), `CurrConnections`, `Evictions`, `DatabaseMemoryUsagePercentage`, `CacheHits` / `CacheMisses`, `ReplicationLag` | Single-threaded Valkey/Redis engine loop saturated (`EngineCPUUtilization > 90%` from `KEYS *`, large Lua scripts, or hot key) or `maxmemory` reached causing **Cache Stampede**. | Replace `KEYS` with `SCAN`, offload reads to replicas, upgrade to **ElastiCache for Valkey** (multi-threaded I/O), enable `volatile-lru`/`allkeys-lfu`, and add jittered TTLs in application code. |
| **SQS (`AWS/SQS`)** | `ApproximateAgeOfOldestMessage` (SLO SLI!), `ApproximateNumberOfMessagesVisible`, `ApproximateNumberOfMessagesNotVisible`, `NumberOfMessagesSent` | Consumer crash or downstream dependency slowdown causing `ApproximateAgeOfOldestMessage` to climb and poison pills to flood the **Dead-Letter Queue (DLQ)**. | Correlate consumer logs/traces first; fix downstream bottleneck before running `StartMessageMoveTask` (DLQ redrive) with rate limiting. |

---

## 2. Aurora / RDS Performance Insights & Failover Diagnostics

1. **Performance Insights (`DBLoad` vs `Max vCPU`)**:
   - Query `aws pi get-resource-metrics --service-type RDS --identifier <dbi-resource-id>` via `aws-api`.
   - Group by `db.wait_event` and `db.sql.tokenized`:
     - `CPU` wait event dominant -> Unindexed in-memory sort/hash join or high concurrency.
     - `IO:DataFileRead` / `IO:XactSync` -> Working set exceeds buffer pool (`FreeableMemory` low) or high commit frequency.
     - `Lock:tuple` / `Lock:transactionid` / `LWLock:BufferContent` -> Long-running transaction holding locks (`idle in transaction`).
2. **Fast Failover (>30s RTO Reduction)**:
   - Use the **AWS Advanced JDBC / Python / Go Wrapper Driver** (or RDS Proxy), which queries cluster topology directly and cuts Aurora failover recovery from 30–60s (DNS TTL) down to **3–8 seconds**.

---

## Reference Files

- [references/aurora-rds-diagnostics.md](references/aurora-rds-diagnostics.md) — Performance Insights CLI queries, PostgreSQL/MySQL lock & bloat diagnostics (`pg_stat_activity`), and RDS Proxy session-pinning triggers
- [references/dynamodb-throttling-and-gsi.md](references/dynamodb-throttling-and-gsi.md) — DynamoDB partition math (`3,000 RCU` / `1,000 WCU`), GSI write backpressure cascading failures, and Warm Throughput / Contributor Insights runbook
- [references/elasticache-and-sqs-dlq.md](references/elasticache-and-sqs-dlq.md) — ElastiCache `EngineCPUUtilization` vs `CPUUtilization`, cache stampede mitigation, and SQS DLQ redrive (`StartMessageMoveTask`) & visibility timeout sizing
