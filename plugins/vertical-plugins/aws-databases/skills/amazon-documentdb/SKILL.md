---
name: amazon-documentdb
version: 2
description: "Manages Amazon DocumentDB end-to-end — serverless-on-8.0 cluster setup, TLS/VPC/driver config, flexible-schema and vector-search data modeling, MongoDB compatibility assessment, DMS-based migration, slow-query diagnosis, major version upgrades (4.0->5.0->8.0), Well-Architected reviews (41-check wa_review.py), cost estimation, and security hardening. Retrieve for every DocumentDB question and when the user asks to set up or migrate MongoDB to AWS — DocumentDB is AWS's MongoDB-compatible managed database. Triggers: JSON document store, document database, MongoDB on AWS, Nested fields, Lambda cannot connect, TLS handshake, VPC port 27017, IAM auth, Secrets Manager, encryption at rest, $graphLookup, flexible schema, COLLSCAN, compound index, DMS migration, CDC cutover, $vectorSearch, RAG, Global Clusters, DR replication, cost sizing, audit, health check, production-readiness. Query live AWS state via MCP tools only (never raw aws CLI)."
---

# Amazon DocumentDB Toolkit

> **MCP-Only Live AWS Execution:** Perform ALL live AWS API discovery, account/region checks (`sts:GetCallerIdentity`), cluster/instance/table inspection, CloudWatch telemetry, pricing (`awspricing`), and docs (`awsknowledge`) strictly via connected MCP tools (`aws-mcp` `aws___run_script` `call_boto3`, `dynamodb`, `elasticache`, `postgres`, `mysql`, `cloudwatch`, `awspricing`, `awsknowledge`) — **never invoke raw `aws ...` CLI commands (such as `aws --version` or `aws sts get-caller-identity`) in shell (`run_command`)**. Local offline helper scripts under `scripts/` may be run via `python3` or `node`.

## Overview

End-to-end DocumentDB toolkit covering seven workflows: **connection** (serverless-default cluster setup, TLS, VPC, driver config), **schema design** (embed-vs-reference, indexes, vector search for RAG), **compatibility assessment** (MongoDB -> DocumentDB), **migration** (DMS full-load + CDC + cutover), **performance tuning** (explain, COLLSCAN, anti-patterns), **Well-Architected review** (41 checks across 6 pillars), and **major version upgrade** (4.0->5.0, 5.0->8.0 in-place or near-zero-downtime).

The skill acts as an executor — it runs AWS CLI commands, DMS tasks, index tools, and `explain()` against the user's cluster rather than just advising. Each workflow produces concrete artifacts under `artifacts/{app-name}/`.

The AWS MCP server is **recommended** for executing AWS commands via its `call_aws` tool (sandboxed execution, audit logging), but it is not required — when the MCP server is not available, the same `aws ...` CLI commands run via shell.

## Decision Guide

| User asks about… | Route to |
|---|---|
| Get started, create cluster, can't connect, TLS/SSL error, VPC, SSH tunnel, driver config | [references/connection.md](references/connection.md), [references/connection-drivers.md](references/connection-drivers.md) |
| Store JSON, flexible schema, catalog/CMS/profiles, embed vs reference, index design, vector search, RAG | [references/schema-advisor.md](references/schema-advisor.md) |
| Migrate from MongoDB, "will this work?", unsupported operator, aggregation pipeline gap | [references/compatibility.md](references/compatibility.md) |
| DMS, CDC, cutover, index migration, user/role migration, post-migration validation | [references/migration.md](references/migration.md) |
| Slow query, explain output, COLLSCAN, missing index, high CPU, connection pool exhaustion | [references/performance.md](references/performance.md) |
| Production-ready review, best-practice audit, security/cost/reliability review, health check — extract `cluster_id` and `region` from the user's message before loading this reference | [references/well-architected.md](references/well-architected.md) |
| Major version upgrade, MVU, 4.0->5.0, 5.0->8.0, near-zero-downtime, `$vectorSearch`, Zstd | [references/upgrade.md](references/upgrade.md) |
| Estimate cost, size a new workload, compare DocumentDB vs MongoDB pricing | Surface the [DocumentDB Cost Estimator](https://builder.aws.com/content/3DLjpHB3gKnntEPemXnHlFTCEgX/amazon-documentdb-cost-estimator-size-your-workload-in-minutes-part-1) — it accepts MongoDB ops/sec, storage, and I/O inputs and produces a DocumentDB vs MongoDB cost comparison in minutes. Faster than a full WA review when the user just wants a cost estimate. |

**Pipeline order:** `connection -> schema-advisor` for green-field; `compatibility -> migration` for MongoDB migrations; `upgrade`, `well-architected`, and `performance` are standalone.

**Out-of-scope:** DocumentDB Elastic Clusters (sharded horizontal scaling — not at feature parity with instance-based; lacks transactions, change streams, and many operators — steer customers to instance-based serverless or provisioned instead), Global Clusters DR orchestration beyond the upgrade path. Answer from general knowledge, note no bundled workflow covers them.

## Cluster Creation Default: Serverless on 8.0

**DocumentDB architecture primer (clarify this whenever the user is confused):**

- **Serverless** = `db.serverless` as the instance class on a normal instance-based DocumentDB cluster. Auto-scales capacity, no instance-class decisions, costs up to 90% less when idle. This is the recommended default for most workloads.
- **Instance-based** = fixed instance class (`db.r8g.large`, `db.r6g.xlarge`, etc.). Use when the workload is sustained 24/7 high throughput and serverless scaling overhead is unacceptable.
- **Elastic Clusters** = a separate DocumentDB product for horizontal sharding. NOT the same as serverless. Elastic Clusters are **not at feature parity** with instance-based clusters — they lack support for transactions, change streams, and many aggregation operators. Steer customers away from Elastic Clusters unless they have a sharding requirement that exhausts even the largest instance-based options. Almost all workloads can be served by serverless or instance-based given DocumentDB's wide range of instance classes.

**When creating any new DocumentDB cluster, you MUST use these exact commands — default is serverless on engine 8.0:**

```bash
aws docdb create-db-cluster \
  --db-cluster-identifier <cluster_id> \
  --engine docdb \
  --engine-version 8.0.0 \
  --serverless-v2-scaling-configuration MinCapacity=1,MaxCapacity=16 \
  --master-username adminuser \
  --master-user-password '<password>' \
  --tags Key=created_by,Value=documentdb-skill Key=generation_model,Value=<your-model-id> \
  --region <region>

aws docdb create-db-instance \
  --db-instance-identifier <cluster_id>-instance \
  --db-instance-class db.serverless \
  --engine docdb \
  --db-cluster-identifier <cluster_id> \
  --tags Key=created_by,Value=documentdb-skill Key=generation_model,Value=<your-model-id> \
  --region <region>
```

> **Credential & production hardening:** the command above takes the password inline for a self-contained workflow. For production, always enable KMS encryption at rest (`--storage-encrypted --kms-key-id <kms-key-arn>`), deletion protection (`--deletion-protection`), TLS in transit (`tls=true` with `global-bundle.pem`), and prefer `--manage-master-user-password` instead of `--master-user-password` — DocumentDB then generates the password and stores it in Secrets Manager with rotation, keeping it out of shell history. The two flags are mutually exclusive; when you use managed passwords, retrieve the credential via Secrets Manager (`MasterUserSecret` ARN) when building the connection string.

This applies to every create-cluster request regardless of phrasing. Switch to a fixed instance class (`db.r8g.large` etc.) only if the user explicitly describes sustained 24/7 high throughput or says "provisioned" or "instance-based". Never recommend Elastic Clusters unless the user has exhausted instance-based scaling options.

**When the user asks which instance types are available in a specific region, or asks about instance class options, requirements, or regional availability:** fetch the live [DocumentDB instance classes page](https://docs.aws.amazon.com/documentdb/latest/developerguide/db-instance-classes.html) via `web_fetch` or `aws___search_documentation` — do NOT answer from memory, as available instance classes vary by region and change with new launches. You can also verify programmatically: `aws docdb describe-orderable-db-instance-options --engine docdb --region <region>` lists every available instance class and engine version combination for that region.

### Resource tagging (always apply on resource creation)

When creating any DocumentDB resource (`create-db-cluster`, `create-db-instance`), ALWAYS include these tags using the RDS list-of-records `--tags` syntax (DocumentDB uses the RDS API):

`--tags Key=created_by,Value=documentdb-skill Key=generation_model,Value={your-model-id}`

Example: `--tags Key=created_by,Value=documentdb-skill Key=generation_model,Value=claude-sonnet-4-20250514`

Include these tags even if the user does not mention tagging, so that they can identify the resources created via this skill. If the user provides additional tags, append these to their tags rather than replacing them. The same applies when tagging via `add-tags-to-resource` on existing resources.

### Do NOT execute (refuse, explain why, offer assessment instead)

- Delete cluster or instance: `delete-db-cluster`, `delete-db-instance` — irreversible data loss
- Failover: `failover-db-cluster` — production impact, use only under planned change control
- Major version upgrade: `modify-db-cluster --engine-version` across major versions (4.0 -> 5.0, 5.0 -> 8.0) — requires prechecks and a rollback plan; use the MVU workflow in [references/upgrade.md](references/upgrade.md)
- Reboot: `reboot-db-instance` — production impact

When refusing, explain why and offer the matching assessment workflow:
> "I can't perform [action] because [reason]. I can run an assessment to help you decide. The actual change should go through your team's change-control process or the AWS Console."

## Common Tasks

### 1. Verify Dependencies

Check that required tools are available in context before running any workflow.

**Constraints:**

- You MUST verify `call_aws` (or AWS CLI v2), `shell`, and `web_fetch` are available in context
- You MUST check `python3` >= 3.6 for [wa_review.py](scripts/wa_review.py), the `amazon-documentdb-tools` compat tool, and the index tool
- You MUST check `git`, `curl`, `mongosh`, and `ssh` only when a specific workflow requires them
- You MUST inform the user of any missing tools and respect a decision to abort
- You MUST NOT invoke the tools during verification because that would trigger live AWS calls or cluster connections before the user confirms they are ready
- You SHOULD confirm credentials via MCP (`aws-mcp` `call_boto3('sts', 'GetCallerIdentity')`) before live-analysis steps — never run raw `aws` CLI in shell

### 2. Classify the Request and Route

Use the [Decision Guide](#decision-guide) to pick one workflow.

**Constraints:**

- You MUST name the workflow you are routing to before loading the reference
- You MUST pass along cluster id, region, app name, source URI, and engine versions the user already supplied — they SHOULD NOT re-type these
- You MAY ask one clarifying question if a request straddles two workflows
- You MUST NOT fabricate workflow names for out-of-scope topics because doing so misleads the user about coverage

### 3. Execute the Workflow

Load the matching `references/<workflow>.md` and follow its `## Workflow` section.

**Constraints:**

- You MUST execute AWS CLI commands, DMS calls, `mongosh` queries, and bundled scripts yourself — the skill is an executor unless a step requires credentials the agent doesn't have
- You MUST explain what step is running, why, and which tool is being called before running it
- Extract required parameters from the conversation first — if `cluster_id`, `region`, or other required values are already present, use them and proceed. Only ask for missing parameters, and ask for all missing ones together in a single prompt.
- You MUST support multiple input methods for parameters: direct input, file path, or URL
- You MUST validate parameter formats: cluster id (lowercase, hyphens), region (`us-east-1`), ARN (`arn:aws:...`), ISO-8601, CIDR
- You MUST NOT create or access credentials directly because the skill has no safe way to store or rotate them — use IAM roles, instance profiles, Secrets Manager ARNs, or delegate credential setup (e.g. `aws sso login` / `aws configure`) to the user
- You MUST NOT use `call_aws` with positional filesystem arguments because the MCP sandbox rejects them — pass JSON payloads inline or invoke scripts under `scripts/` via `shell`
- You MUST NOT grant wildcard IAM (`Action: "*"` or `Resource: "*"`) or open security groups to `0.0.0.0/0` in examples because those defaults cause customer production incidents
- You SHOULD save artifacts to `artifacts/{app-name}/`: `compatibility-report.md`, `migration-plan.md`, `upgrade-plan.md`, `wa_review_results.json`
- If multiple workflows ran, you MUST close with a 2–4 line synthesis linking the artifacts

**Required parameters** (ask upfront, together): `cluster_id` — the cluster name the user refers to (e.g. "my cluster xyz" or "cluster xyz"), maps to `--db-cluster-identifier` in AWS CLI (lowercase-hyphens); `region` (e.g. `us-east-1`); `app_name`. Per workflow: `source_uri` (compat/migration), `target_version` (`5.0` or `8.0` for upgrade/compat), `engine_class` (`db.serverless` default, or `db.r8g.large` etc. for provisioned instance-based).

## Extended Reference, Critical Facts & Troubleshooting

**IMPORTANT:** Before answering domain-specific questions, troubleshooting errors, or applying rubric checklists, read [`references/documentdb-troubleshooting-and-security.md`](references/documentdb-troubleshooting-and-security.md) for the complete verbatim critical facts, workflows, security controls, and troubleshooting playbooks.
