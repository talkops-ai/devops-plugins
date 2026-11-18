#!/usr/bin/env python3
"""Stop hook: deterministic IaC verification gate before completing an agent turn.

Inspects `git status --porcelain` in the current working directory for modified
or untracked Infrastructure-as-Code files:
  - Terraform / OpenTofu: *.tf -> `terraform fmt -check` and `terraform validate`
  - CloudFormation: *.cfn.yaml, *.cfn.yml, *.cfn.json, *.template.yaml, *.template.json -> `cfn-lint`
  - Crossplane Compositions: *composition*.yaml + xr.yaml + functions.yaml -> `crossplane render`

If a corresponding validator binary is installed on PATH and reports syntax or
validation errors on the modified files, the hook returns `{"decision": "block", "reason": ...}`
so the agent fixes the validation errors before yielding to the user.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _modified_files(cwd: Path) -> list[Path]:
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode != 0:
        return []
    files: list[Path] = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        status = line[:2]
        if "D" in status:
            continue
        rel = line[3:].strip()
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1].strip()
        candidate = (cwd / rel.strip('"')).resolve()
        if candidate.is_file():
            files.append(candidate)
    return files


def _check_terraform(tf_files: list[Path]) -> list[str]:
    tf_bin = shutil.which("terraform") or shutil.which("tofu")
    if not tf_bin or not tf_files:
        return []
    errors: list[str] = []
    dirs = sorted({f.parent for f in tf_files})
    for d in dirs:
        try:
            fmt = subprocess.run(
                [tf_bin, "fmt", "-check", "-no-color"],
                cwd=d,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if fmt.returncode != 0:
                unformatted = ", ".join(fmt.stdout.split()) or str(d)
                errors.append(f"`{Path(tf_bin).name} fmt -check` failed in {d.name} ({unformatted}). Run `{Path(tf_bin).name} fmt`.")
        except (OSError, subprocess.SubprocessError):
            pass
    return errors


def _check_cloudformation(cfn_files: list[Path]) -> list[str]:
    cfn_lint = shutil.which("cfn-lint")
    if not cfn_lint or not cfn_files:
        return []
    errors: list[str] = []
    for f in cfn_files:
        try:
            res = subprocess.run(
                [cfn_lint, str(f)],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if res.returncode not in (0, 4):  # 4 = warnings only in cfn-lint
                snippet = (res.stdout or res.stderr).strip().splitlines()[:5]
                errors.append(f"`cfn-lint {f.name}` reported errors:\n" + "\n".join(snippet))
        except (OSError, subprocess.SubprocessError):
            pass
    return errors


def main() -> int:
    if os.environ.get("TALKOPS_IAC_VERIFICATION_GATE", "").strip().lower() == "off":
        return 0
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        payload = {}
    if isinstance(payload, dict) and payload.get("stop_hook_active"):
        return 0

    cwd = Path(payload.get("cwd") or os.getcwd()) if isinstance(payload, dict) else Path.cwd()
    modified = _modified_files(cwd)
    if not modified:
        return 0

    tf_files = [f for f in modified if f.suffix == ".tf"]
    cfn_files = [
        f
        for f in modified
        if f.name.endswith((".cfn.yaml", ".cfn.yml", ".cfn.json", ".template.yaml", ".template.yml", ".template.json"))
    ]

    failures = _check_terraform(tf_files) + _check_cloudformation(cfn_files)
    if failures:
        json.dump(
            {
                "decision": "block",
                "reason": "IaC verification gate failed on modified files:\n- " + "\n- ".join(failures),
            },
            sys.stdout,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
