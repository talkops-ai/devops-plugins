---
name: aws-stateful-data-and-caching-platform
description: Designs, provisions, secures, and troubleshoots platform stateful data and caching layers across Amazon DynamoDB (tables, GSIs, streams, capacity modes), Amazon ElastiCache and MemoryDB (Valkey, Memcached), and Amazon Aurora/RDS (PostgreSQL, MySQL, Serverless v2, RDS Proxy) with strict non-superuser guardrails.
metadata:
  version: "2.0"
---

# AWS Stateful Data and Caching Platform Engineering

## Purpose

Platform engineers own the reliability, network isolation, connection pooling, encryption, backup durability, and IaC lifecycle of the stateful data and caching tiers that back containerized and serverless workloads. This skill provides production-ready platform patterns for **Amazon DynamoDB**, **Amazon ElastiCache / MemoryDB (Valkey & Memcached)**, and **Amazon Aurora / RDS (PostgreSQL & MySQL)**, and integrates with the optional stateful data MCP profile (`mcp.data-extensions.json`: `dynamodb`, `elasticache`, and `postgres` with `--privilege_check enforce`).

---

## 1. Platform Data & Caching Selection Matrix

| Workload Pattern | Recommended AWS Service | Platform Tiering (`dev`/`qa` vs `prod`) |
|---|---|---|
| **Single-digit ms key-value / document lookups, event-driven state, high-scale serverless APIs** | **Amazon DynamoDB** (+ DAX or ElastiCache Valkey if sub-millisecond read caching is needed) | `dev`/`qa`: `PAY_PER_REQUEST` (On-Demand) with `MaxRequestUnits` cap; `prod`: `PAY_PER_REQUEST` for spiky traffic or `PROVISIONED` with Application Auto Scaling for steady predictable traffic + **Point-in-Time Recovery (PITR)** + `DeletionProtectionEnabled: true`. |
| **Relational OLTP (PostgreSQL / MySQL) with ACID transactions, joins, and extensions (`pgvector`)** | **Amazon Aurora PostgreSQL / MySQL** (+ **Amazon RDS Proxy** for Lambda/ECS/EKS connection pooling) | `dev`/`qa`: **Aurora Serverless v2** (`MinCapacity: 0` or `0.5` ACU, Single-AZ); `prod`: Multi-AZ Aurora Cluster (Writer + 1–2 Readers across AZs, `Serverless v2` or Graviton `db.r7g`/`db.r8g` instances, `StorageEncrypted: true`, `DeletionProtection: true`, **Aurora I/O-Optimized** when I/O > 25% of DB cost). |
| **Low-latency in-memory cache, session store, rate limiting, pub/sub, distributed locks, leaderboards** | **Amazon ElastiCache for Valkey** (or **MemoryDB for Valkey** when durable multi-AZ transaction log persistence is required) | Prefer **Valkey** over legacy Redis OSS (drop-in wire-compatible, open-source, **20% lower price on ElastiCache Serverless and node-based**). `dev`/`qa`: ElastiCache Serverless for Valkey or single `cache.t4g.micro`; `prod`: Multi-AZ Replication Group with `AutomaticFailoverEnabled: true`, `MultiAZEnabled: true`, `TransitEncryptionEnabled: true`, `AtRestEncryptionEnabled: true`. |
| **Simple multi-threaded transient object/fragment caching without persistence or complex data structures** | **Amazon ElastiCache for Memcached** | Scale horizontally across Graviton `cache.m7g` / `cache.r7g` nodes with Auto Discovery enabled and `TransitEncryptionEnabled: true`. |

---

## 2. Amazon DynamoDB Platform Engineering Guardrails

1. **Partition Key & GSI Architecture**:
   - Design high-cardinality partition keys (`PK`) to prevent hot-partition throttling (`1,000 WCU` / `3,000 RCU` per physical partition).
   - Project only required attributes (`INCLUDE` or `KEYS_ONLY`) on Global Secondary Indexes (GSIs) when item payloads are large to avoid doubling write amplification costs.
   - Monitor `OnlineIndexPercentageProgress` and `ThrottledPutRecordCount` on GSIs—remember that **GSI write throttling throttles base table writes**!
2. **Resilience & Lifecycle Controls**:
   - Enable `PointInTimeRecoverySpecification: { PointInTimeRecoveryEnabled: true }` (35-day continuous backup) and `DeletionProtectionEnabled: true` on all production tables.
   - Configure native `TimeToLiveSpecification` (TTL) to expire ephemeral session/idempotency records at `$0.00` write cost instead of running batch `DeleteItem` jobs.
   - Route DynamoDB traffic from VPC-attached compute over the **free S3/DynamoDB VPC Gateway Endpoint (`$0.00`)**.
3. **CVE-2026-85654 Schema Sanitization & Read-Only MCP Safety**:
   - When using the `dynamodb` MCP server (`awslabs.dynamodb-mcp-server>=2.1.6` with `DDB-MCP-READONLY=true`), validate that every table name, index name, and attribute identifier in `schema.json` matches `^[a-zA-Z0-9_.-]+$` with zero shell metacharacters before invoking code/CDK generators.

---

## 3. Amazon ElastiCache (Valkey / Memcached) Platform Engineering Guardrails

1. **Valkey First & Memory Eviction Policy**:
   - Default new cache clusters to **Valkey 7.2 / 8.0+**.
   - Explicitly select the `maxmemory-policy` parameter group setting based on workload semantics:
     - Pure cache with TTLs: `volatile-lru` or `volatile-lfu`.
     - General LRU cache without strict TTLs: `allkeys-lru` or `allkeys-lfu`.
     - Queue / distributed lock / rate-limiter state where silent eviction corrupts state: `noeviction` (paired with an alarm on `DatabaseMemoryUsagePercentage > 80%`).
2. **Network & Security Hardening**:
   - Deploy ElastiCache in **isolated/private subnets** (`AWS::ElastiCache::SubnetGroup`) with Security Groups allowing TCP `6379` (Valkey) or `11211` (Memcached) **only** from the application compute Security Group.
   - Enforce `TransitEncryptionEnabled: true` (TLS), `AtRestEncryptionEnabled: true` (KMS), and **IAM Authentication** (`AuthToken` / IAM user group) or Secrets Manager rotation.
3. **Day-2 Observability Alarms**:
   - Wire CloudWatch alarms on `EngineCPUUtilization > 75%` (Valkey core command execution is primarily single-threaded per shard), `DatabaseMemoryUsagePercentage > 80%`, `SwapUsage > 50 MB`, `Evictions`, and `CurrConnections`.

---

## 4. Amazon Aurora & RDS Platform Engineering Guardrails

1. **Zero-Plaintext Credentials & RDS Proxy Connection Pooling**:
   - Set `ManageMasterUserPassword: true` (with `MasterUserSecret.KmsKeyId`) on `AWS::RDS::DBCluster` / `AWS::RDS::DBInstance` so AWS Secrets Manager automatically generates and rotates the master password without the secret ever entering CloudFormation state or git.
   - When serverless functions (Lambda) or high-replica container fleets (ECS/EKS) connect to Aurora/RDS, provision **Amazon RDS Proxy** (`RequireTLS: true`, `IAMAuth: REQUIRED` or Secrets Manager pool) to multiplex connections, prevent `FATAL: remaining connection slots are reserved for non-replication superuser connections`, and reduce Multi-AZ failover times by up to 66%.
2. **Non-Superuser Runtime & MCP Guardrails (`--privilege_check enforce`)**:
   - Application workloads and the optional `postgres` MCP server (`awslabs.postgres-mcp-server`) must **never** connect as `postgres` / `rds_superuser` or a role with `SUPERUSER` or `BYPASSRLS` attributes.
   - Configure the `postgres` MCP server with `--privilege_check enforce` and `--readonly True`, and create a dedicated least-privilege database role (`GRANT pg_read_all_data TO app_readonly; GRANT rds_iam TO app_readonly;`).
3. **Zero-Downtime Maintenance & Disaster Recovery**:
   - Use **RDS/Aurora Blue/Green Deployments** for major engine version upgrades and schema changes with sub-minute switchover.
   - Configure `BackupRetentionPeriod: 14–35` days, `CopyTagsToSnapshot: true`, `DeletionPolicy: Snapshot` / `Retain`, and **Performance Insights** (`EnablePerformanceInsights: true`) for wait-event bottleneck triage.
   - Hand off deep SQL query plan tuning, heterogeneous Oracle/SQL Server DMS migrations, or specialized engines (Neptune, DocumentDB, Keyspaces) to `aws-database-engineer`.
