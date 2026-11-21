---
name: agents-connect
description: >
  Use when connecting your agent to external APIs, tools, or services via
  Gateway, or restricting tool access with Cedar policies. Handles gateway
  setup, target types, outbound auth (OAuth, API key, IAM), credentials,
  and Cedar policy authoring. Triggers on: "connect to API", "add gateway",
  "connect to MCP server", "Lambda tools", "OpenAPI", "gateway target",
  "Cedar policy", "restrict tools", "policy engine", "gateway auth error",
  "store API key", "outbound credential", "env var API key", "API key None
  after deploy", "credential not available after deploy",
  "should this be a gateway target", "give my agent tools",
  "add tools to agent".
  Not for inbound auth (who can call your agent) — use agents-harden.
  Not for debugging agent behavior — use agents-debug.
  Not for VPC networking errors (agent can't reach APIs due to VPC) — use
  agents-build. Not for creating or hosting a new MCP server project — use
  agents-get-started.
allowed-tools: Read Grep Glob Bash
metadata:
  type: skill
  version: "1.0.0"
  author: aws-agentcore
  requires-cli: ">=0.9.0"
---

# connect

Give your AgentCore agent access to external APIs, tools, and services via the AgentCore Gateway — and control what it can access with Cedar policies.

## When to use

- You want your agent to call an external API or MCP server
- You want to expose Lambda functions as agent tools
- You have an OpenAPI spec or API Gateway REST API you want to turn into agent tools
- Your agent needs outbound credentials to call an external service
- You want to restrict which tools your agent can call (Cedar policies, role-based or amount-based rules)
- A gateway connection, tool call, or policy authorization is failing

**Progressive-disclosure references (load on demand):**
- Copy-paste CLI commands, `tools.json` schemas, MCP client code (Strands, LangGraph, framework-agnostic), and `@requires_api_key` / `@requires_access_token` wiring → [`references/connection-paths.md`](references/connection-paths.md)
- Cedar policy authoring, schema generation, and `LOG_ONLY` → `ENFORCE` rollout → [`references/policy.md`](references/policy.md)
- MCP `2026-07-28` protocol version negotiation (`supportedVersions`, `-32022` error handling), Gateway Request/Response Interceptor Lambdas, Two-Step On-Behalf-Of (OBO) token exchange with KMS asymmetric signing, and S3/CloudFront OIDC discovery shims → [`references/interceptors-and-obo.md`](references/interceptors-and-obo.md)
- Custom inbound HTTP header allowlisting → [`references/request-headers.md`](references/request-headers.md)
- Calling your agent from an app (inbound direction) → [`references/integrate.md`](references/integrate.md)
- Multi-agent A2A communication → [`references/multi-agent.md`](references/multi-agent.md)

## MCP-Only Execution & Read-Only Safety

- **MCP-Only Live Discovery & Docs:** Execute **all** live AWS discovery, AgentCore runtime/gateway/memory inspection, telemetry/log/trace queries, IAM policy checks, and documentation lookups **exclusively via connected MCP tools**: `aws-mcp` (`aws___run_script` using read-only `await call_boto3(...)`, `aws___search_documentation`, `aws___read_documentation`), `agentcore` (`search_agentcore_docs`, `fetch_agentcore_doc`, `list_agent_runtimes`, `get_agent_runtime`, etc.), `strands-agents` (`search_docs`, `fetch_doc`, `find_integrations`), `cloudwatch`, `appsignals`, `cloudtrail`, `awspricing`, `awsiac`, and `awsknowledge`.
- **Zero Raw CLI Execution, Strictly Read-Only & Secret-Safe:** **Never** run raw `aws ...` or `agentcore ...` CLI commands in Bash/`run_command` to query or mutate live AWS accounts (present CLI commands in Markdown strictly as operator reference snippets). **Never** invoke live mutations (`create_*`, `update_*`, `delete_*`, `InvokeAgentRuntime`, `InvokeModel`) — refuse unapproved destructive/mutating requests and explain the safe approval-gated operator workflow with verification and rollback steps. **Never** read or print plaintext secrets (`secretsmanager:GetSecretValue`, `ssm:GetParameter` with `WithDecryption=True`, `.env` / `.env.local` values, or raw memory record contents).
- **Edge-Case Documentation Fallback:** For unmapped AWS/AgentCore/Bedrock edge cases (e.g., latest `CreateGatewayTarget` auth fields), run 1–2 focused queries via `agentcore`, `strands-agents`, `awsknowledge`, or `aws-mcp` documentation search tools.

## Input

`$ARGUMENTS` is optional:

```
/connect                    # interactive — asks what you're connecting to
/connect mcp                # MCP server setup
/connect lambda             # Lambda function as tools
/connect openapi            # OpenAPI schema as tools
/connect credential         # Add a credential for outbound auth
```

## Process

### Step 0: Verify CLI version prerequisite

This workflow requires AgentCore CLI `>= 0.9.0` (operators can check locally via `agentcore --version` and upgrade via `agentcore update`).

### Step 1: Read the project

Read `agentcore/agentcore.json` (if present in the workspace) to inspect the framework and existing `agentCoreGateways` / targets. Never read `.env` or `agentcore/.env.local`. If no project file exists, ask what they are connecting to and recommend the right pattern.

### Step 2: Identify what they're connecting to

Ask (or infer from `$ARGUMENTS`):
1. External MCP server (`mcp-server` — Path A)
2. AWS Lambda function (`lambda-function-arn` — Path B)
3. HTTP API with an OpenAPI spec (`open-api-schema` — Path C)
4. AWS API Gateway REST API (`api-gateway` — Path C)
5. External service with no OpenAPI spec, MCP server, or Lambda in front of it where fronting isn't practical (Path D — direct call with Identity credential provider)

---

## Default: Prefer a Gateway Target Over Direct API Calls in Code

**Why Gateway (Options 1–4) is the default:**
- **Credential injection at the edge:** Gateway credential providers (OAuth, API key, IAM) attach auth to outbound requests so agent code (`session.call_tool(...)`) never sees the secret and cannot leak it via prompts, logs, or tracebacks.
- **Discoverable tool catalog:** Frameworks (Strands, LangGraph) bind MCP tools automatically; adding tools is config + deploy rather than code edits.
- **Policy enforcement:** Cedar Policy Engine rules authorize/deny per principal, tool, and argument at the Gateway edge.
- **Built-in semantic search:** For catalogs with **20+ tools**, `x_amz_bedrock_agentcore_search` selects relevant tools per turn without custom vector stores.

**When a direct API call in agent code IS the right answer:**

| Situation | Why Gateway isn't right | What to do |
|---|---|---|
| Streaming/bidirectional protocol (SSE with live output, WebSockets, WebRTC, long-polling) | Gateway's MCP transport doesn't front those yet | Direct call, Path D |
| Latency hot path where the MCP hop is measurable and the trade-off is accepted | Extra network hop | Direct call, Path D, with measurement to back the decision |
| Vendor proprietary protocol / binary SDK (or third-party MCP server requiring API-key auth) | No supported Gateway target surface | Use SDK/client directly, Path D (`@requires_*`) for secrets |
| Calling another agent via A2A | A2A is HTTP-by-design with its own auth model | Load [`references/multi-agent.md`](references/multi-agent.md), not a Gateway target |
| AWS service SDK (S3, DynamoDB, SQS, etc.) the runtime already has IAM for | No auth value in fronting — adds hops | Direct `boto3` call with the runtime's execution role |

For **every other case**, steer the developer back to a Gateway target (Paths A–C).

---

## What Gateway Is — and What It Isn't

**Gateway hosts outbound tools for your agent to call** (`Your agent ──→ Gateway ──→ Lambda / OpenAPI / MCP server / API Gateway / Smithy`).
**Gateway is NOT an inbound reverse proxy for your agent.** Apps invoking your agent call AgentCore Runtime directly (`Your app ──→ AgentCore Runtime` via IAM SigV4 or `CUSTOM_JWT` — see [`references/integrate.md`](references/integrate.md)). Never point a Gateway target at `bedrock-agentcore.<region>.amazonaws.com` or your own runtime URL.

| What the tool is | Target type (`--type`) | Notes |
|---|---|---|
| MCP server (third-party or your own) | `mcp-server` | Most common for MCP tool catalogs |
| AWS Lambda function you wrote | `lambda-function-arn` | Uses IAM role auth (`lambda:InvokeFunction`) automatically |
| HTTP API with an OpenAPI spec | `open-api-schema` | FastAPI/Spring/ASP.NET auto-generated `/openapi.json` works |
| AWS API Gateway REST API | `api-gateway` | For APIs already fronted by API Gateway |
| AWS service with a Smithy model | `smithy-model` | Direct AWS service integration |

---

### Step 3: Navigate the Auth Matrix

| What you're connecting to | CLI `--type` | Outbound auth via CLI | Additional options via API/SDK (`CreateGatewayTarget`) |
|---|---|---|---|
| External MCP server | `mcp-server` | `none`, `oauth` (2LO only) | OAuth 3LO (`AUTHORIZATION_CODE` + `defaultReturnUrl`); IAM (`GATEWAY_IAM_ROLE` + `iamCredentialProvider.service`) |
| Lambda function | `lambda-function-arn` | `none` (default — gateway IAM role invokes Lambda), `oauth` (2LO) | OAuth 3LO |
| OpenAPI spec | `open-api-schema` | `oauth` (2LO), `api-key` (**required** — no `none`) | OAuth 3LO |
| AWS API Gateway | `api-gateway` | `none`, `api-key` | IAM (`GATEWAY_IAM_ROLE`) |
| Smithy model | `smithy-model` | `oauth` (2LO) | IAM; OAuth 3LO |

**Critical Auth Rules:**
1. **2LO vs 3LO OAuth:** CLI `--outbound-auth oauth` configures **2-legged OAuth** (client credentials / M2M) only. **3-legged OAuth** (`grantType: AUTHORIZATION_CODE` + `defaultReturnUrl`) must be configured via `boto3` (`create_gateway_target`) — flag this up front so operators don't hunt for non-existent CLI flags.
2. **IAM (`SigV4`) for MCP servers:** Configured via SDK/API (`GATEWAY_IAM_ROLE` + `iamCredentialProvider.service`). Requires the MCP server to sit behind an AWS SigV4-verifying service (AgentCore Runtime, AgentCore Gateway, API Gateway, or Lambda Function URL — **not** ALB or raw EC2).
3. **API key auth is NOT supported for `mcp-server` targets at the API level:** Only `none`, `OAuth`, and `IAM` exist for MCP targets. For API-key-protected MCP servers, use Path D in agent code.
4. **Gateway inbound auth is mandatory in production:** Never deploy a production gateway without `--authorizer-type CUSTOM_JWT` or `AWS_IAM`.
5. **Semantic tool search (20+ tools):** Enable semantic search on gateways with >20 tools and call `x_amz_bedrock_agentcore_search` (`arguments={"query": "..."}`) rather than building custom RAG/vector tool selectors.
6. **Inbound custom headers:** Runtime strips custom HTTP headers by default; load [`references/request-headers.md`](references/request-headers.md) if callers pass tenant/correlation/`A2A-Version` headers.

---

## Step 4: Configure the Chosen Path (Load [`references/connection-paths.md`](references/connection-paths.md))

Before generating CLI commands, JSON schemas, or framework client code, **load [`references/connection-paths.md`](references/connection-paths.md)** for complete, copy-paste-ready snippets, verification steps, and rollback commands:

| Path | Target / Mechanism | Key Setup & Security Invariants |
|---|---|---|
| **Path A** | `mcp-server` | `agentcore add gateway` (`CUSTOM_JWT` or `AWS_IAM` in prod) → `agentcore add gateway-target --type mcp-server` → `agentcore deploy -y` → `agentcore fetch access --name <Gw>`. Runtime reads `AGENTCORE_GATEWAY_<UPPERCASENAME>_URL` via `streamablehttp_client` / Strands / LangGraph `MultiServerMCPClient`. |
| **Path B** | `lambda-function-arn` | `agentcore add gateway-target --type lambda-function-arn --lambda-arn <ARN> --tool-schema-file tools.json` (`inlinePayload` schema). Gateway role needs `lambda:InvokeFunction`. |
| **Path C** | `open-api-schema` / `api-gateway` | Register secret interactively via `agentcore add credential --name <Name> --type api-key` (omit `--api-key` flag to keep secrets out of shell history), then `--outbound-auth api-key --credential-name <Name>` (or `oauth`). |
| **Path D** | Direct code (`@requires_api_key` / `@requires_access_token`) | Fallback only when Gateway cannot front the protocol. Register via `agentcore add credential`; inject keyword-only `*, api_key: str` or `*, access_token: str` at call time. **Never** ship secrets via runtime env vars. |

**Verification & Rollback (Operator Commands):**
- Pre-flight & deploy check: `agentcore validate`, `agentcore deploy --dry-run`, `agentcore status --type gateway`, `agentcore fetch access --name <GatewayName>`.
- Safe rollback: remove a misconfigured target or policy via `agentcore remove gateway-target --name <Target> --gateway <Gateway>` (or revert `agentcore/agentcore.json`) and re-apply with `agentcore deploy`.

---

## Local Dev Gap

> [!WARNING]
> Gateway URLs (`AGENTCORE_GATEWAY_<UPPERCASENAME>_URL`) are injected **only after `agentcore deploy`** and are unset in `agentcore dev --local`. Always guard in agent code (`if not GATEWAY_URL: tools = []`). For Path D credentials in local dev, `agentcore dev` resolves decorators from gitignored `agentcore/.env.local` (never uploaded on deploy, and never read by the agent).

---

## Troubleshooting

- **`"mcp-server target doesn't support api-key auth"`:** API-level platform constraint — use OAuth (2LO/3LO), IAM SigV4 (behind Runtime/Gateway/API Gateway/Lambda URL), or Path D (`@requires_api_key`) in agent code.
- **Need 3LO (`AUTHORIZATION_CODE`) but `--outbound-auth oauth` has no return URL flag:** CLI supports 2LO only; configure `create_gateway_target` via `boto3` with `credentialProviderType="OAUTH"`, `grantType="AUTHORIZATION_CODE"`, and `defaultReturnUrl`.
- **`"api-gateway target doesn't support oauth"`:** Use `api-key`, `none`, or SDK-configured `GATEWAY_IAM_ROLE`.
- **Gateway URL missing after deploy:** Run `agentcore fetch access --name <Gateway>` and verify `READY` state via `agentcore status --type gateway` (or `agentcore` MCP `get_gateway`).
- **Tool calls failing with 401/403 auth errors:** Inspect runtime/gateway error logs (via `cloudwatch` MCP or operator `agentcore logs --runtime <Agent> --since 1h --level error`) for expired OAuth tokens, mismatched credential provider names, missing `lambda:InvokeFunction`, or Cedar `DENY` decisions.
- **External MCP clients (Claude Desktop, claude.ai) cannot auto-connect to Gateway:** AgentCore Gateway does not implement RFC 8414 OAuth Authorization Server Metadata or RFC 7591 Dynamic Client Registration; configure Cognito `client_id` and `client_secret` manually in the MCP client's advanced settings.

## Output

- Clear **Gateway target vs. direct API call** recommendation grounded in the 5 valid direct-call exceptions
- Validated auth choice from the Gateway Auth Matrix (flagging CLI vs. SDK/API boundaries)
- Copy-paste-ready operator CLI setup, verification, and rollback commands plus framework-specific client code (from [`references/connection-paths.md`](references/connection-paths.md))
- Secret-safe credential wiring (interactive prompt, vault-backed credential provider, local-only `.env.local`, zero secrets in runtime env vars)
