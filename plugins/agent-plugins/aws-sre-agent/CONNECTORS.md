# Optional connectors: AWS SRE Agent

These third-party observability and security MCP servers require tenant URLs, OAuth sign-in, or read-only API tokens that only you can supply, so the plugin does **not** start them automatically. Add the ones you use under the exact key shown (`mcp__<key>__*`); `aws-sre-agent` already includes each `mcp__<key>__*` pattern in its `tools:` allowlist.

## Connectors

| Key | Server | Use it for |
|---|---|---|
| `grafana-cloud` | [Grafana Cloud Hosted MCP](https://mcp.grafana.com/mcp) | Query Grafana Cloud Prometheus/Mimir metrics, Loki logs, Tempo traces, dashboards, alerts, and incidents (`grafana-cloud-investigation`). |
| `cribl` | [Cribl MCP Server](https://<workspace>-<org>.cribl.cloud/api/v1/mcp) | Inspect Cribl Stream/Edge Sources, Destinations, Pipelines, Worker Groups, and Cribl Search datasets (`cribl-investigation`). |
| `clickhouse-observability` | [ClickHouse ClickStack MCP](https://mcp.clickhouse.cloud/clickstack) | Investigate OpenTelemetry logs, traces, and high-cardinality metrics stored in ClickHouse ClickStack (`clickstack-investigation`). |
| `bluebox` | [Dynatrace Bluebox MCP](https://app.bluebox.ai/v1/mcp) | Run Dynatrace Bluebox causal observability and distributed trace root-cause analysis (`bluebox-observability`). |
| `sumo-logic` | [Sumo Logic MCP Server](https://mcp.<region>.sumologic.com/mcp) | Search Sumo Logic logs, Cloud SIEM security insights, and metrics (`sumo-logic-investigator`). |
| `wiz` | [Wiz DevOps MCP](https://mcp.app.wiz.io/?toolset=devops) | Enrich cloud/Kubernetes triage and security reviews with Wiz cloud graph, CVE, and CSPM context (`wiz-security-context`). |

### `grafana-cloud`

Endpoint: `https://mcp.grafana.com/mcp`

### `cribl`

Endpoint: `https://<workspace>-<org>.cribl.cloud/api/v1/mcp`

### `clickhouse-observability`

Endpoint: `https://mcp.clickhouse.cloud/clickstack`

### `bluebox`

Endpoint: `https://app.bluebox.ai/v1/mcp`

### `sumo-logic`

Endpoint: `https://mcp.<region>.sumologic.com/mcp`

### `wiz`

Endpoint: `https://mcp.app.wiz.io/?toolset=devops`
