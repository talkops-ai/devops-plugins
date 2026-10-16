---
name: serverless-relational-aurora-dsql
description: Architect and implement serverless relational SQL databases with Amazon Aurora DSQL and Aurora Serverless v2 (RDS Data API / RDS Proxy). Covers Aurora DSQL PostgreSQL compatibility constraints, Optimistic Concurrency Control (OCC SQLSTATE 40001 retry patterns), IAM token authentication, CREATE INDEX ASYNC, single-DDL-per-transaction rules, transaction limits (3,000 rows / 10 MiB), and multi-tenant isolation.
---

# Serverless Relational SQL: Amazon Aurora DSQL & Aurora Serverless v2

Build relational SQL workloads for AWS Lambda without TCP connection-pool exhaustion using **Amazon Aurora DSQL** (serverless distributed SQL) or **Amazon Aurora Serverless v2** with **RDS Data API / RDS Proxy**.

## When to Use

- Building serverless applications that require strict ACID relational SQL transactions, complex JOINs, and scale-to-zero economics without managing connection pools
- Writing Python (`psycopg` / `asyncpg`), Node.js (`pg` / Drizzle / Prisma), or Go (`pgx`) Lambda handlers against **Amazon Aurora DSQL**
- Migrating standard PostgreSQL schemas or ORMs to Aurora DSQL and resolving DDL, index, or Optimistic Concurrency Control (`SQLSTATE 40001`) errors
- Connecting Lambda to **Aurora Serverless v2** (when `pgvector`, PostGIS, foreign keys, or triggers are required) via **RDS Data API** or **RDS Proxy**

---

## 1. Aurora DSQL vs. Aurora Serverless v2 Selection Matrix

| Dimension | Amazon Aurora DSQL | Aurora Serverless v2 (+ RDS Data API / RDS Proxy) |
|---|---|---|
| **Architecture** | Serverless active-active distributed SQL (no instances to size or patch) | Auto-scaling ACU cluster (`0` or `0.5` to `256` ACUs) |
| **Connection Management** | Native distributed query routing + IAM auth; handles massive Lambda bursts | Requires **RDS Data API** (HTTP) or **RDS Proxy** (VPC TCP multiplexing) to avoid `FATAL: remaining connection slots are reserved` |
| **Concurrency Control** | **Optimistic Concurrency Control (OCC)** — no blocking row locks; conflicts return `SQLSTATE 40001` at commit | Traditional pessimistic locking (`SELECT ... FOR UPDATE`, row/table locks) |
| **PostgreSQL Extensions & Features** | Core SQL, JOINs, CTEs, Window functions, JSONB (no FKs, triggers, `SERIAL`, or extensions) | Full PostgreSQL/MySQL compatibility (`pgvector`, PostGIS, triggers, FKs, stored procedures) |
| **Multi-Region Active-Active** | Built-in strong consistency across regions (`99.999%` SLA) | Global Database (single writer region + read replicas) |

---

## 2. Mandatory Aurora DSQL Rules & PostgreSQL Differences

Aurora DSQL speaks the PostgreSQL wire protocol, **but it is not standard PostgreSQL**. Violating these 6 rules causes immediate runtime failures:

### Rule 1: Primary Keys & Sequences (`UUID` Instead of `SERIAL`)
- `SERIAL`, `BIGSERIAL`, `GENERATED ALWAYS AS IDENTITY`, and `CREATE SEQUENCE` are **NOT supported** (monotonic sequences create distributed hot spots).
- Always use **`UUID DEFAULT gen_random_uuid()`** (or application-generated UUIDv4/UUIDv7) as the primary key:
  ```sql
  CREATE TABLE orders (
      tenant_id UUID NOT NULL,
      order_id UUID NOT NULL DEFAULT gen_random_uuid(),
      customer_email VARCHAR(255) NOT NULL,
      total_cents BIGINT NOT NULL,
      status VARCHAR(32) NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (tenant_id, order_id)
  );
  ```

### Rule 2: No Foreign Key Constraints or Triggers
- `FOREIGN KEY` / `REFERENCES` constraints, `TRIGGER`s, `TRUNCATE`, `VACUUM`, and temporary tables (`CREATE TEMP TABLE`) are **NOT supported**.
- Enforce referential integrity explicitly inside a single ACID `BEGIN ... COMMIT` transaction in your application DAL.

### Rule 3: Single DDL Statement per Transaction & No DDL+DML Mixing
- Each transaction may execute **at most ONE DDL statement** (`CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`), and **cannot combine DDL and DML** (`INSERT`/`UPDATE`/`DELETE`) in the same transaction.
- When running schema migrations, execute each DDL statement in its own auto-committed transaction.

### Rule 4: Always Use `CREATE INDEX ASYNC`
- Standard synchronous `CREATE INDEX` fails on any table that already contains rows.
- Always use **`CREATE INDEX ASYNC`** (or `CREATE UNIQUE INDEX ASYNC`) in migration scripts:
  ```sql
  CREATE INDEX ASYNC idx_orders_tenant_status ON orders (tenant_id, status, created_at);
  ```

### Rule 5: Hard Transaction Boundaries
Every Aurora DSQL transaction is subject to three hard limits:
- **Max rows modified per transaction**: **3,000 rows** (chunk bulk inserts/updates/deletes into batches of `<= 1,000` rows per transaction).
- **Max write payload per transaction**: **10 MiB**.
- **Max transaction duration**: **5 minutes (300 seconds)**.

### Rule 6: Optimistic Concurrency Control (OCC) Retry Wrapper (`SQLSTATE 40001`)
When two concurrent transactions modify the same key range, Aurora DSQL never blocks on locks—the second transaction fails with `SQLSTATE 40001` (`OC000` conflict or `OC001` schema change). Every write transaction MUST be wrapped in an exponential backoff + jitter retry loop.

---

## 3. Production Lambda + Aurora DSQL Pattern (Python `psycopg` v3 + IAM Auth)

### IAM Policy for Aurora DSQL Connection
```yaml
Policies:
  - Statement:
      - Sid: AllowAuroraDsqlConnect
        Effect: Allow
        Action:
          - dsql:DbConnect
          - dsql:DbConnectAdmin
        Resource: !Sub "arn:aws:dsql:${AWS::Region}:${AWS::AccountId}:cluster/${DsqlClusterId}"
```

### Lambda Handler with Cached IAM Token & OCC `40001` Retry Loop

```python
import os
import random
import time
import boto3
import psycopg
from psycopg.errors import SerializationFailure

CLUSTER_ENDPOINT = os.environ["DSQL_CLUSTER_ENDPOINT"]
REGION = os.environ.get("AWS_REGION", "us-east-1")
dsql_client = boto3.client("dsql", region_name=REGION)

def get_connection() -> psycopg.Connection:
    # Generate a short-lived IAM auth token (valid for 15 minutes by default)
    token = dsql_client.generate_db_connect_admin_auth_token(
        Hostname=CLUSTER_ENDPOINT,
        Region=REGION,
        ExpiresIn=900,
    )
    return psycopg.connect(
        host=CLUSTER_ENDPOINT,
        port=5432,
        dbname="postgres",
        user="admin",
        password=token,
        sslmode="require",
        connect_timeout=3,
    )

def execute_with_occ_retry(fn, max_attempts: int = 5):
    """Retry transactions that encounter Aurora DSQL OCC conflicts (SQLSTATE 40001)."""
    for attempt in range(1, max_attempts + 1):
        try:
            with get_connection() as conn:
                with conn.transaction():
                    return fn(conn)
        except SerializationFailure as exc:
            if attempt == max_attempts:
                raise
            # Full jitter exponential backoff (10ms base)
            sleep_sec = random.uniform(0.01, (2 ** attempt) * 0.02)
            time.sleep(sleep_sec)
        except psycopg.OperationalError as exc:
            # Also retry transient OC000 / OC001 SQLSTATE 40001 codes
            if getattr(exc, "sqlstate", None) == "40001" and attempt < max_attempts:
                time.sleep(random.uniform(0.01, (2 ** attempt) * 0.02))
                continue
            raise
```

---

## 4. Using the Optional `aurora-dsql` MCP Connector

When the optional `aurora-dsql` MCP connector (`awslabs.aurora-dsql-mcp-server`) is configured in `.mcp.json`:
- Use `dsql_search_documentation`, `dsql_read_documentation`, and `dsql_recommend` to verify Aurora DSQL SQL syntax and best practices.
- Use `get_schema` and `readonly_query` for non-destructive table inspection and `EXPLAIN` plan analysis.
- Gate any `transact` (DDL/DML execution) call behind explicit user confirmation.

---

## 5. Aurora Serverless v2 + RDS Data API (When Full PostgreSQL Is Required)

If the workload requires `pgvector`, PostGIS, foreign keys, or stored procedures:
1. Enable **RDS Data API** (`EnableHttpEndpoint: true`) on the `AWS::RDS::DBCluster`.
2. Invoke queries over HTTPS using `boto3.client("rds-data").execute_statement(resourceArn=..., secretArn=..., sql=..., parameters=...)` so your Lambda function **does not need to be attached to a VPC** and never exhausts PostgreSQL `max_connections`.
