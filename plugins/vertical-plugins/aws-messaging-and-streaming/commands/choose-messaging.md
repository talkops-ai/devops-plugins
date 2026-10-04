---
description: Choose between SQS, SNS, EventBridge, Kinesis, MSK, and Amazon MQ
argument-hint: "<integration description>"
---

Recommend a messaging or streaming service for `$ARGUMENTS` with the `aws-messaging-and-streaming` skill.

1. Clarify delivery semantics, ordering, fan-out, replay/retention, throughput, latency, and protocol compatibility needs.
2. Compare the best two options with cost and operational trade-offs; for customer messaging (email/SMS/WhatsApp), route to the bundled channel skill instead.
3. Give the recommended design with default settings (DLQs, retention, encryption).

This is a read-only workflow: do not create, modify, or delete resources.
