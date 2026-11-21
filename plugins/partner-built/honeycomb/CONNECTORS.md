# Connector setup: Honeycomb

This partner-built plugin bundles [`.mcp.json`](./.mcp.json) and [`mcp.json`](./mcp.json) pre-wired for the official **Honeycomb** remote MCP server (`honeycomb`). Supply `HONEYCOMB_API_KEY` and optional `HONEYCOMB_MCP_URL` (`https://mcp.honeycomb.io/mcp` US default or `https://mcp.eu1.honeycomb.io/mcp` EU) in your shell environment before launching your agent host.

## Connectors

| Key | Server | Use it for |
|---|---|---|
| `honeycomb` | [Honeycomb MCP](https://www.honeycomb.io) | Official Honeycomb BubbleUp wide-event investigation, OTel metrics, SLO burn-rate triage, and trace skills. |

### `honeycomb`

Endpoint: `https://mcp.honeycomb.io/mcp` (`Authorization: Bearer ${HONEYCOMB_API_KEY}`)
