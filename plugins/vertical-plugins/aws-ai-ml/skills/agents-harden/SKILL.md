---
name: agents-harden
description: >
  Use when preparing your agent for production — IAM scoping, inbound
  auth (JWT, SigV4), secrets management, cold start optimization, session
  lifecycle, rate limiting, input validation, and quota guidance. Triggers
  on: "production checklist", "harden agent", "production ready", "secure
  agent", "inbound auth", "going live", "cold start optimization", "session
  lifecycle", "StopRuntimeSession", "quota", "throttling", "maxVms",
  "rate limit", "security audit of outbound API calls", "gateway target
  audit for production", "restrict who can call", "lock down endpoint",
  "only our app can call".
  Not for Cedar tool-restriction policies — use agents-connect. Not
  for quality measurement — use agents-optimize. Not for outbound
  credential storage or API key wiring — use agents-connect. Not for
  A2A agent-to-agent auth — use agents-build. Cold start observation
  and diagnosis (not optimization) routes to agents-debug.
allowed-tools: Read Grep Glob Bash
metadata:
  type: skill
  version: "1.0.0"
  author: aws-agentcore
  requires-cli: ">=0.9.0"
---

# harden

Prepare your AgentCore agent for production — security, reliability, and performance.

## When to use

- Taking an AgentCore agent to production or running a pre-launch readiness audit
- Restricting inbound callers (`AWS_IAM` SigV4, `CUSTOM_JWT`, or `PutAgentRuntimeResourcePolicy`)
- Scoping IAM execution roles, isolating `InvokeAgentRuntimeCommand`, or configuring KMS CMKs
- Auditing secrets, indirect prompt injection boundaries, or direct outbound HTTP calls
- Optimizing cold starts, tuning session lifecycle (`idleRuntimeSessionTimeout`, `maxLifetime`, `StopRuntimeSession`), protecting background tasks (`add_async_task`), or resolving `maxVms` / throttling quotas

**Progressive-disclosure references (load on demand):**
- Copy-paste IAM policies, JWT `403` playbook, warm-pool singleton + per-request `MCPClient` code, `lifecycleConfiguration`, and `add_async_task` implementations → [`references/hardening-checklist-details.md`](references/hardening-checklist-details.md)
- Service quotas, `maxVms` mitigations, and quota-increase justification template → [`references/limits.md`](references/limits.md)
- VPC subnet, NAT/endpoint, and multi-AZ configuration → [`references/vpc.md`](references/vpc.md)
- App-to-runtime invocation & `InvokeAgentRuntimeCommand` integration → [`references/integrate.md`](references/integrate.md)

## MCP-Only Execution & Read-Only Safety

- **MCP-Only Live Discovery & Docs:** Execute **all** live AWS discovery, AgentCore runtime/gateway/memory inspection, telemetry/log/trace queries, IAM policy checks, and documentation lookups **exclusively via connected MCP tools**: `aws-mcp` (`aws___run_script` using read-only `await call_boto3(...)`, `aws___search_documentation`, `aws___read_documentation`), `agentcore` (`search_agentcore_docs`, `fetch_agentcore_doc`, `list_agent_runtimes`, `get_agent_runtime`, etc.), `strands-agents` (`search_docs`, `fetch_doc`, `find_integrations`), `cloudwatch`, `appsignals`, `cloudtrail`, `awspricing`, `awsiac`, and `awsknowledge`.
- **Zero Raw CLI Execution, Strictly Read-Only & Secret-Safe:** **Never** run raw `aws ...` or `agentcore ...` CLI commands in Bash/`run_command` to query or mutate live AWS accounts (present CLI commands in Markdown strictly as operator reference snippets). **Never** invoke live mutations (`create_*`, `update_*`, `delete_*`, `InvokeAgentRuntime`, `InvokeModel`) — refuse unapproved destructive/mutating requests and explain the safe, approval-gated operator workflow with verification and rollback steps. **Never** read or print plaintext secrets (`secretsmanager:GetSecretValue`, `ssm:GetParameter` with `WithDecryption=True`, `.env` / `.env.local` values, or raw memory record contents).
- **Edge-Case Documentation Fallback:** For unmapped AWS/AgentCore/Bedrock edge cases (e.g., `PutAgentRuntimeResourcePolicy` schema), run 1–2 focused queries via `agentcore`, `strands-agents`, `awsknowledge`, or `aws-mcp` documentation search tools.

## Process

1. **Inspect project & live posture (read-only):** Read `agentcore/agentcore.json` (requires CLI `>= 0.9.0` for operator workflows; never read `.env` / `.env.local`) and inspect live runtime/gateway/memory/IAM configuration via `agentcore` and `aws-mcp` read-only tools.
2. **Audit each hardening pillar below** and load [`references/hardening-checklist-details.md`](references/hardening-checklist-details.md) whenever emitting IAM JSON policies, `agentcore.json` blocks, or Python code fixes.
3. **Deliver a project-specific Production Readiness Checklist** with copy-paste remediation, verification (`agentcore validate`, `agentcore deploy --diff`), and rollback guidance.

---

## 1. IAM Least Privilege, Shell Access & KMS CMK Encryption

- **Scope Execution Role:** Replace scaffolded `arn:aws:bedrock:*::foundation-model/*` with exact foundation-model / inference-profile ARNs (`bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`), scope ECR pull (`ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer`) to `bedrock-agentcore-<AGENT_NAME>-*`, and lock `sts:AssumeRole` trust to `bedrock-agentcore.amazonaws.com` with `aws:SourceAccount` and `aws:SourceArn` conditions. Use `PutAgentRuntimeResourcePolicy` (API-only) for fine-grained resource policies.
- **Isolate `InvokeAgentRuntimeCommand`:** Grants arbitrary shell execution inside a live microVM with the runtime's execution role. Keep in a **separate IAM policy** from `InvokeAgentRuntime`, alert on every call via CloudTrail + EventBridge, and reject shell metacharacters (`&&`, `;`, `$(...)`, backticks, `|`) on any caller input.
- **Customer-Managed KMS Keys (`encryptionKeyArn`) & Prompt Injection Defense:** For regulated workloads (HIPAA, PCI-DSS, SOC2, FedRAMP), configure KMS CMK (`encryptionKeyArn`) on **AgentCore Memory** and **Identity Token Vault** scoped via `kms:ViaService` + `aws:SourceAccount`. Wrap retrieved LTM records in `<retrieved_memory_untrusted>...</retrieved_memory_untrusted>` tags and enforce **Cedar Policy Engine in `ENFORCE` mode** at the Gateway edge.

---

## 2. Inbound Authentication (`AWS_IAM` vs. `CUSTOM_JWT`)

> [!WARNING]
> Never use `--authorizer-type NONE` in production — anyone with the endpoint URL can invoke the agent unauthenticated. Always enforce `AWS_IAM` (SigV4) or `CUSTOM_JWT`.

- **`allowedAudience` vs. `allowedClients`:** Inspect a decoded IdP token: if `aud` is present (or both `aud` and `client_id`), configure **`allowedAudience`**; if only `client_id` is present, configure **`allowedClients`**. Picking the wrong field causes `403` on valid tokens.
- **RFC 8414 §3 Issuer Prefix Rule:** `issuer` in `.well-known/openid-configuration` must be a URL prefix of the discovery URL. Align the IdP discovery domain with `iss` (or front with an S3/CloudFront OIDC shim).
- **`403` Triage:** `Authorization method mismatch` means SigV4 headers (`X-Amz-Date`, `X-Amz-Security-Token`, `Authorization: AWS4-HMAC-SHA256`) were sent to a `CUSTOM_JWT` runtime (or Bearer token sent to `AWS_IAM`). `Invalid inbound token` checks in order: (1) `iss` prefix, (2) `allowedAudience`/`allowedClients`, (3) public `jwks_uri`, (4) `exp`, (5) `RS256` algorithm compatibility.

---

## 3. Secrets, Input Validation & Outbound Tool Surface Audit

- **Secrets & Runtime Env Vars:** Audit `app/**/*.py` (never `.env`) for hardcoded keys (`sk-`, `api_key=`, `password=`) and secret-like `os.getenv`/`os.environ` reads (`TOKEN|SECRET|KEY|PASSWORD|CREDENTIAL`; platform vars `MEMORY_*_ID`, `AGENTCORE_GATEWAY_*_URL`, `AWS_REGION` are safe). AgentCore Runtime env vars are **not** vault-backed — register secrets via `agentcore add credential` and inject at call time with `@requires_api_key` / `@requires_access_token` (gitignored `agentcore/.env.local` is local-only).
- **Error Handling, Input Validation & Rate Limiting:** Catch exceptions internally (`app.logger.error(..., exc_info=True)`) without leaking stack traces; validate required fields, types, IDs (`actor_id`, `session_id`), and prompt length (e.g., `<= 10,000` chars). Runtime enforces 25 TPS default per agent ([`references/limits.md`](references/limits.md)); enforce per-user/per-tenant rate limits at API Gateway or the calling app.
- **Audit Direct Outbound HTTP (`httpx.` / `requests.` / `aiohttp.` in `app/`):**

| Hit looks like | Production Action |
|---|---|
| External REST API treated as an agent tool | Convert to Gateway target (`open-api-schema` or `api-gateway`) via `agents-connect` Path C |
| External MCP server called directly | Convert to Gateway target (`mcp-server`) via `agents-connect` Path A |
| AWS service (S3, DynamoDB, SQS) called via raw HTTP | Replace with `boto3` using the runtime's IAM execution role (no stored secret) |
| Streaming/bidirectional service (`SSE`, `WebSocket`, `WebRTC`) | Keep direct; verify auth uses `@requires_*` (never `os.getenv`) |
| Agent-to-agent `A2A` call | Keep direct; verify bearer auth uses `@requires_access_token` |
| Measured latency hot path accepted by team | Keep direct only with benchmark evidence + `@requires_*` auth |

---

## 4. Cold Start, Warm-Pool Singletons & Session Lifecycle

- **Cold Start (~20–30s typical: image pull + app init + sub-second microVM):** Keep artifacts **< 200 MB** (target **< 100 MB**; ~95 MB CodeZip adds ~1.3s download; 500 MB Container adds 15s+ pull — use multi-stage slim builds + `.dockerignore`). Reuse `session_id` across conversation turns/batches, fire a **frontend warm-up ping** (`{"action": "warmup"}`) on chat open, choose **Elastic Memory Reclamation vs. Committed Baseline** pricing, and enable **Provisioned Concurrency** on Gateway Lambda targets. **Never** send both `runtimeSessionId` and `mcpSessionId` on the same MCP request (binds two VMs).
- **15-Minute Warm-Pool Singletons vs. Per-Request `MCPClient`:** Initialize `BedrockModel`, `boto3` clients, and DB pools at module scope for warm reuse, **except** instantiate `MCPClient` **inside `@app.entrypoint` per request** whenever forwarding caller `Authorization` headers (`context.request_headers` + `MCP-Protocol-Version: 2026-07-28`) so user JWTs never leak across sessions (see [`references/hardening-checklist-details.md`](references/hardening-checklist-details.md)).
- **Session Lifecycle (`idleRuntimeSessionTimeout` default `900s`, `maxLifetime` default `8h` / `28800s`):** Idle VMs charge `$0` for CPU during I/O wait, **but continue consuming `maxVms` concurrency quota AND accruing peak memory GB-second billing** until `idleRuntimeSessionTimeout` expires — call `StopRuntimeSession` immediately when a chat/job ends to reclaim `maxVms` capacity and stop idle memory billing right away.

| Workload | `idleRuntimeSessionTimeout` | `maxLifetime` | Reasoning |
|---|---|---|---|
| Interactive chat / support agent | `600–900s` (default) | `3600–7200s` | Users pause between turns; reclaim once conversation ends |
| Stateless request/reply API | `60–120s` | `1800s` | Self-contained single call — release microVM fast |
| Batch processing (1 session/job) | `120s` | Job duration + buffer | Small inter-item gap; reclaim quickly between jobs |
| Long-running background tasks (`add_async_task`) | `120–300s` | Up to `28800s` (8h) | `app.add_async_task` / `app.complete_async_task` prevents idle reclaim during active work |

- **`maxVms` Quota Mitigation Order:** (1) Call `StopRuntimeSession` when done → (2) reuse `session_id` across related turns → (3) lower `idleRuntimeSessionTimeout` in `agentcore/agentcore.json` (`lifecycleConfiguration`) → (4) request quota increase via Service Quotas ([`references/limits.md`](references/limits.md)).
- **Observability, Evals & VPC:** Verify X-Ray tracing, set CloudWatch log retention (e.g., 30 days on `/aws/bedrock-agentcore/runtimes/<AGENT_ID>-DEFAULT`), establish Two-Tier eval baselines (`Builtin.Helpfulness`, `Builtin.GoalSuccessRate` + `online-eval` ~5% sampling), and place private-data agents in multi-AZ VPCs ([`references/vpc.md`](references/vpc.md)).

---

## Production Checklist Summary

```
Production Readiness Checklist for <AgentName>
- IAM & KMS: Scoped Bedrock model & ECR ARNs; account-scoped trust policy; KMS CMK (encryptionKeyArn) on Memory & Identity Token Vault; InvokeAgentRuntimeCommand isolated + CloudTrail EventBridge alert.
- Inbound Auth & Zero-Trust: AWS_IAM or CUSTOM_JWT (never NONE); allowedAudience/allowedClients + RFC 8414 issuer prefix verified; Two-Step OBO (if user-delegated); <retrieved_memory_untrusted> tags; Cedar Policy Engine in ENFORCE mode.
- Code & Secrets: Graceful error handling (no leaked tracebacks); payload type/length validation; zero hardcoded or runtime-env secrets (@requires_api_key / @requires_access_token used); direct HTTP audited for Gateway conversion.
- Performance & Lifecycle: Package < 200 MB (< 100 MB target); module-level BedrockModel/DB singletons + per-request MCPClient for user JWTs; session_id reuse; StopRuntimeSession + tuned idleRuntimeSessionTimeout/maxLifetime; add_async_task/complete_async_task for background work.
- Observability & Testing: X-Ray active; CloudWatch log retention set; Two-Tier eval baseline + online-eval configured; OTEL_SDK_DISABLED=true pytest + cross-session LTM tests passing.
```

## Output

- Project-specific hardening findings mapped to the checklist above
- Copy-paste IAM policies, `agentcore.json` lifecycle config, and Python/CLI fixes (from [`references/hardening-checklist-details.md`](references/hardening-checklist-details.md)), with verification (`agentcore validate`, `agentcore deploy --diff`) and safe rollback steps
