# AWS Storage

Cloud storage architecture, security, and operations for the main agent: Amazon S3 (Storage Lens, Intelligent-Tiering, Object Lock, S3 Tables), EFS performance & mount troubleshooting, EBS gp3/io2, FSx, AWS Backup vault lock, KMS data protection, and cross-region DR replication.

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install aws-storage@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## How it works

This is a **vertical plugin**: its skills, slash commands, hooks, and MCP servers attach directly to your main agent with no sub-agent hand-off. Prefer the [`aws-platform-engineer`](../../agent-plugins/aws-platform-engineer) or [`aws-solutions-architect`](../../agent-plugins/aws-solutions-architect) or [`aws-cloud-security-engineer`](../../agent-plugins/aws-cloud-security-engineer) agent plugin when you want an isolated specialist sub-agent instead.

- Skills activate automatically from their descriptions, or invoke one explicitly in Claude Code with `/aws-storage:<skill>`.
- Slash commands orchestrate multi-step operational workflows directly in your main session (`/aws-storage:<command>`).

## Skills

| Skill | What it does |
|---|---|
| `aws-resilience-dr-and-migration-architecture` | Architects RTO/RPO-driven Multi-Region Disaster Recovery topologies (Backup & Restore, Pilot Light, Warm Standby, Active-Active), Cell-Based Architectures & Shuffle Sharding, Route 53 ARC (Zonal Auto… |
| `aws-storage` | Selects, investigates, and compares AWS object, file, and block storage services, and answers cost, performance, configuration, security, and troubleshooting questions about storage services. |
| `securing-s3-buckets` | > |
| `security-data-protection` | >- |
| `troubleshooting-efs` | > |
| `troubleshooting-s3-files` | > |

## Commands

| Command | Description |
|---|---|
| `/aws-storage:audit-s3-security` | Audit Amazon S3 buckets for Block Public Access, bucket policies, SSE-KMS encryption, Object Lock, TLS enforcement, and access logging. |
| `/aws-storage:backup-and-replication-plan` | Design an immutable cross-region backup and replication strategy using AWS Backup Vault Lock, S3 CRR, and EFS replication. |
| `/aws-storage:optimize-storage-tiers` | Analyze S3 Storage Lens metrics and EBS/EFS volumes to recommend Intelligent-Tiering, lifecycle policies, and gp2-to-gp3 migration. |
| `/aws-storage:troubleshoot-efs` | Diagnose Amazon EFS mount failures, NFS security groups, throughput/IOPS throttling, and burst credit depletion. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable); started when the plugin is enabled and bound to the main agent.

| Server | Transport | Launch | Claude Code tool names | Notes |
|---|---|---|---|---|
| `aws-mcp` | stdio | `uvx mcp-proxy-for-aws-cli==1.7.0 https://aws-mcp.us-east-1.api.aws/mcp --skip-auth --metadata INSTALL_SOURCE=agent-toolkit-core` | `mcp__plugin_aws-storage_aws-mcp__*` | AWS CLI & API proxy (`aws___call_aws`, `aws___search_documentation`, `aws___read_documentation`). |
| `s3tables` | stdio | `uvx awslabs.s3-tables-mcp-server@latest` | `mcp__plugin_aws-storage_s3tables__*` | Amazon S3 Tables (managed Apache Iceberg) catalog and table operations. |
| `cloudwatch` | stdio | `uvx awslabs.cloudwatch-mcp-server@latest` | `mcp__plugin_aws-storage_cloudwatch__*` | CloudWatch Metrics, Logs Insights queries, Alarms, and live telemetry inspection. |
| `awspricing` | stdio | `uvx awslabs.aws-pricing-mcp-server@latest` | `mcp__plugin_aws-storage_awspricing__*` | Real-time AWS service pricing catalog and architecture cost calculation. |
| `awsiac` | stdio | `uvx --with fastmcp<4.0.0 awslabs.aws-iac-mcp-server==0.2.14` | `mcp__plugin_aws-storage_awsiac__*` | CloudFormation & CDK template validation (`cfn-lint`), policy-as-code (`cfn-guard`), and CDK documentation. |

## Hooks

- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-storage_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.…`
- **PreToolUse** `Bash|use_aws|mcp__aws.*|mcp__plugin_aws-storage_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/aws-mutation-g…`
