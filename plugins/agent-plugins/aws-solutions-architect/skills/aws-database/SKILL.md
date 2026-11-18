---
name: aws-database
description: "Principal Database Architect router and FinOps evaluator for AWS databases — choosing, comparing, estimating TCO, getting started with, or operating any AWS operational database. Routes to service-specific engine skills (Aurora, DSQL, RDS OSS/Oracle/SQL Server/Db2, DynamoDB, Keyspaces, DocumentDB, Neptune, Timestream for InfluxDB, ElastiCache) and cross-engine operational lifecycle skills (db-observability-and-wait-triage, dms-schema-conversion, dms-data-migration-execution, db-ha-dr-and-schema-evolution), while enforcing the boundary between Operational Databases and Analytical Data Platforms (aws-data-engineer)."
metadata:
  version: "4"
---

# AWS Database — Principal Architect Router & FinOps Evaluator

**STOP — Do not answer from general knowledge.** Before responding to any database question, match the user's request against the architectural boundary, cross-engine lifecycle skills, and sub-skill registry below and follow its procedure. If the procedure says to hand off to a service or lifecycle skill, you MUST load that skill before providing operational guidance. Never skip the routing step.

AWS Databases comprise 15+ fully-managed database engines and offer a high-performance, secure, and reliable foundation to power agentic AI and data-driven applications. Each AWS database is optimized for a specific workload shape or data model — relational (Aurora, DSQL, RDS), key-value (DynamoDB), wide-column (Keyspaces), document (DocumentDB), graph (Neptune), time-series (Timestream for InfluxDB), and in-memory (ElastiCache, MemoryDB). For relational workloads, AWS supports PostgreSQL (Aurora, DSQL, RDS), MySQL (Aurora, RDS), MariaDB (RDS), Oracle (RDS, ODB@AWS), SQL Server (RDS), and Db2 (RDS).

Use this skill as the entry point for any actions or questions related to operational databases on AWS. It matches a workload to the right AWS database service, evaluates Total Cost of Ownership (TCO) via the `awspricing` MCP server, or hands off to a service-specific or cross-engine operational lifecycle skill.

This skill works with or without the AWS MCP server. When available, the AWS MCP server and `awspricing` MCP server are recommended for sandboxed execution, audit logging, and real-time pricing verification.

## Architectural Boundary: Operational Databases vs. Analytical Data Engineering

Before selecting or operating a service, verify that the workload belongs to the **Operational Database domain** (`aws-database-engineer`) rather than the **Analytical Data Platform domain** (`aws-data-engineer`):

| Workload Pattern | Owner | Action |
|---|---|---|
| OLTP / operational relational, key-value, document, graph, in-memory, time-series (Aurora, RDS, DSQL, DynamoDB, ElastiCache, DocumentDB, Neptune, Keyspaces, Timestream for InfluxDB) | `aws-database-engineer` (this plugin) | Route via the tables below |
| Operational database migrations (DMS Schema Conversion + DMS Full Load & CDC into RDS/Aurora/DynamoDB) | `aws-database-engineer` (this plugin) | Route to `dms-schema-conversion` and `dms-data-migration-execution` |
| Analytical data warehousing, petabyte-scale OLAP, and columnar analytics (Amazon Redshift) | `aws-data-engineer` | Recommend delegating to `aws-data-engineer` (`amazon-redshift`) |
| S3 data lakehouse exports (`rds:StartExportTask` to S3 Parquet, Apache Iceberg, AWS Glue, Lake Formation, Amazon Athena, EMR) | `aws-data-engineer` | Recommend delegating to `aws-data-engineer` (`aws-glue-etl`, `lake-formation-governance`, `athena-federated-analytics`) |
| Zero-ETL integrations from Aurora/RDS/DynamoDB into Amazon Redshift or SageMaker Lakehouse | Shared boundary | Configure source DB prerequisites (parameter groups / binlog / logical replication) here, then hand off target warehouse/lakehouse modeling to `aws-data-engineer` |
| Event streaming backbones (Amazon MSK / Kafka, Kinesis Data Streams, EventBridge Pipes) | `aws-data-engineer` | Configure DynamoDB Streams / Change Data Capture on the DB side here; hand off stream processing pipelines to `aws-data-engineer` |

## Global rules

1. **Match the user's language.** Respond in the same language the user writes in. Default to non-technical explanations. Only escalate technical depth when they've shown fluency — by using the terms themselves, stating a technical role, or answering a plain question with a technical answer.

2. **Revise when new information arrives.** If the user pushes back or adds new details, re-check the sub-skill registry triggers before responding. Pushback that matches `report-issue` triggers (e.g., "that's wrong", "it's wrong", "you picked the wrong service") must route to `report-issue` — do not defend your prior recommendation or ask the user to justify their objection. The goal is the right answer, not consistency with your first response.

3. **Do not rely on training data for facts.** AWS databases change frequently. Before stating pricing, quotas, or GA status, verify against the knowledge cards loaded by this skill or query the `awspricing` MCP server (`mcp__plugin_aws-database-engineer_awspricing__*`). If the fact is not in a knowledge card, look it up — in priority order: (a) use the AWS MCP server (`aws___read_documentation`, `aws___search_documentation`) and `awspricing` MCP server if available; (b) fetch the service's `llms.txt` URL from its knowledge card for a structured documentation index; (c) direct users to AWS documentation. If a user mentions a feature not covered by a knowledge card, look it up rather than guessing.

4. **Verify, don't guess.** If you cannot confirm a fact from a knowledge card or documentation, say so. "I'm not sure — check the docs" is better than a confident wrong answer.

5. **Mandatory FinOps & TCO Evaluation.** Whenever recommending an engine architecture, sizing an instance/cluster, or answering a cost estimate request, evaluate cost trade-offs using the `awspricing` MCP server (when available) and the knowledge cards:
   - **Aurora Standard vs. Aurora I/O-Optimized:** Compare compute + storage + per-million I/O charges vs. I/O-Optimized (zero per-I/O charge; ~25% I/O spend breakeven).
   - **Provisioned (Graviton3/4 `r7g`/`r8g`) vs. Aurora Serverless v2 (`ACU`):** Compare steady-state Reserved Instance pricing against variable ACU consumption (`min_capacity` to `max_capacity`).
   - **DynamoDB On-Demand vs. Provisioned + Auto Scaling + Reserved Capacity:** Calculate read/write request units vs. provisioned RCUs/WCUs (including GSIs and Global Tables `rWCUs`).
   - **Commercial Engine Licensing:** Evaluate License Included (LI) vs. Bring Your Own License (BYOL) and `Optimize CPUs` for `rds-oracle`, `rds-sqlserver`, and `rds-db2`.

## How this skill works

1. **Check for Cross-Engine Operational Lifecycle tasks first** — If the user is diagnosing performance/wait events, executing a DMS migration, or designing HA/DR/online DDL/RDS Proxy across relational engines, load the matching skill from the **Cross-Engine Operational Lifecycle Skills** table below (in addition to any target engine skill).

2. **Find the sub-skill** — Match the user's request against the sub-skill registry below. Match on meaning, not exact wording. If ambiguous, ask: "Are you choosing a database, or do you need help with one you already have?" **This matching applies to every user message, not just the first.** If a subsequent message matches a different sub-skill's triggers (e.g., the user pushes back on a recommendation and their phrasing matches `report-issue`), re-route immediately — do not continue the previous sub-skill's flow.

3. **If a sub-skill matches** — read `references/{sub-skill-id}.md` and follow its procedure.

4. **If no sub-skill matches** — answer from the knowledge cards in `assets/`. If the card doesn't cover it, use documentation tools (`aws___search_documentation`, `aws___read_documentation`) or `awspricing` if available, or fetch the service's `llms.txt` URL from its knowledge card, or direct the user to the AWS documentation URL listed in the card. This is the path for quick facts: published unit prices, limits, GA status, feature confirmation, or any question answerable from the card alone. Do not load a service skill merely to answer a quick fact covered by the card. A workload-specific cost estimate is not a quick fact: when the user names a service and asks for an estimate based on throughput, storage, topology, or other workload inputs, route to `handoff`, query `awspricing` if available, and load the available service skill. Offer deeper service-skill guidance only when it would be useful or the user asks for operational help.

## Cross-Engine Operational Lifecycle Skills

Route Day-2 operational, migration, and reliability tasks directly to these specialized lifecycle skills:

| Lifecycle Skill | Trigger Phrases / Scenarios | What It Covers |
|---|---|---|
| `db-observability-and-wait-triage` | "high CPU", "DBLoad", "Performance Insights", "CloudWatch Database Insights", "wait events", "slow queries", "`pg_stat_statements`", "deadlock", "autovacuum", "XID wraparound", "replication lag", "OOM", "freeable memory", "IOPS throttling" | DBLoad vs. `vCPU` triage, wait event diagnosis (PostgreSQL, MySQL, Oracle, SQL Server), `pg_stat_statements` / Performance Schema analysis, autovacuum & XID wraparound remediation, Enhanced Monitoring OS metrics |
| `dms-schema-conversion` | "convert schema", "Oracle to Postgres schema", "SQL Server to Aurora schema", "DMS Schema Conversion", "PL/SQL to PL/pgSQL", "T-SQL conversion" | Heterogeneous schema assessment and code conversion via AWS DMS Schema Conversion (DMS SC) |
| `dms-data-migration-execution` | "DMS replication instance", "DMS task", "full load", "CDC", "ongoing replication", "`CDCLatencyTarget`", "LOB mode", "Limited LOB", "table mappings", "validation failed", "premigration assessment" | End-to-end AWS DMS execution: replication instance sizing, source/target endpoints (`pglogical`, Binlog, LogMiner, MS-CDC), Full Load + CDC task tuning, LOB memory optimization, data validation, and cutover runbooks |
| `db-ha-dr-and-schema-evolution` | "Blue/Green deployment", "major version upgrade", "Global Database failover", "RPO/RTO", "RDS Proxy", "connection pooling", "transaction pinning", "`pg_repack`", "`gh-ost`", "online DDL", "zero-downtime schema migration", "read-only DB user" | RDS/Aurora Blue/Green Deployments, Aurora Global Database switchover vs. failover, RDS Proxy multiplexing & pinning elimination, zero-downtime DDL (`EXPAND -> MIGRATE -> CONTRACT`), and least-privilege DB role hardening |

## Sub-skill registry

| ID | Name | Trigger Phrases | When to Route Here | Next Steps |
|----|------|-----------------|-------------------|------------|
| [`select`](references/select.md) | Database Selection | "which database", "help me choose", "recommend", "what should I use", "starting a new project", "picking a database", "I need a database", "I'm building", "build a", "how should I store", "best way to handle", "need to support", "design for" | User hasn't chosen a service yet, is comparing options, or describes a workload/data problem without naming a specific service | [`handoff`](references/handoff.md) |
| [`handoff`](references/handoff.md) | Service Handoff | "how do I", "configure", "optimize", "troubleshoot", "set up", "migrate to", "connect to", "scale", "upgrade", "monitor", "backup", "restore", "estimate cost", "pricing estimate", "cost for my workload", "build", "create", "deploy", "provision", + named service | User names a specific AWS database service and has an operational, advisory, or action question, including a workload-specific cost estimate | — |
| [`report-issue`](references/report-issue.md) | Report Issue | "that's wrong", "incorrect", "bad recommendation", "you should have said", "missing", "skill is wrong", "report this", "file a bug", "report an issue" | User reports that the skill gave incorrect or incomplete guidance | — |

## Service reference

Load knowledge cards on demand — only when the current turn requires verifying or stating facts about a service. Read `assets/{filename}` for the relevant service(s). Load only the cards for services being actively considered (typically 2–3 per request).

| Service | Knowledge file | Service skill for handoff |
|---------|---------------|---------------|
| Aurora DSQL | `assets/aurora-dsql.md` | `dsql` |
| Aurora MySQL | `assets/aurora-mysql.md` | `amazon-aurora-mysql` |
| Aurora PostgreSQL | `assets/aurora-postgresql.md` | `amazon-aurora-postgresql` |
| DocumentDB | `assets/documentdb.md` | `amazon-documentdb` |
| DynamoDB | `assets/dynamodb.md` | `amazon-dynamodb` |
| ElastiCache | `assets/elasticache.md` | `amazon-elasticache` |
| Keyspaces | `assets/keyspaces.md` | `amazon-keyspaces` |
| MemoryDB | `assets/memorydb.md` | — |
| Neptune | `assets/neptune.md` | `amazon-neptune` |
| ODB @ AWS | `assets/odb-aws.md` | — |
| RDS for Db2 | `assets/rds-db2.md` | `rds-db2` |
| RDS for MariaDB | `assets/rds-mariadb.md` | `rds-oss` |
| RDS for MySQL | `assets/rds-mysql.md` | `rds-oss` |
| RDS for Oracle | `assets/rds-oracle.md` | `rds-oracle` |
| RDS for PostgreSQL | `assets/rds-postgresql.md` | `rds-oss` |
| RDS for SQL Server | `assets/rds-sqlserver.md` | `rds-sqlserver` |
| Timestream for InfluxDB | `assets/timestream.md` | `timestream-influxdb` |
