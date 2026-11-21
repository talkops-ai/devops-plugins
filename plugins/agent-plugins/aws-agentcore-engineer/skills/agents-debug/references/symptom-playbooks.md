# AgentCore Symptom Diagnostic Playbooks & Remediation Snippets

Detailed step-by-step diagnostic playbooks, operator CLI reference commands, IAM JSON policies, and Python code fixes referenced by `agents-debug`. Always query live AWS logs, traces, metrics, and runtime configuration via connected MCP tools (`cloudwatch`, `appsignals`, `cloudtrail`, `agentcore`, `aws-mcp`) in read-only mode, and present CLI commands as operator reference snippets.

---

## 1. "model access denied" or Model Error

1. **Model not enabled in Bedrock console:** Enable the model in AWS Console → Amazon Bedrock → Model access for the target region and wait 1–2 minutes for propagation.
2. **Execution role missing `bedrock:InvokeModel`:** Verify via `aws-mcp` (`iam:SimulatePrincipalPolicy`) or operator CLI:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn $(agentcore status --json | jq -r '.runtimes[0].executionRoleArn') \
  --action-names bedrock:InvokeModel \
  --resource-arns "arn:aws:bedrock:*::foundation-model/*"
```

3. **Cross-Region Inference Profile (CRIS) destination region access:**
   AgentCore CLI scaffolds `global.` by default (e.g., `global.anthropic.claude-sonnet-4-5-20250929-v1:0`). Model access must be enabled in **every destination region** covered by the prefix:

| Prefix | Geography | Example destination regions |
|---|---|---|
| `us.` | United States | `us-east-1`, `us-east-2`, `us-west-2` |
| `eu.` | Europe | `eu-central-1`, `eu-west-1`, `eu-west-2`, `eu-west-3` |
| `apac.` | Asia Pacific | `ap-northeast-1`, `ap-southeast-1`, `ap-southeast-2`, `ap-south-1` |
| `global.` | All commercial regions worldwide | All supported commercial regions (available for select models) |

---

## 2. Tool Call Failing & Gateway Auth Errors

### General Tool Call Triage

```bash
# Operator CLI reference (or inspect via cloudwatch / agentcore MCP tools)
agentcore traces get <traceId> --runtime <AgentName>
agentcore status --type gateway
agentcore fetch access --name <AgentName> --type agent
agentcore logs --runtime <AgentName> --since 1h --query "auth"
agentcore status --type credential
aws logs tail /aws/lambda/<function-name> --since 1h
agentcore logs --runtime <AgentName> --since 1h --query "policy"
agentcore status --type policy-engine
```

- **Local dev (`agentcore dev --local`):** `AGENTCORE_GATEWAY_*_URL` is only populated after `agentcore deploy`; guard with `if not GATEWAY_URL: tools = []`.
- **Gateway Outbound Auth Matrix Validation:**

| Target type | Valid outbound auth |
|---|---|
| `mcp-server` | `none`, `oauth` (2LO CLI / 3LO API), or IAM (`GATEWAY_IAM_ROLE` SigV4 via API; no `api-key`) |
| `lambda-function-arn` | IAM role auth (automatic) or `oauth` |
| `open-api-schema` | `oauth` or `api-key` (**required** — no `none`) |
| `api-gateway` | `none`, `api-key`, or IAM (`GATEWAY_IAM_ROLE`) |
| `smithy-model` | IAM or `oauth` |

- **Expired OAuth tokens (`401`/`403`):** Verify the OAuth credential provider's token endpoint is reachable and client credentials remain valid.

---

## 3. Wrong or Unhelpful Answers

Inspect the trace (`agentcore traces get <traceId> --runtime <AgentName>` or `cloudwatch` spans) for:
1. Whether the right tools were selected (improve tool descriptions if skipped).
2. Unexpected tool output formats or silent error payloads.
3. Missing system prompt instructions or undersized model IDs for complex reasoning.
4. Missing memory context (see Section 4 below).

---

## 4. Memory Not Working (LTM & Session Loading)

```bash
# Operator CLI reference (or inspect via agentcore MCP get_memory / list_memories)
agentcore status --type memory --json | jq '.memories[].strategies'
agentcore status --type memory
agentcore status --type memory --json | jq '.memories[].id'
```

- **LTM not persisting across sessions:**
  1. Confirm LTM strategies (`SEMANTIC` or `USER_PREFERENCE`) are configured and memory status is `ACTIVE`.
  2. Wait **5–30 seconds** after session completion — LTM fact extraction is asynchronous.
  3. **Session ID length >= 33 characters:** Use UUID v4 session IDs. Short IDs like `"session-1"` cause LTM extraction to fail silently.
- **Memory not loading at session start:**
  1. Confirm `MEMORY_*_ID` env var is populated.
  2. Confirm `actor_id` is identical across sessions (memory is actor-scoped).
  3. Confirm retrieval namespace paths match write namespaces.

---

## 5. Agent Timeout & `424 Failed Dependency`

### Timeout Causes
- **Cold-start / slow initialization:** Heavy module-level imports, synchronous DB connections, or startup MCP client handshakes. Move slow setup to lazy initialization or warm-pool singletons (`agents-harden`).
- **Model / tool / memory latency:** Use faster models (e.g., Haiku) for latency-critical steps, inspect downstream Lambda/API logs, reduce semantic memory `top_k`, and verify VPC SG/route/NAT rules (`references/vpc.md`).

### `424 Failed Dependency` on Invoke
Container failed to start or crashed during initialization (`agentcore logs --runtime <AgentName> --since 30m --level error`):
1. Missing Python package in `pyproject.toml`.
2. Unhandled import-time exception in `main.py` or `app.run()`.
3. Container image missing in ECR or execution role missing `ecr:BatchGetImage`.
4. Memory resource still in `CREATING` state when entrypoint assumes `ACTIVE`.
5. Startup exceeded the runtime health-check window on first invoke.

---

## 6. `ServiceQuotaExceededException: maxVms limit exceeded`

CloudWatch concurrent-sessions counts active invocations, whereas `maxVms` counts **all live microVMs**, including idle environments waiting for `idleRuntimeSessionTimeout` (default **900s / 15 min**) to expire. Generating a new session ID per request without stopping sessions exhausts `maxVms` rapidly.

**Mandatory mitigation order (before requesting a quota increase):**
1. **Call `StopRuntimeSession` when a logical session completes:**
   ```python
   client.stop_runtime_session(
       agentRuntimeArn=runtime_arn,
       runtimeSessionId=session_id,
   )
   ```
2. **Reuse `runtimeSessionId`** across turns in the same conversation or batch job.
3. **Lower `idleRuntimeSessionTimeout`** (e.g., `60–120s` for request/reply workloads) in `agentcore/agentcore.json` (`lifecycleConfiguration`) and deploy.
4. **Request a quota increase** via AWS Service Quotas (`Amazon Bedrock AgentCore`) — see `references/limits.md`.

---

## 7. Local Invocations Fail with `Connection refused` / Curl Exit Code 7

`agentcore dev` default ports: **HTTP `8080`**, **MCP `8000`**, **A2A `9000`**. When occupied, the CLI silently auto-increments (`8080 → 8081 → 8082`).

```bash
# Check bound port in dev logs or active listeners (operator local check)
tail -20 agentcore/.cli/logs/dev/*.log
lsof -iTCP -sTCP:LISTEN -n -P | grep -E '8080|8081|8082|8000|9000'

# Fix: pin port explicitly or terminate stale listener
agentcore dev --port 8080
```

---

## 8. Missing CloudWatch Logs or Traces (Docker & Terraform/CDK IaC)

- **Trace visibility delay:** Wait **~10–15 seconds** end-to-end; verify **CloudWatch Transaction Search** (`xray:GetTraceSegmentDestination` = `CloudWatchLogs` / `ACTIVE`) is enabled.
- **Container / Docker builds MUST wrap `CMD` with `opentelemetry-instrument`:**
  ```dockerfile
  # Correct
  CMD ["opentelemetry-instrument", "python", "main.py"]
  ```
- **Use Python `logging`, NOT `print()`:** AgentCore ships OTEL-captured `logging` records, not raw stdout `print()`.
  ```python
  import logging
  logger = logging.getLogger(__name__)
  logger.setLevel(logging.INFO)
  logger.info("Processing request")  # Appears in CloudWatch (print() does NOT)
  ```
- **Terraform / CDK / Custom IAM Role Scoping Fix:** `logs:DescribeLogGroups` **must** use `"Resource": "*"` (scoping it narrowly breaks log stream creation), while `CreateLogGroup`/`CreateLogStream`/`PutLogEvents` scope to the runtime log group and X-Ray actions use `"*"`:
  ```json
  [
    {
      "Effect": "Allow",
      "Action": ["logs:DescribeLogGroups", "xray:PutTelemetryRecords", "xray:PutTraceSegments"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:<REGION>:<ACCOUNT_ID>:log-group:/aws/bedrock-agentcore/runtimes/*:*"
    }
  ]
  ```

---

## 9. Streaming Connection Drops Mid-Response (`RemoteProtocolError` / `IncompleteRead`)

During multi-tool turns with several minutes of silence on the stream, upstream load balancers close idle TCP streams. Emit periodic **~30-second SSE heartbeats** while tools run:

```python
import asyncio
import json
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

async def emit_keepalive(tool_task):
    """Yield heartbeat events every 30s while tool_task is running."""
    while not tool_task.done():
        yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        try:
            await asyncio.wait_for(asyncio.shield(tool_task), timeout=30)
        except asyncio.TimeoutError:
            continue

@app.entrypoint
async def invoke(payload, context):
    async def stream():
        tool_task = asyncio.create_task(run_long_tool(payload))
        async for event in emit_keepalive(tool_task):
            yield event
        result = await tool_task
        yield f"data: {json.dumps({'type': 'result', 'content': result})}\n\n"
        yield "data: [DONE]\n\n"
    return stream()
```

Filter `{"type": "heartbeat"}` chunks on the client before rendering. For fire-and-forget work, use `app.add_async_task` / `app.complete_async_task` instead.

---

## 10. Traces Merged Across Concurrent Invocations

1. **Upstream caller sending `Sampled=0`:**
   - **Lambda caller:** Enable Active Tracing (`--tracing-config Mode=Active`).
   - **ECS / EC2 / container caller:** `from aws_xray_sdk.core import patch_all; patch_all()`.
   - **Direct SDK caller without X-Ray:** Set `OTEL_TRACES_SAMPLER=always_on` on the runtime environment (forces 100% sampling at higher trace volume).
2. **Endpoint ARN vs. Runtime ARN trap:**
   - Invoke `arn:aws:bedrock-agentcore:<region>:<account>:runtime/<runtime-name>` (full child spans), **NOT** `.../runtime/<runtime-name>/runtime-endpoint/DEFAULT` (which can emit only a single top-level `AgentCore.Runtime.Invoke` span).

---

## 11. Runtime Stuck in `DELETING` (> 30 Minutes)

Deleting the default endpoint directly fails with `ConflictException: Default endpoints are removed when you delete the agent.` Retrying `DeleteAgentRuntime` will not unstick a backend workflow stalled > 30 minutes:
1. Stop retrying `DeleteAgentRuntime`.
2. Open an AWS Support case including Account ID, Region, `agentRuntimeArn`/`agentRuntimeId`, CloudTrail `requestId` + timestamp of `DeleteAgentRuntime`, and stuck duration (request cleanup of any orphaned ENIs / workload identities).
3. Unblock delivery immediately by deploying a new runtime under a fresh name.

---

## 12. Framework-Specific Issues & Trace Structure

- **LangGraph (`langchain-aws`):** Older `langchain-aws` versions rejected geographic/global CRIS prefixes (`us.`, `eu.`, `apac.`, `global.`). Check `pip show langchain-aws`; upgrade or test non-prefixed `anthropic.claude-sonnet-4-5-20250929-v1:0` with `model_provider="bedrock_converse"`.
- **Google ADK:** Supports `gemini-*` models only (verify `GEMINI_API_KEY` via credential provider).
- **A2A agents:** Must listen on port **`9000`** (not `8080`).
- **Trace inspection structure:** Inspect **Model invocations**, **Tool calls**, **Memory operations**, **Policy decisions**, and **Latency breakdown** (`agentcore traces get <traceId> --runtime <AgentName> --output trace.json`).
