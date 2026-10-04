#!/usr/bin/env python3
"""Validate the TalkOps devops-plugins marketplace.

Checks every plugin listed in .claude-plugin/marketplace.json:

  * marketplace entry -> plugin dir exists, names match .claude-plugin/plugin.json
  * all *.json files in the plugin parse
  * agent plugins: agents/<plugin-name>.md exists with name/description/tools,
    every `mcp__plugin_<plugin>_<server>__*` tool pattern maps to a server in
    .mcp.json and every server is bound in the agent's tools (both directions),
    `mcp__<key>__*` patterns match a connector key in CONNECTORS.md (both
    directions), and the "## Skills this agent uses" list matches
    skills/*/SKILL.md exactly
  * vertical plugins: at least one skill, no primary agent definition
  * .mcp.json servers do not use "disabled" (Claude Code ignores it for plugins)
  * every SKILL.md has name (matching its directory) and description
  * every commands/*.md and other agents/*.md has a description (agents: name too)
  * hooks/hooks.json is well-formed and ${CLAUDE_PLUGIN_ROOT} paths exist; the
    aws-mutation-gate hook has its generated aws-mutation-gate.json sidecar

Multi-host checks (agent, vertical, and partner-built plugins):

  * portable Agent Plugins 1.0.0 layout: root plugin.json has the 1.0.0 $schema, only
    schema keys, and the same name/version as .claude-plugin/plugin.json; mcp.json (when
    present) has the 1.0.0 $schema, only per-transport keys, no host ${VAR} expansion, and
    a subset of the .mcp.json server names
  * Codex overlay .codex-plugin/plugin.json: same name, every referenced path exists,
    interface.displayName/shortDescription/developerName/category set
  * Codex marketplace .agents/plugins/marketplace.json lists every Claude marketplace
    plugin with a local source, policy, and category; no stale root
    .codex-plugin/marketplace.json (Codex does not read it)
  * agent plugins: codex/agents/<name>.toml parses and has name/description/developer_instructions

Usage:
    python3 scripts/validate_plugins.py            # structural checks
    python3 scripts/validate_plugins.py --claude   # also run `claude plugin validate`
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _plugin_lib import (  # noqa: E402
    CODEX_MARKETPLACE_PATH,
    MARKETPLACE_PATH,
    PLUGIN_KINDS,
    PORTABLE_MCP_SCHEMA,
    PORTABLE_PLUGIN_KEYS,
    PORTABLE_PLUGIN_SCHEMA,
    PORTABLE_SERVER_KEYS,
    REPO_ROOT,
    load_json,
    mcp_tool_pattern,
    parse_frontmatter,
    parse_tools,
    skills_listed_in_agent,
    split_frontmatter,
)

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PLUGIN_ROOT_RE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s\"']+)")
HOOK_EVENTS = {
    "PreToolUse", "PostToolUse", "PostToolUseFailure", "UserPromptSubmit", "Notification",
    "Stop", "SubagentStart", "SubagentStop", "SessionStart", "SessionEnd", "PreCompact",
    "PermissionRequest",
}
SKIP_JSON_DIRS = {"node_modules", ".git", "fixtures"}
CONNECTOR_ROW_RE = re.compile(r"^\|\s*`([a-z0-9][a-z0-9-]*)`\s*\|", re.MULTILINE)
NON_PORTABLE_RE = re.compile(r"\$\{(?!PLUGIN_ROOT\}|PLUGIN_DATA\})")
GATE_SCRIPT = "hooks/aws-mutation-gate.py"
CODEX_AGENT_KEYS = {"name", "description", "developer_instructions"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


def check_json_files(root: Path, rep: Report) -> None:
    for path in root.rglob("*.json"):
        if SKIP_JSON_DIRS.intersection(path.relative_to(root).parts):
            continue
        try:
            json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            rep.err(str(path.relative_to(REPO_ROOT)), f"invalid JSON: {exc}")


def check_skills(plugin_dir: Path, rep: Report) -> set[str]:
    names: set[str] = set()
    skills_dir = plugin_dir / "skills"
    if not skills_dir.is_dir():
        return names
    for d in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            continue  # support dirs such as skills/shared are allowed
        where = str(skill_md.relative_to(REPO_ROOT))
        fm = parse_frontmatter(skill_md.read_text())
        name, desc = fm.get("name", ""), fm.get("description", "")
        if not name:
            rep.err(where, "missing frontmatter 'name'")
        elif name != d.name:
            rep.err(where, f"name '{name}' does not match directory '{d.name}'")
        if not desc:
            rep.err(where, "missing frontmatter 'description'")
        names.add(d.name)
    return names


def check_hooks(plugin_dir: Path, rep: Report) -> None:
    hooks_json = plugin_dir / "hooks" / "hooks.json"
    if not hooks_json.exists():
        return
    where = str(hooks_json.relative_to(REPO_ROOT))
    try:
        data = load_json(hooks_json)
    except json.JSONDecodeError:
        return  # already reported
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        rep.err(where, "top-level 'hooks' object missing")
        return
    for event, groups in hooks.items():
        if event not in HOOK_EVENTS:
            rep.warn(where, f"unknown hook event '{event}'")
        for group in groups:
            if "matcher" in group:
                try:
                    re.compile(group["matcher"])
                except re.error as exc:
                    rep.err(where, f"{event}: bad matcher regex {group['matcher']!r}: {exc}")
            for hook in group.get("hooks", []):
                kind = hook.get("type")
                if kind == "command":
                    for rel in PLUGIN_ROOT_RE.findall(hook.get("command", "")):
                        if not (plugin_dir / rel).exists():
                            rep.err(where, f"{event}: referenced file missing: {rel}")
                elif kind == "prompt":
                    if not hook.get("prompt"):
                        rep.err(where, f"{event}: prompt hook without 'prompt'")
                else:
                    rep.err(where, f"{event}: unsupported hook type {kind!r}")
    if GATE_SCRIPT in hooks_json.read_text():
        sidecar = plugin_dir / "hooks" / "aws-mutation-gate.json"
        try:
            agents = load_json(sidecar).get("read_only_agents")
            if not isinstance(agents, list):
                rep.err(str(sidecar.relative_to(REPO_ROOT)), "'read_only_agents' must be a list")
        except (OSError, json.JSONDecodeError):
            rep.err(where, "aws-mutation-gate hook needs hooks/aws-mutation-gate.json (re-run the sync)")


def check_portable(plugin_dir: Path, claude_manifest: dict, rep: Report) -> None:
    """Agent Plugins 1.0.0 root plugin.json + mcp.json (read by Codex, Cursor, Copilot, ...)."""
    pj_path = plugin_dir / "plugin.json"
    where = str(pj_path.relative_to(REPO_ROOT))
    if not pj_path.exists():
        rep.err(where, "missing portable plugin.json (Agent Plugins 1.0.0)")
        return
    try:
        pj = load_json(pj_path)
    except json.JSONDecodeError:
        return
    if pj.get("$schema") != PORTABLE_PLUGIN_SCHEMA:
        rep.err(where, f"$schema must be {PORTABLE_PLUGIN_SCHEMA}")
    for key in sorted(set(pj) - PORTABLE_PLUGIN_KEYS):
        rep.err(where, f"key '{key}' is not allowed by the portable schema (additionalProperties: false)")
    for key in ("name", "version"):
        if pj.get(key) != claude_manifest.get(key):
            rep.err(where, f"{key} {pj.get(key)!r} != .claude-plugin/plugin.json {claude_manifest.get(key)!r}")

    mcp_path = plugin_dir / "mcp.json"
    if not mcp_path.exists():
        return
    where = str(mcp_path.relative_to(REPO_ROOT))
    try:
        mcp = load_json(mcp_path)
    except json.JSONDecodeError:
        return
    if mcp.get("$schema") != PORTABLE_MCP_SCHEMA:
        rep.err(where, f"$schema must be {PORTABLE_MCP_SCHEMA}")
    claude_servers: set[str] = set()
    if (plugin_dir / ".mcp.json").exists():
        try:
            claude_servers = set(load_json(plugin_dir / ".mcp.json").get("mcpServers", {}))
        except json.JSONDecodeError:
            pass
    for sname, conf in mcp.get("mcpServers", {}).items():
        allowed = PORTABLE_SERVER_KEYS.get(conf.get("type"))
        if allowed is None:
            rep.err(where, f"server '{sname}': type must be one of {sorted(PORTABLE_SERVER_KEYS)}")
            continue
        for key in sorted(set(conf) - allowed):
            rep.err(where, f"server '{sname}': key '{key}' is not allowed for type {conf['type']!r}")
        values = [*conf.get("args", []), *conf.get("env", {}).values(), conf.get("cwd", ""), conf.get("url", "")]
        if any(NON_PORTABLE_RE.search(v) for v in values) or any("${" in v for v in conf.get("headers", {}).values()):
            rep.err(where, f"server '{sname}': only ${{PLUGIN_ROOT}}/${{PLUGIN_DATA}} expand in the portable format")
        if sname not in claude_servers:
            rep.err(where, f"server '{sname}' is not in .mcp.json; both files must describe the same servers")


def check_codex(plugin_dir: Path, name: str, is_agent: bool, rep: Report) -> None:
    overlay = plugin_dir / ".codex-plugin" / "plugin.json"
    where = str(overlay.relative_to(REPO_ROOT))
    if not overlay.exists():
        rep.err(where, "missing Codex overlay")
    else:
        try:
            cx = load_json(overlay)
        except json.JSONDecodeError:
            cx = None
        if cx is not None:
            if cx.get("name") != name:
                rep.err(where, f"name {cx.get('name')!r} != plugin name {name!r}")
            for key in ("skills", "mcpServers", "hooks"):
                ref = cx.get(key)
                if ref and not (plugin_dir / ref).exists():
                    rep.err(where, f"'{key}' points to missing path {ref}")
            interface = cx.get("interface", {})
            for key in ("displayName", "shortDescription", "developerName", "category"):
                if not interface.get(key):
                    rep.err(where, f"interface.{key} missing")
    if not is_agent:
        return
    toml_path = plugin_dir / "codex" / "agents" / f"{name}.toml"
    where = str(toml_path.relative_to(REPO_ROOT))
    if not toml_path.exists():
        rep.err(where, "missing Codex custom agent (re-run the sync)")
        return
    try:
        data = tomllib.loads(toml_path.read_text())
    except tomllib.TOMLDecodeError as exc:
        rep.err(where, f"invalid TOML: {exc}")
        return
    for key in sorted(CODEX_AGENT_KEYS - set(data)):
        rep.err(where, f"missing required key '{key}'")
    if data.get("name") != name:
        rep.err(where, f"name {data.get('name')!r} != plugin name {name!r}")


def check_codex_marketplace(claude_entries: list[dict], rep: Report) -> None:
    where = str(CODEX_MARKETPLACE_PATH.relative_to(REPO_ROOT))
    stale = REPO_ROOT / ".codex-plugin" / "marketplace.json"
    if stale.exists():
        rep.err(str(stale.relative_to(REPO_ROOT)), f"Codex does not read this file; use {where}")
    if not CODEX_MARKETPLACE_PATH.exists():
        rep.err(where, "missing Codex marketplace")
        return
    try:
        mp = load_json(CODEX_MARKETPLACE_PATH)
    except json.JSONDecodeError:
        rep.err(where, "invalid JSON")
        return
    if not mp.get("name"):
        rep.err(where, "missing 'name'")
    entries = {e.get("name"): e for e in mp.get("plugins", [])}
    for ce in claude_entries:
        name, source = ce.get("name"), ce.get("source")
        if not isinstance(source, str):
            continue
        e = entries.get(name)
        if e is None:
            rep.err(where, f"plugin '{name}' is in .claude-plugin/marketplace.json but not here")
            continue
        src = e.get("source", {})
        if src.get("source") != "local" or src.get("path") != source:
            rep.err(where, f"'{name}': source must be {{source: local, path: {source}}}")
        if not e.get("policy", {}).get("installation") or not e.get("category"):
            rep.err(where, f"'{name}': policy.installation and category are required")
    for name in sorted(set(entries) - {ce.get("name") for ce in claude_entries}):
        rep.err(where, f"plugin '{name}' is not in .claude-plugin/marketplace.json")


def connector_keys(plugin_dir: Path) -> set[str]:
    """Keys from the '## Connectors' table in CONNECTORS.md."""
    path = plugin_dir / "CONNECTORS.md"
    if not path.exists():
        return set()
    text = path.read_text()
    section = text.split("## Connectors", 1)[-1].split("\n### ", 1)[0]
    return set(CONNECTOR_ROW_RE.findall(section))


def load_servers(plugin_dir: Path, rep: Report) -> set[str]:
    mcp_path = plugin_dir / ".mcp.json"
    if not mcp_path.exists():
        return set()
    try:
        servers = load_json(mcp_path).get("mcpServers", {})
    except json.JSONDecodeError:
        return set()
    where = str(mcp_path.relative_to(REPO_ROOT))
    for sname, conf in servers.items():
        if isinstance(conf, dict) and "disabled" in conf:
            rep.err(where, f"server '{sname}' sets 'disabled', which Claude Code ignores for plugins; model it as a connector")
    return set(servers)


def check_commands(plugin_dir: Path, rep: Report) -> None:
    cmd_dir = plugin_dir / "commands"
    if not cmd_dir.is_dir():
        return
    for md in sorted(cmd_dir.glob("*.md")):
        if not parse_frontmatter(md.read_text()).get("description"):
            rep.err(str(md.relative_to(REPO_ROOT)), "missing frontmatter 'description'")


def check_vertical_plugin(plugin_dir: Path, name: str, skills: set[str], rep: Report) -> None:
    where = str(plugin_dir.relative_to(REPO_ROOT))
    if not skills:
        rep.err(where, "vertical plugins must bundle at least one skill")
    if (plugin_dir / "agents" / f"{name}.md").exists():
        rep.err(where, "vertical plugins attach to the main agent; move agents/<plugin>.md to an agent plugin")


def check_secondary_agents(plugin_dir: Path, primary: str | None, rep: Report) -> None:
    agents_dir = plugin_dir / "agents"
    if not agents_dir.is_dir():
        return
    for md in sorted(agents_dir.glob("*.md")):
        if md.stem == primary:
            continue
        fm = parse_frontmatter(md.read_text())
        where = str(md.relative_to(REPO_ROOT))
        if not fm.get("name"):
            rep.err(where, "missing frontmatter 'name'")
        if not fm.get("description"):
            rep.err(where, "missing frontmatter 'description'")


def check_agent_plugin(plugin_dir: Path, name: str, skills: set[str], rep: Report) -> None:
    agent_md = plugin_dir / "agents" / f"{name}.md"
    where = str(agent_md.relative_to(REPO_ROOT))
    if not agent_md.exists():
        rep.err(where, "primary agent definition missing (agent plugins need agents/<plugin>.md)")
        return
    text = agent_md.read_text()
    fm = parse_frontmatter(text)
    _, body = split_frontmatter(text)
    if fm.get("name") != name:
        rep.err(where, f"frontmatter name {fm.get('name')!r} != plugin name {name!r}")
    if not fm.get("description"):
        rep.err(where, "missing frontmatter 'description'")
    tools = parse_tools(fm.get("tools", ""))
    if not tools:
        rep.err(where, "missing frontmatter 'tools' allowlist")
    elif "Skill" not in tools and skills:
        rep.err(where, "'Skill' tool missing from tools; bundled skills cannot be invoked")
    for ignored in ("mcpServers", "hooks", "permissionMode"):
        if ignored in fm:
            rep.warn(where, f"'{ignored}' frontmatter is ignored for plugin agents; use plugin files")

    # MCP binding, both directions: plugin servers and user-added connectors.
    servers = load_servers(plugin_dir, rep)
    connectors = connector_keys(plugin_dir)
    prefix = f"mcp__plugin_{name}_"
    bound: set[str] = set()
    bound_connectors: set[str] = set()
    for tool in tools:
        if not tool.startswith("mcp__"):
            continue
        if tool.startswith(prefix) and tool.endswith("__*"):
            bound.add(tool[len(prefix):-3])
        elif tool.endswith("__*") and tool[5:-3] in connectors:
            bound_connectors.add(tool[5:-3])
        else:
            rep.err(
                where,
                f"tool {tool!r} is neither {mcp_tool_pattern(name, '<server>')} nor mcp__<key>__* for a CONNECTORS.md key",
            )
    for server in sorted(bound - servers):
        rep.err(where, f"tools bind MCP server '{server}' that is not defined in .mcp.json")
    for server in sorted(servers - bound):
        rep.err(where, f".mcp.json server '{server}' is not bound in tools ({mcp_tool_pattern(name, server)})")
    for key in sorted(connectors - bound_connectors):
        rep.err(where, f"CONNECTORS.md key '{key}' is not bound in tools (mcp__{key}__*)")

    # Skills listed in the body vs bundled skills, both directions.
    listed = skills_listed_in_agent(body)
    if skills and not listed:
        rep.err(where, "missing '## Skills this agent uses' section")
    dupes = {s for s in listed if listed.count(s) > 1}
    if dupes:
        rep.err(where, f"skills listed more than once: {sorted(dupes)}")
    for s in sorted(set(listed) - skills):
        rep.err(where, f"lists skill '{s}' that is not bundled under skills/")
    for s in sorted(skills - set(listed)):
        rep.err(where, f"bundled skill '{s}' is not listed under '## Skills this agent uses'")


def run_claude_validate(paths: list[Path], rep: Report) -> None:
    claude = shutil.which("claude")
    if not claude:
        rep.warn("claude", "`claude` CLI not found on PATH; skipping `claude plugin validate`")
        return
    for path in paths:
        proc = subprocess.run(
            [claude, "plugin", "validate", str(path)], capture_output=True, text=True, timeout=120
        )
        out = (proc.stdout + proc.stderr).strip()
        rel = str(path.relative_to(REPO_ROOT)) or "."
        if proc.returncode != 0:
            rep.err(f"claude plugin validate {rel}", out.splitlines()[-1] if out else "failed")
        elif "warning" in out.lower():
            rep.warn(f"claude plugin validate {rel}", " | ".join(out.splitlines()[-3:]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--claude", action="store_true", help="also run `claude plugin validate`")
    args = ap.parse_args()

    rep = Report()
    if not MARKETPLACE_PATH.exists():
        print(f"ERROR: {MARKETPLACE_PATH} not found")
        return 1
    market = load_json(MARKETPLACE_PATH)
    for key in ("name", "owner", "plugins"):
        if key not in market:
            rep.err(".claude-plugin/marketplace.json", f"missing '{key}'")

    seen: set[str] = set()
    plugin_dirs: list[Path] = []
    for entry in market.get("plugins", []):
        name = entry.get("name", "")
        where = f"marketplace[{name or '?'}]"
        if not NAME_RE.match(name):
            rep.err(where, "name must be kebab-case")
        if name in seen:
            rep.err(where, "duplicate plugin name")
        seen.add(name)
        source = entry.get("source")
        if not isinstance(source, str) or not source.startswith("./"):
            rep.warn(where, f"non-local source {source!r}; skipping on-disk checks")
            continue
        plugin_dir = (REPO_ROOT / source).resolve()
        if not plugin_dir.is_dir():
            rep.err(where, f"source {source} does not exist")
            continue
        plugin_dirs.append(plugin_dir)
        kind = plugin_dir.relative_to(REPO_ROOT / "plugins").parts[0] if "plugins" in plugin_dir.parts else ""
        if kind not in PLUGIN_KINDS:
            rep.err(where, f"plugin must live under plugins/{{{','.join(PLUGIN_KINDS)}}}/")
        manifest = plugin_dir / ".claude-plugin" / "plugin.json"
        if not manifest.exists():
            rep.err(where, "missing .claude-plugin/plugin.json")
            continue
        check_json_files(plugin_dir, rep)
        try:
            pj = load_json(manifest)
        except json.JSONDecodeError:
            continue
        if pj.get("name") != name:
            rep.err(where, f"plugin.json name {pj.get('name')!r} != marketplace name {name!r}")
        if plugin_dir.name != name:
            rep.err(where, f"directory name '{plugin_dir.name}' != plugin name '{name}'")
        for key in ("version", "description"):
            if not pj.get(key):
                rep.err(str(manifest.relative_to(REPO_ROOT)), f"missing '{key}'")
        skills = check_skills(plugin_dir, rep)
        check_hooks(plugin_dir, rep)
        check_commands(plugin_dir, rep)
        primary = name if kind == "agent-plugins" else None
        if primary:
            check_agent_plugin(plugin_dir, name, skills, rep)
        else:
            load_servers(plugin_dir, rep)
            if kind == "vertical-plugins":
                check_vertical_plugin(plugin_dir, name, skills, rep)
        check_secondary_agents(plugin_dir, primary, rep)
        if kind in PLUGIN_KINDS:
            check_portable(plugin_dir, pj, rep)
            check_codex(plugin_dir, name, kind == "agent-plugins", rep)

    check_codex_marketplace(market.get("plugins", []), rep)

    if args.claude:
        run_claude_validate([REPO_ROOT, *plugin_dirs], rep)

    for w in rep.warnings:
        print(f"WARN  {w}")
    for e in rep.errors:
        print(f"ERROR {e}")
    print(f"\n{len(plugin_dirs)} plugins checked: {len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
