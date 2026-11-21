#!/usr/bin/env python3
"""SessionStart hook: automatic ArgoCD token preflight & CLAUDE_ENV_FILE export.

When `ARGOCD_AUTH_TOKEN` is unset and `ARGOCD_USERNAME` + `ARGOCD_PASSWORD` are provided:
1. Exchanges credentials against `POST /api/v1/session` and validates the JWT against
   `GET /api/v1/applications?limit=1`.
2. Persists `ARGOCD_AUTH_TOKEN` (mode 0600) to `CLAUDE_ENV_FILE` when provided by the host
   so subsequent session shell tools inherit the validated token.
3. Emits only a redacted status summary via `hookSpecificOutput.additionalContext` (never
   exposing plaintext tokens or passwords).

Note: The `argocd` MCP server itself also runs `scripts/launch_argocd_mcp.py` as its
pre-launch wrapper so `ARGOCD_AUTH_TOKEN` is injected directly into the MCP server
process environment before `argocd-mcp-server` initializes.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from launch_argocd_mcp import bootstrap_argocd_env, write_token_env_file  # noqa: E402


def main() -> int:
    # Consume hook event payload from stdin if present (Claude Code / Codex protocol)
    try:
        if not sys.stdin.isatty():
            sys.stdin.read()
    except Exception:
        pass

    try:
        res = bootstrap_argocd_env(timeout=8)
    except Exception as exc:
        msg = (
            "[ArgoCD Session Preflight] Automatic token fetch via ARGOCD_USERNAME/ARGOCD_PASSWORD "
            f"failed ({exc}). Verify ARGOCD_SERVER_URL, credentials, and ARGOCD_INSECURE / ARGOCD_VERIFY_TLS."
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

    status = res.get("status")
    if status == "skipped":
        # Do not clutter non-ArgoCD Kubernetes sessions (Helm, Rollouts, Kargo, Traefik)
        return 0

    token = res.get("token", "")
    claude_env_file = (os.environ.get("CLAUDE_ENV_FILE") or "").strip()
    if token and claude_env_file:
        try:
            write_token_env_file(
                Path(claude_env_file),
                server_url=res["server_url"],
                token=token,
                insecure=not res.get("verify_tls", True),
            )
        except Exception:
            pass

    auth_desc = (
        f"auto-fetched & validated via session login ({res['token_preview']})"
        if status == "fetched"
        else f"configured in environment ({res['token_preview']})"
    )
    msg = f"[ArgoCD Session Preflight] server={res['server_url']} | ARGOCD_AUTH_TOKEN={auth_desc}."
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
