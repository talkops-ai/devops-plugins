#!/usr/bin/env python3
"""SessionStart hook: non-blocking AWS caller identity and read-only architect preflight check."""

from __future__ import annotations

import json
import os
import subprocess
import sys


def main() -> int:
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "unset (defaulting to us-east-1)"
    profile = os.environ.get("AWS_PROFILE") or "default"
    identity_summary = "unauthenticated or unreachable"

    try:
        proc = subprocess.run(
            ["aws", "sts", "get-caller-identity", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            ident = json.loads(proc.stdout)
            account = ident.get("Account", "unknown")
            arn = ident.get("Arn", "unknown")
            identity_summary = f"Account={account}, Arn={arn}"
    except Exception:
        pass

    msg = (
        f"[AWS Solutions Architect Preflight] AWS_PROFILE={profile} | AWS_REGION={region} | "
        f"Caller={identity_summary}. "
        "Mode=STRICT READ-ONLY on live AWS resources (local writes permitted for ADRs, IaC blueprints, .threatmodel/, and .drawio/.mmd diagrams)."
    )
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": msg,
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
