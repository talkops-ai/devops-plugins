#!/usr/bin/env python3
"""Skill Evaluation Runner for the TalkOps devops-plugins repository.

Evaluates a skill and its associated plugin ecosystem (Skills, References, Scripts,
MCP Servers, Commands, and Hooks) using natural read-only queries against live AWS:
  1. Static & Component Contract Gate (`static`):
     - agentskills.io frontmatter & size invariants (description <= 1024 chars, body <= 500 lines)
     - internal `references/*` and `scripts/*` path verification
     - shared-skill drift detection across `agent-plugins` and `vertical-plugins`
     - non-interactive `--help` / syntax smoke checks on bundled `scripts/*`
     - parent plugin `hooks/`, `mcp.json`, and `commands/*.md` verification
  2. Trigger & Sibling-Collision Evals (`trigger`):
     - 4-quadrant dataset (Explicit, Implicit, Contextual, Near-Miss Negative)
     - 60/40 train/val split support and multi-run trigger rate calculation
     - mounts `companion_skills` in an isolated workspace to test sibling routing collisions
  3. Outcome & Expectation Evals (`run`):
     - mounts the skill and its parent plugin ecosystem (References, Scripts, MCP Servers,
       Commands, and Hooks as configured in the plugin)
     - passes the natural read-only user query (`prompt`) verbatim to the agent harness
       (no prompt coaching, no custom command-catching workarounds, and no hardcoded
       reference/script checklists)
     - records observed telemetry (`skills_invoked`, `mcp_tools_called`, `commands_run`,
       `files_read`, `hook_audit`) and grades `expectations` via the binary evaluator:
       * If all expectations match -> GREEN (`PASS`)
       * Otherwise -> RED (`FAIL` — revisit the skill or its components)

Primary harness: `agy` (Antigravity CLI — strictly pinned to Gemini 4 Hydrogen models only,
defaulting to `gemini-4-hydrogen-medium` with `--effort medium`), with built-in adapters for
`claude` and `codex`.

Usage:
    python3 scripts/eval_skills.py static --skill amazon-aurora-postgresql
    python3 scripts/eval_skills.py trigger --skill amazon-aurora-postgresql --harness agy --split val
    python3 scripts/eval_skills.py run --skill amazon-aurora-postgresql --harness agy
    python3 scripts/eval_skills.py run --skill deploying-helm-charts --harness agy --model gemini-4-hydrogen-medium --effort medium
"""

from __future__ import annotations

import argparse
import json
import math
import os
import py_compile
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _plugin_lib import (  # noqa: E402
    PLUGINS_ROOT,
    REPO_ROOT,
    dump_json,
    load_json,
    parse_frontmatter,
    split_frontmatter,
)

EVALS_ROOT = REPO_ROOT / "evals"
SKILLS_EVALS_DIR = EVALS_ROOT / "skills"
WORKSPACES_DIR = Path(
    os.environ.get("DEVOPS_PLUGINS_EVAL_RUNS_DIR", str(REPO_ROOT / ".eval-runs"))
).expanduser().resolve()
SCHEMAS_DIR = EVALS_ROOT / "schemas"
DEFAULT_TALKOPS_MCP_SRC = REPO_ROOT.parent / "talkops-mcp" / "src"

ALLOWED_DUMMY_AWS_ACCOUNT_IDS = {
    "123456789012",
    "111122223333",
    "222233334444",
    "333344445555",
    "444455556666",
    "555566667777",
    "777788889999",
    "888899990000",
    "999988887777",
    "000000000000",
    "000000000001",
    "111111111111",
    "222222222222",
    "555555555555",
    "210987654321",
    "987654321098",
    "012345678901",
    "602401143452",
    "763104351884",
}


def _display_path(p: Path) -> str:
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)

AGY_BRAIN_DIR = Path.home() / ".gemini" / "antigravity-cli" / "brain"

# When `agy` CLI is used to run or grade evals, strictly enforce Gemini 4 Hydrogen only
# (defaulting to `gemini-4-hydrogen-medium` with `medium` reasoning effort).
AGY_DEFAULT_MODEL = "gemini-4-hydrogen-medium"
AGY_DEFAULT_EFFORT = "medium"
AGY_HYDROGEN_MODEL_BY_EFFORT: dict[str, str] = {
    "low": "gemini-4-hydrogen-low",
    "medium": "gemini-4-hydrogen-medium",
    "high": "gemini-4-hydrogen-high",
    "xhigh": "gemini-4-hydrogen-xhigh",
}
AGY_EFFORT_BY_HYDROGEN_MODEL: dict[str, str] = {
    v: k for k, v in AGY_HYDROGEN_MODEL_BY_EFFORT.items()
}
AGY_ALLOWED_HYDROGEN_MODELS: tuple[str, ...] = tuple(AGY_HYDROGEN_MODEL_BY_EFFORT.values())

TALKOPS_PKG_RE = re.compile(r"^talkops-([a-z0-9-]+-mcp-server)(?:==.*|>=.*|~=.*)?$")
SHELL_ENV_DEFAULT_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}$")
K8S_DEFAULT_CONTEXT = "docker-desktop"
K8S_PASSTHROUGH_ENV_KEYS = (
    "KUBECONFIG",
    "K8S_KUBECONFIG",
    "K8S_CONTEXT",
    "KUBE_CONTEXT",
    "K8S_ENABLED",
    "ARGOCD_SERVER",
    "ARGOCD_SERVER_URL",
    "ARGOCD_AUTH_TOKEN",
    "ARGOCD_INSECURE",
    "KARGO_API_URL",
    "KARGO_BASE_URL",
    "KARGO_VERIFY_SSL",
    "KARGO_AUTH_TOKEN",
    "KARGO_AUTH_MODE",
    "KARGO_DEFAULT_PROJECT",
    "KARGO_PROJECT",
    "PROMETHEUS_URL",
    "PROMETHEUS_BASE_URL",
    "PROMETHEUS_BACKENDS",
    "PROMETHEUS_BACKEND_ID",
    "PROMETHEUS_TYPE",
    "PROMETHEUS_RULER_URL",
    "PROMETHEUS_TENANT_ID",
    "PROMETHEUS_TOOLSETS",
    "ALERTMANAGER_URL",
    "ALERTMANAGER_BASE_URL",
    "ALERTMANAGER_BACKENDS",
    "ALERTMANAGER_BACKEND_ID",
    "AM_MAX_SILENCE_MINUTES",
    "AM_SILENCE_CONFIRM_THRESHOLD",
    "AM_SILENCE_WARNING_THRESHOLD",
    "AM_WATCHDOG_ALERTNAME",
    "AM_AUDIT_LOG_PATH",
    "AM_SEED_AUDIT_LOG_PATH",
    "MCP_TOOLSETS",
    "TEMPO_BASE_URL",
    "TEMPO_URL",
    "TEMPO_BACKENDS",
    "TEMPO_BACKEND_ID",
    "TEMPO_TYPE",
    "TEMPO_DISPLAY_NAME",
    "TEMPO_MULTI_TENANT",
    "TEMPO_DEFAULT_TENANT",
    "TEMPO_TENANT_HEADER",
    "TEMPO_DEPLOYMENT_MODE",
    "TEMPO_LLM_FORMAT",
    "TEMPO_VERIFY_SSL",
    "TEMPO_TIMEOUT",
    "TEMPO_CRD_GROUP",
    "TEMPO_CRD_API_VERSION",
    "OTEL_COLLECTOR_VERSION_DEFAULT",
    "OTEL_TARGET_ALLOCATOR_API_VERSION",
    "LOKI_URL",
    "LOKI_TIMEOUT",
    "LOKI_ORG_ID",
    "LOKI_TOOLSETS",
    "LOKI_VERIFY_SSL",
    "LOKI_MAX_QUERY_BYTES",
    "LOKI_MAX_TIME_WINDOW_HOURS",
    "LOKI_MAX_LOG_LIMIT",
    "LOKI_MAX_SERIES",
    "LOKI_MAX_POINTS_PER_SERIES",
    "LOKI_HIGH_CARDINALITY_THRESHOLD",
    "LOKI_CRD_GROUP",
    "TRAEFIK_API_URL",
    "TRAEFIK_HTTP_URL",
    "TRAEFIK_HTTPS_URL",
    "TRAEFIK_NAMESPACE",
    "TRAEFIK_CERT_EXPIRY_WARNING_DAYS",
    "TRAEFIK_LOG_MAX_LINES",
    "TRAEFIK_PROBE_ALLOW_ANY_HOST",
    "MCP_ALLOW_WRITE",
)

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RELATIVE_REF_RE = re.compile(
    r"(?:`|\b|\(|\[)((?:references|scripts|assets)/[A-Za-z0-9_./-]+?\.(?:md|py|sh|ts|js|json|yaml|yml))(?:`|\b|\)|\])"
)


@dataclass
class CommandRecord:
    command: str
    exit_code: int | None = None
    output_preview: str = ""


@dataclass
class MCPToolRecord:
    server: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedTrace:
    harness: str
    model: str = ""
    effort: str = ""
    conversation_id: str = ""
    skills_invoked: list[str] = field(default_factory=list)
    files_read: list[str] = field(default_factory=list)
    commands_run: list[CommandRecord] = field(default_factory=list)
    mcp_tools_called: list[MCPToolRecord] = field(default_factory=list)
    hook_audit: list[dict[str, Any]] = field(default_factory=list)
    final_response: str = ""
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0
    num_turns: int = 0
    raw_events: list[dict[str, Any]] = field(default_factory=list)


def resolve_agy_model_and_effort(
    model: str | None = None,
    effort: str | None = None,
) -> tuple[str, str]:
    """Enforce Gemini 4 Hydrogen-only execution when `agy` CLI is used (default: medium effort).

    Every `agy` invocation (trigger, execution, and judge) MUST use a Gemini 4 Hydrogen model
    (`gemini-4-hydrogen-medium` with `--effort medium` by default). Non-Hydrogen models are rejected.
    """
    raw_effort = effort.strip().lower() if effort else None
    if raw_effort is not None and raw_effort not in AGY_HYDROGEN_MODEL_BY_EFFORT:
        raise ValueError(
            f"Unsupported --effort {effort!r} for harness 'agy'. "
            f"Allowed reasoning effort levels for Gemini 4 Hydrogen: {', '.join(AGY_HYDROGEN_MODEL_BY_EFFORT)}."
        )

    raw_model = model.strip().lower() if model else None
    if not raw_model or raw_model in ("hydrogen", "gemini-4-hydrogen"):
        eff = raw_effort or AGY_DEFAULT_EFFORT
        return AGY_HYDROGEN_MODEL_BY_EFFORT[eff], eff

    if raw_model not in AGY_EFFORT_BY_HYDROGEN_MODEL:
        raise ValueError(
            f"Harness 'agy' must use a Gemini 4 Hydrogen model only "
            f"({', '.join(AGY_ALLOWED_HYDROGEN_MODELS)}); got {model!r}."
        )

    inferred_effort = AGY_EFFORT_BY_HYDROGEN_MODEL[raw_model]
    if raw_effort is not None and raw_effort != inferred_effort:
        raise ValueError(
            f"Conflicting Hydrogen model tier {raw_model!r} and --effort {raw_effort!r}; "
            f"use --model {AGY_HYDROGEN_MODEL_BY_EFFORT[raw_effort]!r} --effort {raw_effort!r} "
            f"or omit --model."
        )
    return raw_model, inferred_effort


def resolve_local_mcp_src_dir(mcp_src_dir: str | Path | None = None, disable_local_mcp: bool = False) -> Path | None:
    """Resolve the local `talkops-mcp/src` directory for direct MCP server execution during evals."""
    if disable_local_mcp:
        return None
    raw = mcp_src_dir or os.environ.get("TALKOPS_MCP_SRC_DIR")
    cand = Path(raw).expanduser().resolve() if raw else DEFAULT_TALKOPS_MCP_SRC.resolve()
    return cand if cand.is_dir() else None


def _ensure_eval_venv() -> Path | None:
    """Ensure a shared virtualenv with `boto3`, `pyyaml`, `cryptography`, and `pydantic`
    exists under `evals/workspaces/.venv` so bundled AWS and Kubernetes skill scripts run cleanly."""
    venv_dir = WORKSPACES_DIR / ".venv"
    venv_py = venv_dir / "bin" / "python3"
    need_install = not venv_py.exists()
    if not need_install:
        chk = subprocess.run(
            [str(venv_py), "-c", "import boto3, yaml, cryptography, pydantic, pydantic_settings"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        need_install = chk.returncode != 0
    if need_install:
        WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if not venv_py.exists():
                subprocess.run(
                    ["uv", "venv", str(venv_dir)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=True,
                )
            subprocess.run(
                [
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    str(venv_py),
                    "boto3",
                    "pyyaml",
                    "cryptography",
                    "pydantic",
                    "pydantic-settings",
                ],
                capture_output=True,
                text=True,
                timeout=90,
                check=True,
            )
        except Exception:
            return venv_dir if venv_py.exists() else None
    return venv_dir


def build_aws_env(
    aws_profile: str | None = None,
    aws_region: str | None = None,
    mcp_src_dir: str | Path | None = None,
    disable_local_mcp: bool = False,
) -> dict[str, str]:
    """Configure live AWS and local TalkOps MCP environment variables for eval execution.

    Prepends `.eval-runs/.venv/bin` to `PATH` without setting cross-interpreter
    `PYTHONPATH` or `VIRTUAL_ENV`, preventing ABI mismatches when `uv run` spawns MCP
    servers that use a different Python minor version in their own `.venv`.
    """
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("VIRTUAL_ENV", None)
    env.pop("PYTHONPATH", None)
    venv_dir = _ensure_eval_venv()
    if venv_dir and (venv_dir / "bin").is_dir():
        venv_bin = str((venv_dir / "bin").resolve())
        env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
    local_mcp = resolve_local_mcp_src_dir(mcp_src_dir, disable_local_mcp=disable_local_mcp)
    if local_mcp:
        env["TALKOPS_MCP_SRC_DIR"] = str(local_mcp)
    profile = (aws_profile or env.get("AWS_PROFILE") or "").strip()
    region = (aws_region or env.get("AWS_REGION") or env.get("AWS_DEFAULT_REGION") or "us-east-1").strip()
    if profile:
        env.pop("AWS_ACCESS_KEY_ID", None)
        env.pop("AWS_SECRET_ACCESS_KEY", None)
        env.pop("AWS_SESSION_TOKEN", None)
        env["AWS_PROFILE"] = profile
        env["AWS_DEFAULT_PROFILE"] = profile
    if region:
        env["AWS_REGION"] = region
        env["AWS_DEFAULT_REGION"] = region
    return env


def discover_skill_paths() -> dict[str, list[Path]]:
    """Map canonical skill name -> list of SKILL.md paths across all plugins."""
    by_name: dict[str, list[Path]] = defaultdict(list)
    for skill_md in sorted(PLUGINS_ROOT.rglob("SKILL.md")):
        if "packages/openclaw" in str(skill_md):
            continue
        by_name[skill_md.parent.name].append(skill_md)
    return dict(by_name)


def resolve_canonical_skill_dir(skill_name: str, skill_map: dict[str, list[Path]]) -> Path:
    """Return the primary skill directory for a canonical skill name."""
    paths = skill_map.get(skill_name)
    if not paths:
        raise FileNotFoundError(f"Skill '{skill_name}' not found under {PLUGINS_ROOT}")
    return paths[0].parent


def resolve_associated_plugins(skill_name: str, skill_map: dict[str, list[Path]]) -> list[Path]:
    """Return all plugin directories that bundle `skill_name`, preferring vertical plugins first."""
    paths = skill_map.get(skill_name, [])
    plugin_dirs: list[Path] = []
    for p in paths:
        cand = p.parent.parent.parent
        if (cand / "plugin.json").exists() and cand not in plugin_dirs:
            plugin_dirs.append(cand)
    plugin_dirs.sort(key=lambda d: (0 if "vertical-plugins" in str(d) else 1, d.name))
    return plugin_dirs


def next_iteration_dir(skill_name: str) -> Path:
    """Return the next `evals/workspaces/<skill-name>/iteration-<N>` directory."""
    base = WORKSPACES_DIR / skill_name
    base.mkdir(parents=True, exist_ok=True)
    existing = [
        int(m.group(1))
        for p in base.iterdir()
        if p.is_dir() and (m := re.match(r"^iteration-(\d+)$", p.name))
    ]
    nxt = (max(existing) + 1) if existing else 1
    out = base / f"iteration-{nxt}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def compute_pass_at_k(n: int, c: int, k: int) -> float:
    if n <= 0 or c <= 0:
        return 0.0
    if n < k:
        k = n
    if n - c < k:
        return 1.0
    return round(1.0 - (math.comb(n - c, k) / math.comb(n, k)), 4)


def compute_pass_hat_k(n: int, c: int, k: int) -> float:
    if n <= 0 or c <= 0:
        return 0.0
    return round((c / n) ** k, 4)


# ---------------------------------------------------------------------------
# Layer 1: Static & Component Contract Validator
# ---------------------------------------------------------------------------


def _verify_plugin_hooks_contract(plugin_dir: Path, errors: list[str]) -> None:
    """Verify the plugin's hooks (`aws-mutation-gate.py`, `secret-safety.py`, `iac-post-write-lint.py`) pass their self-tests."""
    hooks_dir = plugin_dir / "hooks"
    if not hooks_dir.is_dir():
        return
    env = build_aws_env()
    mutation_gate = hooks_dir / "aws-mutation-gate.py"
    if mutation_gate.exists():
        where = str(mutation_gate.relative_to(REPO_ROOT))
        proc = subprocess.run(
            [sys.executable, str(mutation_gate), "--self-test"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        if proc.returncode != 0:
            errors.append(f"{where}: `--self-test` failed: {proc.stdout} {proc.stderr}")

    secret_safety = hooks_dir / "secret-safety.py"
    if secret_safety.exists():
        where = str(secret_safety.relative_to(REPO_ROOT))
        deny_payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "aws secretsmanager get-secret-value --secret-id prod/jwt"},
            }
        )
        allow_payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "aws secretsmanager describe-secret --secret-id prod/jwt"},
            }
        )
        proc_deny = subprocess.run(
            [sys.executable, str(secret_safety)],
            input=deny_payload,
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        if '"permissionDecision": "deny"' not in proc_deny.stdout:
            errors.append(f"{where}: failed to deny `get-secret-value` smoke check")
        proc_allow = subprocess.run(
            [sys.executable, str(secret_safety)],
            input=allow_payload,
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        if '"permissionDecision": "deny"' in proc_allow.stdout:
            errors.append(f"{where}: falsely denied `describe-secret` smoke check")

    iac_lint = hooks_dir / "iac-post-write-lint.py"
    if iac_lint.exists():
        where = str(iac_lint.relative_to(REPO_ROOT))
        try:
            py_compile.compile(str(iac_lint), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"{where}: Python syntax error: {exc}")

    finops_gate = hooks_dir / "finops-sql-and-cost-gate.py"
    if finops_gate.exists():
        where = str(finops_gate.relative_to(REPO_ROOT))
        proc = subprocess.run(
            [sys.executable, str(finops_gate), "--self-test"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        if proc.returncode != 0:
            errors.append(f"{where}: `--self-test` failed: {proc.stdout} {proc.stderr}")


def run_static_checks(target_skill: str | None = None, strict_limits: bool = False) -> int:
    skill_map = discover_skill_paths()
    if target_skill and target_skill not in skill_map:
        print(f"ERROR: Skill '{target_skill}' not found in repository.")
        return 1

    names_to_check = [target_skill] if target_skill else sorted(skill_map)
    errors: list[str] = []
    warnings: list[str] = []
    checked_plugins: set[Path] = set()

    for skill_name in names_to_check:
        paths = skill_map[skill_name]
        if len(paths) > 1:
            contents = {p.read_text() for p in paths}
            if len(contents) > 1:
                locs = ", ".join(str(p.relative_to(REPO_ROOT)) for p in paths)
                warnings.append(f"{skill_name}: shared skill has diverged across plugins ({locs})")

        skill_md = paths[0]
        skill_dir = skill_md.parent
        where = str(skill_md.relative_to(REPO_ROOT))
        text = skill_md.read_text()
        fm = parse_frontmatter(text)
        _, body = split_frontmatter(text)

        # 1. Skill frontmatter & spec limits
        name = str(fm.get("name", ""))
        desc = str(fm.get("description", ""))
        if not name or name != skill_name:
            errors.append(f"{where}: frontmatter name {name!r} != directory name {skill_name!r}")
        if not (1 <= len(name) <= 64) or not SKILL_NAME_RE.match(name):
            errors.append(f"{where}: name {name!r} violates agentskills.io naming rules")
        if not desc:
            errors.append(f"{where}: missing frontmatter description")
        elif len(desc) > 1024:
            msg = f"{where}: description length ({len(desc)} chars) exceeds 1024-char limit"
            (errors if strict_limits else warnings).append(msg)

        line_count = len(text.splitlines())
        approx_tokens = len(text) // 4
        if line_count > 500 or approx_tokens > 5000:
            msg = f"{where}: {line_count} lines (~{approx_tokens} tokens) exceeds recommended 500-line / 5000-token ceiling"
            (errors if strict_limits else warnings).append(msg)

        # 2. References & relative paths check
        for rel_path in sorted(set(RELATIVE_REF_RE.findall(body))):
            if "{" in rel_path or "*" in rel_path:
                continue
            candidate = (skill_dir / rel_path).resolve()
            if not candidate.exists():
                errors.append(
                    f"{where}: referenced path '{rel_path}' does not exist in {skill_dir.relative_to(REPO_ROOT)}"
                )

        # 3. Bundled scripts syntax & --help check
        scripts_dir = skill_dir / "scripts"
        if scripts_dir.is_dir():
            env = build_aws_env()
            venv_py_bin = shutil.which("python3", path=env.get("PATH")) or sys.executable
            for script_file in sorted(scripts_dir.iterdir()):
                if not script_file.is_file():
                    continue
                s_where = str(script_file.relative_to(REPO_ROOT))
                if script_file.suffix == ".py":
                    tmp_pyc = Path(tempfile.gettempdir()) / f"eval_check_{script_file.stem}.pyc"
                    try:
                        py_compile.compile(str(script_file), cfile=str(tmp_pyc), doraise=True)
                    except py_compile.PyCompileError as exc:
                        errors.append(f"{s_where}: Python syntax error: {exc}")
                        continue
                    finally:
                        tmp_pyc.unlink(missing_ok=True)
                    s_text = script_file.read_text(errors="ignore")
                    if "argparse" in s_text and "__main__" in s_text:
                        try:
                            proc = subprocess.run(
                                [venv_py_bin, str(script_file), "--help"],
                                capture_output=True,
                                text=True,
                                timeout=10,
                                env=env,
                            )
                            if proc.returncode != 0:
                                warnings.append(f"{s_where}: `--help` exited with code {proc.returncode}")
                        except subprocess.TimeoutExpired:
                            errors.append(f"{s_where}: `--help` hung waiting for input (>10s)")
                elif script_file.suffix == ".sh":
                    proc = subprocess.run(["bash", "-n", str(script_file)], capture_output=True, text=True)
                    if proc.returncode != 0:
                        errors.append(f"{s_where}: bash syntax error: {proc.stderr.strip()}")

        # 4. Associated Plugin Components Check (MCP servers, Commands, Hooks)
        for p_dir in resolve_associated_plugins(skill_name, skill_map):
            if p_dir in checked_plugins:
                continue
            checked_plugins.add(p_dir)
            _verify_plugin_hooks_contract(p_dir, errors)
            mcp_file = p_dir / "mcp.json"
            if mcp_file.exists():
                try:
                    mcp_data = load_json(mcp_file)
                    if not isinstance(mcp_data.get("mcpServers"), dict):
                        errors.append(f"{mcp_file.relative_to(REPO_ROOT)}: missing mcpServers object")
                except Exception as exc:
                    errors.append(f"{mcp_file.relative_to(REPO_ROOT)}: {exc}")
            cmd_dir = p_dir / "commands"
            if cmd_dir.is_dir():
                for cmd_md in sorted(cmd_dir.glob("*.md")):
                    if not parse_frontmatter(cmd_md.read_text()).get("description"):
                        errors.append(f"{cmd_md.relative_to(REPO_ROOT)}: missing frontmatter description")

        # 5. Enforce canonical top-level `evals/skills/<skill-name>/` layout & open-source hygiene
        for p in paths:
            stray_evals = p.parent / "evals"
            if stray_evals.is_dir():
                errors.append(
                    f"{stray_evals.relative_to(REPO_ROOT)}: co-located evals inside plugins/ are disallowed; "
                    f"keep canonical suites under evals/skills/{skill_name}/ so plugin installs stay lightweight"
                )

        eval_dir = SKILLS_EVALS_DIR / skill_name
        if not eval_dir.is_dir():
            warnings.append(f"evals/skills/{skill_name}: missing canonical eval directory")
        else:
            valid_quadrants = {"explicit", "implicit", "contextual", "near_miss_negative"}
            valid_splits = {"train", "val"}

            def _check_opensource_hygiene(f_where: str, raw_text: str) -> None:
                for m_acct in re.finditer(r"(?<!\d)(\d{12})(?!\d)", raw_text):
                    aid = m_acct.group(1)
                    if aid not in ALLOWED_DUMMY_AWS_ACCOUNT_IDS and not re.match(
                        r"^202[0-9](?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])(?:[01]\d|2[0-3])[0-5]\d$", aid
                    ):
                        errors.append(
                            f"{f_where}: non-placeholder 12-digit AWS account ID '{aid}' detected; use 123456789012"
                        )
                for m_upath in re.finditer(r"/Users/([A-Za-z0-9_.-]+)/", raw_text):
                    uname = m_upath.group(1)
                    if uname.lower() not in ("user", "username", "alice", "bob", "dev", "developer", "example"):
                        errors.append(f"{f_where}: personal local path '/Users/{uname}/...' detected")

            trig_path = eval_dir / "trigger_evals.json"
            if not trig_path.exists():
                errors.append(f"evals/skills/{skill_name}: missing trigger_evals.json")
            else:
                t_where = str(trig_path.relative_to(REPO_ROOT))
                raw_t = trig_path.read_text(errors="replace")
                _check_opensource_hygiene(t_where, raw_t)
                try:
                    t_data = json.loads(raw_t)
                    if not isinstance(t_data, dict):
                        errors.append(f"{t_where}: trigger_evals.json must be a JSON object matching trigger_evals.schema.json")
                    else:
                        if t_data.get("skill_name") != skill_name:
                            errors.append(f"{t_where}: skill_name {t_data.get('skill_name')!r} != {skill_name!r}")
                        queries = t_data.get("queries", [])
                        if not isinstance(queries, list) or len(queries) < 4:
                            errors.append(f"{t_where}: 'queries' must contain at least 4 items")
                        else:
                            for idx_t, t_item in enumerate(queries):
                                if not isinstance(t_item, dict):
                                    errors.append(f"{t_where}[{idx_t}]: query item must be an object")
                                    continue
                                if not t_item.get("prompt") or "should_trigger" not in t_item:
                                    errors.append(f"{t_where}[{idx_t}]: requires 'prompt' and 'should_trigger'")
                                if t_item.get("quadrant") not in valid_quadrants:
                                    errors.append(f"{t_where}[{idx_t}]: invalid quadrant {t_item.get('quadrant')!r}")
                                if t_item.get("split") not in valid_splits:
                                    errors.append(f"{t_where}[{idx_t}]: invalid split {t_item.get('split')!r}")
                except Exception as exc:
                    errors.append(f"{t_where}: invalid trigger_evals.json: {exc}")

            exec_path = eval_dir / "evals.json"
            if not exec_path.exists():
                errors.append(f"evals/skills/{skill_name}: missing evals.json")
            else:
                e_where = str(exec_path.relative_to(REPO_ROOT))
                raw_e = exec_path.read_text(errors="replace")
                _check_opensource_hygiene(e_where, raw_e)
                try:
                    e_data = json.loads(raw_e)
                    if not isinstance(e_data, dict):
                        errors.append(f"{e_where}: evals.json must be a JSON object matching execution_evals.schema.json")
                    else:
                        if e_data.get("skill_name") != skill_name:
                            errors.append(f"{e_where}: skill_name {e_data.get('skill_name')!r} != {skill_name!r}")
                        for ev in e_data.get("evals", []):
                            if not ev.get("prompt") or not ev.get("expectations"):
                                errors.append(f"{e_where}: each eval item requires 'prompt' and 'expectations'")
                            for rf in ev.get("files") or []:
                                cand_local = (eval_dir / rf).resolve()
                                cand_repo = (REPO_ROOT / rf).resolve()
                                if not cand_local.exists() and not cand_repo.exists():
                                    errors.append(f"{e_where}: fixture file '{rf}' not found in {eval_dir.relative_to(REPO_ROOT)} or repo root")
                except Exception as exc:
                    errors.append(f"{e_where}: invalid evals.json: {exc}")

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(
        f"\nStatic skill & component audit complete: {len(names_to_check)} skill(s) and "
        f"{len(checked_plugins)} associated plugin(s) checked, {len(errors)} error(s), {len(warnings)} warning(s)."
    )
    return 1 if errors else 0


# ---------------------------------------------------------------------------
# Workspace Provisioning: Mounts Skills, References, Scripts, MCP, Commands & Hooks
# ---------------------------------------------------------------------------

AGY_HOOK_BRIDGE_SCRIPT = '''#!/usr/bin/env python3
"""Antigravity PreToolUse & PostToolUse Hook Adapter for devops-plugins.

Forwards Antigravity `PreToolUse` and `PostToolUse` events (`toolCall`) directly to the
plugin's configured hooks (`hooks/secret-safety.py`, `hooks/aws-mutation-gate.py`, and
`hooks/iac-post-write-lint.py`) with `TALKOPS_AWS_MUTATION_GATE=deny` enforced for
read-only skill evaluations, records each hook invocation in `hook_audit.jsonl`, and
returns the hook's decision to Antigravity.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
AUDIT_LOG = WORKSPACE_DIR / "hook_audit.jsonl"
PLUGIN_HOOKS_DIR = Path(os.environ.get("EVAL_PLUGIN_HOOKS_DIR", ""))

BOTO3_CALL_RE = re.compile(
    r"call_boto3\\s*\\(\\s*service_name\\s*=\\s*['\\"]([a-zA-Z0-9_-]+)['\\"]\\s*,\\s*operation_name\\s*=\\s*['\\"]([a-zA-Z0-9_-]+)['\\"]",
    re.S,
)

def run_plugin_hook(script_path: Path, hook_payload: dict) -> tuple[str, str]:
    if not script_path.exists():
        return "allow", ""
    hook_env = dict(os.environ)
    hook_env.setdefault("TALKOPS_AWS_MUTATION_GATE", "deny")
    proc = subprocess.run(
        [sys.executable, str(script_path)],
        input=json.dumps(hook_payload),
        capture_output=True,
        text=True,
        timeout=5,
        env=hook_env,
    )
    out = proc.stdout.strip()
    if not out:
        return "allow", ""
    try:
        data = json.loads(out)
        hso = data.get("hookSpecificOutput", {})
        dec = hso.get("permissionDecision") or "allow"
        if dec == "ask":
            dec = "deny"
        reason = hso.get("permissionDecisionReason") or hso.get("additionalContext") or ""
        return dec, reason
    except Exception:
        return "allow", ""

def evaluate_mutation_gate(hook_payload: dict) -> tuple[str, str]:
    gate_path = PLUGIN_HOOKS_DIR / "aws-mutation-gate.py"
    if not gate_path.exists():
        return "allow", ""
    t_name = str(hook_payload.get("tool_name", ""))
    t_inp = hook_payload.get("tool_input", {}) or {}
    try:
        has_ast_classifier = "classify_run_script" in gate_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        has_ast_classifier = False
    if not has_ast_classifier and t_name.endswith("run_script") and isinstance(t_inp, dict) and isinstance(t_inp.get("code"), str):
        code_str = t_inp["code"]
        boto_ops = BOTO3_CALL_RE.findall(code_str)
        if boto_ops:
            for svc, op in boto_ops:
                kebab_op = re.sub(r"(?<!^)(?=[A-Z])", "-", op).lower()
                sub_dec, sub_reason = run_plugin_hook(
                    gate_path,
                    {"tool_name": "use_aws", "tool_input": {"service_name": svc, "operation_name": kebab_op}},
                )
                if sub_dec == "deny":
                    return "deny", sub_reason
            return "allow", ""
    return run_plugin_hook(gate_path, hook_payload)

def main() -> None:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        print(json.dumps({"decision": "allow"}))
        return

    tc = payload.get("toolCall", {}) or {}
    t_name = tc.get("name", "")
    t_args = tc.get("args", {}) or {}

    if t_name in ("write_file", "edit_file"):
        f_path = str(t_args.get("Path") or t_args.get("file_path") or t_args.get("path") or "")
        post_payload = {"tool_name": "Write", "tool_input": {"file_path": f_path}}
        lint_dec, lint_reason = run_plugin_hook(PLUGIN_HOOKS_DIR / "iac-post-write-lint.py", post_payload)
        audit_entry = {
            "agy_tool": t_name,
            "hook_tool_name": "PostToolUse:Write",
            "tool_input": post_payload["tool_input"],
            "secret_safety_decision": "allow",
            "mutation_gate_decision": "allow",
            "iac_lint_warning": lint_reason,
            "final_decision": "allow",
            "reason": lint_reason,
        }
        try:
            with AUDIT_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry, ensure_ascii=False) + "\\n")
        except Exception:
            pass
        print(json.dumps({"decision": "allow"}))
        return

    if t_name == "run_command":
        cmd_str = str(t_args.get("CommandLine") or t_args.get("command") or "")
        hook_payload = {"tool_name": "Bash", "tool_input": {"command": cmd_str}}
    elif t_name == "call_mcp_tool":
        srv = str(t_args.get("ServerName", ""))
        tool = str(t_args.get("ToolName", ""))
        mcp_args = t_args.get("Arguments", {}) or {}
        hook_payload = {
            "tool_name": f"mcp__{srv}__{tool}",
            "tool_input": mcp_args if isinstance(mcp_args, dict) else {},
        }
    elif t_name.startswith("mcp_"):
        # Eager MCP tool in agy: mcp_<plugin>_<server>_<tool>
        rest = t_name[4:]
        parts = rest.split("_", 2)
        if len(parts) == 3:
            srv = f"{parts[0]}_{parts[1]}"
            tool = parts[2]
        elif len(parts) == 2:
            srv, tool = parts[0], parts[1]
        else:
            srv, tool = "mcp", rest
        hook_payload = {
            "tool_name": f"mcp__{srv}__{tool}",
            "tool_input": t_args if isinstance(t_args, dict) else {},
        }
    else:
        hook_payload = {"tool_name": t_name, "tool_input": t_args}

    sec_dec, sec_reason = run_plugin_hook(PLUGIN_HOOKS_DIR / "secret-safety.py", hook_payload)
    mut_dec, mut_reason = evaluate_mutation_gate(hook_payload)
    sql_dec, sql_reason = run_plugin_hook(PLUGIN_HOOKS_DIR / "finops-sql-and-cost-gate.py", hook_payload)

    final_dec = "deny" if ("deny" in (sec_dec, mut_dec, sql_dec)) else "allow"
    final_reason = (
        sec_reason
        if sec_dec == "deny"
        else (sql_reason if sql_dec == "deny" else (mut_reason or sql_reason or sec_reason))
    )

    audit_entry = {
        "agy_tool": t_name,
        "hook_tool_name": hook_payload["tool_name"],
        "tool_input": hook_payload["tool_input"],
        "secret_safety_decision": sec_dec,
        "mutation_gate_decision": mut_dec,
        "finops_sql_gate_decision": sql_dec,
        "final_decision": final_dec,
        "reason": final_reason,
    }
    try:
        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(audit_entry, ensure_ascii=False) + "\\n")
    except Exception:
        pass

    out_obj = {"decision": final_dec}
    if final_reason and final_dec == "deny":
        out_obj["reason"] = final_reason
    print(json.dumps(out_obj))

if __name__ == "__main__":
    main()
'''


def _plugin_uses_talkops_k8s_mcp(plugin_dir: Path) -> bool:
    """Return True if `plugin_dir` configures any TalkOps Kubernetes MCP server (uvx or local uv run)."""
    for fn in ("mcp.json", ".mcp.json"):
        p = plugin_dir / fn
        if not p.exists():
            continue
        try:
            mcp_obj = load_json(p)
        except Exception:
            continue
        for srv_cfg in (mcp_obj.get("mcpServers") or {}).values():
            raw_args = [str(a) for a in srv_cfg.get("args", [])]
            if len(raw_args) >= 2 and raw_args[0] == "--from" and TALKOPS_PKG_RE.match(raw_args[1]):
                return True
            for idx, arg in enumerate(raw_args):
                if arg == "--directory" and idx + 1 < len(raw_args):
                    dir_name = Path(raw_args[idx + 1]).name
                    if dir_name.endswith("-mcp-server"):
                        return True
    return False


def stage_isolated_kubeconfig(
    workspace_dir: Path,
    kube_context: str | None = K8S_DEFAULT_CONTEXT,
) -> tuple[Path | None, str]:
    """Export a single-context kubeconfig (`<workspace_dir>/.kube/config`) pinned to `kube_context` (`docker-desktop`).

    Isolating the workspace kubeconfig prevents evals on both `kubernetes-delivery-engineer`
    and `kubernetes-observability-engineer` from touching remote GKE/EKS/Hetzner clusters or
    mutating the host `~/.kube/config` during `kubernetes_set_context` calls.
    """
    resolved_ctx = (
        kube_context
        or os.environ.get("K8S_CONTEXT")
        or os.environ.get("KUBE_CONTEXT")
        or K8S_DEFAULT_CONTEXT
    ).strip()
    kube_dir = workspace_dir / ".kube"
    kube_dir.mkdir(parents=True, exist_ok=True)
    dest_cfg = kube_dir / "config"
    try:
        proc = subprocess.run(
            ["kubectl", "config", "view", "--raw", "--minify", "--context", resolved_ctx],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            dest_cfg.write_text(proc.stdout, encoding="utf-8")
            dest_cfg.chmod(0o600)
            return dest_cfg, resolved_ctx
    except Exception:
        pass
    return None, resolved_ctx


def _dotenv_defined_keys(env_file: Path) -> set[str]:
    """Return the set of non-empty variable names defined in a `.env` file without exposing secret values."""
    keys: set[str] = set()
    if not env_file.is_file():
        return keys
    for raw_line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() and v.strip().strip("'").strip('"'):
            keys.add(k.strip())
    return keys


def _load_non_secret_dotenv_overrides(env_file: Path) -> dict[str, str]:
    """Read non-secret connection overrides (URLs/flags) from a local `.env` file while skipping tokens/passwords."""
    out: dict[str, str] = {}
    if not env_file.is_file():
        return out
    for raw_line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        val = v.strip().strip("'").strip('"')
        if any(sec in key.upper() for sec in ("TOKEN", "PASSWORD", "SECRET", "KEY")):
            continue
        out[key] = val
    return out


def _rewrite_mcp_server_config(
    srv_cfg: dict[str, Any],
    plugin_dir: Path,
    plugin_data_dir: Path,
    aws_profile: str | None,
    aws_region: str | None,
    local_mcp_src: Path | None,
    mcp_allow_write: str = "auto",
    kube_context: str | None = None,
    isolated_kubeconfig: Path | None = None,
    strip_type: bool = False,
) -> dict[str, Any]:
    """Rewrite an MCP server entry for isolated eval workspaces.

    - When `local_mcp_src` is present and the server uses `uvx --from talkops-<dir>==...`,
      points execution directly to `uv run --quiet --directory <local_mcp_src>/<dir> ...`
      so local MCP server code changes are tested live without republishing wheels.
    - Pins Kubernetes MCP servers to `isolated_kubeconfig` and `kube_context` (`docker-desktop`).
    - Loads `.argocd.env` / `.kargo.env` via `uv run --env-file` so bearer tokens never land in `mcp_config.json`.
    - Expands `${PLUGIN_DATA}` and `${PLUGIN_ROOT}` and forwards live K8s/MCP environment overrides.
    - Controls `MCP_ALLOW_WRITE` (`auto` enables write+delete tool registration on local TalkOps K8s MCPs).
    """
    cfg: dict[str, Any] = {k: v for k, v in srv_cfg.items() if (k != "type" or not strip_type)}
    cmd = str(cfg.get("command", ""))
    raw_args = [
        str(a)
        .replace("${PLUGIN_DATA}", str(plugin_data_dir))
        .replace("${PLUGIN_ROOT}", str(plugin_dir))
        .replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_dir))
        for a in cfg.get("args", [])
    ]
    cfg["args"] = raw_args
    is_talkops_k8s_mcp = False
    srv_subdir_name = ""
    server_env_file: Path | None = None

    from_idx = raw_args.index("--from") if "--from" in raw_args else -1
    if cmd in ("uvx", "uv") and from_idx >= 0 and len(raw_args) >= from_idx + 3:
        m_pkg = TALKOPS_PKG_RE.match(raw_args[from_idx + 1])
        if m_pkg:
            is_talkops_k8s_mcp = True
            srv_subdir_name = m_pkg.group(1)
            if srv_subdir_name == "argocd-mcp-server" and (WORKSPACES_DIR / ".argocd.env").is_file():
                server_env_file = (WORKSPACES_DIR / ".argocd.env").resolve()
            elif srv_subdir_name == "kargo-mcp-server" and (WORKSPACES_DIR / ".kargo.env").is_file():
                server_env_file = (WORKSPACES_DIR / ".kargo.env").resolve()
            elif srv_subdir_name == "traefik-mcp-server" and (WORKSPACES_DIR / ".traefik.env").is_file():
                server_env_file = (WORKSPACES_DIR / ".traefik.env").resolve()
            elif srv_subdir_name == "prometheus-mcp-server" and (WORKSPACES_DIR / ".prometheus.env").is_file():
                server_env_file = (WORKSPACES_DIR / ".prometheus.env").resolve()
            elif srv_subdir_name == "alertmanager-mcp-server" and (WORKSPACES_DIR / ".alertmanager.env").is_file():
                server_env_file = (WORKSPACES_DIR / ".alertmanager.env").resolve()
            elif srv_subdir_name == "loki-mcp-server" and (WORKSPACES_DIR / ".loki.env").is_file():
                server_env_file = (WORKSPACES_DIR / ".loki.env").resolve()
            elif srv_subdir_name == "tempo-mcp-server" and (WORKSPACES_DIR / ".tempo.env").is_file():
                server_env_file = (WORKSPACES_DIR / ".tempo.env").resolve()
            elif srv_subdir_name == "opentelemetry-mcp-server" and (WORKSPACES_DIR / ".opentelemetry.env").is_file():
                server_env_file = (WORKSPACES_DIR / ".opentelemetry.env").resolve()
            if local_mcp_src and (local_mcp_src / srv_subdir_name).is_dir():
                target_dir = str((local_mcp_src / srv_subdir_name).resolve())
                cfg["command"] = "uv"
                uv_args = ["run", "--quiet"]
                if server_env_file is not None:
                    uv_args.extend(["--env-file", str(server_env_file)])
                uv_args.extend(["--directory", target_dir, *raw_args[from_idx + 2:]])
                cfg["args"] = uv_args
            elif cmd == "uv" and server_env_file is not None and "--env-file" not in raw_args:
                run_idx = raw_args.index("run") + 1 if "run" in raw_args else 0
                raw_args[run_idx:run_idx] = ["--env-file", str(server_env_file)]
                cfg["args"] = raw_args
    elif cmd == "uv" and "--directory" in raw_args:
        dir_idx = raw_args.index("--directory")
        if dir_idx + 1 < len(raw_args):
            cand_dir = Path(raw_args[dir_idx + 1])
            if cand_dir.name.endswith("-mcp-server"):
                is_talkops_k8s_mcp = True
                srv_subdir_name = cand_dir.name
                if srv_subdir_name == "argocd-mcp-server" and (WORKSPACES_DIR / ".argocd.env").is_file():
                    server_env_file = (WORKSPACES_DIR / ".argocd.env").resolve()
                elif srv_subdir_name == "kargo-mcp-server" and (WORKSPACES_DIR / ".kargo.env").is_file():
                    server_env_file = (WORKSPACES_DIR / ".kargo.env").resolve()
                elif srv_subdir_name == "traefik-mcp-server" and (WORKSPACES_DIR / ".traefik.env").is_file():
                    server_env_file = (WORKSPACES_DIR / ".traefik.env").resolve()
                elif srv_subdir_name == "prometheus-mcp-server" and (WORKSPACES_DIR / ".prometheus.env").is_file():
                    server_env_file = (WORKSPACES_DIR / ".prometheus.env").resolve()
                elif srv_subdir_name == "alertmanager-mcp-server" and (WORKSPACES_DIR / ".alertmanager.env").is_file():
                    server_env_file = (WORKSPACES_DIR / ".alertmanager.env").resolve()
                elif srv_subdir_name == "loki-mcp-server" and (WORKSPACES_DIR / ".loki.env").is_file():
                    server_env_file = (WORKSPACES_DIR / ".loki.env").resolve()
                elif srv_subdir_name == "tempo-mcp-server" and (WORKSPACES_DIR / ".tempo.env").is_file():
                    server_env_file = (WORKSPACES_DIR / ".tempo.env").resolve()
                elif srv_subdir_name == "opentelemetry-mcp-server" and (WORKSPACES_DIR / ".opentelemetry.env").is_file():
                    server_env_file = (WORKSPACES_DIR / ".opentelemetry.env").resolve()
                if server_env_file is not None and "--env-file" not in raw_args:
                    insert_pos = raw_args.index("--directory")
                    raw_args[insert_pos:insert_pos] = ["--env-file", str(server_env_file)]
                    cfg["args"] = raw_args

    if "command" in cfg:
        raw_env = dict(cfg.get("env", {}))
        dotenv_keys = _dotenv_defined_keys(server_env_file) if server_env_file is not None else set()
        resolved_env: dict[str, str] = {}
        for ek, ev in raw_env.items():
            val = str(ev)
            val = val.replace("${PLUGIN_DATA}", str(plugin_data_dir)).replace("${PLUGIN_ROOT}", str(plugin_dir))
            m_env = SHELL_ENV_DEFAULT_RE.match(val)
            if m_env:
                env_key, env_def = m_env.group(1), m_env.group(2) or ""
                if env_key not in os.environ and ek in dotenv_keys:
                    # Do not shadow keys loaded via `uv run --env-file` with empty/default placeholders
                    continue
                val = os.environ.get(env_key, env_def)
            resolved_env[ek] = val

        if server_env_file is not None:
            resolved_env.update(_load_non_secret_dotenv_overrides(server_env_file))

        for k_pass in K8S_PASSTHROUGH_ENV_KEYS:
            if k_pass in os.environ and os.environ[k_pass]:
                resolved_env[k_pass] = os.environ[k_pass]

        if is_talkops_k8s_mcp:
            if isolated_kubeconfig is not None:
                kc_str = str(isolated_kubeconfig.resolve())
                resolved_env["KUBECONFIG"] = kc_str
                resolved_env["K8S_KUBECONFIG"] = kc_str
            if kube_context:
                resolved_env["K8S_CONTEXT"] = kube_context
                resolved_env["KUBE_CONTEXT"] = kube_context

        if mcp_allow_write in ("true", "false"):
            resolved_env["MCP_ALLOW_WRITE"] = mcp_allow_write
        elif mcp_allow_write == "auto" and is_talkops_k8s_mcp and "MCP_ALLOW_WRITE" not in os.environ:
            resolved_env["MCP_ALLOW_WRITE"] = "true"

        if aws_profile and "AWS_PROFILE" not in resolved_env and not is_talkops_k8s_mcp:
            resolved_env["AWS_PROFILE"] = aws_profile
            resolved_env["AWS_DEFAULT_PROFILE"] = aws_profile
        if aws_region and "AWS_REGION" not in resolved_env and not is_talkops_k8s_mcp:
            resolved_env["AWS_REGION"] = aws_region
            resolved_env["AWS_DEFAULT_REGION"] = aws_region

        cfg["env"] = resolved_env

    return cfg


def prepare_isolated_workspace(
    run_dir: Path,
    mounted_skills: list[str],
    skill_map: dict[str, list[Path]],
    primary_skill: str,
    input_files: list[str] | None = None,
    mount_plugin_ecosystem: bool = True,
    aws_profile: str | None = None,
    aws_region: str | None = None,
    mcp_src_dir: str | Path | None = None,
    disable_local_mcp: bool = False,
    mcp_allow_write: str = "auto",
    kube_context: str | None = K8S_DEFAULT_CONTEXT,
) -> Path:
    """Create an isolated workspace mounting the skill and its associated plugin ecosystem."""
    ws = run_dir / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / ".git").mkdir(exist_ok=True)
    plugin_data_dir = ws / ".plugin-data"
    plugin_data_dir.mkdir(parents=True, exist_ok=True)
    local_mcp_src = resolve_local_mcp_src_dir(mcp_src_dir, disable_local_mcp=disable_local_mcp)

    agents_dir = ws / ".agents"
    agents_skills_dir = agents_dir / "skills"
    claude_skills_dir = ws / ".claude" / "skills"
    agents_skills_dir.mkdir(parents=True, exist_ok=True)
    claude_skills_dir.mkdir(parents=True, exist_ok=True)

    for s_name in mounted_skills:
        src_dir = resolve_canonical_skill_dir(s_name, skill_map)
        for dest_parent in (agents_skills_dir, claude_skills_dir):
            dest = dest_parent / s_name
            if not dest.exists():
                os.symlink(src_dir, dest, target_is_directory=True)

    skills_json = {
        "entries": [{"path": ".agents/skills", "include_only": mounted_skills}] if mounted_skills else []
    }
    dump_json(agents_dir / "skills.json", skills_json)

    if mount_plugin_ecosystem and primary_skill in skill_map:
        assoc_plugins = resolve_associated_plugins(primary_skill, skill_map)
        if assoc_plugins:
            p_dir = assoc_plugins[0]
            p_name = p_dir.name

            # 1. Stage Commands (`commands/*.md` and `.claude/commands/*.md`) across associated plugins
            for ap_dir in assoc_plugins:
                src_cmds = ap_dir / "commands"
                if src_cmds.is_dir():
                    ws_cmds = ws / "commands"
                    claude_cmds = ws / ".claude" / "commands"
                    ws_cmds.mkdir(parents=True, exist_ok=True)
                    claude_cmds.mkdir(parents=True, exist_ok=True)
                    for cmd_md in src_cmds.glob("*.md"):
                        if not (ws_cmds / cmd_md.name).exists():
                            os.symlink(cmd_md, ws_cmds / cmd_md.name)
                        if not (claude_cmds / cmd_md.name).exists():
                            os.symlink(cmd_md, claude_cmds / cmd_md.name)

            # 2. Stage Plugin-level scripts (`plugin_scripts/`) and Agent Definition (`AGENTS.md`) if present
            src_p_scripts = p_dir / "scripts"
            if src_p_scripts.is_dir() and not (ws / "plugin_scripts").exists():
                os.symlink(src_p_scripts, ws / "plugin_scripts", target_is_directory=True)

            if mounted_skills:
                agent_mds = sorted((p_dir / "agents").glob("*.md")) if (p_dir / "agents").is_dir() else []
                if agent_mds and not (ws / "AGENTS.md").exists():
                    raw_agent_md = agent_mds[0].read_text(encoding="utf-8")
                    *_, agent_body = parse_frontmatter(raw_agent_md)
                    body_txt = (agent_body or raw_agent_md).strip() + "\n"
                    (ws / "AGENTS.md").write_text(body_txt, encoding="utf-8")
                    if not (ws / "CLAUDE.md").exists():
                        (ws / "CLAUDE.md").write_text(body_txt, encoding="utf-8")

            # 3. Stage MCP Server Configuration (`mcp_config.json`, `mcp.json`, `.mcp.json`)
            agy_plugin_dir = agents_dir / "plugins" / p_name
            agy_plugin_dir.mkdir(parents=True, exist_ok=True)
            dump_json(agy_plugin_dir / "plugin.json", {"name": p_name})

            isolated_kc: Path | None = None
            resolved_k8s_ctx: str | None = None
            if _plugin_uses_talkops_k8s_mcp(p_dir):
                isolated_kc, resolved_k8s_ctx = stage_isolated_kubeconfig(ws, kube_context=kube_context)

            src_mcp = p_dir / "mcp.json"
            if src_mcp.exists():
                mcp_raw = load_json(src_mcp)
                agy_servers: dict[str, Any] = {}
                portable_servers: dict[str, Any] = {}
                for srv_name, srv_cfg in mcp_raw.get("mcpServers", {}).items():
                    agy_servers[srv_name] = _rewrite_mcp_server_config(
                        srv_cfg,
                        plugin_dir=p_dir,
                        plugin_data_dir=plugin_data_dir,
                        aws_profile=aws_profile,
                        aws_region=aws_region,
                        local_mcp_src=local_mcp_src,
                        mcp_allow_write=mcp_allow_write,
                        kube_context=resolved_k8s_ctx,
                        isolated_kubeconfig=isolated_kc,
                        strip_type=True,
                    )
                    portable_servers[srv_name] = _rewrite_mcp_server_config(
                        srv_cfg,
                        plugin_dir=p_dir,
                        plugin_data_dir=plugin_data_dir,
                        aws_profile=aws_profile,
                        aws_region=aws_region,
                        local_mcp_src=local_mcp_src,
                        mcp_allow_write=mcp_allow_write,
                        kube_context=resolved_k8s_ctx,
                        isolated_kubeconfig=isolated_kc,
                        strip_type=False,
                    )
                dump_json(agents_dir / "mcp_config.json", {"mcpServers": agy_servers})
                dump_json(agy_plugin_dir / "mcp_config.json", {"mcpServers": agy_servers})
                if not (ws / "mcp.json").exists():
                    out_portable = dict(mcp_raw)
                    out_portable["mcpServers"] = portable_servers
                    dump_json(ws / "mcp.json", out_portable)
            if (p_dir / ".mcp.json").exists() and not (ws / ".mcp.json").exists():
                dot_mcp_raw = load_json(p_dir / ".mcp.json")
                dot_servers: dict[str, Any] = {}
                for srv_name, srv_cfg in dot_mcp_raw.get("mcpServers", {}).items():
                    dot_servers[srv_name] = _rewrite_mcp_server_config(
                        srv_cfg,
                        plugin_dir=p_dir,
                        plugin_data_dir=plugin_data_dir,
                        aws_profile=aws_profile,
                        aws_region=aws_region,
                        local_mcp_src=local_mcp_src,
                        mcp_allow_write=mcp_allow_write,
                        kube_context=resolved_k8s_ctx,
                        isolated_kubeconfig=isolated_kc,
                        strip_type=False,
                    )
                out_dot = dict(dot_mcp_raw)
                out_dot["mcpServers"] = dot_servers
                dump_json(ws / ".mcp.json", out_dot)

            # 4. Stage Plugin Hooks (`.agents/hooks.json` for `agy` + `hooks/` for `claude`/`codex`)
            src_hooks_dir = p_dir / "hooks"
            if src_hooks_dir.is_dir():
                if not (ws / "hooks").exists():
                    os.symlink(src_hooks_dir, ws / "hooks", target_is_directory=True)
                bridge_path = agents_dir / "agy_hook_bridge.py"
                bridge_path.write_text(AGY_HOOK_BRIDGE_SCRIPT)
                bridge_path.chmod(0o755)
                hook_cmd = f"EVAL_PLUGIN_HOOKS_DIR={src_hooks_dir} {sys.executable} {bridge_path}"
                plugin_hook_entry: dict[str, Any] = {
                    "enabled": True,
                    "PreToolUse": [
                        {
                            "matcher": "run_command|call_mcp_tool|mcp_.*",
                            "hooks": [{"type": "command", "command": hook_cmd, "timeout": 10}],
                        }
                    ],
                }
                if (src_hooks_dir / "iac-post-write-lint.py").exists():
                    plugin_hook_entry["PostToolUse"] = [
                        {
                            "matcher": "write_file|edit_file",
                            "hooks": [{"type": "command", "command": hook_cmd, "timeout": 10}],
                        }
                    ]
                agy_hooks_cfg = {f"{p_name}-hooks": plugin_hook_entry}
                dump_json(agents_dir / "hooks.json", agy_hooks_cfg)

    for rel_file in input_files or []:
        cand_skill = (SKILLS_EVALS_DIR / primary_skill / rel_file).resolve()
        cand_repo = (REPO_ROOT / rel_file).resolve()
        src_f = cand_skill if cand_skill.exists() else cand_repo
        if src_f.exists():
            # Stage at both workspace root basename (e.g. `agent-context.json`) and relative path (`files/agent-context.json`)
            shutil.copy2(src_f, ws / Path(rel_file).name)
            dst_nested = ws / rel_file
            dst_nested.parent.mkdir(parents=True, exist_ok=True)
            if dst_nested.resolve() != (ws / Path(rel_file).name).resolve():
                shutil.copy2(src_f, dst_nested)

    return ws


def _extract_skill_name_from_path(path_str: str) -> str | None:
    m = re.search(r"skills/([a-z0-9][a-z0-9-]*)/SKILL\.md", path_str.replace("\\", "/"))
    return m.group(1) if m else None


def _load_hook_audit(workspace_dir: Path) -> list[dict[str, Any]]:
    audit_file = workspace_dir / "hook_audit.jsonl"
    if not audit_file.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in audit_file.read_text(errors="ignore").splitlines():
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def parse_agy_trace(
    stream_stdout: str,
    elapsed_ms: int,
    workspace_dir: Path,
    requested_model: str = AGY_DEFAULT_MODEL,
    requested_effort: str = AGY_DEFAULT_EFFORT,
) -> NormalizedTrace:
    """Parse `agy -p --output-format stream-json` output + brain transcript.jsonl + hook_audit.jsonl."""
    trace = NormalizedTrace(
        harness="agy",
        model=requested_model,
        effort=requested_effort,
        duration_ms=elapsed_ms,
    )
    known_servers: list[str] = []
    ws_mcp_cfg = workspace_dir / ".agents" / "mcp_config.json"
    if ws_mcp_cfg.exists():
        try:
            known_servers = sorted((load_json(ws_mcp_cfg).get("mcpServers") or {}).keys(), key=len, reverse=True)
        except Exception:
            known_servers = []

    def _split_eager_mcp_tool(full_name: str) -> tuple[str, str]:
        rest = full_name[4:]
        for ks in known_servers:
            for prefix in (f"{ks}_", f"{ks.replace('-', '_')}_"):
                if rest.startswith(prefix):
                    return ks, rest[len(prefix):]
        parts = rest.split("_", 1)
        return (parts[0], parts[1]) if len(parts) == 2 else ("mcp", rest)

    for raw_line in stream_stdout.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        trace.raw_events.append(evt)
        if evt.get("event") == "init":
            trace.conversation_id = evt.get("conversation_id", "")
        elif evt.get("event") == "step_update":
            su = evt.get("step_update", {}) or {}
            if su.get("step_type") == "tool" and su.get("state") == "DONE":
                t_info = su.get("tool_info", {}) or {}
                t_name = su.get("tool_name") or t_info.get("name") or ""
                params = t_info.get("parameters", {}) or {}
                if t_name in ("read_file", "view_file"):
                    p = str(params.get("Path") or params.get("AbsolutePath") or params.get("path") or "")
                    if p and p not in trace.files_read:
                        trace.files_read.append(p)
                        sk = _extract_skill_name_from_path(p)
                        if sk and sk not in trace.skills_invoked:
                            trace.skills_invoked.append(sk)
                elif t_name == "run_command":
                    cmd = str(params.get("CommandLine") or params.get("command") or "")
                    out_str = str(t_info.get("output", ""))
                    m_code = re.search(r"Command exited with code (\d+)", out_str)
                    code = int(m_code.group(1)) if m_code else 0
                    if cmd and not any(c.command == cmd for c in trace.commands_run):
                        trace.commands_run.append(
                            CommandRecord(command=cmd, exit_code=code, output_preview=out_str[:400])
                        )
                elif t_name in ("read_resource", "list_resources"):
                    srv = str(params.get("ServerName", ""))
                    uri = str(params.get("Uri", ""))
                    tl = f"{t_name}:{uri}" if uri else t_name
                    trace.mcp_tools_called.append(
                        MCPToolRecord(server=srv, tool_name=tl, arguments=params if isinstance(params, dict) else {})
                    )
                elif t_name == "call_mcp_tool":
                    srv = str(params.get("ServerName", ""))
                    tl = str(params.get("ToolName", ""))
                    t_args = params.get("Arguments", {}) or {}
                    trace.mcp_tools_called.append(
                        MCPToolRecord(server=srv, tool_name=tl, arguments=t_args if isinstance(t_args, dict) else {})
                    )
                elif t_name.startswith("mcp_"):
                    srv, tl = _split_eager_mcp_tool(t_name)
                    trace.mcp_tools_called.append(
                        MCPToolRecord(server=srv, tool_name=tl, arguments=params if isinstance(params, dict) else {})
                    )
        elif evt.get("event") == "result":
            res = evt.get("result", {})
            trace.conversation_id = res.get("conversation_id", trace.conversation_id)
            trace.final_response = res.get("response", "")
            trace.num_turns = int(res.get("num_turns", 0))
            if res.get("duration_seconds"):
                trace.duration_ms = int(float(res["duration_seconds"]) * 1000)
            usage = res.get("usage", {})
            trace.input_tokens = int(usage.get("input_tokens", 0))
            trace.output_tokens = int(usage.get("output_tokens", 0))
            trace.total_tokens = int(usage.get("total_tokens", trace.input_tokens + trace.output_tokens))

    if trace.conversation_id:
        logs_dir = AGY_BRAIN_DIR / trace.conversation_id / ".system_generated" / "logs"
        transcript_path = logs_dir / "transcript_full.jsonl"
        if not transcript_path.exists():
            transcript_path = logs_dir / "transcript.jsonl"
        if transcript_path.exists():
            in_tok_sum = 0
            out_tok_sum = 0
            last_planner_text = ""
            planner_turns = 0
            transcript_mcp_calls: list[MCPToolRecord] = []
            for raw_line in transcript_path.read_text(errors="ignore").splitlines():
                if not raw_line.strip():
                    continue
                try:
                    step = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if step.get("type") == "PLANNER_RESPONSE":
                    planner_turns += 1
                    in_tok_sum += int(step.get("input_tokens", 0) or 0)
                    out_tok_sum += int(step.get("output_tokens", 0) or 0)
                    if step.get("model") and isinstance(step.get("model"), str):
                        trace.model = step["model"]
                    if step.get("content") and isinstance(step.get("content"), str):
                        last_planner_text = step["content"]
                for tc in step.get("tool_calls", []) or []:
                    t_name = tc.get("name", "") or tc.get("tool_name", "")
                    args = tc.get("arguments") or tc.get("args") or tc.get("input") or {}
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    if t_name in ("read_file", "view_file"):
                        p = str(args.get("Path") or args.get("AbsolutePath") or args.get("path") or "")
                        if p and p not in trace.files_read:
                            trace.files_read.append(p)
                            sk = _extract_skill_name_from_path(p)
                            if sk and sk not in trace.skills_invoked:
                                trace.skills_invoked.append(sk)
                    elif t_name == "run_command":
                        cmd = str(args.get("CommandLine") or args.get("command") or "")
                        if cmd and not any(c.command == cmd for c in trace.commands_run):
                            trace.commands_run.append(CommandRecord(command=cmd, exit_code=0))
                    elif t_name in ("read_resource", "list_resources"):
                        srv = str(args.get("ServerName", ""))
                        uri = str(args.get("Uri", ""))
                        tl = f"{t_name}:{uri}" if uri else t_name
                        transcript_mcp_calls.append(
                            MCPToolRecord(server=srv, tool_name=tl, arguments=args if isinstance(args, dict) else {})
                        )
                    elif t_name == "call_mcp_tool":
                        srv = str(args.get("ServerName", ""))
                        tl = str(args.get("ToolName", ""))
                        t_args = args.get("Arguments", {}) if isinstance(args, dict) else {}
                        if isinstance(t_args, str):
                            try:
                                t_args = json.loads(t_args)
                            except json.JSONDecodeError:
                                t_args = {}
                        if srv or tl:
                            transcript_mcp_calls.append(
                                MCPToolRecord(server=srv, tool_name=tl, arguments=t_args if isinstance(t_args, dict) else {})
                            )
                    elif t_name.startswith("mcp_"):
                        srv, tl = _split_eager_mcp_tool(t_name)
                        transcript_mcp_calls.append(
                            MCPToolRecord(server=srv, tool_name=tl, arguments=args if isinstance(args, dict) else {})
                        )
            if transcript_mcp_calls:
                trace.mcp_tools_called = transcript_mcp_calls
            if not trace.final_response and last_planner_text:
                trace.final_response = last_planner_text
            if trace.total_tokens == 0 and (in_tok_sum + out_tok_sum) > 0:
                trace.input_tokens = in_tok_sum
                trace.output_tokens = out_tok_sum
                trace.total_tokens = in_tok_sum + out_tok_sum
            if trace.num_turns == 0 and planner_turns > 0:
                trace.num_turns = planner_turns

    trace.hook_audit = _load_hook_audit(workspace_dir)
    return trace


def parse_codex_trace(jsonl_stdout: str, elapsed_ms: int, workspace_dir: Path) -> NormalizedTrace:
    trace = NormalizedTrace(harness="codex", duration_ms=elapsed_ms)
    for raw_line in jsonl_stdout.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        trace.raw_events.append(evt)
        etype = evt.get("type", "")
        item = evt.get("item", {}) or {}
        if etype == "item.completed":
            itype = item.get("type", "")
            if itype == "command_execution":
                cmd = str(item.get("command", ""))
                code = item.get("exit_code")
                trace.commands_run.append(CommandRecord(command=cmd, exit_code=code))
                sk = _extract_skill_name_from_path(cmd)
                if sk and sk not in trace.skills_invoked:
                    trace.skills_invoked.append(sk)
                for m in RELATIVE_REF_RE.findall(cmd):
                    trace.files_read.append(m)
            elif itype == "mcp_tool_call":
                trace.mcp_tools_called.append(
                    MCPToolRecord(server=str(item.get("server", "")), tool_name=str(item.get("tool", "")))
                )
            elif itype in ("agent_message", "message"):
                text = item.get("text") or item.get("content") or ""
                if isinstance(text, str) and text:
                    trace.final_response = text
        elif etype == "turn.completed":
            trace.num_turns += 1
            usage = evt.get("usage", {})
            trace.input_tokens += int(usage.get("input_tokens", 0))
            trace.output_tokens += int(usage.get("output_tokens", 0))
            trace.total_tokens = trace.input_tokens + trace.output_tokens
    trace.hook_audit = _load_hook_audit(workspace_dir)
    return trace


def parse_claude_trace(json_stdout: str, elapsed_ms: int, workspace_dir: Path) -> NormalizedTrace:
    trace = NormalizedTrace(harness="claude", duration_ms=elapsed_ms)
    try:
        data = json.loads(json_stdout)
    except json.JSONDecodeError:
        trace.final_response = json_stdout.strip()
        return trace
    trace.raw_events.append(data)
    trace.final_response = str(data.get("result", ""))
    trace.duration_ms = int(data.get("duration_ms", elapsed_ms))
    trace.num_turns = int(data.get("num_turns", 1))
    usage = data.get("usage", {})
    trace.input_tokens = int(usage.get("input_tokens", 0))
    trace.output_tokens = int(usage.get("output_tokens", 0))
    trace.total_tokens = trace.input_tokens + trace.output_tokens
    for msg in data.get("messages", []) or []:
        for block in msg.get("content", []) if isinstance(msg.get("content"), list) else []:
            if block.get("type") == "tool_use":
                name = block.get("name", "")
                inp = block.get("input", {}) or {}
                if name == "Skill":
                    sk = str(inp.get("skill", ""))
                    if sk and sk not in trace.skills_invoked:
                        trace.skills_invoked.append(sk)
                elif name in ("Read", "read_file"):
                    p = str(inp.get("file_path") or inp.get("path") or "")
                    if p:
                        trace.files_read.append(p)
                        sk = _extract_skill_name_from_path(p)
                        if sk and sk not in trace.skills_invoked:
                            trace.skills_invoked.append(sk)
                elif name == "Bash":
                    cmd = str(inp.get("command", ""))
                    if cmd:
                        trace.commands_run.append(CommandRecord(command=cmd, exit_code=0))
                elif name.startswith("mcp__"):
                    parts = name.split("__")
                    srv = parts[1] if len(parts) > 2 else "mcp"
                    tl = parts[-1]
                    trace.mcp_tools_called.append(MCPToolRecord(server=srv, tool_name=tl, arguments=inp))
    trace.hook_audit = _load_hook_audit(workspace_dir)
    return trace


def execute_agent_run(
    harness: str,
    prompt: str,
    workspace_dir: Path,
    aws_profile: str | None = None,
    aws_region: str | None = None,
    timeout_sec: int = 180,
    mcp_src_dir: str | Path | None = None,
    disable_local_mcp: bool = False,
    model: str | None = None,
    effort: str | None = None,
    kube_context: str | None = None,
) -> NormalizedTrace:
    """Run the natural `prompt` verbatim in `workspace_dir` with live AWS / local MCP environment."""
    env = build_aws_env(
        aws_profile=aws_profile,
        aws_region=aws_region,
        mcp_src_dir=mcp_src_dir,
        disable_local_mcp=disable_local_mcp,
    )
    ws_kubeconfig = workspace_dir / ".kube" / "config"
    if ws_kubeconfig.exists():
        kc_abs = str(ws_kubeconfig.resolve())
        env["KUBECONFIG"] = kc_abs
        env["K8S_KUBECONFIG"] = kc_abs
        eff_k8s_ctx = (
            kube_context
            or os.environ.get("K8S_CONTEXT")
            or os.environ.get("KUBE_CONTEXT")
            or K8S_DEFAULT_CONTEXT
        ).strip()
        env["K8S_CONTEXT"] = eff_k8s_ctx
        env["KUBE_CONTEXT"] = eff_k8s_ctx

    agy_model = ""
    agy_effort = ""
    if harness == "agy":
        agy_model, agy_effort = resolve_agy_model_and_effort(model=model, effort=effort)
        env.pop("AGY_MODEL", None)
        env.pop("ANTIGRAVITY_MODEL", None)
        cmd = [
            "agy",
            "-p",
            prompt,
            "--model",
            agy_model,
            "--effort",
            agy_effort,
            "--output-format",
            "stream-json",
            "--new-project",
            "--dangerously-skip-permissions",
        ]
    elif harness == "codex":
        cmd = [
            "codex",
            "exec",
            "--json",
            "--sandbox",
            "workspace-write",
            *(["--model", model] if model else []),
            prompt,
        ]
    elif harness == "claude":
        cmd = [
            "claude",
            "-p",
            prompt,
            "--output-format",
            "json",
            *(["--model", model] if model else []),
        ]
    else:
        raise ValueError(f"Unsupported harness: {harness}")

    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(workspace_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        stdout_str = proc.stdout or ""
    except subprocess.TimeoutExpired as exc:
        raw_out = exc.stdout or ""
        stdout_str = raw_out.decode("utf-8", errors="ignore") if isinstance(raw_out, bytes) else str(raw_out)
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    if harness == "agy":
        return parse_agy_trace(
            stdout_str,
            elapsed_ms,
            workspace_dir,
            requested_model=agy_model,
            requested_effort=agy_effort,
        )
    if harness == "codex":
        tr = parse_codex_trace(stdout_str, elapsed_ms, workspace_dir)
        tr.model = model or ""
        return tr
    tr = parse_claude_trace(stdout_str, elapsed_ms, workspace_dir)
    tr.model = model or ""
    return tr


# ---------------------------------------------------------------------------
# Expectation Grader (Evaluates Query -> Expectations against Trace + Output)
# ---------------------------------------------------------------------------


def build_trace_telemetry_summary(trace: NormalizedTrace) -> dict[str, Any]:
    """Summarize the observed tool trajectory without hardcoding any file or script checks."""
    return {
        "skills_activated": trace.skills_invoked,
        "mcp_tools_called": [
            {"server": m.server, "tool": m.tool_name, "arguments": m.arguments}
            for m in trace.mcp_tools_called
        ],
        "shell_commands_run": [
            {"command": c.command, "exit_code": c.exit_code}
            for c in trace.commands_run
        ],
        "files_and_references_read": [
            Path(f).name if "skills/" not in f else f[f.find("skills/") :]
            for f in trace.files_read
        ],
        "hooks_triggered": [
            {
                "tool": h.get("hook_tool_name"),
                "secret_safety": h.get("secret_safety_decision"),
                "mutation_gate": h.get("mutation_gate_decision"),
                "final_decision": h.get("final_decision"),
            }
            for h in trace.hook_audit
        ],
    }


def grade_expectations_with_judge(
    harness: str,
    prompt: str,
    expected_output: str,
    trace: NormalizedTrace,
    expectations: list[str],
    timeout_sec: int = 240,
    model: str | None = None,
    effort: str | None = None,
) -> list[dict[str, Any]]:
    """Grade `expectations` against the observed execution trace and agent response.

    If all expectations match -> GREEN (`passed: true`);
    otherwise -> RED (`passed: false`), signaling that the skill or its components need to be revisited.
    """
    schema_path = SCHEMAS_DIR / "grading_rubric.schema.json"
    telemetry = build_trace_telemetry_summary(trace)
    expectations_numbered = "\n".join(f"{i+1}. {e}" for i, e in enumerate(expectations))
    judge_prompt = f"""You are a strict, calibrated binary evaluator grading an AI agent's skill execution against expected outcomes.

## Grading Rules
1. Evaluate each expectation independently as strictly PASS (`passed: true`) or FAIL (`passed: false`). No partial credit.
2. Use BOTH the Observed Execution Telemetry (skills activated, MCP tools called, shell commands run, files read, hooks triggered) AND the Agent Final Response to verify each expectation.
3. If an expectation requires using connected MCP tools (e.g., AWS or Kubernetes/TalkOps MCP tools) rather than raw CLI shell commands (`aws`, `kubectl`, `helm`, `argocd`, `kargo`), or requires activating a skill or running a bundled script, verify this directly from `Observed Execution Telemetry`.
4. Cite concrete evidence from `Observed Execution Telemetry` or `Agent Final Response` in `evidence`.
5. Do NOT execute any tools or commands—evaluate only the telemetry and response provided below.

## User Query
{prompt}

## Expected Output Summary
{expected_output}

## Observed Execution Telemetry
```json
{json.dumps(telemetry, indent=2)}
```

## Expectations to Grade
{expectations_numbered}

## Agent Final Response
{trace.final_response}

Return ONLY valid JSON conforming to the grading rubric schema with one entry per expectation in `assertion_results`.
"""
    env = build_aws_env()
    if harness == "agy":
        agy_model, agy_effort = resolve_agy_model_and_effort(model=model, effort=effort)
        env.pop("AGY_MODEL", None)
        env.pop("ANTIGRAVITY_MODEL", None)
        cmd = [
            "agy",
            "-p",
            judge_prompt,
            "--model",
            agy_model,
            "--effort",
            agy_effort,
            "--output-format",
            "json",
            "--json-schema",
            str(schema_path),
        ]
    elif harness == "codex":
        out_tmp = Path(tempfile.mktemp(suffix=".json"))
        cmd = [
            "codex",
            "exec",
            *(["--model", model] if model else []),
            judge_prompt,
            "--output-schema",
            str(schema_path),
            "-o",
            str(out_tmp),
        ]
    else:
        cmd = [
            "claude",
            "-p",
            judge_prompt,
            "--output-format",
            "json",
            *(["--model", model] if model else []),
        ]

    def _extract_json_dicts(blob: str) -> list[dict[str, Any]]:
        objs: list[dict[str, Any]] = []
        decoder = json.JSONDecoder()
        idx = 0
        n = len(blob)
        while idx < n:
            brace = blob.find("{", idx)
            if brace == -1:
                break
            try:
                val, end_idx = decoder.raw_decode(blob, brace)
                if isinstance(val, dict):
                    objs.append(val)
                idx = end_idx
            except json.JSONDecodeError:
                idx = brace + 1
        return objs

    def _find_assertion_results(candidate: Any) -> list[dict[str, Any]] | None:
        if not isinstance(candidate, dict):
            return None
        so = candidate.get("structured_output")
        if isinstance(so, dict) and isinstance(so.get("assertion_results"), list):
            return so["assertion_results"]
        if isinstance(candidate.get("assertion_results"), list):
            return candidate["assertion_results"]
        for key in ("result", "response"):
            sub = candidate.get(key)
            if isinstance(sub, dict):
                found = _find_assertion_results(sub)
                if found is not None:
                    return found
            elif isinstance(sub, str):
                for inner_obj in reversed(_extract_json_dicts(sub)):
                    found = _find_assertion_results(inner_obj)
                    if found is not None:
                        return found
        return None

    out_tmp: Path | None = None
    if harness == "codex":
        for i, arg in enumerate(cmd):
            if arg == "-o" and i + 1 < len(cmd):
                out_tmp = Path(cmd[i + 1])

    last_err = ""
    for _attempt in range(2):
        try:
            proc = subprocess.run(
                cmd,
                cwd=tempfile.gettempdir(),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            blobs = [proc.stdout.strip()]
            if out_tmp and out_tmp.exists():
                blobs.insert(0, out_tmp.read_text(errors="ignore").strip())
            for blob in blobs:
                if not blob:
                    continue
                for parsed in reversed(_extract_json_dicts(blob)):
                    raw_assertions = _find_assertion_results(parsed)
                    if raw_assertions is not None:
                        return [
                            {
                                "text": str(item.get("text", "")),
                                "passed": bool(item.get("passed", False)),
                                "evidence": str(item.get("evidence", "")),
                            }
                            for item in raw_assertions
                        ]
        except Exception as exc:
            last_err = str(exc)

    if last_err:
        return [
            {
                "text": e,
                "passed": False,
                "evidence": f"Judge invocation error: {last_err}",
            }
            for e in expectations
        ]

    return [
        {
            "text": e,
            "passed": False,
            "evidence": "Failed to parse structured JSON from judge response.",
        }
        for e in expectations
    ]


# ---------------------------------------------------------------------------
# Subcommand: `trigger`
# ---------------------------------------------------------------------------


def run_trigger_evals(args: argparse.Namespace) -> int:
    resolved_model = getattr(args, "model", None) or ""
    resolved_effort = getattr(args, "effort", None) or ""
    if args.harness == "agy":
        try:
            resolved_model, resolved_effort = resolve_agy_model_and_effort(
                model=getattr(args, "model", None),
                effort=getattr(args, "effort", None),
            )
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return 2

    skill_map = discover_skill_paths()
    skill_name = args.skill
    if skill_name not in skill_map:
        print(f"ERROR: Skill '{skill_name}' not found.")
        return 1

    trig_path = SKILLS_EVALS_DIR / skill_name / "trigger_evals.json"
    if not trig_path.exists():
        print(f"ERROR: Trigger suite not found at {trig_path.relative_to(REPO_ROOT)}")
        return 1

    suite = load_json(trig_path)
    if isinstance(suite, list):
        suite = {"skill_name": skill_name, "companion_skills": [], "queries": suite}
    companions = [c for c in suite.get("companion_skills", []) if c in skill_map]
    mounted_skills = [skill_name, *[c for c in companions if c != skill_name]]
    raw_queries = suite.get("queries", [])
    queries: list[dict[str, Any]] = []
    for idx, q in enumerate(raw_queries, start=1):
        norm_q = dict(q)
        norm_q.setdefault("id", f"trigger-{idx:02d}")
        if "prompt" not in norm_q and "query" in norm_q:
            norm_q["prompt"] = norm_q["query"]
        norm_q.setdefault(
            "quadrant",
            "should_trigger" if norm_q.get("should_trigger", True) else "should_not_trigger",
        )
        norm_q.setdefault("split", "train")
        queries.append(norm_q)
    if args.split in ("train", "val"):
        queries = [q for q in queries if q.get("split") == args.split]
    if args.query_id:
        queries = [q for q in queries if q.get("id") == args.query_id]

    if not queries:
        print("No matching trigger queries to run.")
        return 1

    model_info = (
        f", model={resolved_model}, effort={resolved_effort}"
        if args.harness == "agy"
        else (f", model={resolved_model}" if resolved_model else "")
    )
    if args.dry_run:
        print(
            f"Running Trigger Evals [DRY-RUN] for '{skill_name}' "
            f"(harness={args.harness}{model_info}, split={args.split}, queries={len(queries)}, runs={args.runs})"
        )
        print(f"Mounted catalog ({len(mounted_skills)} skills): {', '.join(mounted_skills)}\n")
        for q in queries:
            print(
                f"  [DRY-RUN] {q['id']} ({q['quadrant']}, split={q['split']}, "
                f"should_trigger={q['should_trigger']}): {q['prompt'][:90]}..."
            )
        return 0

    iter_dir = next_iteration_dir(skill_name)
    print(
        f"Running Trigger Evals for '{skill_name}' "
        f"(harness={args.harness}{model_info}, split={args.split}, queries={len(queries)}, runs={args.runs})"
    )
    print(f"Mounted catalog ({len(mounted_skills)} skills): {', '.join(mounted_skills)}")
    print(f"Workspace output: {_display_path(iter_dir)}\n")

    from concurrent.futures import ThreadPoolExecutor, as_completed

    query_results: list[dict[str, Any]] = []
    passed_queries = 0

    def _run_trig_query(q: dict[str, Any]) -> dict[str, Any]:
        qid = q["id"]
        should_trigger = bool(q["should_trigger"])
        triggers = 0
        invoked_lists: list[list[str]] = []

        for r_idx in range(1, args.runs + 1):
            q_run_dir = iter_dir / "trigger" / qid / f"run-{r_idx}"
            ws = prepare_isolated_workspace(
                q_run_dir,
                mounted_skills=mounted_skills,
                skill_map=skill_map,
                primary_skill=skill_name,
                aws_profile=args.aws_profile,
                aws_region=args.aws_region,
                mcp_src_dir=args.mcp_src_dir,
                disable_local_mcp=args.use_uvx_mcp,
                mcp_allow_write=args.mcp_allow_write,
                kube_context=args.kube_context,
            )
            trace = execute_agent_run(
                args.harness,
                q["prompt"],
                ws,
                aws_profile=args.aws_profile,
                aws_region=args.aws_region,
                timeout_sec=args.timeout,
                mcp_src_dir=args.mcp_src_dir,
                disable_local_mcp=args.use_uvx_mcp,
                model=resolved_model or None,
                effort=resolved_effort or None,
                kube_context=args.kube_context,
            )
            triggered = skill_name in trace.skills_invoked
            if triggered:
                triggers += 1
            invoked_lists.append(trace.skills_invoked)
            dump_json(q_run_dir / "trace.json", asdict(trace))

        trigger_rate = round(triggers / args.runs, 4)
        query_passed = (trigger_rate >= 0.5) if should_trigger else (trigger_rate < 0.5)
        return {
            "id": qid,
            "quadrant": q["quadrant"],
            "split": q["split"],
            "should_trigger": should_trigger,
            "triggers": triggers,
            "runs": args.runs,
            "trigger_rate": trigger_rate,
            "passed": query_passed,
            "skills_invoked_per_run": invoked_lists,
        }

    workers = max(1, int(getattr(args, "workers", 1) or 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_run_trig_query, q) for q in queries]
        for fut in futs:
            q_res = fut.result()
            if q_res["passed"]:
                passed_queries += 1
            status = "GREEN" if q_res["passed"] else "RED"
            print(
                f"  [{status}] {q_res['id']} ({q_res['quadrant']}, should_trigger={q_res['should_trigger']}) "
                f"-> trigger_rate={q_res['trigger_rate']} ({q_res['triggers']}/{q_res['runs']}), invoked={q_res['skills_invoked_per_run']}"
            )
            query_results.append(q_res)

    accuracy = round(passed_queries / len(queries), 4)
    report = {
        "skill_name": skill_name,
        "harness": args.harness,
        "model": resolved_model or None,
        "effort": resolved_effort or None,
        "split": args.split,
        "mounted_skills": mounted_skills,
        "summary": {
            "total_queries": len(queries),
            "passed_queries": passed_queries,
            "failed_queries": len(queries) - passed_queries,
            "accuracy": accuracy,
        },
        "results": query_results,
    }
    report_path = iter_dir / "trigger_report.json"
    dump_json(report_path, report)
    print(f"\nTrigger Eval Accuracy: {accuracy * 100:.1f}% ({passed_queries}/{len(queries)})")
    print(f"Saved report to {_display_path(report_path)}")
    return 0 if passed_queries == len(queries) else 1


# ---------------------------------------------------------------------------
# Subcommand: `run` (Query -> Expectations Skill Evaluation & Benchmarking)
# ---------------------------------------------------------------------------


def _eval_single_deterministic_clause(text: str, clause: str) -> bool:
    clause = clause.strip()
    m_not = re.match(r"^not\s+contains\s+(['\"])(.*?)\1$", clause, re.S)
    if m_not:
        return m_not.group(2) not in text
    m_con = re.match(r"^contains\s+(['\"])(.*?)\1$", clause, re.S)
    if m_con:
        return m_con.group(2) in text
    m_rx = re.match(r"^matches\s+regex\s+/(.+)/([imsx]*)$", clause, re.S)
    if m_rx:
        flags = 0
        if "i" in m_rx.group(2):
            flags |= re.I
        if "m" in m_rx.group(2):
            flags |= re.M
        if "s" in m_rx.group(2):
            flags |= re.S
        return re.search(m_rx.group(1), text, flags) is not None
    return clause.lower() in text.lower()


def evaluate_deterministic_assertions(text: str, assertions: list[str]) -> list[dict[str, Any]]:
    """Evaluate deterministic `contains '...'`, `not contains '...'`, and `matches regex /.../` assertions."""
    results: list[dict[str, Any]] = []
    for raw_a in assertions:
        or_parts = re.split(r"\s+or\s+(?=(?:not\s+)?contains\s+|matches\s+regex\s+)", raw_a)
        passed = any(_eval_single_deterministic_clause(text, part) for part in or_parts)
        results.append({
            "text": f"[deterministic] {raw_a}",
            "passed": passed,
            "evidence": "Matched response text deterministically" if passed else "Response did not satisfy deterministic assertion",
        })
    return results


def _execute_single_eval_config(
    eval_case: dict[str, Any],
    skill_name: str,
    config_name: str,
    mounted_skills: list[str],
    skill_map: dict[str, list[Path]],
    out_dir: Path,
    harness: str,
    aws_profile: str | None,
    aws_region: str | None,
    timeout_sec: int,
    mcp_src_dir: str | Path | None = None,
    disable_local_mcp: bool = False,
    mcp_allow_write: str = "auto",
    model: str | None = None,
    effort: str | None = None,
    kube_context: str | None = K8S_DEFAULT_CONTEXT,
) -> dict[str, Any]:
    outputs_dir = out_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    case_write = eval_case.get("mcp_allow_write")
    effective_allow_write = (
        ("true" if case_write else "false")
        if isinstance(case_write, bool)
        else (str(case_write).lower() if case_write in ("true", "false") else mcp_allow_write)
    )
    ws = prepare_isolated_workspace(
        out_dir,
        mounted_skills=mounted_skills,
        skill_map=skill_map,
        primary_skill=skill_name,
        input_files=eval_case.get("files", []),
        mount_plugin_ecosystem=(config_name == "with_skill"),
        aws_profile=aws_profile,
        aws_region=aws_region,
        mcp_src_dir=mcp_src_dir,
        disable_local_mcp=disable_local_mcp,
        mcp_allow_write=effective_allow_write,
        kube_context=kube_context,
    )

    trace = execute_agent_run(
        harness,
        eval_case["prompt"],
        ws,
        aws_profile=aws_profile,
        aws_region=aws_region,
        timeout_sec=timeout_sec,
        mcp_src_dir=mcp_src_dir,
        disable_local_mcp=disable_local_mcp,
        model=model,
        effort=effort,
        kube_context=kube_context,
    )
    (outputs_dir / "response.md").write_text(trace.final_response + "\n")

    trace_jsonl_path = out_dir / "trace.jsonl"
    with trace_jsonl_path.open("w", encoding="utf-8") as f:
        for evt in trace.raw_events:
            f.write(json.dumps(evt, ensure_ascii=False) + "\n")
    dump_json(out_dir / "normalized_trace.json", asdict(trace))

    timing = {
        "model": trace.model or model or None,
        "effort": trace.effort or effort or None,
        "total_tokens": trace.total_tokens,
        "input_tokens": trace.input_tokens,
        "output_tokens": trace.output_tokens,
        "duration_ms": trace.duration_ms,
        "num_turns": trace.num_turns,
    }
    dump_json(out_dir / "timing.json", timing)

    expectations = eval_case.get("expectations", [])
    expectation_results = grade_expectations_with_judge(
        harness=harness,
        prompt=eval_case["prompt"],
        expected_output=eval_case.get("expected_output", ""),
        trace=trace,
        expectations=expectations,
        timeout_sec=timeout_sec,
        model=model,
        effort=effort,
    )
    det_assertions = [a for a in (eval_case.get("assertions") or []) if isinstance(a, str) and a.strip()]
    if det_assertions:
        expectation_results.extend(evaluate_deterministic_assertions(trace.final_response, det_assertions))

    passed_cnt = sum(1 for a in expectation_results if a["passed"])
    total_cnt = len(expectation_results)
    pass_rate = round(passed_cnt / total_cnt, 4) if total_cnt else 0.0
    all_passed = passed_cnt == total_cnt and total_cnt > 0
    telemetry = build_trace_telemetry_summary(trace)

    grading = {
        "status": "GREEN" if all_passed else "RED",
        "model": trace.model or model or None,
        "effort": trace.effort or effort or None,
        "action_required": None if all_passed else "Revisit skill or its associated plugin components (references, scripts, MCP servers, commands, hooks)",
        "observed_telemetry": telemetry,
        "assertion_results": expectation_results,
        "summary": {
            "passed": passed_cnt,
            "failed": total_cnt - passed_cnt,
            "total": total_cnt,
            "pass_rate": pass_rate,
        },
    }
    dump_json(out_dir / "grading.json", grading)
    return {
        "pass_rate": pass_rate,
        "all_passed": all_passed,
        "time_seconds": round(trace.duration_ms / 1000.0, 2),
        "tokens": trace.total_tokens,
        "grading": grading,
    }


def _summarize_metric(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "stddev": 0.0}
    mean_v = round(statistics.mean(values), 4)
    sd_v = round(statistics.stdev(values), 4) if len(values) > 1 else 0.0
    return {"mean": mean_v, "stddev": sd_v}


def run_execution_evals(args: argparse.Namespace) -> int:
    resolved_model = getattr(args, "model", None) or ""
    resolved_effort = getattr(args, "effort", None) or ""
    if args.harness == "agy":
        try:
            resolved_model, resolved_effort = resolve_agy_model_and_effort(
                model=getattr(args, "model", None),
                effort=getattr(args, "effort", None),
            )
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return 2

    skill_map = discover_skill_paths()
    skill_name = args.skill
    if skill_name not in skill_map:
        print(f"ERROR: Skill '{skill_name}' not found.")
        return 1

    evals_path = SKILLS_EVALS_DIR / skill_name / "evals.json"
    if not evals_path.exists():
        print(f"ERROR: Execution eval suite not found at {evals_path.relative_to(REPO_ROOT)}")
        return 1

    suite = load_json(evals_path)
    eval_cases = suite.get("evals", [])
    if args.eval_id:
        wanted_ids = [x.strip() for x in str(args.eval_id).split(",") if x.strip()]
        eval_cases = [
            e
            for e in eval_cases
            if any(str(e.get("id")) == w or str(e.get("id")).startswith(f"{w}-") for w in wanted_ids)
        ]
    if not eval_cases:
        print("No matching eval cases found.")
        return 1

    configs = ["with_skill", "without_skill"] if args.baseline else ["with_skill"]
    model_info = (
        f", model={resolved_model}, effort={resolved_effort}"
        if args.harness == "agy"
        else (f", model={resolved_model}" if resolved_model else "")
    )

    if args.dry_run:
        print(
            f"Running Skill Execution Evals [DRY-RUN] for '{skill_name}' "
            f"(harness={args.harness}{model_info}, cases={len(eval_cases)}, runs={args.runs}, configs={configs})\n"
        )
        for ev in eval_cases:
            exps = ev.get("expectations", [])
            print(f"  [DRY-RUN] {ev['id']} (expectations={len(exps)})")
            print(f"    Query: {ev['prompt']}")
        return 0

    iter_dir = next_iteration_dir(skill_name)
    print(
        f"Running Skill Execution Evals for '{skill_name}' "
        f"(harness={args.harness}{model_info}, cases={len(eval_cases)}, runs={args.runs}, configs={configs})"
    )
    print(f"Workspace output: {_display_path(iter_dir)}\n")

    trig_path = SKILLS_EVALS_DIR / skill_name / "trigger_evals.json"
    companions: list[str] = []
    if trig_path.exists():
        t_obj = load_json(trig_path)
        if isinstance(t_obj, dict):
            companions = [
                c for c in t_obj.get("companion_skills", []) if c in skill_map
            ]

    metrics_by_config: dict[str, dict[str, list[float]]] = {
        c: {"pass_rate": [], "time_seconds": [], "tokens": [], "full_pass": []} for c in configs
    }

    tasks_to_run: list[tuple[dict[str, Any], str, str, list[str], int, Path]] = []
    for ev in eval_cases:
        ev_id = str(ev["id"])
        for cfg in configs:
            if cfg == "with_skill":
                mounted = [skill_name, *[c for c in companions if c != skill_name]]
            else:
                mounted = []
            for r_idx in range(1, args.runs + 1):
                run_sub = cfg if args.runs == 1 else f"{cfg}/run-{r_idx}"
                case_out_dir = iter_dir / ev_id / run_sub
                tasks_to_run.append((ev, ev_id, cfg, mounted, r_idx, case_out_dir))

    def _run_one(item: tuple[dict[str, Any], str, str, list[str], int, Path]) -> tuple[str, str, int, dict[str, Any]]:
        ev, ev_id, cfg, mounted, r_idx, case_out_dir = item
        res = _execute_single_eval_config(
            eval_case=ev,
            skill_name=skill_name,
            config_name=cfg,
            mounted_skills=mounted,
            skill_map=skill_map,
            out_dir=case_out_dir,
            harness=args.harness,
            aws_profile=args.aws_profile,
            aws_region=args.aws_region,
            timeout_sec=args.timeout,
            mcp_src_dir=args.mcp_src_dir,
            disable_local_mcp=args.use_uvx_mcp,
            mcp_allow_write=args.mcp_allow_write,
            model=resolved_model or None,
            effort=resolved_effort or None,
            kube_context=args.kube_context,
        )
        return ev_id, cfg, r_idx, res

    from concurrent.futures import ThreadPoolExecutor, as_completed

    workers = max(1, int(getattr(args, "workers", 1) or 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(_run_one, t): t for t in tasks_to_run}
        for fut in as_completed(future_map):
            ev_id, cfg, r_idx, res = fut.result()
            metrics_by_config[cfg]["pass_rate"].append(res["pass_rate"])
            metrics_by_config[cfg]["time_seconds"].append(res["time_seconds"])
            metrics_by_config[cfg]["tokens"].append(float(res["tokens"]))
            metrics_by_config[cfg]["full_pass"].append(1.0 if res["all_passed"] else 0.0)

            s = res["grading"]["summary"]
            status_badge = "GREEN" if res["all_passed"] else "RED (revisit skill/component)"
            tel = res["grading"]["observed_telemetry"]
            print(
                f"  [{status_badge}] [{ev_id}][{cfg}][run {r_idx}] "
                f"expectations={s['passed']}/{s['total']} ({s['pass_rate']*100:.1f}%), "
                f"time={res['time_seconds']}s, tokens={res['tokens']}"
            )
            print(
                f"    Telemetry: skills={tel['skills_activated']}, "
                f"mcp_calls={[m['server'] + ':' + m['tool'] for m in tel['mcp_tools_called']]}, "
                f"commands={[c['command'] for c in tel['shell_commands_run']]}, "
                f"files_read={tel['files_and_references_read']}, "
                f"hooks={len(tel['hooks_triggered'])}"
            )
            for ar in res["grading"]["assertion_results"]:
                mark = "GREEN" if ar["passed"] else "RED"
                print(f"    - [{mark}] {ar['text']}")
                print(f"        Evidence: {ar['evidence']}")

    run_summary: dict[str, Any] = {}
    for cfg in configs:
        m = metrics_by_config[cfg]
        n_trials = len(m["full_pass"])
        c_passed = int(sum(m["full_pass"]))
        run_summary[cfg] = {
            "pass_rate": _summarize_metric(m["pass_rate"]),
            "time_seconds": _summarize_metric(m["time_seconds"]),
            "tokens": _summarize_metric(m["tokens"]),
            "reliability": {
                "trials": n_trials,
                "green_evals": c_passed,
                "red_evals": n_trials - c_passed,
                "pass_at_1": compute_pass_at_k(n_trials, c_passed, 1),
                "pass_hat_3": compute_pass_hat_k(n_trials, c_passed, 3),
            },
        }

    if "with_skill" in run_summary and "without_skill" in run_summary:
        run_summary["delta"] = {
            "pass_rate": round(
                run_summary["with_skill"]["pass_rate"]["mean"]
                - run_summary["without_skill"]["pass_rate"]["mean"],
                4,
            ),
            "time_seconds": round(
                run_summary["with_skill"]["time_seconds"]["mean"]
                - run_summary["without_skill"]["time_seconds"]["mean"],
                2,
            ),
            "tokens": round(
                run_summary["with_skill"]["tokens"]["mean"]
                - run_summary["without_skill"]["tokens"]["mean"],
                1,
            ),
        }

    benchmark_path = iter_dir / "benchmark.json"
    dump_json(
        benchmark_path,
        {
            "skill_name": skill_name,
            "harness": args.harness,
            "model": resolved_model or None,
            "effort": resolved_effort or None,
            "run_summary": run_summary,
        },
    )
    print(f"\nSaved benchmark summary to {_display_path(benchmark_path)}")
    all_green = run_summary["with_skill"]["reliability"]["red_evals"] == 0
    return 0 if all_green else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # 1. static
    p_static = sub.add_parser("static", help="Run Layer 1 static spec, reference, script, MCP, command & hook checks")
    p_static.add_argument("--skill", help="Check a single canonical skill name and its parent plugins")
    p_static.add_argument("--strict-limits", action="store_true", help="Treat >500 lines or >1024-char description as errors")

    # 2. trigger
    p_trig = sub.add_parser("trigger", help="Run Layer 2 4-quadrant trigger & collision evaluations")
    p_trig.add_argument("--skill", required=True, help="Canonical skill name (e.g. amazon-aurora-postgresql)")
    p_trig.add_argument("--harness", choices=("agy", "claude", "codex"), default="agy", help="Agent CLI harness (default: agy)")
    p_trig.add_argument(
        "--model",
        default=None,
        help="Model ID override. When --harness agy is used, strictly restricted to Gemini 4 Hydrogen only (default: gemini-4-hydrogen-medium).",
    )
    p_trig.add_argument(
        "--effort",
        choices=("low", "medium", "high", "xhigh"),
        default=None,
        help="Reasoning effort for --harness agy (default: medium).",
    )
    p_trig.add_argument("--split", choices=("train", "val", "all"), default="all", help="Dataset split to evaluate")
    p_trig.add_argument("--query-id", help="Run a single trigger query by id")
    p_trig.add_argument("--aws-profile", default=None, help="AWS CLI profile override (defaults to $AWS_PROFILE)")
    p_trig.add_argument("--aws-region", default=None, help="AWS region override (defaults to $AWS_REGION or us-east-1)")
    p_trig.add_argument("--kube-context", default=K8S_DEFAULT_CONTEXT, help="Kubernetes context to isolate & target for Kubernetes plugin evals (default: docker-desktop)")
    p_trig.add_argument("--mcp-src-dir", default=None, help="Local talkops-mcp/src directory override (auto-detected when ../talkops-mcp/src exists)")
    p_trig.add_argument("--use-uvx-mcp", action="store_true", help="Disable local talkops-mcp/src rewrite and launch published uvx packages")
    p_trig.add_argument("--mcp-allow-write", choices=("auto", "true", "false"), default="auto", help="Control MCP_ALLOW_WRITE for TalkOps MCP servers (default: auto -> true for local K8s MCP testing)")
    p_trig.add_argument("--runs", type=int, default=1, help="Number of trials per query (default: 1; use 3 for variance)")
    p_trig.add_argument("--workers", type=int, default=1, help="Number of parallel trigger eval workers (default: 1)")
    p_trig.add_argument("--timeout", type=int, default=180, help="Timeout in seconds per run")
    p_trig.add_argument("--dry-run", action="store_true", help="Validate and list trigger queries without invoking LLM")

    # 3. run
    p_run = sub.add_parser("run", help="Run outcome & expectation skill evaluations (GREEN if expectations match, else RED)")
    p_run.add_argument("--skill", required=True, help="Canonical skill name (e.g. amazon-aurora-postgresql)")
    p_run.add_argument("--eval-id", help="Run a single eval case by id")
    p_run.add_argument("--harness", choices=("agy", "claude", "codex"), default="agy", help="Agent CLI harness (default: agy)")
    p_run.add_argument(
        "--model",
        default=None,
        help="Model ID override. When --harness agy is used, strictly restricted to Gemini 4 Hydrogen only (default: gemini-4-hydrogen-medium).",
    )
    p_run.add_argument(
        "--effort",
        choices=("low", "medium", "high", "xhigh"),
        default=None,
        help="Reasoning effort for --harness agy (default: medium).",
    )
    p_run.add_argument("--aws-profile", default=None, help="AWS CLI profile override (defaults to $AWS_PROFILE)")
    p_run.add_argument("--aws-region", default=None, help="AWS region override (defaults to $AWS_REGION or us-east-1)")
    p_run.add_argument("--kube-context", default=K8S_DEFAULT_CONTEXT, help="Kubernetes context to isolate & target for Kubernetes plugin evals (default: docker-desktop)")
    p_run.add_argument("--mcp-src-dir", default=None, help="Local talkops-mcp/src directory override (auto-detected when ../talkops-mcp/src exists)")
    p_run.add_argument("--use-uvx-mcp", action="store_true", help="Disable local talkops-mcp/src rewrite and launch published uvx packages")
    p_run.add_argument("--mcp-allow-write", choices=("auto", "true", "false"), default="auto", help="Control MCP_ALLOW_WRITE for TalkOps MCP servers (default: auto -> true for local K8s MCP testing)")
    p_run.add_argument("--baseline", action="store_true", help="Also run without_skill baseline for A/B delta")
    p_run.add_argument("--runs", type=int, default=1, help="Number of trials per eval case (default: 1)")
    p_run.add_argument("--workers", type=int, default=1, help="Number of parallel eval workers (default: 1)")
    p_run.add_argument("--timeout", type=int, default=480, help="Timeout in seconds per run")
    p_run.add_argument("--dry-run", action="store_true", help="Validate and list eval cases without invoking LLM")

    args = parser.parse_args()
    if args.command == "static":
        return run_static_checks(target_skill=args.skill, strict_limits=args.strict_limits)
    if args.command == "trigger":
        return run_trigger_evals(args)
    if args.command == "run":
        return run_execution_evals(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
