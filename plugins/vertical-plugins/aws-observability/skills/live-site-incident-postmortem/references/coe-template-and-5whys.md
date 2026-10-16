# Amazon Correction of Errors (COE) Postmortem Template & 5-Whys Guide

Copy and populate this Markdown template when generating a formal incident postmortem or COE report.

---

```markdown
# Correction of Errors (COE): [INCIDENT-ID] — [Concise Incident Title]

- **Date of Incident**: YYYY-MM-DD
- **Severity**: Sev-1 / Sev-2
- **Impacted Services / Accounts / Regions**: `<service-name>` (`<account-id>`, `<region>`)
- **Incident Commander / Authors**: `<names>`
- **Status**: Draft / Reviewed / Action Items Tracked

---

## 1. Executive Summary
*[2–4 sentences summarizing what happened, customer/business impact, root cause, and how it was mitigated. Include exact UTC start/end times and total duration.]*

---

## 2. Customer & Business ImpactQuantification
| Metric | Value | Source |
|---|---|---|
| **Impact Start (`T_onset`)** | `YYYY-MM-DD HH:MM:SS UTC` | CloudWatch Metric / Application Signals |
| **Impact End (`T_recover`)** | `YYYY-MM-DD HH:MM:SS UTC` | CloudWatch Metric / Application Signals |
| **Total Impact Duration (MTTR)** | `XX minutes` | `T_recover - T_onset` |
| **Time to Detect (TTD)** | `XX minutes` | `T_detect - T_onset` |
| **Time to Mitigate (TTM)** | `XX minutes` | `T_recover - T_detect` |
| **Peak Error Rate / Failed Requests** | `XX.X%` (`N` failed requests) | ALB / API GW / Application Signals |
| **30-Day SLO Error Budget Consumed** | `XX.X%` of monthly budget | Application Signals / AMP |

---

## 3. Detection & Response Evaluation
- **How was the incident detected?** *[Automated CloudWatch/AMP SLO alarm vs. customer report vs. synthetic canary]*
- **Was TTD <= 5 minutes?** *[If No, explain the telemetry blind spot or alarm threshold misconfiguration]*
- **Did automated mitigation (circuit breaker, auto-rollback, zonal autoshift) trigger?** *[Yes/No and why]*

---

## 4. Chronological UTC Timeline
| Timestamp (UTC) | Event / Observation / Action | Evidence Source (Alarm / Trace / CloudTrail Event ID) |
|---|---|---|
| `HH:MM:SS` | **`T_trigger`**: Deployment / config change / traffic event occurred | CloudTrail Event `...` |
| `HH:MM:SS` | **`T_onset`**: Error rate / latency crossed SLO threshold | CloudWatch `HTTPCode_ELB_5XX_Count` |
| `HH:MM:SS` | **`T_detect`**: Alarm `<alarm-name>` transitioned to `ALARM` | CloudWatch Alarm History |
| `HH:MM:SS` | **`T_engage`**: On-call SRE began investigation | Incident Bridge |
| `HH:MM:SS` | **`T_mitigate_start`**: Rollback / Zonal Shift initiated | CloudTrail / CLI |
| `HH:MM:SS` | **`T_recover`**: SLI returned to baseline; alarm transitioned to `OK` | Application Signals |

---

## 5. Blameless 5-Whys Root Cause Analysis
1. **Why did customers experience `<symptom>`?**
   - Because `<proximate technical failure>`.
2. **Why did `<proximate technical failure>` occur?**
   - Because `<component/resource saturation or misconfiguration>`.
3. **Why did `<component/resource saturation or misconfiguration>` happen at `T_trigger`?**
   - Because `<change or environmental trigger>`.
4. **Why wasn't this caught before production impact (or isolated to a single canary/AZ)?**
   - Because `<missing pre-flight validation, test gap, or deployment guardrail>`.
5. **Why did our engineering system lack that guardrail?**
   - Because `<systemic architectural or IaC standard gap>`.

### Contributing Factors & Lessons Learned
- **What went well**: *[e.g., ARC Zonal Shift drained traffic in 45 seconds; structured logs isolated the failing dependency]*
- **What went poorly**: *[e.g., Missing alarm on RDS `DatabaseConnections`; retry storm amplified load 4x]*
- **Where we got lucky**: *[e.g., Incident occurred during off-peak traffic window]*

---

## 6. Preventive Action Items
| Priority | Category | Action Item Description | Owner | Due Date | Verification / Chaos Test |
|---|---|---|---|---|---|
| **P0** | Detection | Add CloudWatch/AMP multi-window burn-rate alarm on `<metric>` | `<team>` | `YYYY-MM-DD` | Trigger synthetic fault in staging |
| **P1** | Prevention | Enforce `cfn-guard` / deployment circuit breaker in IaC | `<team>` | `YYYY-MM-DD` | CI pipeline policy check |
| **P2** | Resilience | Validate fix with AWS Fault Injection Service (FIS) experiment | `<team>` | `YYYY-MM-DD` | FIS experiment report |
```
