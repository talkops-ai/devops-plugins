#!/usr/bin/env python3
"""PostToolUse hook: automatic validation of CloudFormation templates, Terraform files, and draw.io/Mermaid diagrams."""

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

    if not isinstance(data, dict):
        return 0

    tool_input = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    file_path = str(tool_input.get("file_path") or tool_input.get("path") or "").strip()

    if not file_path or not os.path.isfile(file_path):
        return 0

    warnings: list[str] = []
    ext = os.path.splitext(file_path)[1].lower()

    # Validate CloudFormation templates with cfn-lint when installed
    if ext in (".yaml", ".yml", ".json", ".template"):
        try:
            text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        if "AWSTemplateFormatVersion" in text and shutil.which("cfn-lint"):
            proc = subprocess.run(
                ["cfn-lint", file_path],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            if proc.returncode != 0 and (proc.stdout.strip() or proc.stderr.strip()):
                out = (proc.stdout.strip() or proc.stderr.strip())[:800]
                warnings.append(f"[cfn-lint] Issues detected in {file_path}:\n{out}")

    # Validate .drawio or .mmd files with the bundled validate_mermaid.py validator
    if ext in (".drawio", ".mmd", ".mermaid"):
        validator = (
            Path(__file__).resolve().parent.parent
            / "skills"
            / "aws-architecture-diagramming"
            / "scripts"
            / "validate_mermaid.py"
        )
        if validator.is_file():
            proc = subprocess.run(
                [sys.executable, str(validator), file_path],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if proc.returncode != 0:
                out = (proc.stderr.strip() or proc.stdout.strip())[:800]
                warnings.append(f"[diagram-validator] Issues detected in {file_path}:\n{out}")

    # Check Terraform files with terraform fmt -check when installed
    if ext == ".tf" and shutil.which("terraform"):
        proc = subprocess.run(
            ["terraform", "fmt", "-check", file_path],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode != 0:
            warnings.append(f"[terraform fmt] {file_path} is not canonically formatted. Run `terraform fmt`.")

    if warnings:
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "\n\n".join(warnings),
                }
            },
            sys.stdout,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
