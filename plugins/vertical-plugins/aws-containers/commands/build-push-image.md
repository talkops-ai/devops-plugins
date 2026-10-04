---
description: Build a container image with Finch and push it to Amazon ECR
argument-hint: "<Dockerfile path> <ECR repository>"
---

Build and push a container image using the `finch` server.

1. Confirm the Dockerfile, build context, target platform (arm64 for Graviton/Fargate ARM, amd64 otherwise), and tag from `$ARGUMENTS`.
2. Build the image, then push to the ECR repository. If the repository does not exist, explain that creating it needs `--enable-aws-resource-write` on the `finch` server or a separate approved step.
3. Report the pushed image URI and digest; suggest enabling scan-on-push and lifecycle policies.

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
