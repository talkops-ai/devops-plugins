---
description: Build or extend an AWS Amplify Gen 2 app
argument-hint: "<feature, e.g. 'auth + todo data model'>"
---

Use the `aws-amplify` skill to implement `$ARGUMENTS` in an Amplify Gen 2 project.

1. Detect the framework and whether an `amplify/` backend exists (Gen 1 needs explicit migration consent).
2. Define backend resources in TypeScript with explicit authorization rules, then wire the frontend.
3. Verify in a cloud sandbox (`npx ampx sandbox`).

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
