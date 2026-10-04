---
description: Diagnose a failed or stuck CloudFormation stack
argument-hint: "<stack name> [region]"
---

Find the root cause of the CloudFormation failure for stack `$ARGUMENTS`.

1. Load `aws-cloudformation`. Pull stack status and the first failing events (`describe-stack-events`), not just the final rollback.
2. Use the `awsiac` deployment-troubleshooting tools and CloudTrail evidence to explain the underlying API error.
3. Return: root cause, evidence, the fix (template or parameter change), and how to recover (continue-update-rollback, retain resources, re-deploy).

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
