#!/usr/bin/env python3
"""ArgoCD MCP Server Pre-Launch Token Bootstrapper & Session Validator.

Resolves `ARGOCD_AUTH_TOKEN` automatically from `ARGOCD_USERNAME` and `ARGOCD_PASSWORD`
(via `POST /api/v1/session` + `GET /api/v1/applications?limit=1` validation) BEFORE
exec'ing `uvx --from talkops-argocd-mcp-server==0.4.1 argocd-mcp-server --transport stdio`.

Why a pre-launch wrapper in addition to a SessionStart hook:
- Plugin hooks (`SessionStart`, `PreToolUse`) run in separate short-lived subprocesses and
  cannot mutate `os.environ` inside an already-spawned MCP server process.
- Running this stdlib-only bootstrapper as the `argocd` MCP entry point fetches and
  validates the JWT in-process, injects `ARGOCD_AUTH_TOKEN` into `os.environ` (and scrubs
  `ARGOCD_PASSWORD`), and replaces the current process via `os.execvp("uvx", ...)` without
  writing a single byte to `stdout` (keeping the MCP JSON-RPC stdio stream clean).

Standalone helper usage:
    python3 scripts/launch_argocd_mcp.py --fetch-only [--server URL] [--username USER]
        [--password PASS] [--insecure | --verify-tls] [--output summary|json|env] [--env-file PATH]
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_ARGOCD_SERVER_URL = "https://argocd-server.argocd.svc:443"
DEFAULT_UVX_ARGS = [
    "--from",
    "talkops-argocd-mcp-server==0.4.1",
    "argocd-mcp-server",
    "--transport",
    "stdio",
]


def mask_token(token: str) -> str:
    """Return a redacted preview of a bearer token safe for logs and hook context."""
    if not token or len(token) < 10:
        return "***REDACTED***"
    return f"{token[:4]}...{token[-4:]} (len={len(token)})"


def _load_dotenv_if_present(dotenv_path: Path | None = None) -> None:
    """Load simple KEY=VALUE entries from `.env` without overriding existing `os.environ`."""
    target = dotenv_path or (Path.cwd() / ".env")
    if not target.is_file():
        return
    try:
        for raw in target.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                val = val[1:-1]
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError:
        pass


def _make_ssl_context(verify_tls: bool) -> ssl.SSLContext:
    if verify_tls:
        return ssl.create_default_context()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def resolve_tls_verify(explicit_insecure: bool | None = None, explicit_verify: bool | None = None) -> bool:
    """Determine TLS verification from flags or `ARGOCD_INSECURE` / `ARGOCD_VERIFY_TLS`."""
    if explicit_insecure is True:
        return False
    if explicit_verify is not None:
        return explicit_verify

    insecure_env = (os.environ.get("ARGOCD_INSECURE") or "").strip().lower()
    if insecure_env in ("1", "true", "yes", "on"):
        return False

    verify_env = (os.environ.get("ARGOCD_VERIFY_TLS") or "").strip().lower()
    if verify_env in ("0", "false", "no", "off"):
        return False

    return True


def fetch_argocd_token(
    server_url: str,
    username: str,
    password: str,
    verify_tls: bool = True,
    timeout: int = 15,
) -> str:
    """Authenticate against `POST /api/v1/session` and return the ArgoCD bearer token."""
    url = f"{server_url.rstrip('/')}/api/v1/session"
    payload = json.dumps({"username": username, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    ctx = _make_ssl_context(verify_tls)
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    token = data.get("token")
    if not token:
        raise ValueError("ArgoCD /api/v1/session response did not contain a 'token' field.")
    return str(token)


def validate_argocd_token(
    server_url: str,
    token: str,
    verify_tls: bool = True,
    timeout: int = 15,
) -> tuple[bool, int]:
    """Validate an ArgoCD token via `GET /api/v1/applications?limit=1`.

    Returns `(valid, http_status)`. HTTP 200 proves full access; HTTP 403 proves the JWT
    signature/session was accepted by ArgoCD (`401` would be returned for an invalid token)
    even when the account has scoped RBAC without global application list rights.
    """
    url = f"{server_url.rstrip('/')}/api/v1/applications?limit=1"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    ctx = _make_ssl_context(verify_tls)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return (200 <= resp.status < 300), int(resp.status)
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            return True, 403
        return False, int(exc.code)


def write_token_env_file(env_file: Path, server_url: str, token: str, insecure: bool) -> None:
    """Persist `ARGOCD_SERVER_URL`, `ARGOCD_AUTH_TOKEN`, and `ARGOCD_INSECURE` with 0600 permissions."""
    existing_lines: list[str] = []
    if env_file.exists():
        existing_lines = env_file.read_text(encoding="utf-8", errors="ignore").splitlines()

    prefixes = (
        "ARGOCD_AUTH_TOKEN=",
        "export ARGOCD_AUTH_TOKEN=",
        "ARGOCD_SERVER_URL=",
        "export ARGOCD_SERVER_URL=",
        "ARGOCD_INSECURE=",
        "export ARGOCD_INSECURE=",
    )
    kept = [ln for ln in existing_lines if not ln.strip().startswith(prefixes)]
    is_shell_export = env_file.name == os.environ.get("CLAUDE_ENV_FILE", "") or any(
        ln.strip().startswith("export ") for ln in existing_lines
    )
    if is_shell_export or str(env_file) == os.environ.get("CLAUDE_ENV_FILE", ""):
        kept.append(f"export ARGOCD_SERVER_URL='{server_url.rstrip('/')}'")
        kept.append(f"export ARGOCD_INSECURE='{'true' if insecure else 'false'}'")
        kept.append(f"export ARGOCD_AUTH_TOKEN='{token}'")
    else:
        kept.append(f"ARGOCD_SERVER_URL={server_url.rstrip('/')}")
        kept.append(f"ARGOCD_INSECURE={'true' if insecure else 'false'}")
        kept.append(f"ARGOCD_AUTH_TOKEN={token}")

    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text("\n".join(kept) + "\n", encoding="utf-8")
    try:
        os.chmod(env_file, 0o600)
    except OSError:
        pass


def bootstrap_argocd_env(
    server_override: str | None = None,
    username_override: str | None = None,
    password_override: str | None = None,
    verify_tls: bool | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    """Ensure `ARGOCD_SERVER_URL`, `ARGOCD_INSECURE`, and `ARGOCD_AUTH_TOKEN` are populated in `os.environ`.

    Returns a non-secret status dictionary describing the authentication outcome.
    """
    _load_dotenv_if_present()

    server_url = (
        server_override
        or os.environ.get("ARGOCD_SERVER_URL")
        or os.environ.get("ARGOCD_SERVER")
        or DEFAULT_ARGOCD_SERVER_URL
    ).strip()
    os.environ["ARGOCD_SERVER_URL"] = server_url.rstrip("/")

    effective_verify = resolve_tls_verify() if verify_tls is None else verify_tls
    if not effective_verify:
        os.environ["ARGOCD_INSECURE"] = "true"

    existing_token = (os.environ.get("ARGOCD_AUTH_TOKEN") or "").strip()
    if existing_token:
        return {
            "status": "present",
            "source": "environment",
            "server_url": server_url.rstrip("/"),
            "verify_tls": effective_verify,
            "token_preview": mask_token(existing_token),
            "token": existing_token,
        }

    username = (username_override or os.environ.get("ARGOCD_USERNAME") or "").strip()
    password = password_override if password_override is not None else (os.environ.get("ARGOCD_PASSWORD") or "")
    if not username or not password:
        return {
            "status": "skipped",
            "source": "none",
            "server_url": server_url.rstrip("/"),
            "verify_tls": effective_verify,
            "reason": "Neither ARGOCD_AUTH_TOKEN nor ARGOCD_USERNAME+ARGOCD_PASSWORD is set.",
        }

    token = fetch_argocd_token(
        server_url=server_url,
        username=username,
        password=password,
        verify_tls=effective_verify,
        timeout=timeout,
    )
    valid, http_status = validate_argocd_token(
        server_url=server_url,
        token=token,
        verify_tls=effective_verify,
        timeout=timeout,
    )
    if not valid:
        raise RuntimeError(
            f"Fetched ArgoCD session token was rejected during validation (HTTP {http_status})."
        )

    os.environ["ARGOCD_AUTH_TOKEN"] = token
    # Scrub plaintext password before spawning the long-lived MCP server child process
    os.environ.pop("ARGOCD_PASSWORD", None)

    return {
        "status": "fetched",
        "source": "session_login",
        "server_url": server_url.rstrip("/"),
        "verify_tls": effective_verify,
        "validation_http_status": http_status,
        "token_preview": mask_token(token),
        "token": token,
    }


def _run_fetch_only(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="launch_argocd_mcp.py --fetch-only",
        description="Fetch and validate an ArgoCD authentication token from ARGOCD_USERNAME/ARGOCD_PASSWORD.",
    )
    parser.add_argument("--fetch-only", action="store_true", help="Fetch & validate token without starting MCP server")
    parser.add_argument("--server", default=None, help="ArgoCD server URL (env: ARGOCD_SERVER_URL or ARGOCD_SERVER)")
    parser.add_argument("--username", default=None, help="ArgoCD username (env: ARGOCD_USERNAME)")
    parser.add_argument("--password", default=None, help="ArgoCD password (env: ARGOCD_PASSWORD)")
    parser.add_argument("--verify-tls", dest="verify_tls", action="store_true", default=None, help="Verify TLS certs")
    parser.add_argument("--insecure", action="store_true", default=False, help="Skip TLS verification")
    parser.add_argument(
        "--output",
        choices=("summary", "json", "env", "text"),
        default="summary",
        help="Output format (default: redacted 'summary')",
    )
    parser.add_argument("--env-file", default=None, help="Optional file path to persist ARGOCD_AUTH_TOKEN (0600)")
    args = parser.parse_args(argv)

    verify_tls = resolve_tls_verify(explicit_insecure=args.insecure, explicit_verify=args.verify_tls)
    try:
        result = bootstrap_argocd_env(
            server_override=args.server,
            username_override=args.username,
            password_override=args.password,
            verify_tls=verify_tls,
        )
    except Exception as exc:
        sys.stderr.write(f"[argocd-token-bootstrap] Failed to fetch/validate ArgoCD token: {exc}\n")
        return 1

    token = result.get("token")
    if not token:
        sys.stderr.write(
            "[argocd-token-bootstrap] Missing credentials: provide ARGOCD_AUTH_TOKEN or "
            "ARGOCD_SERVER_URL + ARGOCD_USERNAME + ARGOCD_PASSWORD.\n"
        )
        return 1

    saved_to: str | None = None
    if args.env_file:
        env_path = Path(args.env_file)
        write_token_env_file(env_path, result["server_url"], token, insecure=not result["verify_tls"])
        saved_to = str(env_path)

    if args.output == "summary":
        safe_out = {
            "server_url": result["server_url"],
            "source": result["source"],
            "token_preview": result["token_preview"],
            "valid": True,
            "saved_to_env_file": saved_to,
        }
        sys.stdout.write(json.dumps(safe_out, indent=2) + "\n")
    elif args.output == "json":
        sys.stdout.write(json.dumps({"token": token, "valid": True}) + "\n")
    elif args.output == "env":
        sys.stdout.write(f"export ARGOCD_AUTH_TOKEN='{token}'\n")
    else:
        sys.stdout.write(f"{token}\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if "--fetch-only" in raw_argv:
        return _run_fetch_only(raw_argv)

    uvx_args = raw_argv if raw_argv else list(DEFAULT_UVX_ARGS)

    # IMPORTANT: Never write to stdout in MCP launcher mode; stdout is the MCP JSON-RPC transport.
    try:
        res = bootstrap_argocd_env(timeout=15)
        if res.get("status") == "fetched":
            sys.stderr.write(
                f"[argocd-token-bootstrap] Authenticated to {res['server_url']} and injected "
                f"ARGOCD_AUTH_TOKEN ({res['token_preview']}).\n"
            )
    except Exception as exc:
        sys.stderr.write(
            f"[argocd-token-bootstrap] Warning: automatic ArgoCD session login failed ({exc}); "
            "continuing MCP server startup.\n"
        )

    if os.name == "nt":
        return subprocess.call(["uvx", *uvx_args])

    os.execvp("uvx", ["uvx", *uvx_args])
    return 0


if __name__ == "__main__":
    sys.exit(main())
