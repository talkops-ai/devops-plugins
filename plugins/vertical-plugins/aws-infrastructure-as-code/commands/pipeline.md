---
description: Design or fix a CodePipeline/CodeBuild/CodeDeploy CI/CD pipeline
argument-hint: "<repository or pipeline name>"
---

Use the `aws-deployment` skill to design, review, or troubleshoot the CI/CD pipeline for `$ARGUMENTS`.

1. Determine source, build, test, and deploy stages and the deployment strategy (rolling, blue/green, canary).
2. For an existing pipeline, inspect recent executions and the failing action's logs first.
3. Produce the pipeline definition as IaC (CDK or CloudFormation) with least-privilege roles.

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
