---
name: rds-sqlserver
version: 1
description: "Full-lifecycle management, administration, and connectivity troubleshooting for Amazon RDS for SQL Server and RDS Custom for SQL Server. Covers Multi-AZ Always On Availability Groups (EE) vs Database Mirroring (SE), native .bak backup and restore to Amazon S3 via msdb.dbo.rds_backup_database and rds_restore_database, Option Groups (SSIS, SSRS, SSAS, TDE, Audit), tempdb contention tuning (PAGELATCH_UP/EX), licensing (License Included vs BYOL), and RDS Custom for SQL Server (OS/sysadmin access, CLR, Linked Servers, Support Perimeter). Also provides connectivity, authentication, and troubleshooting guidance for SSMS timeouts, Cannot generate SSPI context, Lambda with pymssql, auth_scheme NTLM vs KERBEROS on ECS Fargate, SSM tunnels, AWS Managed Microsoft AD, SPNs, RDS Proxy IAM auth, and error 18456. Query live AWS state via MCP tools only (never raw aws CLI)."
---

# Amazon RDS for SQL Server & RDS Custom — Lifecycle, Administration & Connectivity

> **MCP-Only Live AWS Execution:** Perform ALL live AWS API discovery, account/region checks (`sts:GetCallerIdentity`), cluster/instance/table inspection, CloudWatch telemetry, pricing (`awspricing`), and docs (`awsknowledge`) strictly via connected MCP tools (`aws-mcp` `aws___run_script` `call_boto3`, `dynamodb`, `elasticache`, `postgres`, `mysql`, `cloudwatch`, `awspricing`, `awsknowledge`) — **never invoke raw `aws ...` CLI commands (such as `aws --version` or `aws sts get-caller-identity`) in shell (`run_command`)**. Local offline helper scripts under `scripts/` may be run via `python3` or `node`.

## Safety guidance

This skill covers creating and modifying RDS for SQL Server resources when the user requests it. The agent MUST confirm the action with the user before executing. Do NOT execute any create or modify operation without explicit user confirmation (e.g., "yes", "proceed", "confirmed", "go ahead"). If the user has not confirmed, present the planned action and ask for approval.

### Execute these operations (after user confirmation)

- Create an instance: `create-db-instance` (requires a DB subnet group; RDS SQL Server is VPC-only and not publicly accessible by default)
- Create a custom parameter group: `create-db-parameter-group` (family `sqlserver-ex-15.00`, `sqlserver-se-15.00`, etc.) — needed to set `rds.force_ssl=1` among others
- Create an option group: `create-option-group` (for TDE, S3 integration, SQLServer Audit, Native Backup/Restore, SSIS, SSAS, SSRS)
- Create an RDS Proxy: `create-db-proxy`, `register-db-proxy-targets` (for IAM DB auth in front of SQL Server — see the rds-proxy reference)
- Create an AWS Managed Microsoft AD directory for Windows auth: `create-directory` (then associate via `modify-db-instance --domain`)
- Create a Secrets Manager secret with rotation: `create-secret`, `rotate-secret --rotation-rules AutomaticallyAfterDays=N`
- Change backup retention, deletion protection, log exports: `modify-db-instance --backup-retention-period` / `--deletion-protection` / `--cloudwatch-logs-export-configuration`
- Attach/detach parameter group or option group: `modify-db-instance --db-parameter-group-name / --option-group-name`
- Tag resources: `add-tags-to-resource`, `remove-tags-from-resource`

### Resource tagging (always apply on resource creation)

When creating any RDS for SQL Server resource (`create-db-instance`, `create-db-parameter-group`, `create-option-group`, `create-db-proxy`, `create-secret` for RDS credentials, `create-directory` for Windows auth), ALWAYS include these tags using the RDS list-of-records `--tags` syntax (AWS Directory Service and Secrets Manager use the same shape):

`--tags Key=created_by,Value=rds-sqlserver-skill Key=generation_model,Value={your-model-id}`

Example: `--tags Key=created_by,Value=rds-sqlserver-skill Key=generation_model,Value=claude-sonnet-4-20250514`

Include these tags even if the user does not mention tagging, so that they can identify the resources created via this skill. If the user provides additional tags, append these to their tags rather than replacing them. The same applies when tagging via `add-tags-to-resource` on existing resources.

### Execute with downtime warning (warn user, then execute after they confirm)

- Change instance class: `modify-db-instance --db-instance-class` — warn: "This causes a failover in Multi-AZ configurations and brief unavailability on single-AZ instances."
- Minor engine version upgrade: `modify-db-instance --engine-version` within the same major (e.g., 15.00.4X → 15.00.4Y) — warn: "This triggers a restart and may cause a brief outage."
- Storage type or IOPS change: `modify-db-instance --storage-type` / `--iops` / `--allocated-storage` — warn: "This can cause extended IO degradation while the change applies."
- Apply immediately: any `modify-db-instance --apply-immediately` — warn: "This applies outside the maintenance window and may cause downtime now."
- Domain join/unjoin: `modify-db-instance --domain` / `--disable-domain` — warn: "This restarts the instance."

### Do NOT execute (refuse, explain why, offer assessment instead)

- Delete instance: `delete-db-instance` — irreversible data loss
- Delete automated backups: `delete-db-instance --delete-automated-backups` — destroys point-in-time recovery history
- Failover: `reboot-db-instance --force-failover` — production impact
- Major version upgrade: `modify-db-instance --engine-version` across major versions (e.g., 15.0 → 16.0) — requires prechecks and a rollback plan; should go through change-control
- Reboot: `reboot-db-instance` — production impact
- Enable public accessibility: `modify-db-instance --publicly-accessible true` — security regression; use SSM port forwarding, VPN, or Direct Connect

When refusing, explain why and offer the matching assessment workflow:
> "I can't perform [action] because [reason]. I can run an assessment to help you decide. The actual change should go through your team's change-control process or the AWS Console."

## Overview

Amazon RDS for SQL Server is the managed SQL Server service from AWS (with RDS Custom for SQL Server available when host OS or full `sysadmin` access is required). This skill covers both **database lifecycle & administration** (Multi-AZ Always On Availability Groups on Enterprise Edition vs. Database Mirroring on Standard Edition, native `.bak` backup and restore to Amazon S3 via `msdb.dbo.rds_backup_database` and `msdb.dbo.rds_restore_database`, Option Groups for SSIS/SSRS/SSAS/TDE, `tempdb` allocation contention tuning, licensing, and RDS Custom for SQL Server) and the **connection lifecycle** (driver selection, connection strings, SSL/TLS encryption, SQL and Windows/Kerberos authentication, IAM authentication via RDS Proxy, connection pooling, VPC networking, deployment patterns for EC2 / ECS / Lambda / EKS, and troubleshooting).

This skill works with the AWS CLI directly. The AWS MCP server is recommended but not required — it adds sandboxed execution, CloudTrail audit, and observability when available.

## Common Tasks

### 1. Verify Dependencies

Check for required tools and warn the user if any are missing.

**Constraints:**

- You MUST use connected MCP tools (`aws-mcp` `call_boto3`) for live AWS API calls rather than raw `aws` CLI
- You MUST inform the user if the AWS CLI is missing, because most steps need AWS API access
- If the AWS MCP server tools (`call_aws`, `suggest_aws_commands`) are available, prefer them for audit and observability — but they are NOT required

### 2. Classify and Route

Collect the connection or administration context and route to the right sub-skill reference file.

Parameters (for connectivity workflows):

- **language** (required for connectivity): `python` | `dotnet` | `java` | `nodejs`. Infer from project files (`requirements.txt`/`*.py` → python; `*.csproj` → dotnet; `pom.xml`/`build.gradle` → java; `package.json` → nodejs). Ask only if ambiguous.
- **runtime** (required for connectivity): `ec2` | `ecs` | `lambda` | `eks` | `laptop`. Drives networking + secrets pattern.
- **auth** (required for connectivity): `sql` | `windows-kerberos` | `windows-ntlm` | `iam-proxy`. Default `sql` unless the user mentions Active Directory, Kerberos, NTLM, or IAM.
- **region** (required): AWS region, e.g. `us-east-1`.
- **db_instance_id** (required for troubleshooting/admin): RDS instance identifier.

**Constraints:**

- You MUST ask for all required parameters upfront in a single prompt, because iterative questioning frustrates users
- You MUST infer `language` from project files when available rather than asking
- You MUST validate `region` against the enumerated list of AWS regions before proceeding
- You SHOULD default to SQL authentication unless the user explicitly says Windows auth, IAM auth, or Active Directory

#### Sub-skill routing

Load the matching lifecycle or driver/topic reference files:

| User is doing | Load |
|---|---|
| Always On AGs / Mirroring / native `.bak` backup & restore to S3 / `rds_backup_database` / `rds_restore_database` / SSIS / SSRS / SSAS / TDE / `tempdb` contention / licensing / RDS Custom / `sysadmin` | [references/lifecycle-and-admin.md](references/lifecycle-and-admin.md) |
| Python / pymssql / pyodbc | [references/python.md](references/python.md) |
| .NET / C# / Microsoft.Data.SqlClient | [references/dotnet.md](references/dotnet.md) |
| Java / JDBC / mssql-jdbc | [references/java.md](references/java.md) |
| Node.js / tedious / mssql | [references/nodejs.md](references/nodejs.md) |
| EC2 hosting | [references/ec2-vpc.md](references/ec2-vpc.md) |
| Lambda hosting | [references/lambda-vpc.md](references/lambda-vpc.md) |
| ECS or Fargate hosting | [references/ecs-fargate-vpc.md](references/ecs-fargate-vpc.md) |
| Laptop via SSM tunnel | [references/ssm-tunneling.md](references/ssm-tunneling.md) |
| SSL/TLS, rds.force_ssl, certificates | [references/encryption.md](references/encryption.md) |
| Windows / AD / Kerberos / NTLM | [references/ad-kerberos.md](references/ad-kerberos.md) |
| Cross-VPC, Transit Gateway, VPC peering | [references/networking.md](references/networking.md) |
| SQL auth, Secrets Manager, credentials | [references/connection-auth.md](references/connection-auth.md) |
| IAM auth, RDS Proxy, connection pooling | [references/rds-proxy.md](references/rds-proxy.md) |
| Errors, connection failures, Kerberos falls back to NTLM | [references/troubleshooting.md](references/troubleshooting.md) |

### 3. Execute the Workflow

Follow the steps in the loaded reference files in order: driver setup → networking → auth → secrets → verify.

**Constraints:**

- You MUST use `TLS 1.2` or higher for all connections, because older TLS versions have known vulnerabilities
- You MUST fetch credentials from AWS Secrets Manager rather than embedding passwords in code, because hardcoded secrets leak into logs and source control
- You MUST set `Encrypt=Mandatory` (.NET) / `encrypt=true` (JDBC) / `encryption="require"` (pymssql) / `encrypt: true` (tedious) in production, because opportunistic encryption may silently fall back to plaintext
- You MUST verify server certificate chain using the RDS CA bundle from `https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem` rather than setting `TrustServerCertificate=true` in production, because disabling verification exposes you to MITM attacks
- You MUST NOT enable `PubliclyAccessible: true` on the DB instance, because it exposes SQL Server port 1433 to the public internet
- You MUST use security group IDs as the source for same-VPC access and CIDR blocks for cross-VPC access via Transit Gateway or VPC peering, because SG references don't cross VPC boundaries
- You MUST NOT use IAM authentication directly against RDS for SQL Server, because RDS for SQL Server does not support it — IAM auth requires RDS Proxy in front of the instance
- You MUST test Windows authentication from a domain-joined host (EC2 or client), not via SSM send-command, because SSM runs as the system account, not the user's AD identity
- You SHOULD prefer Kerberos over NTLM when both are available, because Kerberos is cryptographically stronger and easier to audit
- You SHOULD use `pyodbc` instead of `pymssql` when the application requires Kerberos/Windows authentication, because pymssql does not support Kerberos

## Extended Reference, Critical Facts & Troubleshooting

**IMPORTANT:** Before answering domain-specific questions, troubleshooting errors, or applying rubric checklists, read [`references/rds-sqlserver-troubleshooting-and-handoff.md`](references/rds-sqlserver-troubleshooting-and-handoff.md) for the complete verbatim critical facts, workflows, security controls, and troubleshooting playbooks.
