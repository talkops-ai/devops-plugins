---
description: Check SQS queues and SNS topics for backlog, DLQ, and delivery problems
argument-hint: "[queue or topic name prefix]"
---

Assess messaging health for `$ARGUMENTS` (default: all queues/topics in the region) using the `sns-sqs` server and the `aws-messaging-and-streaming` skill.

1. For queues: depth, age of oldest message, in-flight count, redrive policy and DLQ depth, visibility timeout vs consumer duration, encryption.
2. For topics: subscriptions, delivery failures, filter policies, and DLQs on subscriptions.
3. Report problems by severity with the recommended fix.

This is a read-only workflow: do not create, modify, or delete resources. Do not send, purge, or redrive messages without approval.
