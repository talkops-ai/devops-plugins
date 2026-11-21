---
name: rds-oracle
version: 1
description: "Full-lifecycle management, administration, and connectivity troubleshooting for Amazon RDS for Oracle and RDS Custom for Oracle. Covers CDB/PDB multitenant architecture, rdsadmin stored procedures, Option Groups (TDE, Native Network Encryption, Timezone, APEX, OEM, STATSPACK, S3_INTEGRATION), Oracle Data Pump and RMAN backups to S3, License Included (SE2) vs BYOL (EE/SE2) and Optimize CPUs, and RDS Custom for Oracle (OS/SYSDBA access, Custom Engine Versions, Support Perimeter). Also diagnoses and resolves connectivity, authentication, networking, and driver issues including Python Lambda in a VPC with pooling and cold-start optimization, EKS pods via Secrets Manager CSI driver with IRSA and SecretProviderClass, ORA-12170 cross-VPC timeouts, DPI-1047 errors, and Oracle Connection Manager (CMAN) on EC2 with HA across two AZs. Query live AWS state via MCP tools only (never raw aws CLI)."
---

# Amazon RDS for Oracle & RDS Custom — Lifecycle, Administration & Connectivity

> **MCP-Only Live AWS Execution:** Perform ALL live AWS API discovery, account/region checks (`sts:GetCallerIdentity`), cluster/instance/table inspection, CloudWatch telemetry, pricing (`awspricing`), and docs (`awsknowledge`) strictly via connected MCP tools (`aws-mcp` `aws___run_script` `call_boto3`, `dynamodb`, `elasticache`, `postgres`, `mysql`, `cloudwatch`, `awspricing`, `awsknowledge`) — **never invoke raw `aws ...` CLI commands (such as `aws --version` or `aws sts get-caller-identity`) in shell (`run_command`)**. Local offline helper scripts under `scripts/` may be run via `python3` or `node`.

## Safety guidance

This skill covers creating and modifying RDS for Oracle resources when the user requests it. The agent MUST confirm the action with the user before executing. Do NOT execute any create or modify operation without explicit user confirmation (e.g., "yes", "proceed", "confirmed", "go ahead"). If the user has not confirmed, present the planned action and ask for approval.

### Execute these operations (after user confirmation)

- Create an instance: `create-db-instance` (requires a DB subnet group; RDS Oracle is VPC-only and not publicly accessible by default)
- Create a custom parameter group: `create-db-parameter-group` (family `oracle-se2-19`, `oracle-ee-19`, etc.)
- Create an option group: `create-option-group` (for Oracle Native Network Encryption, TLS/TCPS, S3 integration, APEX, Spatial)
- Change backup retention: `modify-db-instance --backup-retention-period`
- Enable/disable deletion protection: `modify-db-instance --deletion-protection`
- Change CloudWatch log exports: `modify-db-instance --cloudwatch-logs-export-configuration`
- Attach/detach parameter group or option group: `modify-db-instance --db-parameter-group-name / --option-group-name`
- Tag resources: `add-tags-to-resource`, `remove-tags-from-resource`

### Resource tagging (always apply on resource creation)

When creating any RDS for Oracle resource (`create-db-instance`, `create-db-parameter-group`, `create-option-group`, `create-db-instance-read-replica`), ALWAYS include these tags using the RDS list-of-records `--tags` syntax:

`--tags Key=created_by,Value=rds-oracle-skill Key=generation_model,Value={your-model-id}`

Example: `--tags Key=created_by,Value=rds-oracle-skill Key=generation_model,Value=claude-sonnet-4-20250514`

Include these tags even if the user does not mention tagging, so that they can identify the resources created via this skill. If the user provides additional tags, append these to their tags rather than replacing them. The same applies when tagging via `add-tags-to-resource` on existing resources.

### Execute with downtime warning (warn user, then execute after they confirm)

- Change instance class: `modify-db-instance --db-instance-class` — warn: "This causes a failover in Multi-AZ configurations and brief unavailability on single-AZ instances."
- Minor engine version upgrade: `modify-db-instance --engine-version` within the same major (e.g., 19.0.0.0.ru-2024-01 → 19.0.0.0.ru-2024-04) — warn: "This triggers a restart and may cause a brief outage."
- Storage type or IOPS change: `modify-db-instance --storage-type` / `--iops` — warn: "This can cause extended IO degradation while the change applies."
- Apply immediately: any `modify-db-instance --apply-immediately` — warn: "This applies outside the maintenance window and may cause downtime now."

### Do NOT execute (refuse, explain why, offer assessment instead)

- Delete instance: `delete-db-instance` — irreversible data loss
- Delete automated backups: `delete-db-instance --delete-automated-backups` — destroys point-in-time recovery history
- Force failover: `reboot-db-instance --force-failover` — production impact
- Major version upgrade: `modify-db-instance --engine-version` across major versions (e.g., 19c → 21c) — requires prechecks, option group migration, and a rollback plan; should go through change-control
- Reboot: `reboot-db-instance` — production impact
- Promote a read replica: `promote-read-replica` — breaks replication and is rarely reversible
- Enable public accessibility: `modify-db-instance --publicly-accessible true` — security regression; use SSM port forwarding, VPN, or Direct Connect instead (per the Overview's security posture)

When refusing, explain why and offer the matching assessment workflow:
> "I can't perform [action] because [reason]. I can run an assessment to help you decide. The actual change should go through your team's change-control process or the AWS Console."

## Overview

Amazon RDS for Oracle is a managed Oracle Database service (with RDS Custom for Oracle available when OS/SYSDBA access is required). This skill covers both **database lifecycle & administration** (CDB/PDB multitenant architecture, `rdsadmin` package replacements for `ALTER SYSTEM`, Option Groups, Oracle Data Pump and RMAN backups via `S3_INTEGRATION`, License Included vs. BYOL with Optimize CPUs, and RDS Custom for Oracle) and the **connection lifecycle** (private-subnet networking on port 1521, cross-VPC peering or Transit Gateway, TLS/TCPS and Native Network Encryption (NNE), username/password auth with AWS Secrets Manager, Kerberos with AWS Managed Microsoft AD, language connection pooling, EC2/ECS Fargate/EKS/Lambda patterns, SSM port forwarding, Oracle Connection Manager (CMAN) on EC2 for HA multiplexing, and driver troubleshooting).

Key constraints: RDS Oracle does **NOT** support RDS Proxy, does not allow SYS/SYSTEM logins on standard RDS (use `rdsadmin.rdsadmin_util` or RDS Custom if true SYSDBA is needed), and is not publicly accessible by default — external access uses SSM port forwarding, VPN, or Direct Connect.

Routes to one of nine sub-skills: **lifecycle-and-admin**, **networking**, **connection-auth**, **compute-runtime**, **encryption**, **cman-proxy**, **client-tools**, **ssm-tunneling**, **troubleshooting**. Load only the matching reference.

## Security Considerations

- **Encryption at rest:** Enable `--storage-encrypted` (and optionally `--kms-key-id <key-arn>`) when creating the instance. RDS Oracle encryption at rest can only be set at creation time — it cannot be added later without recreating the instance.
- **Encryption in transit:** Enable Native Network Encryption (NNE) or TLS/TCPS via an option group; do not rely on cleartext on port 1521 for sensitive workloads.
- **Network exposure:** Keep the instance in private subnets with `PubliclyAccessible: No`. Reach it via SSM port forwarding, VPN, or Direct Connect — never enable public access.
- **Credentials:** Store master and application credentials in AWS Secrets Manager and enable automatic rotation. Never hardcode credentials in code, connection strings, or logs.
- **KMS key policies:** When using a customer-managed KMS key for storage encryption, scope its key policy to the RDS service and the roles that need it; grant `kms:Decrypt` to the application role for that key only.
- **Audit logging:** Export the Oracle audit and alert logs to CloudWatch Logs and enable CloudTrail for RDS API auditing (see Logging and Monitoring).

## Common Tasks

### Verify Dependencies

Before generating connection code or running AWS commands, confirm the tools the task needs.

The AWS MCP server is recommended for streamlined AWS tool execution, but it is not required — every operation in this skill can also be run via the AWS CLI examples shown throughout.

- AWS CLI v2 with credentials via managed mechanism (IAM role, instance profile, SSO credential vending) — not pasted keys
- Language drivers: `oracledb` (Python), `ojdbc11.jar` (Java 11+), `oracledb` (Node ≥ 6), `Oracle.ManagedDataAccess.Core` (.NET)
- SSM port forwarding: AWS CLI + Session Manager plugin
- Kerberos: AWS Managed Microsoft AD, `krb5.conf`, `okinit` tool
- CMAN: Oracle Enterprise Edition BYOL license + full Oracle Client install (Instant Client is insufficient)

**Constraints:**

- The agent MUST check dependencies before generating code or running AWS commands.
- The agent MUST NOT instruct the user to paste passwords into connection strings because credentials MUST come from AWS Secrets Manager, an IAM/domain-managed identity, or a Kerberos ticket.
- The agent MUST tell the user which dependencies are missing and MUST respect the user's decision to abort.
- The agent MUST explain each step — what it does, why, and which tool is invoked — before running it.

### Classify and Route

Map the user's question to the correct sub-skill reference, then load only those files.

| User says | Load |
|---|---|
| CDB / PDB / multitenant / `rdsadmin` / Option Group / Data Pump / `expdp` / `impdp` / RMAN / S3_INTEGRATION / BYOL / License Included / Optimize CPUs / RDS Custom / SYSDBA / CEV | [lifecycle-and-admin.md](references/lifecycle-and-admin.md) |
| SG / VPC peering / TGW / Route 53 / port 1521 / CIDR | [networking.md](references/networking.md) |
| connect / connection string / python-oracledb / JDBC / node-oracledb / ODP.NET / Secrets Manager / auth / Kerberos | [connection-auth.md](references/connection-auth.md) + language reference ([python.md](references/python.md), [java.md](references/java.md), [nodejs.md](references/nodejs.md), [dotnet.md](references/dotnet.md)) |
| Lambda / EC2 / ECS Fargate / EKS / container / serverless / IRSA | [compute-runtime.md](references/compute-runtime.md) |
| SQL Developer / Toad / SQLcl / DBeaver / sqlplus / GUI | [client-tools.md](references/client-tools.md) |
| SSL / TLS / TCPS / NNE / encrypt / FIPS / cipher | [encryption.md](references/encryption.md) |
| CMAN / Connection Manager / proxy / multiplex / RDS Proxy | [cman-proxy.md](references/cman-proxy.md) |
| SSM / port forward / tunnel / localhost / laptop | [ssm-tunneling.md](references/ssm-tunneling.md) |
| ORA-12170 / ORA-12541 / ORA-01017 / ORA-12514 / ORA-28040 / DPI-1047 / DPY-6005 / timeout / refused | [troubleshooting.md](references/troubleshooting.md) |

**Constraints:**

- The agent MUST read only reference files matching the user's question, to keep context focused.
- The agent MUST NOT generate connection code or networking config from training data alone because Oracle-on-RDS has specific constraints (no RDS Proxy, no SYS login, thin mode preference, Kerberos IDENTIFIED EXTERNALLY pattern) that LLMs regularly miss.
- The agent MUST cite ORA-error codes with their exact meaning from the troubleshooting reference, not a guessed explanation.
- If a question spans multiple sub-skills (e.g. "ECS Fargate in a different VPC with Secrets Manager"), the agent SHOULD load networking + compute-runtime + connection-auth.

### Execute Workflow

Once routed, give the user a concrete, runnable answer grounded in the reference file.

Parameter acquisition:

- All required parameters (region, instance id, endpoint, service/SID, source VPC CIDR, SG ids, Secrets Manager ARN, client language/runtime) MUST be collected upfront in a single message.
- Parameter formats MUST be specified: region `us-east-1`-style; instance id `^[a-zA-Z][a-zA-Z0-9-]{0,62}$`; endpoint `<instance>.<hash>.<region>.rds.amazonaws.com`; CIDR `a.b.c.d/n`; ARN `arn:aws:<service>:<region>:<account>:...`.
- The agent MUST accept parameters via direct input, a JSON/YAML file path, or a URL.

Tool use:

- Use AWS CLI for AWS operations (example: `aws ec2 authorize-security-group-ingress --group-id sg-123 --protocol tcp --port 1521 --source-group sg-456`).
- Use bundled scripts — [test_connectivity.sh](scripts/test_connectivity.sh), [check_rds_status.sh](scripts/check_rds_status.sh), [check_security_groups.sh](scripts/check_security_groups.sh), [test_oracle_connection.py](scripts/test_oracle_connection.py), [check_ssl_status.sql](scripts/check_ssl_status.sql) — for diagnostics.
- Write plans, HA architectures, troubleshooting reports to `artifacts/<app-name>/`.

**Constraints:**

- The agent MUST NOT recommend enabling public access on RDS Oracle because public RDS increases the attack surface — use SSM port forwarding, VPN, or Direct Connect.
- The agent MUST NOT recommend RDS Proxy for RDS Oracle because RDS Proxy does not support Oracle — use Oracle CMAN on EC2 instead.
- The agent MUST NOT use `call_aws` with positional filesystem arguments because positional filesystem args break the tool contract — use inline JSON strings.
- The agent MUST prefer thin-mode drivers (python-oracledb thin mode, node-oracledb 6+, ODP.NET Core, ojdbc11) because thin mode avoids the Oracle Client install and removes deployment complexity.
- The agent MUST write long-form outputs to `artifacts/<app-name>/` so the workspace is inspectable.

## Extended Reference, Critical Facts & Troubleshooting

**IMPORTANT:** Before answering domain-specific questions, troubleshooting errors, or applying rubric checklists, read [`references/rds-oracle-troubleshooting-and-resources.md`](references/rds-oracle-troubleshooting-and-resources.md) for the complete verbatim critical facts, workflows, security controls, and troubleshooting playbooks.
