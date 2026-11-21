---
name: agents-debug
description: >
  Use when your agent or environment is broken — wrong answers, errors,
  timeouts, tool failures, or CLI issues. Reads traces and logs to
  diagnose root causes. Also checks prerequisites when the CLI itself
  isn't working. Triggers on: "agent not working", "wrong answer",
  "agent error", "tool call failing", "debug agent", "check logs",
  "read traces", "broken", "500 error", "424 error", "model access
  denied", "command not found", "stuck in DELETING", "maxVms exceeded",
  "cold start diagnosis", "cold start slow", "agentcore create error",
  "create failed", "exit code 7", "connection refused local dev".
  Not for deploy failures — use agents-deploy. Not for performance
  tuning without errors — use agents-optimize. Not for VPC
  configuration — use agents-build. Not for observability setup or
  missing logs — use agents-optimize.
allowed-tools: Read Grep Glob Bash
metadata:
  type: skill
  version: "1.0.0"
  author: aws-agentcore
  requires-cli: ">=0.9.0"
---

# debug

Diagnose why your AgentCore agent or environment isn't working correctly.

## When to use

- Your agent is returning wrong answers, `500` / `424` errors, or `AccessDenied` / `ServiceQuotaExceededException`
- Tool calls, Gateway targets, Cedar policy checks, or Memory recall are failing or timing out
- Agent works locally (`agentcore dev`) but fails after deploying (or vice versa)
- Logs or traces aren't appearing in CloudWatch, or concurrent traces appear merged
- `agentcore` CLI command not found or local prerequisites are broken

Do NOT use for:
- Deploy failures (CDK errors, IAM during deploy) → use `agents-deploy`
- Scaffolding a new project → use `agents-get-started`
- Measuring quality or setting up monitoring from scratch → use `agents-optimize`

## MCP-Only Execution & Read-Only Safety

- **MCP-Only Live Discovery & Docs:** Execute **all** live AWS discovery, AgentCore runtime/gateway/memory inspection, telemetry/log/trace queries, IAM policy simulations, and documentation lookups **exclusively via connected MCP tools**: `aws-mcp` (`aws___run_script` using read-only `await call_boto3(...)`, `aws___search_documentation`, `aws___read_documentation`), `agentcore` (`search_agentcore_docs`, `fetch_agentcore_doc`, `list_agent_runtimes`, `get_agent_runtime`, etc.), `strands-agents` (`search_docs`, `fetch_doc`, `find_integrations`), `cloudwatch`, `appsignals`, `cloudtrail`, `awspricing`, `awsiac`, and `awsknowledge`.
- **Zero Raw CLI Execution, Strictly Read-Only & Secret-Safe:** **Never** run raw `aws ...` or `agentcore ...` CLI commands in Bash/`run_command` to query or mutate live AWS accounts (present CLI commands in Markdown strictly as operator reference snippets). **Never** invoke live mutations (`create_*`, `update_*`, `delete_*`, `InvokeAgentRuntime`, `InvokeModel`) — refuse unapproved destructive/mutating requests and provide the safe, approval-gated operator workflow with verification and rollback guidance. **Never** read or print plaintext secrets (`secretsmanager:GetSecretValue`, `ssm:GetParameter` with `WithDecryption=True`, `.env` / `.env.local` values, or raw memory record contents).
- **Edge-Case Documentation Fallback:** For unmapped AWS/AgentCore/Bedrock error codes or SDK quirks, run 1–2 focused queries via `agentcore`, `strands-agents`, `awsknowledge`, or `aws-mcp` documentation search tools.

## Input

`$ARGUMENTS` is optional:

```
/agents-debug                      # interactive — describe what's wrong
/agents-debug traces               # read and explain recent traces
/agents-debug logs                 # search recent logs for errors
/agents-debug memory               # diagnose memory recall issues specifically
/agents-debug doctor               # check environment prerequisites
```

## Process

### Step 0: Route by problem type

- **Local CLI / prerequisite failure** (`command not found`, Node/Python/uv/credentials setup) → Load [`references/doctor.md`](references/doctor.md).
- **Live production incident, SLO breach, CloudWatch alarm, Gateway `-32022` protocol error, Cedar `DENY` spike, or LTM Dead-Letter Queue (DLQ) lag** → Load [`references/aiops-runbooks.md`](references/aiops-runbooks.md) to correlate across `cloudwatch`, `appsignals`, `cloudtrail`, and `agentcore` MCP servers.
- **Agent runtime / tool / memory / streaming / observability symptom** → Continue to Step 1 and load [`references/symptom-playbooks.md`](references/symptom-playbooks.md) for detailed remediation code and IAM snippets.

### Step 1: Check project context & CLI version

Read `agentcore/agentcore.json` (if present) to identify `<AgentName>`, framework, gateways, and memory resources (never read `.env` or `agentcore/.env.local`). Note that AgentCore CLI workflows require `v0.9.0+` (`agentcore --version` / `agentcore update`).

### Step 2: Classify the symptom

Identify whether the failure is: (1) explicit error (`401`/`403`/`424`/`500`/quota/model access), (2) wrong or unhelpful output, (3) tool/Gateway failure, (4) Memory recall/persistence issue, (5) timeout or mid-stream disconnect, or (6) missing/merged logs & traces.

### Step 3: Query traces and logs via MCP

Query `/aws/bedrock-agentcore/runtimes/*` log groups, X-Ray/CloudWatch spans, and runtime/gateway/memory status directly via `cloudwatch`, `appsignals`, `agentcore`, and `aws-mcp` tools rather than asking the user to paste logs. For operator CLI reference:

```bash
agentcore traces list --runtime <AgentName> --since 1h --limit 5
agentcore traces get <traceId> --runtime <AgentName>
agentcore logs --runtime <AgentName> --since 1h --level error
```

**Ingestion Latency Fact:** CloudWatch put-to-get latency is **~10 seconds end-to-end** for **both** trace reads and eval queries — there is no separate 2–5 minute eval indexing window. If just invoked, wait ~15 seconds.

---

### Step 4: Diagnose by Symptom (Load [`references/symptom-playbooks.md`](references/symptom-playbooks.md))

Use the rapid triage table below to pinpoint the root cause, and **load [`references/symptom-playbooks.md`](references/symptom-playbooks.md)** when generating code fixes, Dockerfile/IAM JSON snippets, or full diagnostic steps:

| Symptom | Primary Root Causes & Exact Thresholds / Rules | Key Fix Summary |
|---|---|---|
| **`model access denied` / model `ValidationException`** | (1) Model not enabled in Bedrock console; (2) Execution role missing `bedrock:InvokeModel`; (3) Cross-region inference profile (`us.`, `eu.`, `apac.`, `global.`) missing model access in **every** destination region covered by the prefix | Enable model across all profile destination regions; verify execution role via `iam:SimulatePrincipalPolicy` |
| **Tool call / Gateway auth error (`401` / `403`)** | (1) `AGENTCORE_GATEWAY_*_URL` unset in local dev; (2) Invalid target×auth combo (`mcp-server` supports `none`/`oauth`/IAM SigV4 only — **no `api-key`**; `open-api-schema` **requires** `oauth` or `api-key`; `api-gateway` supports `none`/`api-key`/IAM); (3) Expired OAuth token, Lambda failure, or Cedar `DENY` | Guard `if not GATEWAY_URL:` locally; align target outbound auth; inspect Lambda & Cedar policy logs |
| **Wrong or unhelpful answers** | Vague system prompt, poor tool descriptions causing skipped/wrong tool selection, unexpected tool output schema, or undersized model | Inspect trace reasoning steps (`modelInvocationOutput`, tool I/O, memory spans) and refine prompt/tool schemas |
| **Memory (LTM / STM) not working** | (1) LTM requires `SEMANTIC` or `USER_PREFERENCE` strategy + `ACTIVE` status; (2) Async LTM extraction takes **5–30s** after session ends; (3) Session IDs **must be >= 33 chars** (UUID v4 — short IDs like `"session-1"` fail silently); (4) Mismatched `actor_id` or retrieval namespace | Use UUID v4 (`>=33` chars), wait 5–30s post-session, verify `MEMORY_*_ID`, consistent `actor_id`, and matching namespaces |
| **Agent timeout** | Module-level heavy imports/DB/MCP init on cold start, slow model/tool call, large memory `top_k`, or blocked VPC egress/SG | Move init to warm-pool singletons/lazy load, lower `top_k`, use faster model, or audit VPC ([`references/vpc.md`](references/vpc.md)) |
| **`ServiceQuotaExceededException: maxVms limit exceeded`** | `maxVms` counts active **plus idle** microVMs awaiting `idleRuntimeSessionTimeout` (default **900s / 15m**), not just CloudWatch concurrent sessions | Fix in strict order: (1) call `StopRuntimeSession` when done → (2) reuse `runtimeSessionId` → (3) lower `idleRuntimeSessionTimeout` → (4) Service Quotas ([`references/limits.md`](references/limits.md)) |
| **`424 Failed Dependency` on invoke** | Container crashed/timed out on startup: missing `pyproject.toml` dependency, `main.py` import crash, missing `ecr:BatchGetImage`, memory still `CREATING`, or init exceeding health-check window | Inspect startup error logs; fix dependency/IAM/lazy init |
| **Local dev `Connection refused` / exit code `7`** | `agentcore dev` defaults (**HTTP `8080`**, **MCP `8000`**, **A2A `9000`**) silently auto-increment (`8080 → 8081 → 8082`) when occupied | Check `agentcore/.cli/logs/dev/*.log` / `lsof`, or pin `agentcore dev --port 8080` |
| **No CloudWatch logs or traces** | (1) Docker `CMD` missing `opentelemetry-instrument`; (2) Using `print()` instead of Python `logging`; (3) Terraform/CDK IAM role scoping `logs:DescribeLogGroups` instead of `"Resource": "*"`; (4) CloudWatch **Transaction Search** (`CloudWatchLogs`/`ACTIVE`) disabled | Wrap `CMD ["opentelemetry-instrument", "python", "main.py"]`, use `logging`, set `logs:DescribeLogGroups` on `"*"`, enable Transaction Search |
| **Streaming drops mid-response (`RemoteProtocolError` / `IncompleteRead`)** | Upstream LB closes SSE/streaming TCP connections idle for several minutes during multi-tool execution | Emit SSE heartbeat (`data: {"type": "heartbeat"}\n\n`) every **~30s** while tools execute, or use `add_async_task` / `complete_async_task` |
| **Concurrent traces merged or missing child spans** | (1) Caller sends `Sampled=0` (X-Ray Active Tracing off); (2) Caller invokes endpoint ARN (`.../runtime-endpoint/DEFAULT`) instead of runtime ARN (`...:runtime/<name>`) | Enable Lambda `Mode=Active` / `aws_xray_sdk.core.patch_all()` or runtime `OTEL_TRACES_SAMPLER=always_on`; invoke the **runtime ARN** |
| **Runtime stuck in `DELETING` (> 30 min)** | Backend deletion workflow stalled (`ConflictException` if deleting DEFAULT endpoint directly) | Do **not** retry `DeleteAgentRuntime`; open AWS Support case (Account, Region, Runtime ARN, CloudTrail `requestId`+timestamp); deploy under a new runtime name |
| **Framework-specific errors** | Old `langchain-aws` rejecting CRIS prefix; Google ADK used with non-`gemini-*` model; A2A server bound to `8080` instead of **`9000`** | Upgrade `langchain-aws`, set `gemini-*` + `GEMINI_API_KEY` for ADK, bind A2A to port `9000` |

---

## Output

- Root-cause diagnosis backed by observed MCP trace/log/configuration evidence (including AIOps Golden Signal thresholds from [`references/aiops-runbooks.md`](references/aiops-runbooks.md) during incident triage — `SystemErrorRate > 1%` critical / `> 0.5%` warn, `ThrottleRate > 5%` critical / `> 2%` warn, `Latency p99 > 25s` / `p95 > 12s`, `Token Anomaly > 4x` loop / `> 2x` warn, and `PolicyDenyCount > 20%` critical / `> 5%` warn — even when reporting an empty region)
- Copy-paste-ready code fixes, IAM policy adjustments, or operator CLI commands — plus verification and safe rollback guidance (e.g., `agentcore deploy --diff`, `agentcore deploy` to revert config, or endpoint version rollback)
- Clear explanation of trace spans (`Model invocations`, `Tool calls`, `Memory operations`, `Policy decisions`, `Latency breakdown`)

## After diagnosis — handoff

| Root cause | Hand off to | Detail |
|---|---|---|
| Memory misconfigured (wrong strategy, namespace, wiring) | `agents-build` | [`references/memory.md`](references/memory.md) |
| Agent invocation from app not working (auth, URL, streaming, cross-account) | `agents-build` | [`references/integrate.md`](references/integrate.md) |
| VPC connectivity (can't reach RDS, no internet, AZ error) | `agents-build` | [`references/vpc.md`](references/vpc.md) |
| Multi-agent delegation not working | `agents-build` | [`references/multi-agent.md`](references/multi-agent.md) |
| Custom request headers not reaching agent code | `agents-build` | [`references/request-headers.md`](references/request-headers.md) |
| Gateway auth / target type misconfigured | `agents-connect` | Gateway Auth Matrix & target selection |
| Cedar policy denying unexpectedly | `agents-connect` | [`references/policy.md`](references/policy.md) |
| Observability not set up (no logs, no traces, dashboards) | `agents-optimize` / `agentcore-observability-setup` | [`references/observability.md`](references/observability.md) |
| Cold start optimization, session lifecycle (`maxVms`), `add_async_task`, or JWT `403` hardening | `agents-harden` | Production hardening & [`references/limits.md`](references/limits.md) |
| Deploy artifact stale or version rollback needed | `agents-deploy` | Redeploy / rollback workflow |
| Local CLI / prerequisite environment broken | Self-contained | [`references/doctor.md`](references/doctor.md) |
