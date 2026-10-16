---
name: db-observability-and-wait-triage
description: >-
  Diagnoses AWS database performance bottlenecks, query latency, high CPU, I/O saturation, lock
  contention, connection exhaustion, autovacuum lag, and hot-partition throttling across RDS,
  Aurora, and DynamoDB using Performance Insights (Average Active Sessions / DBLoad wait events),
  Enhanced Monitoring 1-second OS counters, CloudWatch metrics, EXPLAIN ANALYZE plans, and
  read-only MCP database introspection.
version: 1
---

# Database Observability and Wait-Event Triage

Use this skill whenever an engineer reports **slow database queries, high CPU or `DBLoad`, application API timeouts, lock contention, connection exhaustion, replication lag, or DynamoDB throttling**. Never advise scaling up an instance class as a first resort without correlating control-plane metrics, Performance Insights wait events, and in-engine query plans.

## Reference Library (Load On-Demand)

- **[references/wait-event-catalog-and-queries.md](references/wait-event-catalog-and-queries.md)** — Load for engine-specific diagnostic SQL queries (`pg_stat_activity`, `pg_blocking_pids`, `pg_stat_statements`, `pg_stat_user_tables` autovacuum/XID wraparound age, MySQL `performance_schema.data_lock_waits`, InnoDB status), CloudWatch `get_metric_data` payloads, and wait-event remediation runbooks.

---

## Diagnostic Workflow

### Step 1: Pull Control-Plane Telemetry via `cloudwatch` MCP

Never rely solely on 60-second `CPUUtilization` averages, which obscure sub-second micro-burst saturation and non-CPU resource waits. Query the last 1–6 hours of metrics for the target identifier via `cloudwatch` (`get_metric_data`, `get_active_alarms`):

- **RDS / Aurora Core Metrics (`AWS/RDS`):** `DBLoad`, `DBLoadCPU`, `DBLoadNonCPU` (Performance Insights Average Active Sessions / AAS), `CPUUtilization`, `FreeableMemory`, `SwapUsage`, `ReadIOPS`, `WriteIOPS`, `ReadLatency`, `WriteLatency`, `DatabaseConnections`, `DiskQueueDepth`, `AuroraReplicaLag` / `ReplicaLag`.
- **RDS Proxy Metrics (`AWS/RDS`):** `DatabaseConnections`, `DatabaseConnectionsCurrentlyBorrowed`, `DatabaseConnectionsCurrentlySessionPinned`, `QueryDatabaseResponseLatency`.
- **DynamoDB Core Metrics (`AWS/DynamoDB`):** `ConsumedReadCapacityUnits`, `ConsumedWriteCapacityUnits`, `ReadThrottleEvents`, `WriteThrottleEvents`, `SuccessfulRequestLatency`, `ThrottledRequests`, `SystemErrors`.

### Step 2: Evaluate Average Active Sessions (`DBLoad` / AAS) Against `max vCPU`

Compare `DBLoad` (Average Active Sessions) against the instance's vCPU count (`max vCPU` line):

#### Case A: `DBLoadCPU > vCPU count` (Processor Saturation)
The instance is genuinely CPU-bound. Inspect Top SQL by CPU wait time before considering vertical scaling:
- **High calls/sec + moderate latency:** High-frequency unindexed point lookup, chatty N+1 ORM loop, missing cache (`amazon-elasticache`), or excessive connection establishment churn (add RDS Proxy).
- **Low calls/sec + high latency + high rows examined vs. returned:** Missing composite index, stale planner statistics, or suboptimal join order. Connect via read-only `postgres` or `mysql` MCP (`connect_to_database`) and run `EXPLAIN (ANALYZE, BUFFERS)` (PostgreSQL, for `SELECT` queries) or `EXPLAIN FORMAT=JSON` (MySQL) on the normalized SQL digest.

#### Case B: `DBLoad > vCPU count`, but `DBLoadNonCPU` Dominates (`CPUUtilization` is Low)
Sessions are queued on storage I/O, commit durability, locks, or internal latches. **Do NOT scale up compute** before diagnosing the dominant wait state:

| Dominant Wait Event | Engine | Root Cause Mechanism | Deterministic Remediation |
|---|---|---|---|
| `IO:XactSync` | Aurora PostgreSQL / Aurora MySQL | Sessions waiting for Aurora distributed storage to acknowledge transaction commits (`COMMIT` / WAL / binlog flush). | Inspect Top SQL for single-row `INSERT`/`UPDATE` statements running in autocommit loops. Batch writes into multi-row `INSERT INTO ... VALUES (...), (...)` or wrap loops in explicit transactions. |
| `IO:DataFileRead` / `wait/io/table/sql/handler` | Aurora & RDS (PG / MySQL) | Buffer pool / shared buffer cache misses caused by full table or index scans reading from storage. | Check `FreeableMemory` and buffer cache hit ratio; run `EXPLAIN` on Top SQL and create covering B-Tree/GIN indexes via online DDL (`db-ha-dr-and-schema-evolution`) before considering an R-family memory upgrade. |
| `Lock:transactionid` / `Lock:tuple` / `Lock:relation` | PostgreSQL (Aurora & RDS) | Row-level or table-level lock contention from uncommitted transactions or blocking DDL. | Query `pg_stat_activity` joined with `pg_blocking_pids(pid)` via `postgres` MCP to identify `idle in transaction` or long-running blockers. Set `idle_in_transaction_session_timeout` and `lock_timeout`. |
| `row lock` / `wait/io/table/sql/handler` lock waits | MySQL / MariaDB | InnoDB row lock or metadata lock (`MDL`) contention. | Query `performance_schema.data_lock_waits` and `performance_schema.metadata_locks` via `mysql` MCP; narrow transaction scope and index predicate columns. |
| `LWLock:BufferMapping` / `LWLock:lock_manager` | PostgreSQL (Aurora & RDS) | High-concurrency contention on shared buffer mapping partitions or fast-path lock slots (excessive partitions or unpooled connections). | Introduce RDS Proxy (`db-ha-dr-and-schema-evolution`) to cap active backend processes, prune unused table partitions, or upgrade to PostgreSQL 16+ where `lock_manager` scalability is improved. |
| `SYNCH` (mutex / lock array contention) | Aurora MySQL | Thread synchronization mutex contention under high concurrency. Standard 60s CloudWatch CPU averages often miss sub-second CPU spikes. | Inspect 1-second Enhanced Monitoring OS CPU counters (`RDSOSMetrics`). Increase static parameter `innodb_sync_array_size` (default `1`) to `>= vCPU count` in a custom Parameter Group, and introduce connection pooling or statement batching. |
| `Client:ClientRead` / `idle in transaction` | PostgreSQL / MySQL | Database holds open transaction while waiting on slow application middle-tier logic (e.g., external HTTP call inside a DB transaction). | Move network/API calls outside the database transaction boundary and enforce `idle_in_transaction_session_timeout` (e.g., `30000` ms). |

### Step 3: Engine Health, Maintenance & Hot-Partition Checks

When connected via read-only `postgres` or `mysql` MCP (always using a least-privilege read-only role with `default_transaction_read_only = on`, never `rds_superuser`):

1. **PostgreSQL Autovacuum & Transaction ID (XID) Wraparound:**
   - Query `pg_stat_user_tables` for high `n_dead_tup`, dead-tuple ratio, and stale `last_autovacuum`.
   - Check `SELECT datname, age(datfrozenxid), current_setting('autovacuum_freeze_max_age') FROM pg_database ORDER BY age(datfrozenxid) DESC;` (alert when `age(datfrozenxid)` exceeds 500 million; emergency at 1.5+ billion).
   - For hot update-heavy tables, tune table-level storage parameters (`ALTER TABLE ... SET (autovacuum_vacuum_scale_factor = 0.01, autovacuum_vacuum_cost_limit = 2000);`).
2. **DynamoDB Hot-Partition & GSI Backpressure Triage:**
   - If `ReadThrottleEvents` or `WriteThrottleEvents` occur while aggregate `ConsumedReadCapacityUnits` / `ConsumedWriteCapacityUnits` remain well below table limits, a single physical partition (limit: **1,000 WCU / 3,000 RCU per partition**) is hot.
   - Check `ThrottledRequests` vs. `SystemErrors` and inspect **CloudWatch Contributor Insights for DynamoDB** (`MostAccessedItems` / `ThrottledKeys`), or watch for GSI write throttling backpressure (`OnlineIndexThrottleEvents`) stalling base-table writes. Hand off to `amazon-dynamodb` to redesign the partition key with write sharding or high-cardinality composite keys.
