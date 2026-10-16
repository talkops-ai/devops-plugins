---
name: dms-data-migration-execution
description: >-
  Architects, configures, optimizes, and troubleshoots AWS Database Migration Service (DMS) data
  migration tasks (Full Load, Change Data Capture / CDC, and Full Load + CDC). Activate after or
  alongside dms-schema-conversion whenever migrating data between operational databases, sizing DMS
  replication instances, configuring Limited/Inline/Full LOB settings, tuning parallel table loads,
  or debugging DMS swap exhaustion and CDC replication latency.
version: 1
---

# AWS DMS Data Migration Execution & Tuning

Use this skill to architect, right-size, execute, and troubleshoot **operational database migrations** using AWS Database Migration Service (DMS) across **Full Load**, **Change Data Capture (CDC)**, and **Full Load + CDC** modes. Pair with `dms-schema-conversion` when migrating across heterogeneous engines (such as Oracle or SQL Server to Aurora PostgreSQL/MySQL).

> **Scope Boundary with `aws-data-engineer`:** This skill governs operational database-to-database migrations (OLTP/NoSQL cutovers and homogeneous/heterogeneous engine migrations). For continuous analytical CDC extraction into Amazon S3 Parquet or Apache Iceberg / S3 Tables data lakes, hand off to `aws-data-engineer` (`ingesting-streaming-and-cdc-data`).

## Reference Library (Load On-Demand)

- **[references/dms-task-and-lob-tuning.md](references/dms-task-and-lob-tuning.md)** — Load for source LOB discovery SQL queries (Oracle, PostgreSQL, MySQL, SQL Server), `table-settings` parallel-load JSON rules (`partitions-auto`, `subpartitions-auto`, `ranges` with `ntile`), CloudWatch DMS metric thresholds (`CDCLatencySource`, `CDCLatencyTarget`, `SwapUsage`), and SORTER swap-spill remediation.

---

## Workflow

### Step 1: Pre-Migration Source & Target Readiness Audit

1. **Verify CDC Prerequisites on Source:**
   - **PostgreSQL:** `wal_level = logical` (`rds.logical_replication = 1` on RDS/Aurora), sufficient `max_replication_slots` and `max_wal_senders`, and `REPLICA IDENTITY FULL` on tables without primary keys.
   - **MySQL / MariaDB:** `binlog_format = ROW`, `binlog_row_image = FULL`, automated backups enabled, and binary log retention $\ge 24$ hours (`CALL mysql.rds_set_configuration('binlog retention hours', 24);`).
   - **Oracle:** `ARCHIVELOG` mode enabled; database-level minimal supplemental logging plus primary-key/unique-index supplemental logging (`rdsadmin.rdsadmin_util.alter_supplemental_logging`).
   - **SQL Server:** MS-CDC or transactional replication enabled (`exec msdb.dbo.rds_cdc_enable_db '<db_name>'` on RDS SQL Server) with full backup retention protecting active LSNs.

2. **Analyze Large Object (LOB) Distribution on Source:**
   Never guess LOB settings. Run or provide the diagnostic queries on the source database (see [references/dms-task-and-lob-tuning.md](references/dms-task-and-lob-tuning.md)):
   - Identify LOB columns (`BLOB`, `CLOB`, `NCLOB`, `TEXT`, `MEDIUMTEXT`, `LONGTEXT`, `BYTEA`, `JSONB`, `VARCHAR(MAX)`, `NVARCHAR(MAX)`).
   - Measure maximum and p95 size in KB per column: `SELECT MAX(LENGTH(col))/1024.0 FROM schema.table;` (or `MAX(DBMS_LOB.GETLENGTH(col)/1024)` in Oracle).
   - **Select LOB Mode Deterministically:**
     - **All LOBs $< 64\text{ KB}$ ($< 32\text{ KB}$ on Oracle source):** Use **Limited LOB Mode** (`"SupportLobs": true, "LimitedSizeLobMode": true, "FullLobMode": false, "LobMaxSize": <calculated_kb>`). Calculate `LobMaxSize` using:
       $$\text{Total LOB Size (KB)} = \left(\frac{\sum \text{Max Column Sizes in Bytes}}{1024}\right) + 10\% \text{ buffer}$$
       Limited LOB Mode treats LOBs as inline VARCHARs, pre-allocates memory, and loads in bulk — substantially faster than Full LOB Mode.
     - **Skewed LOB Distribution (e.g., $>80\%$ under $32\text{ KB}$, outliers $> 1\text{ MB}$):** Use **Inline LOB Mode** (`"SupportLobs": true, "FullLobMode": true, "InlineLobMaxSize": 32, "LimitedSizeLobMode": false`). Transfers small LOBs inline at high speed and falls back to piecewise Full LOB lookup only for large outliers. Requires a Primary Key or Unique Index on the table.
     - **Uniformly Huge LOBs ($> 100\text{ MB}$):** Use **Full LOB Mode** with tuned `"LobChunkSize": 64` and isolate the LOB-heavy table into its own dedicated DMS replication task so it does not block standard tables.

### Step 2: Replication Instance Sizing & Network Topology

- **Co-locate in Target AZ:** Provision the DMS Replication Instance in the **same AWS Region and Availability Zone (AZ)** as the target RDS/Aurora writer instance to eliminate cross-AZ network latency during high-volume writes.
- **Instance Family Selection:**
  - **Compute-Optimized (`dms.c6i.*` / `dms.c7i.*`):** Best for CPU-bound homogeneous Full Loads with minimal ongoing CDC state.
  - **Memory-Optimized (`dms.r6i.*` / `dms.r7i.*`):** Mandatory for high-concurrency CDC workloads, large uncommitted source transactions, Batch Apply, and Limited/Inline LOB pre-allocation (`LobMaxSize * CommitRate`).
- **Multi-AZ Replication Instance:** Enable `--multi-az` only during long-running production CDC phases where replication high availability is required; keep Single-AZ during initial testing to reduce cost.

### Step 3: Optimize Full Load + CDC Task Settings JSON

Generate the DMS Task Settings JSON with explicit performance, LOB, and memory parameters:

```json
{
  "TargetMetadata": {
    "TargetSchema": "",
    "SupportLobs": true,
    "FullLobMode": true,
    "InlineLobMaxSize": 32,
    "LimitedSizeLobMode": false,
    "LobChunkSize": 64,
    "ParallelLoadThreads": 0,
    "ParallelLoadBufferSize": 0
  },
  "FullLoadSettings": {
    "TargetTablePrepMode": "DROP_AND_CREATE",
    "CreatePkAfterFullLoad": true,
    "StopTaskCachedChangesApplied": false,
    "StopTaskCachedChangesNotApplied": true,
    "MaxFullLoadSubTasks": 16,
    "TransactionConsistencyTimeout": 600,
    "CommitRate": 25000
  },
  "ChangeProcessingTuning": {
    "BatchApplyPreserveTransaction": true,
    "BatchApplyTimeoutMin": 1,
    "BatchApplyTimeoutMax": 30,
    "BatchApplyMemoryLimit": 500,
    "BatchSplitSize": 0,
    "MinTransactionSize": 1000,
    "CommitTimeout": 1,
    "MemoryLimitTotal": 2048,
    "MemoryKeepTime": 120,
    "StatementCacheSize": 50
  },
  "ValidationSettings": {
    "EnableValidation": true,
    "ThreadCount": 5
  }
}
```

- **Scale `MaxFullLoadSubTasks`:** Increase from the default of `8` up to `16–49` concurrent tables when the replication instance has $\ge 8$ vCPUs and the source can sustain parallel reads.
- **Large Table Parallel Segmentation:** For multi-hundred-million-row tables, add a `table-settings` rule with `"parallel-load"`: use `"type": "partitions-auto"` (or `"subpartitions-auto"`) for source-partitioned tables, or `"type": "ranges"` with `ntile` boundary values for unpartitioned tables (see [references/dms-task-and-lob-tuning.md](references/dms-task-and-lob-tuning.md)).

### Step 4: Target RDS Staging, Index Building & Cutover Protocol

1. **Before Full Load:** On the target RDS/Aurora instance, temporarily disable Multi-AZ, disable foreign keys and triggers, and omit secondary indexes so Full Load writes sequentially without index maintenance overhead.
2. **Pause After Full Load (`"StopTaskCachedChangesNotApplied": true`):** Pause the DMS task immediately after Full Load completes and *before* applying cached CDC changes. **Create all Primary Keys and Secondary Indexes on the target database now.** Without secondary indexes, applying CDC `UPDATE` and `DELETE` events triggers full-table scans on the target, causing `CDCLatencyTarget` to skyrocket.
3. **Resume CDC & Validate Cutover:** Resume the task (`start-replication-task --start-replication-task-type resume-processing`) with Batch Apply and Data Validation enabled. Monitor `CDCLatencySource` and `CDCLatencyTarget` via `cloudwatch` until lag reaches $< 5$ seconds, re-enable Multi-AZ, re-enable foreign keys/triggers and reset sequences during the cutover window, and switch application endpoints.
