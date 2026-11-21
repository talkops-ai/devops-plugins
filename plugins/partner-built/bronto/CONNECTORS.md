# Connector setup: Bronto Log Analytics

This partner-built plugin bundles [`.mcp.json`](./.mcp.json) and [`mcp.json`](./mcp.json) pre-wired for the official **Bronto Log Analytics** remote MCP server (`bronto`). Supply `BRONTO_API_KEY` and `BRONTO_REGION` (`us` or `eu`; default `us`) in your shell environment before launching your agent host.

## Connectors

| Key | Server | Use it for |
|---|---|---|
| `bronto` | [Bronto Log Analytics MCP](https://bronto.io) | Official Bronto dataset discovery, SQL-style log search & time-series aggregation, and error spike triage skills. |

### `bronto`

Endpoint: `https://mcp.<us|eu>.bronto.io/mcp` (`X-BRONTO-API-KEY: ${BRONTO_API_KEY}`)
