---
name: upgrading-mwaa-environments
description: >
  Upgrades an MWAA environment to a newer Airflow version — within 2.x, within 3.x, or
  across the 2.x-to-3.x boundary. Computes the version-jump path, inserting the 2.11.x
  stepping-stone and Python-transition step when needed. Chooses an approach by
  whether run history and the same environment (URL/ARN) must be kept: a
  new-environment upgrade (blue-green), a rehearsed in-place upgrade validated on a
  test copy, or a direct in-place upgrade. Runs Ruff scanning and deprecation-warning
  log scans for 3.x moves, plus Docker validation, batched deployment, and switchover.
  Saves a resumable upgrade plan for multi-session work. Triggers on: upgrade MWAA,
  upgrade Airflow, migrate to Airflow 3, MWAA Airflow 3, Airflow 2 to 3, preserve
  Airflow history, keep same MWAA environment, blue-green cutover, validation
  environment before cutover. Not for authoring new DAGs (authoring-mwaa-workflow),
  debugging unrelated DAG failures (debugging-mwaa-workflow), or MWAA Serverless YAML
  workflows (provisioned Python DAGs only).
metadata:
  version: "1"
---

# Upgrading MWAA Environments

> **AWS MCP server (optional but recommended):** running the AWS CLI commands in
> this skill through the AWS MCP server gives sandboxed execution and audit
> logging. Every command here also works with the plain AWS CLI.

Upgrade an MWAA provisioned environment to any newer, MWAA-supported Airflow
version: within 2.x, within 3.x, or across the 2.x-to-3.x boundary. A path
planner computes an ordered version-jump list from `(source, target)`; the
latest 2.11.x stepping-stone version and a Python-line transition step are
inserted only when required. Select the deployment approach by whether
historical run data (and the same environment URL/ARN) must be preserved:
- `new-environment` — New-environment upgrade (blue-green, clean slate)
- `in-place-rehearsed` — Rehearsed in-place upgrade validated on a test copy first
- `in-place-direct` — Direct in-place upgrade (unrecommended)

> **Execution note — poll in discrete steps:** issue **one status check per
> call** and decide in your own loop whether to check again. Never block a
> single command or script with `while`+`sleep` until done.

## Guardrail — where this skill's own files live (MCP vs local install)

- **Loaded through the AWS MCP `retrieve_skill` tool:** Fetch each reference via
  `retrieve_skill` with `file` (e.g. `file="references/strategy-blue-green-fresh.md"`).
  Do NOT `file_read` these paths locally.
- **Installed locally:** Read files from the local skill directory using relative paths.

User data and session artifacts (`.mwaa-upgrade-plan-<env-name>.md`) are always
read from and written to the user's working directory.

## Safety & Security

- **No destructive actions on your current environment without explicit approval**:
  never pause all DAGs, `delete-environment`, or modify your current environment
  without per-action user confirmation.
- **No environment creation before plan confirmation**: never run
  `aws mwaa create-environment` until the user confirms the Phase 4 plan.
- **Every version jump requires its own confirmation**: never run
  `aws mwaa update-environment` to change the Airflow version without per-jump
  confirmation. Rollback options: 3.x -> 2.11.x is supported; within-major
  downgrade to a still-supported version is supported; downgrade to an EOS
  version is not possible. Direct in-place upgrade requires an extra
  confirmation checkpoint.
- **Decommission requires per-step approval**: present each destructive command
  and wait for confirmation. For `in-place-rehearsed`, decommission the test copy
  (never delete the current environment).
- **Least-privilege IAM & Secrets**: scope IAM to specific environment/S3 ARNs
  (no `*FullAccess`/`service:*`). Prefer Secrets Manager or Parameter Store for
  connections/variables; connection passwords do not round-trip via REST API
  (2.x omits, 3.x masks).

## Reference Documentation

- [discovery-preflight.md](references/discovery-preflight.md) — Phase 1: environment discovery, pre-flight checks, version-matrix refresh, target selection, upgrade-path planning
- [plan-materialization.md](references/plan-materialization.md) — Plan format contract, checklist invariants, status vocabulary (`LOADED` vs `VERIFIED`), and resumable state tracking
- [upgrade-engine.md](references/upgrade-engine.md) — Step-by-step per-jump upgrade, conditional validate/scan/fix, and resume logic
- [airflow2-to-3-checklist.md](references/airflow2-to-3-checklist.md) — Grep patterns for 2->3 issues Ruff cannot catch (used when `crosses_major` is true)
- [mwaa-version-matrix.md](references/mwaa-version-matrix.md) — Runtime-first version/Python/EOS matrix, version-jump rules, providers, unsupported features
- [airflow2-to-3-quick-reference.md](references/airflow2-to-3-quick-reference.md) — 2->3 import/context/config mapping tables
- [strategy-blue-green-fresh.md](references/strategy-blue-green-fresh.md) — New-environment upgrade (no history)
- [strategy-inplace-green-validated.md](references/strategy-inplace-green-validated.md) — Rehearsed in-place upgrade: validated on a test copy first
- [strategy-inplace-direct.md](references/strategy-inplace-direct.md) — Direct in-place upgrade (unrecommended)

External AWS documentation:
- MWAA migration guide: https://docs.aws.amazon.com/mwaa/latest/migrationguide/key-considerations.html
- MWAA in-place upgrade path: https://docs.aws.amazon.com/mwaa/latest/userguide/upgrading-environment.html
- MWAA supported versions & Python mapping: https://docs.aws.amazon.com/mwaa/latest/userguide/airflow-versions.html
- Ruff AIR rules: https://docs.astral.sh/ruff/rules/#airflow-air

## Phase 0: Re-entry Check

Check for `.mwaa-upgrade-plan-<env-name>.md` in the workspace root:

- **If exists**: Re-read the entire plan file verbatim before taking any action
  (never rely on a remembered summary). Run **Plan Reconciliation** against the
  self-consistency invariants in [plan-materialization.md](references/plan-materialization.md):
  - Any `PASSED` checkpoint requires all prerequisite Checklist items `DONE`/`SKIP`.
  - `Where we are.test_run_checkpoint` must match the `## Test-run results` table
    (any row not in `SUCCESS` or `NEEDS-DECISION` means `NOT-PASSED` and blocks
    switchover, `live_upgrade_allowed`, or completion regardless of
    `has_import_errors: false`).
  - `current_jump`/`jump_status` must match the Upgrade Path Status.
  - On any violation, establish ground truth with read-only
    `aws mwaa get-environment`, `/dags`, and `/health`, repair the plan, and
    update `Last updated`.
  Resume [upgrade-engine.md](references/upgrade-engine.md) at `(working_on, current_jump, jump_status)`.
- **If absent**: Proceed to Phase 1.

## Phase 1: Discover + Plan Path + Pre-flight

Follow [references/discovery-preflight.md](references/discovery-preflight.md) to run
environment discovery, pre-flight safety checks, version-matrix refresh, target
selection, and upgrade-path planning (detection only — version jumps execute in
Phase 7). Record:
- Discovered environment facts (Airflow version, S3 artifact paths + object
  versions, KmsKey, config options, DAG list, shared utilities)
- New-environment / test-copy S3 layout (`new-environment`, `in-place-rehearsed`)
- Pre-flight results (S3 versioning, target constraints, KMS key-policy reuse)
- Selected target version and ordered upgrade path (`from`/`to`/`python_change`/`crosses_major`,
  inserting the latest 2.11.x stepping-stone + Python-transition step only when
  needed)

## Phase 2: Choose the Upgrade Approach

Ask one deciding question: **Do you need to keep your run history** (past DAG runs
and task instances in the Airflow UI)?

- **No, a clean slate is fine** → **New-environment upgrade** (`new-environment`):
  Build a brand-new environment on the target version with a new URL/ARN and switch
  over to it. Your current environment runs untouched until switchover.
- **Yes, keep it** → **Rehearsed in-place upgrade** (`in-place-rehearsed`):
  Keep the same URL/ARN and full history by rehearsing the upgrade on a temporary
  test copy first, then upgrading the current environment in place. Use
  **Direct in-place upgrade** (`in-place-direct`) only if the user explicitly
  declines rehearsal.

| Approach | History | URL/ARN | Current environment during upgrade | New/test environment created at | Recommended |
|---|---|---|---|---|---|
| New-environment upgrade (`new-environment`) | Discarded | New | Runs until switchover | First version jump's target | Yes |
| Rehearsed in-place upgrade (`in-place-rehearsed`) | Preserved (snapshot) | Same | Rehearsed on test copy, then upgraded | First version jump's target | Yes |
| Direct in-place upgrade (`in-place-direct`) | Preserved (snapshot) | Same | Upgraded directly | None | No |

**Guardrail**: If the user picks `in-place-rehearsed` or `in-place-direct` and
the environment has >50 DAGs or complex DAGs in Phase 3, warn and recommend
`new-environment` instead (do not block).

## Phase 3: Assess Compatibility

1. **Compatibility scan (required checkpoint when any jump is `crosses_major`):**
   ```
   ruff check --preview --select AIR .
   ```
   Report findings grouped by rule code (`AIR301/302/303/311/312`, `AIR321`).
   - **Version-aware severity for `AIR311` (`airflow.sdk` import moves):**
     - **Target 3.0.x or 3.1.x:** soft deprecation (compatibility shims exist).
     - **Target 3.2.1+:** hard blocker (`ModuleNotFoundError` at parse time; shims
       removed). Must fix before deploying to target (note: `from airflow.sdk import ...`
       is AF3-only and deploys after the cross-major jump completes).
2. **Manual scan ([airflow2-to-3-checklist.md](references/airflow2-to-3-checklist.md)):**
   Always run even when Ruff reports zero findings (catches `_TaskDecorator.output`
   in section 15 and Airflow CLI in `BashOperator` in section 16).
   - **Surface metadata-DB warning (`crosses_major` only):**
     - **ORM-access DAGs** (`settings.Session()`, `provide_session` — section 1):
       redesign to REST API or drop.
     - **CLI-access DAGs** (`airflow db ...` in `BashOperator` — section 16):
       redesign to MWAA CLI endpoint (verify via `cheat-sheet`) or REST API or drop.
3. **Requirements check**: Validate `requirements.txt` against target version
   constraints in [mwaa-version-matrix.md](references/mwaa-version-matrix.md).
4. **Secrets backend detection**: Check `secrets.backend` override. If using
   Secrets Manager or Parameter Store, variables/connections are external. **If NO
   secrets backend is configured, warn at plan time:** connection passwords will
   NOT migrate via REST API (2.x omits, 3.x masks) and must be moved to a secrets
   backend or re-entered out of band.
5. **Plugin inventory & DAG batching**: Inspect `PluginsS3Path` (flag FAB/web-view
   plugins), classify DAGs (Simple, Moderate, Complex), and group into batches
   (shared utilities in batch 0, simple first).

## Phase 4: Generate Upgrade Plan

Write `.mwaa-upgrade-plan-<env-name>.md` to workspace root following
[plan-materialization.md](references/plan-materialization.md) in full before
presenting the plan to the user:
- Environment details (source name, source version, region, target version) and
  chosen approach slug (`new-environment` / `in-place-rehearsed` / `in-place-direct`)
- Pre-flight results, Docker validation status (`pending`), secrets backend
  detection, requirements changes, and (`crosses_major` only) metadata-DB findings
  + PENDING post-fix re-scan checkpoint
- Approach-specific S3/environment fields and per-DAG batch table
- `## Upgrade Path` table (`Jump | From → To | Python change | New major version | Status`;
  for `in-place-rehearsed`, separate `Test copy status` and `Your current environment status`
  columns with current-environment jumps marked `IRREVERSIBLE`)
- All mandatory sections from [plan-materialization.md](references/plan-materialization.md):
  `## Checklist`, discrete `PENDING` checkpoints, pre-seeded `## Test-run results`
  and `## Switchover progress` tables, `## Where we are` block, and `LOADED` vs
  `VERIFIED` vocabulary (`has_import_errors: false` is `LOADED`, never `VERIFIED`).

Present the plan to the user for confirmation before proceeding.

## Phase 5: Fix Code

1. **Batch 0 (shared utilities):** Fix shared modules first using
   [airflow2-to-3-quick-reference.md](references/airflow2-to-3-quick-reference.md).
2. **Per batch (1..N):**
   a. Run `ruff check --preview --select AIR --fix --unsafe-fixes <files>`
   b. Fix remaining issues using [airflow2-to-3-quick-reference.md](references/airflow2-to-3-quick-reference.md).
   c. Re-run Ruff to verify zero AIR violations.
   d. **Re-scan FIXED files (`crosses_major` only)** with checklist section 15/16
      greps (`--unsafe-fixes` can rewrite `xcom_pull` into AF3-invalid `<task>.output`).
   e. Save progress to the plan (`DONE` + `Last updated`).

## Phase 6: Local Validation via Docker (Strongly Recommended for Cross-Major)

Uses `aws/amazon-mwaa-docker-images` (available for Airflow 2.9.2+). If target < 2.9.2,
Docker is unavailable, or user declines, log `SKIP` with reason (and warn of
undetected runtime errors when `crosses_major`) and proceed to Phase 7.
1. Check `docker --version` and pull the target-version image.
2. Validate `requirements.txt`, `plugins.zip` (if present), and DAG imports inside
   the container; loop back to Phase 5 on import errors.
3. Mark Docker validation `DONE` or `SKIP` in the plan and update `Last updated`.

## Phase 7: Deploy

Dispatch to the approach-specific reference and execute
[upgrade-engine.md](references/upgrade-engine.md), saving progress to the plan
after every step, sub-step, version jump, checkpoint, and batch:
- **New-environment upgrade**: [strategy-blue-green-fresh.md](references/strategy-blue-green-fresh.md)
- **Rehearsed in-place upgrade**: [strategy-inplace-green-validated.md](references/strategy-inplace-green-validated.md)
- **Direct in-place upgrade**: [strategy-inplace-direct.md](references/strategy-inplace-direct.md)

**DAG test-run validation (REQUIRED checkpoint for every approach):** After parse
validation passes, invoke **skill** `testing-mwaa-workflow` for each DAG/batch
to confirm execution succeeds at the target version, and invoke **skill**
`debugging-mwaa-workflow` on failure. Do NOT trigger DAG runs manually via
`POST /dags/{id}/dagRuns` or poll states inline. Record results in
`## Test-run results`. Do NOT proceed to live upgrade (`in-place-rehearsed`),
switchover (`new-environment`), or completion (`in-place-direct`) until test-run
validation passes.

## Phase 8: Switchover + Decommission

Applies to `new-environment` (switch over then decommission current environment)
and `in-place-rehearsed` (skip switchover; decommission the TEST COPY only).
`in-place-direct` completes at Phase 7.

1. **Batched switchover (`new-environment` only; explicit approval per batch):**
   a. Pause batch DAGs on current environment (use backoff; `invoke-rest-api` has
      10s timeout / 6 MB cap and 64-char `--path` limit — use CLI token fallback
      for over-length `dag_id`):
      ```
      aws mwaa invoke-rest-api --name <current-env> --method PATCH \
        --path /dags/<dag_id> --body '{"is_paused":true}'
      sleep 0.2
      ```
   b. Drain in-flight runs (`state=running`). If still running after 10 minutes
      only on `deferred` or `sensing` tasks, proceed with unpausing on the new
      environment.
   c. Unpause the same DAGs on the new environment (`{"is_paused":false}`, `sleep 0.2`).
   d. Monitor the batch for one full schedule cycle before advancing (rollback on
      failure). Offer all-at-once switchover for small environments (<10 DAGs or
      all-simple).
2. **Stability period**: Recommend 24h or one full cycle of the longest-interval
   DAG, monitoring CloudWatch Scheduler heartbeat and Oldest queued task age.
3. **Decommission (explicit approval per step):**
   - `new-environment`: `aws mwaa delete-environment --name <current-env>` (or
     keep paused read-only for historical UI access).
   - `in-place-rehearsed`: `aws mwaa delete-environment --name <test-copy>`.
4. Mark upgrade `DONE`, set `Where we are` `phase: complete`, and update `Last updated`.
