---
name: amplify-functions-cdk
description: >-
  Builds AWS Lambda functions (defineFunction), resolves CloudFormation nested-stack circular
  dependencies (resourceGroupName), configures typed environment variables ($amplify/env/*) and
  SSM secrets (secret()), calls Amplify Data GraphQL APIs from Lambda handlers
  (getAmplifyDataClientConfig), authors custom CDK stacks (backend.createStack) and L1/L2
  cfnResources overrides, and runs cfn-lint/cfn-guard compliance checks on synthesized templates.
  Use whenever working with Amplify Gen 2 functions, schedules, custom REST/HTTP APIs, CDK
  escape hatches, or circular dependency errors.
---

# Amplify Functions, CDK Overrides, and Stack Architecture

Use this skill whenever adding or debugging serverless compute (`amplify/functions/<name>/resource.ts`), granting cross-resource access between Functions, Auth, Data, and Storage, authoring CDK escape hatches in `amplify/backend.ts`, or resolving CloudFormation circular dependency errors.

## Five Non-Negotiable Guardrails

1. **`runtime` MUST Be an Integer:**
   - In `defineFunction({ runtime: 22 })`, always pass an integer (`18`, `20`, `22`, `24`), **NEVER** a string like `'nodejs22.x'`.
2. **Use Strongly Typed `$amplify/env/<function-name>`:**
   - Import `import { env } from '$amplify/env/<function-name>'` inside `handler.ts` rather than untyped `process.env`. Amplify generates `.amplify/generated/env/<function-name>.ts` automatically during `npx ampx sandbox` or `npx ampx pipeline-deploy`.
   - Store sensitive credentials with `secret('MY_SECRET')` in `defineFunction({ environment: { API_KEY: secret('MY_SECRET') } })`—never hardcode secrets or pass them as plain string environment variables.
3. **Break Nested-Stack Circular Dependencies with `resourceGroupName`:**
   - When a Lambda function is registered as a trigger in `defineAuth` (`amplify/auth/resource.ts`) or `defineStorage` (`amplify/storage/resource.ts`) **AND** is also granted access to `defineData` (`allow.resource(fn)`) or another category, CloudFormation fails with a circular dependency between the `auth`, `data`, `storage`, and `function` nested stacks.
   - Fix this at the source by co-locating the function into the owning stack via `resourceGroupName`:
     - Auth trigger function: `defineFunction({ name: 'post-confirmation', resourceGroupName: 'auth' })`
     - Data resolver/mutation function: `defineFunction({ name: 'order-processor', resourceGroupName: 'data' })`
     - Storage trigger function: `defineFunction({ name: 'image-resizer', resourceGroupName: 'storage' })`
4. **Declarative Resource Grants Over Manual `addEnvironment`:**
   - Grant functions access to Data models via `.authorization((allow) => [allow.resource(myFunc)])` in `amplify/data/resource.ts`, to Auth via `access: (allow) => [allow.resource(myFunc).to([...])]` in `amplify/auth/resource.ts`, and to Storage via `access: (allow) => ({ 'path/*': [allow.resource(myFunc).to(['read', 'write'])] })` in `amplify/storage/resource.ts`.
   - Avoid manually wiring `backend.myFunc.resources.lambda.addEnvironment('USER_POOL_ID', backend.auth.resources.userPool.userPoolId)` in `amplify/backend.ts` when declarative `access` grants exist, as manual cross-stack token references trigger CDK circular dependency errors.
5. **Pre-Deploy CloudFormation Validation (`awsiac` MCP):**
   - Before deploying custom CDK stacks (`backend.createStack()`) or L1 `cfnResources` overrides to production, validate synthesized templates under `.amplify/artifacts/cdk.out/*.template.json` using the `awsiac` MCP tools `validate_cloudformation_template` (`cfn-lint`) and `check_cloudformation_template_compliance` (`cfn-guard`).

---

## Workflow & Reference Routing

| Task | Reference to Load |
|---|---|
| Define Lambda functions (`defineFunction`), typed `$amplify/env/*`, `secret()`, scheduled cron jobs, calling the Amplify Data GraphQL API from inside a Lambda handler (`getAmplifyDataClientConfig`), or fixing CDK circular dependencies (`resourceGroupName`) | [`references/circular-dependencies-and-runtime-data.md`](references/circular-dependencies-and-runtime-data.md) |
| Author custom CDK stacks (`backend.createStack()`), L1 `cfnResources` overrides (Cognito, DynamoDB, S3, AppSync), API Gateway REST/HTTP APIs, or run `awsiac` template compliance checks | [`references/cdk-escape-hatches-and-compliance.md`](references/cdk-escape-hatches-and-compliance.md) |
