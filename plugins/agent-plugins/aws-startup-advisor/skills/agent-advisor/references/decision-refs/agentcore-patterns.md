# Amazon Bedrock AgentCore Patterns: OAuth/OIDC Identity, Memory Migration & Sandboxes

Load this reference when designing or migrating production AI agents onto **Amazon Bedrock AgentCore** (`agent-advisor` `design`, `generate`, `poc`, or `add-capabilities` phases) and the agent requires user-scoped OAuth tool access, persistent memory migration, or isolated code/browser execution.

---

## 1. AgentCore Identity: Inbound Auth & Outbound 3LO OAuth Token Vault

Startups building AI agents that act on behalf of end users (reading/writing Slack, GitHub, Google Workspace, Salesforce, Linear, or internal APIs) must never store user OAuth refresh tokens in plaintext database columns or pass tokens through LLM prompt context.

### Two-Sided Identity Architecture
1. **Inbound Identity (Who is calling the agent?)**:
   - Authenticate user sessions with **Amazon Cognito** (or existing OIDC provider: Auth0, Clerk, WorkOS) and pass the validated JWT identity into the AgentCore Runtime session context (`userId` + `tenantId`).
2. **Outbound Identity (How does the agent call 3P tools on the user's behalf?)**:
   - Register external OAuth2 / API Key providers in **AgentCore Identity Token Vault**.
   - **3-Legged OAuth (3LO) Consent Flow**: When an agent tool decorated with `@requires_access_token(provider_name="github", scopes=["repo:read"], auth_flow="USER_FEDERATION")` is invoked and no valid token exists for `userId`, AgentCore pauses tool execution and emits an authorization URL to the client UI. Once the user completes consent, AgentCore vaults the refresh token encrypted with KMS and injects a short-lived access token directly into the tool execution context — **the LLM never sees the raw OAuth token**.
   - **Machine-to-Machine (2LO / Client Credentials)**: Use `auth_flow="M2M"` for internal microservices or shared SaaS integrations.

---

## 2. AgentCore Memory: Short-Term Session State & Long-Term Memory Migration

When migrating an existing agent from LangChain/LangGraph (`PostgresChatMessageHistory`, `RedisChatMessageHistory`, `Mem0`, or custom vector tables) to **AgentCore Memory**:

### Memory Tier Mapping

| Source Pattern | AgentCore Memory Primitive | Retention & Retrieval Behavior |
|---|---|---|
| `RedisChatMessageHistory` / in-memory thread state / LangGraph checkpointer | **AgentCore Short-Term Memory (Session Events)** | Stores raw turn-by-turn conversation events and tool call state keyed by `(actorId, sessionId)` with configurable TTL. |
| `Mem0` / custom `user_facts` pgvector table / summary buffer | **AgentCore Long-Term Memory Strategies** (`Semantic`, `Summary`, `UserPreferences`) | Asynchronously extracts durable user preferences, episodic summaries, and semantic facts from Short-Term events into namespaces (`/users/{actorId}/preferences`, `/users/{actorId}/facts`). |

### Zero-Downtime Memory Ingestion & Migration Plan
1. **Dual-Write Cutover (Phase 1)**: Keep existing Redis/Postgres session reads active while mirroring new conversation turns to `bedrock-agentcore:CreateEvent`.
2. **Historical Backfill (Phase 2)**: For active users (last 30 days), replay historical conversation summaries or extracted facts into AgentCore Memory namespaces using batch ingestion (`CreateEvent` / memory records) throttled via SQS so token/extraction quotas are respected.
3. **Read Cutover (Phase 3)**: Switch the agent's context builder to `RetrieveMemoryRecords` (top-k semantic recall + recent session turns) and retire the self-managed Redis/vector memory cluster.

---

## 3. AgentCore Built-In Sandboxes (Code Interpreter & Browser)

- **Code Interpreter**: When an agent needs to run Python data analysis, chart generation, or CSV/Excel processing, bind **AgentCore Code Interpreter** instead of running `exec()` or `subprocess` inside your application container (which is a critical RCE vulnerability). Each session executes in a hardware-isolated microVM sandbox.
- **Browser Tool**: When an agent needs to navigate external web pages or fill forms without an API, bind **AgentCore Browser** (managed headless Chromium inside an isolated microVM with session recording in S3) rather than bundling Playwright/Puppeteer inside Lambda or ECS containers.
