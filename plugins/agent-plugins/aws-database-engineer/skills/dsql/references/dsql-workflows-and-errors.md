# Aurora DSQL — Quick Start, Performance Routing, 12 Common Workflows & Error Scenarios

> Extracted verbatim from `SKILL.md` for progressive disclosure. Relative paths (`references/...`, `scripts/...`) resolve from the skill root directory.

## Quick Start

0. **Pick a connection path:** confirm the `aurora-dsql` MCP targets your cluster; if not, use the CLI/`psql` path instead — see [Choosing How to Connect](#choosing-how-to-connect-mcp-vs-clipsql). The steps below name MCP tools; the equivalent SQL runs the same way through `psql-connect.sh --command "..."`.
1. **Explore:** Use `readonly_query` with `information_schema` to list tables. Use `get_schema` for table structure.
2. **Query:** Use `readonly_query` for SELECT queries. **MUST** include `tenant_id` in WHERE for multi-tenant apps. **MUST** build SQL with `safe_query.build()`.
3. **Schema changes:** Use `transact` with one DDL per transaction. **MUST** batch DML under 3,000 rows. **MUST** use `CREATE INDEX ASYNC` in a separate call. Use `dsql_lint` to validate first.
4. **Bulk load data:** Use `aurora-dsql-loader` for CSV/TSV/Parquet. Load [data-loading.md](references/data-loading.md) for details. Use `--dry-run` first.

---

## Performance Routing

When the user reports a performance problem, use this table to select the correct workflow:

| User signal                                                                                                             | Route to                                                                           |
| ----------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| General performance complaint, "cluster is slow", "something changed", latency regression, no specific query identified | **Workflow 12** (System Diagnostics) — observe via CloudWatch first                |
| Specific query or query_id to investigate, "explain this plan", "why is this query slow"                                | **Workflow 9** (Query Plan Explainability) — direct EXPLAIN analysis               |
| OCC conflicts, commit errors, retry storms                                                                              | **Workflow 12** (System Diagnostics) — confirm via CW metrics before investigating |
| Cost optimization, "where is compute time spent"                                                                        | **Workflow 12** (System Diagnostics) — identify top contributors first             |

**Rule:** When in doubt, start with Workflow 12. It identifies specific queries to investigate and routes to Workflow 9 with context.

---

## Common Workflows

### Workflow 1: Create Multi-Tenant Schema

1. Create tenant-owned tables with `tenant_id` using separate `transact` calls
2. Use composite tenant FKs for tenant-owned parents and ordinary FKs for shared parents
3. Create tenant and query-pattern indexes with separate `CREATE INDEX ASYNC` calls
4. Verify with `get_schema`

- MUST issue each DDL in its own transact call: `transact(["CREATE TABLE ..."])`
- MUST serialize arrays into a single-column representation — DSQL has no array column type; PREFER `JSONB` (operators work directly); MAY use `TEXT` when the column is opaque to the database; ASK the user. For `JSONB` arrays, expand at query time with `jsonb_array_elements_text(data)`

### Workflow 2: Safe Data Migration

MUST validate every DDL with `dsql_lint(fix=true)` before executing. DML does not require linting.

1. Validate DDL with `dsql_lint(sql=..., fix=true)` — handle diagnostics per [dsql-lint.md](references/dsql-lint.md)
2. Execute the reviewed `fixed_sql` when present, otherwise the reviewed source statement
3. Add column in its own `transact` call
4. Populate existing rows with UPDATE (batched under 3,000 rows)
5. Verify with readonly_query COUNT
6. Create an index if needed: validate then execute the reviewed DDL in its own `transact` call

- MUST issue each `ALTER TABLE` in its own `transact` call — DSQL rejects multi-DDL transactions with `multiple ddl statements not supported in a transaction`
- MUST add column with only name and type; apply DEFAULT via separate UPDATE
- MUST batch updates under 3,000 rows in separate transact calls

**Recovery:** Resume failed batches by filtering `WHERE new_column IS NULL`.

### Workflow 3: Bulk Data Loading

Use `aurora-dsql-loader` for CSV, TSV, or Parquet loads. MUST load [data-loading.md](references/data-loading.md) before advising on throughput or diagnosing slow loads.

1. Validate with `--dry-run` first
2. Run with `--manifest-dir` on persistent storage (not `/tmp` — tmpfs on AL2023, lost on crash) and `--header` if file has a header row
3. On failure: resume with `--resume-job-id`; for duplicates use `--on-conflict do-nothing`
4. For large tables: create secondary indexes after load using `CREATE INDEX ASYNC`

### Workflow 4: Foreign Key Constraints

**MUST** load and follow [foreign-keys.md](references/foreign-keys.md)
before creating, altering, dropping, or migrating foreign keys.

### Workflow 5: Query with Tenant Isolation

1. **MUST** authorize the caller against the tenant — format validation does not establish authorization
2. **MUST** build SQL with [`safe_query.build()`](mcp/tools/safe_query.py) — use `allow()`/`regex()` for
   values (emits `'v'`), `ident()` for table/column names (emits `"v"`).
   See [input-validation.md](mcp/tools/input-validation.md)
3. **MUST** include `tenant_id` in the WHERE clause; reject cross-tenant access at the application layer

### Workflow 6: Set Up Scoped Database Roles

MUST load [access-control.md](references/access-control.md) for role setup, IAM mapping, and schema permissions.

### Workflow 7: Table Recreation DDL Migration

For `ALTER COLUMN TYPE`, `SET NOT NULL`, or `MODIFY PRIMARY KEY`, **MUST**
load [ddl-migrations/overview.md](references/ddl-migrations/overview.md). Use a direct ALTER form
when supported; otherwise, present a user-approved table-recreation plan.

### Workflow 8: Validate and Migrate to DSQL

MUST load [dsql-lint.md](references/dsql-lint.md) before running `dsql_lint`. Run `dsql_lint(sql=source_sql, fix=true)` to validate and auto-convert. For MySQL-origin SQL, MUST cross-check against [mysql-migrations/type-mapping.md](references/mysql-migrations/type-mapping.md) even when lint returns clean. On `parse_error`, fall back to manual conversion then re-lint.

### Workflow 9: Query Plan Explainability

Explains why the DSQL optimizer chose a particular plan. Triggered by slow queries, high DPU, unexpected Full Scans, or plans the user doesn't understand. **REQUIRES a structured Markdown diagnostic report as the deliverable.**

MUST load [query-plan/workflow.md](references/query-plan/workflow.md) at entry — it defines trigger criteria, context disambiguation, routing, and the full phased workflow (Phase 0–4). Workflow.md specifies which reference files to load at each phase.

**Safety.** Plan capture uses `readonly_query` exclusively. Rewrite DML to SELECT for plan capture. **MUST NOT** use `transact --allow-writes` for plan capture.

### Workflow 10: Full PostgreSQL → DSQL Schema Migration

MUST load [pg-migrations/type-mapping.md](references/pg-migrations/type-mapping.md), [pg-migrations/index-conversion.md](references/pg-migrations/index-conversion.md), [pg-migrations/schema-objects.md](references/pg-migrations/schema-objects.md), and [foreign-keys.md](references/foreign-keys.md). Run `dsql_lint(fix=true)` first for mechanical fixes, preserve foreign-key relationships, translate unsupported source syntax or options, then apply semantic conversions from the pg-migrations references for unfixable diagnostics and patterns the linter cannot handle. Re-lint the final output before deploying.

### Workflow 11: ORM Migration and Locking (Django/EF Core/Hibernate/Rails/SQLAlchemy)

Load [orm-guides/overview.md](references/orm-guides/overview.md) for adapter names, locking guidance, and framework-specific gotchas.

### Workflow 12: System Diagnostics (CloudWatch AAS)

Diagnose cluster performance by querying `db.active_sessions.avg` via PromQL. Detects temporal anomalies in wait event distribution, identifies regressed queries, and routes to Workflow 9 for per-query investigation.

**Requires:** CloudWatch MCP server (`awslabs.cloudwatch-mcp-server`) enabled and configured with PromQL access in the same region as the cluster — see [mcp/mcp-setup.md](mcp/mcp-setup.md#cloudwatch-mcp-server-system-diagnostics--workflow-12) for enabling it, region requirements, and the session restart needed for its tools to register.

MUST load [system-diagnostics/workflow.md](references/system-diagnostics/workflow.md) at entry — it defines prerequisites, 5 diagnostic phases, temporal baselines, and the routing to Workflow 9 for identified queries.

## Error Scenarios

- **`awsknowledge` returns no results:** Use the default limits in the table above and note that limits should be verified against [DSQL documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/).
- **`dsql_lint` unavailable or timing out:** See the Error Handling section of [dsql-lint.md](references/dsql-lint.md). Do not silently skip validation — inform the user and require explicit confirmation before proceeding with manual rules from [development-guide.md](references/development-guide.md).
- **OCC serialization error:** Retry the transaction. If persistent, check for hot-key contention — see [troubleshooting.md](references/troubleshooting.md).
- **Foreign key violation (`23503`):** Correct the relationship or referential action; **MUST NOT**
  send it through the `40001` retry loop — see [troubleshooting.md](references/troubleshooting.md).
- **Transaction exceeds limits:** Split write batches to stay under 3,000 row modifications and 10 MiB; locked-row primary keys count toward the size limit — see [batched-migration.md](references/ddl-migrations/batched-migration.md).
- **Token expiration mid-operation:** Generate a fresh IAM token — see [authentication-guide.md](references/auth/authentication-guide.md). See [troubleshooting.md](references/troubleshooting.md) for other issues.

## Additional Resources

- [Aurora DSQL Documentation](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/)
- [Code Samples Repository](https://github.com/aws-samples/aurora-dsql-samples)
