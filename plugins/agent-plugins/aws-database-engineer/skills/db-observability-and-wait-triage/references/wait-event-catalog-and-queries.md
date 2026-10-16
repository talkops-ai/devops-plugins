# Wait-Event Catalog, CloudWatch Telemetry & In-Engine Diagnostic Queries

## 1. CloudWatch & Performance Insights Telemetry Queries

When investigating an RDS or Aurora performance issue, query the `AWS/RDS` namespace over a 1-to-6 hour window with a 60-second period using `cloudwatch` (`get_metric_data`):

```json
{
  "MetricDataQueries": [
    {
      "Id": "dbload",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/RDS",
          "MetricName": "DBLoad",
          "Dimensions": [{"Name": "DBInstanceIdentifier", "Value": "<db-instance-id>"}]
        },
        "Period": 60,
        "Stat": "Average"
      }
    },
    {
      "Id": "dbload_cpu",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/RDS",
          "MetricName": "DBLoadCPU",
          "Dimensions": [{"Name": "DBInstanceIdentifier", "Value": "<db-instance-id>"}]
        },
        "Period": 60,
        "Stat": "Average"
      }
    },
    {
      "Id": "dbload_noncpu",
      "MetricStat": {
        "Metric": {
          "Namespace": "AWS/RDS",
          "MetricName": "DBLoadNonCPU",
          "Dimensions": [{"Name": "DBInstanceIdentifier", "Value": "<db-instance-id>"}]
        },
        "Period": 60,
        "Stat": "Average"
      }
    }
  ]
}
```

### Pulling Performance Insights Wait-Event Breakdown (`pi` API via `aws-mcp`)

To break down `DBLoad` by exact wait event and Top SQL digest using `aws___call_aws`:

```bash
aws pi get-resource-metrics \
  --service-type RDS \
  --identifier <DbiResourceId> \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period-in-seconds 60 \
  --metric-queries '[
    {"Metric": "db.load.avg", "GroupBy": {"Group": "db.wait_event", "Limit": 10}},
    {"Metric": "db.load.avg", "GroupBy": {"Group": "db.sql_tokenized", "Limit": 10}}
  ]'
```

*(Retrieve `DbiResourceId` via `aws rds describe-db-instances --db-instance-identifier <id> --query 'DBInstances[0].DbiResourceId'`.)*

### Enhanced Monitoring 1-Second Granularity (`RDSOSMetrics`)

Standard CloudWatch metrics aggregate at 60-second intervals, hiding micro-bursts (such as Aurora MySQL `SYNCH` mutex storms or sub-second I/O queue spikes). Query the `RDSOSMetrics` log group in CloudWatch Logs via `cloudwatch` (`execute_log_insights_query`):

```
fields @timestamp, instanceID, cpuUtilization.total, cpuUtilization.wait, memory.free, swap.used, diskIO.0.readIOsPS, diskIO.0.writeIOsPS, diskIO.0.diskQueueDepth
| filter instanceID = "<db-instance-id>"
| sort @timestamp desc
| limit 50
```

---

## 2. PostgreSQL In-Engine Diagnostic Queries (`postgres` MCP)

> **Security Guardrail:** Always connect using a least-privilege read-only database role (`default_transaction_read_only = on`). Never connect as `rds_superuser` or `postgres`.

### A. Active Wait Events & Blocking Lock Tree

```sql
SELECT
  blocked.pid AS blocked_pid,
  blocked.usename AS blocked_user,
  blocked.state AS blocked_state,
  blocked.wait_event_type,
  blocked.wait_event,
  now() - blocked.query_start AS blocked_duration,
  LEFT(blocked.query, 200) AS blocked_query,
  blocking.pid AS blocking_pid,
  blocking.usename AS blocking_user,
  blocking.state AS blocking_state,
  now() - blocking.xact_start AS blocker_xact_age,
  LEFT(blocking.query, 200) AS blocking_query
FROM pg_stat_activity blocked
JOIN LATERAL unnest(pg_blocking_pids(blocked.pid)) AS b_pid ON true
JOIN pg_stat_activity blocking ON blocking.pid = b_pid
ORDER BY blocked_duration DESC;
```

### B. Top Resource-Consuming SQL (`pg_stat_statements`)

```sql
SELECT
  queryid,
  calls,
  ROUND(total_exec_time::numeric, 2) AS total_ms,
  ROUND(mean_exec_time::numeric, 2) AS mean_ms,
  rows,
  shared_blks_hit,
  shared_blks_read,
  ROUND(100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0), 2) AS cache_hit_pct,
  LEFT(query, 250) AS sql_sample
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 15;
```

### C. Autovacuum Dead Tuples & XID Wraparound Age

```sql
-- Check database-level transaction ID wraparound age
SELECT
  datname,
  age(datfrozenxid) AS xid_age,
  current_setting('autovacuum_freeze_max_age')::bigint AS freeze_max_age,
  ROUND(100.0 * age(datfrozenxid) / current_setting('autovacuum_freeze_max_age')::bigint, 2) AS pct_towards_wraparound
FROM pg_database
WHERE datallowconn
ORDER BY age(datfrozenxid) DESC;

-- Check table-level dead tuple bloat and vacuum lag
SELECT
  schemaname,
  relname,
  n_live_tup,
  n_dead_tup,
  ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_tup_pct,
  last_autovacuum,
  last_autoanalyze
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC
LIMIT 20;
```

---

## 3. MySQL / MariaDB In-Engine Diagnostic Queries (`mysql` MCP)

### A. Active InnoDB Row Lock & Metadata Lock (`MDL`) Waits

```sql
SELECT
  r.trx_id AS waiting_trx_id,
  r.trx_mysql_thread_id AS waiting_thread,
  TIMESTAMPDIFF(SECOND, r.trx_wait_started, NOW()) AS wait_seconds,
  LEFT(r.trx_query, 200) AS waiting_query,
  b.trx_id AS blocking_trx_id,
  b.trx_mysql_thread_id AS blocking_thread,
  LEFT(b.trx_query, 200) AS blocking_query
FROM performance_schema.data_lock_waits w
JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_engine_transaction_id
JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_engine_transaction_id
ORDER BY wait_seconds DESC;
```

### B. Top Digest Statements by Latency & Full Table Scans

```sql
SELECT
  DIGEST,
  COUNT_STAR AS exec_count,
  ROUND(SUM_TIMER_WAIT / 1000000000, 2) AS total_ms,
  ROUND(AVG_TIMER_WAIT / 1000000000, 2) AS avg_ms,
  SUM_ROWS_EXAMINED AS rows_examined,
  SUM_ROWS_SENT AS rows_sent,
  SUM_NO_INDEX_USED AS full_scans,
  LEFT(DIGEST_TEXT, 250) AS sql_digest
FROM performance_schema.events_statements_summary_by_digest
WHERE SCHEMA_NAME IS NOT NULL
ORDER BY SUM_TIMER_WAIT DESC
LIMIT 15;
```

### C. Aurora MySQL `SYNCH` Mutex Contention Check

When `SYNCH` wait events spike in Performance Insights on Aurora MySQL:
1. Check current `innodb_sync_array_size`:
   ```sql
   SHOW GLOBAL VARIABLES LIKE 'innodb_sync_array_size';
   ```
2. If set to `1` (the default) on a multi-vCPU instance under high concurrency, create or update a **custom DB Cluster/Instance Parameter Group** to set `innodb_sync_array_size` equal to or greater than the vCPU count (for example, `16` on a 16-vCPU instance). Note that `innodb_sync_array_size` is a **static** parameter and requires a scheduled instance reboot during a maintenance window to take effect.
