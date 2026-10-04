---
description: Design a production-ready multi-AZ VPC
argument-hint: "<CIDR and environment, e.g. '10.20.0.0/16 prod'>"
---

Design a VPC for `$ARGUMENTS` with the `creating-production-vpc-multi-az` skill.

1. Plan CIDRs and subnets across at least two AZs (public, private-app, private-data), route tables, NAT strategy (per-AZ vs shared), and VPC endpoints.
2. Include flow logs, default security group lockdown, and IPv6 if requested.
3. Produce the design table and the IaC (CDK or CloudFormation), with NAT and endpoint cost notes.

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
