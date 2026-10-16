# RDS & Amazon Aurora Optimization (Right-Sizing & I/O-Optimized Break-Even)

## Compute Optimizer & Two-Key CloudWatch Validation for RDS

Supported engines: MySQL, PostgreSQL, MariaDB, Aurora MySQL, Aurora PostgreSQL.

**Metrics analyzed (`AWS/RDS`):** `CPUUtilization` (`p95`, `p99`, `Maximum`), `FreeableMemory` (`Minimum`, `p5`), `DatabaseConnections` (`Maximum`), `NetworkReceiveThroughput`/`NetworkTransmitThroughput` (`Maximum`), `ReadIOPS`/`WriteIOPS` (`p95`, `Maximum`, `Sum`), `ReadThroughput`/`WriteThroughput`, `BufferCacheHitRatio` (`Minimum`), `EBSIOBalance%`/`EBSByteBalance%`, `FreeStorageSpace`. With Performance Insights: `DBLoad`, `os.swap.in`/`out`.

### Two-Key Telemetry Thresholds (`cloudwatch:get_metric_data` over 14–30 Days)
- **Safe to downsize instance class when:**
  - `CPUUtilization` P95 `< 35%` and P99 `< 55%`
  - `FreeableMemory` Minimum exceeds **35% of the target (smaller) instance's total RAM**
  - `BufferCacheHitRatio` remains `> 98%`
  - `DatabaseConnections` Maximum `< 50%` of target instance `max_connections`
- **Hold / Block downsizing when:**
  - `FreeableMemory` drops below 20% of target instance RAM (triggers buffer pool eviction, disk read storms, and swap thrashing)
  - Peak `ReadIOPS + WriteIOPS` or `ReadThroughput + WriteThroughput` exceeds the target instance class's EBS bandwidth cap

**Finding classifications:** `Overprovisioned`, `Underprovisioned`, `Optimized`.

**Finding reason codes:** `CPUOverprovisioned`, `CPUUnderprovisioned`, `MemoryUnderprovisioned` (high swap/OOM), `NetworkBandwidthOverprovisioned`/`Underprovisioned`, `EBSThroughputOverprovisioned`/`Underprovisioned`, `EBSIOPSOverprovisioned`/`Underprovisioned`, `NewGenerationAvailable`, `NewEngineVersionAvailable`.

**Storage findings:** `EBSVolumeAllocatedStorageUnderprovisioned`, `EBSVolumeIOPSOverprovisioned`, `EBSVolumeThroughputOverprovisioned`, `NewGenerationStorageTypeAvailable` (`gp2` → `gp3`).

```bash
aws compute-optimizer get-rds-database-recommendations \
  --filters Name=Finding,Values=Overprovisioned
```

---

## Amazon Aurora: Standard vs. Aurora I/O-Optimized (The 25% Break-Even Rule)

Aurora clusters offer two storage configurations per cluster:
1. **Aurora Standard:** Base compute rate + **$0.10/GB-month** storage + **$0.20 per 1 million I/O requests** (`Aurora:StorageIOUsage` in `us-east-1`).
2. **Aurora I/O-Optimized:** **+30% compute premium** (applies to both Provisioned instances and Serverless v2 ACUs) + **+125% storage premium ($0.225/GB-month)** + **$0.00 I/O charges**.

### Deterministic Break-Even Formula (Run via Python Script)
$$\text{Net Monthly Savings of I/O-Optimized} = \text{Cost}_{\text{IO}} - \left(0.30 \times \text{Cost}_{\text{Standard\_Compute}} + 1.25 \times \text{Cost}_{\text{Standard\_Storage}}\right)$$

- **Switch Standard → I/O-Optimized:** Only when monthly `Aurora:StorageIOUsage` spend exceeds **~25% of total Aurora cluster spend (`Compute + Storage + I/O`)**.
- **Reverse Audit (Switch I/O-Optimized → Standard to Save 15%–30%):**
  Many teams enable `Aurora I/O-Optimized` by default on low-I/O clusters and overpay **30% on compute and 125% on storage** every month!
  1. Query CloudWatch `AWS/RDS` `VolumeReadIOPs` and `VolumeWriteIOPs` (`Sum` over 30 days) for the cluster.
  2. Calculate what I/Os would cost under Standard:
     `projected_io_cost_usd = ((monthly_read_iops + monthly_write_iops) / 1_000_000.0) * 0.20`
  3. Compare against the I/O-Optimized premium currently being paid:
     `io_optimized_premium_usd = (current_compute_cost_usd * (0.30 / 1.30)) + (current_storage_cost_usd * (0.125 / 0.225))`
  4. If `projected_io_cost_usd < io_optimized_premium_usd`, switching back to **Aurora Standard** is an online operation (allowed once every 30 days) that immediately saves `io_optimized_premium_usd - projected_io_cost_usd`!

---

## AWS Graviton (`db.r7g` / `db.m7g` / `db.r8g`) & Multi-AZ Optimization

1. **Managed Graviton Upgrade (Zero Application Code Changes):**
   - RDS and Aurora are fully managed services—migrating from `db.m5`/`db.m6i` to `db.m7g` or `db.r5`/`db.r6i` to `db.r7g`/`db.r8g` requires **zero application binary changes** and delivers up to **20% lower hourly price** and up to **30%–40% better price-performance**.
2. **Multi-AZ in Non-Production:**
   - Converting `dev`, `test`, and `staging` RDS instances from `Multi-AZ` to `Single-AZ` cuts compute and storage costs by **50%**.
   - Stopping non-production RDS instances or pausing Aurora Serverless v2 (`MinCapacity=0.0`) outside business hours saves **65%–70%** of compute hours.
3. **Extended Support Fees (`RDS:ExtendedSupport`):**
   - Check Cost Explorer `USAGE_TYPE` for `*ExtendedSupport*` (e.g., MySQL 5.7, PostgreSQL 11/12, Aurora legacy versions). Extended Support adds **$0.10 to $0.20 per vCPU-hour** (often **+100% to +200% compute surcharge**!). Prioritize engine version upgrades to eliminate Extended Support surcharges.

## Read Replica & Storage Considerations

- Recommendations are synchronized with writer for promotion tiers ≤ 1
- Smaller replica instances may increase replication lag (`AuroraReplicaLag` / `ReplicaLag`)
- Allocated RDS storage can only be increased, not decreased without a logical dump/DMS migration; however, migrating RDS storage from `gp2` or `io1` to **`gp3`** is supported online

## Gotchas

- DB instance class modifications typically require a brief failover/downtime (1–5 min with Multi-AZ; 5–10 min Single-AZ)
- Parameter group values (`shared_buffers`, `innodb_buffer_pool_size`, `max_connections`) scale with instance RAM — verify custom static values before downsizing
- Always take a manual snapshot before implementing changes
- Performance risk scale: 0-1 Very Low, >1-2 Low, >2-3 Medium, >3-4 High
