---
name: amplify-workflow
description: >-
  Master 4-phase orchestrator (Backend -> Sandbox -> Frontend -> Production) to build and deploy
  full-stack web and mobile apps with AWS Amplify Gen 2 (TypeScript code-first). Coordinates
  auth (Cognito), data (AppSync/DynamoDB), storage (S3), functions/CDK, and Amplify AI Kit across
  React, Next.js, Vue, Angular, React Native, Flutter, Swift, and Android, routing deep domain
  work to specialized skills. Always load this skill first for any Amplify Gen 2 task.
---

# AWS Amplify Gen 2 — Master 4-Phase Orchestrator

Build and deploy full-stack applications using AWS Amplify Gen 2's TypeScript code-first paradigm. This skill governs the 4-phase lifecycle state machine, platform/framework detection across 8 web and mobile frameworks, and routing to specialized domain skills.

## Four-Phase Execution Lifecycle & Checkpoints

Evaluate the developer's request and current workspace state (`amplify/backend.ts`, `amplify_outputs.json`, `package.json`) to schedule only the applicable phases, pausing for explicit confirmation before provisioning cloud resources:

1. **Phase 1 — Backend Definition (`amplify/`):**
   - Author TypeScript resource definitions in `amplify/auth/resource.ts` (`defineAuth`), `amplify/data/resource.ts` (`defineData`), `amplify/storage/resource.ts` (`defineStorage`), and `amplify/functions/<name>/resource.ts` (`defineFunction`).
   - Register every resource inside `amplify/backend.ts` via `defineBackend({ auth, data, storage, ... })`.
2. **Phase 2 — Cloud Sandbox & Output Generation (`npx ampx sandbox --once`):**
   - Verify AWS credentials (`aws sts get-caller-identity`; invoke `signing-in-to-aws` if expired).
   - Run `npx ampx sandbox --once` (with confirmation) to deploy personal cloud sandbox stacks and generate `amplify_outputs.json` (or Dart outputs for Flutter).
   - If custom CDK stacks or `cfnResources` overrides were added, validate `.amplify/artifacts/cdk.out/*.template.json` via the `awsiac` MCP server (`validate_cloudformation_template` and `check_cloudformation_template_compliance`).
3. **Phase 3 — Frontend Integration & End-to-End Verification:**
   - Configure `Amplify.configure(outputs)` in the exact framework entry point (`core-web.md` or `core-mobile.md`).
   - Wire typed clients (`generateClient<Schema>()` at module scope, `<Authenticator>`, `<StorageBrowser>`, `createAIHooks(client)` / `<AIConversation />`).
4. **Phase 4 — Production Hosting & Branch CI/CD (`amplify.yml`):**
   - Only after explicit user approval, configure `amplify.yml` (`npx ampx pipeline-deploy --branch $AWS_BRANCH --app-id $AWS_APP_ID`), attach the `AmplifyBackendDeployFullAccess` IAM service role, configure branch secrets (`npx ampx secret set`), and deploy via AWS Amplify Hosting.

---

## Specialized Domain Skill Routing

Alongside the reference files in this skill, invoke these specialized skills for deep domain implementation:

| Domain | Specialized Skill | When to Invoke |
|---|---|---|
| **Cognito Auth** | `amplify-auth-cognito` | `defineAuth`, MFA, WebAuthn Passkeys, OAuth/OIDC with `secret()`, Enterprise SAML 2.0 CDK setup, RBAC groups, Cognito triggers, `allow.resource(fn)` Admin API grants, `referenceAuth` |
| **AppSync & DynamoDB** | `amplify-data-appsync` | `defineData`, `a.schema()`, bidirectional relationships (`a.id()` FKs), composite `.identifier()`, `.secondaryIndexes()`, 6 authorization rules, custom resolvers, RDS PostgreSQL/MySQL (`schema-from-database`) |
| **S3 Storage** | `amplify-storage-s3` | `defineStorage`, the 4 S3 path compiler rules (`/*`, `{entity_id}` collision rules), `allow.guest`/`allow.authenticated` property syntax, multi-bucket `isDefault: true`, `onUpload`/`onDelete` triggers |
| **Lambda & CDK** | `amplify-functions-cdk` | `defineFunction`, typed `$amplify/env/*`, `secret()`, calling Data API from Lambda (`getAmplifyDataClientConfig`), breaking circular dependencies (`resourceGroupName`), `backend.createStack()`, `cfnResources` overrides |
| **Amplify AI Kit** | `amplify-ai-kit` | `a.conversation()` (`allow.owner()` only) vs `a.generation()` (non-owner auth only, `a.customType()` returns, 8 forbidden `.required()` scalars), `a.ai.dataTool()`, `@aws-amplify/backend-ai`, Bedrock Knowledge Base RAG, `@aws-amplify/ui-react-ai` |
| **Hosting & CI/CD** | `amplify-hosting-cicd` | `npx ampx sandbox --once`, production `amplify.yml` (`baseDirectory` per framework), monorepos (`appRoot`, `npx ampx generate outputs`), branch secrets, custom domains, security headers, Gen 1 migration |
| **Composable Blocks** | `aws-blocks` | Adding `@aws-blocks/*` Infrastructure-from-Code building blocks alongside `amplify/backend.ts` |
| **AWS Auth / STS** | `signing-in-to-aws` | Resolving expired AWS CLI/SSO credentials when `aws sts get-caller-identity` fails |

---

## Prerequisites & Defaults

- **Node.js:** `^18.19.0 || ^20.6.0 || >=22` and `npm`
- **AWS Credentials:** `aws sts get-caller-identity` succeeds
- **Framework Defaults (when unspecified):**
  - **Web:** Default to **React (Vite)** and explain the choice.
  - **Mobile:** Always ask which platform the user wants (**Flutter**, **Swift**, **Android**, or **React Native**).
  - **React Native:** Ask whether the project uses **Expo** or **Bare React Native CLI**.
  - **Next.js:** Default to **App Router** (`ConfigureAmplifyClientSide` with `{ ssr: true }` + `generateServerClientUsingCookies`).
  - **Auth:** Ask which login mechanism the user wants (email, social OAuth, passkeys, SAML/OIDC) rather than guessing.
  - **Data Authorization:** Default to `allow.owner()` with `defaultAuthorizationMode: 'userPool'` when Auth is present; use `allow.publicApiKey()` only for unauthenticated starter prototypes.

---

## Quick Start — Route to the Right Reference

### Step 0: Read Core Reference (ALWAYS)

Read the core reference for your target platform **before** reading feature references:

- **Web** (React, Next.js, Vue, Angular, React Native): [core-web.md](references/core-web.md)
- **Mobile** (Flutter, Swift, Android): [core-mobile.md](references/core-mobile.md)
- **Backend only** (no frontend work): Skip to Step 1.

### Step 1: Identify the Task Type

| Task | Go To |
|---|---|
| **Create a new project** | → [scaffolding.md](references/scaffolding.md), then Step 2 and/or Step 3 |
| **Add or modify a backend feature** | → Step 2 (Backend Features) + matching specialized skill |
| **Connect frontend to existing backend** | → Step 3 (Frontend Integration) |
| **Deploy the application** | → [deployment.md](references/deployment.md) + `amplify-hosting-cicd` |

### Step 2: Backend Features

| Feature | Reference | Specialized Skill |
|---|---|---|
| Authentication | [auth-backend.md](references/auth-backend.md) | `amplify-auth-cognito` |
| Data Models | [data-backend.md](references/data-backend.md) | `amplify-data-appsync` |
| File Storage | [storage-backend.md](references/storage-backend.md) | `amplify-storage-s3` |
| Functions & API | [functions-and-api.md](references/functions-and-api.md) | `amplify-functions-cdk` |
| AI Features | [ai.md](references/ai.md) | `amplify-ai-kit` |
| Geo, PubSub, CDK | [advanced-features.md](references/advanced-features.md) | `amplify-functions-cdk` |

### Step 3: Frontend Integration

**Web** (React, Next.js, Vue, Angular, React Native):
- Auth UI & flows: [auth-web.md](references/auth-web.md)
- Data CRUD & subscriptions: [data-web.md](references/data-web.md)
- Storage upload/download: [storage-web.md](references/storage-web.md)

**Mobile** (Flutter, Swift, Android):
- Auth UI & flows: [auth-mobile.md](references/auth-mobile.md)
- Data CRUD & subscriptions: [data-mobile.md](references/data-mobile.md)
- Storage upload/download: [storage-mobile.md](references/storage-mobile.md)

---

## Core Architecture & Security Summary

```text
project-root/
├── amplify/
│   ├── backend.ts            # defineBackend({ auth, data, storage, ... })
│   ├── auth/resource.ts      # defineAuth({ ... })
│   ├── data/resource.ts      # defineData({ schema }) + export type Schema
│   ├── storage/resource.ts   # defineStorage({ ... })
│   └── functions/
│       └── my-func/
│           ├── resource.ts   # defineFunction({ ... })
│           └── handler.ts    # import { env } from '$amplify/env/my-func'
├── src/                      # Frontend code
├── amplify_outputs.json      # Generated — DO NOT edit or commit (gitignored)
└── package.json
```

- **Secrets:** Always use `secret()` for credentials and API keys (`npx ampx sandbox secret set` for sandbox; `npx ampx secret set --branch` for hosting).
- **Least Privilege:** Scope function access via `allow.resource(fn)` rather than wildcard IAM `Resource: ['*']`. Review `allow.guest()` carefully since Cognito Identity Pools enable unauthenticated identities by default unless disabled via `cfnIdentityPool.allowUnauthenticatedIdentities = false`.
