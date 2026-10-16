---
description: Execute post-deployment synthetic smoke tests, CloudWatch Synthetics canaries, API Gateway test invocations, and bake-window SLO verification
argument-hint: "[<stack-name, service, or canary-name>]"
---

Invoke the **executing-synthetic-release-tests** skill to verify target group and compute health, run CloudWatch Synthetics canaries and API Gateway smoke tests, monitor CloudWatch Golden Signals (`5XX`, latency, throttles) across the bake window, and trigger gated rollback if SLOs breach.

Deployment target: $ARGUMENTS
