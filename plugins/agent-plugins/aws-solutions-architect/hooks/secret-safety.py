#!/usr/bin/env python3
"""PreToolUse hook: block direct secret fetching, plaintext .tfstate reads, hardcoded keys/PEMs, and .env writes."""

from __future__ import annotations

import json
import os
import re
import sys

DENY_MSG = (
    "Direct secret fetching is blocked. "
    "Use {{resolve:secretsmanager:secret-id:SecretString:key}} dynamic references in CloudFormation/CDK "
    "or asm-exec instead. See the aws-iam skill (or aws-secrets-manager in aws-security-identity)."
)

TFSTATE_DENY_MSG = (
    "Direct reading of plaintext Terraform/OpenTofu state files (*.tfstate, *.tfstate.backup) is blocked "
    "because state files store unencrypted secret attributes. Use `terraform state list` or `terraform output` instead."
)

ENV_FILE_DENY_MSG = (
    "Writing or modifying .env / .env.* files is blocked by secret-safety. "
    "Store application secrets in AWS Secrets Manager or SSM Parameter Store SecureString and inject via dynamic references."
)

HARDCODED_SECRET_DENY_MSG = (
    "Hardcoded AWS access keys (AKIA/ASIA) or PEM private key blocks detected in tool input. "
    "Never commit or pass static credentials; use IAM roles, OIDC, or Secrets Manager dynamic references."
)

TFSTATE_FILE_PATTERN = re.compile(
    r'(?:^|[\s"\'=:/])(?:[A-Za-z0-9_./-]*\.)?tfstate(?:\.backup|\.\d+)?(?:$|[\s"\'])',
    re.I,
)

SMA_PATTERN = re.compile(
    r'(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|::1):2773/secretsmanager/get'
)

_CLI_FLAGS = r'(?:-\S+(?:\s+[^-\s]\S*)?\s+){0,12}'
CLI_GSV_PATTERN = re.compile(
    rf'aws\s+{_CLI_FLAGS}secretsmanager\s+{_CLI_FLAGS}(?:batch-)?get-secret-value\b',
    re.I,
)

GSV_OPERATIONS = ("getsecretvalue", "batchgetsecretvalue")

SDK_CALL_PATTERN = re.compile(
    r'\.\s*(batch[-_]?)?get[-_]?secret[-_]?value\s*\('
    r'|GetSecretValueCommand\s*\('
    r'|(Batch)?GetSecretValue(Request|Command)?\s*\(',
    re.I,
)

AWS_KEY_ID_PATTERN = re.compile(r'\b(?:AKIA|ASIA)(?!IOSFODNN7EXAMPLE|I44QH8DHBEXAMPLE)[0-9A-Z]{16}\b')

PEM_PRIVATE_KEY_PATTERN = re.compile(
    r'-----BEGIN\s+(?:RSA\s+|EC\s+|DSA\s+|OPENSSH\s+|ENCRYPTED\s+)?PRIVATE\s+KEY-----'
)

_READ_ONLY_PREFIXES = (
    'grep', 'egrep', 'fgrep', 'rg', 'ag', 'ack',
    'cat', 'less', 'more', 'head', 'tail', 'bat',
    'git', 'gh', 'find', 'ls', 'wc', 'diff',
    'awk', 'sed', 'sort', 'uniq', 'cut', 'tr',
    'echo', 'printf', 'man', 'help',
)

_INTERPRETER_INLINE_RE = re.compile(
    r'(?:python[23]?|python3\.\d+|node|ruby|perl)\s+(?:-[a-zA-Z]*c|-e)\s'
)

_COMPOUND_OPERATORS_RE = re.compile(r'[;&|`]|\$\(')


def _normalize_op(operation: str) -> str:
    return operation.lower().replace("-", "").replace("_", "")


def _is_read_only_command(command: str) -> bool:
    stripped = command.lstrip()
    while True:
        if re.match(r'[A-Za-z_][A-Za-z0-9_]*=\S*\s', stripped):
            stripped = re.sub(r'^[A-Za-z_][A-Za-z0-9_]*=\S*\s+', '', stripped)
            continue
        if re.match(r'(sudo|env|time|nice|nohup|command|builtin)\s', stripped):
            stripped = re.sub(r'^(sudo|env|time|nice|nohup|command|builtin)\s+', '', stripped)
            continue
        break
    first_token = stripped.split()[0] if stripped.split() else ''
    first_token = first_token.rsplit('/', 1)[-1]
    return first_token in _READ_ONLY_PREFIXES


def _has_sdk_call_in_inline_code(command: str) -> bool:
    if _INTERPRETER_INLINE_RE.search(command):
        return bool(SDK_CALL_PATTERN.search(command))
    return False


def _is_env_file(path_str: str) -> bool:
    base = os.path.basename(path_str.strip())
    if base in (".env.example", ".env.sample", ".env.template"):
        return False
    return base == ".env" or base.startswith(".env.")


def _has_hardcoded_secret(text: str) -> bool:
    return bool(AWS_KEY_ID_PATTERN.search(text) or PEM_PRIVATE_KEY_PATTERN.search(text))


def deny(reason: str = DENY_MSG) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    sys.exit(0)


def allow() -> None:
    sys.exit(0)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        allow()
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        tool_input = {}

    if tool_name in ("Write", "Edit", "MultiEdit"):
        file_path = str(tool_input.get("file_path") or tool_input.get("path") or "")
        if file_path and _is_env_file(file_path):
            deny(ENV_FILE_DENY_MSG)
        content_blobs = [
            str(tool_input.get("content") or ""),
            str(tool_input.get("new_string") or ""),
            json.dumps(tool_input.get("edits") or []),
        ]
        if _has_hardcoded_secret("\n".join(content_blobs)):
            deny(HARDCODED_SECRET_DENY_MSG)
        allow()

    if tool_name == "use_aws" or tool_name.startswith("mcp__"):
        service = (
            tool_input.get("service_name")
            or tool_input.get("service")
            or tool_input.get("serviceName")
            or ""
        ).lower()
        operation = (
            tool_input.get("operation_name")
            or tool_input.get("operation")
            or tool_input.get("operationName")
            or ""
        )
        if service == "secretsmanager" and _normalize_op(str(operation)) in GSV_OPERATIONS:
            deny()
        input_str = json.dumps(tool_input)
        if _has_hardcoded_secret(input_str):
            deny(HARDCODED_SECRET_DENY_MSG)
        if SDK_CALL_PATTERN.search(input_str) and "secretsmanager" in input_str.lower():
            deny()
        if CLI_GSV_PATTERN.search(input_str):
            deny()
        allow()

    if "run_script" in tool_name:
        for val in tool_input.values():
            if isinstance(val, str):
                if SDK_CALL_PATTERN.search(val):
                    deny()
                if _has_hardcoded_secret(val):
                    deny(HARDCODED_SECRET_DENY_MSG)
        allow()

    if tool_name == "Bash":
        command = str(tool_input.get("command", ""))
        if _has_hardcoded_secret(command):
            deny(HARDCODED_SECRET_DENY_MSG)
        if TFSTATE_FILE_PATTERN.search(command) and not re.match(
            r"^\s*(?:terraform|tofu)\s+state\s+(?:list|mv|rm)\b", command
        ):
            deny(TFSTATE_DENY_MSG)
        if CLI_GSV_PATTERN.search(command):
            deny()
        if SMA_PATTERN.search(command):
            deny()
        if _is_read_only_command(command) and not _COMPOUND_OPERATORS_RE.search(command):
            allow()
        if _has_sdk_call_in_inline_code(command):
            deny()
        if SDK_CALL_PATTERN.search(command) and "secretsmanager" in command.lower():
            deny()

    allow()


if __name__ == "__main__":
    main()
