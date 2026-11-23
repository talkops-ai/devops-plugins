# CLAUDE.md

Guidance for Claude Code and contributors working in `talkops-ai/devops-plugins`: an Apache-2.0 marketplace (ID `talkops-devops-plugins`) of DevOps and cloud plugins for Claude Code, Codex, and any [Agent Plugins 1.0.0](https://agent-plugins.org) host.

The full standards live in these docs. Read the relevant one before you make a non-trivial change:

- [CONTRIBUTING.md](./CONTRIBUTING.md): workflow, shared-skill sync, new plugins, pre-PR checklist
- [docs/authoring-agent-plugins.md](./docs/authoring-agent-plugins.md): manifests, agent frontmatter, MCP binding, connectors, hooks
- [evals/README.md](./evals/README.md) and [docs/skill-evals-handover-guide.md](./docs/skill-evals-handover-guide.md): eval schemas and authoring rules

## Repository layout

```text
.claude-plugin/marketplace.json   # Claude Code marketplace catalog
.agents/plugins/marketplace.json  # Codex marketplace catalog (keep in sync with the Claude catalog)
plugins/
  agent-plugins/<agent>/          # Specialist sub-agents (agents/<agent>.md + codex/agents/<agent>.toml)
  vertical-plugins/<domain>/      # Domain bundles that attach to the main agent (no agents/ dir)
  partner-built/<vendor>/         # Vendor/ecosystem plugins (copy vendor content unmodified)
evals/
  schemas/                        # execution_evals / trigger_evals JSON Schemas
  skills/<skill-name>/            # One canonical eval suite per skill: evals.json, trigger_evals.json, files/
scripts/
  validate_plugins.py             # Manifest, binding, hook, portable-schema & Codex catalog validator
  eval_skills.py                  # Skill evals: static / trigger / run
docs/                             # Authoring guide, IAM guardrails, MCP coverage, eval guides
llms.txt                          # Machine-readable repo index for LLMs
```

All plugins are authored and maintained in place. No generator step applies.

## Plugin authoring and maintenance rules

- **Ship all 3 host formats.** Every plugin is kebab-case, and the directory name, manifest `name`, and marketplace `name` all match. Each plugin needs `.claude-plugin/plugin.json` (Claude Code), `plugin.json` (portable Agent Plugins 1.0.0), and `.codex-plugin/plugin.json` (Codex overlay). MCP servers go in both `.mcp.json` (Claude) and `mcp.json` (portable). The portable file expands only `${PLUGIN_ROOT}` and `${PLUGIN_DATA}`. Claude-only features (slash commands, `tools:` allowlists, `prompt` hooks) can enhance a plugin but must never be its only mechanism.
- **Register new plugins in both catalogs**: `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`. Also add them to `README.md` and `plugins/<category>/README.md`.
- **Sync shared skill mirrors.** Many skills exist in a vertical plugin *and* in one or more agent plugins (for example, `amazon-aurora-postgresql` is in `vertical-plugins/aws-databases` and `agent-plugins/aws-database-engineer`). When you edit a shared skill's `SKILL.md`, `references/`, or `scripts/`, copy the identical change to every plugin that bundles it. `eval_skills.py static --skill <name>` reports any drift.
- **Keep agent metadata in sync** when an agent plugin gains or loses a skill or MCP server:
  - `## Skills this agent uses` in `agents/<agent>.md` must match `skills/*/SKILL.md` exactly.
  - `tools:` must bind every `.mcp.json` server as `mcp__plugin_<agent>_<server>__*` and every `CONNECTORS.md` key as `mcp__<key>__*`, in both directions.
  - `codex/agents/<agent>.toml` must stay aligned with `agents/<agent>.md`.
- **Keep `SKILL.md` small.** The frontmatter `name` must equal the directory name, and `description` must be ≤ 1,024 chars with clear triggers and "not for" boundaries. Keep the body ≤ 500 lines and ≤ 5,000 tokens. Move deep content into `references/*.md` and calculators into `scripts/*.py`. Every referenced path must exist, and bundled scripts must be valid stdlib Python whose `--help` runs without reading stdin.
- **Never put `"disabled": true` in `.mcp.json` or `mcp.json`.** Claude Code ignores it and the portable schema forbids it. Servers that need an endpoint, credentials, or Docker go in `CONNECTORS.md` as connectors.
- **Default to read-only MCP servers.** Don't use `--allow-write` unless mutation is the plugin's core job. Never set `AWS_PROFILE` or hardcode secrets. Use `AWS_REGION` = `${AWS_REGION:-us-east-1}` in `.mcp.json` only.
- **Safety hooks.** Every plugin wires `hooks/secret-safety.py` through `hooks/hooks.json`. AWS/IaC plugins also wire `hooks/aws-mutation-gate.py` with its `aws-mutation-gate.json` sidecar. Hooks are stdlib-only Python `command` hooks that handle both the Claude Code and Codex JSON protocols. They reference files via `${CLAUDE_PLUGIN_ROOT}`, use `PreToolUse` for gates and `PostToolUse` for linters, and match both `mcp__plugin_.*<server>` and `mcp__<server>` tool prefixes.
- **Don't hardcode marketplace counts** (numbers of plugins, skills, or eval cases) in `README.md` or `llms.txt`. They go stale with every addition. Describe categories and link to the catalogs and indexes instead.
- **Partner-built plugins.** Keep vendor identity and license metadata, don't modify copyleft (for example, MPL-2.0) upstream files, and add attribution to `NOTICE`.
- If you change MCP servers, update `docs/mcp-server-coverage.md`.

## Validation and eval commands

Requires Python 3.11+. The scripts use only the standard library, so there is nothing to install.

```bash
# Before every PR
python3 scripts/validate_plugins.py               # manifests, bindings, connectors, hooks, portable & Codex catalogs
python3 scripts/validate_plugins.py --claude      # also run `claude plugin validate` (needs the claude CLI)
python3 scripts/eval_skills.py static             # Layer 1: frontmatter, links, scripts, mirror drift, eval schemas, hygiene

# For each skill you created or edited
python3 scripts/eval_skills.py static --strict-limits --skill <skill-name>
python3 scripts/eval_skills.py trigger --skill <skill-name> --dry-run
python3 scripts/eval_skills.py run --skill <skill-name> --dry-run

# Live evals (need an agent CLI; --harness agy|claude|codex, default agy)
python3 scripts/eval_skills.py trigger --skill <skill-name> --harness claude --workers 3   # Layer 2: 4-quadrant routing
python3 scripts/eval_skills.py run --skill <skill-name> --harness claude \
  --aws-profile <readonly-profile> --aws-region us-east-1 --workers 2                      # Layer 3: end-to-end execution
```

Live `run` evals write to `.eval-runs/<skill>/iteration-<N>/`. You can override the location with `DEVOPS_PLUGINS_EVAL_RUNS_DIR`. Use only a read-only AWS profile (see [docs/iam-guardrails.md](./docs/iam-guardrails.md)).

## Eval authoring

- Every canonical skill has `evals/skills/<skill-name>/evals.json` and `trigger_evals.json`. Each must conform to the schemas in `evals/schemas/`. Trigger quadrants are `explicit`, `implicit`, `contextual`, and `near_miss_negative`.
- Never create `plugins/**/evals/` directories. Evals live only at the top level, so plugin installs stay small.
- Write natural, outcome-driven prompts. Don't name internal `references/*.md`, `scripts/*.py`, or `/plugin:command` in prompts or expectations.
- Live checks must be strictly read-only. Include adversarial cases that confirm `secret-safety.py` and `aws-mutation-gate.py` block secret exfiltration and unapproved mutations.

## Open-source hygiene (enforced by `eval_skills.py static`)

- **Placeholder AWS account IDs only**: `123456789012`, `111122223333`, `444455556666`, `999988887777`. Use example resource prefixes such as `example-prod-*`.
- **No personal machine paths** (`/Users/...`, `/home/...`). Use repo-relative paths such as `files/...`.
- **Never commit `.eval-runs/`**, traces, grading output, `.env*` files, credentials, tokens, or private keys. Most of these are already gitignored.

## Commits and PRs

Use Conventional Commits (`feat(scope):`, `fix(scope):`, `docs(scope):`, `evals(scope):`, `refactor(scope):`, `chore(scope):`). Keep each PR focused on one plugin, domain, or eval wave, and paste the output of `validate_plugins.py` and `eval_skills.py static` into the PR template.
