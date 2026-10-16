# AWS Data Engineer

Principal AWS data-lake, streaming, and analytics engineer: S3 Tables/Apache Iceberg, Glue Data Catalog/Connections/5.1+ PySpark & EMR Serverless ETL, Data Firehose/DMS CDC/Kinesis/MSK/Flink/AppFlow streaming, Athena & Redshift (Provisioned/Serverless), OpenSearch OSIS/ISM, Step Functions/EventBridge & MWAA (Airflow) orchestration, Glue Data Quality (DQDL), Lake Formation governance, and CDK/CloudFormation data IaC.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-data-engineer@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/aws-data-engineer.toml`](./codex/agents/aws-data-engineer.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, command, hook, and MCP server below is bound to the [`aws-data-engineer`](./agents/aws-data-engineer.md) agent, which the host runtime spawns as a dynamic sub-agent.

- Claude Code: `@agent-aws-data-engineer:aws-data-engineer` or let Claude delegate based on the agent description
- Headless: `claude --agent aws-data-engineer:aws-data-engineer`
- Codex: install the custom agent above, then ask Codex to spawn `aws-data-engineer`. Codex plugins can't bundle agents, so without it the skills and MCP servers attach to the main agent.

## Skills

| Skill | What it does |
|---|---|
| `amazon-opensearch-service` | Guides OpenSearch Ingestion (OSIS), Index State Management (ISM) hot-warm-cold tiering, PPL log analytics, OpenTelemetry trace analytics, k-NN vector/hybrid search, Solr/Elasticsearch migration, and cluster/Serverless p… |
| `auditing-aws-system-tables` | Consolidates administrative system-table analytics exported as Apache Iceberg tables in Amazon S3 Tables across three AWS-managed table buckets: (1) Redshift SYS_* system-table logs (s3tablescatalog/aws-redshift: sys_qu… |
| `authoring-glue-and-emr-spark-jobs` | Authors, optimizes, and tunes distributed PySpark and Ray ETL jobs on AWS Glue 5.1+ and Amazon EMR (Serverless and EC2). |
| `authoring-mwaa-workflow` | Authors and deploys MWAA workflow artifacts: Python Airflow DAGs for provisioned environments or YAML workflow files for Serverless. |
| `connecting-to-data-source` | Create and troubleshoot AWS Glue connections to JDBC databases (Oracle, SQL Server, PostgreSQL, MySQL, RDS), Redshift, Snowflake, and BigQuery. |
| `creating-data-lake-table` | Create managed Iceberg tables using Amazon S3 Tables (s3tables API namespace) with automatic compaction and snapshot management. |
| `debugging-mwaa-workflow` | Diagnoses and root-causes Amazon MWAA workflow failures across Provisioned (Python DAG) and Serverless (YAML workflow) environments. |
| `developing-applications-on-managed-service-for-apache-flink` | MANDATORY for Flink or Amazon Managed Service for Apache Flink (MSF) questions. |
| `enforcing-data-quality` | Authors, executes, and automates data quality rulesets using AWS Glue Data Quality (Data Quality Definition Language - DQDL) for both Glue Data Catalog tables at rest and in-flight Glue ETL PySpark jobs, alongside AWS G… |
| `exploring-data-catalog` | Full inventory and audit of AWS Glue Data Catalog assets across S3 Tables, Redshift-federated, and remote Iceberg catalogs. |
| `finding-data-lake-assets` | Resolve data lake and lakehouse asset references across Glue Data Catalog, S3, S3 Tables, and Redshift. |
| `governing-and-securing-data-lake` | Configures and troubleshoots AWS Lake Formation fine-grained access control (database, table, column, and row-level Data Cell Filters, LF-Tag-Based Access Control LF-TBAC, and IAMAllowedPrincipals hybrid-mode resolution… |
| `ingesting-into-data-lake` | Import data into the AWS data lake from S3 files, local uploads, JDBC databases (Oracle, SQL Server, PostgreSQL, MySQL, RDS, Aurora), Amazon Redshift, Snowflake, BigQuery, DynamoDB, or existing Glue catalog tables (migr… |
| `ingesting-streaming-and-cdc-data` | Configures continuous streaming delivery and analytical Change Data Capture (CDC) pipelines using Amazon Data Firehose (direct delivery to S3 Parquet, Amazon S3 Tables / Apache Iceberg with multi-table routing, Amazon R… |
| `managing-amazon-kinesis-data-streams` | Operates Amazon Kinesis Data Streams (KDS). |
| `managing-amazon-msk` | Operates Amazon MSK Provisioned clusters (Standard and Express brokers). |
| `migrate-to-msk` | Helps migrate self-managed Apache Kafka workloads to Amazon MSK Express. |
| `migrating-to-amazon-redshift` | Guides an end-to-end data-warehouse migration to Amazon Redshift — discovery, schema/SQL/stored-procedure/macro/script conversion, data migration, validation, performance comparison, and reporting. |
| `orchestrating-serverless-data-pipelines` | Designs and deploys event-driven and scheduled serverless data pipelines using AWS Step Functions (Glue, EMR Serverless, Athena, and Redshift Data API .sync integrations plus Distributed Map), Amazon EventBridge Rules a… |
| `provisioning-data-infrastructure-iac` | Packages AWS data engineering pipelines, Amazon S3 Tables (Iceberg), AWS Glue Data Catalogs, Connections, Jobs, and Data Quality rulesets, Amazon Redshift Serverless workgroups, Kinesis/MSK/ Firehose streams, AWS Step F… |
| `querying-data-lake` | Execute and manage Athena SQL queries across default and federated catalogs (Glue, S3 Tables, Redshift). |
| `redshift-guide` | Amazon Redshift is NOT PostgreSQL — corrects PostgreSQL-derived LLM mistakes; covers Redshift-specific SQL, DDL, COPY/UNLOAD, system views, metadata discovery, and operational patterns. |
| `signing-in-to-aws` | Gets AWS credentials for CLI/SDK access via `aws login`. |
| `testing-mwaa-workflow` | Tests Amazon MWAA workflow execution end-to-end: trigger a run and monitor it to completion for Provisioned (Python DAG, via Airflow REST API) and Serverless (YAML workflow, via StartWorkflowRun). |
| `upgrading-mwaa-environments` | Upgrades an MWAA environment to a newer Airflow version — within 2.x, within 3.x, or across the 2.x-to-3.x boundary. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). In Claude Code they are bound to the agent through its `tools:` allowlist.

| Server | Transport | Launch | Claude Code tool pattern | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0` `--skip-auth --metadata` | `mcp__plugin_aws-data-engineer_aws-mcp__*` |  |
| `dataprocessing` | stdio | `uvx awslabs.aws-dataprocessing-mcp-server@latest` | `mcp__plugin_aws-data-engineer_dataprocessing__*` | Read-only by default. Add --allow-write to let the agent create/modify Glue, EMR, and Athena resources. |
| `redshift` | stdio | `uvx awslabs.redshift-mcp-server@latest` | `mcp__plugin_aws-data-engineer_redshift__*` |  |
| `s3tables` | stdio | `uvx awslabs.s3-tables-mcp-server@latest` | `mcp__plugin_aws-data-engineer_s3tables__*` | Read-only by default. Add --allow-write to enable table creation and appends. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-data-engineer_cloudwatch__*` |  |
| `spark-troubleshooting` | stdio | `uvx mcp-proxy-for-aws@latest` `--service --region --read-timeout` | `mcp__plugin_aws-data-engineer_spark-troubleshooting__*` | Managed remote MCP (SageMaker Unified Studio) that diagnoses failed Spark jobs on EMR, Glue, and SageMaker notebooks. Uses your AWS credentials via SigV4. |

AWS credentials are inherited from the host environment (`AWS_PROFILE`, SSO, or instance role). In Claude Code `AWS_REGION` defaults to `us-east-1` when unset; the portable `mcp.json` can't express that default, so set `AWS_REGION` in your environment on other hosts. Codex starts MCP servers with a minimal environment: if a server can't see your profile, set `AWS_PROFILE`/`AWS_REGION` for it in `~/.codex/config.toml`.

## Hooks

- **PreToolUse** `Bash` — command: `sh -c 'python3 "$0" 2>/dev/null \|\| python "$0" 2>/dev/null \|\| py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `use_aws|mcp__aws.*|mcp__plugin_.*aws-.*mcp.*|mcp__plugin_.*awslocation.*|mcp__.*agentcore.*` — command: `sh -c 'python3 "$0" 2>/dev/null \|\| python "$0" 2>/dev/null \|\| py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`
- **PreToolUse** `Bash` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`
- **PreToolUse** `use_aws|mcp__aws.*|mcp__plugin_.*aws-.*mcp.*|mcp__plugin_.*awslocation.*|mcp__.*agentcore.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-gate.py"`

## Upstream

Derived from the following open-source sources (see the repository `NOTICE`):

- [`aws-data-analytics`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`aws-core`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`specialized-skills/analytics-skills`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
- [`specialized-skills/system-table-skills`](https://github.com/aws/agent-toolkit-for-aws) (aws/agent-toolkit-for-aws, Apache-2.0)
