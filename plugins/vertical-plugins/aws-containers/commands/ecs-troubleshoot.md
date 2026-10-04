---
description: Diagnose failing ECS services, tasks, or deployments
argument-hint: "<cluster> [service]"
---

Troubleshoot ECS for `$ARGUMENTS` using the `aws-containers` skill and the `ecs` server (write mode off).

1. Inspect service events, deployment state, and the stopped-task reasons for the most recent failures.
2. Check task definition (image, CPU/memory, secrets, log configuration), load balancer health checks, and networking (subnets, security groups, NAT/endpoints for image pulls).
3. Return the root cause with evidence and the configuration change that fixes it.

This is a read-only workflow: do not create, modify, or delete resources.
