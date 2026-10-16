---
name: amplify-ai-kit
description: >-
  Architects and implements AWS Amplify AI Kit features in Amplify Gen 2 (TypeScript code-first)
  backed by Amazon Bedrock, AWS AppSync, Amazon DynamoDB, and AWS Lambda. Covers multi-turn
  streaming conversation routes (a.conversation()), stateless structured generation routes
  (a.generation()), asymmetric authorization rules, strict return-type scalar constraints,
  three-tier tool calling (a.ai.dataTool, custom queries, @aws-amplify/backend-ai custom handlers,
  client tools), Amazon Bedrock Knowledge Base RAG HTTP resolvers, and @aws-amplify/ui-react-ai
  hooks and components. Use whenever adding AI chat, structured output generation, AI tools, or
  RAG to an Amplify Gen 2 app.
---

# Amplify AI Kit (`a.conversation()` & `a.generation()`)

Use this skill whenever designing, implementing, or debugging AI capabilities in an AWS Amplify Gen 2 application (`amplify/data/resource.ts` and `@aws-amplify/ui-react-ai`). Foundation models routinely hallucinate Amplify AI Kit schema rules—follow the invariants in this skill and its references strictly.

## Architectural Decision Matrix: `a.conversation()` vs. `a.generation()`

Both AI route types are defined directly inside `a.schema({...})` in `amplify/data/resource.ts`, but they provision completely different AWS infrastructure and enforce **opposite authorization rules**:

| Dimension | Conversation Route (`a.conversation()`) | Generation Route (`a.generation()`) |
|---|---|---|
| **Execution Pattern** | Asynchronous, multi-turn, real-time WebSocket streaming | Synchronous, single-turn request-response AppSync Query |
| **State & Persistence** | Automatically provisions `Conversation` and `ConversationMessage` DynamoDB tables and sends message history to Bedrock on each turn | Stateless request-response; no DynamoDB conversation tables provisioned |
| **AWS Infrastructure** | AWS AppSync + Amazon DynamoDB + AWS Lambda (turn handler) + Amazon Bedrock | AWS AppSync (direct HTTP resolver to Bedrock Converse API) + Amazon Bedrock |
| **Supported Models** | Any supported Bedrock model (Anthropic Claude, Amazon Nova, Meta Llama, Cohere, Mistral) or `{ resourcePath }` | **Anthropic Claude models ONLY** (requires structured output tool-use support) |
| **Mandatory Authorization** | **ONLY `allow.owner()`** (`.authorization((allow) => allow.owner())`). Non-owner auth throws a `TypeError` at CDK synthesis. | **ONLY non-owner auth** (`allow.authenticated()`, `allow.guest()`, `allow.group()`, `allow.publicApiKey()`). `allow.owner()` throws a `TypeError` at CDK synthesis. |
| **Return Type** | Streams `ConversationStreamEvent` chunks over AppSync subscriptions (`.onStreamEvent()`) | Structured output via `.returns(...)`. **MUST** use scalars or `a.customType()`, **NEVER** `a.model()`. |
| **Tool Calling** | Supports `a.ai.dataTool()`, custom `a.query()` tools, custom `@aws-amplify/backend-ai` Lambda handlers, and client-side tools | No tool calling (single-turn structured extraction/generation only) |
| **Frontend Client & React UI** | `client.conversations.<name>.create()`, `.sendMessage()`, `.onStreamEvent()`; `useAIConversation` & `<AIConversation />` | `client.generations.<name>({...})`; `useAIGeneration` from `createAIHooks(client)` |

---

## Four Non-Negotiable Engineering Guardrails

1. **Asymmetric Authorization Rule (Synthesis Blocker):**
   - `a.conversation()` **MUST** use `.authorization((allow) => allow.owner())`.
   - `a.generation()` **MUST** use `.authorization((allow) => allow.authenticated())` (or `guest()`, `group()`, `publicApiKey()`), **NEVER** `allow.owner()`.
2. **`a.generation()` Return Type & Scalar Constraints (Bedrock Validation Blocker):**
   - Never pass a DynamoDB `a.model()` to `.returns(a.ref('MyModel'))` on `a.generation()`. Always define an `a.customType({...})` and reference it via `.returns(a.ref('MyCustomType'))` or inline `a.customType({...})`.
   - Inside an `a.generation()` return type, **NEVER mark these 8 AppSync scalar types as `.required()`**:
     `a.email()`, `a.date()`, `a.time()`, `a.datetime()`, `a.timestamp()`, `a.phone()`, `a.url()`, `a.ipAddress()`.
     Keep them optional (e.g., `supplierUrl: a.url()`) or use `a.string().required()`.
3. **Three-Tier Tool Calling Authorization:**
   - When exposing a data model to `a.conversation()` via `a.ai.dataTool({ name, description, model: a.ref('Model'), modelOperation: 'list' })`, the conversation turn Lambda invokes AppSync using the caller's Cognito identity—ensure the target model allows `allow.authenticated()` or `allow.owner()`.
   - When exposing a custom query (`a.query()`) as a conversation tool (`{ name, description, query: a.ref('myQuery') }`), the custom query **MUST** include `allow.authenticated()` in its `.authorization()` rules.
4. **Streaming Chunk Reordering & Deletion Semantics:**
   - When subscribing directly to `conversation.onStreamEvent()` without `<AIConversation />` / `useAIConversation()`, chunks are **not** guaranteed to arrive in order. Always sort/reassemble using `contentBlockIndex` and `contentBlockDeltaIndex`.
   - Calling `client.conversations.<route>.delete({ id })` deletes the `Conversation` record and makes it inaccessible, but **does not cascade-delete** associated `ConversationMessage` items in DynamoDB.

---

## Workflow & Reference Routing

1. **Inspect `amplify/data/resource.ts` and target region:**
   - Confirm which Bedrock foundation models or Cross-Region Inference Profiles are available in the deployment region. Remind the user that Bedrock model access must be enabled in the target region.
2. **Load the required reference file before writing code:**

| Task | Reference to Load |
|---|---|
| Define `a.conversation()` or `a.generation()` routes, `a.customType()` return schemas, model selection, inference config, or cross-region inference profiles | [`references/ai-routes-and-schema-rules.md`](references/ai-routes-and-schema-rules.md) |
| Add AI tools (`a.ai.dataTool()`, custom `a.query()` tools, custom `@aws-amplify/backend-ai` conversation turn handlers, client-side tools), wire Amazon Bedrock Knowledge Bases (RAG), or build React/Next.js AI UI (`createAIHooks`, `<AIConversation />`, streaming) | [`references/ai-tools-rag-and-react-ui.md`](references/ai-tools-rag-and-react-ui.md) |

3. **Deploy & Verify:**
   - Run `npx ampx sandbox --once` to synthesize the AI routes, provision the conversation tables/turn handler Lambda, and regenerate `amplify_outputs.json` before compiling frontend code.
