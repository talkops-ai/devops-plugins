#!/usr/bin/env python3
"""SessionStart hook: non-blocking AWS caller identity and region preflight check."""

from __future__ import annotations

import json
import os
import subprocess
import sys


def main() -> int:
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "unset (defaulting to us-east-1)"
    profile = os.environ.get("AWS_PROFILE") or "default"
    identity_summary = "unauthenticated or unreachable"
    is_prod_suspect = any(tok in profile.lower() for tok in ("prod", "production", "prd", "live"))

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
            if any(tok in arn.lower() for tok in ("prod", "production", "prd")):
                is_prod_suspect = True
    except Exception:
        pass

    prod_warning = (
        " WARNING: Active profile/role appears to target a PRODUCTION environment. "
        "Enforce Multi-AZ, KMS encryption, DeletionPolicy: Retain, and explicit human confirmation before any mutation."
        if is_prod_suspect
        else ""
    )

    msg = (
        f"[AWS Platform Preflight] AWS_PROFILE={profile} | AWS_REGION={region} | "
        f"Caller={identity_summary}.{prod_warning}"
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
