---
name: triaging-loki-incidents-and-errors
description: Triages production incidents, error rate spikes, CrashLoopBackOff events, and cross-service failures using high-signal Loki aggregation tools, period-over-period comparisons, and trace-to-log correlation. Use when investigating service outages, 5xx spikes, latency regressions, or correlating distributed trace IDs with log streams. Do not use for writing standalone LogQL syntax tutorials (use authoring-logql-and-analyzing-logs) or configuring Loki storage/compactor settings (use operating-loki-deployments-and-ingestion).
license: Apache-2.0
metadata:
  author: TalkOps
  version: "0.2.0"
  domain: observability
  service: grafana-loki
---

# Triaging Loki Incidents and Errors

Use this skill to execute a fast, token-efficient incident triage workflow that isolates root-cause error signatures, detects new regressions across deployments, and correlates logs with traces and metrics.

## Core Rule: Aggregate First, Drill Down Second

Never start an incident investigation by dumping hundreds of raw log lines into your context window. Always start with the $N \to 1$ composite analysis tools (`loki_summarize_service_logs`, `loki_compare_periods`, `loki_correlate_trace_logs`) and only inspect targeted raw log lines when needed.

## Incident Triage Workflow

### Step 1: Verify Backend Health and Target Environment
1. Read `loki://system/health` and `loki://config/backends` to verify Loki readiness and confirm the target cluster/tenant.
2. Identify the affected workload selector (e.g., `{service_name="checkout", namespace="prod"}`) and the incident time window (`start`, `end`).

### Step 2: Generate a One-Shot Service Health & Error Digest
Call `loki_summarize_service_logs` with `selector`, `start` (e.g., `"now-30m"`), and `end`:
- Inspect `index_stats`, `error_summary.sampled_error_lines`, and `error_summary.estimated_error_ratio` to quantify impact.
- Review `error_summary.top_error_signatures` to see whether a single error template dominates volume.
- Review `sample_error_streams` and `extracted_trace_ids` for stack traces, upstream connection refusals, or `trace_id` values.

### Step 3: Separate New Regressions from Chronic Noise
Call `loki_compare_periods` with `selector`, `start` (e.g., `"now-15m"`), and `baseline_offset` (e.g., `"1h"` or `"24h"`):
- Check `error_count_delta_pct` and `regression_detected`.
- Focus first on `new_error_signatures` (error templates that had `0` occurrences in the baseline window)—these almost always correspond to the triggering deploy, config change, or downstream outage.

### Step 4: Cluster Raw Error Lines Locally (Optional)
When you pull raw error samples via `loki_query_range`, pipe them through [scripts/extract_error_signatures.py](scripts/extract_error_signatures.py) to deduplicate UUIDs, timestamps, and IPs into clean failure clusters and extract embedded `trace_id` values:
```bash
python skills/triaging-loki-incidents-and-errors/scripts/extract_error_signatures.py \
  --input error_lines.json --json
```

### Step 5: Pivot Across Services via Trace/Request ID
When `loki_summarize_service_logs` or `loki_query_range` surfaces a `trace_id`, `span_id`, or `request_id`:
1. Call `loki_correlate_trace_logs` with `correlation_id` (and optional `scope_selector` or `correlation_key`) to reconstruct the full chronological cross-service log timeline.
2. Locate the **earliest service in the timeline** that logged an error or timeout—that service is the root failure point, while upstream services logging 502/504 are cascading victims.
3. If the user asks for an interactive visual timeline or chart, render the query with `loki_query_a2ui`.

### Step 6: Deliver the Structured Incident Brief
Synthesize your findings using [references/incident-brief-template.md](references/incident-brief-template.md).

## Key Reference Guides & Scripts

- [references/incident-triage-sop.md](references/incident-triage-sop.md) — Playbooks for 5xx spikes, latency degradation, CrashLoopBackOff/OOMs, and database connection pool exhaustion.
- [references/cross-pillar-correlation-guide.md](references/cross-pillar-correlation-guide.md) — How to pivot seamlessly between Grafana Loki logs, Prometheus metrics, and Tempo distributed traces using OpenTelemetry resource attributes and exemplars.
- [references/incident-brief-template.md](references/incident-brief-template.md) — Standardized executive + engineering root-cause report format.
- [scripts/extract_error_signatures.py](scripts/extract_error_signatures.py) — Deterministic log clustering script that normalizes dynamic tokens (UUIDs, IPs, hex IDs, numbers) into canonical error signatures and extracts trace IDs.
