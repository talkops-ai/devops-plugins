# Optional connectors: AWS DevSecOps Engineer

These third-party observability and security MCP servers require tenant URLs, OAuth sign-in, or read-only API tokens that only you can supply, so the plugin does **not** start them automatically. Add the ones you use under the exact key shown (`mcp__<key>__*`); `aws-devsecops-engineer` already includes each `mcp__<key>__*` pattern in its `tools:` allowlist.

## Connectors

| Key | Server | Use it for |
|---|---|---|
| `wiz` | [Wiz DevOps MCP](https://mcp.app.wiz.io/?toolset=devops) | Enrich cloud/Kubernetes triage and security reviews with Wiz cloud graph, CVE, and CSPM context (`wiz-security-context`). |

### `wiz`

Endpoint: `https://mcp.app.wiz.io/?toolset=devops`
