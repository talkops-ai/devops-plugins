# AI Routes, Model Selection, and Schema Rules

## 1. Model Selection & Cross-Region Inference Profiles

Use `a.ai.model('<Human Readable Name>')` in both `a.conversation()` and `a.generation()`:

- **Anthropic (supported in BOTH `a.conversation` and `a.generation`)**:
  `'Claude 3.5 Haiku'`, `'Claude 3.5 Sonnet'`, `'Claude 3.5 Sonnet v2'`, `'Claude 3.7 Sonnet'`, `'Claude Sonnet 4'`, `'Claude Opus 4'`, `'Claude Haiku 4.5'`, `'Claude Sonnet 4.5'`, `'Claude Opus 4.5'`
- **Amazon Nova (supported in `a.conversation` ONLY)**:
  `'Amazon Nova Pro'`, `'Amazon Nova Lite'`, `'Amazon Nova Micro'`
- **Meta / Cohere / Mistral (supported in `a.conversation` ONLY)**:
  `'Llama 3.1 405B Instruct'`, `'Llama 3.1 70B Instruct'`, `'Llama 3.1 8B Instruct'`, `'Cohere Command R+'`, `'Mistral Large 2'`

### Escape Hatch for Cross-Region Inference Profiles or Newer Model IDs

When using a Bedrock Cross-Region Inference Profile (e.g., `us.anthropic.claude-sonnet-4-20250514-v1:0` or `global.anthropic.claude-sonnet-4-5-20250929-v1:0`) or a model ID not yet mapped in `a.ai.model()`, pass `{ resourcePath }`:

```typescript
aiModel: {
  resourcePath: 'us.anthropic.claude-3-5-haiku-20241022-v1:0',
}
```

> **Important:** When using a Cross-Region Inference Profile (`us.*`, `eu.*`, `apac.*`, `global.*`), ensure the underlying Bedrock foundation model is enabled in the source and destination regions, and if overriding IAM policies on the conversation handler Lambda, permit `bedrock:InvokeModel*` on both the `inference-profile/*` ARN and `foundation-model/*` ARN across the profile's regions.

---

## 2. Complete Schema Blueprint (`amplify/data/resource.ts`)

```typescript
import { type ClientSchema, a, defineData } from '@aws-amplify/backend';

const schema = a.schema({
  // 1. Standard DynamoDB Model (Accessible by AI Conversation via a.ai.dataTool)
  Product: a.model({
    name: a.string().required(),
    category: a.string().required(),
    price: a.float().required(),
    inStock: a.boolean().default(true),
  }).authorization((allow) => [
    allow.authenticated().to(['read']),
    allow.owner(),
  ]),

  // 2. Custom Type for AI Generation
  // RULE A: Must be a.customType(), NEVER a.model()
  // RULE B: Never chain .required() on a.url(), a.email(), a.date(), a.time(),
  //         a.datetime(), a.timestamp(), a.phone(), or a.ipAddress()
  ExtractedCatalogItem: a.customType({
    title: a.string().required(),
    tags: a.string().array(),
    estimatedPrice: a.float().required(),
    supplierUrl: a.url(),       // MUST NOT be .required()
    contactEmail: a.email(),    // MUST NOT be .required()
    releaseDate: a.date(),      // MUST NOT be .required()
  }),

  // 3. Synchronous Structured Data Generation Route
  // RULE C: Must use non-owner authorization (authenticated, guest, group, publicApiKey)
  extractProductSpec: a.generation({
    aiModel: a.ai.model('Claude 3.5 Haiku'),
    systemPrompt:
      'Extract structured product catalog attributes from unstructured vendor descriptions. Never invent placeholder values.',
    inferenceConfiguration: {
      temperature: 0.2,
      maxTokens: 1000,
      topP: 0.9,
    },
  })
    .arguments({ rawDescription: a.string().required() })
    .returns(a.ref('ExtractedCatalogItem'))
    .authorization((allow) => allow.authenticated()),

  // 4. Asynchronous Multi-Turn Streaming Conversation Route
  // RULE D: Must exclusively use allow.owner() authorization
  catalogAssistant: a.conversation({
    aiModel: a.ai.model('Claude 3.5 Haiku'),
    systemPrompt:
      'Assist users with inventory lookup using the provided Product query tool.',
    inferenceConfiguration: {
      temperature: 0.5,
      maxTokens: 2048,
    },
    tools: [
      a.ai.dataTool({
        name: 'listProductsByCategory',
        description: 'Lists available products in the catalog database',
        model: a.ref('Product'),
        modelOperation: 'list',
      }),
    ],
  }).authorization((allow) => allow.owner()),
});

export type Schema = ClientSchema<typeof schema>;

export const data = defineData({
  schema,
  authorizationModes: {
    defaultAuthorizationMode: 'userPool',
  },
});
```

---

## 3. Why the 8 AppSync Scalars Cannot Be `.required()` in `a.generation()`

Under the hood, `a.generation()` compiles the `.returns(...)` type into a Bedrock Converse `toolConfig` JSON Schema to force Claude to emit structured output. AppSync scalar types (`AWSEmail`, `AWSDate`, `AWSTime`, `AWSDateTime`, `AWSTimestamp`, `AWSPhone`, `AWSURL`, `AWSIPAddress`) have strict regex/format validators in AppSync's GraphQL response mapping layer.

- If the LLM does not find an email or URL in the input prompt and the field is marked `.required()`, the LLM emits `"N/A"`, `""`, or `"unknown"` to satisfy the JSON Schema `required` array.
- AppSync then validates `"N/A"` against the `AWSEmail` / `AWSURL` scalar validator and **throws a GraphQL serialization error**, failing the entire generation request.
- Additionally, Amplify's schema compiler rejects `.required()` on those 8 scalar types inside `a.generation()` return types.
- **Fix:** Either leave those 8 scalar fields optional (nullable) so the model can omit them when absent, or use `a.string().required()` if you want raw unvalidated text.
