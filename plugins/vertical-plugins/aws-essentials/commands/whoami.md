---
description: Show which AWS account, principal, and region are active
---

Report the active AWS identity and context.

1. Run `aws sts get-caller-identity` and `aws configure list` (or the `aws-mcp` equivalent).
2. Report account ID, principal ARN (role/user, session name), profile source, and effective region (`AWS_REGION` / profile / default `us-east-1`).
3. If the call fails, explain why and suggest `/aws-essentials:signin`.

This is a read-only workflow: do not create, modify, or delete resources. Never print credential values.
