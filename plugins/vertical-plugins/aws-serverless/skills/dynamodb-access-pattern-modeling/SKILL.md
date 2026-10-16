---
name: dynamodb-access-pattern-modeling
description: Design, validate, cost-estimate, and generate code for Amazon DynamoDB data models and relational-to-DynamoDB migrations using aws-dynamodb-mcp (dynamodb_data_modeling, source_db_analyzer, compute_performances_and_costs, dynamodb_data_model_validation, dynamodb_data_model_schema_converter, generate_data_access_layer, generate_resources). Enforces access-pattern-first design, zero production Scans, hot-partition prevention, and CVE-2026-85654 schema sanitization.
---

# Amazon DynamoDB Access-Pattern Modeling, Validation & Migration

Architect single-table and multi-table Amazon DynamoDB schemas from application access patterns or existing relational databases (PostgreSQL, MySQL, SQL Server, Oracle) using the `aws-dynamodb-mcp` server (`awslabs.dynamodb-mcp-server>=2.1.6`).

## When to Use

- Designing a new DynamoDB schema from business requirements and query/write access patterns
- Migrating an existing relational database (PostgreSQL, MySQL, Aurora, SQL Server, Oracle) to DynamoDB (`source_db_analyzer`)
- Calculating exact RCU/WCU capacity and monthly DynamoDB storage/throughput costs (`compute_performances_and_costs`)
- Validating every read/write access pattern locally against **DynamoDB Local** (`dynamodb_data_model_validation`)
- Generating type-safe Data Access Layer (DAL) code (`generate_data_access_layer`) or AWS CDK constructs (`generate_resources`)

---

## 1. End-to-End `aws-dynamodb-mcp` Modeling Workflow

Execute these steps in order when designing or migrating a DynamoDB data model:

```
[1. Analyze Requirements / Source DB]
   ├─ Greenfield: Call `dynamodb_data_modeling` -> produce `dynamodb_requirement.md`
   └─ Migration:  Call `source_db_analyzer` (Self-Service SQL or Managed RDS Data API)
         │
         ▼
[2. Design Table & GSI Access Patterns + Calculate Costs]
   └─ Call `compute_performances_and_costs` -> produce `dynamodb_data_model.md`
         │
         ▼
[3. Validate Against DynamoDB Local (Docker/Finch/Podman)]
   └─ Call `dynamodb_data_model_validation` -> verify `dynamodb_model_validation.json`
         │
         ▼
[4. Convert & Validate Schema Artifact (with CVE-2026-85654 Sanitization)]
   ├─ Call `dynamodb_data_model_schema_converter` -> generates `schema.json`
   └─ Call `dynamodb_data_model_schema_validator` -> verifies `schema.json`
         │
         ▼
[5. Code & Infrastructure Generation]
   ├─ Call `generate_data_access_layer` (Type-safe DAL)
   └─ Call `generate_resources` (AWS CDK app)
```

### Relational Database Migration Modes (`source_db_analyzer`)
- **Self-Service Mode (Any DB: MySQL, PostgreSQL, SQL Server, Oracle — No Credentials Needed)**:
  1. Call `source_db_analyzer` with `source_db_type`, `generate_queries_only=True`, and `output_dir`.
  2. Have the user execute the generated schema/query-log inspection SQL script against their database and save the output file.
  3. Re-run `source_db_analyzer` with `query_result_file_path` pointing to the saved results.
- **Managed Mode (Aurora / RDS PostgreSQL or MySQL via RDS Data API)**:
  - Call `source_db_analyzer` with `db_cluster_arn`, `secret_arn`, `database_name`, and `aws_region` to introspect tables, indexes, foreign keys, and query performance statistics directly.

---

## 2. CRITICAL Security Guardrail: CVE-2026-85654 Schema Sanitization

Prior to version `2.1.6`, `awslabs.dynamodb-mcp-server` contained a command injection vulnerability (CVE-2026-85654) in its CDK generation pipeline when processing untrusted identifiers in `schema.json`.

**Enforce both defenses without exception:**
1. Ensure `.mcp.json` pins `"awslabs.dynamodb-mcp-server>=2.1.6"`.
2. **Pre-Generation Identifier Audit**: Before calling `dynamodb_data_model_schema_validator`, `generate_data_access_layer`, or `generate_resources`, verify that every `table_name`, `index_name`, `partition_key`, `sort_key`, and attribute identifier in `schema.json` strictly matches `^[a-zA-Z0-9_.-]+$` and contains **zero** shell metacharacters (`;`, `|`, `&`, `$`, `` ` ``, `(`, `)`, quotes, or newlines).

---

## 3. Core DynamoDB Architectural Rules

### Rule 1: Zero Production `Scan` Operations
Never design an API endpoint or synchronous workflow that relies on `dynamodb:Scan`. `Scan` reads every item in the table, consumes massive RCUs, and degrades linearly as table size grows. Every read access pattern MUST map to either:
- `GetItem` / `BatchGetItem` (exact `PK` + `SK` lookup)
- `Query` on the Base Table (`PK = :pk` with optional `SK` condition: `=`, `<`, `<=`, `>`, `>=`, `BETWEEN`, or `begins_with`)
- `Query` on a Global Secondary Index (GSI)

### Rule 2: Single-Table vs. Multi-Table Selection
| Scenario | Recommendation | Rationale |
|---|---|---|
| Tightly coupled domain entities fetched together in 1 request (e.g., `Order` + `OrderItems` via `PK=ORDER#123`) | **Single-Table Design** (or cohesive domain table) | Retrieves parent + child items in a single `Query` (`PK = :orderId`) with 1 network round-trip |
| Unrelated bounded contexts, independent microservice teams, or vastly different compliance/backup lifecycles | **Separate Domain Tables** | Simplifies IAM least-privilege boundaries, CloudWatch metrics, and export/analytics pipelines |

### Rule 3: Composite Sort Keys & Hierarchical Queries
Encode multi-attribute hierarchies into the Sort Key (`SK`) delimited by `#` so `begins_with` and `BETWEEN` can filter multiple dimensions in a single `Query`:
- **Example**: `PK = TENANT#<tenant_id>`, `SK = STATUS#<status>#DATE#<iso8601_date>#ORDER#<order_id>`
  - Query all orders for tenant: `PK = TENANT#t1 AND begins_with(SK, "STATUS#")`
  - Query all `PENDING` orders for tenant: `PK = TENANT#t1 AND begins_with(SK, "STATUS#PENDING#")`
  - Query `PENDING` orders in a date range: `PK = TENANT#t1 AND SK BETWEEN "STATUS#PENDING#DATE#2026-01-01" AND "STATUS#PENDING#DATE#2026-01-31~"`

### Rule 4: Sparse Global Secondary Indexes (Cost Optimization)
DynamoDB only indexes items into a GSI if the item actually contains the GSI's Partition Key and Sort Key attributes.
- **Pattern**: To query only active/unprocessed jobs (< 1% of total items), set attribute `GSI1PK = "UNPROCESSED"` only on active items and `REMOVE GSI1PK` once processed. This cuts GSI write and storage costs by up to 99%.

### Rule 5: Hot Partition Prevention & Write Sharding
A single DynamoDB physical partition supports up to **1,000 WCU/sec** and **3,000 RCU/sec**.
- Never use a low-cardinality attribute (like `status = "ACTIVE"` or `date = "2026-10-15"`) as a Partition Key (`PK`) on high-write tables.
- If a single logical key exceeds 1,000 WCU/sec, append a deterministic hash suffix or random shard number (`0..N-1`): `PK = METRIC#2026-10-15#SHARD#<0..9>` and scatter-gather read across the `N` shards in parallel.

### Rule 6: Production Table Hardening Checklist
Every production `AWS::DynamoDB::Table` resource must configure:
- **`BillingMode: PAY_PER_REQUEST`** (On-Demand) with **`OnDemandThroughput`** (`MaxReadRequestUnits` / `MaxWriteRequestUnits`) to cap runaway traffic, OR `PROVISIONED` with Application Auto Scaling for predictable high-volume workloads.
- **`PointInTimeRecoverySpecification: { PointInTimeRecoveryEnabled: true }`** (protects against accidental deletes/corruptions for 35 days).
- **`SSESpecification: { SSEEnabled: true }`** (encryption at rest).
- **`TimeToLiveSpecification`** (`Enabled: true`, `AttributeName: expiresAt` stored as Unix epoch seconds—free automatic item expiration that consumes **0 WCUs**).
- **`DeletionProtectionEnabled: true`** on production environments.
