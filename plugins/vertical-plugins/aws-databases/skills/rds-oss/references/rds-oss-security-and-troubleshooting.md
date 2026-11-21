# RDS OSS — Critical Facts, Security Considerations, Troubleshooting & Resources

> Extracted verbatim from `SKILL.md` for progressive disclosure. Relative paths (`references/...`, `scripts/...`) resolve from the skill root directory.

### Critical Facts to Always Surface

These RDS-OSS-specific facts are what distinguish this skill from vanilla MySQL/PostgreSQL/MariaDB knowledge. General answers typically conflate RDS with Aurora, omit the CLI command names, or stray into action-taking when this is an advisory skill.

**For "run the RDS upgrade advisor for my RDS MySQL instance", you MUST tell the user ALL of the following five facts:**

1. **Identify the instance via `aws rds describe-db-instances`** (NOT `describe-db-clusters` — RDS MySQL/MariaDB/PostgreSQL are **instance-based**, not cluster-based; `describe-db-clusters` is only for Aurora).
2. **Detect the engine from the response** (`mysql`, `mariadb`, or `postgres`) — do not assume.
3. **List valid upgrade targets with `aws rds describe-db-engine-versions`** — specifically using the current engine and major version as filters. This is how you enumerate the allowed upgrade paths.
4. **Present the latest version recommendation** explicitly (e.g., "8.0.40 is the latest 8.0 minor, 8.4.x is the next major").
5. **Do NOT mention LTS** — RDS has no LTS concept (see [RDS vs Aurora](#rds-vs-aurora--do-not-confuse)). Offering LTS advice indicates routing confusion between RDS and Aurora. Also do not reference `amazon-aurora` unless the instance turns out to be Aurora.

**Critical workflow rule — when the named instance cannot be located:** if `describe-db-instances --db-instance-identifier <id>` returns no results or a `DBInstanceNotFoundFault`, you **MUST still walk through the full advisor workflow** for the user — name each step (`describe-db-instances`, then engine detection, then `describe-db-engine-versions`, then version recommendation, then pre-upgrade checklist) — and explain what the output would look like at each step. **DO NOT bail out asking "could you double-check the instance ID?" and stop.** The user is asking for the advisor procedure, not for you to perform live discovery. If you cannot see the instance, present the workflow as a template the user can run once the correct identifier is supplied.

**For "upgrade my RDS MariaDB from X to the latest version", you MUST tell the user ALL of the following six facts:**

1. **Detect engine as `mariadb`** via describe-db-instances.
2. **Use `describe-db-engine-versions`** (with `--engine mariadb`) to identify target versions, not a hand-maintained list.
3. **Offer SSM or direct-connection precheck methods** — RDS MariaDB can be prechecked via SSM Run Command on a client host or via direct mysql-client connection.
4. **DO NOT use RDS Data API — MariaDB does not support the Data API.** This is the classic trap. Data API is only for Aurora Serverless and a subset of clusters, never MariaDB on RDS.
5. **Run MySQL-compatible precheck queries** from [upgrade-prechecks-mysql.md](references/upgrade-prechecks-mysql.md) — removed features, reserved keywords, `sql_mode` changes. MariaDB reuses the MySQL precheck set because it's a MySQL fork.
6. **Decline to execute the upgrade** — advisor only. Recommend a snapshot-and-restore dry-run in a test environment before proceeding. Explicitly say you will not run `modify-db-instance --engine-version`.

**For "2x db.r7g.2xlarge RDS MySQL 24/7 — buy RI or Savings Plan?", you MUST tell the user ALL of the following seven facts:**

1. **Run [rds_commitment_pricing_analyzer.py](scripts/rds_commitment_pricing_analyzer.py)** offline with `--instance-type db.r7g.2xlarge --engine mysql --num-instances 2`. Print the exact command as a fenced bash block.
2. **Present a full comparison table of all five options** — On-Demand, 1yr RI, 3yr RI, 1yr DSP, 3yr DSP — with savings vs on-demand in **both dollars and percentage** for each.
3. **Recommend 3yr RI** given the stated 2+-year confidence and 24/7 usage.
4. **Explain that RDS Database Savings Plan covers the r7g family specifically** — DSP coverage is family-scoped, not instance-scoped, which is a key advantage if the user might resize within the family.
5. **Mention the 3yr lock-in tradeoff** — if workload changes or the family gets superseded, the commitment is not recoverable in full.
6. **Note that RDS RIs are region-locked** — moving the workload cross-region would forfeit the RI benefit.
7. **DO NOT include purchase action steps** — no "Next Steps" section with purchase directions. No "go to Console → Reserved Instances → Purchase". No `aws rds purchase-reserved-db-instances-offering` or `aws savingsplans create-savings-plan` commands. **This is a hard ban.** This skill is advisory-only and MUST NOT guide users toward executing purchases. Say "When you're ready to purchase, refer to the AWS console or CLI docs." and stop there. Do NOT try to be helpful by showing what the purchase command would look like "for reference."

**For "change a VARCHAR(10) column to INT on RDS MySQL 8.0 via Blue/Green", you MUST tell the user ALL of the following seven facts:**

1. **Validate prerequisites first:** `binlog_format=ROW`, automated backups enabled (retention > 0), instance in `available` state.
2. **Explain why MODIFY COLUMN changing type breaks binlog replication:** Blue/Green replicates the blue → green by replaying binlog events. A type change produces a **different binary representation** on the two sides, so replication events recorded against VARCHAR can't be applied to an INT column. This is the root cause, not a "row format" issue.
3. **Create the green environment with `aws rds create-blue-green-deployment`** — include the exact CLI command name, not a generic description.
4. **Let green catch up** via binlog replication before the DDL.
5. **Apply the schema change on green** (the MODIFY COLUMN DDL) once green has caught up.
6. **Switch over immediately** with `aws rds switchover-blue-green-deployment` — **do not let green run in parallel with blue after the incompatible DDL**. The schema divergence breaks further replication.
7. **Verify the schema change on the production endpoint after switchover** and **you MUST pause and ask the user for explicit confirmation before presenting the `switchover-blue-green-deployment` command, even as a suggested step**. Do NOT list switchover as an automatic next step in a sequential workflow — state that the switchover is a destructive action that transfers production traffic, then ask "Are you ready to switch over? I'll give you the exact CLI command to run when you confirm." Only after the user confirms should you emit the `switchover-blue-green-deployment` command.

**For "we run PgBouncer in transaction mode — would RDS Proxy add anything?", you MUST tell the user ALL of the following six facts:**

1. **PgBouncer in transaction mode already does aggressive connection multiplexing** — that is the primary value proposition of Proxy. In this scenario the multiplexing benefit is marginal.
2. **What RDS Proxy adds on top:** managed infrastructure (no EC2 to operate or patch).
3. **Built-in IAM authentication** — RDS Proxy supports IAM auth natively, which PgBouncer does not out of the box.
4. **Automatic failover integrated with RDS events** — Proxy reacts to RDS failover events in seconds; PgBouncer needs external health checks and manual reconfiguration.
5. **Secrets Manager integration for credential rotation** — Proxy can pull credentials from Secrets Manager and rotate without downtime.
6. **Recommendation:** if PgBouncer is working and none of the above four features are specifically desired, **stay on PgBouncer**. Switch to RDS Proxy only if IAM auth, managed failover, or Secrets-Manager-rotated credentials are specifically needed.

## Security Considerations

Advisory skill — never modifies **existing** AWS resources. The only write action allowed is `create-db-instance` for new instance provisioning (see [Production Instance Creation](#production-instance-creation)); everything else is read-only. Never handle credentials directly; prefer short-lived credentials.

Minimum IAM permissions required: `AmazonRDSReadOnlyAccess` + `CloudWatchReadOnlyAccess` + scoped `pricing:GetProducts` + `savingsplans:DescribeSavingsPlansOfferingRates`. For instance creation, also `rds:CreateDBInstance` + `rds:AddTagsToResource`, plus `logs:CreateLogGroup` if CloudWatch Logs exports are enabled. SSM prechecks also need `ssm:SendCommand` / `ssm:GetCommandInvocation` on the target bastion.

Apply these security practices in all guidance:

1. **Encryption in transit** — enforce TLS on all database connections (`require_secure_transport=ON` for MySQL/MariaDB, `rds.force_ssl=1` for PostgreSQL).
2. **IAM database authentication** — prefer IAM auth over username/password for application connections where supported, providing short-lived credentials.
3. **Audit logging** — recommend enabling database audit logging (on RDS MySQL via the MARIADB_AUDIT_PLUGIN in an Option Group, on RDS MariaDB via the built-in server audit parameters such as `server_audit_logging=1`, and the `pgaudit` extension for PostgreSQL) and CloudTrail for API-level audit.
4. **VPC security** — deploy instances in a private subnet. Security groups should restrict inbound access to specific application CIDR ranges or security group references — never `0.0.0.0/0`.
5. **Credential rotation** — `--manage-master-user-password` provides automatic rotation via Secrets Manager.
6. **Monitoring and alarms** — recommend CloudWatch Alarms on security-relevant metrics, such as `DatabaseConnections` spikes (possible credential compromise) and `FreeableMemory` drops (possible resource-exhaustion attack).

Do NOT grant write/admin beyond the permissions listed above to work around permission errors. Do NOT store DB passwords in SSM parameters or command text — use Secrets Manager and retrieve the secret inside the command.

## Troubleshooting

**Access denied.** Attach the read-only policies above.

**Expired credentials.** Refresh, or fall back to `--offline` for commitment pricing.

**Timeouts / throttling.** Retry once, then narrow scope. SSM precheck timeouts on large schemas: switch to direct connection or user-runs-script. RDS Data API is not available for standalone RDS.

**Resource not found.** Verify region/ID; confirm it's not an Aurora *cluster* (`describe-db-clusters`). Empty RI/DSP offerings — fall back to offline.

**User asks to execute a change.** Advisory skill — modifications to existing resources happen via the AWS console or user-run CLI.

**Aurora question.** Route to `amazon-aurora`. See [RDS vs Aurora](#rds-vs-aurora--do-not-confuse) above.

**Oracle / SQL Server / Db2 question.** Route to `rds-oracle`, `rds-sqlserver`, or `rds-db2`.

## Additional Resources

- [Amazon RDS User Guide](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/)
- [RDS pricing](https://aws.amazon.com/rds/pricing/)
- [RDS MySQL upgrades](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_UpgradeDBInstance.MySQL.html) · [RDS MariaDB upgrades](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_UpgradeDBInstance.MariaDB.html) · [RDS PostgreSQL upgrades](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_UpgradeDBInstance.PostgreSQL.html)
- [RDS Reserved Instances](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithReservedDBInstances.html) · [Database Savings Plans](https://docs.aws.amazon.com/savingsplans/latest/userguide/what-is-savings-plans.html)
- [RDS Proxy](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.html) · [RDS Blue/Green Deployments](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/blue-green-deployments.html)
- [RDS Extended Support](https://aws.amazon.com/rds/extended-support/)
- [RDS Security Best Practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.Security.html)
