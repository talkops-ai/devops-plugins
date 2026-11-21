# Amazon RDS for Db2 — Troubleshooting, Security, Catalog & Handoff

> Extracted verbatim from `SKILL.md` for progressive disclosure. Relative paths (`references/...`, `scripts/...`) resolve from the skill root directory.

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `SQL30082N` | Password rotated in Secrets Manager | Run `db2_use <instance-id>` — the helper re-fetches the current password and rewrites `~/.db2env`. |
| `SQL1531N` | DSN not yet in cache | `db2 terminate` to clear, then retry; if still failing, re-run [db2client-configure.sh](scripts/db2client-configure.sh). |
| `SQL01013N` / TCP timeout | Security group blocks 50000/50443 | Check SG inbound rules — add client's SG on TCP 50000 (plain) or 50443 (SSL). |
| GSKit / SSL certificate error | RDS cert bundle missing or RSA cert not first | Re-download `<region>-bundle.pem` from RDS truststore and re-run `db2client-configure.sh`. |
| Access denied on RDSADMIN call | IAM role missing `S3_INTEGRATION` feature | `aws rds add-role-to-db-instance --feature-name S3_INTEGRATION --role-arn <role-arn> --db-instance-identifier <id>`. |
| Restore fails with "database in rollforward pending" | ONLINE restore left DB in rollforward state | Call `rdsadmin.rollforward_database` for each archive log, then `rdsadmin.complete_rollforward`. |
| Standby replica creation fails | Missing prereqs | Verify: automated backups enabled, custom parameter group in DR region, KMS multi-region key, no pending `rdsadmin` tasks, all databases in active state. |
| AD domain join `Status` not `joined` | RPC port range blocked, wrong secret format, or SPN attribute missing | Open RPC 49152–65535 between RDS and the DCs, confirm the secret username is the sAMAccountName with no `DOMAIN\` prefix, and grant `servicePrincipalName` on User objects via ADSI Edit — see [ad-kerberos.md](references/ad-kerberos.md). |
| `import-key-material` fails — token expired | Import token older than 24 hours | Re-run `get-parameters-for-import` for a fresh token and wrapping key, re-wrap the material with `openssl`, then retry the import — see [byok-kms.md](references/byok-kms.md). |
| Throttling from RDS API | Exceeded API request rate | Exponential backoff with jitter; batch operations; check Service Quotas. |

## Security Considerations

Surface these controls when advising on any production RDS for Db2 deployment. They consolidate the security guidance that the sub-skill references cover in depth.

- **Encryption at rest and in transit** — Always create instances with `--storage-encrypted`; for key ownership and compliance use a customer-managed KMS key (BYOK), and for DR use a multi-region key. Enforce TLS on every connection (port 50443, `<region>-bundle.pem`); never connect in plaintext for production. See [byok-kms.md](references/byok-kms.md) and [connectivity-tls.md](references/connectivity-tls.md). (Guideline 1)
- **Least-privilege IAM** — Use the scoped policy and trust policy in [minimum-iam.md](references/minimum-iam.md); never attach a `*FullAccess` managed policy. Scope `iam:PassRole` and ARN-pattern every mutating statement that supports resource-level permissions. (Guideline 5)
- **Network isolation** — Keep instances in private subnets, restrict security groups to the application/source SG (never `0.0.0.0/0`), and use VPC endpoints for S3/SSM/Secrets Manager so traffic stays off the public internet. See [colocation.md](references/colocation.md). (Guideline 5)
- **Audit logging and monitoring** — Enable Db2 audit to S3 ([db2-audit.md](references/db2-audit.md)), RDS Enhanced Monitoring, and CloudTrail for RDS/KMS/Secrets Manager API calls. Alarm on failed logins and configuration changes. (Guideline 12)
- **Secret rotation** — Provision with `--manage-master-user-password` so RDS stores and rotates the master password in Secrets Manager; never embed plaintext passwords. After rotation, refresh clients with `db2_use <instance-id>`. (Guideline 13)
- **Backup encryption and retention** — Set a backup retention period, encrypt automated and manual snapshots with your KMS key, and apply S3 bucket encryption plus lifecycle/retention to any Db2 audit or backup buckets. (Guideline 13)

## Additional Resources

### In-scope documentation and blogs

- AWS docs — RDS for Db2: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_RDSDb2.html
- AWS docs — RDS for Db2 IAM permissions: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAM.html
- AWS docs — Kerberos authentication for RDS for Db2: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/db2-kerberos.html
- Blog — Connect to RDS for Db2 from CloudShell: https://aws.amazon.com/blogs/database/connect-to-amazon-rds-for-db2-using-aws-cloudshell/
- Blog — Restore self-managed Db2 Linux into RDS for Db2: https://aws.amazon.com/blogs/database/restore-self-managed-db2-linux-databases-in-amazon-rds-for-db2/
- Blog — Near-zero downtime from AIX/Windows to RDS for Db2 with Q Replication: https://aws.amazon.com/blogs/database/near-zero-downtime-migrations-from-self-managed-db2-on-aix-or-windows-to-amazon-rds-for-db2-using-ibm-q-replication/
- Blog — Cross-region standby replicas: https://aws.amazon.com/blogs/database/configure-amazon-rds-for-db2-standby-replicas-for-high-availability-and-faster-disaster-recovery/
- Blog — Mainframe DDL conversion (z/OS to RDS for Db2): https://aws.amazon.com/blogs/database/migrating-tables-from-ibm-db2-for-z-os-to-amazon-rds-for-db2/
- Blog — Code page and collation for mainframe migration: https://aws.amazon.com/blogs/database/choosing-the-right-code-page-and-collation-for-migration-from-mainframe-db2-to-amazon-rds-for-db2/
- Blog — Bring your own customer-managed KMS key for RDS for Db2 (DBBLOG-5188): https://aws.amazon.com/blogs/database/bring-your-own-key-to-amazon-rds-for-db2-with-a-customer-managed-kms-key/
- Blog — Self-managed Active Directory with Kerberos for RDS for Db2: https://aws.amazon.com/blogs/database/use-kerberos-authentication-with-a-self-managed-active-directory-for-amazon-rds-for-db2/

### Related topics (cited resources, not yet routed sub-skills)

These adjacent topics are not expanded into routed references in this iteration. Each is discoverable through the cited resource below.

- Reverse log shipping for RDS for Db2 (DBBLOG-5352): https://aws.amazon.com/blogs/database/implement-reverse-log-shipping-for-amazon-rds-for-db2/
- Multi-account connectivity: workspace source `04-db2-client/RDS-Db2-Multiple-Account-Connectivity/`
- Terraform provisioning: workspace source `04-db2-client/RDS-Db2-Terraform/`
- CIS compliance: workspace source `04-db2-client/CIS-Compliance/`
- db2mon monitoring: workspace source `04-db2-client/db2mon_RDS/`
- Compression savings: workspace source `04-db2-client/Compression-Savings/`
- Migration prerequisite check (DBBLOG-5048): https://aws.amazon.com/blogs/database/migrate-from-ibm-db2-to-amazon-rds-for-db2-using-a-migration-prerequisite-check/
- Load from S3: workspace source `04-db2-client/load-from-s3/`
- Sample Java stored procedures: workspace source `04-db2-client/sample-java-sp/`

### Blog catalog

The authoritative list of published RDS for Db2 blogs and sample tools is maintained at https://github.com/aws-samples/sample-rds-db2-tools/tree/main — consult it for the current set of blog articles and companion code.

- Related skill (migrating off Db2 LUW to PostgreSQL): `rds-postgres-migration` (if present in corpus).

## Handoff from aws-database-selection

This skill can be invoked directly, or it can be entered from the `aws-database-selection` parent skill after that skill has run a requirements interview and produced a `requirements.json` artifact. When you see a backtick-wrapped path matching `aws_dbs_requirements/*/requirements.json` in recent conversation, follow the entry protocol in `aws-database-selection/handoff-contract.md`:

1. Read the artifact using `file_read`.
2. Validate it against `aws-database-selection/workload-primary-artifact.schema.json`. If malformed or unreadable, tell the user and proceed without it.
3. Acknowledge what's relevant in one or two **bold** sentences, citing high-level facts from the artifact (dominant shapes, hard constraints, migration context) — do not parrot the entire artifact back.
4. Scope-check: this skill is scoped to Amazon RDS for Db2 — migrations from Db2 z/OS or LUW, HADR, standby replicas, SQL PL routines, Q Replication cutovers. If the artifact's `workload_primaries.dominant_shapes` or `migration_context` don't match that scope, emit weak backpressure per the handoff contract: suggest `amazon-aurora` for refactor-to-PostgreSQL from Db2, or go back to `aws-database-selection` if Db2 isn't the source, then ask the user whether to go back or proceed anyway. Do not silently misuse the artifact.
5. Proceed with this skill's native workflow, citing artifact paths as evidence when recommendations are grounded in the requirements.

The curated RDS-for-Db2 selection facts that the parent `aws-database-selection` skill consumes live at `assets/selection-knowledge-input.json` (with a human-readable companion at `assets/selection-knowledge-input.md`). These capture the in-scope source-migration scenarios, hard constraints, HA/DR options, and security areas in a structured, reusable form — read them when you need the curated selection view rather than re-deriving it.

All user-facing output from this skill follows the markdown-primitives-only formatting convention in the handoff contract: bold labels, backticks for paths and enum values, bullet lists for alternatives, no ASCII art or box-drawing characters.
