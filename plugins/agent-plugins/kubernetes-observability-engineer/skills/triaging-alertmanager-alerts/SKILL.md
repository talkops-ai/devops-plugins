---
name: triaging-alertmanager-alerts
description: Triages active and suppressed Prometheus Alertmanager alerts during incidents, alert storms, and on-call shift handovers. Use when asked to summarize firing alerts, prioritize critical incidents, investigate alert storms, inspect Alertmanager dispatch groups, or prepare an on-call shift handover report. Do not use for creating silences (use managing-alert-silences) or debugging missing receiver notifications (use diagnosing-missed-notifications).
license: Apache-2.0
metadata:
  author: talkops
  version: "0.2.0"
  domain: observability
  component: alertmanager
---

# Triaging Alertmanager Alerts

## Overview

Guides structured on-call triage of firing and suppressed alerts across one or more Alertmanager backends. Prioritizes pipeline liveness (`Watchdog`), blast radius across services, root-cause vs. symptom separation via inhibition state, and actionable shift handovers.

## MCP Execution Primitives Used

- **Resources**:
  - `am://backends` — discover configured Alertmanager backends and verify live health.
  - `am://backends/{backend_id}/alerts/active` — bounded snapshot of currently firing alerts.
  - `am://backends/{backend_id}/alerts/groups` — Alertmanager dispatch groups grouped by route `group_by` labels.
  - `am://backends/{backend_id}/alerts/{fingerprint}` — full labels, annotations (`summary`, `runbook_url`), and suppression status for a single alert.
- **Tools (`triage` & `routing` toolsets)**:
  - `am_summarize_oncall` — aggregate active and suppressed alerts by severity, environment, service, and team, including `Watchdog` status.
  - `am_list_alerts` — query alerts using exact or regex matchers (`label_filters`), receiver filters, and state filters (`active`, `suppressed`, `silenced`, `inhibited`, `unprocessed`).
  - `am_list_alert_groups` — inspect grouped alert batches as dispatched to receivers.
  - `am_explain_routing` — trace which receiver owns a firing alert and whether inhibition rules apply.

## Step-by-Step Triage Workflow

### 1. Verify Backend & Pipeline Liveness
1. Read `am://backends` if the target `backend_id` is not already known.
2. Call `am_summarize_oncall(backend_id=...)` (optionally scoped by `env`, `service`, or `team`).
3. Check `watchdog_status` in the response:
   - If `watchdog_status == "missing"` or `"suppressed"`, flag a **Priority-0 monitoring pipeline issue**: Prometheus may not be delivering alerts to Alertmanager, or someone silenced `Watchdog`.

### 2. Prioritize by Severity and Blast Radius
Consult [references/severity-response-matrix.md](references/severity-response-matrix.md) to classify response urgency:
1. Inspect `by_severity`, `by_service`, and `top_alert_groups` from `am_summarize_oncall`.
2. During an **alert storm** ($\ge 20$ firing alerts):
   - Call `am_list_alert_groups(backend_id=..., state="active")` to collapse individual instance alerts into receiver dispatch groups.
   - Identify shared infrastructure labels (`cluster`, `namespace`, `zone`, `node`, `db_cluster`) across groups to isolate the upstream root cause before investigating downstream application symptoms.

### 3. Inspect High-Priority Alerts & Suppressed Context
1. Call `am_list_alerts(backend_id=..., severity="critical", state="active")` to retrieve critical firing alerts with their fingerprints, `startsAt` timestamps, and annotations.
2. For each top critical alert group, read `am://backends/{backend_id}/alerts/{fingerprint}` or inspect `annotations.runbook_url` and `annotations.summary`.
3. Check whether related alerts are suppressed by calling `am_list_alerts(backend_id=..., state="suppressed", label_filters={"service": "<affected_service>"})`:
   - Alerts in `inhibited` state confirm that an upstream root-cause alert is already firing (`status.inhibitedBy`).
   - Alerts in `silenced` state indicate an active maintenance window or manual suppression (`status.silencedBy`).

### 4. Produce the Triage or Shift Handover Summary
Format the output using [references/handover-template.md](references/handover-template.md), including:
- Pipeline health (`backend_id`, `watchdog_status`, active silence count).
- Critical and warning incident groups ordered by blast radius and firing duration.
- Root-cause candidates vs. downstream inhibited symptoms.
- Direct runbook links (`annotations.runbook_url`) and recommended next actions.
