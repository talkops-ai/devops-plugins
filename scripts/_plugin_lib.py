"""Shared helpers for the devops-plugins marketplace tooling.

Dependency-free (no PyYAML) so the scripts run on a stock Python 3.10+.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE_PATH = REPO_ROOT / ".claude-plugin" / "marketplace.json"
# Codex reads repo marketplaces from .agents/plugins/marketplace.json (and falls back to
# .claude-plugin/marketplace.json). See https://developers.openai.com/codex/plugins/build
CODEX_MARKETPLACE_PATH = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
PLUGINS_ROOT = REPO_ROOT / "plugins"
PLUGIN_KINDS = ("agent-plugins", "vertical-plugins", "partner-built")

# Agent Plugins 1.0.0 portable package format (https://agent-plugins.org): root plugin.json + mcp.json.
PORTABLE_PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
PORTABLE_MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
PORTABLE_PLUGIN_KEYS = {
    "$schema", "name", "version", "description", "author", "homepage", "repository", "license",
    "keywords", "extensions",
}
PORTABLE_SERVER_KEYS = {
    "stdio": {"type", "command", "args", "env", "cwd"},
    "streamable-http": {"type", "url", "headers"},
    "sse": {"type", "url", "headers"},
}

_FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.S)
_KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):\s?(.*)$")


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_block, body). Frontmatter is '' when absent."""
    m = _FM_RE.match(text)
    if not m:
        return "", text
    return m.group(1), text[m.end():]


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse the top-level scalar keys of a YAML frontmatter block.

    Supports plain, single/double-quoted, and block scalars (|, |-, >, >-).
    Nested mappings (e.g. ``metadata:``) are returned as raw indented text.
    """
    block, _ = split_frontmatter(text)
    if not block:
        return {}
    lines = block.splitlines()
    out: dict[str, Any] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _KEY_RE.match(line)
        if not m or line.startswith((" ", "\t")):
            i += 1
            continue
        key, raw = m.group(1), m.group(2).strip()
        i += 1
        # Collect indented continuation lines.
        cont: list[str] = []
        while i < len(lines) and (lines[i].startswith((" ", "\t")) or lines[i].strip() == ""):
            cont.append(lines[i])
            i += 1
        if raw in ("|", "|-", "|+", ">", ">-", ">+"):
            stripped = [c.strip() for c in cont]
            if raw.startswith("|"):
                value = "\n".join(stripped).strip()
            else:
                value = " ".join(s for s in stripped if s).strip()
        elif raw == "" and cont:
            value = "\n".join(cont)  # nested mapping / list, keep raw
        else:
            value = raw
            if cont:  # plain multi-line scalar
                value = " ".join([raw] + [c.strip() for c in cont if c.strip()])
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
                if raw.startswith('"'):
                    value = value.replace('\\"', '"').replace("\\\\", "\\")
                else:
                    value = value.replace("''", "'")
        out[key] = value
    return out


def first_sentence(text: str, limit: int = 220) -> str:
    text = " ".join(str(text).split())
    m = re.search(r"(.+?[.!?])(\s|$)", text)
    s = m.group(1) if m else text
    if len(s) > limit:
        s = s[: limit - 1].rstrip() + "…"
    return s


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def strip_comments(obj: Any) -> Any:
    """Recursively drop keys starting with '$comment'."""
    if isinstance(obj, dict):
        return {k: strip_comments(v) for k, v in obj.items() if not k.startswith("$comment")}
    if isinstance(obj, list):
        return [strip_comments(v) for v in obj]
    return obj


def parse_tools(value: str) -> list[str]:
    return [t.strip() for t in str(value).split(",") if t.strip()]


def mcp_tool_pattern(plugin: str, server: str) -> str:
    """Claude Code names plugin MCP tools mcp__plugin_<plugin>_<server>__<tool>."""
    return f"mcp__plugin_{plugin}_{server}__*"


SKILLS_HEADING_RE = re.compile(r"^##\s+Skills this agent uses\s*$", re.M | re.I)


def skills_listed_in_agent(body: str) -> list[str]:
    """Extract backticked skill names from the '## Skills this agent uses' section."""
    m = SKILLS_HEADING_RE.search(body)
    if not m:
        return []
    rest = body[m.end():]
    nxt = re.search(r"^##\s+", rest, re.M)
    section = rest[: nxt.start()] if nxt else rest
    return re.findall(r"`([a-z0-9][a-z0-9-]*)`", section)
