## Summary

<!-- Briefly describe what this PR adds, fixes, or updates and why. -->

## Type of Change

- [ ] New plugin (`agent-plugins`, `vertical-plugins`, or `partner-built`)
- [ ] New skill or slash command
- [ ] Skill / reference / script improvement or bug fix
- [ ] Skill evaluation suite (`evals/skills/<skill-name>/`)
- [ ] Safety hook or MCP server / connector update
- [ ] Documentation or repository tooling

## Affected Plugins & Skills

<!-- List affected plugins and canonical skill names (e.g., `aws-databases`, `amazon-aurora-postgresql`). -->
- 

## Validation & Testing

Paste or summarize the results of local checks:

- `python3 scripts/validate_plugins.py`: <!-- e.g., 49 plugins checked: 0 error(s), 0 warning(s) -->
- `python3 scripts/eval_skills.py static`: <!-- e.g., 446 skill(s) checked, 0 error(s) -->
- Targeted evals (if applicable): <!-- e.g., trigger / run --dry-run or live GREEN results -->

## Pre-Submit Checklist

- [ ] I read [CONTRIBUTING.md](../CONTRIBUTING.md) and [docs/authoring-agent-plugins.md](../docs/authoring-agent-plugins.md).
- [ ] All shared skill copies across `vertical-plugins`, `agent-plugins`, and `partner-built` are synced (zero content drift).
- [ ] Any modified/added `SKILL.md` stays within the progressive-disclosure ceiling (`<= 500` lines / `<= 5,000` tokens) or offloads detail to `references/`.
- [ ] If adding a plugin: all 3 host layouts (`.claude-plugin/plugin.json`, root `plugin.json`, `.codex-plugin/plugin.json`) and both marketplace catalogs (`.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`) are updated.
- [ ] If modifying an agent plugin: `agents/<agent>.md` (`tools:` + `## Skills this agent uses`) and `codex/agents/<agent>.toml` are in sync.
- [ ] No `"disabled": true` entries in `.mcp.json` / `mcp.json`, no hardcoded secrets, no personal paths (`/Users/...`), and only placeholder AWS Account IDs (`123456789012`, etc.).
- [ ] No ephemeral `.eval-runs/` artifacts are committed.
- [ ] `README.md`, `docs/mcp-server-coverage.md`, and `NOTICE` are updated where applicable.
