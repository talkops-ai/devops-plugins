---
description: Run full-stack Kubernetes incident triage correlating Alertmanager alerts, Prometheus RED/SLO metrics, Loki logs, and Tempo distributed traces
argument-hint: "<service, namespace, alert-name, or symptom> [--window 30m]"
---

Invoke **triaging-alertmanager-alerts**, **triaging-prometheus-incidents-and-slos**, **triaging-loki-incidents-and-errors**, and **triaging-tempo-service-errors** (chaining **investigating-tempo-latency-regressions** for latency spikes and **troubleshooting-telemetry-pipelines** when OpenTelemetry collector drops, OOMs, or missing telemetry signals are suspected) to perform a correlated 4-signal SRE triage:
1. Inspect firing/inhibited Alertmanager alerts and recent workload restarts or saturation signals in the target namespace.
2. Query Prometheus RED (Rate, Errors, Duration) and USE metrics plus SLO burn rates, extracting trace exemplars where available.
3. Run discovery-first LogQL queries against Loki to isolate anomalous error patterns, stack traces, and release regressions correlated by pod and `trace_id`.
4. Query Tempo via TraceQL to pinpoint critical-path span errors or downstream dependency bottlenecks, and deliver an evidence-backed root-cause summary with concrete remediation steps.

Triage scope: $ARGUMENTS
