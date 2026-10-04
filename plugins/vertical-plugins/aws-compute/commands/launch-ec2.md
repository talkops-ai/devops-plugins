---
description: Launch an EC2 instance following AWS best practices
argument-hint: "<purpose, e.g. 'web server in private subnet'>"
---

Plan and launch an EC2 instance for `$ARGUMENTS` with the `launching-ec2-instance-with-best-practices` skill.

1. Gather requirements: workload, architecture (prefer Graviton when compatible), VPC/subnet, access method (SSM Session Manager over SSH), storage, and tags.
2. Apply the skill's defaults: IMDSv2 required, encrypted EBS, least-privilege instance profile, no public IP unless needed.
3. Present the launch template / `run-instances` parameters and estimated cost.

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
