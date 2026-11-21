#!/usr/bin/env python3
"""PostToolUse hook: audit trail logging and automatic IaC linting after Write/Edit operations."""

from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _append_audit_log(tool_name: str, file_path: str) -> None:
    try:
        audit_file = Path.cwd() / ".aws-platform-audit.jsonl"
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event": "PostToolUse",
            "tool_name": tool_name,
            "file_path": file_path,
        }
        with audit_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0

    if not isinstance(data, dict):
        return 0

    tool_name = str(data.get("tool_name", ""))
    tool_input = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    file_path = str(tool_input.get("file_path") or tool_input.get("path") or "").strip()

    if file_path and os.environ.get("AWS_PLATFORM_AUDIT_LOG", "").lower() in ("1", "true", "yes"):
        _append_audit_log(tool_name, file_path)

    if not file_path or not os.path.isfile(file_path):
        return 0

    warnings: list[str] = []
    ext = os.path.splitext(file_path)[1].lower()

    # Check CloudFormation templates with cfn-lint if available
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

    # Check Terraform files with terraform fmt -check if available
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
