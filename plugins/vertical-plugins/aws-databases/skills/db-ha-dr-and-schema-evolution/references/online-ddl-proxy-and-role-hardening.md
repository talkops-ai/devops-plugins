# Online DDL Playbooks, RDS Proxy Unpinning, Aurora Fast Cloning & MCP Role Hardening

## 1. Zero-Downtime Online DDL SQL Playbooks

### A. PostgreSQL Safe Online DDL Patterns

```sql
-- 1. Safe Column Addition (PostgreSQL 11+: constant default is instant metadata-only)
BEGIN;
SET LOCAL lock_timeout = '2s';
ALTER TABLE app.orders ADD COLUMN fulfillment_status TEXT DEFAULT 'PENDING';
COMMIT;

-- 2. Non-Blocking Index Creation (MUST run outside a transaction block)
SET statement_timeout = 0;
SET lock_timeout = '2s';
CREATE INDEX CONCURRENTLY idx_orders_customer_created
  ON app.orders (customer_id, created_at DESC);

-- If CREATE INDEX CONCURRENTLY fails mid-build, check for and drop INVALID indexes:
SELECT indexrelid::regclass AS invalid_index
FROM pg_index
WHERE NOT indisvalid;
-- DROP INDEX CONCURRENTLY app.idx_orders_customer_created;

-- 3. Non-Blocking Foreign Key Addition (Two-Phase NOT VALID -> VALIDATE)
BEGIN;
SET LOCAL lock_timeout = '2s';
ALTER TABLE app.order_items
  ADD CONSTRAINT fk_order_items_order_id
  FOREIGN KEY (order_id) REFERENCES app.orders (id)
  NOT VALID;
COMMIT;

-- Phase 2: Validate constraint (takes SHARE UPDATE EXCLUSIVE lock; does NOT block reads/writes)
ALTER TABLE app.order_items VALIDATE CONSTRAINT fk_order_items_order_id;

-- 4. Safe NOT NULL Enforcement on Large Existing Table (PostgreSQL 12+)
BEGIN;
SET LOCAL lock_timeout = '2s';
ALTER TABLE app.orders
  ADD CONSTRAINT chk_orders_status_not_null
  CHECK (fulfillment_status IS NOT NULL) NOT VALID;
COMMIT;

ALTER TABLE app.orders VALIDATE CONSTRAINT chk_orders_status_not_null;

BEGIN;
SET LOCAL lock_timeout = '2s';
ALTER TABLE app.orders ALTER COLUMN fulfillment_status SET NOT NULL;
ALTER TABLE app.orders DROP CONSTRAINT chk_orders_status_not_null;
COMMIT;
```

### B. MySQL / Aurora MySQL Safe Online DDL Patterns

```sql
-- 1. Instant Column Addition (MySQL 8.0+ / Aurora MySQL 3.x)
SET SESSION lock_wait_timeout = 3;
ALTER TABLE orders
  ADD COLUMN fulfillment_status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
  ALGORITHM=INSTANT;

-- 2. Online Secondary Index Creation without Blocking DML
SET SESSION lock_wait_timeout = 3;
ALTER TABLE orders
  ADD INDEX idx_orders_customer_created (customer_id, created_at),
  ALGORITHM=INPLACE,
  LOCK=NONE;
```

---

## 2. Amazon RDS Proxy Connection Pinning Prevention

### Why Pinning Happens & How to Fix It per Driver

| Runtime / Driver | Default Pinning Trap | Production Unpinning Configuration |
|---|---|---|
| **Node.js `mysql2`** | `conn.execute(sql, params)` creates and caches server-side prepared statements (`COM_STMT_PREPARE`), pinning the physical connection for the lifetime of the client session. | Use `conn.query(sql, params)` (client-side parameter escaping), or call `conn.unprepare(sql)` immediately after execution. In AWS Lambda, configure `mysql2.createPool({ connectionLimit: 1, maxIdle: 1 })` outside the handler. |
| **Python `PyMySQL` / `SQLAlchemy`** | Setting session variables per connection (`SET SESSION sql_mode=...`, `SET time_zone=...`). | Move static session initialization into the **RDS Proxy Target Group `InitQuery`** via `aws rds modify-db-proxy-target-group --connection-pool-config InitQuery="SET time_zone='+00:00'"`. |
| **PostgreSQL `pg` / `psycopg3` / `asyncpg`** | Using `SET search_path = ...` or `SET statement_timeout = ...` at session scope, or unnamed prepared statement caching. | Always use transaction-scoped **`SET LOCAL`** (`SET LOCAL statement_timeout = '5s';` inside `BEGIN ... COMMIT`), which resets at transaction end and **never pins** RDS Proxy connections. Disable automatic prepared statement caching (`prepare_threshold=None` in `psycopg3`). |
| **Java `HikariCP` + `pgjdbc` / `mysql-connector-j`** | Large per-pod connection pool (`maximumPoolSize=20`) combined with `prepareThreshold=5`. | When fronting with RDS Proxy, reduce pod pool size (`maximumPoolSize=2` to `5`), set `prepareThreshold=0` on PostgreSQL if statement texts vary dynamically, and disable server-side prepared statements (`useServerPrepStmts=false`) on MySQL. |

### CloudWatch Check for RDS Proxy Pinning

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnectionsCurrentlySessionPinned \
  --dimensions Name=ProxyName,Value=<proxy-name> \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Average Maximum
```

---

## 3. Aurora Fast Database Cloning & Blue/Green Deployment CLI

### Zero-Copy Aurora Fast Clone (Lower-Environment Refresh / DDL Testing)

```bash
aws rds restore-db-cluster-to-point-in-time \
  --db-cluster-identifier <target-clone-cluster-id> \
  --source-db-cluster-identifier <source-prod-cluster-id> \
  --restore-type copy-on-write \
  --use-latest-restorable-time \
  --db-subnet-group-name <subnet-group> \
  --vpc-security-group-ids <sg-id> \
  --deletion-protection \
  --tags Key=created_by,Value=aws-database-engineer Key=environment,Value=staging-clone
```

*(After the clone cluster reaches `available`, attach a `db.serverless` or provisioned reader/writer instance via `aws rds create-db-instance`.)*

---

## 4. Least-Privilege Database Role Hardening for MCP Servers

To protect against SQL validation bypasses (GHSA-fph8-pg5w-78fv, GHSA-pwr4-hmph-gqgc, GHSA-x25m-ph3m-3r9q, CVE-2026-107322) and indirect data exfiltration via Foreign Data Wrappers (`postgres_fdw`):

### A. PostgreSQL Least-Privilege MCP Role (`mcp_inspector`)

```sql
-- 1. Create dedicated read-only role with no superuser or role-creation privileges
CREATE ROLE mcp_inspector WITH
  LOGIN
  PASSWORD '<rotated- via-secrets-manager>'
  NOSUPERUSER
  NOCREATEDB
  NOCREATEROLE
  NOINHERIT
  NOREPLICATION
  CONNECTION LIMIT 5;

-- 2. Enforce read-only transactions and strict statement timeouts at the role level
ALTER ROLE mcp_inspector SET default_transaction_read_only = on;
ALTER ROLE mcp_inspector SET statement_timeout = '15s';
ALTER ROLE mcp_inspector SET lock_timeout = '2s';
ALTER ROLE mcp_inspector SET idle_in_transaction_session_timeout = '15s';

-- 3. Explicitly revoke dangerous server-level roles and FDW access
REVOKE rds_superuser FROM mcp_inspector;
REVOKE pg_read_server_files, pg_write_server_files, pg_execute_server_program FROM mcp_inspector;

-- 4. Grant read-only access strictly to target application schemas (exclude credential tables)
GRANT CONNECT ON DATABASE app_db TO mcp_inspector;
GRANT USAGE ON SCHEMA app TO mcp_inspector;
GRANT SELECT ON ALL TABLES IN SCHEMA app TO mcp_inspector;
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT SELECT ON TABLES TO mcp_inspector;
```

**Verification Query (Run Before Approving MCP Connection):**

```sql
SELECT
  r.rolname,
  r.rolsuper,
  r.rolconfig,
  ARRAY(
    SELECT b.rolname
    FROM pg_auth_members m
    JOIN pg_roles b ON (m.roleid = b.oid)
    WHERE m.member = r.oid
  ) AS member_of_roles
FROM pg_roles r
WHERE r.rolname = 'mcp_inspector';
```

### B. MySQL / Aurora MySQL Least-Privilege MCP User (`mcp_inspector`)

```sql
CREATE USER 'mcp_inspector'@'%' IDENTIFIED BY '<rotated-via-secrets-manager>' REQUIRE SSL
  WITH MAX_USER_CONNECTIONS 5 MAX_STATEMENT_TIME 15;

GRANT SELECT, PROCESS, SHOW VIEW ON app_db.* TO 'mcp_inspector'@'%';
GRANT SELECT ON performance_schema.* TO 'mcp_inspector'@'%';
FLUSH PRIVILEGES;
```
