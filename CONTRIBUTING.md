# Contributing to TalkOps DevOps Plugins

Thank you for your interest in contributing to **TalkOps DevOps Plugins**! This repository is an open-source marketplace of **49 plugins** (**446 canonical skills**) spanning AWS architecture, cloud engineering, FinOps, security, SRE, Kubernetes, and partner DevOps tools—working across **Claude Code**, **Codex**, and any host implementing [Agent Plugins 1.0.0](https://agent-plugins.org).

Whether you are fixing a typo, hardening a safety hook, improving a skill, adding evaluation coverage, or contributing a brand-new plugin, this guide walks you through the workflow and quality gates.

---

## Table of Contents

- [Ways to Contribute](#ways-to-contribute)
- [Prerequisites & Local Setup](#prerequisites--local-setup)
- [Repository Architecture](#repository-architecture)
- [Updating an Existing Skill or Plugin](#updating-an-existing-skill-or-plugin)
- [Adding a New Plugin](#adding-a-new-plugin)
- [Authoring & Running Skill Evaluations](#authoring--running-skill-evaluations)
- [Pre-PR Validation Checklist](#pre-pr-validation-checklist)
- [Pull Request & Commit Guidelines](#pull-request--commit-guidelines)
- [Licensing & Upstream Attribution](#licensing--upstream-attribution)

---

## Ways to Contribute

- **Improve existing skills**: Fix outdated service limits, add missing edge cases, split oversized `SKILL.md` files into progressive-disclosure `references/`, or sharpen trigger descriptions.
- **Add new skills or slash commands**: Extend an existing agent or vertical plugin with new operational workflows, calculators, or troubleshooting playbooks.
- **Add a new plugin**: Contribute a specialist agent plugin (`plugins/agent-plugins/`), a main-agent domain bundle (`plugins/vertical-plugins/`), or a vendor/ecosystem plugin (`plugins/partner-built/`).
- **Expand skill evaluations**: Upgrade baseline suites under `evals/skills/` to full multi-quadrant `evals.json` and `trigger_evals.json` suites, or add regression tests for real-world bugs.
- **Strengthen safety hooks & MCP integrations**: Improve `secret-safety.py`, `aws-mutation-gate.py`, domain linters, or `CONNECTORS.md` setup guides.
- **Report bugs & propose features**: Open an issue using our [GitHub issue templates](./.github/ISSUE_TEMPLATE). For security vulnerabilities, see [SECURITY.md](./SECURITY.md) instead of opening a public issue.

---

## Prerequisites & Local Setup

1. **Fork and clone** the repository:

   ```bash
   git clone https://github.com/<your-username>/devops-plugins.git
   cd devops-plugins
   git checkout -b feat/<short-description>
   ```

2. **Required local tooling**:
   - **Python 3.11+** on `PATH` (used by `scripts/validate_plugins.py`, `scripts/eval_skills.py`, and deterministic safety hooks). All validation scripts use the Python standard library only.
   - **[`uv`](https://docs.astral.sh/uv/)** (`uvx`) if you test stdio MCP servers locally.
   - **Node.js (`npx`)** if you work with `@drawio/mcp`.
   - **Optional (for live evals and host testing)**:
     - Claude Code (`claude`) and/or Codex (`codex`) CLI.
     - AWS CLI v2 configured with a **read-only** profile (see [docs/iam-guardrails.md](./docs/iam-guardrails.md)) for live AWS skill evaluations.
     - Local Kubernetes cluster (e.g., `docker-desktop`) for Kubernetes delivery/observability evaluations.

3. **Verify your baseline environment**:

   ```bash
   python3 scripts/validate_plugins.py
   python3 scripts/eval_skills.py static
   ```

---

## Repository Architecture

All plugins are authored and maintained **directly in-place** across three categories:

| Category | Path | Attaches To | Purpose |
|---|---|---|---|
| **Agent plugins** | `plugins/agent-plugins/<agent>/` | Isolated specialist sub-agent | End-to-end role (e.g., `aws-sre-agent`, `kubernetes-delivery-engineer`) with scoped MCP tools, guardrails, and persona |
| **Vertical plugins** | `plugins/vertical-plugins/<domain>/` | Main agent directly | Focused domain bundles of skills, multi-phase slash commands, hooks, and MCP servers with no sub-agent hand-off |
| **Partner-built plugins** | `plugins/partner-built/<vendor>/` | Main agent (or vendor agent) | Official vendor/ecosystem skills and MCP servers (e.g., HashiCorp Terraform, LaunchDarkly, Coralogix, Honeycomb, Elastic, Neo4j, Bronto) |

Key supporting directories:

- `.claude-plugin/marketplace.json` — Claude Code marketplace catalog (`talkops-devops-plugins`).
- `.agents/plugins/marketplace.json` — Codex marketplace catalog (must stay in sync with `.claude-plugin/marketplace.json`).
- `evals/skills/<skill-name>/` — Single source of truth for canonical skill evaluation suites (`evals.json`, `trigger_evals.json`, optional `files/`). Keeping evals at the repo root guarantees **0 KB install bloat** for plugin users.
- `scripts/validate_plugins.py` — Validates all manifests, agent/MCP bindings, connectors, hooks, portable Agent Plugins 1.0.0 schemas, and Codex layouts.
- `scripts/eval_skills.py` — Runs Layer 1 (`static`), Layer 2 (`trigger`), and Layer 3 (`run`) skill evaluations.
- `docs/` — Deep standards: [authoring-agent-plugins.md](./docs/authoring-agent-plugins.md), [iam-guardrails.md](./docs/iam-guardrails.md), [mcp-server-coverage.md](./docs/mcp-server-coverage.md), [skill-evals-handover-guide.md](./docs/skill-evals-handover-guide.md), and [skill-evals-rollout-plan.md](./docs/skill-evals-rollout-plan.md).

---

## Updating an Existing Skill or Plugin

Before editing any skill or plugin, review [docs/authoring-agent-plugins.md](./docs/authoring-agent-plugins.md) and follow these rules:

### 1. Keep `SKILL.md` Concise (Progressive Disclosure)
- Keep `SKILL.md` frontmatter `name` matching its directory name and `description` **≤ 1,024 characters**, sharply scoped with clear trigger keywords and explicit negative boundaries where sibling skills exist.
- Keep `SKILL.md` body **≤ 500 lines** and **≤ 5,000 tokens** (~20 KB). Move deep reference tables, runbooks, and schemas into `references/*.md` and deterministic calculators/validators into `scripts/*.py`.
- Every relative `references/*`, `scripts/*`, or `assets/*` path mentioned in `SKILL.md` must exist on disk.
- Every bundled Python script in `scripts/` must be syntactically valid and support `--help` cleanly without hanging on `stdin`.

### 2. Enforce MCP-First & Safe Fallbacks
- Instruct agents to query connected MCP servers (`aws-mcp`, `awspricing`, `cloudwatch`, `eks`, `ecs`, etc.) before falling back to raw CLI commands.
- Include an `awsknowledge` fallback directive for AWS skills so edge cases outside local `references/` trigger 1–2 focused documentation searches instead of stalling.
- Never recommend unsafe defaults (e.g., public S3 ACLs, IMDSv1, plaintext credentials, `Resource: "*"` trust policies, unapproved mutations).

### 3. Sync Shared Skill Mirrors Across Plugins
Many canonical skills live in both a **vertical plugin** and one or more **agent plugins** (for example, `amazon-aurora-postgresql` exists in both `plugins/vertical-plugins/aws-databases/` and `plugins/agent-plugins/aws-database-engineer/`).

- Whenever you update a shared skill's `SKILL.md`, `references/`, or `scripts/`, copy the exact changes to **every plugin** that bundles that skill.
- Run `python3 scripts/eval_skills.py static --skill <skill-name>` — it automatically detects and reports any content drift across shared plugin copies.

### 4. Keep Agent & Codex Metadata in Sync
If you add or remove a skill or MCP server on an **agent plugin**:
- Update `## Skills this agent uses` in `agents/<agent>.md` so it matches `skills/*/SKILL.md` exactly.
- Update `tools:` in `agents/<agent>.md` so every `.mcp.json` server (`mcp__plugin_<agent>_<server>__*`) and every `CONNECTORS.md` entry (`mcp__<key>__*`) is bound in both directions.
- Update `codex/agents/<agent>.toml` so Codex `developer_instructions` stays aligned with `agents/<agent>.md`.

---

## Adding a New Plugin

For a new plugin, open a [New Plugin / Skill Proposal](./.github/ISSUE_TEMPLATE/new_plugin_or_skill.yml) issue first so maintainers can help confirm the right category, naming, and scope.

### 1. Required Directory Layout (All 3 Host Formats)

Every plugin must be kebab-case (`[a-z0-9][a-z0-9-]*`) and ship all three layouts so it works on Claude Code, Codex, and Agent Plugins 1.0.0 hosts:

```text
plugins/<category>/<plugin-name>/
├── .claude-plugin/plugin.json     # Claude Code manifest (name == <plugin-name>)
├── plugin.json                    # Portable Agent Plugins 1.0.0 manifest ($schema + matching name/version)
├── .codex-plugin/plugin.json      # Codex overlay (skills/mcp/hooks paths + interface card)
├── .mcp.json                      # Claude Code MCP servers (optional; no "disabled" keys)
├── mcp.json                       # Portable Agent Plugins 1.0.0 MCP servers (no host ${VAR} expansion)
├── CONNECTORS.md                  # Optional connection-bound / Docker / credentialed MCP servers
├── hooks/
│   ├── hooks.json                 # Safety & lint hooks referencing ${CLAUDE_PLUGIN_ROOT}/hooks/...
│   ├── secret-safety.py           # Required across all plugins
│   └── aws-mutation-gate.py       # Required for AWS/IaC plugins (+ aws-mutation-gate.json sidecar)
├── skills/<skill-name>/SKILL.md   # One or more self-contained skills
├── commands/*.md                  # Optional slash commands (description + mutation policy)
├── agents/<plugin-name>.md        # Agent plugins ONLY (not vertical plugins)
├── codex/agents/<plugin-name>.toml# Agent plugins ONLY
└── README.md                      # Skills, commands, MCP servers, hooks, and usage examples
```

See [docs/authoring-agent-plugins.md](./docs/authoring-agent-plugins.md) for the exact frontmatter keys, `tools:` allowlist rules, hook JSON protocol, and portable schema constraints.

### 2. Register in Both Marketplace Catalogs

Add your plugin entry to **both**:
1. `.claude-plugin/marketplace.json` (with `name`, `displayName`, `source`, `description`, `version`, `category`, `keywords`, `author`, `license`).
2. `.agents/plugins/marketplace.json` (with `name`, `source` pointing to the local path, `policy`, and `category`).

### 3. Safety & MCP Rules

- **Never ship `"disabled": true` in `.mcp.json` or `mcp.json`.** Claude Code ignores it and the portable schema forbids it. Model endpoint-bound or Docker-based servers as connectors in `CONNECTORS.md`.
- **Default to read-only.** Start bundled MCP servers with read-only flags (`--read-only`, `MCP_ALLOW_WRITE=false`, etc.) unless mutation is the plugin's primary job.
- **Never hardcode `AWS_PROFILE` or secrets.** Credentials must come from the user's runtime environment.
- **Wire deterministic hooks.** Include `secret-safety.py` in `hooks/hooks.json` (and `aws-mutation-gate.py` + `aws-mutation-gate.json` for AWS/IaC plugins). Hook scripts must be stdlib-only Python and support both Claude Code and Codex JSON event formats.

### 4. Update Repository Docs & Attribution

- Add your plugin to [README.md](./README.md) (in the appropriate collapsible catalog table; avoid adding hardcoded counts) and the relevant category index (`plugins/<category>/README.md`).
- If you add or change MCP servers, update [docs/mcp-server-coverage.md](./docs/mcp-server-coverage.md).
- If your plugin adapts or redistributes third-party upstream skills (especially partner-built plugins), keep upstream files unmodified where required by license (e.g., MPL-2.0) and add full attribution to [NOTICE](./NOTICE).

---

## Authoring & Running Skill Evaluations

Every canonical skill in the marketplace must have an evaluation folder at `evals/skills/<skill-name>/` containing:

- `evals.json` — Layer 3 execution cases conforming to `evals/schemas/execution_evals.schema.json`.
- `trigger_evals.json` — Layer 2 4-quadrant trigger queries (`explicit`, `implicit`, `contextual`, `negative`) conforming to `evals/schemas/trigger_evals.schema.json`.
- `files/` *(optional)* — Sample fixtures staged into isolated test workspaces.

### Evaluation Authoring Rules

Read [evals/README.md](./evals/README.md) and [docs/skill-evals-handover-guide.md](./docs/skill-evals-handover-guide.md) in full before authoring evals. Key rules:

1. **Natural, outcome-driven prompts**: Never hardcode internal `references/*.md`, `scripts/*.py`, or `/plugin:command` names in `evals.json` prompts or expectations.
2. **Strictly read-only live checks + adversarial safety cases**: Never write an AWS eval prompt that mutates live resources. Include adversarial cases verifying that `secret-safety.py` and `aws-mutation-gate.py` refuse secret exfiltration and unapproved mutations.
3. **Open-source hygiene (enforced automatically by `eval_skills.py static`)**:
   - **No co-located `plugins/**/evals/` directories** — all evals live under top-level `evals/skills/`.
   - **No real AWS Account IDs** — only use AWS documentation placeholder IDs (`123456789012`, `111122223333`, `444455556666`, `999988887777`) and example resource prefixes (`example-prod-*`).
   - **No personal machine paths** (e.g., `/Users/...`, `/home/...`) or committed `.eval-runs/` artifacts.

### Running Evaluations Locally

```bash
# Layer 1: Static spec, link, script, drift, schema & open-source hygiene audit
python3 scripts/eval_skills.py static
python3 scripts/eval_skills.py static --strict-limits --skill <skill-name>

# Dry-run schema & staging check (no LLM / AWS calls)
python3 scripts/eval_skills.py trigger --skill <skill-name> --dry-run
python3 scripts/eval_skills.py run --skill <skill-name> --dry-run

# Layer 2: 4-quadrant trigger routing eval (supports --harness claude|codex|agy)
python3 scripts/eval_skills.py trigger --skill <skill-name> --harness claude --workers 3

# Layer 3: Isolated end-to-end execution eval (writes ephemeral runs to .eval-runs/)
python3 scripts/eval_skills.py run --skill <skill-name> --harness claude --aws-profile <readonly-profile> --aws-region us-east-1 --workers 2
```

> **Note**: `.eval-runs/` is gitignored. Never commit runtime logs, traces, or credentials.

---

## Pre-PR Validation Checklist

Run these commands locally before opening a pull request:

```bash
# 1. Validate all plugin manifests, bindings, hooks, portable schemas & Codex catalogs
python3 scripts/validate_plugins.py

# 2. (Optional, if Claude Code CLI is installed) Run Claude's built-in validator
python3 scripts/validate_plugins.py --claude

# 3. Validate all 446+ skills, links, scripts, shared-skill parity & eval schemas
python3 scripts/eval_skills.py static

# 4. For any skill you created or edited, enforce strict line/token ceilings & dry-run evals
python3 scripts/eval_skills.py static --strict-limits --skill <skill-name>
python3 scripts/eval_skills.py trigger --skill <skill-name> --dry-run
python3 scripts/eval_skills.py run --skill <skill-name> --dry-run
```

---

## Pull Request & Commit Guidelines

- **Branch naming**: Use descriptive branches such as `feat/<plugin-or-skill>`, `fix/<issue-slug>`, `evals/<skill-name>`, or `docs/<topic>`.
- **Conventional Commits**: Follow standard prefixes (`feat(scope): ...`, `fix(scope): ...`, `docs(scope): ...`, `refactor(scope): ...`, `evals(scope): ...`, `chore(scope): ...`).
- **Keep PRs focused**: Group changes by plugin, domain, or evaluation wave so reviewers can validate diffs cleanly.
- **Fill out the PR template**: Include validation outputs (`validate_plugins.py` and `eval_skills.py static`) and note any live eval results.
- **Follow the Code of Conduct**: All interactions in issues, PRs, and discussions must adhere to [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md).

---

## Licensing & Upstream Attribution

- Contributions to this repository are licensed under the **Apache License, Version 2.0** ([LICENSE](./LICENSE)), unless explicitly scoped to a third-party partner plugin directory carrying its own upstream license (such as `plugins/partner-built/terraform/` under MPL-2.0).
- By submitting a pull request, you confirm that you have the right to contribute your changes under the repository's license and that any third-party upstream content is properly attributed in [NOTICE](./NOTICE).
