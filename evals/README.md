# Skill Evaluations (`evals/`)

Open-source evaluation suites, JSON schemas, and multi-harness execution runner for all **446 canonical skills** across the 49 plugins in `devops-plugins`.

> **Why top-level `evals/` instead of `plugins/**/skills/*/evals/`?**
> Because `devops-plugins` is an installable multi-plugin marketplace where 200+ canonical skills are shared across specialist **agent plugins** and **vertical plugins**, keeping evaluation suites in `evals/skills/<skill-name>/` ensures:
> 1. **Zero install bloat (`0 KB` overhead)** when users run `claude plugin install` or `codex plugin install`.
> 2. **Single source of truth** per canonical skill — no duplicated `evals.json` files across shared plugins.
> 3. **Clean runtime isolation** — ephemeral execution sandboxes are staged into `.eval-runs/` (gitignored), never inside `plugins/` or `evals/`.

---

## Directory Layout

```text
evals/
├── README.md                          # This guide
├── schemas/
│   ├── execution_evals.schema.json    # Layer 3 functional & outcome eval schema
│   └── trigger_evals.schema.json      # Layer 2 4-quadrant trigger routing schema
└── skills/
    └── <skill-name>/                  # 1 canonical folder per skill (446 total)
        ├── evals.json                 # Functional prompts, expectations & optional deterministic assertions
        ├── trigger_evals.json         # Explicit, implicit, contextual & near-miss negative routing queries
        └── files/                     # Optional input fixtures staged into the isolated workspace
```

All runtime artifacts (`workspace/`, `trace.jsonl`, `normalized_trace.json`, `grading.json`, `benchmark.json`, `trigger_report.json`) are written to **`.eval-runs/<skill-name>/iteration-<N>/`** (override with `DEVOPS_PLUGINS_EVAL_RUNS_DIR=/tmp/eval-runs`).

---

## Three-Layer Evaluation Pipeline

All checks are driven by [`scripts/eval_skills.py`](../scripts/eval_skills.py):

### Layer 1: Static Spec, Reference, Script & Open-Source Hygiene Audit (`static`)

Validates `SKILL.md` frontmatter, shared-skill parity across plugins, local `references/` / `scripts/` / `assets/` link integrity, Python script syntax & `--help` execution, JSON schema conformance of `evals.json` & `trigger_evals.json`, and open-source hygiene (no co-located `plugins/**/evals/`, no personal `/Users/...` paths, and no non-placeholder 12-digit AWS Account IDs):

```bash
# Audit all 446 canonical skills and 49 plugins
python3 scripts/eval_skills.py static

# Audit a single skill
python3 scripts/eval_skills.py static --skill amazon-aurora-postgresql
```

### Layer 2: 4-Quadrant Trigger & Sibling Collision Evaluation (`trigger`)

Mounts the target skill alongside its `companion_skills` to verify activation precision and recall across four quadrants (`explicit`, `implicit`, `contextual`, and `near_miss_negative`):

```bash
# Dry-run validate trigger queries
python3 scripts/eval_skills.py trigger --skill eks-karpenter-autoscaling --dry-run

# Execute trigger evaluation (supports --harness agy|claude|codex)
python3 scripts/eval_skills.py trigger --skill eks-karpenter-autoscaling --harness claude --workers 3
```

### Layer 3: End-to-End Execution, Hook & MCP Telemetry Grading (`run`)

Provisions a clean workspace in `.eval-runs/` with the owning plugin's `SKILL.md`, `references/`, `scripts/`, `.mcp.json` / `mcp.json`, slash commands, and safety hooks (`secret-safety.py` + `aws-mutation-gate.py` in read-only mode), executes each prompt, and grades both **Observed Execution Telemetry** (skills invoked, MCP tools called, files read, hooks triggered) and the **Final Response** against `expectations` (LLM judge) and optional deterministic `assertions` (`contains`, `not contains`, `matches regex`):

```bash
# Dry-run validate execution cases
python3 scripts/eval_skills.py run --skill deploying-helm-charts --dry-run

# Run full evaluation (add --baseline to compare with_skill vs without_skill A/B delta)
python3 scripts/eval_skills.py run --skill deploying-helm-charts --harness claude --workers 2
```

---

## Authoring Standards & Open-Source Hygiene Rules

1. **Outcome-driven, natural prompts**: Write realistic operator/architect prompts without hardcoding internal `references/*.md` filenames in the prompt text.
2. **Strictly read-only live checks + adversarial safety cases**: Include guardrail test cases verifying that `secret-safety.py` and `aws-mutation-gate.py` block `.env`/secret exfiltration and unapproved infrastructure mutations.
3. **Placeholder identifiers only**: Always use standard AWS documentation dummy Account IDs (`123456789012`, `111122223333`, `444455556666`, `999988887777`), example resource prefixes (`example-prod-*`), and repo-relative paths (`files/...`). `eval_skills.py static` automatically rejects real account IDs and personal `/Users/...` paths.

For detailed authoring patterns and debugging workflows, see [`docs/skill-evals-handover-guide.md`](../docs/skill-evals-handover-guide.md).
