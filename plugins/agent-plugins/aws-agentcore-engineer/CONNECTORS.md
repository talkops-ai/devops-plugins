# Optional connectors: AWS AgentCore Engineer

These third-party observability and security MCP servers require tenant URLs, OAuth sign-in, or read-only API tokens that only you can supply, so the plugin does **not** start them automatically. Add the ones you use under the exact key shown (`mcp__<key>__*`); `aws-agentcore-engineer` already includes each `mcp__<key>__*` pattern in its `tools:` allowlist.

## Connectors

| Key | Server | Use it for |
|---|---|---|
| `arize-ax` | [Arize AX Observability MCP](https://api.arize.com/mcp) | Investigate LLM/agent OpenTelemetry traces, evaluations, prompt regressions, and latency spikes (`arize-incident-investigation`). |

### `arize-ax`

Endpoint: `https://api.arize.com/mcp`
