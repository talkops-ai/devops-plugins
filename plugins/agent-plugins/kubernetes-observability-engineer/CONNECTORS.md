# Optional connectors: Kubernetes Observability Engineer

These third-party observability and security MCP servers need tenant endpoints, OAuth sign-in, or read-only service credentials that only you can supply, so the plugin does **not** start them automatically. Add the ones you use to your own agent host configuration with the exact key shown; the key determines the tool names (`mcp__<key>__*`). In Claude Code the `kubernetes-observability-engineer` agent's `tools:` allowlist already grants `mcp__<key>__*` for each key below.

All connectors below are **optional** — when a connector is not configured, `kubernetes-observability-engineer` falls back cleanly to its bundled Kubernetes telemetry servers (`prometheus`, `alertmanager`, `tempo`, `loki`, `opentelemetry`).

## Connectors

| Key | Server | Use it for |
|---|---|---|
| `grafana-cloud` | [Grafana Cloud Hosted MCP](https://grafana.com/docs/grafana-cloud/ai-tools/mcp-servers/cloud-mcp/) | Query Grafana Cloud Prometheus/Mimir metrics, Loki logs, Tempo traces, Pyroscope profiles, dashboards, alerts, and incidents (`grafana-cloud-investigation`). |
| `cribl` | [Cribl MCP Server](https://docs.cribl.io/copilot/cribl-mcp-server/) | Inspect Cribl Stream/Edge Sources, Destinations, Pipelines, Worker Groups, alerts, metrics, and Cribl Search datasets (`cribl-investigation`). |

### `grafana-cloud`

Connects to Grafana Labs' hosted OAuth MCP server (`https://mcp.grafana.com/mcp`):

Claude Code:

```bash
claude mcp add --transport http --scope user grafana-cloud https://mcp.grafana.com/mcp
```

Codex:

```bash
codex mcp add grafana-cloud --url https://mcp.grafana.com/mcp
```

Codex `config.toml`:

```toml
[mcp_servers.grafana-cloud]
url = "https://mcp.grafana.com/mcp"
```

### `cribl`

Supply your Cribl.Cloud `<workspace>-<org>` tenant (or on-prem Leader `https://<leader>:<port>/api/v1/mcp`) and a Cribl Bearer token (`Settings > Global > MCP Server > Get your token`):

Claude Code:

```bash
claude mcp add --transport http --scope user   --header 'Authorization: Bearer <CRIBL_BEARER_TOKEN>'   cribl 'https://<workspace>-<org>.cribl.cloud/api/v1/mcp'
```

Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.cribl]
url = "https://<workspace>-<org>.cribl.cloud/api/v1/mcp"
http_headers = { Authorization = "Bearer <CRIBL_BEARER_TOKEN>" }
```
