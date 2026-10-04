---
description: Create or fix an EC2 instance profile and role
argument-hint: "<instance ID or workload>"
---

Use `setting-up-ec2-instance-profiles` to give `$ARGUMENTS` the AWS permissions it needs without long-lived keys.

1. Identify the AWS APIs the workload calls and any existing role/profile attached.
2. Draft a least-privilege role with the EC2 trust policy, attach `AmazonSSMManagedInstanceCore` only if SSM is required, and wrap it in an instance profile.
3. Explain how to attach or replace the profile on a running instance and how to verify it from the instance.

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
