---
name: live-site-incident-postmortem
description: Coordinate Sev-1/Sev-2 AWS live-site incident command and author blameless Correction of Errors (COE) / Postmortem documents with UTC timelines, 5-Whys root-cause analysis, blast-radius quantification, and tracked preventive action items. Use when the user asks for an incident postmortem, COE document, RCA report, incident timeline reconstruction, or live-site war-room coordination.
---

# Live-Site Incident Command & Correction of Errors (COE) Postmortem Guide

Use this skill during active **Sev-1 / Sev-2 live-site incident response** ("stop the bleeding first") and after mitigation to generate an Amazon-style **Correction of Errors (COE) / Blameless Postmortem** backed by exact UTC telemetry and change history.

---

## 1. Live-Site Incident Command Protocol ("Stop the Bleeding First")

During an active outage, **Mean Time to Recovery (MTTR)** takes absolute priority over deep root-cause exploration:

1. **Establish the Incident Window & Blast Radius (`T+0` to `T+5m`)**:
   - Query `cloudwatch.get_active_alarms` and `appsignals.list_slos` to quantify which customer-facing SLOs and Availability Zones are impacted.
   - Determine whether failure is **Zonal (single AZ)**, **Regional**, **Deployment-induced**, or **Capacity/Quota-induced**.
2. **Evaluate Immediate Mitigation Levers (`T+5m` to `T+15m`)**:
   - **Single-AZ Impairment**: Propose **Route 53 Application Recovery Controller (ARC) Zonal Shift** (`aws arc-zonal-shift start-zonal-shift`) to drain ALB/NLB traffic away from the impaired AZ in seconds.
   - **Bad Deployment / Config Push**: Correlate with `cloudtrail.lookup_events` or `ecs`/`eks` revision history and propose an immediate **rollback** to the last known-good revision (`ecs update-service --task-definition <prev>`, `kubectl rollout undo`, or CodeDeploy/CloudFormation rollback).
   - **Traffic Surge / Retry Storm / DDoS**: Propose WAF rate-based rules, API Gateway/AppConfig feature-flag shedding, or emergency capacity scale-out.
   - **Regional Catastrophe**: Evaluate **ARC Routing Control** or **ARC Region Switch** (`arc-region-switch` skill) only after verifying standby region readiness.
3. **Preserve Forensic Evidence Before Destructive Recovery**:
   - Before terminating wedged instances or pods, capture log streams (`cloudwatch.execute_log_insights_query`), X-Ray fault traces (`appsignals.query_sampled_traces`), and task/pod stop codes (`eks.get_k8s_events`, `ecs.ecs_troubleshooting_tool`).

---

## 2. Reconstructing the UTC Incident Timeline

Every timestamp in a COE must be anchored to **UTC** (`YYYY-MM-DD HH:MM:SS UTC`) and backed by an explicit telemetry or audit source:

| Milestone | Required Telemetry Source | Definition |
|---|---|---|
| **`T_trigger`** | `cloudtrail.lookup_events` / Git / CI-CD | The deployment, config mutation, traffic spike, or hardware event that introduced the latent or active fault |
| **`T_onset`** | `cloudwatch.get_metric_data` / `appsignals` | First measurable deviation in customer-facing SLI (5xx rate, P99 latency, queue age) |
| **`T_detect`** | `cloudwatch.get_alarm_history` | Timestamp when the first automated alarm transitioned to `ALARM` (or manual detection occurred) |
| **`T_engage`** | Incident bridge / Pager log | Timestamp when the on-call SRE acknowledged and began triage |
| **`T_mitigate_start`** | `cloudtrail.lookup_events` | Timestamp when rollback, zonal shift, or scale-out command was initiated |
| **`T_recover`** | `cloudwatch.get_metric_data` / `appsignals` | Timestamp when customer-facing SLI returned within SLO bounds |

### Key Derived Metrics (Compute Deterministically)
- **Time to Detect (TTD)** = `T_detect - T_onset` (if `TTD > 5 minutes`, a **Monitoring Gap Action Item** is mandatory).
- **Time to Mitigate (TTM)** = `T_recover - T_detect`.
- **Total Customer Impact Duration (MTTR)** = `T_recover - T_onset`.

---

## 3. Blameless 5-Whys Root Cause Analysis Rules

- **Never stop at human error or a single component failure** ("The engineer deployed a bad config" or "The pod OOM'd").
- Ask **"Why did the system allow this fault to reach production or impact customers?"** until you uncover the **process, architectural, testing, or guardrail gap**:
  1. *Why #1*: Customer checkout requests failed with HTTP 503.
  2. *Why #2*: All ECS tasks in `checkout-service` exited with `OutOfMemoryError (Exit Code 137)`.
  3. *Why #3*: Task definition revision 42 lowered container memory from `1024 MiB` to `256 MiB` while JVM `-Xmx` remained `768m`.
  4. *Why #4*: The CI/CD pipeline lacked a pre-deploy container memory vs. JVM heap validation check and deployed to 100% of tasks simultaneously instead of a canary with CloudWatch alarm rollback.
  5. *Why #5 (Systemic Root Cause)*: ECS deployment circuit breaker and CodeDeploy canary alarms were not enforced in the shared CDK construct library.

---

## 4. Preventive Action Items (P0 / P1 / P2 Governance)

Every COE must conclude with concrete, verifiable action items across three horizons:
- **P0 (Immediate — Within 24–48h)**: Restore redundancy, close detection blind spots (missing CloudWatch/AMP alarms), and revert temporary workarounds.
- **P1 (Short-Term — Within 2 Sprints)**: Add CI/CD guardrails (`cfn-guard`, canary rollbacks, circuit breakers, PodDisruptionBudgets).
- **P2 (Long-Term — Architectural Resilience)**: Chaos engineering validation (`aws-fault-injection-service` game day) and `resilience-hub-failure-mode-assessment`.

---

## Reference Files

- [references/coe-template-and-5whys.md](references/coe-template-and-5whys.md) — Complete copy-ready Amazon COE Markdown template, 5-Whys anti-pattern checklist, and SLA/Error Budget burn calculation formulas
