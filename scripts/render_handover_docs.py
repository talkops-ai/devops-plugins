#!/usr/bin/env python3
"""Render the team handover / audit documents for agent and vertical plugins.

Writes, for every plugin in scripts/aws-plugin-map.json:

    docs/handover/agent-plugins.md
    docs/handover/vertical-plugins.md

Facts (skills and their provenance, agent definitions, MCP launch configs,
connectors, hooks, rewrites, commands) are computed from the map and the
synced plugin directories. Rationale and known gaps come from
scripts/handover-notes.json. Automated findings flag things an auditor should
look at; they are hints, not failures (scripts/validate_plugins.py is the gate).

Run after a sync:

    python3 scripts/sync_aws_plugins.py && python3 scripts/render_handover_docs.py
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _plugin_lib import (  # noqa: E402
    REPO_ROOT,
    first_sentence,
    load_json,
    mcp_tool_pattern,
    parse_frontmatter,
    parse_tools,
    skills_listed_in_agent,
    split_frontmatter,
)
from sync_aws_plugins import (  # noqa: E402
    KIND_ROOTS,
    MAP_PATH,
    SyncError,
    kind_of,
    merge_hooks,
    mcp_notes,
    resolve_connectors,
    resolve_mcp,
    resolve_rewrites,
    skills_root,
)

NOTES_PATH = REPO_ROOT / "scripts" / "handover-notes.json"
OUT_DIR = REPO_ROOT / "docs" / "handover"
OUT_FILES = {"agent": OUT_DIR / "agent-plugins.md", "vertical": OUT_DIR / "vertical-plugins.md"}
WRITE_FLAGS = (
    "--allow-write",
    "--allow-sensitive-data-access",
    "--allow_write_query",
    "--allow-resource-creation",
    "--enable-aws-resource-write",
    "--allow-writes",
)
VERBATIM_AGENT_SECTIONS = ("What you produce", "Hand-offs", "Guardrails")
SAFETY_PHRASES = (
    "approval", "approve", "read-only", "do not create", "confirm before", "wait for",
    "ask before", "only if the user asks",
)


# --------------------------------------------------------------------------- helpers


def rel(path: Path) -> str:
    """Link target relative to docs/handover/."""
    return "../../" + path.relative_to(REPO_ROOT).as_posix()


def esc(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def short(text: str, limit: int) -> str:
    text = esc(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def git_head(path: Path) -> str:
    try:
        sha = subprocess.run(
            ["git", "-C", str(path), "log", "-1", "--format=%h (%cs)"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return sha or "unknown"
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def dir_hash(path: Path) -> str:
    h = hashlib.sha1()
    for f in sorted(p for p in path.rglob("*") if p.is_file()):
        h.update(f.relative_to(path).as_posix().encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:10]


def anchor(name: str) -> str:
    return re.sub(r"[^a-z0-9 -]", "", name.lower()).replace(" ", "-")


def upstream_url(cfg: dict, ref: str, skill: str | None = None) -> str:
    key, _, plugin = ref.partition("/")
    src = cfg["sources"][key]
    repo_rel = "/".join(Path(src["path"]).parts[2:])  # drop reference/<repo>
    url = f"{src['upstream']}/tree/main/{repo_rel}/{plugin}"
    if skill:
        url += f"/{skill}" if src.get("flat") else f"/skills/{skill}"
    return url


def launch_line(conf: dict) -> str:
    if conf.get("url"):
        return f"{conf.get('type', 'http')} {conf['url']}"
    return " ".join([conf.get("command", "")] + conf.get("args", []))


def server_mode(conf: dict, note: str) -> list[str]:
    """Human-readable safety/repro flags for one resolved MCP server config."""
    flags: list[str] = []
    args = conf.get("args", [])
    writes = [a for a in args if a in WRITE_FLAGS]
    env = conf.get("env", {})
    writes += [f"{k}={v}" for k, v in env.items() if k.startswith("ALLOW_") and str(v).lower() == "true"]
    if writes:
        flags.append("⚠️ write-enabled (" + ", ".join(f"`{w}`" for w in writes) + ")")
    elif "no read-only mode" in note.lower():
        flags.append("⚠️ no read-only mode")
    elif "aws-mcp." in launch_line(conf):
        flags.append("any AWS API call, bounded by IAM")
    else:
        flags.append("no write flags")
    blob = launch_line(conf)
    if "@latest" in blob:
        flags.append("unpinned `@latest`")
    elif re.search(r"==\d", blob):
        flags.append("pinned")
    if "us-east-1" in re.sub(r"\$\{[^}]*\}", "", blob):
        flags.append("region hard-coded `us-east-1`")
    if any("${" in str(v) for v in list(env.values()) + list(conf.get("headers", {}).values())):
        needed = sorted(set(re.findall(r"\$\{([A-Z0-9_]+)", str(env) + str(conf.get("headers", {})) + blob)))
        needed = [n for n in needed if n != "AWS_REGION"]
        if needed:
            flags.append("needs env " + ", ".join(f"`{n}`" for n in needed))
    return flags


def md_sections(path: Path) -> list[tuple[str, int, int, str]]:
    """(heading, start_line, end_line, body) for each '## ' section, 1-based lines."""
    lines = path.read_text(errors="ignore").splitlines()
    heads = [i for i, line in enumerate(lines) if line.startswith("## ")]
    out = []
    for n, i in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(lines)
        body = "\n".join(lines[i + 1:end]).strip("\n")
        out.append((lines[i][3:].strip(), i + 1, end, body))
    return out


def quote(body: str) -> list[str]:
    return [("> " + line).rstrip() for line in body.strip().splitlines()] + [""]


# --------------------------------------------------------------------------- model


class Plugin:
    def __init__(self, cfg: dict, spec: dict):
        self.cfg = cfg
        self.spec = spec
        self.name = spec["name"]
        self.kind = kind_of(spec)
        self.dir = KIND_ROOTS[self.kind] / self.name
        self.servers = resolve_mcp(cfg, spec.get("mcp", []))
        self.notes = mcp_notes(cfg, spec.get("mcp", []))
        self.connectors = resolve_connectors(cfg, spec)
        self.hook_events, self.hook_files, hook_rw = merge_hooks(cfg, spec)
        self.rewrites = [(rw, "hook") for rw in hook_rw]
        for entry in spec.get("rewrites", []):
            tag = entry if isinstance(entry, str) else "inline"
            self.rewrites += [(rw, tag) for rw in resolve_rewrites(cfg, [entry])]
        self.all_dirs = self._skills()
        self.skills = [s for s in self.all_dirs if s["exists"]]
        self.support_dirs = [s for s in self.all_dirs if not s["exists"]]
        self.findings: list[str] = []

    def _skills(self) -> list[dict]:
        rows = []
        for spec in self.spec["skills"]:
            src = skills_root(self.cfg, spec["from"])
            names = spec["names"]
            chosen = sorted(p.name for p in src.iterdir() if p.is_dir()) if names == "*" else names
            for skill in chosen:
                if skill in spec.get("except", []):
                    continue
                local = self.dir / "skills" / skill
                skill_md = local / "SKILL.md"
                fm = parse_frontmatter(skill_md.read_text(errors="ignore")) if skill_md.is_file() else {}
                rows.append({
                    "name": skill,
                    "from": spec["from"],
                    "wildcard": names == "*",
                    "local": local,
                    "exists": skill_md.is_file(),
                    "fm_name": fm.get("name", ""),
                    "desc": fm.get("description", ""),
                    "files": sum(1 for p in local.rglob("*") if p.is_file()) if local.is_dir() else 0,
                    "hash": dir_hash(local) if local.is_dir() else "",
                    "upstream": upstream_url(self.cfg, spec["from"], skill),
                })
        return rows

    @property
    def excluded(self) -> list[tuple[str, str]]:
        return [(x, s["from"]) for s in self.spec["skills"] for x in s.get("except", [])]


# --------------------------------------------------------------------------- analysis


def analyse(plugins: list[Plugin]) -> dict:
    by_skill: dict[str, list[Plugin]] = {}
    for p in plugins:
        for s in p.skills:
            by_skill.setdefault(s["name"], []).append(p)
    names = {p.name for p in plugins}
    all_skills = set(by_skill)
    all_servers = {k for p in plugins for k in p.servers} | {k for p in plugins for k in p.connectors}

    for p in plugins:
        f = p.findings
        for s in p.support_dirs:
            if not any(s["local"].rglob("*")):
                f.append(f"Mapped skill directory `{s['name']}` is empty (re-run the sync).")
        rewritten = lambda q, n: any(rw["path"].startswith(f"skills/{n}/") for rw, _ in q.rewrites)  # noqa: E731
        for s in p.skills:
            if s["fm_name"] and s["fm_name"] != s["name"]:
                f.append(f"Skill `{s['name']}` declares frontmatter name `{s['fm_name']}`.")
            if not s["desc"]:
                f.append(f"Skill `{s['name']}` has no description, so it cannot auto-activate.")
            peers = {}
            for q in by_skill[s["name"]]:
                x = next(x for x in q.skills if x["name"] == s["name"])
                peers[q.name] = (x["hash"], x["from"], rewritten(q, s["name"]))
            if len({h for h, _, _ in peers.values()}) > 1:
                others = sorted(n for n, (h, _, _) in peers.items() if h != s["hash"])
                sources = {src for _, src, _ in peers.values()}
                if len(sources) > 1:
                    s["variant"] = "upstream variant differs"
                    f.append(
                        f"Skill `{s['name']}` comes from a different upstream source than in "
                        + ", ".join(f"`{o}`" for o in others) + "; confirm the variant choice."
                    )
                elif any(r for _, _, r in peers.values()):
                    s["variant"] = "plugin-specific rewrite"
                else:
                    s["variant"] = "stale copy"
                    f.append(
                        f"Skill `{s['name']}` differs from the copy in " + ", ".join(f"`{o}`" for o in others)
                        + " although both use the same source and no rewrite; re-run the sync."
                    )
        for sname, conf in p.servers.items():
            for flag in server_mode(conf, p.notes.get(sname, "")):
                if flag.startswith("⚠️"):
                    f.append(f"MCP `{sname}`: {flag[2:].strip()}.")
        if p.kind == "agent":
            analyse_agent(p, names, all_skills)
        else:
            analyse_vertical(p, all_skills, all_servers)
    return {"by_skill": by_skill}


def analyse_agent(p: Plugin, names: set[str], all_skills: set[str]) -> None:
    f = p.findings
    agent_md = p.dir / "agents" / f"{p.name}.md"
    p.agent_md = agent_md
    if not agent_md.is_file():
        f.append("Primary agent file is missing.")
        p.agent_fm, p.agent_sections, p.handoffs = {}, [], []
        return
    text = agent_md.read_text(errors="ignore")
    p.agent_fm = parse_frontmatter(text)
    _, body = split_frontmatter(text)
    p.agent_sections = md_sections(agent_md)
    heads = {h for h, *_ in p.agent_sections}
    for req in ("What you produce", "Workflow", "MCP servers bound to this agent", "Hand-offs",
                "Skills this agent uses", "Guardrails"):
        if req not in heads:
            f.append(f"Agent file has no `## {req}` section.")
    if p.agent_fm.get("name") != p.name:
        f.append(f"Agent frontmatter name is `{p.agent_fm.get('name')}`, expected `{p.name}`.")

    listed = set(skills_listed_in_agent(body))
    bundled = {s["name"] for s in p.skills}
    p.unlisted = sorted(bundled - listed)
    p.phantom = sorted(listed - bundled)
    if p.unlisted:
        f.append("Bundled but not listed in *Skills this agent uses*: " + ", ".join(f"`{s}`" for s in p.unlisted) + ".")
    if p.phantom:
        f.append("Listed in *Skills this agent uses* but not bundled: " + ", ".join(f"`{s}`" for s in p.phantom) + ".")

    tools = parse_tools(p.agent_fm.get("tools", ""))
    p.builtin_tools = [t for t in tools if not t.startswith("mcp__")]
    p.mcp_tools = [t for t in tools if t.startswith("mcp__")]
    expected = {mcp_tool_pattern(p.name, s) for s in p.servers} | {f"mcp__{k}__*" for k in p.connectors}
    for t in sorted(expected - set(p.mcp_tools)):
        f.append(f"`tools:` does not allowlist `{t}`, so the agent cannot use that server.")
    for t in sorted(set(p.mcp_tools) - expected):
        f.append(f"`tools:` allowlists `{t}`, which no bundled server or connector provides.")

    handoff_body = next((b for h, _, _, b in p.agent_sections if h == "Hand-offs"), "")
    refs = re.findall(r"`(aws-[a-z0-9-]+)`", handoff_body)
    p.handoffs = sorted({r for r in refs if r in names})
    unknown = sorted({r for r in refs if r not in names and r not in all_skills})
    if unknown:
        f.append("Hand-offs reference unknown plugin(s): " + ", ".join(f"`{u}`" for u in unknown) + ".")
    if p.name in p.handoffs:
        f.append("Agent hands off to itself.")


def analyse_vertical(p: Plugin, all_skills: set[str], all_servers: set[str]) -> None:
    f = p.findings
    bundled = {s["name"] for s in p.skills}
    local_servers = set(p.servers) | set(p.connectors)
    p.commands = []
    for cmd in sorted((p.dir / "commands").glob("*.md")):
        text = cmd.read_text(errors="ignore")
        fm = parse_frontmatter(text)
        _, body = split_frontmatter(text)
        ticks = set(re.findall(r"`([a-z0-9][a-z0-9-]*)`", body))
        skills = sorted(ticks & bundled)
        servers = sorted(ticks & local_servers)
        missing = sorted((ticks & (all_skills | all_servers)) - bundled - local_servers)
        gated = any(ph in body.lower() for ph in SAFETY_PHRASES)
        p.commands.append({"path": cmd, "fm": fm, "skills": skills, "servers": servers, "gated": gated})
        if not skills and not servers:
            f.append(f"Command `/{p.name}:{cmd.stem}` names neither a bundled skill nor a bundled MCP server.")
        if missing:
            f.append(
                f"Command `/{p.name}:{cmd.stem}` references " + ", ".join(f"`{m}`" for m in missing)
                + ", which this plugin does not bundle."
            )
        if not gated:
            f.append(f"Command `/{p.name}:{cmd.stem}` has no explicit read-only statement or approval gate.")
        if not fm.get("description"):
            f.append(f"Command `/{p.name}:{cmd.stem}` has no description.")
    if not p.commands:
        f.append("No hand-authored commands.")
    for a in p.spec.get("agents", []):
        if not (KIND_ROOTS["agent"] / a).is_dir():
            f.append(f"Related agent `{a}` does not exist.")


# --------------------------------------------------------------------------- rendering


def render_header(cfg: dict, notes: dict, kind: str, plugins: list[Plugin]) -> list[str]:
    title = "Agent plugins" if kind == "agent" else "Vertical plugins"
    other = "vertical-plugins.md" if kind == "agent" else "agent-plugins.md"
    total_skills = sum(len(p.skills) for p in plugins)
    total_findings = sum(len(p.findings) for p in plugins)
    lines = [
        "<!-- Generated by scripts/render_handover_docs.py from scripts/aws-plugin-map.json, "
        "scripts/handover-notes.json, and the synced plugins. Do not edit by hand; re-run the renderer. -->\n",
        f"# Handover: {title}\n",
        f"Audit handbook for the **{len(plugins)} {title.lower()}** in the `{cfg['marketplace']['name']}` marketplace "
        f"({total_skills} skill copies, {total_findings} automated findings). Companion document: [{other}](./{other}). "
        "MCP server usage across both kinds: [mcp-server-coverage.md](../mcp-server-coverage.md).\n",
        f"Generated {_dt.date.today().isoformat()}.\n",
        "## How to audit\n",
        "1. Read *How this plugin kind works* and *Cross-cutting decisions* once.",
        "2. For each plugin, work through its section: identity, "
        + ("agent definition, " if kind == "agent" else "commands, related agents, ")
        + "skills and provenance, MCP servers, connectors, hooks, rewrites, design notes, and automated findings.",
        "3. Tick the plugin's audit checklist. Record each finding as an issue or PR that names the plugin.",
        "4. Fix at the source, never in generated files (see *Where to make changes*), then run "
        "`python3 scripts/sync_aws_plugins.py && python3 scripts/validate_plugins.py --claude && "
        "python3 scripts/render_handover_docs.py`.\n",
        "> [!NOTE]",
        "> *Automated findings* are computed hints, such as write-enabled servers, skills that differ between "
        "plugins, or commands without a safety gate. They are not validation errors; `scripts/validate_plugins.py` "
        "is the gate and currently passes. Each finding needs a human decision: accept and document, or fix.\n",
    ]
    return lines


def render_model(cfg: dict, kind: str) -> list[str]:
    lines = ["## How this plugin kind works\n"]
    if kind == "agent":
        lines += [
            "An **agent plugin** packages one specialist. Its primary agent (`agents/<name>.md`) is spawned as a "
            "dynamic sub-agent; every skill, command, hook, and MCP server in the plugin is reached through it. "
            "The agent's `tools:` frontmatter is the binding for MCP: only allowlisted servers are usable.\n",
            "- Invoke: `@agent-<name>:<name>`, or let Claude delegate from the agent description.",
            "- Headless: `claude --agent <name>:<name>`.\n",
            "```text",
            "plugins/agent-plugins/<name>/",
            "├── .claude-plugin/plugin.json   generated",
            "├── .mcp.json                    generated (bundled MCP servers)",
            "├── agents/<name>.md             HAND-AUTHORED (primary agent); other agents/*.md are upstream workers",
            "├── skills/<skill>/SKILL.md      copied from upstream",
            "├── commands/ scripts/ ...       copied from upstream when mapped",
            "├── hooks/hooks.json             generated from hooks_catalog / hooks_inline",
            "├── CONNECTORS.md                generated when the plugin has connectors",
            "└── README.md                    generated",
            "```\n",
        ]
    else:
        lines += [
            "A **vertical plugin** attaches its skills, commands, hooks, and MCP servers directly to the user's "
            "main agent. There is no sub-agent hand-off and no tool allowlist: every bundled server is available "
            "once the plugin is enabled, which is why read-only defaults matter more here.\n",
            "- Install: `claude plugin install <name>@" + cfg["marketplace"]["name"] + "`.",
            "- Skills activate from their descriptions; invoke explicitly with `/<name>:<skill>`; commands are "
            "`/<name>:<command>`.\n",
            "```text",
            "plugins/vertical-plugins/<name>/",
            "├── .claude-plugin/plugin.json   generated",
            "├── .mcp.json                    generated (bundled MCP servers)",
            "├── commands/*.md                HAND-AUTHORED",
            "├── skills/<skill>/SKILL.md      copied from upstream",
            "├── scripts/ ...                 copied from upstream when mapped",
            "├── hooks/hooks.json             generated when hooks are mapped",
            "├── CONNECTORS.md                generated when the plugin has connectors",
            "└── README.md                    generated",
            "```\n",
        ]
    lines += [
        "### Where to make changes\n",
        "| To change | Edit | Then |",
        "|---|---|---|",
        "| Which skills, MCP servers, connectors, hooks, or rewrites a plugin gets | "
        "[`scripts/aws-plugin-map.json`](../../scripts/aws-plugin-map.json) | sync, validate, render |",
        "| An MCP server's launch config (shared) | `mcp_catalog` in the map | sync, validate, render |",
        "| A connector's install instructions | `connector_catalog` in the map | sync, validate, render |",
    ]
    if kind == "agent":
        lines.append("| The agent's prompt, tools allowlist, workflow, hand-offs, guardrails | `plugins/agent-plugins/<name>/agents/<name>.md` | validate, render |")
    else:
        lines.append("| A slash command | `plugins/vertical-plugins/<name>/commands/<command>.md` | validate, render |")
    lines += [
        "| Rationale, known gaps in this document | [`scripts/handover-notes.json`](../../scripts/handover-notes.json) | render |",
        "| Skill content itself | Upstream repository (then pull and re-sync), or a rewrite in the map | sync, validate, render |",
        "",
    ]
    return lines


def render_sources(cfg: dict) -> list[str]:
    lines = [
        "## Sources\n",
        "| Key | Local path (gitignored) | Upstream | Commit at render time |",
        "|---|---|---|---|",
    ]
    for key, src in cfg["sources"].items():
        repo = REPO_ROOT / Path(*Path(src["path"]).parts[:2])
        lines.append(f"| `{key}` | `{src['path']}` | {src['upstream']} | `{git_head(repo)}` |")
    idx = cfg.get("mcp_upstream_index", {})
    if idx:
        lines.append(f"| MCP servers | `{idx['path']}` | {idx['upstream']} | `{git_head(REPO_ROOT / Path(*Path(idx['path']).parts[:2]))}` |")
    lines.append("")
    return lines


def render_bullets(title: str, items: list[str]) -> list[str]:
    return [f"## {title}\n", *[f"- {i}" for i in items], ""] if items else []


def render_summary(kind: str, plugins: list[Plugin]) -> list[str]:
    if kind == "agent":
        head = "| Plugin | Category | Skills | Commands | Workers | MCP | Connectors | Hooks | Hands off to | Findings |"
    else:
        head = "| Plugin | Category | Skills | Commands | MCP | Connectors | Hooks | Agent alternative | Findings |"
    lines = ["## Plugin summary\n", head, "|" + "---|" * (head.count("|") - 1)]
    for p in plugins:
        cmds = len(list((p.dir / "commands").glob("*.md")))
        hooks = ", ".join(p.spec.get("hooks", []) + (["inline"] if p.spec.get("hooks_inline") else [])) or "—"
        link = f"[`{p.name}`](#{anchor(p.name)})"
        if kind == "agent":
            workers = len([w for w in (p.dir / "agents").glob("*.md") if w.stem != p.name])
            lines.append(
                f"| {link} | {p.spec['category']} | {len(p.skills)} | {cmds} | {workers} | {len(p.servers)} | "
                f"{len(p.connectors)} | {hooks} | {', '.join(p.handoffs) or '—'} | {len(p.findings)} |"
            )
        else:
            alt = ", ".join(p.spec.get("agents", [])) or "—"
            lines.append(
                f"| {link} | {p.spec['category']} | {len(p.skills)} | {cmds} | {len(p.servers)} | "
                f"{len(p.connectors)} | {hooks} | {alt} | {len(p.findings)} |"
            )
    lines.append("")
    if kind == "agent":
        lines += ["### Hand-off graph\n", "```mermaid", "flowchart LR"]
        for p in plugins:
            for h in p.handoffs:
                lines.append(f"  {p.name.replace('-', '_')}[\"{p.name}\"] --> {h.replace('-', '_')}[\"{h}\"]")
        lines += ["```", ""]
        inbound = {h for p in plugins for h in p.handoffs}
        orphans = [p.name for p in plugins if p.name not in inbound]
        if orphans:
            lines.append(
                "No agent hands off to: " + ", ".join(f"`{o}`" for o in orphans)
                + ". They are reached only by direct invocation or Claude's delegation from their description.\n"
            )
    return lines


def render_catalog(cfg: dict, plugins: list[Plugin], kind: str) -> list[str]:
    catalog = {k: resolve_mcp(cfg, [k])[k] for k in cfg["mcp_catalog"]}
    used: dict[str, list[str]] = {}
    configs: dict[str, tuple[dict, str, str, str]] = {}
    for p in plugins:
        for sname, conf in p.servers.items():
            key = sname if catalog.get(sname) == conf else next((k for k, v in catalog.items() if v == conf), None)
            if key == sname:
                label, shown = sname, f"`{sname}`"
            elif key:
                label, shown = f"{sname}->{key}", f"`{sname}` (catalog `{key}`)"
            else:
                label, shown, key = f"{sname}@{p.name}", f"`{sname}` (inline in `{p.name}`)", sname
            used.setdefault(label, []).append(p.name)
            configs[label] = (conf, p.notes.get(sname, ""), key, shown)
    index = {}
    for d, info in cfg["mcp_upstream_index"]["servers"].items():
        if info.get("key"):
            index[info["key"]] = d
    lines = [
        "## MCP servers used by these plugins\n",
        "Every distinct launch configuration, once. Plugin sections refer back here.\n",
        "| Server | Upstream | Launch | Env | Mode | Used by |",
        "|---|---|---|---|---|---|",
    ]
    for label in sorted(used):
        conf, note, key, shown = configs[label]
        up = index.get(key, "—")
        env = "<br>".join(f"`{k}={v}`" for k, v in conf.get("env", {}).items()) or "—"
        mode = "<br>".join(server_mode(conf, note))
        users = ", ".join(f"[`{u}`](#{anchor(u)})" for u in used[label])
        lines.append(f"| {shown} | `{up}` | `{esc(launch_line(conf))}` | {env} | {mode} | {users} |")
    lines.append("")
    conns = sorted({k for p in plugins for k in p.connectors})
    if conns:
        cat = cfg["connector_catalog"]
        lines += ["### Connectors\n", "| Key | Package | Purpose | Used by |", "|---|---|---|---|"]
        for k in conns:
            c = cat[k]
            users = ", ".join(f"[`{p.name}`](#{anchor(p.name)})" for p in plugins if k in p.connectors)
            lines.append(f"| `{k}` | [`{c['package']}`]({c['docs']}) | {esc(c['purpose'])} | {users} |")
        lines.append("")
    hooks = sorted({h for p in plugins for h in p.spec.get("hooks", [])})
    if hooks:
        lines += ["### Hook templates\n", "| Template | Event | Matcher | Action | Files copied | Used by |", "|---|---|---|---|---|---|"]
        for h in hooks:
            tpl = cfg["hooks_catalog"][h]
            users = ", ".join(f"[`{p.name}`](#{anchor(p.name)})" for p in plugins if h in p.spec.get("hooks", []))
            files = "<br>".join(f"`{s}` → `{d}`" for s, d in tpl.get("files", {}).items()) or "—"
            for ev, items in tpl["hooks"].items():
                for it in items:
                    for hk in it.get("hooks", []):
                        action = hk.get("command") or hk.get("prompt", "")
                        lines.append(
                            f"| `{h}` | {ev} | `{esc(it.get('matcher', '*'))}` | {hk['type']}: {short(action, 140)} | {files} | {users} |"
                        )
        lines.append("")
    rws = sorted({t for p in plugins for _, t in p.rewrites if t not in ("hook", "inline")})
    if rws:
        lines += ["### Rewrite templates\n", "| Template | File | Find | Replace |", "|---|---|---|---|"]
        for t in rws:
            for rw in cfg["rewrites_catalog"][t]:
                lines.append(f"| `{t}` | `{rw['path']}` | {short(rw['find'], 110)} | {short(rw['replace'], 110)} |")
        lines.append("")
    return lines


def render_plugin(cfg: dict, notes: dict, p: Plugin, ctx: dict) -> list[str]:
    s = p.spec
    lines = [f"## {p.name}\n", f"**{s['displayName']}**: {esc(s['description'])}\n"]
    lines += [
        "### Identity\n",
        "| Field | Value |",
        "|---|---|",
        f"| Path | [`{p.dir.relative_to(REPO_ROOT).as_posix()}/`]({rel(p.dir)}) |",
        f"| Kind / category | {p.kind} / `{s['category']}` |",
        f"| Version | `{s.get('version', cfg['defaults']['version'])}` |",
        f"| Keywords | {', '.join(f'`{k}`' for k in s.get('keywords', []))} |",
        f"| Install | `claude plugin install {p.name}@{cfg['marketplace']['name']}` |",
        f"| Generated README | [README.md]({rel(p.dir / 'README.md')}) |",
    ]
    if p.kind == "vertical":
        alts = s.get("agents", [])
        lines.append(
            "| Agent alternative | "
            + (", ".join(f"[`{a}`](./agent-plugins.md#{anchor(a)})" for a in alts) or "none (vertical only)")
            + " |"
        )
    lines.append("")

    lines += ["### Upstream sources\n"]
    for up in s.get("upstream", []):
        ref = f"{up['source']}/{up['plugin']}"
        lines.append(f"- `{ref}`: {upstream_url(cfg, ref)}")
    for c in s.get("copy", []):
        paths = c["paths"]
        mapping = paths.items() if isinstance(paths, dict) else ((x, x) for x in paths)
        for src, dst in mapping:
            lines.append(f"- Extra copy: `{c['from']}/{src}` → `{dst}`")
    lines.append("")

    if p.kind == "agent":
        lines += render_agent(p)
    else:
        lines += render_vertical_commands(p, ctx)

    lines += [f"### Skills ({len(p.skills)})\n"]
    lines += ["| Skill | Source | Files | Also in | What it does |", "|---|---|---|---|---|"]
    for sk in p.skills:
        peers = [q.name for q in ctx["by_skill"][sk["name"]] if q.name != p.name]
        doc = "agent-plugins.md" if p.kind == "vertical" else "vertical-plugins.md"
        also = []
        for q in peers:
            qkind = next(x.kind for x in ctx["by_skill"][sk["name"]] if x.name == q)
            also.append(f"[`{q}`](#{anchor(q)})" if qkind == p.kind else f"[`{q}`](./{doc}#{anchor(q)})")
        src = f"[`{sk['from']}`]({sk['upstream']})" + (" (`*`)" if sk["wildcard"] else "")
        also_txt = ", ".join(also) or "—"
        if sk.get("variant"):
            also_txt += f" ({sk['variant']})"
        lines.append(
            f"| [`{sk['name']}`]({rel(sk['local'] / 'SKILL.md')}) | {src} | {sk['files']} | "
            f"{also_txt} | {short(first_sentence(sk['desc'], 400), 200)} |"
        )
    lines.append("")
    lines.append(
        "*Also in* lists other plugins bundling a skill with the same name; a note in parentheses means the "
        "copies differ and why.\n"
    )
    if p.support_dirs:
        lines.append(
            "Support directories copied with the skills (no `SKILL.md`; shared by other skills): "
            + ", ".join(f"[`{s['name']}/`]({rel(s['local'])}) ({s['files']} files)" for s in p.support_dirs)
            + ".\n"
        )
    if p.excluded:
        lines.append("Excluded from wildcard sources: " + ", ".join(f"`{x}` (from `{f}`)" for x, f in p.excluded) + ".\n")

    if p.servers:
        lines += ["### MCP servers\n"]
        col = " Allowlisted |" if p.kind == "agent" else ""
        lines += [f"| Server | Launch | Mode | Tool names |{col} Notes |", "|---|---|---|---|" + ("---|" if col else "") + "---|"]
        tools = set(getattr(p, "mcp_tools", []))
        for sname, conf in p.servers.items():
            pattern = mcp_tool_pattern(p.name, sname)
            allow = (" ✅ |" if pattern in tools else " ❌ |") if p.kind == "agent" else ""
            lines.append(
                f"| `{sname}` | `{esc(launch_line(conf))}` | {'<br>'.join(server_mode(conf, p.notes.get(sname, '')))} | "
                f"`{pattern}` |{allow} {esc(p.notes.get(sname, '')) or '—'} |"
            )
        lines.append("")
    else:
        lines += ["### MCP servers\n", "None bundled.\n"]

    if p.connectors:
        lines += [
            "### Connectors\n",
            f"User-added servers documented in [CONNECTORS.md]({rel(p.dir / 'CONNECTORS.md')}); tool names are `mcp__<key>__*`.\n",
            "| Key | Package | Purpose |",
            "|---|---|---|",
        ]
        for k, c in p.connectors.items():
            lines.append(f"| `{k}` | [`{c['package']}`]({c['docs']}) | {esc(c['purpose'])} |")
        lines.append("")

    if p.hook_events:
        lines += ["### Hooks\n", "| Event | Matcher | Type | Action | Origin |", "|---|---|---|---|---|"]
        origins = []
        for name in s.get("hooks", []):
            for ev, items in cfg["hooks_catalog"][name]["hooks"].items():
                origins += [(ev, it, name) for it in items]
        for ev, items in s.get("hooks_inline", {}).items():
            origins += [(ev, it, "inline") for it in items]
        for ev, it, origin in origins:
            for hk in it.get("hooks", []):
                action = hk.get("command") or hk.get("prompt", "")
                lines.append(f"| {ev} | `{esc(it.get('matcher', '*'))}` | {hk['type']} | {short(action, 160)} | `{origin}` |")
        if p.hook_files:
            lines.append("")
            lines.append("Hook files: " + ", ".join(f"`{d}` (from `{src}`)" for src, d in p.hook_files) + ".")
        lines.append("")

    if p.rewrites:
        lines += ["### Rewrites applied to upstream files\n", "| File | Find | Replace | Origin |", "|---|---|---|---|"]
        for rw, tag in p.rewrites:
            lines.append(f"| `{rw['path']}` | {short(rw['find'], 100)} | {short(rw['replace'], 100)} | `{tag}` |")
        lines.append("")

    design = notes["plugins"].get(p.name, [])
    lines += ["### Design notes\n", *([f"- {d}" for d in design] or ["- _No notes recorded. Add them to `scripts/handover-notes.json`._"]), ""]

    lines += ["### Automated findings\n"]
    lines += [f"- {x}" for x in p.findings] if p.findings else ["- None."]
    lines.append("")

    lines += ["### Audit checklist\n"]
    lines += [f"- [ ] {c}" for c in checklist(p)]
    lines += ["", "---", ""]
    return lines


def render_agent(p: Plugin) -> list[str]:
    if not getattr(p, "agent_fm", None):
        return ["### Agent definition\n", "⚠️ Missing.\n"]
    fm = p.agent_fm
    lines = [
        "### Agent definition\n",
        f"File: [`agents/{p.name}.md`]({rel(p.agent_md)}) (hand-authored).\n",
        "| Field | Value |",
        "|---|---|",
        f"| `name` | `{fm.get('name', '')}` |",
        f"| `description` (delegation trigger) | {esc(fm.get('description', ''))} |",
        f"| Built-in tools | {', '.join(f'`{t}`' for t in p.builtin_tools) or '—'} |",
        f"| MCP tools | {'<br>'.join(f'`{t}`' for t in p.mcp_tools) or '—'} |",
    ]
    for k in ("model", "color"):
        if fm.get(k):
            lines.append(f"| `{k}` | `{fm[k]}` |")
    lines += [f"| Hands off to | {', '.join(f'[`{h}`](#{anchor(h)})' for h in p.handoffs) or '—'} |", ""]
    lines += ["Sections (click to open at the line range):\n"]
    for head, start, end, _ in p.agent_sections:
        lines.append(f"- [{head}]({rel(p.agent_md)}#L{start}-L{end})")
    lines.append("")
    for head, _, _, body in p.agent_sections:
        if head in VERBATIM_AGENT_SECTIONS:
            lines += [f"**{head}** (verbatim):\n", *quote(body)]
    workers = sorted(w for w in (p.dir / "agents").glob("*.md") if w.stem != p.name)
    if workers:
        lines += ["**Worker agents** (copied from upstream, dispatched by skills):\n", "| Agent | Tools | Description |", "|---|---|---|"]
        for w in workers:
            wfm = parse_frontmatter(w.read_text(errors="ignore"))
            lines.append(f"| [`{w.stem}`]({rel(w)}) | {esc(wfm.get('tools', '')) or '⚠️ all (inherited; no `tools:` field)'} | {short(first_sentence(wfm.get('description', ''), 400), 200)} |")
        lines.append("")
    cmds = sorted((p.dir / "commands").glob("*.md"))
    if cmds:
        lines += ["**Commands** (copied from upstream):\n", "| Command | Description |", "|---|---|"]
        for c in cmds:
            cfm = parse_frontmatter(c.read_text(errors="ignore"))
            lines.append(f"| [`/{p.name}:{c.stem}`]({rel(c)}) | {short(cfm.get('description', ''), 200)} |")
        lines.append("")
    return lines


def render_vertical_commands(p: Plugin, ctx: dict) -> list[str]:
    lines = [f"### Commands ({len(p.commands)}, hand-authored)\n"]
    if not p.commands:
        return lines + ["None.\n"]
    lines += ["| Command | Arguments | Description | Skills used | MCP named | Safety gate |", "|---|---|---|---|---|---|"]
    for c in p.commands:
        lines.append(
            f"| [`/{p.name}:{c['path'].stem}`]({rel(c['path'])}) | `{esc(c['fm'].get('argument-hint', '—'))}` | "
            f"{esc(c['fm'].get('description', ''))} | {', '.join(f'`{x}`' for x in c['skills']) or '—'} | "
            f"{', '.join(f'`{x}`' for x in c['servers']) or '—'} | {'✅' if c['gated'] else '⚠️'} |"
        )
    lines.append("")
    bundled = {s["name"] for s in p.skills}
    for a in p.spec.get("agents", []):
        agent = ctx["agents"].get(a)
        if not agent:
            continue
        theirs = {s["name"] for s in agent.skills}
        lines += [
            f"**Skill overlap with [`{a}`](./agent-plugins.md#{anchor(a)})**: {len(bundled & theirs)} shared, "
            f"{len(bundled - theirs)} only here"
            + (f" ({', '.join(f'`{x}`' for x in sorted(bundled - theirs))})" if bundled - theirs else "")
            + f", {len(theirs - bundled)} only in the agent.\n"
        ]
    return lines


def checklist(p: Plugin) -> list[str]:
    items = [
        "Description and keywords are accurate and specific enough for discovery.",
        "Every bundled skill belongs in this plugin's scope; nothing important for the scope is missing.",
        "Skill sources and variant choices are right (see *Source* and *Also in* columns).",
        "Every MCP server is needed, starts with valid credentials, and its mode (read-only / write) is intended.",
    ]
    if p.connectors:
        items.append("Connector install commands in CONNECTORS.md work and recommend least privilege.")
    if p.hook_events:
        items.append("Hooks behave as intended, are fast, and fail safe.")
    if p.rewrites:
        items.append("Rewrites still make sense and leave the upstream file coherent.")
    if p.kind == "agent":
        items += [
            "Agent `description` triggers delegation for the right requests and excludes neighbours' work.",
            "Workflow is correct and uses the bundled skills and servers by their real names.",
            "Hand-offs are complete and point at the right agents.",
            "Guardrails cover destructive actions, credentials, and approval before changes.",
            "`tools:` allowlist is minimal and matches the bundled servers and connectors.",
        ]
    else:
        items += [
            "Each command is correct, names the right skill, and has a read-only statement or approval gate.",
            "Skills from this vertical and from other installed verticals do not conflict on the main agent.",
            "The agent-alternative link points at the right agent plugin.",
        ]
    items.append("All automated findings above are resolved or accepted with a recorded reason.")
    return items


def render_global_checklist(kind: str) -> list[str]:
    lines = [
        "## Appendix: marketplace-level checklist\n",
        "- [ ] `python3 scripts/sync_aws_plugins.py` runs clean against the current upstream commits.",
        "- [ ] `python3 scripts/validate_plugins.py --claude` reports 0 errors and 0 warnings.",
        "- [ ] `.claude-plugin/marketplace.json` lists every plugin with the right source path and category.",
        "- [ ] `claude plugin marketplace add ./` then installing a sample plugin works end to end.",
        "- [ ] MCP coverage ([mcp-server-coverage.md](../mcp-server-coverage.md)) skip reasons are agreed.",
        "- [ ] `NOTICE` attribution covers every upstream source.",
    ]
    if kind == "agent":
        lines.append("- [ ] Hand-off graph has no dead ends or missing specialists.")
    else:
        lines.append("- [ ] Domain grouping is right; no skill sits in a surprising vertical.")
    lines.append("")
    return lines


def main() -> int:
    cfg = load_json(MAP_PATH)
    notes = load_json(NOTES_PATH)
    try:
        # The handbooks cover the AWS agent and vertical plugins; partner-built plugins are vendor content.
        plugins = [Plugin(cfg, spec) for spec in cfg["plugins"] if kind_of(spec) in OUT_FILES]
    except SyncError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    unknown = set(notes["plugins"]) - {p.name for p in plugins}
    if unknown:
        print(f"ERROR: handover-notes.json has notes for unknown plugin(s): {', '.join(sorted(unknown))}", file=sys.stderr)
        return 1
    ctx = analyse(plugins)
    ctx["agents"] = {p.name: p for p in plugins if p.kind == "agent"}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for kind, path in OUT_FILES.items():
        group = [p for p in plugins if p.kind == kind]
        lines = render_header(cfg, notes, kind, group)
        lines += render_model(cfg, kind)
        lines += render_sources(cfg)
        lines += render_bullets("Cross-cutting decisions", notes["common"]["decisions"] + notes[kind]["decisions"])
        lines += render_bullets("Known gaps and open questions", notes["common"]["gaps"] + notes[kind]["gaps"])
        lines += render_summary(kind, group)
        lines += render_catalog(cfg, group, kind)
        lines += ["# Plugins\n"]
        for p in group:
            lines += render_plugin(cfg, notes, p, ctx)
        lines += render_global_checklist(kind)
        path.write_text("\n".join(lines).rstrip() + "\n")
        missing = [p.name for p in group if p.name not in notes["plugins"]]
        print(
            f"{path.relative_to(REPO_ROOT)}: {len(group)} plugins, {sum(len(p.findings) for p in group)} findings"
            + (f" (no design notes: {', '.join(missing)})" if missing else "")
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
