---
name: rds-oss
version: 1
description: "Advises on Amazon RDS open-source engines (MySQL, MariaDB, PostgreSQL) for instance creation, upgrade planning, commitment pricing, proxy evaluation, and Blue/Green deployments. Handles any RDS MySQL, MariaDB, or PostgreSQL question, including create a production-ready RDS MySQL instance, provision an RDS PostgreSQL database, run the RDS upgrade advisor for my RDS MySQL instance, what are my upgrade options, upgrade RDS MariaDB from 10.6 to the latest version, should I buy reserved instances or a savings plan for db.r7g.2xlarge RDS MySQL, change a VARCHAR to INT column on RDS MySQL 8.0 with Blue/Green, and does RDS Proxy help when PgBouncer already runs in transaction mode. Covers instance creation with production best practices, describe-db-instances and describe-db-engine-versions upgrade-target workflow, live prechecks via SSM or direct connection, RI versus DSP commitment pricing, RDS Proxy versus PgBouncer, and Blue/Green lifecycle with. Query live AWS state via MCP tools only (never raw aws CLI)."
---

# RDS OSS Advisor (MySQL, MariaDB, PostgreSQL)

> **MCP-Only Live AWS Execution:** Perform ALL live AWS API discovery, account/region checks (`sts:GetCallerIdentity`), cluster/instance/table inspection, CloudWatch telemetry, pricing (`awspricing`), and docs (`awsknowledge`) strictly via connected MCP tools (`aws-mcp` `aws___run_script` `call_boto3`, `dynamodb`, `elasticache`, `postgres`, `mysql`, `cloudwatch`, `awspricing`, `awsknowledge`) — **never invoke raw `aws ...` CLI commands (such as `aws --version` or `aws sts get-caller-identity`) in shell (`run_command`)**. Local offline helper scripts under `scripts/` may be run via `python3` or `node`.

## Overview

Advisor for Amazon RDS on the open-source engines — **MySQL**, **MariaDB**, and **PostgreSQL**. Five decision areas:

1. **Instance creation** — provision production-ready instances with best-practice defaults (latest version, Multi-AZ, encryption, Performance Insights, Secrets Manager password management)
2. **Upgrade planning** — identify instance, enumerate targets, run live prechecks, flag plan regressions, surface pre/post checklists
3. **Commitment pricing** — estimate RI and Database Savings Plan savings for steady workloads
4. **RDS Proxy evaluation** — decide whether proxy is worth it, based on connection utilization and pinning risks
5. **Blue/Green deployments** — plan low-downtime DDL or major upgrades, with DDL compatibility analysis

Produces cost estimates, precheck findings, and CLI commands. For instance creation, executes the create-db-instance call with production best practices. For upgrades, purchases, and switchovers — advisory only, never executes without explicit user confirmation.

Scoped to RDS open-source engines. For Aurora, use `amazon-aurora`. For Oracle, SQL Server, Db2, use the engine-specific skills.

The AWS MCP server is recommended for executing commands but is not required; all operations can also be performed via the AWS CLI.

## Decision Guide

| User asks about… | Go to |
|---|---|
| Create, provision, or set up a new RDS MySQL/MariaDB/PostgreSQL instance | [Production Instance Creation](#production-instance-creation) below |
| Upgrade, target version, pre/post-upgrade checklist, upgrade prechecks, Read Replica upgrade order | [references/upgrade-workflow.md](references/upgrade-workflow.md) |
| Reserved Instance, RI, Database Savings Plan, DSP, 1yr vs 3yr, Multi-AZ commitment, No/Partial/All Upfront | [references/commitment-pricing-workflow.md](references/commitment-pricing-workflow.md) |
| RDS Proxy, connection pooling, too many connections, Lambda DB connections, proxy pinning, PgBouncer vs Proxy | [references/proxy-advisor-workflow.md](references/proxy-advisor-workflow.md) |
| Blue/Green, zero-downtime DDL, switchover, schema change with minimal downtime, type change on production | [references/bluegreen-advisor-workflow.md](references/bluegreen-advisor-workflow.md) |

Broad request ("help me with RDS")? Present the five options as one line each. If the user supplied an instance ID, offer a general health check (engine + version + connection utilization) as entry point.

Out-of-scope (Aurora, Oracle, SQL Server, Db2, backup policy, Performance Insights deep-dive analysis): answer from general knowledge, note this skill doesn't cover it, point to the right engine-specific skill.

## RDS vs Aurora — Do Not Confuse

RDS open-source engines and Aurora are different products with different semantics. You MUST NOT apply Aurora concepts to RDS:

| Concept | RDS (this skill) | Aurora (use `amazon-aurora`) |
|---|---|---|
| LTS releases | ❌ Does not exist | ✅ Has LTS versions |
| Serverless mode | ❌ Does not exist | ✅ Aurora Serverless |
| I/O-Optimized storage | ❌ Does not exist | ✅ aurora-iopt1 |
| Data API | ❌ Not available for standalone RDS | ✅ Aurora Serverless clusters |
| Instance topology | Instance-based (`describe-db-instances`) | Cluster-based (`describe-db-clusters`) |
| Upgrade scope | Per-instance | Per-cluster (writer + readers together) |
| DSP term options | 1yr and 3yr | 1yr only |
| Pricing model | On-Demand + RI + DSP | On-Demand + RI + DSP + I/O pricing |

If a user asks about any Aurora-specific concept, route to `amazon-aurora`. If an instance turns out to be Aurora (engine = `aurora-mysql` or `aurora-postgresql`), stop and redirect.

## Production Instance Creation

When a user asks to create or provision a new RDS MySQL, MariaDB, or PostgreSQL instance for production use, you MUST apply the following best practices by default:

1. **Use the latest stable major version** — run `aws rds describe-db-engine-versions --engine <engine> --query "DBEngineVersions[].EngineVersion"` to find the latest. For MySQL, prefer 8.4.x over 8.0 (8.0 has an earlier end-of-standard-support date than 8.4 — see [RDS Extended Support](https://aws.amazon.com/rds/extended-support/) for dates). For PostgreSQL, use the latest major. For MariaDB, use the latest major.
2. **Enable Multi-AZ** — set `--multi-az` for automatic failover.
3. **Enable storage encryption using a customer-managed KMS key** — set `--storage-encrypted --kms-key-id <key-arn>`. A customer-managed key gives full control over key rotation, access policies, and cross-account sharing.
4. **Disable public access** — set `--no-publicly-accessible` to ensure the instance is not accessible from the internet.
5. **Set backup retention to 7 days** — set `--backup-retention-period 7`.
6. **Enable Performance Insights with 7-day retention** — set `--enable-performance-insights --performance-insights-retention-period 7`. If Performance Insights captures queries containing sensitive data (e.g., literal values in WHERE clauses), specify `--performance-insights-kms-key-id <key-arn>` to encrypt at rest with a customer-managed KMS key.
7. **Enable deletion protection** — set `--deletion-protection`.
8. **Avoid default master usernames** — do NOT use well-known names like `admin`, `root`, `postgres`, or `master`, which make credential-guessing attacks easier. Choose a custom `--master-username` (e.g., an application- or team-specific name).
9. **Manage master password via Secrets Manager** — set `--manage-master-user-password` instead of providing a plaintext `--master-user-password`. This creates and rotates the password automatically in Secrets Manager. Do NOT accept or use a plaintext password for production instances.
10. **Use gp3 storage** — set `--storage-type gp3`. It's cheaper and faster than gp2 with no minimum IOPS purchase.
11. **Tag the instance so customers can identify resources created via this skill** — set `--tags Key=created_by,Value=rds-oss-skill Key=generation_model,Value={your-model-id}` (see Resource tagging below).
12. **Enforce TLS for connections in transit** — create or modify the DB parameter group to require encrypted connections: `require_secure_transport=ON` for MySQL/MariaDB, `rds.force_ssl=1` for PostgreSQL.
13. **Export database logs to CloudWatch Logs and encrypt with KMS** — set `--enable-cloudwatch-logs-exports` so database-level security events (failed logins, suspicious queries) are centrally visible. Use `["error","slowquery","audit"]` for MySQL/MariaDB (note: the `audit` stream requires audit logging to be enabled first, otherwise it is empty — on RDS MySQL via the MARIADB_AUDIT_PLUGIN in an Option Group, on RDS MariaDB via the built-in server audit parameters such as `server_audit_logging=1` in a parameter group) and `["postgresql"]` for PostgreSQL. Database logs can contain SQL with literal values and usernames, so you MUST configure a KMS key on the resulting `/aws/rds/instance/<name>/*` log groups to protect sensitive data at rest.

**Example CLI (MySQL 8.4, production-ready):**

```bash
aws rds create-db-instance \
  --db-instance-identifier <name> \
  --engine mysql \
  --engine-version 8.4 \
  --db-instance-class <class> \
  --allocated-storage 100 \
  --storage-type gp3 \
  --storage-encrypted \
  --kms-key-id <kms-key-arn> \
  --no-publicly-accessible \
  --multi-az \
  --manage-master-user-password \
  --master-username <custom-non-default-username> \
  --backup-retention-period 7 \
  --enable-performance-insights \
  --performance-insights-retention-period 7 \
  --performance-insights-kms-key-id <kms-key-arn> \
  --deletion-protection \
  --enable-cloudwatch-logs-exports '["error","slowquery","audit"]' \
  --tags Key=created_by,Value=rds-oss-skill Key=generation_model,Value=<your-model-id> \
  --region us-east-1
```

After instance creation, run the following commands to configure TLS enforcement and log group encryption (these are user-executed steps that the skill presents but does not invoke directly):

```bash
# Create a custom parameter group with TLS enforcement (MySQL example)
aws rds create-db-parameter-group --db-parameter-group-family mysql8.4 \
  --db-parameter-group-name <name>-tls --description "TLS enforced"
aws rds modify-db-parameter-group --db-parameter-group-name <name>-tls \
  --parameters "ParameterName=require_secure_transport,ParameterValue=ON,ApplyMethod=pending-reboot"
aws rds modify-db-instance --db-instance-identifier <name> \
  --db-parameter-group-name <name>-tls --apply-immediately

# Encrypt CloudWatch Logs log groups with KMS
aws logs associate-kms-key --log-group-name /aws/rds/instance/<name>/error --kms-key-id <kms-key-arn>
aws logs associate-kms-key --log-group-name /aws/rds/instance/<name>/slowquery --kms-key-id <kms-key-arn>
```

**Constraints:**

- You MUST use `--manage-master-user-password` for production. NEVER use `--master-user-password` with a plaintext password for production instances.
- You MUST check the latest available engine version via `describe-db-engine-versions` rather than hardcoding a version.
- You MUST enable Multi-AZ, encryption, Performance Insights (7-day), backup retention (7 days), and deletion protection unless the user explicitly says otherwise.
- If the user says "production" or "production-ready", apply ALL of the above without asking.

### Resource tagging (always apply on resource creation)

When creating any RDS instance (`create-db-instance`), ALWAYS include these tags using the RDS list-of-records `--tags` syntax:

`--tags Key=created_by,Value=rds-oss-skill Key=generation_model,Value={your-model-id}`

Example: `--tags Key=created_by,Value=rds-oss-skill Key=generation_model,Value=claude-sonnet-4-20250514`

Include these tags even if the user does not mention tagging, so that they can identify the resources created via this skill. If the user provides additional tags, append these to their tags rather than replacing them. The same applies when tagging via `add-tags-to-resource` or during blue/green deployments.

## Common Tasks

### 1. Verify Dependencies

See [references/verify-dependencies.md](references/verify-dependencies.md) for tool and credential requirements before running workflows.

### 2. Classify and Route

Use the [Decision Guide](#decision-guide) to choose a workflow reference, the catalog presentation (broad requests), or a general-knowledge answer (out-of-scope).

**Constraints:**

- You MUST name the workflow you're routing to
- You MUST pass along instance ID, region, engine, or workload details the user already supplied — do not re-ask
- You MAY ask one clarifying question if a request straddles two workflows (e.g., "upgrade with minimal downtime" = upgrade + Blue/Green)
- You MUST NOT route Aurora, Oracle, SQL Server, or Db2 questions here — those engines have different tooling

### 3. Execute the Workflow

Load the matching reference and follow its `## Tasks` section.

**Constraints:**

- You MUST explain what step is executing and which tool is being called before running it
- You MUST NOT execute `modify-*`, `switchover-*`, purchase APIs, or `create-db-proxy`. Allowed: `create-db-instance` (for new instance provisioning), `describe-*`, `list-*`, `get-*`, `send-command` for SSM prechecks.
- You MUST NOT handle DB credentials directly. Use user-supplied secret ARNs, pre-configured SSM parameters, or ask the user to paste script output.
- When a live call or bundled script cannot run, You MUST report the exact blocker and either execute the offline fallback or ask the user for inputs. You MUST NOT fabricate command output, analyzer results, pricing numbers, or version lists — a plausible-looking answer with no factual basis is worse than refusing, because users act on it.
- If multiple workflows ran, close with a 2–4 line synthesis linking to prior outputs.

Each workflow reference includes its own tool-call examples.

## Extended Reference, Critical Facts & Troubleshooting

**IMPORTANT:** Before answering domain-specific questions, troubleshooting errors, or applying rubric checklists, read [`references/rds-oss-security-and-troubleshooting.md`](references/rds-oss-security-and-troubleshooting.md) for the complete verbatim critical facts, workflows, security controls, and troubleshooting playbooks.
