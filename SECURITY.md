# Security Policy

Security is foundational to **TalkOps DevOps Plugins**. Because these plugins interact with cloud infrastructure, Kubernetes clusters, observability platforms, and MCP servers, we treat safety-hook bypasses, credential leaks, and unintended destructive behavior as high-priority security issues.

---

## Supported Versions

Security fixes are applied to the latest release on `main`:

| Version | Supported |
|---|---|
| `0.3.x` (`main`) | Yes |
| `< 0.3.0` | No — please upgrade to the latest release |

---

## Defense-in-Depth Safety Model

Plugins in this marketplace rely on three layers of protection (see [README.md](./README.md#safety-model) and [docs/iam-guardrails.md](./docs/iam-guardrails.md)):

1. **Read-only MCP defaults**: Bundled MCP servers default to read-only flags where supported (`--read-only`, `ALLOW_WRITE=false`, `MCP_ALLOW_WRITE=false`, `READ_OPERATIONS_ONLY=true`).
2. **Deterministic safety hooks**:
   - `secret-safety.py` blocks shell commands and MCP tool calls attempting to read, print, exfiltrate, or hardcode AWS credentials, session tokens, `.env` files, or private keys across all plugins.
   - `aws-mutation-gate.py` intercepts mutating cloud/IaC/Kubernetes CLI and MCP operations, blocking mutations outright for read-only agents and requiring confirmation otherwise.
3. **IAM least privilege**: Client-side hooks and prompts are defense-in-depth—IAM policies and Kubernetes RBAC remain the ultimate enforcement boundary. Always attach scoped, least-privilege IAM roles when running AI agents against cloud environments.

---

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues, pull requests, or discussions.**

Instead, report vulnerabilities privately using **GitHub Private Vulnerability Reporting**:

- Open a private advisory at: **[https://github.com/talkops-ai/devops-plugins/security/advisories/new](https://github.com/talkops-ai/devops-plugins/security/advisories/new)**

### What to Include

To help us triage and resolve the issue quickly, please include:

- **Affected plugin(s), hook(s), skill(s), or script(s)** (exact file paths and version).
- **Host runtime** (Claude Code, Codex, Cursor, Gemini CLI / Antigravity, etc.).
- **Reproduction steps** or a minimal proof-of-concept demonstrating the issue.
- **Impact assessment** (e.g., hook bypass, command injection, credential exposure, unintended write/delete execution).
- **Suggested mitigation**, if you have one.

### What Qualifies as a Security Issue

- Bypasses of `secret-safety.py` or `aws-mutation-gate.py` (including regex evasion, shell quoting/chaining tricks, or MCP tool matcher gaps).
- Command injection, path traversal, or unsafe deserialization in bundled plugin scripts (`scripts/*.py`, `scripts/*.sh`, or `hooks/*.py`).
- Bundled MCP configurations that enable write or sensitive-data-access modes unintentionally or leak credentials into logs/arguments.
- Accidental real credentials, API tokens, private keys, or non-placeholder AWS account identifiers committed in skills, fixtures, or eval suites.
- Skill instructions or templates that recommend insecure cloud/Kubernetes configurations without clear warnings (e.g., wildcard IAM privilege escalation, public credentials, disabled TLS/IMDSv2).

---

## Response Timeline

- **Acknowledgment**: Within **3 business days** of receiving a private report.
- **Triage & Assessment**: Within **7 business days**, we will confirm severity and share an estimated remediation plan.
- **Coordinated Disclosure**: Once a fix is verified and released, we will publish a security advisory crediting the reporter (unless anonymity is requested).
