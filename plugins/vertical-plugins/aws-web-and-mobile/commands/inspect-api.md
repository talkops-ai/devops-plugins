---
description: Inspect an AWS AppSync API's schema, data sources, and resolvers
argument-hint: "<API ID or name>"
---

Inspect AppSync API `$ARGUMENTS` with the read-only `appsync` server.

1. List the schema types, data sources, resolvers/functions, auth modes, and caching.
2. Flag issues: missing authorization, unbounded list resolvers, and data sources with broad IAM roles.
3. If the API is Amplify-managed, recommend changes in `amplify/data/resource.ts` rather than direct edits.

This is a read-only workflow: do not create, modify, or delete resources.
