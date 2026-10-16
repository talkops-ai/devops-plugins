---
name: app-data-layer-remediation
description: "Synchronizes application-layer SQL queries, stored procedure calls, and ORM persistence frameworks (JPA/Hibernate, MyBatis, EF Core) across Java, .NET, Node.js, and Python with DMS Schema Conversion when migrating Oracle and SQL Server to Aurora PostgreSQL/DSQL. Packages DDL into versioned Flyway/Liquibase CI/CD pipelines and validates queries via read-only postgres MCP."
---

# Application Data Layer Remediation

## Overview

Heterogeneous database modernization inevitably fails when schema conversion is decoupled from application persistence code. While **AWS DMS Schema Conversion (`dms-schema-conversion`)** transforms database-side DDL, views, and stored procedures, applications will crash at runtime if embedded SQL, ORM mappings, sequence generators, pagination, date arithmetic, and error-handling routines in the application codebase are not synchronized in parallel.

This skill governs the systematic remediation of application-layer code across Java, .NET, Node.js, and Python repositories when migrating from **Oracle** or **Microsoft SQL Server** to **Amazon Aurora PostgreSQL** or **Amazon Aurora DSQL**.

### Mandatory 2026 Guardrails

> **1. STRICT PROHIBITION: Unsynchronized Database Migrations**
> Never convert DDL without scanning and remediating the application code that executes queries against those tables. Every schema change must have a corresponding pull request updating ORM entities and raw queries.
>
> **2. STRICT PROHIBITION: AWS DMS Fleet Advisor**
> AWS DMS Fleet Advisor has reached End of Support (EOL). Execute all database discovery, metadata tree navigation, and compatibility assessments via the `dms-schema-conversion` skill powered by `aws-mcp`.
>
> **3. STRICT PROHIBITION: High-Privilege or Mutating MCP Database Connections**
> When testing or verifying SQL queries against target Aurora PostgreSQL databases, the `postgres` MCP server must ALWAYS be invoked with `--readonly True` and `--privilege_check enforce`. Never connect as `rds_superuser` or execute DDL/DML directly through the MCP data-plane tool.

---

## Remediation Workflow & Lifecycle

```
[ Step 1: Scan Codebase ] 
       | Identify embedded SQL, ORM configurations, JPA/Hibernate entities,
       | MyBatis XML mappers, Entity Framework DbContext, and raw query strings.
       v
[ Step 2: Synchronize with DMS SC ]
       | Ingest DDL mapping definitions from dms-schema-conversion action items.
       | Align column renames, type conversions (e.g. NUMBER(1) -> BOOLEAN), and schema namespaces.
       v
[ Step 3: Rewrite Proprietary SQL Constructs ]
       | Convert Oracle (ROWNUM, SYSDATE, NVL, DECODE, CONNECT BY) and
       | T-SQL (TOP, ISNULL, IDENTITY, @@ROWCOUNT, table variables) to standard PostgreSQL.
       v
[ Step 4: Remediate ORM & Persistence Layer ]
       | Update dialect configuration, sequence generators (@SequenceGenerator, allocationSize),
       | batch fetching, and native query signatures in Hibernate/EF Core/MyBatis.
       v
[ Step 5: Update Error Handling (SQLSTATE) ]
       | Replace proprietary vendor error codes (ORA-00001, ORA-00054, SQL Server 2627)
       | with PostgreSQL 5-character SQLSTATE codes (23505 unique violation, 55P03 lock not available).
       v
[ Step 6: Verify via Read-Only Postgres MCP ]
       | Validate remediated queries and EXPLAIN plans against target Aurora PostgreSQL
       | using `mcp__plugin_aws-modernization-agent_postgres__*` in read-only mode.
       v
[ Step 7: Package into Versioned Flyway/Liquibase CI/CD ]
       | Organize converted DDL and incremental migration scripts into versioned
       | V<Version>__<Description>.sql files for automated CI/CD deployment.
```

---

## Dialect & Query Syntax Quick Reference

### Oracle to Aurora PostgreSQL

| Oracle Feature | PostgreSQL Equivalent | Notes |
|---|---|---|
| `ROWNUM <= 10` | `LIMIT 10` or `FETCH FIRST 10 ROWS ONLY` | Add explicit `ORDER BY` for deterministic pagination. |
| `SYSDATE` | `clock_timestamp()` or `CURRENT_TIMESTAMP` | `clock_timestamp()` returns actual clock time; `CURRENT_TIMESTAMP` returns transaction start time. |
| `NVL(col, default)` | `COALESCE(col, default)` | Standard SQL equivalent. |
| `DECODE(val, 1, 'A', 'B')` | `CASE val WHEN 1 THEN 'A' ELSE 'B' END` | Standard SQL equivalent. |
| `CONNECT BY PRIOR id = parent_id` | `WITH RECURSIVE hier AS (...)` | Recursive Common Table Expressions (CTE). |
| `seq.NEXTVAL` | `nextval('seq')` | Function-based sequence retrieval. |
| `DUAL` table | Omit `FROM DUAL` | `SELECT clock_timestamp();` is valid in PostgreSQL. |

### SQL Server (T-SQL) to Aurora PostgreSQL

| T-SQL Feature | PostgreSQL Equivalent | Notes |
|---|---|---|
| `SELECT TOP (10) *` | `SELECT * ... LIMIT 10` | Place `LIMIT` at end of query. |
| `ISNULL(col, default)` | `COALESCE(col, default)` | Standard SQL equivalent. |
| `IDENTITY(1,1)` | `BIGINT GENERATED ALWAYS AS IDENTITY` | Standard SQL:2008 identity column. |
| `@@ROWCOUNT` | `GET DIAGNOSTICS count = ROW_COUNT` | Inside PL/pgSQL; in client drivers use `executeUpdate()` result. |
| `@table_variable` | `TEMPORARY TABLE` or CTE (`WITH`) | Use temporary tables or in-memory CTEs. |
| `GETDATE()` | `clock_timestamp()` or `CURRENT_TIMESTAMP` | PostgreSQL timestamp function. |

---

## Reference Library

Detailed migration guides, code before/after snippets, and framework configurations are available in `references/`:
- [references/oracle-to-postgres-sql-rewrite.md](references/oracle-to-postgres-sql-rewrite.md) — Exhaustive Oracle SQL and PL/SQL patterns rewritten to PostgreSQL.
- [references/tsql-to-postgres-sql-rewrite.md](references/tsql-to-postgres-sql-rewrite.md) — Comprehensive T-SQL queries, procedural scripts, and table variables converted to PostgreSQL.
- [references/orm-framework-migration.md](references/orm-framework-migration.md) — Hibernate/JPA, MyBatis, and Entity Framework Core configurations, dialect changes, sequence allocation tuning, and SQLSTATE exception mappers.
- [references/flyway-liquibase-cicd.md](references/flyway-liquibase-cicd.md) — Versioned database migration pipelines with GitHub Actions, AWS CodePipeline, and Secrets Manager integration.
