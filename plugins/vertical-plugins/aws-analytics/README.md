# AWS Analytics

Modern data lakehouse and analytics engineering for the main agent: S3 Tables (Apache Iceberg), AWS Glue (Catalog, Spark ETL, Data Quality DQDL), Lake Formation governance, Amazon Athena, Amazon Redshift, Amazon OpenSearch, EMR, MWAA (Airflow), Kinesis/MSK streaming ingestion, and system-table auditing.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-analytics@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-data-engineer`](../../agent-plugins/aws-data-engineer) or [`aws-solutions-architect`](../../agent-plugins/aws-solutions-architect) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-analytics:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-analytics:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `amazon-opensearch-service` | >- |
| `auditing-aws-system-tables` | >- |
| `authoring-glue-and-emr-spark-jobs` | >- |
| `authoring-mwaa-workflow` | > |
| `aws-cleanrooms` | Troubleshoots and debugs AWS Clean Rooms collaboration issues related to IAM roles, S3 bucket policies, KMS keys, Lake Formation permissions, and CloudWatch logging for custom ML model training and i… |
| `aws-data-analytics` | Architects modern transactional data lakes, zero-ETL pipelines, and analytical lakehouses using Amazon S3 Tables (managed Apache Iceberg), AWS Glue 5.1+, AWS Lake Formation (LF-TBAC), Amazon Athena,… |
| `connecting-to-data-source` | >- |
| `creating-data-lake-table` | >- |
| `debugging-mwaa-workflow` | > |
| `developing-applications-on-managed-service-for-apache-flink` | >- |
| `enforcing-data-quality` | >- |
| `exploring-data-catalog` | >- |
| `finding-data-lake-assets` | >- |
| `governing-and-securing-data-lake` | >- |
| `ingesting-into-data-lake` | >- |
| `ingesting-streaming-and-cdc-data` | >- |
| `managing-amazon-kinesis-data-streams` | >- |
| `managing-amazon-msk` | > |
| `migrate-to-msk` | >- |
| `migrating-to-amazon-redshift` | Guides an end-to-end data-warehouse migration to Amazon Redshift — discovery, schema/SQL/stored-procedure/macro/script conversion, data migration, validation, performance comparison, and reporting. |
| `orchestrating-serverless-data-pipelines` | >- |
| `provisioning-data-infrastructure-iac` | >- |
| `querying-data-lake` | >- |
| `redshift-guide` | Amazon Redshift is NOT PostgreSQL — corrects PostgreSQL-derived LLM mistakes; covers Redshift-specific SQL, DDL, COPY/UNLOAD, system views, metadata discovery, and operational patterns. |
| `storing-and-querying-vectors` | >- |
| `testing-mwaa-workflow` | > |
| `upgrading-mwaa-environments` | > |

## Commands

| Command | Description |
|---|---|
| `/aws-analytics:glue-data-quality` | Author AWS Glue Data Quality (DQDL) rulesets with completeness, freshness, and anomaly detection circuit breakers. |
| `/aws-analytics:lake-formation-governance` | Design Lake Formation tag-based access control (LF-TBAC), column/row-level security filters, and cross-account data mesh sharing. |
| `/aws-analytics:lakehouse-design` | Architect an Apache Iceberg transactional data lakehouse on AWS using S3 Tables, Glue Data Catalog, Lake Formation, and Athena/Redshift. |
| `/aws-analytics:opensearch-ops` | Audit and tune an Amazon OpenSearch Service domain or Serverless collection for shard sizing, JVM heap pressure, index lifecycle (ISM), and vector search. |
| `/aws-analytics:redshift-optimize` | Analyze Amazon Redshift query performance, distribution/sort keys, WLM/Serverless RPU scaling, and system table alerts. |
| `/aws-analytics:spark-debug` | Diagnose AWS Glue or Amazon EMR Spark job failures, OOM exceptions, data skew, shuffle spill, and DPU/executor sizing. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-analytics_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `awsdataprocessing` | stdio | `uvx awslabs.aws-dataprocessing-mcp-server@latest` | `mcp__plugin_aws-analytics_awsdataprocessing__*` | AWS Glue Data Catalog, crawlers, Spark jobs, EMR clusters, and Athena workgroups. |
| `redshift` | stdio | `uvx awslabs.redshift-mcp-server@latest` | `mcp__plugin_aws-analytics_redshift__*` | Amazon Redshift provisioned and Serverless cluster inspection and SQL execution. |
| `s3tables` | stdio | `uvx awslabs.s3-tables-mcp-server@latest` | `mcp__plugin_aws-analytics_s3tables__*` | Amazon S3 Tables (managed Apache Iceberg) catalog and table operations. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-analytics_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |
| `spark-troubleshooting` | stdio | `uvx mcp-proxy-for-aws@latest https://sagemaker-unified-studio-mcp.us-east-1.api.aws/spark-troubleshooting/mcp --service sagemaker-unified-studio-mcp --region us-east-1 --read-timeout 180` | `mcp__plugin_aws-analytics_spark-troubleshooting__*` | Remote Spark history server and Glue/EMR shuffle/OOM root-cause diagnostics. |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-analytics_awspricing__*` | Real-time AWS service pricing catalog and architecture cost calculation. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-analytics_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-analytics_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
