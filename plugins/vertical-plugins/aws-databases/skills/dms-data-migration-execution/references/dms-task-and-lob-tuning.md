# AWS DMS Source LOB Audit Queries, Parallel Load Rules & Troubleshooting

## 1. Source Database LOB Distribution Audit Queries

Before choosing Limited LOB Mode, Inline LOB Mode, or Full LOB Mode, profile the actual LOB sizes in the source database.

### A. Oracle Source (`DBMS_LOB.GETLENGTH`)

```sql
-- 1. List all LOB columns in the target migration schema
SELECT owner, table_name, column_name, data_type
FROM dba_tab_cols
WHERE owner = 'APP_SCHEMA'
  AND data_type IN ('CLOB', 'BLOB', 'NCLOB', 'LONG', 'LONG RAW')
ORDER BY table_name, column_name;

-- 2. Profile size distribution (under 32 KB vs. over 32 KB) for a specific LOB column
SELECT
  COUNT(*) AS total_rows,
  ROUND(MAX(DBMS_LOB.GETLENGTH(lob_col)) / 1024.0, 2) AS max_kb,
  SUM(CASE WHEN DBMS_LOB.GETLENGTH(lob_col) <= 32768 THEN 1 ELSE 0 END) AS rows_le_32kb,
  SUM(CASE WHEN DBMS_LOB.GETLENGTH(lob_col) > 32768 THEN 1 ELSE 0 END) AS rows_gt_32kb
FROM APP_SCHEMA.TARGET_TABLE
WHERE lob_col IS NOT NULL;
```

### B. PostgreSQL Source (`octet_length`)

```sql
-- 1. Identify TEXT, BYTEA, and JSONB columns
SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
  AND data_type IN ('text', 'bytea', 'json', 'jsonb');

-- 2. Measure max and 95th percentile size in KB
SELECT
  COUNT(*) AS total_rows,
  ROUND(MAX(octet_length(payload::text)) / 1024.0, 2) AS max_kb,
  ROUND(percentile_cont(0.95) WITHIN GROUP (ORDER BY octet_length(payload::text)) / 1024.0, 2) AS p95_kb,
  SUM(CASE WHEN octet_length(payload::text) <= 32768 THEN 1 ELSE 0 END) AS rows_le_32kb
FROM app_schema.events;
```

### C. MySQL / MariaDB Source (`LENGTH`)

```sql
-- 1. Identify TEXT and BLOB columns
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'app_db'
  AND DATA_TYPE IN ('text', 'mediumtext', 'longtext', 'blob', 'mediumblob', 'longblob', 'json');

-- 2. Measure max size in KB
SELECT
  COUNT(*) AS total_rows,
  ROUND(MAX(LENGTH(lob_col)) / 1024.0, 2) AS max_kb,
  SUM(CASE WHEN LENGTH(lob_col) <= 32768 THEN 1 ELSE 0 END) AS rows_le_32kb,
  SUM(CASE WHEN LENGTH(lob_col) > 32768 THEN 1 ELSE 0 END) AS rows_gt_32kb
FROM app_db.documents;
```

### D. Limited LOB Memory Pre-Allocation Warning

In **Limited LOB Mode**, DMS pre-allocates memory per LOB column equal to:
$$\text{Memory Pre-Allocated} = \text{LobMaxSize} \times \text{CommitRate} \times \text{Number of Parallel Subtasks}$$
Never set `"LobMaxSize": 65536` (64 MB) alongside `"CommitRate": 50000` — doing so causes immediate Out-Of-Memory (OOM) termination on the replication instance. When any LOB exceeds $64\text{ KB}$, switch to **Inline LOB Mode** (`"FullLobMode": true, "InlineLobMaxSize": 32`).

---

## 2. Parallel Table Load Selection Rules (`table-settings`)

For tables exceeding 50–100 million rows, configure parallel Full Load threads inside the DMS table mapping JSON (`--table-mappings`):

### Option A: Auto-Partitioned Source Table (`partitions-auto`)

```json
{
  "rules": [
    {
      "rule-type": "selection",
      "rule-id": "1",
      "rule-name": "include-orders",
      "object-locator": {
        "schema-name": "app_schema",
        "table-name": "orders"
      },
      "rule-action": "include"
    },
    {
      "rule-type": "table-settings",
      "rule-id": "2",
      "rule-name": "parallel-orders-partitions",
      "object-locator": {
        "schema-name": "app_schema",
        "table-name": "orders"
      },
      "parallel-load": {
        "type": "partitions-auto",
        "max-threads": 8
      }
    }
  ]
}
```

### Option B: Unpartitioned Large Table Range Segmentation (`ranges`)

Compute evenly distributed primary-key boundaries on the source table using `ntile(4)`:

```sql
SELECT segment, MAX(order_id) AS boundary_id
FROM (
  SELECT order_id, ntile(4) OVER (ORDER BY order_id) AS segment
  FROM app_schema.orders
) t
WHERE segment < 4
GROUP BY segment
ORDER BY segment;
```

Then configure `"type": "ranges"` in `table-settings`:

```json
{
  "rule-type": "table-settings",
  "rule-id": "2",
  "rule-name": "parallel-orders-ranges",
  "object-locator": {
    "schema-name": "app_schema",
    "table-name": "orders"
  },
  "parallel-load": {
    "type": "ranges",
    "columns": ["order_id"],
    "boundaries": [
      ["25000000"],
      ["50000000"],
      ["75000000"]
    ]
  }
}
```

---

## 3. Troubleshooting DMS Bottlenecks (`AWS/DMS` CloudWatch Metrics)

| Symptom / Metric | Root Cause | Remediation |
|---|---|---|
| `SwapUsage` rising + task log shows `Reading from source paused` | Long-running uncommitted source transactions or high CDC volume exceeding `MemoryLimitTotal` or `MemoryKeepTime`, spilling transactions into on-disk SORTER swap files. | Upgrade to a memory-optimized `dms.r6i` / `dms.r7i` instance; increase `ChangeProcessingTuning.MemoryLimitTotal` (e.g., `4096` MB) and `MemoryKeepTime` (e.g., `240` seconds). |
| `CDCLatencyTarget` high while `CDCLatencySource` is low | Target database cannot apply changes fast enough — typically missing secondary indexes during CDC `UPDATE`/`DELETE`, single-row transactional apply, or target `IO:XactSync` latency. | Pause task and verify target primary/secondary indexes exist; enable `"BatchApplyPreserveTransaction": true` (or `"BatchApplyEnabled": true`); temporarily disable target Multi-AZ during initial catch-up. |
| `CDCLatencySource` high | DMS cannot read source redo/WAL/binlog fast enough (Oracle LogMiner bottleneck, network latency, or throttled source IOPS). | For Oracle, switch from LogMiner to **DMS Binary Reader** (`useBfile=true;useLogminerReader=N`); ensure DMS is in the same VPC/AZ or connected via high-bandwidth Direct Connect. |
| PostgreSQL source storage fills up during DMS failure | Open logical replication slot (`dms_*`) retains WAL segments indefinitely when a DMS task stops or fails. | Monitor `OldestReplicationSlotLag` and `TransactionLogsDiskUsage` in CloudWatch; drop orphaned replication slots via `SELECT pg_drop_replication_slot('slot_name');` if a task is permanently retired. |
