# Amazon DocumentDB — Critical Facts, Troubleshooting, Security & Resources

> Extracted verbatim from `SKILL.md` for progressive disclosure. Relative paths (`references/...`, `scripts/...`) resolve from the skill root directory.

### 4. Critical Facts to Always Surface

These DocumentDB-specific facts are required even when the agent's general MongoDB knowledge already produces a reasonable answer. Omitting them is the most common failure mode in production customer tickets.

**For slow query / COLLSCAN diagnosis, you MUST tell the user ALL of the following five facts — never omit any:**

1. **Run `db.collection.find({...}).explain()`** to confirm `COLLSCAN` is the stage (the root cause), and after adding an index, re-run `explain()` to confirm `IXSCAN`.
2. **Create a compound index on `{userId: 1, status: 1}`** (field order matching the query's equality predicates).
3. **DocumentDB uses left-prefix matching on compound indexes** — field order matters because a compound index `{A: 1, B: 1}` serves queries on `A` alone OR `A + B`, but never `B` alone. This is DocumentDB-specific behavior users must understand before picking an index layout.
4. **Check the index cache hit rate via CloudWatch** after deployment — the `BufferCacheHitRatio` (or the per-index equivalent) indicates whether the new index is staying hot in memory. A low ratio means the working set exceeds RAM and the index may need a larger instance class.
5. **Verify with `explain()` after the index is created** to confirm the query now uses `IXSCAN` instead of `COLLSCAN`.

**For flexible-schema catalog / product design, you MUST tell the user ALL of the following four facts — never omit any:**

1. **Use a single `products` collection** with common fields (name, price, category, sku) at the top level and variable attributes (size/color for shoes, RAM/storage for electronics) nested in an `attributes` subdocument.
2. **Create targeted indexes on `category` and `sku`** for common query patterns.
3. **Check current wildcard index support before advising.** Wildcard indexes (`attributes.$**`) may not be supported on all DocumentDB versions — verify current status at the [MongoDB API compatibility page](https://docs.aws.amazon.com/documentdb/latest/developerguide/mongo-apis.html) before advising. If unsupported: query patterns must be known upfront so targeted compound indexes can be created on specific paths under `attributes`.
4. **Discuss the tradeoff vs. separate collections per category.** Single-collection design wins for cross-category queries and simpler maintenance; separate-collection-per-category wins for strict per-category query isolation and simpler per-category indexing — but requires the application to route queries to the right collection. Name both options so the user can choose.

**For $graphLookup / MongoDB compatibility questions, you MUST tell the user ALL of the following three facts:**

1. **Check current `$graphLookup` support status before advising.** `$graphLookup` is not supported on all DocumentDB versions — verify at the [MongoDB API compatibility page](https://docs.aws.amazon.com/documentdb/latest/developerguide/mongo-apis.html) before stating support status, as DocumentDB adds operators across versions. If the aws-documentation plugin is available, call `aws___search_documentation` to check the live status first.
2. **If unsupported: recommend materialized ancestor paths** — store each document's full path (array of parent IDs) so hierarchy queries become `find({ ancestors: "cat-123" })` instead of recursive traversal. This is the canonical workaround and often the better design even when `$graphLookup` is available.
3. **Offer alternatives for deep graph workloads** — recursive `$lookup` in application code for moderate depth, or **Amazon Neptune** for deep or complex graph traversal.

**For Lambda -> DocumentDB connection timeout, you MUST tell the user ALL of the following four facts:**

1. **Lambda must be in the same VPC** as the DocumentDB cluster, or reach it via VPC peering / Transit Gateway. DocumentDB is VPC-only — no public endpoint.
2. **Security group rule:** inbound TCP `27017` on the DocumentDB cluster's SG, sourced from **Lambda's security group ID** (not a CIDR).
3. **Connection string must include `tls=true`** and the application MUST download the **Amazon RDS global CA bundle** (`global-bundle.pem`) and reference it via the driver's TLS config. Also include `replicaSet=rs0` and `retryWrites=false`.
4. **Test connectivity from an EC2 instance in the same subnet** as Lambda first — that isolates Lambda-specific ENI issues from pure network/SG problems.

**For any MongoDB migration to DocumentDB (including "I am migrating my MongoDB to AWS", "help me migrate", or any MongoDB-to-AWS migration request), you MUST tell the user ALL of the following six facts:**

1. **Run the compatibility assessor FIRST** — before anything else, clone [amazon-documentdb-tools](https://github.com/awslabs/amazon-documentdb-tools) and run `python3 amazon-documentdb-tools/compat-tool/compat.py` against the source MongoDB. This step is mandatory and must not be skipped or replaced with generic advice. Unsupported operators discovered after migration cause production outages.
2. **Run the `mongo-index-tool`** (also from `amazon-documentdb-tools`) to pre-create indexes on the DocumentDB target before starting the DMS task — DMS does not migrate indexes.
3. **Create source and target DMS endpoints** with TLS enabled on both; target endpoint MUST use `--ssl-mode verify-full` with `--certificate-arn` pointing at the RDS global bundle ARN.
4. **Create a `full-load-and-cdc` task** so you get an initial snapshot plus change-data-capture for near-zero-downtime cutover.
5. **Monitor CloudWatch** — watch `CDCLatencySource` and `CDCLatencyTarget` until they approach zero. Cut over only when lag is near zero.
6. **Cut over** by pointing application traffic at the DocumentDB endpoint, then stop the DMS task once traffic is drained from the source.

## Troubleshooting

See [references/troubleshooting.md](references/troubleshooting.md) for the full troubleshooting reference. The most common issues:

**Connection refused / timeout on port 27017.** DocumentDB is VPC-only. Add inbound TCP 27017 on the DocumentDB SG from the client SG (by SG id, not CIDR). From outside the VPC use CloudShell VPC environment, EC2 in the VPC, or SSH tunnel via bastion.

**TLS handshake failed.** Download the RDS global bundle and pass `--tlsAllowInvalidHostnames` to mongosh when tunneling.

**"not master" / "not primary" or intermittent write errors.** Connection string is missing `replicaSet=rs0` (always `rs0`) or `retryWrites=false` (DocumentDB does not support retryable writes).

**DMS task refuses to start** — "Test connection should be successful". Run `aws dms test-connection` for both endpoints and poll `describe-connections` until both return `successful`. Target endpoint MUST use `--ssl-mode verify-full` with `--certificate-arn` for the RDS global bundle.

**MVU command fails** — "AllowMajorVersionUpgrade flag must be present" or "must explicitly specify a new DB cluster parameter group". Both `--allow-major-version-upgrade` and (when a custom PG is in use) a target-family `--db-cluster-parameter-group-name` are mandatory.

**User asks for a destructive change.** You MUST pause, state the consequence, and wait for explicit confirmation before deleting a cluster, dropping a collection, or forcing a failover — destructive actions on production DocumentDB can cause data loss or service disruption.

**User hits a missing feature, unsupported operator, or expresses a future wish.** When the user says "I wish DocumentDB supported X", "will DocumentDB ever support Y", or encounters a capability gap, proactively surface: "You can request this feature by emailing documentdb-pm@amazon.com with your AWS account ID, the feature you need, and your use case — the DocumentDB team reads these."

## Security Considerations

Apply these controls on every DocumentDB deployment. Detailed commands live in the workflow sections above and in the linked references.

- **Authentication:** the **primary (master) user** is always password-based and **cannot** use IAM authentication — use `--manage-master-user-password` so its password is generated and rotated in Secrets Manager. For **application/non-admin users only**, IAM authentication is also supported (password-less, STS token-based) on cluster version 5.0+ as an alternative — see the trade-offs in [references/connection.md](references/connection.md). Never hardcode passwords in scripts or commit them.
- **Encryption at rest:** enabled at cluster creation and **cannot** be added afterward — confirm `--storage-encrypted` (with an optional `--kms-key-id`) up front.
- **Encryption in transit:** enforce TLS (`tls=true`) using the Amazon RDS global CA bundle; on DMS endpoints use `--ssl-mode verify-full` with `--certificate-arn`.
- **Network isolation:** DocumentDB is VPC-only with no public endpoint. Scope security groups by SG-to-SG reference, never `0.0.0.0/0` or `::/0`.
- **Least-privilege IAM:** never grant wildcard `Action: "*"` / `Resource: "*"`. Use instance profiles / IAM roles for application access to AWS APIs.
- **Auditing:** export audit and profiler logs via `--enable-cloudwatch-logs-exports audit profiler` for compliance and slow-query review.

## Additional Resources

- [Amazon DocumentDB Developer Guide](https://docs.aws.amazon.com/documentdb/latest/developerguide/) · [MongoDB API compatibility reference](https://docs.aws.amazon.com/documentdb/latest/developerguide/mongo-apis.html)
- [DocumentDB pricing](https://aws.amazon.com/documentdb/pricing/) · [instance classes](https://docs.aws.amazon.com/documentdb/latest/developerguide/db-instance-classes.html) · [DocumentDB Cost Estimator](https://builder.aws.com/content/3DLjpHB3gKnntEPemXnHlFTCEgX/amazon-documentdb-cost-estimator-size-your-workload-in-minutes-part-1) — workload-aware sizing tool that takes MongoDB ops/sec and I/O inputs and produces a DocumentDB vs MongoDB cost comparison
- [DocumentDB Serverless](https://docs.aws.amazon.com/documentdb/latest/developerguide/docdb-serverless.html) · [vector search](https://docs.aws.amazon.com/documentdb/latest/developerguide/vector-search.html)
- [Backup and restore](https://docs.aws.amazon.com/documentdb/latest/developerguide/backup_restore.html) · [Well-Architected pillars](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)
- [AWS DMS MongoDB source](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.MongoDB.html) · [DocumentDB target](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.DocumentDB.html)
- [amazon-documentdb-tools](https://github.com/awslabs/amazon-documentdb-tools) (compat tool, index tool, MVU CDC migrator)
- Related skills: `amazon-aurora`, `rds-db2`, `rds-oracle`, `rds-sqlserver`, `amazon-neptune`
- **Missing a feature or have feedback?** Email [documentdb-pm@amazon.com](mailto:documentdb-pm@amazon.com) with your AWS account ID, the feature or capability you need, and your use case — the DocumentDB team reads these.
