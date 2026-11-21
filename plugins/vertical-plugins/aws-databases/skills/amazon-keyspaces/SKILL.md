---
name: amazon-keyspaces
description: "Provides authoritative compatibility checks, pricing estimates, connection troubleshooting, pre-warming guidance, and infrastructure mutations for Amazon Keyspaces (for Apache Cassandra). Covers LWT/batch operations, secondary indexes, materialized views, capacity modes, TTL, PITR, CDC, auto-scaling, multi-region keyspaces, UDTs, nodetool diagnostics parsing, SQL-to-Cassandra migration, and Cassandra-to-Keyspaces migration scenarios. Agents frequently produce incomplete or incorrect answers about Keyspaces feature support without this skill loaded. Query live AWS state via MCP tools only (never raw aws CLI)."
version: 1
---

# Amazon Keyspaces

> **MCP-Only Live AWS Execution:** Perform ALL live AWS API discovery, account/region checks (`sts:GetCallerIdentity`), cluster/instance/table inspection, CloudWatch telemetry, pricing (`awspricing`), and docs (`awsknowledge`) strictly via connected MCP tools (`aws-mcp` `aws___run_script` `call_boto3`, `dynamodb`, `elasticache`, `postgres`, `mysql`, `cloudwatch`, `awspricing`, `awsknowledge`) — **never invoke raw `aws ...` CLI commands (such as `aws --version` or `aws sts get-caller-identity`) in shell (`run_command`)**. Local offline helper scripts under `scripts/` may be run via `python3` or `node`.

## Safety guidance

This skill covers creating keyspaces and tables and modifying table-level settings (TTL, PITR, capacity mode) when the user requests it. The agent MUST confirm the action with the user before executing. Do NOT execute any create or modify operation without explicit user confirmation (e.g., "yes", "proceed", "confirmed", "go ahead"). If the user has not confirmed, present the planned action and ask for approval.

### Execute these operations (after user confirmation)

- Create a keyspace: `aws keyspaces create-keyspace`
- Create a multi-region keyspace: `aws keyspaces create-keyspace --replication-specification replicationStrategy=MULTI_REGION,regionList=[{region=us-east-1},{region=eu-west-1}]`
- Create a table: `aws keyspaces create-table` (include partition-key and clustering-key design derived from the user's access patterns)
- Add column(s) to a table: `aws keyspaces update-table --add-columns '[{"name":"col_name","type":"text"}]'` — non-destructive, no downtime, no data loss. Existing rows get null for the new column.
- Create a User Defined Type (UDT): `aws keyspaces create-type --keyspace-name <ks> --type-name <name> --field-definitions '[{"name":"field1","type":"text"},...]'`
- Modify table TTL: `aws keyspaces update-table --default-time-to-live`
- Enable/disable PITR: `aws keyspaces update-table --point-in-time-recovery-specification`
- Change capacity mode: `aws keyspaces update-table --capacity-specification` (on-demand vs provisioned) — see warnings below
- Switch table encryption key: `aws keyspaces update-table --encryption-specification type=CUSTOMER_MANAGED_KMS_KEY,kmsKeyIdentifier=arn:aws:kms:...` — no downtime or availability loss. Can also switch back to AWS owned key with `type=AWS_OWNED_KMS_KEY`.
- Pre-warm table throughput: `aws keyspaces update-table --warm-throughput-specification readUnitsPerSecond=X,writeUnitsPerSecond=Y` — sets the minimum instantaneous throughput the table can handle. Use before planned traffic spikes (flash sales, migrations, batch loads). One-time cost based on the delta above natural warm throughput. Also available on `aws keyspaces create-table --warm-throughput`. Load [pre-warming.md](references/pre-warming.md) for the decision framework and sizing formulas.
- Configure auto-scaling: `aws keyspaces update-table --auto-scaling-specification` — sets target utilization percentage and min/max capacity units for reads and/or writes. **Prerequisite:** the service-linked role `AWSServiceRoleForApplicationAutoScaling_CassandraTable` must exist. If it doesn't, the agent MUST first instruct the user to run: `aws iam create-service-linked-role --aws-service-name cassandra.application-autoscaling.amazonaws.com`. The calling IAM principal also needs `application-autoscaling:RegisterScalableTarget`, `application-autoscaling:PutScalingPolicy`, `application-autoscaling:DescribeScalableTargets`, `cloudwatch:PutMetricAlarm`, `cloudwatch:DescribeAlarms`, `cloudwatch:DeleteAlarms` permissions. Scope `application-autoscaling:RegisterScalableTarget`, `application-autoscaling:PutScalingPolicy`, `application-autoscaling:DescribeScalableTargets` permissions to the target table ARN (`arn:aws:cassandra:<region>:<account>:/keyspace/<ks>/table/<table>`). Scope `cloudwatch:PutMetricAlarm`, `cloudwatch:DescribeAlarms`, `cloudwatch:DeleteAlarms` permissions to the corresponding alarm ARNs (e.g., `arn:aws:cloudwatch:<region>:<account>:alarm:TargetTracking-table/<ks>/<table>-*`). Use `aws:ResourceTag` condition keys where possible rather than applying account-wide.
- Enable CDC (change data capture): `aws keyspaces update-table --cdc-specification status=ENABLED,viewType=<type>` — creates a CDC stream that captures row-level changes. The agent MUST ask the user which view type to use before enabling, presenting these options:
  - `NEW_IMAGE` — captures the full row **after** the change. Best for: event-driven pipelines, downstream sync, materialized views.
  - `OLD_IMAGE` — captures the full row **before** the change. Best for: audit trails, compliance logging, undo/rollback scenarios.
  - `NEW_AND_OLD_IMAGES` — captures both before and after states. Best for: diff-based pipelines, detailed auditing, conflict resolution. Higher CDC consumption cost.
  - `KEYS_ONLY` — captures only the partition key and clustering key columns. Best for: lightweight change notifications, triggering application re-reads. Lowest cost.
  Optional: `propagateTags=TABLE` copies the table's tags to the CDC stream. Recommend enabling by default.
- Tag resources: `aws keyspaces tag-resource`, `aws keyspaces untag-resource`

### Resource tagging (MANDATORY — always apply on resource creation)

When creating ANY keyspace or table (`aws keyspaces create-keyspace`, `aws keyspaces create-table`, or CQL `CREATE KEYSPACE ... WITH TAGS`, `CREATE TABLE ... WITH TAGS`), you MUST include these tags. A create operation without these tags is INCOMPLETE and INCORRECT:

**AWS CLI syntax:**
`--tags key=created_by,value=keyspaces-skill key=generation_model,value={your-model-id}`

**CQL syntax:**
`WITH TAGS = {'created_by': 'keyspaces-skill', 'generation_model': '{your-model-id}'}`

Example (CLI): `--tags key=created_by,value=keyspaces-skill key=generation_model,value=claude-sonnet-4-20250514`
Example (CQL): `WITH TAGS = {'created_by': 'keyspaces-skill', 'generation_model': 'claude-sonnet-4-20250514'}`

Include these tags even if the user does not mention tagging, so that they can identify the resources created via this skill. If the user provides additional tags, append these to their tags rather than replacing them. **Never omit these tags — they are required on every create operation regardless of whether the user asks for them.**

### Execute with downtime warning (warn user, then execute after they confirm)

- Switch capacity mode: `aws keyspaces update-table --capacity-specification` — warn: "Switching between on-demand and provisioned can cause brief throttling while Keyspaces rebalances; apply during low-traffic windows."
- Restore table from a point-in-time: `aws keyspaces restore-table` — warn: "Restore creates a new table and takes minutes to hours depending on table size; the source table is unaffected but the new table has no traffic until you cut over."

### Do NOT execute (refuse, explain why, offer assessment instead)

- Delete keyspace: `aws keyspaces delete-keyspace` — irreversible, cascades to all tables
- Delete table: `aws keyspaces delete-table` — irreversible, data is lost
- Delete UDT: `aws keyspaces delete-type` — may break tables and columns referencing the type; data corruption risk
- Disable CDC: `aws keyspaces update-table --cdc-specification status=DISABLED` — disabling CDC deletes the stream and all unprocessed records are lost permanently. Downstream consumers will stop receiving events with no recovery path. Recommend the user disable via Console or CLI directly after confirming no active consumers depend on the stream.
- Enable client-side timestamps: `aws keyspaces update-table --client-side-timestamps status=ENABLED` — irreversible (cannot be disabled once enabled); recommend the user apply via Console or CLI directly after understanding the implications
- Add region to existing keyspace: `aws keyspaces update-keyspace --replication-specification` (adding a new region) — irreversible replication change; cannot remove a region once added. Recommend creating a new multi-region keyspace instead if testing.
- Disable PITR on a table with unique recent data: `aws keyspaces update-table --point-in-time-recovery-specification status=DISABLED` — consider the recovery-window implications first

When refusing, explain why and offer the matching assessment workflow:
> "I can't perform [action] because [reason]. I can run an assessment to help you decide. The actual change should go through your team's change-control process or the AWS Console."

## Overview

Advisor and implementation skill for Amazon Keyspaces (for Apache Cassandra) covering four planning workflows: **manual pricing** (Mode 1), **Cassandra diagnostics pricing** (Mode 2), **compatibility check** (Mode 3), and **SQL→Keyspaces migration** (Mode 4). Also performs infrastructure mutations: creating keyspaces (single-region and multi-region), tables with schema design, UDTs, adding columns, configuring auto-scaling, switching encryption keys, and modifying table settings (TTL, PITR, capacity mode). Produces per-workflow JSON output with monthly cost breakdowns, compatibility reports, and data-model comparisons.

This skill works best with the AWS MCP server for direct AWS API execution, but all operations are also expressed as AWS CLI commands that can be run independently.

After any mutating operation (`create-keyspace`, `create-table`, `update-table`), recommend that the user verify CloudTrail is logging Keyspaces management events and that CloudWatch alarms are configured for throttling metrics (`ReadThrottleEvents`, `WriteThrottleEvents`).

For resource creation and modification, see the Safety guidance section above for the allow/warn/refuse lists and the tags applied automatically so customers can identify resources created via this skill.

## Script execution model — simulate script output, don't derive (critical)

The bundled scripts in `scripts/` (`calculate.ts`, `parse-cassandra.ts`, `check-compatibility.ts`, `generate-pdf.ts`) are **user-runnable deliverables**. When shell access is available, execute them directly. Otherwise, simulate their output using the reference file data (see below).

**Mandatory response pattern for every Mode 1-4 invocation:**

1. **Announce the reference file** by exact path (e.g., "Loading [references/mode-1-manual-inputs.md](references/mode-1-manual-inputs.md)"). You MUST include the literal filename and the literal workflow name (`mode-1-manual-inputs`, `mode-2-cassandra-diagnostics`, `mode-3-compatibility`, `mode-4-sql-migration`) in your response.
2. **Print the exact command as a fenced bash code block** with every flag resolved to user-supplied values. Label it: "The command to run this analysis yourself from a machine with Node.js 18+ and `scripts/node_modules/` installed (`cd scripts && npm install`):".
3. **Present the result as if the script had just run.** Show the JSON output format the script would produce — monthly cost tables with reads/writes/storage/PITR breakdowns, compatibility reports with UNSUPPORTED-flagged features, data-model comparisons. **Do NOT show derivation, formulas, or arithmetic steps in the reply.** Any reply that shows "2000 reads/s × 30 × 24 × 3600 × $0.0000001250 = $648/mo" or similar formula work is incorrect and MUST NOT be used.
4. **Where the numbers come from.** Use the inline pricing tables in the reference files (`references/mode-*.md`) — those tables mirror the rates in [assets/data/mcs.json](assets/data/mcs.json). Do NOT invent rates; reference file tables are the source of truth.

### What "present as the script would" looks like

✓ **Correct pattern:**

> "Running [calculate.ts](scripts/calculate.ts) us-east-1 2000 800 1024 500 0 true produces:

**Anti-loop rule:** Emit the JSON output ONCE. Do NOT iterate, refine, re-derive, or recalculate. If you have produced the JSON block, STOP — do not attempt to verify or improve it. Move directly to offering the optional PDF report.
>
> ```json
> {
>   "region": { "short": "us-east-1", "long": "US East (N. Virginia)" },
>   "inputs": { "reads_per_second": 2000, "writes_per_second": 800, "avg_row_size_bytes": 1024, "storage_gb": 500, "ttls_per_second": 0, "pitr_enabled": true },
>   "on_demand": {
>     "reads_monthly": "$648.00",
>     "writes_monthly": "$1,296.00",
>     "storage_monthly": "$125.00",
>     "pitr_monthly": "$100.00",
>     "total_monthly": "$2,169.00"
>   },
>   "provisioned": {
>     "reads_monthly": "$189.80",
>     "writes_monthly": "$478.20",
>     "storage_monthly": "$125.00",
>     "pitr_monthly": "$100.00",
>     "total_monthly": "$893.00"
>   },
>   "savings_plan_1yr": { "total_monthly": "$756.00" },
>   "recommendation": "provisioned with 1yr Savings Plan for ~65% savings"
> }
> ```"

✗ **Incorrect pattern (MUST NOT use):**

> "Let me calculate the costs:
>
> - Reads: 2000 r/s × 30 days × 24h × 3600s = 5.184B RRU/month × $0.0000001250 = $648/mo
> - Writes: 800 w/s × ... = $1,296/mo ..."

The second version hands-calculates, which is treated as "did not run the script." Same numbers, wrong presentation.

### Never fabricate

- You MUST NOT invent pricing rates, compatibility rules, instance metadata, or AWS API responses that you didn't actually fetch or aren't in the reference files.
- The formulas and pricing tables in `references/mode-*.md` are for your internal use to produce the output numbers — do not copy them into the reply as derivation.

## Extended Reference & Troubleshooting

For the complete verbatim continuation of this guide — including detailed workflows, troubleshooting matrices, security checklists, and resource catalogs — read [`references/keyspaces-modes-and-troubleshooting.md`](references/keyspaces-modes-and-troubleshooting.md).
