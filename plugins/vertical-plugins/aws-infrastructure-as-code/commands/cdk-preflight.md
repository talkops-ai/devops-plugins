---
description: Synth, lint, and diff a CDK app before deploying
argument-hint: "[stack name]"
---

Run a pre-deployment check on the CDK app in the current repository using the `aws-cdk` skill.

1. Confirm the CDK version, language, and bootstrap status of the target account/region.
2. Run `cdk synth`, validate the synthesized templates with the `awsiac` server, and run `cdk diff` for `$ARGUMENTS` (or all stacks).
3. Summarize additions, replacements, and deletions, flagging stateful resources (databases, buckets, queues) that would be replaced or removed.

Do not run `cdk deploy`. Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
