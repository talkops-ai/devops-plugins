# Aurora & RDS Performance Insights, Lock Forensics, and RDS Proxy Reference

## 1. Performance Insights CLI Inspection (`aws pi`)

First retrieve the `DbiResourceId` (`db-...`) from `describe-db-instances`:
```bash
aws rds describe-db-instances \
  --db-instance-identifier "$DB_INSTANCE_ID" \
  --query 'DBInstances[0].DbiResourceId' \
  --output text
```

Query top wait events and top tokenized SQL queries over the incident window:
```bash
aws pi get-resource-metrics \
  --service-type RDS \
  --identifier "$DBI_RESOURCE_ID" \
  --start-time "2026-04-15T14:00:00Z" \
  --end-time "2026-04-15T15:00:00Z" \
  --period-in-seconds 60 \
  --metric-queries '[
    {"Metric": "db.load.avg", "GroupBy": {"Group": "db.wait_event", "Limit": 10}},
    {"Metric": "db.load.avg", "GroupBy": {"Group": "db.sql_tokenized", "Limit": 10}}
  ]'
```

---

## 2. Read-Only PostgreSQL Lock & Connection Forensics (`postgres` MCP Extension)

When the optional read-only `postgres` MCP server is connected, run these diagnostic queries:

### Identify Blocking & Blocked Queries (`pg_blocking_pids`)
```sql
SELECT
  blocked.pid AS blocked_pid,
  blocked.usename AS blocked_user,
  now() - blocked.query_start AS blocked_duration,
  blocked.query AS blocked_query,
  blocking.pid AS blocking_pid,
  blocking.state AS blocking_state,
  now() - blocking.xact_start AS blocking_xact_age,
  blocking.query AS blocking_query
FROM pg_stat_activity AS blocked
JOIN pg_stat_activity AS blocking
  ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
ORDER BY blocked_duration DESC;
```

### Check Transaction ID Wraparound Risk (`age(datfrozenxid)`)
```sql
SELECT
  datname,
  age(datfrozenxid) AS xid_age,
  round(100.0 * age(datfrozenxid) / 2000000000, 2) AS pct_towards_wraparound
FROM pg_database
ORDER BY xid_age DESC;
```

---

## 3. RDS Proxy Session-Pinning Triggers

When `DatabaseConnectionsCurrentlySessionPinned` spikes on RDS Proxy, connection pooling breaks down. Common causes in PostgreSQL/MySQL:
1. Executing `SET` session variables (`SET statement_timeout = ...`, `SET search_path = ...`).
2. Using named prepared statements at protocol level without deallocating them (in PgBouncer/RDS Proxy, configure client driver `preferQueryMode=simple` or `prepareThreshold=0` if pinning exceeds 30%).
3. Creating temporary tables (`CREATE TEMP TABLE`) or holding advisory locks (`pg_advisory_lock`).
