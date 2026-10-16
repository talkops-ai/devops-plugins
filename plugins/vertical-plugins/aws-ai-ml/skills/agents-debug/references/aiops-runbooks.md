# AIOps Day-2 Incident Triage & Multi-Signal Correlation Runbooks

Use these operational runbooks to monitor, triage, and remediate live production incidents on Amazon Bedrock AgentCore using the bound `cloudwatch`, `appsignals`, `cloudtrail`, `agentcore`, and `aws-mcp` MCP servers.

---

## 1. Golden Signals & SLO Alerting Matrix (`AWS/Bedrock-AgentCore`)

Monitor these golden signals across Runtime, Gateway, Memory, and Policy Engine resources:

| Signal | Metric / Span Attribute | Warning Threshold | Critical / Rollback Threshold | Primary Triage Action |
| :--- | :--- | :--- | :--- | :--- |
| **System Error Rate** | `SystemErrorRate` / `5xx` | `> 0.5%` (5m) | `> 1.0%` (5m) | Immediate canary rollback (`update-agent-runtime-endpoint` to `V(N-1)`). |
| **Throttle Rate** | `ThrottleRate` / `ThrottledRequests` | `> 2.0%` (5m) | `> 5.0%` (5m) | Check Bedrock model TPM/RPM quotas & Gateway Redis rate limiter. |
| **End-to-End Latency** | `Latency` (p95 / p99) | `p95 > 12s` | `p99 > 25s` | Inspect trace waterfall for cold starts, slow MCP targets, or LTM sync reads. |
| **Token Anomaly** | `gen_ai.usage.input_tokens` + `output_tokens` | `> 2x` baseline | `> 4x` baseline | Check for cyclic loop runaway in LangGraph/Strands or oversized MCP tool schemas. |
| **Policy Deny Spike** | Gateway `PolicyDenyCount` / Cedar `DENY` | `> 5%` of calls | `> 20%` of calls | Correlate with recent `UpdatePolicy` events in CloudTrail or missing OBO claims. |

---

## 2. Closed-Loop Incident Triage Workflow (4-Step Correlation)

When an alarm fires or a user reports degraded agent behavior:

### Step 1: Application Signals & CloudWatch Metrics (`appsignals` & `cloudwatch` MCPs)
1. Query Application Signals SLO health and service operation metrics for the affected runtime endpoint (`DEFAULT`, `PROD`, `CANARY`).
2. Identify whether the latency or error spike originates in:
   - **Runtime Compute (`BedrockAgentCoreRuntime`)**
   - **Foundation Model Invocation (`Bedrock ConverseStream`)**
   - **Gateway Tool Target (`BedrockAgentCoreGateway`)**
   - **Memory Plane (`BedrockAgentCoreMemory`)**

### Step 2: Distributed Trace Waterfall (`agentcore traces` & X-Ray)
1. List recent traces for the failing session or time window:
   ```bash
   agentcore traces list --agent <agent-name> --session-id <session-id>
   agentcore traces get --trace-id <trace-id>
   ```
2. Inspect OpenTelemetry GenAI semantic attributes on each span:
   - `gen_ai.operation.name`: `chat`, `invoke_agent`, `execute_tool`
   - `gen_ai.request.model`: verify model ID and cross-region inference profile (`us.anthropic...`)
   - `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens`: detect context bloat
   - `otel.status_code` & `exception.message`: pinpoint the exact failing span

### Step 3: CloudWatch Logs Insights Correlation (`cloudwatch` MCP)
Run targeted CloudWatch Logs Insights queries correlated by `traceId` or `sessionId` across `/aws/bedrock-agentcore/runtimes/<agent-id>-<endpoint>`:

```sql
fields @timestamp, @message, level, sessionId, traceId
| filter sessionId = "<session-id>" or traceId = "<trace-id>" or level in ["ERROR", "CRITICAL"]
| sort @timestamp desc
| limit 100
```

For Gateway and Cedar Policy Engine failures, query `/aws/vendedlogs/bedrock-agentcore/gateway/<gateway-id>`:

```sql
fields @timestamp, method, toolName, policyDecision, errorCode, errorMessage
| filter policyDecision = "DENY" or ispresent(errorCode)
| sort @timestamp desc
| limit 50
```

### Step 4: Control-Plane Change Correlation (`cloudtrail` MCP)
Use the `cloudtrail` MCP server (`lookup_events`) to check whether a control-plane mutation preceded the incident:
- `UpdateAgentRuntime` / `UpdateAgentRuntimeEndpoint` (bad image digest or env var change)
- `UpdateGateway` / `UpdateGatewayTarget` (changed MCP endpoint or `supportedVersions`)
- `CreatePolicy` / `UpdatePolicy` / `UpdatePolicyEngine` (Cedar policy switched from `LOG_ONLY` to `ENFORCE`)
- IAM role or KMS key policy edits (`AccessDeniedException` on `kms:Decrypt` or `kms:Sign`)

---

## 3. Specialized AIOps Playbooks

### Playbook A: Gateway JSON-RPC `-32022` (`Unsupported protocol version`)
- **Symptom:** Agent tool calls fail immediately at the Gateway with JSON-RPC error `-32022`.
- **Root Cause:** Client sent an MCP protocol version (or omitted `MCP-Protocol-Version: 2026-07-28`) not listed in the Gateway target's `supportedVersions`.
- **Remediation:**
  1. Inspect target config via `get_gateway_target`.
  2. Update `protocolConfiguration.supportedVersions` to `["2026-07-28", "2025-11-25"]`.
  3. Ensure the agent's `MCPClient` sends `MCP-Protocol-Version: 2026-07-28` and never falls back to `2025-03-26`.

### Playbook B: Long-Term Memory (LTM) Extraction Lag & Dead-Letter Queue (DLQ) Redrive
- **Symptom:** `create_event` succeeds for Short-Term Memory (STM), but `retrieve_memories` returns empty results for LTM namespaces (`/facts/{actorId}/`, `/preferences/{actorId}/`, `/summaries/{actorId}/{sessionId}/`) minutes later.
- **Root Cause:** Asynchronous background LTM extraction/consolidation failed due to Bedrock model throttling, revoked KMS CMK permissions (`kms:Decrypt`/`kms:GenerateDataKey`), or malformed custom consolidation prompts.
- **Remediation:**
  1. Check the Memory resource's configured Dead-Letter Queue (SQS DLQ) depth via `aws-mcp` (`aws sqs get-queue-attributes`).
  2. Inspect sample failed extraction messages in the DLQ to identify `ThrottlingException` vs. `AccessDeniedException` on the `encryptionKeyArn` or `consolidationConfiguration` model.
  3. Fix the underlying IAM/KMS policy or quota, then trigger an SQS DLQ redrive (`aws sqs start-message-move-task`) to re-process the failed LTM extraction payloads without losing user memories.

### Playbook C: Emergency Canary Rollback
When a newly promoted `AgentRuntimeVersion` breaches `SystemErrorRate > 1%`:

```bash
# 1. Inspect current endpoint version routing
aws bedrock-agentcore-control get-agent-runtime-endpoint \
  --agent-runtime-id <agent-runtime-id> \
  --endpoint-name PROD

# 2. Immediately point PROD back to the last known-good immutable version
aws bedrock-agentcore-control update-agent-runtime-endpoint \
  --agent-runtime-id <agent-runtime-id> \
  --endpoint-name PROD \
  --agent-runtime-version <previous-good-version>
```
