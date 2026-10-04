---
description: Investigate an application error or latency spike
argument-hint: "<service> <time window>"
---

Investigate `$ARGUMENTS` using `troubleshooting-application-failures` and `aws-observability`.

1. Check active alarms (`cloudwatch`) and service health/SLOs (`appsignals`).
2. Correlate metrics, Logs Insights queries (bounded time window), and traces around onset; use `prometheus` for EKS/AMP workloads.
3. Check `cloudtrail` for changes before onset, then return a timeline, root cause with confidence, and a mitigation proposal.

This is a read-only workflow: do not create, modify, or delete resources.
