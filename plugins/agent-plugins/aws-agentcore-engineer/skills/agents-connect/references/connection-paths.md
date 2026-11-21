# AgentCore Gateway Connection Paths & Outbound Credential Wiring

Detailed CLI setup commands, schema templates, and framework client implementations for **Paths A–D** referenced by `agents-connect`. Present CLI commands as copy-paste operator reference snippets (never execute live mutations without operator approval, and never expose plaintext secrets in shell history or runtime environment variables).

---

## Path A: External MCP Server (`mcp-server`)

### 1. Add a Gateway (if none exists)

> [!WARNING]
> Never deploy a gateway without inbound authentication to production. A gateway with no authorizer exposes all connected tools (Lambda, MCP, OpenAPI) to any caller who knows the URL — functionally equivalent to `--authorizer-type NONE` on the runtime. Always use `--authorizer-type CUSTOM_JWT` or `AWS_IAM` for production gateways. The no-auth form (`agentcore add gateway --name X`) is for local testing only.

```bash
# Development only (no inbound auth — never use in production)
agentcore add gateway --name MyGateway

# Production (JWT inbound auth)
agentcore add gateway \
  --name MyGateway \
  --authorizer-type CUSTOM_JWT \
  --discovery-url https://your-idp.example.com/.well-known/openid-configuration \
  --allowed-audience my-api \
  --allowed-clients my-client-id
```

### 2. Add the MCP Server as a Gateway Target

```bash
# No outbound auth (public MCP server)
agentcore add gateway-target \
  --type mcp-server \
  --name WeatherTools \
  --endpoint https://mcp.example.com/mcp \
  --gateway MyGateway

# OAuth outbound auth (2-legged — client credentials / M2M)
# Omit --oauth-client-secret on the CLI in interactive shells to avoid shell-history exposure
agentcore add gateway-target \
  --type mcp-server \
  --name WeatherTools \
  --endpoint https://mcp.example.com/mcp \
  --gateway MyGateway \
  --outbound-auth oauth \
  --oauth-client-id your-client-id \
  --oauth-discovery-url https://auth.example.com/.well-known/openid-configuration \
  --oauth-scopes read,write
```

**Advanced MCP Target Auth (API/SDK Only):**

- **3-legged OAuth (`AUTHORIZATION_CODE` grant)** — user-delegated access has no CLI flag. Configure via boto3 `create_gateway_target` with `OAuthCredentialProvider.grantType = "AUTHORIZATION_CODE"` and `defaultReturnUrl`. See [Connecting to an OAuth-protected MCP server using Authorization Code flow](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-MCPservers.html#gateway-target-MCPservers-auth-code-grant-flow).
- **IAM (`SigV4`)** — for MCP servers hosted behind AWS services that natively verify SigV4 (AgentCore Runtime, AgentCore Gateway, Amazon API Gateway, or Lambda Function URLs; **not** ALB or direct EC2). Configure via `CreateGatewayTarget` with `GATEWAY_IAM_ROLE` credential provider and `iamCredentialProvider.service`.
- **API key auth** — **not supported** for `mcp-server` targets at the API level (only No authorization, OAuth, and IAM are supported). If a third-party MCP provider requires an API key, call it directly from agent code using Path D (`@requires_api_key`).

### 3. Deploy, Verify & Rollback

```bash
# Validate and preview before deploying
agentcore validate
agentcore deploy --dry-run

# Deploy and retrieve gateway endpoint URL
agentcore deploy -y
agentcore fetch access --name MyGateway
agentcore status --type gateway

# Rollback / remove target or gateway if needed
agentcore remove gateway-target --name WeatherTools --gateway MyGateway
agentcore deploy -y
```

After deploy, AgentCore injects the gateway URL into the runtime environment as `AGENTCORE_GATEWAY_<UPPERCASENAME>_URL` (for example, `AGENTCORE_GATEWAY_MYGATEWAY_URL`).

### 4. Generate Gateway Client Code

**Framework-agnostic MCP client:**

```python
import os
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Injected by AgentCore after deploy. Format: AGENTCORE_GATEWAY_<UPPERCASENAME>_URL
GATEWAY_URL = os.getenv("AGENTCORE_GATEWAY_MYGATEWAY_URL")

async def get_gateway_tools():
    """Discover tools from the gateway. Returns empty list if not deployed."""
    if not GATEWAY_URL:
        return []
    async with streamablehttp_client(GATEWAY_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return result.tools

async def call_gateway_tool(tool_name: str, arguments: dict):
    """Call a specific tool through the gateway."""
    if not GATEWAY_URL:
        raise RuntimeError("Gateway not available in local dev — deploy first")
    async with streamablehttp_client(GATEWAY_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await session.call_tool(tool_name, arguments)
```

**Semantic tool search (for catalogs with 20+ tools):**

```python
# Let AgentCore Gateway select relevant tools per turn instead of passing 20+ schemas
result = await session.call_tool(
    "x_amz_bedrock_agentcore_search",
    arguments={"query": "find tools related to processing refunds"},
)
# result.content lists the matching tools — invoke the selected tools normally
```

**Strands integration:**

```python
import os
import asyncio
from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model  # scaffolded by `agentcore create`

app = BedrockAgentCoreApp()
GATEWAY_URL = os.getenv("AGENTCORE_GATEWAY_MYGATEWAY_URL")

@app.entrypoint
def invoke(payload, context):
    if not GATEWAY_URL:
        # Local dev — run gracefully without gateway tools
        agent = Agent(model=load_model())
        return {"response": str(agent(payload.get("prompt", "")))}

    tools = asyncio.run(get_gateway_tools())
    agent = Agent(model=load_model(), tools=tools)
    return {"response": str(agent(payload.get("prompt", "")))}

if __name__ == "__main__":
    app.run()
```

**LangGraph integration:**

```python
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

@app.entrypoint
def agent_invocation(payload, context):
    if not GATEWAY_URL:
        tools = []
    else:
        client = MultiServerMCPClient(
            {"gateway": {"url": GATEWAY_URL, "transport": "streamable_http"}}
        )
        tools = asyncio.run(client.get_tools())

    llm_with_tools = llm.bind_tools(tools)
    # ... rest of your LangGraph StateGraph ...
```

---

## Path B: AWS Lambda Function as Tools (`lambda-function-arn`)

```bash
agentcore add gateway-target \
  --type lambda-function-arn \
  --name MyTools \
  --lambda-arn arn:aws:lambda:us-east-1:123456789012:function:my-tools \
  --tool-schema-file tools.json \
  --gateway MyGateway
```

`tools.json` defines the MCP tool schemas exposed for the Lambda function:

```json
{
  "inlinePayload": [
    {
      "name": "get_weather",
      "description": "Get current weather for a city",
      "inputSchema": {
        "type": "object",
        "properties": {
          "city": {"type": "string", "description": "City name"}
        },
        "required": ["city"]
      }
    }
  ]
}
```

- **Auth:** Lambda targets use IAM role auth automatically (no `--outbound-auth` flag required unless passing OAuth 2LO/3LO downstream). Ensure the gateway's execution role has `lambda:InvokeFunction` scoped to the target Lambda ARN.
- **Client code:** Identical to Path A (`AGENTCORE_GATEWAY_<UPPERCASENAME>_URL` + MCP client).

---

## Path C: OpenAPI Spec (`open-api-schema`) or API Gateway (`api-gateway`)

```bash
# 1. Register credential interactively (recommended — avoids putting --api-key in shell history)
agentcore add credential --name MyAPIKey --type api-key

# 2. Register OpenAPI target (outbound auth is REQUIRED: oauth or api-key; no 'none' option)
agentcore add gateway-target \
  --type open-api-schema \
  --name MyAPI \
  --schema specs/api.json \
  --gateway MyGateway \
  --outbound-auth api-key \
  --credential-name MyAPIKey
```

For AWS API Gateway REST APIs (`--type api-gateway`), CLI outbound auth supports `none` or `api-key`, and SDK/API additionally supports IAM (`GATEWAY_IAM_ROLE`).

**Secret Handling Rules:**

1. **Interactive prompt:** Omit `--api-key` and `--client-secret` flags so the CLI prompts interactively and writes directly to the Secrets Manager-backed credential provider without touching shell history.
2. **Local dev (`agentcore/.env.local`):** Put local test credentials in gitignored `agentcore/.env.local` for `agentcore dev`. It is **never** uploaded on deploy, and agents must **never** read or print `.env.local`.
3. **Never use runtime env vars for secrets:** AgentCore Runtime environment variables are plaintext configuration, not vault-backed.

---

## Path D: Direct Outbound Credentials in Agent Code (Fallback Only)

Use Path D **only** when a Gateway target (Paths A–C) cannot front the call: (1) streaming/bidirectional protocols (`SSE`, `WebSockets`, `WebRTC`), (2) measured latency-critical hot paths with accepted trade-offs, (3) vendor binary/proprietary SDKs without an HTTP/OpenAPI surface (or third-party MCP servers requiring API keys), or (4) A2A agent-to-agent calls. (For AWS SDK calls like S3/DynamoDB, use the runtime IAM execution role directly with `boto3` — no credential registration needed.)

### 1. Register the Credential (Interactive)

```bash
# API key (prompts interactively when --api-key is omitted)
agentcore add credential --name OpenAI --type api-key

# OAuth M2M (prompts interactively for secret when --client-secret is omitted)
agentcore add credential \
  --name MyOAuthProvider \
  --type oauth \
  --discovery-url https://idp.example.com/.well-known/openid-configuration \
  --client-id my-client-id \
  --scopes read,write
```

### 2. Inject Credentials via Identity Decorators

`@requires_api_key` and `@requires_access_token` work on both sync and async functions, handle token caching/refresh automatically, and inject secrets via keyword-only arguments (`*, api_key: str` or `*, access_token: str`). Locally (`agentcore dev`), they resolve from gitignored `agentcore/.env.local`; deployed, they fetch from the Secrets Manager-backed AgentCore Identity vault.

```python
from bedrock_agentcore.identity.auth import requires_api_key, requires_access_token

# Sync function — keyword-only api_key injected at call time
@requires_api_key(provider_name="OpenAI")
def call_openai(prompt: str, *, api_key: str) -> str:
    import openai
    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content

# Async function — OAuth M2M token cached and refreshed automatically
@requires_access_token(
    provider_name="MyOAuthProvider",
    scopes=["read", "write"],
    auth_flow="M2M",
)
async def call_my_api(data: dict, *, access_token: str) -> dict:
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.example.com/endpoint",
            headers={"Authorization": f"Bearer {access_token}"},
            json=data,
        )
        return response.json()
```
