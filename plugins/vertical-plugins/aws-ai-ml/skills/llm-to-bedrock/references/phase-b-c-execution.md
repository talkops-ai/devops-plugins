# Phase B & Phase C Execution Reference (`llm-to-bedrock`)

Complete execution specifications, subagent dispatch prompt templates, JSON state schemas, scoped invalidation rules, inline fallback mode, failure handling, and contextual offers protocol for `llm-to-bedrock`.

> **MCP-Only & Read-Only Safety Note:** During read-only architecture reviews or evaluations, perform all live AWS identity, model catalog, inference-profile, quota, and pricing checks **exclusively via connected MCP tools** (`aws-mcp` `aws___run_script` using read-only `await call_boto3(...)`, `awspricing`, `awsknowledge`) — never execute raw `aws ...` CLI commands in shell, never invoke billable/mutating operations (`InvokeModel`, `Converse`, `Create*`, `Delete*`) without explicit approval outside read-only mode, and never print or expose plaintext API keys.

---

## Phase B — Execute Prep (Detailed Procedures)

### B1 — Read Assess outputs

Read `$MIGRATION_DIR/aws-design-ai.json` and extract:
- `ai_architecture.bedrock_models[]` → array of `{source_model, aws_model_id, use_case}`
- Collect all `aws_model_id` values into `$TARGET_MODELS` (array). Keep the `use_case` of each: the preflight script probes each model by the right API automatically (Converse for chat, InvokeModel for embeddings), while the evaluator's quality scoring applies only to chat models (embedding targets receive format/dimension validation only).

Read `$MIGRATION_DIR/ai-workload-profile.json` and extract:
- `summary.ai_source` → source provider

Read `$MIGRATION_DIR/preferences.json` and extract:
- `design_constraints.target_region` → `$REGION` (default `us-east-1` if absent)

**Validation:** If `aws-design-ai.json` has no `ai_architecture.bedrock_models[]` array, or the array is empty, STOP: `"Assess output incomplete — model mapping missing."`

### B2 — AWS identity confirmation

Verify caller identity via `aws-mcp` (`aws___run_script` calling `sts` `GetCallerIdentity`).
- **If credentials fail** (no credentials, expired SSO token): show the error and instruct the user to run `aws configure` or `aws sso login` in their terminal, then re-run B2. Do not proceed without a confirmed identity.
- **On success**, show `Account`, `Arn`, and `UserId` via **AskUserQuestion**: `"This AWS identity will be used for Bedrock calls. Is this correct?"`
  - **Yes, use this identity** → proceed.
  - **Use a different AWS profile** → ask which profile, record it as `$AWS_PROFILE_CHOICE`, re-verify identity for `$AWS_PROFILE_CHOICE`, and re-confirm. **Do NOT rely on exporting `AWS_PROFILE`** — env vars do not persist across Bash tool calls or into workflow subagents. Pass the choice explicitly everywhere (`AWS_PROFILE=$AWS_PROFILE_CHOICE` inline on preflight/subagent dispatches and `awsProfile` in context).
- Confirm region: `"Bedrock region will be $REGION. OK or override?"`

### B3 — Source API key (optional, zero-transcript exposure)

First, create the artifact directory and make it self-ignoring **immediately** before any key file exists:

```bash
mkdir -p "$REPO/.saws-migrate" && printf '*\n' > "$REPO/.saws-migrate/.gitignore"
```

Determine `$KEY_ENV_VAR` from B1's source provider (the baseline parser requires the `NAME=` prefix):
- `openai` → `OPENAI_API_KEY`
- `anthropic` → `ANTHROPIC_API_KEY`
- `google` / `gemini` → `GEMINI_API_KEY`

**HARD RULE — The key must never enter this conversation.** Never ask the user to paste a key in chat, and never echo, `cat`, read `.env`, or interpolate secret values into any command, question, or output. If the user pastes a key unprompted, refuse to use it, warn that it is in the transcript, recommend rotating it immediately, and proceed via one of the safe paths below.

Check presence only (POSIX-safe across bash/zsh; prints presence flag only, never the value):

```bash
[ -n "$(printenv "$KEY_ENV_VAR")" ] && echo ENV_KEY_PRESENT || echo ENV_KEY_ABSENT
```

**AskUserQuestion:** `"Do you have an API key for the source model (e.g. OpenAI key for GPT-4o)? Providing it enables side-by-side quality comparison. Without it, evaluation uses absolute scoring only."`

Options (offer the first only on `ENV_KEY_PRESENT`):
- **Use the `$KEY_ENV_VAR` already in my environment** → materialize env var to file without echoing:
  ```bash
  printf '%s=%s\n' "$KEY_ENV_VAR" "$(printenv "$KEY_ENV_VAR")" > "$REPO/.saws-migrate/.source-provider-env" && chmod 600 "$REPO/.saws-migrate/.source-provider-env"
  ```
  Run the format check below and set `sourceBaselineAvailable = true`, `sourceKeyRef = "$REPO/.saws-migrate/.source-provider-env"`.
- **I'll write it to a file myself** → give the user this command to run in **their own terminal** (`read -rs` reads silently):
  ```bash
  read -rs k && printf '%s=%s\n' "<KEY_ENV_VAR>" "$k" > "<REPO>/.saws-migrate/.source-provider-env" && chmod 600 "<REPO>/.saws-migrate/.source-provider-env" && unset k
  ```
  Run the format check below and set the same flags.
- **Skip** → `sourceBaselineAvailable = false`, `sourceKeyRef = ""`.

Format verification (never prints the key):

```bash
grep -qE '^(OPENAI|ANTHROPIC|GEMINI)_API_KEY=.+' "$REPO/.saws-migrate/.source-provider-env" && echo KEY_FORMAT_OK || echo KEY_FORMAT_BAD
```

On `KEY_FORMAT_BAD`, have the same path rewrite it with the `NAME=` prefix without echoing contents.

### B4 — Bedrock preflight (when approved for active migration execution)

*(Skip live model invocation in strictly read-only audit mode; inspect foundation models and inference profiles read-only via `aws-mcp` instead.)*

```bash
uv run --project $SCRIPTS python $SCRIPTS/preflight_bedrock.py --region $REGION --models <comma-separated $TARGET_MODELS> --dataset-size 200
```

(`--dataset-size 200` matches the golden-dataset cap; prepend `AWS_PROFILE=$AWS_PROFILE_CHOICE` if non-default.)

Parse JSON output (`reason`/`detail` + `failing_models` at top level; per-model verdicts in `models[]`):
- `ok == false` + `reason: credentials` → surface `detail` (configure/refresh credentials), stop.
- `ok == false` + `reason: model_access` → model access not enabled in Bedrock console (not IAM); point user to Model access page for `failing_models`, stop.
- `ok == false` + `reason: authz` → IAM denies inference (`bedrock:InvokeModel` for Converse/InvokeModel targets, or `bedrock-mantle:*` for mantle-only `openai.gpt-5*` targets per `detail`). Name exact action to grant; stop.
- `ok == false` + `reason: mantle_deps_missing` → pinned scripts env lacks `openai` / `aws-bedrock-token-generator`; instruct `uv sync --project $SCRIPTS` and stop (never treat unprobed access as verified).
- `ok == false` + `reason: model_unavailable` → follow `$HELPERS/resolve-bedrock-model-id/resolve-bedrock-model-id.md` for each ID in `failing_models` + `$REGION`. Offer `"Use <candidate> (cross-region inference profile)"` / `"Paste a different model ID"` / `"Abort"`; update `$TARGET_MODELS` and re-run B4.
- `ok == false` + any other `reason` → show `detail` and stop.
- `ok == true` → proceed; surface any `quota_warning` and any `embedding_unprobed` model (remind user to verify console access manually).

---

## Phase C — Execute (Subagent Orchestration, Schemas & Gates)

Phase C dispatches five sequential subagents (`aws-startup-advisor:llm2bedrock-code-analyzer`, `aws-startup-advisor:llm2bedrock-log-ingestor`, `aws-startup-advisor:llm2bedrock-prompt-evaluator`, `aws-startup-advisor:llm2bedrock-code-rewriter`, `aws-startup-advisor:llm2bedrock-report-generator`), persisting results under `$PHASE_DIR = $REPO/.saws-migrate/phase-results/`.

### Validator Contract (run after every step)

```bash
uv run --project $SCRIPTS python $SCRIPTS/validate_result.py --schema <analysis|ingestion|eval|rewrite|delta-decisions> <file>
```

- Exit `0` + `RESULT=valid CONTROL=ok` → phase completed; proceed.
- Exit `0` + `CONTROL=blocked REASON=<r>` → enter **Blocked flow** below.
- Exit `0` + `CONTROL=partial COMPLETED=<n> TOTAL=<m>` → enter **Partial flow** below (`eval` only).
- Exit `1` (`RESULT=invalid`) or exit `2` (file missing) → **Stateless fixer retry**: dispatch a fresh subagent of the same type with original context block + output file path + verbatim validator errors + `"fix ONLY the output file at <path> so it validates; do not redo the phase's work unless a required field is genuinely missing from it"`. Cap at **2 retries** per phase, then stop and surface errors.

### Subagent Context Block Template (instantiated per dispatch)

Use exact label names (omit optional lines when empty; pass prior phase results as **file paths**, never inline JSON):

```text
Repository: <$REPO>
AWS region: <$REGION>
AWS profile (pass as --profile / AWS_PROFILE= inline on every aws/boto3 invocation): <$AWS_PROFILE_CHOICE — omit line if default>
Target Bedrock model(s): <comma-joined $TARGET_MODELS, with any resolved overrides already applied>
Migration plan dir: <$MIGRATION_DIR>
Resolved target model id: <override for the primary chat model — omit if none>
Scripts directory (pinned uv toolchain): <$SCRIPTS>
Report date suffix: <saved suffix from run-context — C5/C6 dispatches only>
Source baseline available: <true|false>
Source provider env file: <path — omit if none>
User-supplied log files: <comma-joined — omit if none>
Golden dataset cap (max cases the ingestor may emit): 200
Phase results directory: <$PHASE_DIR>
Prior phase results (Read these files): <paths of already-validated phase JSONs>
Confirmed behavior-delta decisions file (Read it): <$PHASE_DIR/delta-decisions.json — C5 only>
<helper-reference lines — inject ONLY the ones this agent needs, expanded to absolute paths>
```

#### Helper-Reference Injection Table (expand `$HELPERS` to absolute path)

| Step & Subagent | Helper-reference lines to append |
|---|---|
| **C1** `llm2bedrock-code-analyzer` | `behavior-delta-detection reference: <ABS_HELPERS>/behavior-delta-detection/behavior-delta-detection.md`<br>`resolve-bedrock-model-id reference: <ABS_HELPERS>/resolve-bedrock-model-id/resolve-bedrock-model-id.md` |
| **C2** `llm2bedrock-log-ingestor` | *(none)* |
| **C3** `llm2bedrock-prompt-evaluator` | `bedrock-known-fixes reference: <ABS_HELPERS>/bedrock-known-fixes/bedrock-known-fixes.md`<br>`resolve-bedrock-model-id reference: <ABS_HELPERS>/resolve-bedrock-model-id/resolve-bedrock-model-id.md`<br>`run-source-model-baseline reference: <ABS_HELPERS>/run-source-model-baseline/run-source-model-baseline.md` |
| **C5** `llm2bedrock-code-rewriter` | `bedrock-known-fixes reference: <ABS_HELPERS>/bedrock-known-fixes/bedrock-known-fixes.md`<br>`behavior-delta-detection reference: <ABS_HELPERS>/behavior-delta-detection/behavior-delta-detection.md`<br>`dependency-conflict-resolution reference: <ABS_HELPERS>/dependency-conflict-resolution/dependency-conflict-resolution.md` |
| **C6** `llm2bedrock-report-generator` | *(none)* |

### C0 — Run-Context Gate & Scoped Resume Invalidation

Warn the user upfront that C3 Evaluation makes up to 200 paid Bedrock calls (plus up to 200 paid source-provider calls if a source key was provided).

1. `mkdir -p "$PHASE_DIR"` and build `$PHASE_DIR/current-context.json` (hashes via `shasum -a 256`; never store plaintext keys):

```json
{
  "repo_root": "<cd $REPO && pwd -P>",
  "migration_dir": "<$MIGRATION_DIR>",
  "region": "<$REGION>",
  "aws_profile": "<$AWS_PROFILE_CHOICE or \"\">",
  "aws_account": "<Account from B2>",
  "repo_head_sha": "<git -C $REPO rev-parse HEAD>",
  "repo_branch": "<git -C $REPO rev-parse --abbrev-ref HEAD>",
  "repo_dirty_sha256": "<sha256 of git status --porcelain + git diff + git diff --cached excluding .saws-migrate, .migration, MIGRATION_REPORT_*.md; \"\" when empty>",
  "target_models": [{"source_model": "...", "aws_model_id": "...", "use_case": "..."}],
  "resolved_model_overrides": {},
  "source_provider": "<from B1>",
  "source_baseline_available": true,
  "source_key_sha256": "<sha256 of .source-provider-env contents, \"\" when absent>",
  "log_files": [{"path": "...", "sha256": "..."}],
  "max_golden_cases": 200,
  "assess_design_sha256": "<sha256 of $MIGRATION_DIR/aws-design-ai.json>",
  "report_date_suffix": "<date +%Y-%m-%d>",
  "schema_version": 1,
  "plugin_version": "<version from plugin.json>"
}
```

2. **Stage 0 (post-C5 normalization):** If `$PHASE_DIR/rewrite.json` exists with `CONTROL=ok`, check:
   - (1) `rewrite.baseline_parent_sha == saved repo_head_sha`
   - (2) `git rev-parse <rewrite.branch_name> == rewrite.branch_tip_sha`
   - (3) `git status --porcelain` (with artifact exclusions) is empty.
   - All pass → copy saved `repo_*` values into `current-context.json` verbatim. Check 2 fails → ask `"Keep your commits (regenerate report only, with mixed-authorship note)"` / `"Reset branch to rewriter tip and regenerate from C6"` / `"Abort"`. Check 3 fails → ask user to commit/stash or discard edits. Check 1 fails → treat as full `repo_*` mismatch.

3. **Compare saved `run-context.json` (if present):**
   ```bash
   uv run --project $SCRIPTS python $SCRIPTS/validate_result.py --check-run-context $PHASE_DIR/run-context.json --current $PHASE_DIR/current-context.json
   ```
   - `RUN_CONTEXT=match` → walk `C1 → C2 → C3 → C4 (delta-decisions.json) → C5 → C6 (MIGRATION_REPORT_<saved suffix>.md)`; stop at first missing/invalid/control-state file (archive any files after an unexplained gap) and offer to skip completed phases.
   - `RUN_CONTEXT=mismatch` → archive invalidated units to sibling `$REPO/.saws-migrate/phase-results-archive/<saved suffix>-$(date +%H%M%S)/` (never nested inside `phase-results/`), overwrite `run-context.json` with `current-context.json` (preserving `report_date_suffix` unless `REPORT` is invalidated), and re-run from earliest invalidated phase:

| Mismatched field(s) | Archive (units) | Keep |
|---|---|---|
| `repo_root`, `migration_dir`, `region`, `aws_profile`, `aws_account`, `source_provider`, `assess_design_sha256`, `schema_version`, `plugin_version` | everything | — |
| `repo_head_sha` / `repo_branch` / `repo_dirty_sha256` | everything | — |
| `target_models` / `resolved_model_overrides` | `ANALYSIS`, `EVAL`, `REWRITE`, `REPORT` | `INGESTION` |
| `log_files` / `max_golden_cases` | everything | — |
| `source_key_sha256` / `source_baseline_available` | `ANALYSIS`, `EVAL`, `REWRITE`, `REPORT` | `INGESTION` |

*(Units: `ANALYSIS` = `analysis.json`; `INGESTION` = `ingestion.json` + `.saws-migrate/golden-dataset/`; `EVAL` = `eval.json` + `.saws-migrate/eval-results/` minus `cost_compare.py`; `REWRITE` = `rewrite.json` + `delta-decisions.json`; `REPORT` = `MIGRATION_REPORT_<saved suffix>.md`. If `rewrite.json` was valid and `ANALYSIS`/`INGESTION`/`EVAL` are invalidated, confirm with user before checking out `<saved repo_branch>` and deleting `<rewrite.branch_name>` + tag `saws-migrate-baseline`.)*

4. **Fresh run (no saved `run-context.json`):** copy `current-context.json` to `run-context.json` and dispatch C1.

### C1 — Analyzer · C2 — Ingestor · C3 — Evaluator

- **Blocked flow (`CONTROL=blocked`):**
  - `model_access`: user enables model in Bedrock console → re-dispatch blocked phase.
  - `model_unresolvable`: user chooses/pastes ID → record in `resolved_model_overrides` and update Target line.
  - `source_key_auth`: re-run B3 or set `source_baseline_available = false`.
  - `authz`: grant `bedrock:InvokeModel*` (Converse) or `bedrock-mantle:*` (`CreateInference`, `CallWithBearerToken` for `openai.gpt-5*`) per `detail` (never confuse IAM denial with console `model_access`) → re-dispatch blocked phase.
  - `mantle_deps_missing`: `uv sync --project $SCRIPTS` → re-dispatch blocked phase.
  - `assess_output_missing`: re-run Phase A, restart at C0.
  - After any resolution, re-run C0 invalidation recipe and resume from earliest invalidated phase.
- **Partial flow (`CONTROL=partial`, C3 only):** AskUserQuestion:
  - **Continue remaining cases:** re-dispatch C3 with `"Resume: raw_results.jsonl already contains completed cases — evaluate only prompts whose ids are not present in it, then re-score and overwrite eval.json"`.
  - **Proceed with partial pass rate:** re-dispatch C3 with `"Finalize partial: do NOT call Bedrock again — score the cases already in raw_results.jsonl and emit the FULL eval payload over only those cases, with total_cases = the number scored and a notes prefix line 'partial_coverage: <completed>/<total> cases (throttled)'"`, then proceed to C4.
  - **Abort:** stop cleanly; artifacts remain resumable at C0.

### C4 — Sidebar Gates & `delta-decisions.json`

1. **Gate (a) — Quality go/no-go:** Check `$PHASE_DIR/eval.json`. Threshold: `pass_rate >= 0.9` **AND** `source_baseline_quality != 'poor'` (if `no_golden_cases: true`, always ask). Below threshold → AskUserQuestion: **Proceed anyway** / **Change target model** (updates `resolved_model_overrides`, re-runs C0 from C1, max 2 retries) / **Abort**.
2. **Gate (a.5) — Rewrite strategy (`mantle` prefix check):** Read `$MIGRATION_DIR/aws-design-ai.json` → `ai_architecture.code_migration.migration_path`. If it **starts with `"mantle"`** (`"mantle"`, `"mantle_openai_responses"`), set `rewrite_strategy = "mantle"`; otherwise (`"converse"`, `"gpt-oss"`, or absent) set `rewrite_strategy = "converse"`. Always match prefix (not exact equality) so `"mantle_openai_responses"` is never misrouted to Converse.
3. **Gate (b) — Behavior-delta resolution:** For each `analysis.behavior_deltas[]` where `user_visible == true`, prompt user with options from `$HELPERS/behavior-delta-detection/behavior-delta-detection.md` (+ provider sub-reference). Write `{delta_type, location, resolution_chosen, source}` array (`[]` if none) to `$PHASE_DIR/delta-decisions.json` and validate with `--schema delta-decisions`.

### C5 — Rewriter · C6 — Report · C7 — Render Summary

- For **C5** (`llm2bedrock-code-rewriter` → `$PHASE_DIR/rewrite.json`), include `Confirmed behavior-delta decisions file` and saved `Report date suffix`. When `rewrite_strategy == "mantle"`, also append:
  - `Rewrite strategy: mantle`
  - `Mantle model map: <source-model> -> <bedrock-model-id>`
  - `Mantle surface: responses` and `Mantle base path: /openai/v1` whenever any mapped `aws_model_id` matches `openai.gpt-5*` (proprietary GPT models use `/openai/v1` Responses API — see [references/shared/openai-on-bedrock.md](shared/openai-on-bedrock.md))
  - `Same model: true` when `bedrock_models[].model_change == false`.
- For **C6** (`llm2bedrock-report-generator` → `$REPO/MIGRATION_REPORT_<saved suffix>.md`), pass all 4 validated phase JSON paths.
- **C7 — Render summary & safe undo instructions:**
  ```bash
  uv run --project $SCRIPTS python $SCRIPTS/render_report.py --phase-results $PHASE_DIR --repo $REPO --date-suffix <saved suffix>
  ```
  Always substitute the **actual** `rewrite.branch_name` (never hardcode `bedrock-migration` in case of collision suffix `bedrock-migration-2`):
  > To discard: `git checkout <original-branch>`, `git branch -D <rewrite.branch_name>`, `git tag -d saws-migrate-baseline`, and `rm -rf .saws-migrate .migration`.

---

## Inline Mode, Failure Handling & Contextual Offers

- **Inline Mode (when platform lacks subagent dispatch):** Read and execute **one** agent definition (`<plugin>/agents/<name>.md`) at a time, write + validate its phase JSON, and **STOP** to report the validator `CONTROL` line and ask user confirmation before loading the next phase definition. Warn upfront about context weight and in-session git branch/commit mutations during C5.
- **Failure Handling:** Missing output file (validator exit 2) triggers stateless fixer retry (max 2 retries). User abort before C5 leaves source code untouched (share C7 artifact cleanup commands).
- **Contextual Offers (mandatory closing check):** After final output, check [references/offers.md](offers.md). Surface **at most one** offer (never a list, max 1 per 5 messages / 2 per session, skip if muted) **only** if it is a credit on a partner tool kept/selected by the migration (e.g., LangSmith when LangChain remains) — **never** an offer competing with Amazon Bedrock. Append `?source=ide-startupAdvisor-<host>` (`claude` | `vscode` | `cursor` | `kiro` | `codex`, or `ide-startupAdvisor`):
  ```markdown
  ***<Offer>** has an exclusive offer via AWS Activate — <value>, <eligibility>. [Redeem →](<source_url>?source=ide-startupAdvisor-<host>)*
  ```
