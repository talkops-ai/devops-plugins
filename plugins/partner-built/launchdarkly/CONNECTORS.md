# Connector setup: LaunchDarkly

This partner-built plugin bundles [`.mcp.json`](./.mcp.json) and [`mcp.json`](./mcp.json) pre-wired for the official **LaunchDarkly** remote MCP server (`launchdarkly`). Supply `LAUNCHDARKLY_ACCESS_TOKEN` (LaunchDarkly API access token; optional `LAUNCHDARKLY_MCP_URL` override, default `https://mcp.launchdarkly.com/mcp`) in your shell environment before launching your agent host.

## Connectors

| Key | Server | Use it for |
|---|---|---|
| `launchdarkly` | [LaunchDarkly MCP](https://launchdarkly.com) | Official LaunchDarkly feature flags, guarded rollouts, experiments, observability, and AI Config skills. |

### `launchdarkly`

Endpoint: `https://mcp.launchdarkly.com/mcp` (`Authorization: ${LAUNCHDARKLY_ACCESS_TOKEN}`)
