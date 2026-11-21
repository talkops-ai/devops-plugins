---
name: llm-to-bedrock
description: "Use when the user wants to migrate code that calls OpenAI, Gemini/Google AI, or the Anthropic API to Amazon Bedrock — a pure model/SDK rewrite. End-to-end: assesses the codebase, rewrites SDK calls, evaluates output quality against Bedrock, and delivers a ready-to-merge git branch. Also has an access-only mode for users who just want to check or enable Bedrock model access for specific models (e.g. 'request access to Claude on Bedrock', 'enable GPT models on Bedrock', 'which models do I turn on') with no code migration — it checks each model and walks the right access step (Marketplace/model access and IAM) for the named models, then stops. Not for agent runtime selection or agent migration planning (use agent-advisor), nor standalone cost estimates or infra-only migration. The full migration REQUIRES gcp-to-aws installed alongside this skill (Assess is delegated to it, no standalone fallback if absent); access-only mode does not need gcp-to-aws."
---

# Migrate to Bedrock (Assess + Execute)

End-to-end AI SDK/model migration from OpenAI, Google Gemini, or Anthropic APIs to Amazon Bedrock, plus a standalone **Access-Only Mode** for checking and enabling Bedrock model entitlements without modifying source code.

## MCP-Only Execution & Read-Only Safety

- **MCP-Only Live Queries:** Execute **all** live AWS discovery, Bedrock/SageMaker control-plane checks, pricing lookups, IaC compliance checks, CloudWatch telemetry queries, and documentation searches **exclusively via connected MCP tools**: `aws-mcp` (`aws___run_script` using read-only `await call_boto3(...)`, `aws___search_documentation`, `aws___read_documentation`), `sagemaker` (`describe_hp_cluster`), `agentcore`, `strands-agents`, `cloudwatch`, `awspricing` (`get_pricing`, `get_bedrock_patterns`), `awsiac`, and `awsknowledge`. Offline pure-Python bundled helper scripts in `scripts/*.py` (`validate_result.py`, `render_report.py`, `iam_policy.py`, `bedrock_pricing.py`) that perform local math/schema rendering without live AWS credentials are permitted when inspecting local inputs, whereas live AWS API queries must go through MCP rather than raw `aws` CLI or boto3 shell scripts.
- **Strict Read-Only & Secret Safety:** **Never** run raw `aws ...` (not even `aws sts get-caller-identity` — always query `sts.GetCallerIdentity` inside `aws___run_script`) CLI commands in Bash/`run_command`, **never** mutate live AWS resources (`Create*`, `Update*`, `Delete*`, `InvokeModel`, `CreateEndpoint` — refuse unapproved mutations and present a safe, approval-gated plan with verification and rollback steps), and **never** read or expose plaintext secrets (`secretsmanager:GetSecretValue`, `ssm:GetParameter` with `WithDecryption=True`, `.env` API keys, or `.saws-migrate/.source-provider-env` values).
- **Unmapped Edge Cases:** Query `awsknowledge` / `aws-mcp` documentation search tools (`aws___search_documentation`, `aws___read_documentation`) with 1–2 focused queries before recommending unverified model parameters or Mantle endpoints.

## Skill Paths & Sibling Dependency

Call this skill's directory `<SKILL_BASE>`:
- `$SCRIPTS` = `<SKILL_BASE>/scripts`
- `$HELPERS` = `<SKILL_BASE>/references/helpers`
- `$GCP_BASE` = `<SKILL_BASE>/../gcp-to-aws` (fallback local phase mirrors under `references/phases/`)

Full code migration delegates Phase A (Assess) inline to `gcp-to-aws`'s phase files; **Access-Only Mode** does not require `gcp-to-aws`.

---

## Step 0 — Check Prerequisites & Route Mode

1. **0a — Verify `uv`:** Ensure `uv` is installed (`https://docs.astral.sh/uv/getting-started/installation/`). If missing, instruct the user to install `uv` and stop.
2. **0a-bis — Route Full Migration vs. Access-Only Mode (run BEFORE `0b`):**
   - Route to **Access-Only Mode** ([references/access-only-mode.md](references/access-only-mode.md)) when `$ARGUMENTS` contains an explicit access phrase (`model access`, `request access`, `enable model access`, `just access`, `preflight`) with no source-code path, **or** the user asks to check/enable Bedrock model access without code changes (do not trigger on bare words `enable` or `access` alone, e.g., `"enable the Bedrock rewrite"` is Full Migration).
   - If ambiguous (both codebase and access mentioned), ask via **AskUserQuestion**: `[Full migration]` vs `[Just model access]`.
3. **0b — Verify sibling `gcp-to-aws` (Full Migration only):**
   - Check whether `<SKILL_BASE>/../gcp-to-aws/SKILL.md` is installed. If missing, **stop immediately** — do not improvise a standalone Assess phase; instead offer all three actionable paths: (1) install `gcp-to-aws` alongside `llm-to-bedrock` (`npx skills add aws/agent-toolkit-for-aws/plugins/aws-startup-advisor/skills --skill llm-to-bedrock --skill gcp-to-aws`), (2) use standalone **`ai-to-bedrock`** for decoupled AI SDK codebase migration without `gcp-to-aws`, or (3) run **`llm-to-bedrock` Access-Only Mode** (`model access preflight`) without codebase discovery.

---

## Step 1 — Collect & Validate `$REPO` (Full Migration)

1. Obtain `$REPO` from `$ARGUMENTS` or ask via **AskUserQuestion** (local path or GitHub URL).
2. **Git-root check:** Compare `git -C <REPO> rev-parse --show-toplevel` against `cd <REPO> && pwd -P` (handles macOS `/tmp` → `/private/tmp`). If not a git repo, stop and re-ask (deliverable is a git branch). If a subdirectory inside a git repo, ask whether to use the repo root (recommended), continue in subdirectory, or abort.
3. **Dirty-tree check:** Check `git -C <REPO> status --porcelain`. If dirty, surface uncommitted files and ask `"Continue anyway"` vs `"Let me clean up first"`.

---

## Phase A — Assess (Inline `gcp-to-aws` AI Path)

Do **not** scan code or invent Clarify questions ad hoc. Read and execute `gcp-to-aws`'s phase files inline (resolving internal references under `$GCP_BASE`, while `$MIGRATION_DIR` lives under `$REPO/.migration/<MMDD-HHMM>/`):

1. **A1 — Execute Discover → Clarify → Design → Estimate in order:**
   - Resolve `$MIGRATION_DIR` per `references/phases/discover/discover.md` Step 0 (note: a directory lacking `.phase-status.json` is an interrupted fresh dir, not a resumable run).
   - Run `references/phases/discover/discover.md` (recording `"initiated_by": "LLM_TO_BEDROCK"` alongside `owning_skill: "GCP_TO_AWS"` in `.phase-status.json`). Gate: `ai-workload-profile.json` (and/or infra/billing profile) exists.
   - Run `references/phases/clarify/clarify.md` (`clarify-ai-only.md` when AI-only). Gate: `preferences.json` exists.
   - Run `references/phases/design/design.md` (`design-ai.md`). Gate: `aws-design-ai.json` exists.
   - Run `references/phases/estimate/estimate.md` and stop at the post-Estimate decision pack (do **not** run Terraform `generate.md`).
   - On any `GATE_FAIL`, stop immediately and report verbatim — never patch artifacts to force a gate.
2. **A2 — State Validation & Workshop Guard:** On session resume, validate `$MIGRATION_DIR/.phase-status.json` per `gcp-to-aws` § State Validation before resuming incomplete phases. If `phases.workshop == "in_progress"`, finish `design.md`'s workshop loop before treating Design as complete.
3. **A3 — Verify Assess Artifacts in the Exact Same `$MIGRATION_DIR`:** Never re-glob `ls -td .migration/*/` (which could pick an unfinished sibling run). Confirm `aws-design-ai.json`, `ai-workload-profile.json`, and `preferences.json` all exist in `$MIGRATION_DIR`.

---

## Phase B — Execute Prep

Read [references/phase-b-c-execution.md](references/phase-b-c-execution.md) and execute `B1`–`B4` in order:

1. **B1 — Parse Assess Outputs:** Extract `ai_architecture.bedrock_models[]` (`$TARGET_MODELS` + `use_case`), `summary.ai_source` (`ai-workload-profile.json`), and `design_constraints.target_region` (`$REGION`, default `us-east-1`). Stop if `bedrock_models[]` is empty.
2. **B2 — Confirm AWS Identity & Region:** Verify caller identity (`Account`, `Arn`, `UserId`) via `aws-mcp` (`sts` `GetCallerIdentity`) and confirm `$AWS_PROFILE_CHOICE` + `$REGION` with the user. Pass `$AWS_PROFILE_CHOICE` explicitly inline on every downstream tool/subagent invocation (never rely on shell `export`).
3. **B3 — Source API Key (Optional, Zero-Transcript Rule):** Create `$REPO/.saws-migrate/.gitignore` (`*`) first. Map provider to `OPENAI_API_KEY` | `ANTHROPIC_API_KEY` | `GEMINI_API_KEY`. **Never** accept, print, or read plaintext keys in chat, and **never read `.env`, `.env.local`, or `.saws-migrate/.source-provider-env` with agent file-read tools (strictly off-limits to agent reads)**; have the user materialize keys locally to `$REPO/.saws-migrate/.source-provider-env` (`chmod 0600`) outside the transcript.
4. **B4 — Bedrock Preflight:** When approved for active migration execution, run `scripts/preflight_bedrock.py --region $REGION --models <csv> --dataset-size 200` (in strictly read-only audit mode, inspect model/profile catalog read-only via `aws-mcp` instead). Route `credentials`, `model_access`, `authz`, `mantle_deps_missing`, `model_unavailable` ([references/helpers/resolve-bedrock-model-id/resolve-bedrock-model-id.md](references/helpers/resolve-bedrock-model-id/resolve-bedrock-model-id.md)), `quota_warning`, and `embedding_unprobed` per [references/phase-b-c-execution.md](references/phase-b-c-execution.md).

---

## Phase C — Execute (5-Agent Pipeline & Schema Gates)

Read [references/phase-b-c-execution.md](references/phase-b-c-execution.md) for the exact Subagent Context Block template, Helper-Reference injection table, `current-context.json` schema, and `RUN_CONTEXT=mismatch` invalidation matrix. Phase outputs live in `$PHASE_DIR = $REPO/.saws-migrate/phase-results/` and are validated after every step via `scripts/validate_result.py`:

| Step | Subagent (`aws-startup-advisor:*`) | Output Artifact | Schema (`scripts/schemas/*.json`) | Primary Helper References |
|---|---|---|---|---|
| **C0** | *(Orchestrator Run-Context Gate)* | `$PHASE_DIR/run-context.json` | `--check-run-context` | Warn user of ≤200 paid eval calls; run Stage 0 post-C5 git checks & scoped invalidation |
| **C1** | `llm2bedrock-code-analyzer` | `$PHASE_DIR/analysis.json` | [scripts/schemas/analysis.json](scripts/schemas/analysis.json) | [behavior-delta-detection.md](references/helpers/behavior-delta-detection/behavior-delta-detection.md), [resolve-bedrock-model-id.md](references/helpers/resolve-bedrock-model-id/resolve-bedrock-model-id.md) |
| **C2** | `llm2bedrock-log-ingestor` | `$PHASE_DIR/ingestion.json` | [scripts/schemas/ingestion.json](scripts/schemas/ingestion.json) | *(none)* |
| **C3** | `llm2bedrock-prompt-evaluator` | `$PHASE_DIR/eval.json` | [scripts/schemas/eval.json](scripts/schemas/eval.json) | [bedrock-known-fixes.md](references/helpers/bedrock-known-fixes/bedrock-known-fixes.md), [resolve-bedrock-model-id.md](references/helpers/resolve-bedrock-model-id/resolve-bedrock-model-id.md), [run-source-model-baseline.md](references/helpers/run-source-model-baseline/run-source-model-baseline.md) |
| **C4** | *(Orchestrator Sidebar Gates)* | `$PHASE_DIR/delta-decisions.json` | [scripts/schemas/delta-decisions.json](scripts/schemas/delta-decisions.json) | Gate (a) `pass_rate >= 0.9` & `source_baseline_quality != 'poor'`; Gate (a.5) `migration_path` `"mantle"` **prefix** check; Gate (b) user-visible delta choices |
| **C5** | `llm2bedrock-code-rewriter` | `$PHASE_DIR/rewrite.json` | [scripts/schemas/rewrite.json](scripts/schemas/rewrite.json) | [bedrock-known-fixes.md](references/helpers/bedrock-known-fixes/bedrock-known-fixes.md), [behavior-delta-detection.md](references/helpers/behavior-delta-detection/behavior-delta-detection.md), [dependency-conflict-resolution.md](references/helpers/dependency-conflict-resolution/dependency-conflict-resolution.md), [openai-on-bedrock.md](references/shared/openai-on-bedrock.md) |
| **C6** | `llm2bedrock-report-generator` | `MIGRATION_REPORT_<suffix>.md` | *(file existence check)* | *(none)* |
| **C7** | *(Orchestrator Summary & Undo)* | Console summary | `scripts/render_report.py` | Print `rewrite.branch_name`, report path, and exact branch-safe undo commands |

- **Stateless Fixer Retry:** On validator exit `1` or `2`, dispatch a fresh subagent to fix only the invalid/missing output file (cap **2 retries** per phase).
- **Blocked & Partial Flows:** Handle `CONTROL=blocked` (`model_access`, `model_unresolvable`, `source_key_auth`, `authz`, `mantle_deps_missing`, `assess_output_missing`) and C3 `CONTROL=partial` (`Continue remaining cases` / `Proceed with partial pass rate` / `Abort`) exactly as specified in [references/phase-b-c-execution.md](references/phase-b-c-execution.md).

---

## Access-Only Mode (`AC1`–`AC5`)

When routed from Step `0a-bis`, load and execute [references/access-only-mode.md](references/access-only-mode.md) end-to-end:

1. **AC1 — Set Expectations:** Explain commercial Marketplace auto-subscribe (`aws-marketplace:Subscribe`/`Unsubscribe`/`ViewSubscriptions`), Anthropic one-time FTU (`PutUseCaseForModelAccess`), and per-ID OpenAI routing (`gpt-oss` & CRIS `global.openai.gpt-5.6-*` on `bedrock-runtime` `bedrock:InvokeModel` vs bare `openai.gpt-5*` on `bedrock-mantle` `bedrock-mantle:*`).
2. **AC2 & AC3 — Collect Raw Models + `$REGION`, Then Confirm AWS Identity:** Do **not** resolve friendly names before `$REGION` and caller identity (`$AWS_PROFILE_CHOICE`) are confirmed.
3. **AC3.5 — Resolve Friendly Names:** Map non-ID names via [references/helpers/resolve-bedrock-model-id/resolve-bedrock-model-id.md](references/helpers/resolve-bedrock-model-id/resolve-bedrock-model-id.md) (re-resolve whenever `$REGION` or profile changes).
4. **AC4 & AC5 — Probe / Audit Entitlements, Report Distinct Verdicts & Stop:** Never conflate `embedding_unprobed` (`access unverified — no request made`), `throttled_ok` (`authorized (probe throttled)`), GovCloud 2-account enablement (linked commercial account first + GovCloud `us-gov-west-1` Model access page), and confirmed `enabled & working` (noting the ~15-min background subscription window on first-time 3P invokes). Stop after summary + Contextual Offers check.

---

## Inline Mode, Failure Handling & Contextual Offers

- **Inline Fallback:** If subagent dispatch is unavailable, execute one phase agent definition at a time, validate its JSON output, and **STOP** for user confirmation between phases (see [references/phase-b-c-execution.md](references/phase-b-c-execution.md)).
- **Contextual Offers (Mandatory Closing Step):** After final advice/report, check [references/offers.md](references/offers.md) per [references/phase-b-c-execution.md](references/phase-b-c-execution.md) — append **at most one** non-competing partner offer line with `?source=ide-startupAdvisor-<host>` (never an inference provider competing with Amazon Bedrock).
