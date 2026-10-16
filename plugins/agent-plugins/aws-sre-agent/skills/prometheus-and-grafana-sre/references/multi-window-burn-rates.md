# Multi-Window, Multi-Burn-Rate SLO Recording & Alerting Rules for AMP Ruler

Use this reference to author Amazon Managed Service for Prometheus (AMP) Ruler YAML files (`aws amp create-rule-groups-namespace` / `put-rule-groups-namespace`).

---

## 1. Error Budget Math by SLO Tier (30-Day Window)

| SLO Target | Error Budget (`1 - SLO`) | Allowed Downtime / 30d | 14.4x Fast Burn Threshold | 6.0x Medium Burn Threshold | 1.0x Slow Burn Threshold |
|---|---|---|---|---|---|
| **99.95%** | `0.0005` | 21.6 minutes | `0.0072` (0.72% errors) | `0.0030` (0.30% errors) | `0.0005` (0.05% errors) |
| **99.9%** | `0.001` | 43.2 minutes | `0.0144` (1.44% errors) | `0.0060` (0.60% errors) | `0.0010` (0.10% errors) |
| **99.5%** | `0.005` | 3.6 hours | `0.0720` (7.20% errors) | `0.0300` (3.00% errors) | `0.0050` (0.50% errors) |

---

## 2. Complete AMP Rule Group Namespace YAML (`99.9%` Availability SLO)

```yaml
groups:
  - name: slo-http-availability-recording
    interval: 30s
    rules:
      - record: job:slo_errors_per_request:ratio_rate5m
        expr: |
          sum by (namespace, service) (rate(http_requests_total{status=~"5.."}[5m]))
          /
          clamp_min(sum by (namespace, service) (rate(http_requests_total[5m])), 1e-9)

      - record: job:slo_errors_per_request:ratio_rate30m
        expr: |
          sum by (namespace, service) (rate(http_requests_total{status=~"5.."}[30m]))
          /
          clamp_min(sum by (namespace, service) (rate(http_requests_total[30m])), 1e-9)

      - record: job:slo_errors_per_request:ratio_rate1h
        expr: |
          sum by (namespace, service) (rate(http_requests_total{status=~"5.."}[1h]))
          /
          clamp_min(sum by (namespace, service) (rate(http_requests_total[1h])), 1e-9)

      - record: job:slo_errors_per_request:ratio_rate6h
        expr: |
          sum by (namespace, service) (rate(http_requests_total{status=~"5.."}[6h]))
          /
          clamp_min(sum by (namespace, service) (rate(http_requests_total[6h])), 1e-9)

      - record: job:slo_errors_per_request:ratio_rate3d
        expr: |
          sum by (namespace, service) (rate(http_requests_total{status=~"5.."}[3d]))
          /
          clamp_min(sum by (namespace, service) (rate(http_requests_total[3d])), 1e-9)

  - name: slo-http-availability-alerts
    interval: 30s
    rules:
      - alert: SLOErrorBudgetBurnCritical
        expr: |
          job:slo_errors_per_request:ratio_rate1h > (14.4 * 0.001)
          and
          job:slo_errors_per_request:ratio_rate5m > (14.4 * 0.001)
        for: 2m
        labels:
          severity: critical
          page: "true"
        annotations:
          summary: "High error budget burn (14.4x) on {{ $labels.namespace }}/{{ $labels.service }}"
          description: "Service {{ $labels.service }} is burning 2% of its 30-day 99.9% error budget per hour."

      - alert: SLOErrorBudgetBurnHigh
        expr: |
          job:slo_errors_per_request:ratio_rate6h > (6.0 * 0.001)
          and
          job:slo_errors_per_request:ratio_rate30m > (6.0 * 0.001)
        for: 15m
        labels:
          severity: high
          page: "true"
        annotations:
          summary: "Sustained error budget burn (6x) on {{ $labels.namespace }}/{{ $labels.service }}"
          description: "Service {{ $labels.service }} will consume 5% of its 30-day error budget in 6 hours."

      - alert: SLOErrorBudgetBurnTicket
        expr: |
          job:slo_errors_per_request:ratio_rate3d > (1.0 * 0.001)
          and
          job:slo_errors_per_request:ratio_rate6h > (1.0 * 0.001)
        for: 1h
        labels:
          severity: warning
          page: "false"
        annotations:
          summary: "Slow error budget burn (1x) on {{ $labels.namespace }}/{{ $labels.service }}"
          description: "Service {{ $labels.service }} is consuming >10% of its 30-day error budget over 3 days."
```
