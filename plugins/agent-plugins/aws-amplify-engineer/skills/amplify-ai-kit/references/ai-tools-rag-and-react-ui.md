# AI Tools, Bedrock Knowledge Base RAG, and React UI Integration

## 1. Three-Tier Tool-Calling Architecture for `a.conversation()`

Amplify AI Kit supports three distinct tool-calling mechanisms on `a.conversation()`:

### Tier 1A: Model Data Tools (`a.ai.dataTool()`) — Zero Lambda Code
Directly expose `get` or `list` operations on any `a.model()` in your schema:

```typescript
tools: [
  a.ai.dataTool({
    name: 'searchOrders',
    description: 'Lists customer orders from the Order table',
    model: a.ref('Order'),
    modelOperation: 'list', // 'list' | 'get'
  }),
]
```

### Tier 1B: Custom Query Tools (`a.ai.dataTool()` with `query`) — Custom Business Logic
Expose a custom `a.query()` backed by a `defineFunction` Lambda handler. The custom query **MUST** allow `allow.authenticated()`:

```typescript
// amplify/data/resource.ts
import { calculateShippingFn } from '../functions/calculate-shipping/resource';

const schema = a.schema({
  calculateShipping: a.query()
    .arguments({ zipCode: a.string().required(), weightKg: a.float().required() })
    .returns(a.customType({ rateUsd: a.float(), estimatedDays: a.integer() }))
    .handler(a.handler.function(calculateShippingFn))
    .authorization((allow) => allow.authenticated()),

  supportAssistant: a.conversation({
    aiModel: a.ai.model('Claude 3.5 Sonnet v2'),
    systemPrompt: 'Help customers estimate shipping costs.',
    tools: [
      a.ai.dataTool({
        name: 'calculateShipping',
        description: 'Calculates shipping rate and delivery time for a ZIP code and weight',
        query: a.ref('calculateShipping'),
      }),
    ],
  }).authorization((allow) => allow.owner()),
});
```

### Tier 2: Custom Conversation Turn Handler (`@aws-amplify/backend-ai`)
When you need full control over the Bedrock Converse loop, custom guardrails, or arbitrary backend orchestration:

```bash
npm install --save-dev @aws-amplify/backend-ai
```

```typescript
// amplify/data/chat-handler/resource.ts
import { defineConversationHandlerFunction } from '@aws-amplify/backend-ai/conversation';

export const customChatHandler = defineConversationHandlerFunction({
  entry: './handler.ts',
  name: 'customChatHandler',
  models: [
    {
      modelId: 'anthropic.claude-3-5-haiku-20241022-v1:0',
      region: 'us-east-1',
    },
  ],
});
```

```typescript
// amplify/data/chat-handler/handler.ts
import {
  ConversationTurnEvent,
  handleConversationTurnEvent,
} from '@aws-amplify/backend-ai/conversation/runtime';

export const handler = async (event: ConversationTurnEvent) => {
  await handleConversationTurnEvent(event, {
    tools: [
      // Custom server-side executable tools with inputSchema and execute()
    ],
  });
};
```

Bind `handler: customChatHandler` on `a.conversation({ aiModel, systemPrompt, handler: customChatHandler })` and register `customChatHandler` in `amplify/backend.ts`.

### Tier 3: Client-Side Tools (`aiContext` & `tools` in React)
Use client tools when the AI assistant needs to read or manipulate browser/UI state:

```tsx
const [
  { data: { messages }, isLoading },
  sendMessage,
] = useAIConversation('catalogAssistant', {
  tools: {
    highlightProductCard: {
      description: 'Highlights a product card in the user interface by product ID',
      inputSchema: {
        json: {
          type: 'object',
          properties: {
            productId: { type: 'string', description: 'The ID of the product to highlight' },
          },
          required: ['productId'],
        },
      },
      execute: async ({ productId }) => {
        highlightDomElement(productId);
        return { content: [{ text: `Highlighted product ${productId}` }] };
      },
    },
  },
});
```

---

## 2. Wiring an Amazon Bedrock Knowledge Base for RAG

To connect an existing Amazon Bedrock Knowledge Base to an `a.conversation()` route without provisioning an extra Lambda function, wire an AppSync HTTP Data Source directly to the Bedrock Agent Runtime `retrieve` endpoint:

### Step 1: Add the Custom Query & Tool in `amplify/data/resource.ts`

```typescript
const schema = a.schema({
  retrieveKnowledge: a.query()
    .arguments({ input: a.string().required() })
    .handler(
      a.handler.custom({
        dataSource: 'KnowledgeBaseDataSource',
        entry: './resolvers/kbResolver.js',
      }),
    )
    .returns(a.string())
    .authorization((allow) => allow.authenticated()),

  docsAssistant: a.conversation({
    aiModel: a.ai.model('Claude 3.5 Sonnet v2'),
    systemPrompt: 'Answer questions strictly using the retrieveKnowledge tool.',
    tools: [
      a.ai.dataTool({
        name: 'retrieveKnowledge',
        description: 'Searches the internal product documentation Knowledge Base',
        query: a.ref('retrieveKnowledge'),
      }),
    ],
  }).authorization((allow) => allow.owner()),
});
```

### Step 2: Write the AppSync JS Resolver (`amplify/data/resolvers/kbResolver.js`)

```javascript
export function request(ctx) {
  return {
    resourcePath: '/knowledgebases/YOUR_KNOWLEDGE_BASE_ID/retrieve',
    method: 'POST',
    params: {
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        retrievalQuery: {
          text: ctx.args.input,
        },
      }),
    },
  };
}

export function response(ctx) {
  return JSON.stringify(ctx.result.body);
}
```

### Step 3: Register the HTTP Data Source & IAM Policy in `amplify/backend.ts`

```typescript
import { defineBackend } from '@aws-amplify/backend';
import { Effect, PolicyStatement } from 'aws-cdk-lib/aws-iam';
import { auth } from './auth/resource';
import { data } from './data/resource';

const backend = defineBackend({ auth, data });

const region = backend.data.stack.region;
const account = backend.data.stack.account;
const knowledgeBaseId = 'YOUR_KNOWLEDGE_BASE_ID';

const kbDataSource = backend.data.addHttpDataSource(
  'KnowledgeBaseDataSource',
  `https://bedrock-agent-runtime.${region}.amazonaws.com`,
  {
    authorizationConfig: {
      signingRegion: region,
      signingServiceName: 'bedrock',
    },
  },
);

kbDataSource.grantPrincipal.addToPrincipalPolicy(
  new PolicyStatement({
    effect: Effect.ALLOW,
    actions: ['bedrock:Retrieve'],
    resources: [
      `arn:aws:bedrock:${region}:${account}:knowledge-base/${knowledgeBaseId}`,
    ],
  }),
);
```

---

## 3. Frontend Integration (`@aws-amplify/ui-react-ai`)

```bash
npm install aws-amplify @aws-amplify/ui-react @aws-amplify/ui-react-ai
```

### Setup Shared Client & AI Hooks (`src/client.ts`)

Instantiate `generateClient<Schema>()` and `createAIHooks(client)` **once at module scope** (never inside a React component render body):

```typescript
// src/client.ts
import { generateClient } from 'aws-amplify/data';
import { createAIHooks } from '@aws-amplify/ui-react-ai';
import type { Schema } from '../amplify/data/resource';

export const client = generateClient<Schema>({ authMode: 'userPool' });
export const { useAIConversation, useAIGeneration } = createAIHooks(client);
```

### Conversation UI Component

```tsx
import '@aws-amplify/ui-react/styles.css';
import { AIConversation } from '@aws-amplify/ui-react-ai';
import { useAIConversation } from './client';

export function SupportChat() {
  const [
    {
      data: { messages },
      isLoading,
    },
    handleSendMessage,
  ] = useAIConversation('catalogAssistant');

  return (
    <AIConversation
      messages={messages}
      isLoading={isLoading}
      handleSendMessage={handleSendMessage}
      aiContext={() => ({
        currentTime: new Date().toISOString(),
      })}
    />
  );
}
```

### Structured Generation Hook

```tsx
import { useAIGeneration } from './client';

export function ProductExtractor() {
  const [{ data, isLoading, hasError }, extractProductSpec] =
    useAIGeneration('extractProductSpec');

  return (
    <div>
      <button
        disabled={isLoading}
        onClick={() =>
          extractProductSpec({ rawDescription: 'Wireless ANC headphones, $299' })
        }
      >
        Extract
      </button>
      {hasError && <p>Generation failed</p>}
      {data && <pre>{JSON.stringify(data, null, 2)}</pre>}
    </div>
  );
}
```

### Low-Level `.onStreamEvent()` Reordering Caveat

When subscribing to `conversation.onStreamEvent()` directly (for example in Vue, Angular, or custom mobile clients) instead of `<AIConversation />`, WebSocket chunks (`ConversationStreamTextEvent`) **are not guaranteed to arrive in sequential order**:

- Group incoming events by `event.contentBlockIndex`.
- Sort text deltas within each block by `event.contentBlockDeltaIndex` before concatenating `event.text`.
- Wait for the turn completion event (`stopReason`) before finalizing the message bubble, and always call `sub.unsubscribe()` on component unmount.
