# Connector setup: Elastic Observability & Security

This partner-built plugin bundles [`.mcp.json`](./.mcp.json) and [`mcp.json`](./mcp.json) pre-wired for the official **Elastic Observability & Security** remote MCP server (`elastic`). Supply `ELASTIC_API_KEY`, `ELASTIC_PROJECT`, and `ELASTIC_REGION` in your shell environment before launching your agent host.

## Connectors

| Key | Server | Use it for |
|---|---|---|
| `elastic` | [Elastic Observability & Security MCP](https://www.elastic.co) | Official Elastic SRE incident triage, service reliability, Kubernetes, CSP security, and LLM observability skills. |

### `elastic`

Endpoint: `https://<project>.kb.<region>.aws.elastic.cloud/api/agent_builder/mcp` (`Authorization: ApiKey ${ELASTIC_API_KEY}`)
