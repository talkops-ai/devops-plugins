# Authoring plugins for the TalkOps DevOps marketplace

This marketplace follows the layout of [anthropics/financial-services](https://github.com/anthropics/financial-services). Every plugin is one of three kinds, and the kind decides where it lives and how its parts are wired.

| Kind | Directory | Binds to | When to use |
|---|---|---|---|
| **Agent plugin** | `plugins/agent-plugins/<agent>/` | A named specialist agent, spawned as a dynamic sub-agent | The work is an end-to-end role, such as "SRE agent" or "IaC engineer", with its own tools and guardrails |
| **Vertical plugin** | `plugins/vertical-plugins/<domain>/` | The main agent directly | Reusable skills and slash commands for a domain, with no persona or tool isolation |
| **Partner-built** | `plugins/partner-built/<vendor>/` | The main agent (or a vendor agent) | A wrapper for a third-party product, such as Datadog, PagerDuty, HashiCorp, or GitHub, usually built around the vendor's MCP server |

Every plugin needs a `.claude-plugin/plugin.json` and an entry in `.claude-plugin/marketplace.json`. Plugin names, directory names, and the marketplace `name` must all match, and must be kebab-case.

## Agent plugins

```
plugins/agent-plugins/<agent>/
├── .claude-plugin/plugin.json     # Claude Code manifest; name == <agent>
├── plugin.json                    # portable Agent Plugins 1.0.0 manifest (generated)
├── .codex-plugin/plugin.json      # Codex overlay: skills/mcp/hooks paths + interface card (generated)
├── agents/<agent>.md              # the primary agent (hand-written)
├── agents/<worker>.md             # optional worker sub-agents the primary dispatches
├── codex/agents/<agent>.toml      # Codex custom agent rendered from agents/<agent>.md (generated)
├── skills/<skill>/SKILL.md        # self-contained: copy shared skills in, don't reference other plugins
├── commands/*.md                  # optional slash commands (/<agent>:<command>)
├── hooks/hooks.json               # optional; reference files via ${CLAUDE_PLUGIN_ROOT}
├── .mcp.json                      # MCP servers, Claude Code format
├── mcp.json                       # the same servers, portable format (generated)
└── README.md
```

### Write for every host

These plugins run on Claude Code, Codex, and any host that implements [Agent Plugins 1.0.0](https://agent-plugins.org). Claude-only features are enhancements, never the only mechanism:

| Concern | Works everywhere | Claude Code enhancement |
|---|---|---|
| Capability | `skills/` (auto-discovered by every host) | slash commands |
| Tools | `mcp.json` / `.mcp.json` servers | per-agent `tools:` allowlist |
| Specialist persona | `agents/<agent>.md`, rendered to `codex/agents/<agent>.toml` | sub-agent spawning and tool isolation |
| Safety | server-side read-only flags, IAM, PreToolUse **command** hooks (Claude and Codex share the hook JSON protocol) | `prompt` hooks, `agent_type`-aware decisions |

Rules that follow from this:

- **Put safety in servers and command hooks, not only in prose or allowlists.** If an agent must not mutate AWS, set `"aws_read_only": true` in the map, point its `aws-mcp` at `aws-mcp-read-only`, and rely on the `aws-mutation-gate` hook. Codex has no per-agent tool allowlist.
- **Portable MCP.** The portable `mcp.json` expands only `${PLUGIN_ROOT}` and `${PLUGIN_DATA}`, takes literal headers, and has no `timeout`. The sync drops other `${VAR}` env values and skips remote servers that need expansion; document those servers for non-Claude hosts.
- **Hook scripts must handle both protocols.** Read the event from stdin. Claude Code sends `agent_type` for sub-agents; Codex sends `turn_id` and sets `PLUGIN_ROOT`. Emit `hookSpecificOutput.permissionDecision` (`deny`/`ask`) or `additionalContext`, and exit 0. Use a stdlib-only Python script and an `exec` interpreter chain, so that a missing `python3` doesn't silently skip the gate.
- **Agent bodies are reused as Codex `developer_instructions`.** Name skills and MCP servers by plain name (`awsiac`, `terraform-style-guide`), describe actions as CLI commands where possible, and avoid relying on Claude-only tool names for control flow. The sync adds a preamble that maps `mcp__plugin_<plugin>_<server>__*` to Codex names.
- **Codex packaging.** Codex reads the repo marketplace at `.agents/plugins/marketplace.json` (generated from the map), not a root `.codex-plugin/marketplace.json`. Card fields (`displayName`, `category`, `brandColor`, ...) come from `hosts.codex` in the map; set `defaultPrompt` (up to three starter prompts) per plugin to populate the card.

### Agent definition (`agents/<agent>.md`)

The frontmatter contains exactly these keys:

```yaml
---
name: <agent>                       # must equal the plugin name
description: <what it does>. Use for <triggers>. Not for <X> (<other-agent>).
tools: Read, Grep, Glob, Bash, Write, Edit, Skill, TodoWrite, WebFetch, mcp__plugin_<agent>_<server>__*
---
```

- **`description`** is the routing signal. Name the concrete services and tasks the agent covers, and end with explicit "Not for …" hand-offs to sibling agents.
- **`tools`** is an allowlist. Always include `Skill`. Drop `Edit` and `Write` for advisory or read-only agents, such as SRE, FinOps, or documentation agents. Add `Agent` only when the primary agent dispatches worker sub-agents.
- Don't use `mcpServers`, `hooks`, or `permissionMode`. Claude Code ignores them for plugin agents.

Write the body in this order:

1. A one-line role statement: "You are the … —".
2. `## What you produce`: a numbered list of deliverables.
3. `## Workflow`: route by intent to skills, naming each skill in backticks.
4. `## MCP servers bound to this agent`: a table with server and use.
5. `## Guardrails`: confirmations before mutation or spend, secret handling, and **"No questions mid-run as a sub-agent. Return missing inputs as a question list to the caller."** Sub-agents can't prompt the user.
6. `## Hand-offs`: which sibling agent owns adjacent work.
7. `## Skills this agent uses`: every bundled skill, in backticks, separated by ` · `. The validator requires this list to match `skills/*/SKILL.md` exactly. Support directories without a `SKILL.md`, such as `skills/shared/`, are exempt.

### MCP binding

Claude Code names plugin MCP tools `mcp__plugin_<plugin>_<server>__<tool>`. To bind a server:

1. Declare it in `.mcp.json` under `mcpServers.<server>`.
2. Add `mcp__plugin_<agent>_<server>__*` to the agent's `tools`.

The validator fails if a server is declared but not bound, or bound but not declared.

When you configure servers:

- Don't set `AWS_PROFILE`. Inherit credentials from the environment. Set `AWS_REGION` to `${AWS_REGION:-us-east-1}` (Claude Code only; the portable copy drops it).
- Start awslabs servers **read-only** (omit `--allow-write` and `--allow-sensitive-data-access`) unless the agent's core job is mutation, and say so in the README. Check each server's published `--help`: flags in upstream READMEs sometimes differ from the released package (for example, the IAM server is read-only by default and rejects `--readonly`).
- For read-only agents, use `{"aws-mcp": {"$ref": "aws-mcp-read-only"}}`. Keep the server name `aws-mcp` so that tool patterns stay stable.
- Pick servers from the [awslabs/mcp](https://github.com/awslabs/mcp) catalog (`reference/mcp/src`). Reusable definitions live in `mcp_catalog` in `scripts/aws-plugin-map.json`, and [docs/mcp-server-coverage.md](./mcp-server-coverage.md) shows where each one is used.

### Connectors (connection-bound servers)

Plugin MCP files have no reliable "disabled" switch across hosts. Claude Code **ignores `"disabled": true`** (every declared server starts when the plugin is enabled), and the portable schema has no such key. Servers that need a connection target or local runtime at startup (a cluster endpoint, cache host, connection string, scoped list of functions, or Docker) therefore can't ship in the plugin's MCP files. Model them as **connectors** instead:

1. Add the server to `connector_catalog` in the map as structured data: `package`, `docs`, `purpose`, `command`, `args`, optional `env`, optional one-time `setup` shell line, and `notes`. List its key in the plugin's `connectors`.
2. The sync writes `CONNECTORS.md` with `claude mcp add`, `codex mcp add`, and `~/.codex/config.toml` snippets, and links it from the README.
3. In an agent plugin, add `mcp__<key>__*` to the agent's `tools` so the agent can use the server once the user adds it under that exact key. The validator accepts `mcp__<key>__*` only for keys in the plugin's `CONNECTORS.md`, and requires every connector key to be bound.
4. In the agent body, say the connector is optional and give the fallback path when it is missing.

The validator rejects `"disabled"` in any plugin `.mcp.json`.

### Hooks

- Use `PreToolUse` for safety gates (for example, the shared `secret-safety.py` and `aws-mutation-gate.py`) and `PostToolUse` for validators (template linting, diagram checks).
- Matchers are regexes. For MCP tools, match on the `mcp__plugin_<agent>_<server>__` prefix (Claude Code) and the `mcp__<server>__` prefix (Codex), for example `mcp__aws.*|mcp__plugin_.*aws-mcp.*`. Codex reports shell calls as `Bash` and file edits as `apply_patch`.
- Reference every file through `${CLAUDE_PLUGIN_ROOT}`. Codex sets it too, and the validator checks that these paths exist.
- Prefer `command` hooks. `prompt` hooks run only in Claude Code.
- TalkOps-authored hook scripts live in `src/hooks/` and are copied by the sync through the `talkops` source in `hooks_catalog`. Generated sidecars (for example `aws-mutation-gate.json`, the list of read-only agents) are written by the sync.

## Vertical plugins

```
plugins/vertical-plugins/<domain>/
├── .claude-plugin/plugin.json     # name == <domain>
├── skills/<skill>/SKILL.md        # attach to the main agent
├── commands/*.md                  # hand-written slash commands (/<domain>:<command>)
├── hooks/hooks.json               # optional
├── .mcp.json                      # servers available to the main agent
├── CONNECTORS.md                  # optional, generated from connector_catalog
└── README.md
```

Vertical plugins have no `agents/<plugin>.md`. Skills, commands, and MCP servers load into the main agent, so:

- Keep skill descriptions sharply scoped. They compete with every other installed skill for activation.
- Group by **domain** (networking, databases, observability, ...), merging the domain's router skill with its task skills, so users can install exactly the capability they want without a sub-agent hand-off.
- Prefer slash commands as the entry point for multi-step workflows. Each command needs a `description` (and an `argument-hint` when it takes input), routes to named skills and MCP servers, and states its mutation policy: read-only, or "show the plan and wait for approval".
- `.mcp.json` servers become available to the main agent, so keep them read-only by default and leave secret-bearing or endpoint-bound servers to connectors.
- Each vertical is self-contained and ships its own `aws-mcp`. If you install several verticals, toggle duplicate `aws-mcp` instances off in `/mcp`.
- In the map, list the agent plugins that cover the same domain in `agents`; the README points users to them when they want an isolated specialist.

## Partner-built plugins

- Prefer vendor-published content: the vendor's official skills and MCP server (a remote `http` endpoint or the published package). Pin versions when the vendor publishes them.
- Add the plugin to `scripts/aws-plugin-map.json` with `"kind": "partner"`. Add the vendor repo as a `sources` entry (with its `license`) and check it out under `reference/`. The sync then copies the content into `plugins/partner-built/<name>/` and generates the Claude Code, portable, and Codex layouts and both marketplace entries.
- Keep the vendor's identity. Set `author`, `homepage`, `repository`, `license`, and `version` on the map entry (they override `defaults`), and `codex_interface` (`developerName`, `category`, `brandColor`, `websiteURL`) for the Codex card. Use the vendor's plugin name, for example `terraform`.
- Copy vendor content **unmodified**. Don't add rewrites to copyleft (for example MPL-2.0) files. Add the project and license to `NOTICE`.
- Connection-bound or runtime-bound servers (credentials, Docker) go in `connectors`, as for the AWS plugins. Never commit secrets.
- Set `agents` to the TalkOps agent plugins that cover the same ground, so the README can point users to the isolated specialist.

## Generated AWS plugins

The AWS agent and vertical plugins are generated from upstream sources by `scripts/sync_aws_plugins.py` using `scripts/aws-plugin-map.json`.

- To change which skills, MCP servers, connectors, or hooks a plugin gets, edit the map, then re-run the sync.
- To change agent behaviour, edit `agents/<agent>.md`. To change vertical workflows, edit `commands/*.md`. The sync never overwrites either.
- Don't hand-edit generated files (`skills/`, `.mcp.json`, `plugin.json`, `README.md`, `CONNECTORS.md`, `docs/mcp-server-coverage.md`). Use `rewrites` for targeted patches. The sync fails if an upstream file it patches has drifted.

Map features worth knowing:

| Key | Purpose |
|---|---|
| `plugins[].kind` | `agent` (default) or `vertical`; decides the output directory and which dirs the sync owns |
| `sources.<key>.flat` | The source keeps skills directly under the referenced path (the toolkit's `skills/` tree) instead of `<plugin>/skills/` |
| `skills[].except` | Skip named skills when `names` is `"*"` |
| `rewrites_catalog` | Named, reusable rewrite sets; reference them by name from a plugin's or hook's `rewrites` |
| `connector_catalog` / `plugins[].connectors` | Opt-in, user-added MCP servers rendered into `CONNECTORS.md` |
| `mcp_upstream_index` | Every awslabs/mcp server mapped to its catalog key or a skip reason; a full sync fails if a new upstream server is unaccounted for |

Before opening a PR, run `python3 scripts/validate_plugins.py --claude`, then `python3 scripts/render_handover_docs.py` to refresh [docs/handover/](./handover/). When you add a plugin or change a design decision, record the rationale in `scripts/handover-notes.json` so reviewers see it next to the plugin.
