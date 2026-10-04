---
description: Expose a Lambda function through API Gateway
argument-hint: "<function name> [REST|HTTP]"
---

Wire `$ARGUMENTS` to API Gateway.

1. Load `connecting-lambda-to-api-gateway` to choose REST vs HTTP API, integration type, and authorization (IAM, Cognito, Lambda authorizer).
2. Load `creating-api-gateway-stage` for stage variables, logging, throttling, and deployment.
3. Produce SAM/CDK code (or CLI steps), the invoke permission for API Gateway, and a curl test.

Show the exact resources and commands first and wait for explicit approval before creating, modifying, or deleting anything.
