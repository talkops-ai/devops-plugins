# Gateway MCP 2026-07-28 Negotiation, Interceptor Lambdas & Two-Step OBO

## 1. MCP `2026-07-28` Protocol Version Negotiation

Amazon Bedrock AgentCore Gateway enforces explicit Model Context Protocol (MCP) version negotiation across `initialize` and subsequent JSON-RPC requests.

### Configuration & Header Contract
1. **Gateway Target Configuration:** Explicitly declare `supportedVersions` on every MCP Gateway target:
   ```json
   {
     "name": "EnterpriseOrderService",
     "targetType": "MCP_SERVER",
     "endpoint": "https://mcp.internal.example.com/mcp",
     "protocolConfiguration": {
       "supportedVersions": ["2026-07-28", "2025-11-25"]
     }
   }
   ```
2. **Per-Request Header:** Include `MCP-Protocol-Version: 2026-07-28` on all HTTP requests after the `initialize` handshake.
3. **Handling `-32022` Protocol Mismatch Errors:**
   - If the client requests a version not listed in `supportedVersions`, Gateway returns JSON-RPC error code **`-32022`** (`Unsupported protocol version`).
   - **Never silently fall back to `2025-03-26`:** The legacy `2025-03-26` protocol lacks structured authorization context propagation and causes silent Cedar policy context loss. Negotiate `2026-07-28` or `2025-11-25` explicitly.

---

## 2. Gateway Request & Response Interceptor Lambdas

AgentCore Gateway supports attaching AWS Lambda interceptors at two hook points:
- **`REQUEST` Interceptor:** Executes *after* inbound JWT validation and Cedar policy evaluation, *before* the tool target is invoked. Use it to:
  1. Extract custom HTTP headers (`X-Tenant-Id`, `X-Correlation-Id`) or validated JWT claims (`sub`, `department`) and inject them directly into the MCP `tools/call` arguments so the LLM cannot spoof tenant/user identity.
  2. Enforce **per-user, per-tool sliding-window rate limits** backed by Amazon ElastiCache (Redis/Valkey).
- **`RESPONSE` Interceptor:** Executes *after* the target responds, *before* the payload returns to the agent. Use it to:
  1. Dynamically filter `tools/list` results based on the caller's role/scopes.
  2. Scrub PII, internal stack traces, or raw secrets from `tools/call` responses.

> [!IMPORTANT]
> **Interceptor Operational Requirements:**
> - **Idempotency:** Interceptors must be idempotent across Gateway retries.
> - **Streaming Compatibility:** Preserve chunk framing when targets use `streamable-http`.
> - **Resource-Based Policy:** Grant ` bedrock-agentcore.amazonaws.com` `lambda:InvokeFunction` permission scoped via `aws:SourceArn` to the Gateway ARN.

### Reference Implementation: Request Interceptor (Claim Injection + Redis Rate Limiting)

```python
import os
import time
import json
import redis

# Warm-pool module-level Redis client (ElastiCache Serverless / Valkey)
REDIS_Client = redis.Redis(
    host=os.environ.get("REDIS_ENDPOINT", "localhost"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    ssl=True,
    decode_responses=True,
)
RATE_LIMIT_WINDOW_SEC = 60
MAX_CALLS_PER_WINDOW = int(os.environ.get("MAX_CALLS_PER_MINUTE", "30"))


def enforce_sliding_window_limit(user_id: str, tool_name: str) -> bool:
    """Returns True if allowed, False if rate limit exceeded."""
    now_ms = int(time.time() * 1000)
    window_start_ms = now_ms - (RATE_LIMIT_WINDOW_SEC * 1000)
    key = f"ratelimit:{user_id}:{tool_name}"

    pipe = REDIS_Client.pipeline()
    pipe.zremrangebyscore(key, 0, window_start_ms)
    pipe.zcard(key)
    pipe.zadd(key, {str(now_ms): now_ms})
    pipe.expire(key, RATE_LIMIT_WINDOW_SEC + 5)
    _, current_count, _, _ = pipe.execute()
    return current_count < MAX_CALLS_PER_WINDOW


def lambda_handler(event: dict, context) -> dict:
    """AgentCore Gateway REQUEST Interceptor Lambda."""
    mcp_request = event.get("mcpRequest", {})
    method = mcp_request.get("method", "")
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    claims = event.get("authorizerContext", {}).get("claims", {})

    user_sub = claims.get("sub") or headers.get("x-user-id", "anonymous")
    tenant_id = claims.get("custom:tenant_id") or headers.get("x-tenant-id", "default")

    if method == "tools/call":
        params = mcp_request.setdefault("params", {})
        tool_name = params.get("name", "unknown_tool")

        # 1. Per-User, Per-Tool Sliding-Window Rate Limit
        if not enforce_sliding_window_limit(user_sub, tool_name):
            return {
                "interceptorAction": "REJECT",
                "statusCode": 429,
                "jsonRpcError": {
                    "code": -32029,
                    "message": f"Rate limit exceeded for user {user_sub} on tool {tool_name}",
                },
            }

        # 2. Cryptographically Verified Claim/Header Injection (prevents LLM spoofing)
        arguments = params.setdefault("arguments", {})
        arguments["_authenticated_user_id"] = user_sub
        arguments["_authenticated_tenant_id"] = tenant_id

    return {
        "interceptorAction": "CONTINUE",
        "mcpRequest": mcp_request,
        "headers": event.get("headers", {}),
    }
```

### Reference Implementation: Response Interceptor (Role-Based `tools/list` Filtering)

```python
ADMIN_ONLY_TOOLS = {
    "OrderService___refund_order",
    "OrderService___delete_customer_record",
    "InfraService___force_failover",
}


def lambda_handler(event: dict, context) -> dict:
    """AgentCore Gateway RESPONSE Interceptor Lambda."""
    mcp_response = event.get("mcpResponse", {})
    method = event.get("mcpRequest", {}).get("method", "")
    claims = event.get("authorizerContext", {}).get("claims", {})
    roles = set(claims.get("cognito:groups", []) or claims.get("roles", []))

    # Filter admin-only tools from discovery for non-admin callers
    if method == "tools/list" and "admin" not in roles:
        result = mcp_response.get("result", {})
        tools = result.get("tools", [])
        result["tools"] = [t for t in tools if t.get("name") not in ADMIN_ONLY_TOOLS]

    return {
        "interceptorAction": "CONTINUE",
        "mcpResponse": mcp_response,
    }
```

---

## 3. Two-Step On-Behalf-Of (OBO) Token Exchange with KMS Signing

In regulated enterprises, downstream APIs must reject generic agent service-account tokens and instead require a cryptographically signed token proving **both** the human caller (`sub`) and the acting agent/Gateway (`act` claim per RFC 8693).

### 6-Step Two-Step OBO Flow
1. **User -> Runtime:** User authenticates with the corporate IdP and invokes the AgentCore Runtime passing their bearer JWT (`Authorization: Bearer <user-jwt>`).
2. **Per-Request `MCPClient` Forwarding:** Inside `@app.entrypoint`, the agent extracts `context.request_headers["Authorization"]` and instantiates a per-request `MCPClient` so the user's JWT is forwarded to AgentCore Gateway.
3. **Step 1 Exchange (Agent Workload Identity):** The Runtime/Gateway validates the inbound user JWT against the OIDC authorizer.
4. **KMS Private-Key JWT Assertion (`kms:Sign`):** An Interceptor or Token Exchange Lambda constructs an RFC 8693 actor assertion containing `sub` (human user ID), `agent_workload_id`, and `gateway_id`, and signs it using an asymmetric **AWS KMS key (`ECC_NIST_P256` or `RSA_2048`)** so the private key never leaves KMS hardware.
5. **Step 2 Exchange (Downstream OBO Token):** The signed KMS assertion + user subject token are exchanged at the corporate IdP's `/oauth2/token` endpoint (`grant_type=urn:ietf:params:oauth:grant-type:token-exchange`) for a narrow-scoped downstream access token.
6. **Target Invocation:** Gateway invokes the downstream API with the exchanged OBO token.

```python
import base64
import json
import time
import boto3

kms = boto3.client("kms")


def sign_obo_assertion_with_kms(
    kms_key_id: str,
    issuer: str,
    audience: str,
    user_sub: str,
    agent_workload_id: str,
    gateway_id: str,
) -> str:
    """Signs a JWT assertion using an asymmetric KMS key (ECC_NIST_P256 / ES256)."""
    now = int(time.time())
    header = {"alg": "ES256", "typ": "JWT", "kid": kms_key_id}
    payload = {
        "iss": issuer,
        "sub": user_sub,
        "aud": audience,
        "iat": now,
        "exp": now + 300,
        "act": {
            "sub": agent_workload_id,
            "gateway_id": gateway_id,
        },
    }

    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    signing_input = (
        f"{_b64url(json.dumps(header, separators=(',', ':')).encode())}."
        f"{_b64url(json.dumps(payload, separators=(',', ':')).encode())}"
    )
    resp = kms.sign(
        KeyId=kms_key_id,
        Message=signing_input.encode("ascii"),
        MessageType="RAW",
        SigningAlgorithm="ECDSA_SHA_256",
    )
    return f"{signing_input}.{_b64url(resp['Signature'])}"
```

---

## 4. Static S3/CloudFront OIDC Discovery Shim for JWKS-Only Corporate IdPs

AgentCore Runtime and Gateway `CUSTOM_JWT` authorizers require a valid OIDC discovery URL (`https://<issuer>/.well-known/openid-configuration`). If your corporate IdP only exposes a raw JWKS endpoint (`https://idp.internal.corp/keys`) without a discovery document:

1. Create a private **Amazon S3 bucket** fronted by **Amazon CloudFront** with Origin Access Control (OAC).
2. Upload a static `/.well-known/openid-configuration` JSON file pointing `jwks_uri` to the corporate JWKS URL (or a synced S3 copy of `jwks.json`):
   ```json
   {
     "issuer": "https://d111111abcdef8.cloudfront.net",
     "jwks_uri": "https://d111111abcdef8.cloudfront.net/.well-known/jwks.json",
     "authorization_endpoint": "https://idp.internal.corp/oauth2/authorize",
     "token_endpoint": "https://idp.internal.corp/oauth2/token",
     "response_types_supported": ["code", "token", "id_token"],
     "subject_types_supported": ["public"],
     "id_token_signing_alg_values_supported": ["RS256", "ES256"]
   }
   ```
3. Configure `customJWTAuthorizer.discoveryUrl` on the AgentCore Runtime and Gateway to `https://d111111abcdef8.cloudfront.net/.well-known/openid-configuration`.
