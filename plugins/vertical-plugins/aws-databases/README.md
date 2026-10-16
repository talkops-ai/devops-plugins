# AWS Databases

Full-lifecycle AWS database engineering for the main agent: Aurora (PostgreSQL, MySQL, DSQL), RDS (PostgreSQL, MySQL, MariaDB, Oracle, SQL Server, Db2), DynamoDB, DocumentDB, ElastiCache (Valkey/Redis/Memcached), Keyspaces, Neptune, Timestream for InfluxDB, Performance Insights wait-event triage, Blue/Green deployments, and DMS migrations.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-databases@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-database-engineer`](../../agent-plugins/aws-database-engineer) or [`aws-sre-agent`](../../agent-plugins/aws-sre-agent) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-databases:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-databases:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `amazon-aurora-mysql` | >- |
| `amazon-aurora-postgresql` | >- |
| `amazon-documentdb` | Manages Amazon DocumentDB end-to-end — serverless-on-8.0 cluster setup, TLS/VPC/driver config, flexible-schema and vector-search data modeling, MongoDB compatibility assessment, DMS-based migration,… |
| `amazon-dynamodb` | Designs, reviews, and debugs DynamoDB data layers from design axioms — enumerates access patterns, chooses partition/sort keys and GSIs, decides single-table vs. |
| `amazon-elasticache` | Activate when developers have latent caching needs: slow API responses, database read bottlenecks, DynamoDB throttling or cost, RDS/Aurora scaling pressure, Bedrock latency or cost, or adding a cache… |
| `amazon-keyspaces` | >- |
| `amazon-neptune` | Provides authoritative guidance on Amazon Neptune Database and Neptune Analytics for graph, knowledge-graph, and relationship-heavy workloads — fraud detection / fraud rings, agentic memory / chatbot… |
| `aws-database` | Principal Database Architect router and FinOps evaluator for AWS databases — choosing, comparing, estimating TCO, getting started with, or operating any AWS operational database. |
| `database-and-cache-reliability` | Diagnose and remediate production stateful data-plane and queue reliability incidents across Amazon RDS/Aurora (DBLoad wait events, max_connections exhaustion, RDS Proxy pinning, replica lag, failove… |
| `db-ha-dr-and-schema-evolution` | >- |
| `db-observability-and-wait-triage` | >- |
| `dms-data-migration-execution` | >- |
| `dms-schema-conversion` | Handles the full DMS Schema Conversion lifecycle including creating migration projects, converting database schemas to a target engine, running compatibility assessments, navigating metadata trees, e… |
| `dsql` | Build with Aurora DSQL — manage schemas, execute queries, handle migrations, diagnose query plans, diagnose cluster performance, load data, and develop applications with a serverless, distributed SQL… |
| `rds-db2` | Provisions, connects, migrates, and operates Amazon RDS for Db2. |
| `rds-oracle` | Full-lifecycle management, administration, and connectivity troubleshooting for Amazon RDS for Oracle and RDS Custom for Oracle. |
| `rds-oss` | Advises on Amazon RDS open-source engines (MySQL, MariaDB, PostgreSQL) for instance creation, upgrade planning, commitment pricing, proxy evaluation, and Blue/Green deployments. |
| `rds-sqlserver` | Full-lifecycle management, administration, and connectivity troubleshooting for Amazon RDS for SQL Server and RDS Custom for SQL Server. |
| `timestream-influxdb` | Retrieves authoritative guidance on Amazon Timestream for InfluxDB across its supported engine variants. |

## Commands

| Command | Description |
|---|---|
| `/aws-databases:aurora-cluster-ops` | Manage Amazon Aurora PostgreSQL/MySQL clusters: Serverless v2 scaling, Global Database failover, RDS Proxy, and parameter tuning. |
| `/aws-databases:blue-green-schema-migration` | Plan and execute a zero-downtime RDS/Aurora Blue/Green deployment or online schema evolution with rollback safeguards. |
| `/aws-databases:caching-strategy` | Design or tune an Amazon ElastiCache (Valkey/Redis/Memcached) caching layer with TTLs, stampede protection, and hot-key mitigation. |
| `/aws-databases:choose-database` | Recommend the optimal AWS database engine (Aurora PostgreSQL/MySQL, Aurora DSQL, RDS, DynamoDB, DocumentDB, ElastiCache, Neptune, Keyspaces) with cost and HA comparison. |
| `/aws-databases:dynamodb-single-table-design` | Design a DynamoDB single-table schema with partition/sort key overloading, GSIs, sparse indexes, and capacity mode cost analysis. |
| `/aws-databases:troubleshoot-db` | Triage database CPU spikes, lock contention, slow queries, and replication lag using CloudWatch Database Insights / Performance Insights wait events. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-databases_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `awsknowledge` | http | `https://knowledge-mcp.global.api.aws` | `mcp__plugin_aws-databases_awsknowledge__*` | Official AWS documentation, Architecture Center, and Well-Architected knowledge base. |
| `dynamodb` | stdio | `uvx awslabs.dynamodb-mcp-server>=2.1.6` | `mcp__plugin_aws-databases_dynamodb__*` | DynamoDB table/index modeling, capacity inspection, and query validation. |
| `postgres` | stdio | `uvx awslabs.postgres-mcp-server@latest` | `mcp__plugin_aws-databases_postgres__*` | RDS / Aurora PostgreSQL schema inspection and read-only SQL diagnostics via RDS Data API. |
| `mysql` | stdio | `uvx awslabs.mysql-mcp-server@latest` | `mcp__plugin_aws-databases_mysql__*` | RDS / Aurora MySQL schema inspection and read-only SQL diagnostics via RDS Data API. |
| `elasticache` | stdio | `uvx awslabs.elasticache-mcp-server@latest --readonly` | `mcp__plugin_aws-databases_elasticache__*` | Amazon ElastiCache control-plane inspection (read-only). |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-databases_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-databases_awspricing__*` | Real-time AWS service pricing catalog and architecture cost calculation. |

## Optional connectors

Connection-bound MCP servers you add yourself (see [CONNECTORS.md](./CONNECTORS.md)): `aurora-dsql`, `documentdb`, `keyspaces`, `neptune`, `valkey`, `memcached`, `mssql`, `oracle`, `timestream-influxdb`.

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-databases_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-databases_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
- **PostToolUse** `mcp__.*aurora-dsql.*__transact` — prompt: `A DSQL transact operation completed.`
