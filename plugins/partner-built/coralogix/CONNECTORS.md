# Connector setup: Coralogix

This partner-built plugin bundles [`.mcp.json`](./.mcp.json) and [`mcp.json`](./mcp.json) pre-wired for the official **Coralogix** remote MCP server (`coralogix`). Supply `CORALOGIX_API_KEY` and `CORALOGIX_REGION` (`us1`, `us2`, `eu1`, `eu2`, `ap1`, `ap2`, `ap3`; default `us2`) in your shell environment before launching your agent host.

## Connectors

| Key | Server | Use it for |
|---|---|---|
| `coralogix` | [Coralogix MCP](https://coralogix.com) | Official Coralogix DataPrime logs/spans, PromQL metrics, alerts, cases, RUM, AI Center, and TCO skills. |

### `coralogix`

Endpoint: `https://api.<region>.coralogix.com/mgmt/api/v1/mcp` (`Authorization: Bearer ${CORALOGIX_API_KEY}`)
