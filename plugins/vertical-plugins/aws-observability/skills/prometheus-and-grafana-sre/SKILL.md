---
name: prometheus-and-grafana-sre
description: Query Amazon Managed Service for Prometheus (AMP) using PromQL, design multi-window multi-burn-rate SLO alerting rules, troubleshoot EKS/ECS container and node telemetry, and build Amazon Managed Grafana (AMG) operational dashboards. Use when the user asks about PromQL queries, AMP workspaces, node_exporter/kube-state-metrics/cAdvisor metrics, Prometheus recording or alerting rules, or Grafana dashboards.
---

# Amazon Managed Service for Prometheus (AMP) & Grafana (AMG) SRE Guide

Use this skill when investigating container/Kubernetes incidents via Amazon Managed Service for Prometheus (`prometheus` MCP server), writing PromQL queries for Four Golden Signals or USE metrics, designing multi-window multi-burn-rate SLO alerts, or auditing scrape/cardinality health.

---

## 1. Mandatory AMP MCP Discovery Workflow

Never hardcode metric names or label keys without verifying the active workspace schema first:

1. **Discover Workspaces**: Call `GetAvailableWorkspaces` to list AMP workspaces in the target region and obtain the `workspace_id` (`ws-...`).
2. **Inspect Workspace Configuration**: Call `DescribeWorkspace` to verify workspace status, endpoint URL, and KMS/logging configuration.
3. **Discover Metrics & Labels**:
   - Call `ListMetrics` to inspect exported metric names (e.g., `container_cpu_usage_seconds_total`, `kube_pod_container_status_restarts_total`, `http_requests_total`).
   - Call `GetSeries` or `ExecuteQuery` with `group by (...)` to verify exact label names (`namespace`, `pod`, `container`, `service`, `status_code`, `le`) before running complex aggregations.
4. **Execute Queries**:
   - Use `ExecuteQuery` for instant point-in-time snapshots (current saturation, active pod restarts, top cardinality).
   - Use `ExecuteRangeQuery` with explicit `start`, `end`, and `step` (e.g., `60s` or `5m`) to correlate incident onset timelines.

---

## 2. Four Golden Signals & USE Method in PromQL

### Traffic (RPS by Service / Route)
```promql
sum by (namespace, service) (
  rate(http_requests_total[5m])
)
```

### Errors (5xx Error Ratio)
```promql
sum by (namespace, service) (rate(http_requests_total{status=~"5.."}[5m]))
/
clamp_min(sum by (namespace, service) (rate(http_requests_total[5m])), 1e-9)
```

### Latency (P99 & P95 from Classic Histograms)
```promql
histogram_quantile(
  0.99,
  sum by (namespace, service, le) (
    rate(http_request_duration_seconds_bucket[5m])
  )
)
```
*(Always `sum by (..., le)` inside `histogram_quantile()` and wrap counters in `rate()` first.)*

### Container CPU Throttling & Memory OOM Saturation (`cAdvisor` + `kube-state-metrics`)
```promql
# CPU CFS Throttling Ratio (> 0.25 indicates severe CPU limit throttling)
sum by (namespace, pod, container) (rate(container_cpu_cfs_throttled_periods_total{container!=""}[5m]))
/
clamp_min(sum by (namespace, pod, container) (rate(container_cpu_cfs_periods_total{container!=""}[5m])), 1e-9)

# Working Set Memory vs Memory Limit Ratio (> 0.90 indicates imminent OOMKilled / Exit Code 137)
sum by (namespace, pod, container) (container_memory_working_set_bytes{container!="", image!=""})
/
sum by (namespace, pod, container) (kube_pod_container_resource_limits{resource="memory"})
```

---

## 3. Multi-Window, Multi-Burn-Rate SLO Alerting (Google SRE Workbook Standard)

Single-window rate alerts either page too late or suffer from high false-positive reset noise. Always pair a **long window** with a **short confirmation window** (`short = 1/12 * long`):

| Severity | Burn Rate | Long Window | Short Window | Budget Consumed | Action |
|---|---|---|---|---|---|
| **Page (Critical)** | **14.4x** | `1h` | `5m` | 2% in 1 hour | Immediate pager alert (`for: 2m`) |
| **Page (High)** | **6.0x** | `6h` | `30m` | 5% in 6 hours | Pager alert (`for: 15m`) |
| **Ticket (Warning)** | **1.0x** | `3d` | `6h` | 10% in 3 days | Issue ticket (`for: 1h`) |

For a **99.9% SLO** (error budget `0.001`), the **14.4x** threshold is `14.4 * 0.001 = 0.0144`:
```promql
(
  job:slo_errors_per_request:ratio_rate1h{service="checkout"} > (14.4 * 0.001)
  and
  job:slo_errors_per_request:ratio_rate5m{service="checkout"} > (14.4 * 0.001)
)
```

---

## 4. AMP Cardinality & Scrape Health Auditing

- **Identify Top 20 Highest-Cardinality Metrics**:
  ```promql
  topk(20, count by (__name__)({__name__=~".+"}))
  ```
- **Verify Collector & Target Scrape Health**:
  ```promql
  up == 0
  ```
  ```promql
  topk(10, scrape_samples_scraped)
  ```

---

## Reference Files

- [references/promql-sre-templates.md](references/promql-sre-templates.md) — Production PromQL library for Kubernetes (`kube-state-metrics`, `cAdvisor`, `node_exporter`), ALB/Ingress, JVM/Go runtime, and USE saturation signals
- [references/multi-window-burn-rates.md](references/multi-window-burn-rates.md) — Complete AMP Ruler recording-rule and alerting-rule YAML manifests for 99.9%, 99.95%, and 99.5% SLO tiers
