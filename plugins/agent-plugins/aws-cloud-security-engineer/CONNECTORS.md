# Optional connectors: AWS Cloud Security Engineer

These third-party observability and security MCP servers require tenant URLs, OAuth sign-in, or read-only API tokens that only you can supply, so the plugin does **not** start them automatically. Add the ones you use under the exact key shown (`mcp__<key>__*`); `aws-cloud-security-engineer` already includes each `mcp__<key>__*` pattern in its `tools:` allowlist.

## Connectors

| Key | Server | Use it for |
|---|---|---|
| `sumo-logic` | [Sumo Logic MCP Server](https://mcp.<region>.sumologic.com/mcp) | Search Sumo Logic logs, Cloud SIEM security insights, and metrics (`sumo-logic-investigator`). |
| `wiz` | [Wiz DevOps MCP](https://mcp.app.wiz.io/?toolset=devops) | Enrich cloud/Kubernetes triage and security reviews with Wiz cloud graph, CVE, and CSPM context (`wiz-security-context`). |

### `sumo-logic`

Endpoint: `https://mcp.<region>.sumologic.com/mcp`

### `wiz`

Endpoint: `https://mcp.app.wiz.io/?toolset=devops`
