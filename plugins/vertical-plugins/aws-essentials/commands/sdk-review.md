---
description: Review AWS SDK code for correctness and best practices
argument-hint: "<file or directory>"
---

Review the AWS SDK usage in `$ARGUMENTS` (default: the current repository).

1. Detect the language and load the matching skill: `aws-sdk-python-usage` (boto3), `aws-sdk-js-v3-usage`, or `aws-sdk-swift-usage`.
2. Check credential and region resolution, client reuse, pagination, waiters, retries/timeouts, error handling, and streaming/body handling against the skill's rules.
3. Report findings by severity with file:line references and a concrete fix for each; apply edits only if the user asks.
