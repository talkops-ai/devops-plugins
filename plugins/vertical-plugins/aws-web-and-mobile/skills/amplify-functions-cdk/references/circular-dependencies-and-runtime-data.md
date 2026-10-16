# Functions, Runtime Data Client (`getAmplifyDataClientConfig`), and Circular Dependency Fixes

## 1. Defining a Function (`amplify/functions/<name>/resource.ts`)

```typescript
import { defineFunction, secret } from '@aws-amplify/backend';

export const orderProcessor = defineFunction({
  name: 'order-processor',
  entry: './handler.ts',
  runtime: 22,               // MUST be integer (18, 20, 22, 24)
  timeoutSeconds: 60,        // 1 to 900 (default: 3)
  memoryMB: 512,             // default: 512
  architecture: 'arm64',     // 'x86_64' | 'arm64'
  resourceGroupName: 'data', // Co-locates in the 'data' nested stack to prevent circular deps
  environment: {
    STAGE_LABEL: 'production',
    STRIPE_WEBHOOK_SECRET: secret('STRIPE_WEBHOOK_SECRET'),
  },
});
```

### Scheduled (Cron / Rate) Functions

```typescript
export const hourlyCleanup = defineFunction({
  name: 'hourly-cleanup',
  entry: './handler.ts',
  schedule: 'every 1h', // or cron: '0 * * * ? *' or array of schedules
});
```

Handler signature for scheduled functions:

```typescript
import type { EventBridgeHandler } from 'aws-lambda';
import { env } from '$amplify/env/hourly-cleanup';

export const handler: EventBridgeHandler<'Scheduled Event', void, void> = async (event) => {
  console.log('Triggered at', event.time);
};
```

---

## 2. Calling the Amplify Data API from a Lambda Handler (`getAmplifyDataClientConfig`)

When a Lambda function (such as a `postConfirmation` Cognito trigger, a scheduled job, or an S3 `onUpload` trigger) needs to create, update, or query records in your Amplify Data GraphQL API:

### Step 1: Grant `allow.resource(fn)` in `amplify/data/resource.ts`

```typescript
import { type ClientSchema, a, defineData } from '@aws-amplify/backend';
import { postConfirmation } from '../auth/post-confirmation/resource';

const schema = a.schema({
  UserProfile: a.model({
    userId: a.string().required(),
    email: a.string().required(),
    plan: a.string().default('free'),
  }).authorization((allow) => [
    allow.ownerDefinedIn('userId'),
    allow.resource(postConfirmation).to(['create', 'read', 'update']),
  ]),
}).authorization((allow) => [allow.resource(postConfirmation)]);

export type Schema = ClientSchema<typeof schema>;
export const data = defineData({ schema });
```

### Step 2: Configure Amplify Inside the Lambda Handler with `getAmplifyDataClientConfig`

Amplify automatically injects the GraphQL endpoint and IAM signing credentials into `$amplify/env/<function-name>`. Configure `Amplify` at module scope using `getAmplifyDataClientConfig(env)` from `@aws-amplify/backend/function/runtime`:

```typescript
// amplify/auth/post-confirmation/handler.ts
import type { PostConfirmationTriggerHandler } from 'aws-lambda';
import { Amplify } from 'aws-amplify';
import { generateClient } from 'aws-amplify/data';
import { getAmplifyDataClientConfig } from '@aws-amplify/backend/function/runtime';
import { env } from '$amplify/env/post-confirmation';
import type { Schema } from '../../data/resource';

const { resourceConfig, libraryOptions } = await getAmplifyDataClientConfig(env);
Amplify.configure(resourceConfig, libraryOptions);

const client = generateClient<Schema>();

export const handler: PostConfirmationTriggerHandler = async (event) => {
  await client.models.UserProfile.create({
    userId: event.request.userAttributes.sub,
    email: event.request.userAttributes.email,
    plan: 'free',
  });
  return event;
};
```

> **Note:** Ensure `aws-amplify` is installed in the project root `dependencies` so esbuild bundles it cleanly into the function artifact.

---

## 3. Resolving CloudFormation Circular Dependencies (`resourceGroupName`)

### Why the Circular Dependency Happens

By default, every `defineFunction()` is placed in its own `function` nested stack (`functionNestedStack`).
When:
1. `auth` nested stack references `postConfirmation` Lambda ARN to attach the Cognito trigger (`auth -> function`), **and**
2. `data` nested stack grants `postConfirmation` IAM permissions to call AppSync, or `postConfirmation` receives environment variables referencing `auth` or `data` (`function -> auth` or `function -> data`),

CloudFormation rejects synthesis or deployment with:
`Circular dependency between resources: [auth..., data..., function...]`.

### Definitive Resolution Matrix

Assign `resourceGroupName` in `defineFunction({...})` so the Lambda construct is synthesized directly inside the stack that triggers or owns it:

| Scenario | Where Function Is Triggered | What Function Accesses | Required `resourceGroupName` |
|---|---|---|---|
| Cognito trigger (`postConfirmation`, `preSignUp`) calling Cognito Admin APIs or Data API | `amplify/auth/resource.ts` | Auth and/or Data | `resourceGroupName: 'auth'` |
| AppSync custom query/mutation handler (`a.handler.function(fn)`) | `amplify/data/resource.ts` | Data / DynamoDB / external APIs | `resourceGroupName: 'data'` |
| S3 trigger (`onUpload`, `onDelete`) mutating S3 or Data API | `amplify/storage/resource.ts` | Storage and/or Data | `resourceGroupName: 'storage'` |
| Custom EventBridge / API Gateway function in custom stack | `amplify/backend.ts` | Custom stack resources | `resourceGroupName: '<customStackName>'` |
