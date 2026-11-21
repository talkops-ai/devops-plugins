---
name: rds-db2
version: 2
description: "Provisions, connects, migrates, and operates Amazon RDS for Db2. Applies when provisioning with IBM customer and site IDs (License Manager, BYOL, GovCloud), connecting over TLS, fixing SQL30082N after Secrets Manager rotation, migration from Db2 LUW (Linux, AIX, Windows, AS400) or z/OS mainframe (ADB2GEN, Q Replication), choosing code page/collation (EBCDIC, CCSID), S3 backup/restore, Multi-AZ and cross-region standby replicas, RDSADMIN procedures, customer-managed KMS BYOK, self-managed Active Directory Kerberos, Db2 audit to S3, minimum IAM, or colocation. Query live AWS state via MCP tools only (never raw aws CLI)."
---

# Amazon RDS for Db2

> **MCP-Only Live AWS Execution:** Perform ALL live AWS API discovery, account/region checks (`sts:GetCallerIdentity`), cluster/instance/table inspection, CloudWatch telemetry, pricing (`awspricing`), and docs (`awsknowledge`) strictly via connected MCP tools (`aws-mcp` `aws___run_script` `call_boto3`, `dynamodb`, `elasticache`, `postgres`, `mysql`, `cloudwatch`, `awspricing`, `awsknowledge`) — **never invoke raw `aws ...` CLI commands (such as `aws --version` or `aws sts get-caller-identity`) in shell (`run_command`)**. Local offline helper scripts under `scripts/` may be run via `python3` or `node`.

## Overview

Amazon RDS for Db2 is a managed IBM Db2 LUW service. RDS for Db2 is managed — you cannot SSH to the host, install agents, or run unfenced external stored procedures in C/COBOL. Java stored procedures work via `sqlj.install_jar`. This skill covers the operator lifecycle: provisioning with IBM licensing, client install and TLS connectivity, migration from self-managed Db2 on Linux/AIX/Windows/z/OS/AS400, S3 backup and restore, Multi-AZ and cross-region standby replicas, and RDSADMIN stored procedures that replace SYSCTRL/SYSMAINT authority.

It also covers six additional security and operations areas: customer-managed KMS keys (BYOK), self-managed Active Directory with Kerberos authentication, Db2 audit to S3, code page and collation selection (EBCDIC, CCSID), minimum IAM permissions, and EC2/RDS colocation for Multi-AZ latency and failover.

The AWS MCP server is recommended but not required; all operations are expressed in AWS CLI syntax and run with or without it.

Routes to the matching sub-skill reference. Load only the matching reference.

## Common Tasks

### Verify Dependencies

Before executing an RDS for Db2 workflow, confirm required tools exist. Do not run installers or API calls yet.

- AWS CLI v2 for every RDS API call
- AWS credentials via managed mechanism (IAM role, instance profile) — not pasted credentials
- Client install: `bash`/`curl` access, run as root and as `db2inst1`
- Airgap install: internet-connected machine + target with VPC endpoints for S3, SSM, Secrets Manager
- Mainframe migration: z/OS access, IBM ADB2GEN license, Python 3
- BYOK / customer-managed KMS: `openssl` (to wrap imported key material) and `jq` (to parse `get-parameters-for-import` output)
- Self-managed Active Directory + Kerberos: `realmd`, `sssd`, `adcli`, `krb5-workstation` on the client, plus a valid Kerberos ticket (`kinit` produces a TGT — check with `klist`)
- Kerberos JDBC test: a JDK and the Db2 JDBC driver `db2jcc4.jar` v4.33+ (earlier driver versions lack `securityMechanism=11` Kerberos support)

**Constraints:**

- The agent MUST check dependencies before running any install or AWS API command.
- The agent MUST NOT prompt the user to paste credentials because credentials MUST flow through an IAM role or instance profile.
- The agent MUST tell the user which dependencies are missing and MUST respect the user's decision to abort.
- The agent MUST explain, for each step, what it does, why, and which tool will be invoked — before invoking it.

### Classify and Route

Map the user's question to the correct sub-skill reference, then load only that file.

| User says | Sub-skill | Load |
|---|---|---|
| create / provision / parameter group / IBM customer ID / IBM site ID / License Manager / BYOL / GovCloud | provisioning | [provisioning.md](references/provisioning.md) |
| connect / SQL30082N / SQL1531N / DSN / CLP / Python / Java / CloudShell / airgap | connectivity | [connectivity.md](references/connectivity.md) |
| SSL / TLS / GSKit / certificate / truststore / bundle.pem | connectivity-tls | [connectivity-tls.md](references/connectivity-tls.md) |
| Python driver / JDBC / laptop / multi-instance / db2_use | connection drivers | [connection-drivers.md](references/connection-drivers.md) |
| migrate / DMS / Q Replication / IIDR / AIX / Windows / AS400 / precheck | migration | [migration.md](references/migration.md) |
| z/OS / mainframe / ADB2GEN / schema conversion | mainframe-migration | [mainframe-migration.md](references/mainframe-migration.md) |
| code page / collation / CCSID / EBCDIC / UTF-8 / CODEUNITS32 / territory | code page & collation | [code-page-collation.md](references/code-page-collation.md) |
| snapshot / backup / restore / rollforward / PiTR / S3 integration | backup-restore | [backup-restore.md](references/backup-restore.md) |
| Multi-AZ / standby replica / read replica / HADR / cross-region / failover | ha-dr | [ha-dr.md](references/ha-dr.md) |
| parameter group / RDSADMIN / scale / storage / CloudWatch / registry variable | operations | [operations.md](references/operations.md) |
| BYOK / customer-managed KMS / bring your own key / imported key material / multi-region key | byok | [byok-kms.md](references/byok-kms.md) |
| Active Directory / Kerberos / domain join / self-managed AD / kinit / SPN / realm | ad-kerberos | [ad-kerberos.md](references/ad-kerberos.md) |
| audit / DB2_AUDIT / audit policy / audit to S3 / option group | db2-audit | [db2-audit.md](references/db2-audit.md) |
| minimum IAM / least privilege / IAM policy / trust policy / permissions | minimum-iam | [minimum-iam.md](references/minimum-iam.md) |
| colocation / co-locate / EC2 app latency / ASG / ALB / failover routing | colocation | [colocation.md](references/colocation.md) |

**Constraints:**

- The agent MUST read only the reference files that match the user's question, to keep the context focused.
- The agent MUST NOT invent RDSADMIN procedure signatures, because wrong parameter order will fail at runtime — always cite the signature from the reference file.
- The agent MUST cite the source blog URL when an answer is blog-sourced, so the user can verify specifics.
- If a question crosses two sub-skills (e.g. "migrate z/OS with near-zero downtime", or "BYOK plus cross-region standby"), the agent SHOULD load each matching reference and combine them.

### Execute Workflow

Once routed, give the user a concrete, runnable answer grounded in the reference file.

Parameter acquisition:

- All required parameters (region, instance identifier, source/target ARNs, S3 bucket, prefix, the `--master-username` value) MUST be collected upfront in a single message.
- Parameter formats MUST be specified: region `us-east-1`-style; instance identifier `^[a-zA-Z][a-zA-Z0-9-]{0,62}$`; ARN `arn:aws:rds:<region>:<account>:db:<name>`; S3 bucket 3–63 chars lowercase.
- The agent MUST accept parameters via direct input, a JSON/YAML file path, or a URL.

Tool use:

- Use AWS CLI for RDS operations (example: `aws rds create-db-instance-read-replica --db-instance-identifier <name> --source-db-instance-identifier <arn> --replica-mode mounted --region <dr-region>`). Every operation is expressed in AWS CLI syntax so it runs whether or not the AWS MCP server is installed.
- Use bundled scripts — [db2-driver.sh](scripts/db2-driver.sh), [db2client-configure.sh](scripts/db2client-configure.sh), [db2client-airgap.sh](scripts/db2client-airgap.sh), [functions.sh](scripts/functions.sh) — instead of rewriting install steps.
- Write migration plans, upgrade plans, validation reports to a local `artifacts/<app-name>/` directory created at runtime in the working directory (this is a run-time output location, not part of the shipped skill).

**Constraints:**

- The agent MUST give exact CLI commands when behavior is deterministic, not descriptions like "enable Multi-AZ".
- The agent MUST obtain AWS credentials through an IAM role or instance profile and MUST NOT prompt the user to paste credentials.
- The agent MUST cite the source blog or documentation URL whenever the answer is sourced from published material, so the user can verify it.
- The agent MUST write long-form artifacts to a local `artifacts/<app-name>/` directory (created at runtime in the working directory) so the workspace is inspectable.
- When a requested action is unsupported on managed RDS for Db2, the agent MUST state the limitation plainly — no hedging like "limited support" or "with special config" — and offer a supported alternative (for example, unfenced C/COBOL stored procedures are not supported; rewrite them in Java via `sqlj.install_jar`, or in SQL PL).
- The AWS MCP server is recommended but not required. When the MCP server is in use, prefer inline JSON strings over positional filesystem arguments with `call_aws`; this is guidance for the MCP path only, not a requirement. Never treat `call_aws` or `run_script` as the only way to perform an operation — the AWS CLI command always works on its own.

### Resource tagging (always apply on resource creation)

When creating any RDS for Db2 resource (`create-db-instance`, `create-db-parameter-group`, `create-db-cluster` for Multi-AZ deployments, `create-db-instance-read-replica` for standby replicas), ALWAYS include these tags using the RDS list-of-records `--tags` syntax:

`--tags Key=created_by,Value=rds-db2-skill Key=generation_model,Value={your-model-id}`

Example: `--tags Key=created_by,Value=rds-db2-skill Key=generation_model,Value=claude-sonnet-4-20250514`

The same convention applies to every resource this skill creates, including BYOK-encrypted instances (`create-db-instance --storage-encrypted --kms-key-id ...`), audit option groups (`create-option-group`), and customer-managed KMS keys (`kms create-key`, tagged with `--tags TagKey=created_by,TagValue=rds-db2-skill TagKey=generation_model,TagValue={your-model-id}` per the KMS tag syntax).

Include these tags even if the user does not mention tagging, so that they can identify the resources created via this skill. If the user provides additional tags, append these to their tags rather than replacing them. The same applies when tagging via `add-tags-to-resource` on existing resources.

## RDS-managed facts the agent must always surface

These RDS-for-Db2-specific facts are what differentiates this skill from general IBM Db2 knowledge. General-Db2 answers typically omit the RDS-managed constraints (no unfenced C/COBOL, Secrets Manager rotation side effects, `rdsadmin.*` procedures) and the AWS-native migration tooling nuances (DMS z/OS limits, ADB2GEN vs SCT).

**For "create cross-region standby replica for DR", you MUST tell the user ALL of the following six facts:**

1. **Use `aws rds create-db-instance-read-replica`** with `--replica-mode mounted` and the cross-region source ARN — Db2 cross-region standby uses **mounted replica mode**, NOT transactional read-replica mode.
2. **Source prerequisite: automated backups enabled** on the source instance (backup retention period > 0).
3. **Target-region prerequisite: custom parameter group** created in the target region before the command runs.
4. **Target-region prerequisite: KMS key** available in the target region (multi-region KMS key or a target-region customer-managed KMS key).
5. **State prerequisites: all databases in `active` state, no pending reboots**, no license-model restrictions blocking cross-region replicas.
6. **Explain the mounted-vs-transactional distinction** — mounted replicas do not accept reads or SQL from applications; they exist purely as a DR standby that can be promoted. Do not suggest read offload use cases.

**For "restore Db2 backup from S3 (multi-part, N files)", you MUST tell the user ALL of the following six facts — never omit any of the procedure names:**

1. **Attach IAM role with S3 access via `aws rds add-role-to-db-instance`** using `--feature-name S3_INTEGRATION`.
2. **Set restore performance parameters via `rdsadmin.set_configuration`** — tune `USE_STREAMING_RESTORE`, `RESTORE_DATABASE_NUM_BUFFERS`, and `PARALLELISM` before starting the restore.
3. **Call `rdsadmin.restore_database`** with five parameters in this exact order: database name, restore mode (`OFFLINE` or `ONLINE`), S3 prefix, S3 bucket, and region. Multi-file (multi-part) backups are handled by the shared prefix — there is no separate multi-part flag parameter. (Signature: `rdsadmin.restore_database(dbname, type, prefix, bucket, region)`.)
4. **For `ONLINE` restore mode, follow up with `rdsadmin.rollforward_database`** to replay archive logs, then `rdsadmin.complete_rollforward` to finish. `OFFLINE` restores do NOT need rollforward.
5. **Monitor progress with `rdsadmin.get_task_status`** — every `rdsadmin` procedure returns a task ID you poll.
6. **Warn about VPC endpoint for S3 if no internet egress** from the private subnet, and warn about **Db2 version compatibility** between the source backup and the RDS instance engine version (forward-compatible, not backward).

**For "C/COBOL unfenced external stored procedures — lift and shift to RDS for Db2?", you MUST tell the user ALL of the following four facts:**

1. **Unfenced external stored procedures in C and COBOL are NOT supported on RDS for Db2.** State this as an unqualified "not supported" — do not hedge with "limited support" or "with special config."
2. **All routines on RDS for Db2 MUST be fenced.** This is a managed-service architectural constraint, not a flag.
3. **Java stored procedures are supported** — install via `sqlj.install_jar`. C/COBOL SPs should be **rewritten in Java or SQL PL** (Db2's procedural SQL, equivalent to Oracle's PL/SQL).
4. **Offer to help identify which SPs are unfenced** and prioritize the rewrite by call frequency (hot code path first).

**For "migrate Db2 for z/OS to RDS for Db2 with near-zero downtime", you MUST tell the user ALL of the following five facts:**

1. **For near-zero-downtime from z/OS, use Q Replication (IBM IIDR), Qlik Replicate, or Precisely** — these are the CDC tools that support Db2 for z/OS as a source streaming to RDS for Db2.
2. **AWS DMS supports FULL LOAD ONLY from Db2 for z/OS.** DMS does NOT support CDC from z/OS sources. Use DMS for a one-time bulk load, not for near-zero-downtime cutover.
3. **Use ADB2GEN for schema conversion from z/OS.** AWS SCT does NOT support Db2 for z/OS as a source — this is a common trap. Do not recommend SCT for z/OS sources.
4. **Code-page conversion (EBCDIC → UTF-8) is the primary migration risk.** Plan explicit collation and code page mapping before cutover — silent data corruption is the failure mode.
5. **Plan explicit collation selection** on the target RDS instance to match the semantic ordering of the z/OS source.

**For "SQL30082N — USERNAME AND/OR PASSWORD INVALID" with RDS-managed master user (user didn't change it), you MUST tell the user ALL of the following four facts:**

1. **SQL30082N after a previously-working connection almost always means the master password rotated in Secrets Manager.** RDS for Db2 rotates the master password on the Secrets Manager schedule — clients using a cached password will start failing with SQL30082N even though nothing on their side changed.
2. **Fix: run `db2_use <instance-id>`** (from `functions.sh` / the bundled helpers). This fetches the current password from Secrets Manager and rewrites `~/.db2env` with the new value.
3. **Alternative: `db2_test_connection`** to verify the helper's fix worked end-to-end.
4. **If `db2_use` isn't installed**, the user needs to pull the current password with `aws secretsmanager get-secret-value` and update their local credential cache manually. Do not tell them to rotate the password — the password rotation is what caused the problem.

**For "BYOK / customer-managed KMS key for RDS for Db2", you MUST tell the user ALL of the following six facts:**

1. **Use a multi-region KMS key with `--origin EXTERNAL`** when importing your own key material, so the same key ID and material can replicate to a DR region.
2. **The creating principal needs `kms:CreateGrant` and `kms:DescribeKey`** on the key, or instance creation fails.
3. **Encryption is set at instance creation** with `--storage-encrypted --kms-key-id <alias|arn>`. You **cannot encrypt an existing unencrypted instance in place** — go snapshot → `copy-db-snapshot --kms-key-id` → `restore-db-instance-from-db-snapshot`.
4. **For cross-region DR, replicate the multi-region key (`kms:ReplicateKey`)** into the DR region first, then `copy-db-snapshot` across regions with the replica key.
5. **Import tokens expire after 24 hours** — if `import-key-material` fails on expiry, re-run `get-parameters-for-import` to get a fresh token and wrapping key.
6. **Cite blog DBBLOG-5188 and [byok-kms.md](references/byok-kms.md)**; do not invent KMS parameter names.

**For "self-managed Active Directory with Kerberos on RDS for Db2", you MUST tell the user ALL of the following six facts:**

1. **RDS joins your AD via `--domain-fqdn`, `--domain-ou`, `--domain-auth-secret-arn`, and `--domain-dns-ips`** — the self-managed AD path, with no AWS Managed Microsoft AD required.
2. **The Secrets Manager secret uses keys `SELF_MANAGED_ACTIVE_DIRECTORY_USERNAME`** (the sAMAccountName only — **no `DOMAIN\` prefix**, which fails creation) **and `SELF_MANAGED_ACTIVE_DIRECTORY_PASSWORD`**, encrypted by a dedicated KMS key, with a resource policy trusting `rds.amazonaws.com` guarded by `aws:SourceArn` and `aws:SourceAccount` (confused-deputy protection).
3. **Delegate the nine AD permissions** to a dedicated service account scoped to one OU; grant `servicePrincipalName` read/write on **User** objects using **ADSI Edit**, not the ADUC delegation wizard (which filters that attribute out) — this is the most common failure.
4. **Open AD ports between RDS and the domain controllers: DNS 53, Kerberos 88 and 464, LDAP 389 and 3268, and the RPC range 49152–65535.** Missing the RPC range is the top cause of intermittent join failures. Keep clock skew under 5 minutes.
5. **The RDS master user is a local account that cannot get a Kerberos ticket.** AD users need `kinit` plus a `GRANT CONNECT`. Kerberos JDBC uses `securityMechanism=11` and a **region-specific PEM** via `sslCertLocation` (never `global-bundle.pem`).
6. **Cite the self-managed AD blog and [ad-kerberos.md](references/ad-kerberos.md)**; verify with `describe-db-instances ... DomainMemberships` showing `Status: joined`.

## Extended Reference & Troubleshooting

For the complete verbatim continuation of this guide — including detailed workflows, troubleshooting matrices, security checklists, and resource catalogs — read [`references/rds-db2-troubleshooting-and-resources.md`](references/rds-db2-troubleshooting-and-resources.md).
