---
name: db-ha-dr-and-schema-evolution
description: >-
  Designs multi-AZ and cross-region HA/DR topologies mapped to RPO/RTO targets, backup and PITR
  validation, zero-copy Aurora Fast Database Cloning, RDS Blue/Green deployments, Amazon RDS Proxy
  connection multiplexing and connection pinning remediation, least-privilege database role
  security hardening for MCP/applications, and lock-free online DDL schema evolution.
version: 1
---

# Database HA/DR, RDS Proxy Multiplexing, Role Hardening & Online Schema Evolution

Use this skill for cross-engine **Day-2 architecture and operational hygiene**: designing Multi-AZ or multi-region High Availability and Disaster Recovery (HA/DR) topologies against explicit RPO/RTO targets, refreshing lower environments via Aurora Fast Cloning, preventing connection pinning on Amazon RDS Proxy, hardening database roles for data-plane MCP servers, and executing zero-downtime lock-free DDL migrations.

## Reference Library (Load On-Demand)

- **[references/online-ddl-proxy-and-role-hardening.md](references/online-ddl-proxy-and-role-hardening.md)** — Load for runnable online DDL migration playbooks (PostgreSQL `CONCURRENTLY` / `NOT VALID` + `VALIDATE CONSTRAINT`, MySQL `ALGORITHM=INSTANT` / Blue-Green, Aurora DSQL `CREATE INDEX ASYNC`), driver-level RDS Proxy unpinning configurations (`mysql2`, `pg`, JDBC, `psycopg`), Aurora Fast Clone CLI commands, and least-privilege SQL scripts for `postgres` and `mysql` MCP roles.

---

## Workflow

### Step 1: Map RPO, RTO & Read-Scaling Targets to HA/DR Topology

Never select a deployment topology without mapping it to the workload's **Recovery Point Objective (RPO)**, **Recovery Time Objective (RTO)**, and **TCO**:

| Topology | Engine Scope | RPO | Typical RTO | Read Scaling & Cost Profile |
|---|---|---|---|---|
| **Single-AZ DB Instance** | RDS (all engines) | Up to last 5-min transaction log backup (PITR) | 10–30+ min (storage/instance restore) | No HA; baseline $1\times$ compute/storage cost. Dev/test only. |
| **Multi-AZ DB Instance** | RDS (all engines) | $0$ (synchronous physical block replication to standby AZ) | 60–120 sec automatic failover | Standby is **not readable**; $2\times$ instance + storage cost. |
| **Multi-AZ DB Cluster** | RDS PostgreSQL, RDS MySQL | $0$ (semi-synchronous transaction commit to at least 1 standby) | Typically $< 35$ sec | **2 readable standbys** across 3 AZs + local NVMe write cache; $\sim 2.5\text{–}3\times$ Single-AZ cost. |
| **Aurora Cluster (Multi-AZ Storage + Reader)** | Aurora PostgreSQL / MySQL | $0$ (6-way storage quorum across 3 AZs; 4/6 write quorum) | Typically $< 30$ sec (with Failover Priority Tier 0–1) | Up to 15 shared-storage Read Replicas with single-digit-ms lag; zero extra storage cost for replicas. |
| **Aurora Global Database** | Aurora PostgreSQL / MySQL | $\sim 1$ sec cross-region storage replication (or $0$ with Global Database Write Forwarding / planned switchover) | $< 1$ min cross-region promotion | Dedicated storage-layer replication across up to 5 secondary regions without impacting primary writer CPU. |
| **Aurora DSQL Multi-Region** | Aurora DSQL | $0$ (active-active strongly consistent distributed SQL) | Near-zero (no primary failover concept) | Active-active multi-region endpoints with Optimistic Concurrency Control (OCC). |
| **DynamoDB Global Tables** | Amazon DynamoDB | Sub-second (eventual) or $0$ (Multi-Region Strong Consistency) | Near-zero active-active routing | Replicates writes automatically across regions; pay for replicated write units (`rWCU`). |

- **Lower-Environment Refresh (Aurora Fast Database Cloning):** To create staging, performance-test, or schema-migration dry-run environments from a multi-terabyte Aurora cluster without copying storage or paying double storage costs immediately, use `aws rds restore-db-cluster-to-point-in-time --restore-type copy-on-write --source-db-cluster-identifier <prod> --db-cluster-identifier <clone> --use-latest-restorable-time`.

### Step 2: Enforce Lock-Free Online Schema Evolution (Zero-Downtime DDL)

Never execute blocking DDL against a live production table without explicit lock guards:

1. **PostgreSQL Online DDL Rules:**
   - **Always wrap DDL in a short `lock_timeout` retry loop:** `SET lock_timeout = '2s';` before any `ALTER TABLE`. Without `lock_timeout`, an `ACCESS EXCLUSIVE` lock request queues behind a single long-running `SELECT` and blocks all subsequent reads and writes on the table.
   - **Index Creation / Removal:** Always use `CREATE INDEX CONCURRENTLY` and `DROP INDEX CONCURRENTLY` (must run outside a `BEGIN ... COMMIT` transaction block).
   - **Foreign Keys & Check Constraints:** Never add a validated constraint in a single step. Run `ALTER TABLE child ADD CONSTRAINT fk_name FOREIGN KEY (col) REFERENCES parent(id) NOT VALID;` (instant metadata lock), then `ALTER TABLE child VALIDATE CONSTRAINT fk_name;` (acquires only `SHARE UPDATE EXCLUSIVE`, allowing concurrent reads and writes).
   - **Adding `NOT NULL` to an Existing Column:** On PostgreSQL 12+, add a `CHECK (col IS NOT NULL) NOT VALID`, run `VALIDATE CONSTRAINT`, then run `ALTER TABLE ... ALTER COLUMN col SET NOT NULL;` (skips full table scan), and drop the redundant check constraint.
   - **Column Type Changes or Table Rewrites:** Use the **Expand-and-Contract** pattern (add new column $\rightarrow$ dual-write via trigger/app $\rightarrow$ batched backfill $\rightarrow$ swap reads $\rightarrow$ drop old column) or **RDS Blue/Green Deployments**.
2. **MySQL / Aurora MySQL Online DDL Rules:**
   - Prefer `ALGORITHM=INSTANT` (MySQL 8.0+) for appending/dropping columns or changing enum metadata, and `ALGORITHM=INPLACE, LOCK=NONE` for secondary index builds.
   - For blocking data-type changes (e.g., `VARCHAR` to `INT`) or major version upgrades, orchestrate an **RDS / Aurora Blue/Green Deployment** (`create-blue-green-deployment` $\rightarrow$ apply DDL on Green after binlog catch-up $\rightarrow$ confirm with user before `switchover-blue-green-deployment`).
3. **Aurora DSQL Schema Evolution Rules:**
   - DSQL prohibits mixing DDL and DML in the same transaction (`0A000`) and allows only one DDL statement per transaction on standard paths.
   - For populated tables, use `CREATE INDEX ASYNC` so index builds run asynchronously in the background without blocking writes, and leverage native DSQL Foreign Keys (`#4565` when applicable) or application-enforced integrity with OCC retry loops (`40001`).

### Step 3: Prevent & Remediate Amazon RDS Proxy Connection Pinning

When fronting Aurora or RDS (PostgreSQL, MySQL, MariaDB, SQL Server) with **Amazon RDS Proxy** for AWS Lambda, ECS, or EKS workloads:
- Monitor CloudWatch `DatabaseConnectionsCurrentlySessionPinned` alongside `DatabaseConnectionsCurrentlyBorrowed`. If pinning approaches $100\%$, connection multiplexing is defeated.
- **Audit Application Driver Code for Pinning Triggers:**
  - **MySQL (`mysql2`, JDBC, Go `go-sql-driver/mysql`):** Allocating prepared statements (`connection.execute()` in Node.js `mysql2` caches prepared statements by default and pins every connection), setting session variables (`SET @var`, `SET SESSION`), `GET_LOCK()`, or creating temporary tables. Fix: Use `connection.query()` or explicitly `DEALLOCATE PREPARE`, configure constant session variables in the RDS Proxy `InitQuery` instead of per-request `SET` statements, and set Lambda local pool size to `max: 1`.
  - **PostgreSQL (`pg`, `psycopg`, HikariCP):** Prepared statements exceeding 16 KB, `LISTEN`/`NOTIFY`, session-level `SET` (use `SET LOCAL` inside a transaction instead, which does *not* pin the connection after commit), or temporary sequences/tables.

### Step 4: Database-Role Security Hardening for MCP & Applications

Client-side SQL validation inside MCP servers (`postgres`, `mysql`, `mssql`, `oracle`, `documentdb`) is defense-in-depth, not a security boundary (see advisories GHSA-fph8-pg5w-78fv, GHSA-pwr4-hmph-gqgc, GHSA-x25m-ph3m-3r9q, GHSA-j694-4m5j-w8hc, CVE-2026-107322). Before connecting data-plane MCP servers via `--secretManagerARN`:
- **Never connect as the cluster master user or `rds_superuser`.**
- **PostgreSQL Hardening:** Create a dedicated read-only inspection role with `ALTER ROLE mcp_inspector SET default_transaction_read_only = on;`, grant only `CONNECT`, `USAGE`, and `SELECT` on target application schemas, and verify the role holds **zero** `rds_superuser`, `pg_read_server_files`, `pg_write_server_files`, `pg_execute_server_program`, or Foreign Data Wrapper (`postgres_fdw`) / Foreign Server `USAGE` privileges (see [references/online-ddl-proxy-and-role-hardening.md](references/online-ddl-proxy-and-role-hardening.md) for the exact provisioning and verification SQL).
- **MySQL Hardening:** Create a dedicated user granted only `SELECT`, `PROCESS`, and `SHOW VIEW` with `REQUIRE SSL`, and never grant `SUPER`, `FILE`, `GRANT OPTION`, or `ADMIN` privileges.
