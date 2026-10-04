---
description: Summarize AWS spend and what drives it
argument-hint: "[time range, e.g. 'last 3 months']"
---

Produce a cost report for `$ARGUMENTS` (default: last full month vs the month before) with the `aws-billing-and-cost-management` skill and the `billing` server.

1. Break down spend by service, account, region, and usage type; highlight the largest month-over-month changes.
2. Include anomalies detected by Cost Anomaly Detection and budget status.
3. Return a short narrative plus tables; note data latency (Cost Explorer lags up to 24 hours).

This is a read-only workflow: do not create, modify, or delete resources.
