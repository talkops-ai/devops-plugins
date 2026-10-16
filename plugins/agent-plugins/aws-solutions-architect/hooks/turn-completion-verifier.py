#!/usr/bin/env python3
"""Stop hook: verify modified CloudFormation templates and .drawio/.mmd diagrams pass validation before turn completion."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0

    if not isinstance(data, dict) or data.get("stop_hook_active"):
        return 0

    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except Exception:
        return 0

    if proc.returncode != 0 or not proc.stdout.strip():
        return 0

    validator = (
        Path(__file__).resolve().parent.parent
        / "skills"
        / "aws-architecture-diagramming"
        / "scripts"
        / "validate_mermaid.py"
    )
    failures: list[str] = []

    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        status = line[:2]
        if "D" in status:
            continue
        rel_path = line[3:].strip().strip('"')
        if " -> " in rel_path:
            rel_path = rel_path.split(" -> ", 1)[1].strip()
        if not os.path.isfile(rel_path):
            continue
        ext = os.path.splitext(rel_path)[1].lower()
        if ext in (".yaml", ".yml", ".json", ".template") and shutil.which("cfn-lint"):
            try:
                content = Path(rel_path).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "AWSTemplateFormatVersion" in content:
                lint = subprocess.run(
                    ["cfn-lint", rel_path],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    check=False,
                )
                if lint.returncode != 0:
                    detail = (lint.stdout.strip() or lint.stderr.strip())[:400]
                    failures.append(f"cfn-lint failed on {rel_path}: {detail}")
        elif ext in (".drawio", ".mmd", ".mermaid") and validator.is_file():
            diag = subprocess.run(
                [sys.executable, str(validator), rel_path],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if diag.returncode != 0:
                detail = (diag.stderr.strip() or diag.stdout.strip())[:400]
                failures.append(f"Diagram validation failed on {rel_path}: {detail}")

    if failures:
        json.dump(
            {
                "decision": "block",
                "reason": (
                    "Modified architecture deliverable(s) failed validation. "
                    "Fix the reported errors before completing your response:\n"
                    + "\n".join(failures)
                ),
            },
            sys.stdout,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
