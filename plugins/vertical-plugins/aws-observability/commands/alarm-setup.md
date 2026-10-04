---
description: Create CloudWatch alarms with notifications for a service
argument-hint: "<service or resource>"
---

Set up alarms for `$ARGUMENTS` using `setting-up-cloudwatch-alarm-notifications`.

1. Pick the key signals for the resource type (errors, latency percentiles, saturation, throttles) and thresholds or anomaly detection.
2. Wire notifications through SNS (email/chat) with composite alarms to reduce noise.
3. Produce the alarm definitions as IaC and a test plan.

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
