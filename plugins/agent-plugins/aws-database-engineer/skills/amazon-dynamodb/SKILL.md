---
name: amazon-dynamodb
description: "Designs, reviews, and debugs DynamoDB data layers from design axioms — enumerates access patterns, chooses partition/sort keys and GSIs, decides single-table vs. multi-table, configures Streams, Global Tables, TTL, vector indexes for similarity search, and zero-ETL integrations to OpenSearch/Redshift/SageMaker Lakehouse, and produces a defensible data-layer design with a monthly cost estimate and optional live validation. Applies whenever a user is designing, reviewing, or refactoring anything backed by DynamoDB — schemas, access patterns, GSIs, single- vs. multi-table choices, Streams consumers, transactional outboxes, Global Tables, zero-ETL pipelines, or storing embeddings and running semantic/vector similarity search with SearchVectors on items already in DynamoDB — even when they don't say \"axioms\" or \"design review.\" Also applies when debugging hot partitions, throttling, unbounded Scans, LWW conflicts, or surprise bills on DynamoDB. Query live AWS state via MCP tools only (never raw aws CLI)."
version: 2
---

# DynamoDB Axioms

> **MCP-Only Live AWS Execution:** Perform ALL live AWS API discovery, account/region checks (`sts:GetCallerIdentity`), cluster/instance/table inspection, CloudWatch telemetry, pricing (`awspricing`), and docs (`awsknowledge`) strictly via connected MCP tools (`aws-mcp` `aws___run_script` `call_boto3`, `dynamodb`, `elasticache`, `postgres`, `mysql`, `cloudwatch`, `awspricing`, `awsknowledge`) — **never invoke raw `aws ...` CLI commands (such as `aws --version` or `aws sts get-caller-identity`) in shell (`run_command`)**. Local offline helper scripts under `scripts/` may be run via `python3` or `node`.

This document is a set of design axioms for DynamoDB applications. It is intended to be read by an agent with no other context about the application and used to produce a defensible data-layer design.

## Guardrail — where this skill's own files live (MCP vs local install)

This skill can be loaded two ways, and they resolve the skill's own bundled
files from different places. Determine how the skill was loaded before reading
a reference or running a script:

- **Loaded through the AWS MCP `retrieve_skill` tool:** The skill is not
  installed on the local filesystem. You MUST fetch each reference or script
  via `retrieve_skill` with the `file` parameter (e.g.
  `file="references/vector-search.md"` or `file="scripts/calculate_costs.py"`), and
  run the script from the returned content. Do NOT `file_read` these paths
  locally — they do not exist on disk.
- **Installed locally** (e.g. `.kiro/skills/amazon-dynamodb/` or
  `~/.claude/skills/amazon-dynamodb/`): Read and run files from the local skill
  directory using relative paths.

This distinction applies only to the skill's own packaged files. User data and
session artifacts are always read from and written to the user's working
directory. Never fetch or write customer data through `retrieve_skill`.

Separately from where these files live: this skill calls real AWS APIs when it
validates a design, deploys a scratch table or benchmarks one. **The AWS MCP
server is recommended for those AWS interactions where it is available** — it
gives consistent credential handling and region resolution across hosts. It is
**not required**: every script here uses boto3 and the AWS CLI against the
ambient credential chain, so the skill works unchanged when no MCP server is
present.

The `${SKILL_DIR}` resolution below applies to the **locally installed** case: over
MCP there is no directory to resolve, and the scripts this skill ships cannot be
executed from a returned string — so a cost estimate or live validation requires
the locally installed form.

## Resolving the skill's own paths

This skill is host-agnostic — it runs under Claude Code, Kiro, Codex, Cursor, a plain terminal, or CI. Where it lives on disk depends on the host (`~/.claude/skills/…`, `~/.kiro/…`, `~/.codex/…`, `~/.cursor/…`, a repo checkout, anywhere). The agent's working directory is the **user's project**, not the skill bundle, so relative paths like `scripts/calculate_costs.py` will not resolve. Throughout this document, `${SKILL_DIR}` means **the absolute path of the directory that contains this SKILL.md file** (the skill root, which holds `scripts/` and `references/`).

**Resolve `${SKILL_DIR}` once per session, then reuse it.** Pick the first method that works in your host:

1. **You already know it.** You loaded SKILL.md from a path — `${SKILL_DIR}` is the directory that file is in. This is the most reliable source; prefer it.
2. **An environment variable.** If `$DDB_SKILL_DIR` is set, trust it.
3. **The bundled resolver** (host-neutral, no host assumptions). It searches the common install roots *and* verifies the hit against sentinel files, so it never returns the wrong directory silently:

   ```bash
   # If you already know the path to the script, just run it directly:
   #   SKILL_DIR="$(sh /path/to/amazon-dynamodb/scripts/find_skill_dir.sh)"
   # If you don't, this host-neutral one-liner searches the common roots
   # (~/.claude, ~/.kiro, ~/.codex, ~/.cursor, ~/.config, ~/.local/share, $PWD):
   SKILL_DIR="$(find "$HOME" "$PWD" -maxdepth 7 -type f -name SKILL.md -path '*amazon-dynamodb*' 2>/dev/null \
                | head -1 | xargs -I{} dirname {})"
   # Verify it before trusting it (sentinel check), then hand off to the resolver
   # for its loud-on-failure diagnostics:
   SKILL_DIR="$(sh "$SKILL_DIR/scripts/find_skill_dir.sh" 2>/dev/null || echo "$SKILL_DIR")"
   ```

   The resolver prints the verified skill root and exits 0, or prints nothing and exits non-zero with a fix-it message — so `SKILL_DIR="$(sh …/find_skill_dir.sh)"` is safe to trust when it succeeds. It is plain POSIX `sh`, so it behaves identically across hosts.

Once resolved, **export it so every later command is a clean substitution** and the scripts can also pick it up:

```bash
export DDB_SKILL_DIR="$SKILL_DIR"
python3 "$DDB_SKILL_DIR/scripts/calculate_costs.py" --model dynamodb_data_model.json --output cost_report.md
```

Internally the scripts locate their own siblings (other scripts, `scripts/benchmark_lambda.py`) relative to themselves, so you only ever need the **root** path — never each individual script path.

**Rules:**

- Always invoke scripts with an absolute path (the `$DDB_SKILL_DIR/…` form). Do **not** `cd` into the skill directory — the user's working directory must stay put so their artifacts (`dynamodb_data_model.json`, `cost_report.md`, …) land where they expect.
- If none of the three methods resolves the directory, **stop and ask the user where the skill is installed** rather than guessing. A wrong `${SKILL_DIR}` produces confusing "file not found" failures downstream; one clarifying question is cheaper.

## The pipeline at a glance

The skill is one tool per stage. **The default path touches no AWS: most work is stage 1 (a design you can discuss and refine conversationally).** Stage 2 (cost) runs on request or when the design is being finalized — not reflexively every turn. Stages 3–6 are a distinctly opt-in, heavyweight fork that creates real AWS resources and incurs a real bill; enter it only on explicit user agreement. Each stage's detailed contract is in the section named in the last column.

| # | Stage | Command (after `export DDB_SKILL_DIR=…`) | Reads | Writes | AWS? | Section |
|---|---|---|---|---|---|---|
| 1 | Design | *(no script — you produce the access-pattern list + schema)* | — | *(in-reply artifacts)* | no | *Artifacts to produce* |
| 2 | Cost | `python3 "$DDB_SKILL_DIR/scripts/calculate_costs.py" --model dynamodb_data_model.json --output cost_report.md` | `dynamodb_data_model.json` | `cost_report.md` | no | *Cost estimation* |
| 3 | Deploy | `python3 "$DDB_SKILL_DIR/scripts/deploy_model.py" --model dynamodb_data_model.json --config benchmark_config.json --manifest-out created_resources.json --yes-deploy` | model + config | `created_resources.json` | **yes** | *Live validation* |
| 4 | Benchmark | `python3 "$DDB_SKILL_DIR/scripts/benchmark_model.py" --model dynamodb_data_model.json --config benchmark_config.json --manifest created_resources.json --raw-out perf_raw.jsonl --summary-out perf_summary.json` | model + config + manifest | `perf_raw.jsonl`, `perf_summary.json` | **yes** | *Live validation* |
| 5 | Report | `python3 "$DDB_SKILL_DIR/scripts/generate_perf_report.py" --model dynamodb_data_model.json --summary perf_summary.json --output performance_report.md` | model + summary | `performance_report.md`, `design_findings.json` | no | *Live validation* |
| 6 | Teardown | `python3 "$DDB_SKILL_DIR/scripts/generate_teardown.py" --manifest created_resources.json --out teardown.sh` → review → `bash teardown.sh --confirm` | manifest | `teardown.sh` | **yes** (on `--confirm`) | *Live validation* step 6 |
| — | Iterate | `python3 "$DDB_SKILL_DIR/scripts/iterate_design.py" …` (wraps 3→4→5→cost as one human-driven round) | model + config + loop-state + manifest | `loop_state.json` + the above | **yes** (gated) | *Iterative design loop* |

**Who reads what.** *You (the agent)* read the compact artifacts: `cost_report.md`, `design_findings.json`, `loop_state.json`. *The user* reads `performance_report.md`. Never read `perf_raw.jsonl` (large) — it only feeds stage 5.

**Consent gates.** Stage 3+ needs `--yes-deploy`; the benchmark refuses to spend over `cost_guardrail_usd` without `--allow-spend`; teardown needs the user's attested review **and** intent before you run `bash teardown.sh --confirm`. Details in *Live validation*.

**AWS access (MCP recommended, not required).** Stages 3–6 talk to AWS (create tables, a Lambda, an IAM role, then benchmark and tear down). For the best experience with AWS API calls the **AWS MCP server is recommended but not required** — every script here uses `boto3` directly and runs from a plain shell with standard AWS credentials (a profile, SSO, or environment credentials), so the skill works identically with or without the MCP server. Nothing in this skill assumes MCP-specific tools.

## How to use these axioms

1. **Read the reference architecture first** when the task is to design, review, or critique a full-app data layer (multi-entity schemas, multi-table layouts, end-to-end composition with streams/search/notifications). `${SKILL_DIR}/references/reference-architecture.md` is a complete multi-tenant kanban task-board ("TaskBoard") SaaS on AWS backed by DynamoDB, with all of the surrounding pieces (Cognito, CloudFront, HTTP API, Lambdas, Streams, OpenSearch, AppSync Events, SQS/EventBridge, cascades, idempotency middleware) worked out and justified. The axioms tell you *what* must be true; the reference shows *how* these pieces fit together in practice. Not reading it on a multi-table design means you will miss patterns that are in the reference but hard to re-derive from axioms alone — idempotency middleware, phantom-upsert guards, AppSync channel authorization, the Notifications-as-EventBridge-not-table decision, cascade-delete via chunked `BatchWriteItem`. Skip this step only for small-scope questions — a single-table question, a query-cost calculation, a pointed debugging question.
2. Produce the **access-pattern list** (next section) before applying any axiom below. Every modeling axiom assumes this list exists; an axiom that asks "is this pattern frequent?" or "what does this query return?" cannot be applied without it.
3. Produce the **artifacts** listed under *Artifacts to produce*. These are the outputs of a design, not intermediate notes. The axioms shape the artifacts; the artifacts are what the agent hands back.
4. Apply the **Patterns** section alongside the axioms. Patterns are not axioms — they are load-bearing implementation details that the reference made concrete, and that a design will need even when no axiom explicitly calls for them.
5. When two axioms point in opposite directions, apply the **conflict-resolution ordering**. Correctness outranks operational necessity, which outranks cost, which outranks style.
6. When a term is ambiguous, consult the **glossary**. Do not guess.

### Operating discipline: announce, act, verify from evidence

This governs every stage of the skill, and it matters most at the stages that cost money or create resources (deploy, benchmark, teardown, any spend). Three beats, always in this order:

1. **Announce.** Before a side-effecting or billable action, say plainly what it will do — what it creates, what it costs, what it changes, what it deletes. The user should never be surprised by a resource, a charge, or a deletion.
2. **Act.** Run the command. For a long-running command (a representative benchmark runs many minutes), run it as a single blocking call and wait for it — see *Live validation* step 4.
3. **Verify from evidence, then state only what the evidence supports.** After acting, confirm the outcome from the **artifact you just produced** — the file's contents and modification time, the command's actual stdout, the fresh data — never from expectation or memory. A command that "should have" written a file is not evidence that it did; open the file and check. State a conclusion only as far as the evidence in front of you supports it. **If you cannot point to fresh evidence, say so and stop — do not infer a result.** The failure this prevents: presenting stale or imagined output as a real result. The tell is a number that didn't change when it should have (e.g. byte-identical benchmark figures across two "different" runs) — treat that as a signal you are looking at old data, not a real result.

### Summary of the 10 Non-Negotiable DynamoDB Facts (Full Details in [`references/dynamodb-axioms-and-validation.md`](references/dynamodb-axioms-and-validation.md))
1. **DynamoDB Streams iterators** are `TRIM_HORIZON` and `LATEST` only (24h retention; never Kinesis iterator types).
2. **GSI `Projection` is immutable** (`UpdateTable` allows at most 1 GSI Create OR Delete per call; additive new-GSI cutover avoids downtime).
3. **Capacity-mode switches (`PAY_PER_REQUEST` <-> `PROVISIONED`)** have a **24-hour cooldown**.
4. **Single-item `PutItem`/`UpdateItem`/`DeleteItem` are atomic** with `ConditionExpression` (never wrap single items in `TransactWriteItems` at 2x WCU; **`ConditionExpression` is write-only** — `GetItem`/`Query`/`Scan` have no conditional read).
5. **Max item size is `400 KB`** (`1 MB` is the `Query`/`Scan` page cap).
6. **`BatchGetItem` / `BatchWriteItem` are NOT atomic** — retry `UnprocessedKeys` / `UnprocessedItems` with exponential backoff.
7. **Reserved Capacity applies ONLY to `PROVISIONED` mode**, never On-Demand (`PAY_PER_REQUEST`).
8. **Failed `ConditionExpression` (`ConditionalCheckFailedException`) still consumes full WCU/WRU**.
9. **GSI `KeySchema` is immutable** — re-keying or write-sharding requires an additive new GSI migration (enable **CloudWatch Contributor Insights for DynamoDB** to pinpoint throttled/hot partition and GSI keys before re-sharding).
10. **Native Vector Search (`VectorIndexes` + `SearchVectors`, `boto3 >= 1.43.64`)** requires On-Demand capacity, has immutable `Dimensions`/`DistanceFunction`/`Projection`/`SearchSchema`, rejects `Query`/`Scan`/PartiQL/DAX on the vector index, and **never auto-recomputes embeddings** when text changes.
11. **Destructive & credential refusals** — never delete live tables without explicit confirmation and never read `.env` credentials; always offer safe read-only alternatives (`DescribeTable`, `DescribeContinuousBackups` PITR check, and `ListBackups` snapshot verification).

## Extended Reference, Critical Facts & Troubleshooting

**IMPORTANT:** Before answering domain-specific questions, troubleshooting errors, or applying rubric checklists, read [`references/dynamodb-axioms-and-validation.md`](references/dynamodb-axioms-and-validation.md) for the complete verbatim critical facts, workflows, security controls, and troubleshooting playbooks.
