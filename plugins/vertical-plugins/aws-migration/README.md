# AWS Migration and Modernization

Application, database, and cloud-to-AWS migration skills for the main agent: 7 Rs migration strategy & Strangler Fig decomposition, AWS Transform (.NET, Java, mainframe, SQL), AWS MGN & App2Container, DMS schema conversion & CDC cutover, Babelfish/SQL remediation, and Azure/GCP/Heroku to AWS migrations.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-migration@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-modernization-agent`](../../agent-plugins/aws-modernization-agent) or [`aws-database-engineer`](../../agent-plugins/aws-database-engineer) or [`aws-startup-advisor`](../../agent-plugins/aws-startup-advisor) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-migration:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-migration:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `app-data-layer-remediation` | Synchronizes application-layer SQL queries, stored procedure calls, and ORM persistence frameworks (JPA/Hibernate, MyBatis, EF Core) across Java, .NET, Node.js, and Python with DMS Schema Conversion… |
| `aws-transform` | Migrate, modernize, and upgrade codebases to AWS. |
| `azure-to-aws` | Migrate workloads from Microsoft Azure to AWS. |
| `dms-data-migration-execution` | >- |
| `dms-schema-conversion` | Handles the full DMS Schema Conversion lifecycle including creating migration projects, converting database schemas to a target engine, running compatibility assessments, navigating metadata trees, e… |
| `gcp-to-aws` | Migrate workloads from Google Cloud Platform to AWS — plus AI and agentic workloads from any provider. |
| `heroku-to-aws` | Migrate workloads from Heroku to AWS. |
| `legacy-vm-and-mainframe-replatform` | Guides legacy VM containerization via AWS App2Container (A2C 5-stage workflow for Java and .NET to ECS, EKS Standard/Auto Mode, App Runner) standalone and via AWS MGN SSM automation. |
| `modernization-parity-and-cutover` | Engineers functional, data, and performance parity for modernized workloads using automated unit tests, Testcontainers (PostgreSQL, Kafka), REST/event contract tests, mainframe batch/online record-re… |
| `modernization-strategy-and-strangler-fig` | Executes 7 Rs portfolio triage, bounded-context domain decomposition, distributed data patterns (Saga, Outbox, Idempotent Consumer), and multi-account Strangler Fig incremental routing using API Gate… |

## Commands

| Command | Description |
|---|---|
| `/aws-migration:cloud-to-aws-migration` | Generate a service-by-service mapping, IaC blueprint, and zero-downtime data migration plan from Azure, GCP, or Heroku to AWS. |
| `/aws-migration:convert-schema` | Convert commercial database schemas (Oracle, SQL Server) and application SQL to open-source Aurora/RDS using AWS DMS Schema Conversion and Babelfish. |
| `/aws-migration:migration-plan` | Build a phased 7 Rs AWS migration and modernization plan covering wave sequencing, MGN/DMS replication, and rollback runbooks. |
| `/aws-migration:modernize-code` | Modernize legacy .NET, Java, Python, Node.js, or mainframe code using AWS Transform with dependency analysis and test verification. |
| `/aws-migration:strangler-fig-cutover` | Design a Strangler Fig domain extraction and canary traffic cutover plan using API Gateway/ALB weighted routing, dual-write CDC, and parity validation. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-migration_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `aws-transform-mcp` | stdio | `uvx awslabs.aws-transform-mcp-server@latest` | `mcp__plugin_aws-migration_aws-transform-mcp__*` | AWS Transform code modernization (.NET, Java, mainframe, SQL) job orchestration. |
| `awsiac` | stdio | `uvx --with fastmcp<4.0.0 awslabs.aws-iac-mcp-server==0.2.14` | `mcp__plugin_aws-migration_awsiac__*` | CloudFormation & CDK template validation (`cfn-lint`), policy-as-code (`cfn-guard`), and CDK documentation. |
| `postgres` | stdio | `uvx awslabs.postgres-mcp-server@latest` | `mcp__plugin_aws-migration_postgres__*` | RDS / Aurora PostgreSQL schema inspection and read-only SQL diagnostics via RDS Data API. |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-migration_awspricing__*` | Real-time AWS service pricing catalog and architecture cost calculation. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-migration_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-migration_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-migration_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
