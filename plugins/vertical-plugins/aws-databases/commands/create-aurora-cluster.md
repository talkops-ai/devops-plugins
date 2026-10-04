---
description: Create an Aurora PostgreSQL or MySQL cluster with best practices
argument-hint: "<engine> <environment>"
---

Plan an Aurora cluster for `$ARGUMENTS` with `creating-amazon-aurora-db-cluster-with-instances`.

1. Choose engine/version, instance class or Serverless v2 capacity, writer/reader layout across AZs, subnet group, and parameter groups.
2. Apply defaults: encryption with KMS, IAM authentication, managed master password in Secrets Manager, deletion protection, backups, Performance Insights.
3. Produce the IaC or CLI plan with estimated cost.

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
