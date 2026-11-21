# AgentCore Production Hardening Policies, Code Patterns & Deep Dives

Detailed IAM policy JSON templates, JWT troubleshooting steps, `agentcore.json` snippets, and Python reference implementations for `agents-harden`. Always perform live AWS/IAM/AgentCore discovery via connected MCP tools in read-only mode, and present CLI/IaC commands as operator reference snippets.

---

## 1. IAM Least Privilege & `InvokeAgentRuntimeCommand` Separation

### Scoped Bedrock, ECR & Trust Policies

Replace the scaffolded wildcard foundation-model ARN (`arn:aws:bedrock:*::foundation-model/*`) with exact model/inference-profile ARNs, scope ECR to the agent repository, and bind the trust policy to your account:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ScopedBedrockInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:<REGION>::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0"
      ]
    },
    {
      "Sid": "ScopedECRPull",
      "Effect": "Allow",
      "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
      "Resource": "arn:aws:ecr:<REGION>:<YOUR_ACCOUNT_ID>:repository/bedrock-agentcore-<AGENT_NAME>-*"
    }
  ]
}
```

**Execution Role Trust Policy (`sts:AssumeRole`):**

```json
{
  "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
  "Action": "sts:AssumeRole",
  "Condition": {
    "StringEquals": {"aws:SourceAccount": "<YOUR_ACCOUNT_ID>"},
    "ArnLike": {"aws:SourceArn": "arn:aws:bedrock-agentcore:<REGION>:<YOUR_ACCOUNT_ID>:*"}
  }
}
```

For fine-grained caller restrictions beyond IAM roles and JWT claims, configure a runtime resource-based policy via `PutAgentRuntimeResourcePolicy` (`boto3`; API-only).

### Isolating `InvokeAgentRuntimeCommand` (Shell Execution Inside MicroVM)

`InvokeAgentRuntimeCommand` grants arbitrary shell execution inside a live microVM with the runtime's full execution role. Keep it in a dedicated IAM policy separate from `InvokeAgentRuntime`, alert via CloudTrail + EventBridge, and reject shell metacharacters (`&&`, `;`, `$(...)`, backticks, `|`) if any caller constructs commands from input:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "bedrock-agentcore:InvokeAgentRuntimeCommand",
    "Resource": "arn:aws:bedrock-agentcore:<REGION>:<YOUR_ACCOUNT_ID>:runtime/<RUNTIME_NAME>-*"
  }]
}
```

```bash
# Operator CLI reference: CloudTrail EventBridge alert rule for InvokeAgentRuntimeCommand
aws events put-rule \
  --name AgentCoreCommandExecution \
  --event-pattern '{"source":["aws.bedrock-agentcore"],"detail-type":["AWS API Call via CloudTrail"],"detail":{"eventName":["InvokeAgentRuntimeCommand"]}}' \
  --state ENABLED
```

---

## 2. Inbound Auth (`AWS_IAM` vs. `CUSTOM_JWT`) & `403` Troubleshooting

```bash
# Operator CLI reference: configure CUSTOM_JWT inbound auth (never use NONE in production)
agentcore add agent \
  --name MyAgent \
  --authorizer-type CUSTOM_JWT \
  --discovery-url https://your-idp.example.com/.well-known/openid-configuration \
  --allowed-audience my-api \
  --allowed-clients my-client-id
```

1. **`allowedClients` vs. `allowedAudience`:**
   - Token has `client_id` and no `aud` → configure **`allowedClients`**.
   - Token has `aud` (or both `aud` and `client_id`) → configure **`allowedAudience`**.
2. **RFC 8414 §3 Issuer Prefix Rule:** The `issuer` inside `.well-known/openid-configuration` **must** be a URL prefix of the discovery URL (e.g., `https://qa.example.com/.well-known/openid-configuration` cannot advertise `https://example.com`). Align the IdP discovery origin with `iss` (or deploy an S3/CloudFront OIDC discovery shim).
3. **Debugging `403` errors:**
   - **`Authorization method mismatch`:** Runtime expects `AWS_IAM` while caller sends `Bearer` JWT, **or** runtime expects `CUSTOM_JWT` while caller's SDK injects SigV4 headers (`X-Amz-Date`, `X-Amz-Security-Token`, `Authorization: AWS4-HMAC-SHA256`) alongside the Bearer token. Strip SigV4 headers on `CUSTOM_JWT` calls.
   - **`Invalid inbound token`:** Verify in order: (1) `iss` ↔ discovery URL prefix match, (2) `allowedAudience` vs `allowedClients`, (3) public reachability of `jwks_uri`, (4) `exp` timestamp, and (5) signing algorithm compatibility (switch to `RS256` if `PS256`/`ES384` fails).

---

## 3. Graceful Error Handling, Input Validation & Secret-Safe Decorators

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.identity.auth import requires_api_key, requires_access_token

app = BedrockAgentCoreApp()

@requires_api_key(provider_name="MyAPI")
def call_api(payload: dict, *, api_key: str) -> dict:
    ...

@requires_access_token(provider_name="MyOAuthProvider", scopes=["read"], auth_flow="M2M")
async def call_downstream(data: dict, *, access_token: str) -> dict:
    ...

@app.entrypoint
def invoke(payload, context):
    prompt = payload.get("prompt", "")
    if not prompt or not isinstance(prompt, str):
        return {"error": "Missing or invalid 'prompt' field"}
    if len(prompt) > 10000:
        return {"error": "Prompt exceeds maximum length (10,000 characters)"}

    prompt = " ".join(prompt.split())
    try:
        result = agent(prompt)
        return {"response": str(result)}
    except Exception as e:
        app.logger.error(f"Agent error: {e}", exc_info=True)
        return {"error": "An error occurred. Please try again."}
```

**Static Code Audit Patterns (Workspace Source Code Only — Never Read `.env`):**
- Hardcoded secrets: search `*.py` for `sk-`, `api_key\s*=\s*['"]`, `password\s*=\s*['"]`.
- Secrets in non-vault runtime env vars: search `*.py` for `os\.(getenv|environ).*(TOKEN|SECRET|KEY|PASSWORD|CREDENTIAL)` (platform identifiers like `MEMORY_*_ID`, `AGENTCORE_GATEWAY_*_URL`, and `AWS_REGION` are non-secret and safe).
- Direct HTTP tool calls bypassing Gateway: search `*.py` for `httpx\.|requests\.|aiohttp\.`.

---

## 4. Cold-Start Optimization: Warm-Pool Singletons vs. Per-Request `MCPClient`

MicroVMs remain warm for `idleRuntimeSessionTimeout` (default **900s / 15m**). Cache `BedrockModel`, `boto3` clients, and DB pools at module scope, **except** when forwarding a caller's inbound user JWT (`context.request_headers`) to AgentCore Gateway — instantiate `MCPClient` **inside `@app.entrypoint` per request** so user tokens never leak across sessions:

```python
import os
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp, RequestContext

app = BedrockAgentCoreApp()

# Module-level singleton reused across the 15-minute warm pool
MODEL = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")
GATEWAY_URL = os.getenv("AGENTCORE_GATEWAY_MYGATEWAY_URL")

@app.entrypoint
def invoke(payload: dict, context: RequestContext):
    headers = getattr(context, "request_headers", {}) or {}
    user_auth = headers.get("authorization") or headers.get("Authorization")

    req_headers = {"MCP-Protocol-Version": "2026-07-28"}
    if user_auth:
        req_headers["Authorization"] = user_auth

    with MCPClient(lambda: streamablehttp_client(GATEWAY_URL, headers=req_headers)) as mcp:
        agent = Agent(model=MODEL, tools=mcp.list_tools_sync())
        return {"response": str(agent(payload["prompt"]))}
```

**Artifact Trade-Offs:**
- **CodeZip:** ~95 MB archive adds ~1.3s platform download/extract before Python import; prune dev/test dependencies and keep archives `< 100–200 MB`.
- **Container:** Image pull dominates cold start (~15s+ at 500 MB vs. a few seconds at 100 MB); use multi-stage slim/distroless builds and `.dockerignore`.
- **Lambda Gateway Targets:** Enable Lambda Provisioned Concurrency to eliminate downstream tool cold starts.

---

## 5. Session Lifecycle Configuration & Long-Running Background Tasks

Configure `lifecycleConfiguration` in `agentcore/agentcore.json` (or via `agentcore add agent ... --idle-timeout 120 --max-lifetime 3600`):

```json
{
  "runtimes": [
    {
      "name": "MyAgent",
      "lifecycleConfiguration": {
        "idleRuntimeSessionTimeout": 120,
        "maxLifetime": 3600
      }
    }
  ]
}
```

**Explicit Session Teardown (`StopRuntimeSession`):**

```python
client.stop_runtime_session(
    agentRuntimeArn=runtime_arn,
    runtimeSessionId=session_id,
)
```

**Async Background Tasks (`add_async_task` / `complete_async_task`):**
Prevents microVM reclamation at `idleRuntimeSessionTimeout` while work continues after `/invocations` returns (`maxLifetime`, default 8h / 28,800s, still applies as hard cap):

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload, context):
    task_id = app.add_async_task("background_work")
    start_background_work(task_id, payload)
    return {"status": "processing", "taskId": task_id}

def start_background_work(task_id, payload):
    try:
        do_the_work(payload)
    finally:
        app.complete_async_task(task_id)
```

---

## 6. Observability Retention, Eval Baseline & Rollback Commands

```bash
# Operator CLI reference: 30-day CloudWatch log retention
aws logs put-retention-policy \
  --log-group-name /aws/bedrock-agentcore/runtimes/<AGENT_ID>-DEFAULT \
  --retention-in-days 30

# Baseline & continuous online evaluation (5% sampling)
agentcore run eval --evaluator "Builtin.Helpfulness" --evaluator "Builtin.GoalSuccessRate"
agentcore add online-eval \
  --name production_monitor \
  --runtime <AgentName> \
  --evaluator "Builtin.Helpfulness" \
  --sampling-rate 5

# Preview diff, deploy, and safe rollback
agentcore validate
agentcore deploy --diff
agentcore deploy -y
```
