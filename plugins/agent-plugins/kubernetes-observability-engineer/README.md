# Kubernetes Observability Engineer

Principal Kubernetes Observability, Telemetry & Monitoring SRE Engineer: full-stack metrics, alerting, distributed tracing, log analytics, and OpenTelemetry pipeline engineering across Prometheus 3.0+ (PromQL 3.0, Native Histograms, OTLP ingestion, RED/SLO multi-burn-rate triage, exemplar extraction, multi-mode rule unit testing & deployment, TSDB cardinality FinOps, zero-knowledge ServiceMonitor/PodMonitor/Probe CRDs, 19-exporter onboarding), Alertmanager (incident correlation, routing tree simulation, inhibition analysis, SP001-SP010 silence governance, missed-notification diagnostics), Grafana Tempo (TraceQL 2.x/3.x & TraceQL Metrics, critical-path latency regression diffs, service topology, TempoStack/TempoMonolithic operator CRs), Grafana Loki 3.x & Loki Operator (discovery-first 4-stage LogQL authoring, structured metadata & Bloom filter FinOps, N-to-1 service error triage, release regression comparison, cross-service trace_id log correlation, Loki Ruler alerting/recording rules, Compactor PII deletion, LokiStack CRDs), and OpenTelemetry on Kubernetes (OpenTelemetryCollector provisioning, auto-instrumentation & eBPF/OBI zero-code telemetry, OTTL cardinality filtering, tail sampling, spanmetrics/servicegraph connectors, and observability security posture auditing).

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install kubernetes-observability-engineer@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install from the Plugins Directory; for the agent persona, copy [`codex/agents/kubernetes-observability-engineer.toml`](./codex/agents/kubernetes-observability-engineer.toml) to `~/.codex/agents/` |
| Other Agent Plugins hosts | Load this directory; [`plugin.json`](./plugin.json), `skills/`, and [`mcp.json`](./mcp.json) follow the portable [Agent Plugins](https://agent-plugins.org) format |

## Agent

This is an **agent plugin**: every skill, hook, and MCP server below is bound to the [`kubernetes-observability-engineer`](./agents/kubernetes-observability-engineer.md) agent, which the host runtime spawns as a dynamic sub-agent.

- Claude Code: `@agent-kubernetes-observability-engineer:kubernetes-observability-engineer` or let Claude delegate based on the agent description
- Headless: `claude --agent kubernetes-observability-engineer:kubernetes-observability-engineer`
- Codex: install the custom agent above, then ask Codex to spawn `kubernetes-observability-engineer`. Codex plugins can't bundle agents, so without it the skills and MCP servers attach to the main agent.

## Skills (32)

| Domain | Skill | What it does |
|---|---|---|
| **Prometheus** | `authoring-and-testing-prometheus-rules` | Author, validate, unit-test, simulate, and safely deploy Prometheus alerting and recording rules across `k8s_crd`, `http_ruler`, `local_file`, or `yaml_only`. |
| **Prometheus** | `authoring-promql-and-analyzing-metrics` | Construct, validate, and optimize PromQL 3.0 queries (classic & Native Histograms, UTF-8 names, period comparisons). |
| **Prometheus** | `configuring-prometheus-scraping-and-discovery` | Configure and validate Prometheus target scraping (`ServiceMonitor` with `target_service` auto-discovery, `PodMonitor`, `Probe`, `ScrapeConfig`, Native Histograms/OTLP, `file_sd`). |
| **Prometheus** | `onboarding-exporters-and-instrumentation` | Instrument application code and deploy/verify Kubernetes Prometheus exporters across 20 exporter types. |
| **Prometheus** | `optimizing-tsdb-cardinality-and-finops` | Diagnose and reduce Prometheus TSDB high cardinality, series churn, and remote-write observability costs. |
| **Prometheus** | `triaging-prometheus-incidents-and-slos` | Triage production service incidents and SLO burn-rate alerts using RED/USE methodologies and trace exemplars. |
| **Alertmanager** | `auditing-alertmanager-governance` | Run comprehensive SRE governance and hygiene audits against Prometheus Alertmanager (`SP001`–`SP010`). |
| **Alertmanager** | `diagnosing-missed-notifications` | Diagnose why an expected alert notification was not delivered (inhibition, silences, routing, mute intervals). |
| **Alertmanager** | `managing-alert-silences` | Safely preview, create, update, extend, and expire Alertmanager silences with blast-radius validation. |
| **Alertmanager** | `triaging-alertmanager-alerts` | Triage active Alertmanager firing alerts, correlate alert storms by service/namespace/cluster, and build shift handovers. |
| **Alertmanager** | `validating-alertmanager-routing` | Simulate, validate, and lint Alertmanager routing trees, matchers, receivers, and time intervals. |
| **Grafana Tempo** | `authoring-traceql-and-metrics-queries` | Construct and execute TraceQL 2.x/3.x queries and TraceQL Metrics aggregations against Grafana Tempo. |
| **Grafana Tempo** | `diagnosing-tempo-ingestion-and-health` | Diagnose missing spans, ingestion drops, `ALL_OBSERVATION_CODES`, and Tempo 2.x/3.x backend health. |
| **Grafana Tempo** | `investigating-tempo-latency-regressions` | Pinpoint p95/p99 latency regressions using critical-path waterfall analysis and baseline vs. degraded trace diffs. |
| **Grafana Tempo** | `mapping-tempo-topology-and-alerts` | Map upstream/downstream service dependencies from traces and generate Prometheus `spanmetrics` alert rules. |
| **Grafana Tempo** | `operating-tempo-deployments-and-tenants` | Size, configure, and operate `TempoStack` / `TempoMonolithic` CRs and per-tenant `/api/overrides`. |
| **Grafana Tempo** | `triaging-tempo-service-errors` | Triage elevated 5xx/exception rates using TraceQL error queries and cross-pillar exemplar/log trace pivots. |
| **Grafana Loki** | `authoring-logql-and-analyzing-logs` | Author, lint (`lint_logql.py`), cost-check, and execute 4-stage LogQL log and metric queries and A2UI visualizations. |
| **Grafana Loki** | `authoring-loki-alerting-and-recording-rules` | Design, backtest, validate (`validate_loki_rules.py`), and deploy Loki Ruler rules and `AlertingRule`/`RecordingRule` CRDs. |
| **Grafana Loki** | `discovering-loki-schema-and-log-structure` | Discover indexed stream labels, active series, Loki 3.x structured metadata, and repeating log patterns (`infer_log_parser.py`). |
| **Grafana Loki** | `operating-loki-deployments-and-ingestion` | Diagnose `loki_discarded_samples_total`, execute Compactor PII log deletions, and size Loki 3.x / `LokiStack` CRDs. |
| **Grafana Loki** | `optimizing-loki-cardinality-and-finops` | Audit log volume attribution, high-cardinality indexed labels (`audit_label_cardinality.py`), `structured_metadata` migrations, and Bloom filters. |
| **Grafana Loki** | `triaging-loki-incidents-and-errors` | Triage incidents with $N \to 1$ service log digests, baseline regression comparisons, and cross-service `trace_id` log correlation. |
| **OpenTelemetry** | `auditing-observability-security-posture` | Audit OpenTelemetry Collector and Kubernetes telemetry pipelines for TLS/mTLS, RBAC, and secret leaks. |
| **OpenTelemetry** | `controlling-telemetry-cardinality-and-noise` | Reduce telemetry volume, drop health-check noise, redact PII, and cap metric cardinality using OTTL processors. |
| **OpenTelemetry** | `instrumenting-kubernetes-workloads` | Enable OpenTelemetry auto-instrumentation (`Instrumentation` CR) or eBPF/OBI zero-code telemetry on Kubernetes workloads. |
| **OpenTelemetry** | `provisioning-opentelemetry-collectors` | Design and provision Kubernetes `OpenTelemetryCollector` and `TargetAllocator` topologies. |
| **OpenTelemetry** | `troubleshooting-telemetry-pipelines` | Diagnose and resolve OpenTelemetry Collector pipeline issues (missing data, OOMs, exporter queue drops). |
| **OpenTelemetry** | `tuning-sampling-and-trace-derived-metrics` | Configure tail sampling policies and `spanmetrics` / `servicegraph` connectors on OpenTelemetry Collectors. |
| **OpenTelemetry** | `upgrading-opentelemetry-components` | Safely upgrade OpenTelemetry Operator and Collector versions and migrate deprecated configurations. |
| **Cribl** | `cribl-investigation` | Investigate incidents that involve a Cribl observability pipeline. |
| **Grafana Cloud** | `grafana-cloud-investigation` | Use the Grafana Cloud connector to investigate incidents with the customer's Grafana Cloud telemetry. |

## Slash commands (2)

| Command | Arguments | Purpose |
|---|---|---|
| `/kubernetes-observability-engineer:setup-monitoring` | `<workload, namespace, or service> [--slo <target-pct>] [--signals metrics,logs,traces]` | Instrument Kubernetes workloads with OpenTelemetry, Prometheus exporters, `ServiceMonitor`/`PodMonitor` CRDs, and multi-burn-rate SLO alerting rules. |
| `/kubernetes-observability-engineer:triage` | `<service, namespace, alert-name, or symptom> [--window 30m]` | Run full-stack Kubernetes incident triage correlating Alertmanager alerts, Prometheus RED/SLO metrics, Loki logs, and Tempo distributed traces. |

## MCP servers

Declared in [`.mcp.json`](./.mcp.json) (Claude Code) and [`mcp.json`](./mcp.json) (portable). Every server is pinned to its published PyPI release (also available on Docker Hub under `talkopsai/<server-name>`) and starts in read-only mode (`MCP_ALLOW_WRITE=false`) by default.

`.mcp.json` and `mcp.json` intentionally keep only `FASTMCP_LOG_LEVEL`, `MCP_ALLOW_WRITE`, and portable `${PLUGIN_DATA}` audit-log paths in `env` so they never override `.env` files, multi-backend `*_BACKENDS` JSON settings, alternate URL aliases, or local `KUBECONFIG` discovery. Each server applies the built-in defaults below automatically when an environment variable is unset, and your agent host or runtime can pass any of the variables below in `env` to customize backend URLs, authentication, tenancy, and write permissions.

| Server | Package & release | Launch (`stdio`) | Claude Code tool pattern | Surface |
|---|---|---|---|---|
| `prometheus` | [`talkops-prometheus-mcp-server==0.2.1`](https://pypi.org/project/talkops-prometheus-mcp-server/0.2.1/) · [`prometheus-mcp-server/v0.2.1`](https://github.com/talkops-ai/talkops-mcp/releases/tag/prometheus-mcp-server/v0.2.1) | `uvx --from talkops-prometheus-mcp-server==0.2.1 prometheus-mcp-server --transport stdio` | `mcp__plugin_kubernetes-observability-engineer_prometheus__*` | 19 tools (13 read-only), 11 `prom://` resources |
| `alertmanager` | [`talkops-alertmanager-mcp-server==0.2.1`](https://pypi.org/project/talkops-alertmanager-mcp-server/0.2.1/) · [`alertmanager-mcp-server/v0.2.1`](https://github.com/talkops-ai/talkops-mcp/releases/tag/alertmanager-mcp-server/v0.2.1) | `uvx --from talkops-alertmanager-mcp-server==0.2.1 alertmanager-mcp-server --transport stdio` | `mcp__plugin_kubernetes-observability-engineer_alertmanager__*` | 14 tools (9 read-only), 10 `am://` resources |
| `tempo` | [`talkops-tempo-mcp-server==0.2.1`](https://pypi.org/project/talkops-tempo-mcp-server/0.2.1/) · [`tempo-mcp-server/v0.2.1`](https://github.com/talkops-ai/talkops-mcp/releases/tag/tempo-mcp-server/v0.2.1) | `uvx --from talkops-tempo-mcp-server==0.2.1 tempo-mcp-server --transport stdio` | `mcp__plugin_kubernetes-observability-engineer_tempo__*` | 18 tools (16 read-only), 10 `tempo://` resources |
| `loki` | [`talkops-loki-mcp-server==0.2.1`](https://pypi.org/project/talkops-loki-mcp-server/0.2.1/) · [`loki-mcp-server/v0.2.1`](https://github.com/talkops-ai/talkops-mcp/releases/tag/loki-mcp-server/v0.2.1) | `uvx --from talkops-loki-mcp-server==0.2.1 loki-mcp-server --transport stdio` | `mcp__plugin_kubernetes-observability-engineer_loki__*` | 18 tools (14 read-only), 9 `loki://` resources |
| `opentelemetry` | [`talkops-opentelemetry-mcp-server==0.2.1`](https://pypi.org/project/talkops-opentelemetry-mcp-server/0.2.1/) · [`opentelemetry-mcp-server/v0.2.1`](https://github.com/talkops-ai/talkops-mcp/releases/tag/opentelemetry-mcp-server/v0.2.1) | `uvx --from talkops-opentelemetry-mcp-server==0.2.1 opentelemetry-mcp-server --transport stdio` | `mcp__plugin_kubernetes-observability-engineer_opentelemetry__*` | 17 tools (7 read-only), 14 `otel://` resources |

### Environment variable reference (defaults & customization)

Pass these environment variables from your shell, `.env`, agent runtime `env` map, or `~/.codex/config.toml` (`[mcp_servers.<server>.env]`) to connect to your observability backends and clusters:

#### `prometheus` (`talkops-prometheus-mcp-server`)

| Environment variable | Requirement | Built-in default | Description |
|---|---|---|---|
| `PROMETHEUS_BASE_URL` (or `PROMETHEUS_URL`) | **Required** if not on `localhost:9090` (unless `PROMETHEUS_BACKENDS` is set) | `http://localhost:9090` | Base URL of your Prometheus, Mimir, Thanos, Cortex, or VictoriaMetrics HTTP API. |
| `PROMETHEUS_AUTH_HEADER` | Conditional | *none* | Full `Authorization` header value (e.g., `Bearer <token>` or `Basic <base64>`). |
| `PROMETHEUS_TENANT_ID` | Conditional | *none* | `X-Scope-OrgID` tenant header for multi-tenant Mimir, Cortex, or Thanos. |
| `PROMETHEUS_TYPE` / `PROMETHEUS_RULER_URL` | Optional | `prometheus` / *none* | Backend flavor (`prometheus`, `mimir`, `thanos`, `cortex`, `victoriametrics`) and dedicated HTTP Ruler URL. |
| `PROMETHEUS_VERIFY_SSL` / `PROMETHEUS_TIMEOUT` | Optional | `true` / `30` | TLS certificate verification toggle and HTTP request timeout in seconds. |
| `PROMETHEUS_BACKENDS` | Optional | *none* | JSON array of backend objects (`[{"id": "...", "base_url": "...", "type": "...", "tenant_id": "...", "auth_header": "..."}]`) replacing single-URL config for multi-cluster setups. |
| `K8S_ENABLED` / `K8S_KUBECONFIG` (or `KUBECONFIG`) / `K8S_CONTEXT` (or `KUBE_CONTEXT`) | Conditional | `true` / `~/.kube/config` / current context | Kubernetes connection settings used for `PrometheusRule`, `ServiceMonitor`/`PodMonitor`/`Probe`, and exporter tools (`K8S_IN_CLUSTER` defaults to `false`). |
| `PROMETHEUS_AUDIT_LOG_PATH` | Optional | `${PLUGIN_DATA}/prometheus-audit.jsonl` (`mcp.json`) | JSONL audit log path for mutating operations. |
| `MCP_ALLOW_WRITE` / `MCP_READ_ONLY` | Optional | `false` (plugin config) / `false` | Set `MCP_ALLOW_WRITE=true` to enable rule, scrape-config, and exporter mutation tools (note: standalone CLI defaults `MCP_ALLOW_WRITE` to `true` unless `--read-only` or `MCP_ALLOW_WRITE=false` is set). |
| `PROMETHEUS_TOOLSETS` (or `MCP_TOOLSETS`) | Optional | `all` | Comma-separated toolset filter: `all`, `diagnostics`, `query`, `rules`, `scrape`, `exporter`, `readonly`. |

#### `alertmanager` (`talkops-alertmanager-mcp-server`)

| Environment variable | Requirement | Built-in default | Description |
|---|---|---|---|
| `ALERTMANAGER_BASE_URL` (or `ALERTMANAGER_URL`) | **Required** if not on `localhost:9093` (unless `ALERTMANAGER_BACKENDS` is set) | `http://localhost:9093` | Base URL of your Prometheus Alertmanager v2 API. |
| `ALERTMANAGER_AUTH_HEADER` | Conditional | *none* | Full `Authorization` header value (e.g., `Bearer <token>`). |
| `ALERTMANAGER_BASIC_AUTH_USERNAME` / `ALERTMANAGER_BASIC_AUTH_PASSWORD_ENV` | Conditional | *none* / *none* | HTTP Basic Auth username and the **name** of the environment variable containing the password. |
| `ALERTMANAGER_PATH_PREFIX` / `ALERTMANAGER_VERIFY_SSL` / `ALERTMANAGER_TIMEOUT` | Optional | `""` / `true` / `30` | Reverse-proxy path prefix (e.g., `/alertmanager` on Mimir/Cortex), TLS verification toggle, and timeout in seconds. |
| `ALERTMANAGER_BACKENDS` | Optional | *none* | JSON array of Alertmanager backends (`[{"id": "...", "base_url": "...", "is_default": true}]`) for multi-cluster setups. |
| `AM_AUDIT_LOG_PATH` | Optional | `${PLUGIN_DATA}/alertmanager-audit.jsonl` (`mcp.json`) | JSONL audit trail path for silence and test-alert mutations. |
| `AM_MAX_SILENCE_MINUTES` / `AM_SILENCE_CONFIRM_THRESHOLD` / `AM_SILENCE_COMMENT_PATTERN` | Optional | `1440` / `50` / *none* | Silence governance guardrails (`SP001`–`SP010`): max silence duration (minutes), alert match count requiring confirmation, and required comment regex. |
| `MCP_ALLOW_WRITE` | Optional | `false` | Set to `true` to enable `am_create_silence`, `am_silence_alert`, `am_update_silence`, `am_expire_silence`, and `am_push_test_alert`. |
| `MCP_TOOLSETS` | Optional | `all` | Comma-separated toolset filter: `all`, `triage`, `routing`, `silences`, `governance`. |

#### `tempo` (`talkops-tempo-mcp-server`)

| Environment variable | Requirement | Built-in default | Description |
|---|---|---|---|
| `TEMPO_BASE_URL` (or `TEMPO_URL`) | **Required** if not on `localhost:3200` (unless `TEMPO_BACKENDS` is set) | `http://localhost:3200` | Base URL of your Grafana Tempo HTTP API. |
| `TEMPO_AUTH_HEADER` | Conditional | *none* | Full `Authorization` header value (e.g., `Bearer <token>` or `Basic <base64>`). |
| `TEMPO_MULTI_TENANT` / `TEMPO_DEFAULT_TENANT` / `TEMPO_TENANT_HEADER` | Conditional | `false` / *none* / `X-Scope-OrgID` | Enable multi-tenant mode and set the default `X-Scope-OrgID` tenant header (required when Tempo runs with multitenancy enabled). |
| `TEMPO_VERIFY_SSL` / `TEMPO_TIMEOUT` | Optional | `true` / `30` | TLS certificate verification toggle and HTTP request timeout in seconds. |
| `TEMPO_BACKENDS` | Optional | *none* | JSON array of Tempo backend definitions replacing single-URL config. |
| `PROMETHEUS_BASE_URL` (or `PROMETHEUS_URL`) | Optional | *none* | Prometheus base URL for `spanmetrics` / `servicegraph` fallback RED and topology queries. |
| `K8S_ENABLED` / `K8S_KUBECONFIG` (or `KUBECONFIG`) / `K8S_CONTEXT` | Conditional | `false` / `~/.kube/config` / current context | Set `K8S_ENABLED=true` to enable Tempo Operator (`TempoStack` / `TempoMonolithic`) discovery and `tempo_apply_operator_cr` (`K8S_IN_CLUSTER` defaults to `false`). |
| `MCP_ALLOW_WRITE` | Optional | `false` | Set to `true` to enable `tempo_patch_tenant_overrides` and `tempo_apply_operator_cr`. |
| `MCP_TOOLSETS` | Optional | `all` | Comma-separated toolset filter: `all`, `search`, `metrics`, `diagnostics`, `overrides`, `operator`, `readonly`. |

#### `loki` (`talkops-loki-mcp-server`)

| Environment variable | Requirement | Built-in default | Description |
|---|---|---|---|
| `LOKI_URL` | **Required** outside in-cluster `http://loki:3100` | `http://loki:3100` | Base URL of your Grafana Loki HTTP API (e.g., `http://localhost:3100` for local port-forwards or your ingress URL). |
| `LOKI_ORG_ID` | Conditional | *none* | `X-Scope-OrgID` tenant header (required when Loki `auth_enabled: true` multi-tenancy is enabled). |
| `LOKI_AUTH_TOKEN` | Conditional | *none* | Bearer token for Loki authentication (or use `LOKI_BASIC_AUTH_USER` + `LOKI_BASIC_AUTH_PASSWORD` for HTTP Basic Auth). |
| `LOKI_VERIFY_SSL` / `LOKI_TIMEOUT` | Optional | `true` / `30` | TLS certificate verification toggle and HTTP request timeout in seconds. |
| `K8S_ENABLED` / `K8S_KUBECONFIG` (or `KUBECONFIG`) / `K8S_CONTEXT` | Conditional | `false` / `~/.kube/config` / current context | Set `K8S_ENABLED=true` to enable Loki Operator (`LokiStack`, `AlertingRule`, `RecordingRule`) inspection and `loki_apply_operator_cr` (`K8S_IN_CLUSTER` defaults to `false`). |
| `MCP_ALLOW_WRITE` | Optional | `false` | Set to `true` to enable Loki Ruler rule upserts/deletes, Compactor log delete requests, and `loki_apply_operator_cr`. |
| `LOKI_TOOLSETS` (or `MCP_TOOLSETS`) | Optional | `all` | Comma-separated toolset filter: `all`, `discovery`, `query`, `analysis`, `diagnostics`, `rules`, `governance`, `operator`, `readonly`. |

#### `opentelemetry` (`talkops-opentelemetry-mcp-server`)

| Environment variable | Requirement | Built-in default | Description |
|---|---|---|---|
| `K8S_KUBECONFIG` (or `KUBECONFIG`) | Required if `~/.kube/config` is absent and `K8S_IN_CLUSTER=false` | `~/.kube/config` | Path to kubeconfig file for inspecting and managing OpenTelemetry Operator CRDs and workloads. |
| `K8S_CONTEXT` (or `KUBE_CONTEXT`) | Optional | current kubeconfig context | Target Kubernetes context name. |
| `K8S_ENABLED` / `K8S_IN_CLUSTER` | Optional | `true` / `false` | Kubernetes API integration toggle and in-cluster ServiceAccount mode. |
| `OTEL_COLLECTOR_VERSION_DEFAULT` | Optional | `0.152.1` | Default `otel/opentelemetry-collector-contrib` image tag used when provisioning new collectors. |
| `PROMETHEUS_BASE_URL` (or `PROMETHEUS_URL`) | Optional | *none* | Prometheus base URL for querying live `otelcol_*` internal collector metrics (queue drops, exporter failures). |
| `MCP_ALLOW_WRITE` | Optional | `false` | Set to `true` to enable collector provisioning/patching/reversion, workload auto-instrumentation, and OTTL/sampling/connector mutation tools. |
| `MCP_TOOLSETS` | Optional | `all` | Comma-separated toolset filter: `all`, `discovery`, `collector`, `instrumentation`, `pipeline`, `diagnostics`, `governance`, `readonly`. |

### Passing custom `env` values from an agent host

When injecting environment variables from an agent platform or overriding `mcpServers.<server>.env`, pass only the non-empty settings you want to customize:

```json
{
  "prometheus": {
    "env": {
      "PROMETHEUS_BASE_URL": "https://prometheus.example.com",
      "PROMETHEUS_AUTH_HEADER": "Bearer <prom-token>",
      "PROMETHEUS_TENANT_ID": "prod",
      "KUBECONFIG": "/etc/kube/config",
      "MCP_ALLOW_WRITE": "false"
    }
  },
  "alertmanager": {
    "env": {
      "ALERTMANAGER_BASE_URL": "https://alertmanager.example.com",
      "ALERTMANAGER_AUTH_HEADER": "Bearer <am-token>",
      "MCP_ALLOW_WRITE": "false"
    }
  },
  "tempo": {
    "env": {
      "TEMPO_BASE_URL": "https://tempo.example.com",
      "TEMPO_AUTH_HEADER": "Bearer <tempo-token>",
      "TEMPO_MULTI_TENANT": "true",
      "TEMPO_DEFAULT_TENANT": "prod",
      "PROMETHEUS_URL": "https://prometheus.example.com",
      "K8S_ENABLED": "true",
      "KUBECONFIG": "/etc/kube/config",
      "MCP_ALLOW_WRITE": "false"
    }
  },
  "loki": {
    "env": {
      "LOKI_URL": "https://loki.example.com",
      "LOKI_AUTH_TOKEN": "<loki-bearer-token>",
      "LOKI_ORG_ID": "prod",
      "K8S_ENABLED": "true",
      "KUBECONFIG": "/etc/kube/config",
      "MCP_ALLOW_WRITE": "false"
    }
  },
  "opentelemetry": {
    "env": {
      "KUBECONFIG": "/etc/kube/config",
      "K8S_CONTEXT": "prod-cluster",
      "PROMETHEUS_URL": "https://prometheus.example.com",
      "MCP_ALLOW_WRITE": "false"
    }
  }
}
```

## Optional connectors

Connection-bound partner MCP servers you add yourself (see [CONNECTORS.md](./CONNECTORS.md)): `grafana-cloud`, `cribl`.

## Hooks

- **PreToolUse** `Bash|mcp__.*|mcp__plugin_kubernetes-observability-engineer_.*` — command: `sh -c 'command -v python3 >/dev/null 2>&1 && exec python3 "$0"; command -v python >/dev/null 2>&1 && exec python "$0"; exec py -3 "$0"' "${CLAUDE_PLUGIN_ROOT}/hooks/secret-safety.py"`

## Upstream

Derived from the following open-source sources (see the repository `NOTICE`):

- [`talkops-mcp`](https://github.com/talkops-ai/talkops-mcp) (talkops-ai/talkops-mcp, Apache-2.0)
- [`tools-for-devops-agent`](https://github.com/aws/tools-for-devops-agent) (aws/tools-for-devops-agent, Apache-2.0)
