---
description: Find out why a Lambda function times out
argument-hint: "<function name> [region]"
---

Diagnose timeouts for `$ARGUMENTS` with the `debugging-lambda-timeouts` skill.

1. Pull recent duration/timeout metrics and the log lines around `Task timed out` events (CloudWatch Logs via `aws-mcp` or the `aws-serverless-mcp` server).
2. Check downstream calls, VPC egress (NAT/endpoints), cold starts, memory/CPU sizing, and SDK retry/timeout settings.
3. Return root cause with evidence and the specific fix (code, configuration, or networking).

This is a read-only workflow: do not create, modify, or delete resources.
