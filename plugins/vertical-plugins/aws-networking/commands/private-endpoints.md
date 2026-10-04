---
description: Reach AWS services privately through VPC endpoints
argument-hint: "<VPC ID> <services, e.g. 's3 ecr secretsmanager'>"
---

Use `configuring-vpc-endpoints-for-private-aws-service-access` to add VPC endpoints for `$ARGUMENTS`.

1. Choose gateway endpoints (S3, DynamoDB) vs interface endpoints, the subnets/AZs, private DNS, and endpoint security groups.
2. Draft endpoint policies that restrict access to the account's resources.
3. Estimate interface-endpoint cost vs NAT data processing and produce the IaC.

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
