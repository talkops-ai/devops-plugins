---
name: bedrock-operation-review
description: Comprehensive Amazon Bedrock review aligned with the AWS 
  Well-Architected Framework and Bedrock best practices. Use this skill when
  a user asks to review, audit, or assess Amazon Bedrock workloads for
  best-practices compliance, security posture, performance, cost optimization,
  service quotas, or resilience. Triggers on requests
  like "Bedrock review", "Bedrock best practices audit", "GenAI operational
  assessment", "review my Bedrock account", "Bedrock health check", "Bedrock cost
  optimization review", or "ORR for Bedrock".
metadata:
  author: sean-nixon
  version: "1.0.3"
  aws-devops-agent-skills.agent-types: "CHAT"
  aws-devops-agent-skills.aws-services: "Amazon Bedrock"
  aws-devops-agent-skills.technical-domains: "AI/ML"
---

# Amazon Bedrock Operational Review

Conduct a comprehensive operational review of Amazon Bedrock workloads aligned with the AWS Well-Architected Framework and Amazon Bedrock best practices.

This skill uses the **AWS Bedrock, Bedrock Agent, CloudWatch, Service Quotas, and EC2 APIs only** — all data is collected through native AWS control-plane APIs and CloudWatch metrics. It performs **no** data-plane model invocations (`InvokeModel`) and reads **no** prompt or response content.

## MCP-Only Execution & Read-Only Safety

- **MCP-Only Live Discovery & Docs:** Execute **all** live AWS discovery, Bedrock / AgentCore inspection, CloudWatch metric queries, Service Quotas checks, IAM/VPC reviews, and documentation lookups **exclusively via connected MCP tools**: `aws-mcp` (`aws___run_script` using read-only `await call_boto3(...)`, `aws___search_documentation`, `aws___read_documentation`), `agentcore` (`search_agentcore_docs`, `fetch_agentcore_doc`, `list_agent_runtimes`, `get_agent_runtime`, etc.), `strands-agents` (`search_docs`, `fetch_doc`, `find_integrations`), `cloudwatch`, `appsignals`, `cloudtrail`, `awspricing`, `awsiac`, and `awsknowledge`.
- **Zero Raw CLI Execution, Strictly Read-Only & Secret-Safe:** **Never** run raw `aws ...` or `agentcore ...` CLI commands in Bash/`run_command` to query or mutate live AWS accounts (present CLI commands in Markdown strictly as operator reference snippets). **Never** invoke live mutations (`create_*`, `update_*`, `delete_*`, `InvokeAgentRuntime`, `InvokeModel`) and **never** read plaintext secrets (`secretsmanager:GetSecretValue`, `ssm:GetParameter` with `WithDecryption=True`, `.env` values, prompt templates via `GetPrompt`, or raw memory record contents).
- **Edge-Case Documentation Fallback:** For unmapped AWS/Bedrock/AgentCore edge cases (e.g., new model lifecycle dates or regional feature support), run 1–2 focused queries via `awsknowledge`, `aws-mcp`, `agentcore`, or `strands-agents` documentation search tools.

## When to Use

Activate this skill when the user asks to:
- Review, audit, or assess an Amazon Bedrock workload or best-practices compliance
- Evaluate Bedrock **Security, Performance, Service Quotas, Cost Optimization, or Resilience**
- Perform a Bedrock Operational Readiness Review (ORR) or investigate drift, throttling, or cost drivers

## Step 1: Identify Target Scope

Ask which accounts and regions to review (specific account/regions, "all regions", or specific pillars). If unspecified, default to all configured regions, all five pillars, and a **7-day** analysis window (windows older than ~2 weeks may have lower CloudWatch resolution).

## Step 2: Discover Bedrock Resources

Per account/region, determine activity from **account-owned resources and `AWS/Bedrock` metrics** — **do NOT use `bedrock.ListFoundationModels` as an activity signal** (it returns the regional model catalog regardless of usage):
- **Account-owned resources:** `bedrockagent.ListAgents`, `bedrockagent.ListKnowledgeBases`, `bedrock.ListGuardrails`, `bedrock.ListCustomModels`, `bedrock.ListProvisionedModelThroughputs`, `bedrock.ListInferenceProfiles` (application-scoped), `bedrock.ListModelCustomizationJobs`.
- **Invocation activity:** `cloudwatch.ListMetrics` for namespace `AWS/Bedrock`.

**If no account-owned Bedrock resources exist AND CloudWatch shows no `AWS/Bedrock` metrics, record `"No Bedrock activity detected — skipping pillar analysis"` for that region and do not generate empty findings tables.**

For active regions, collect the read-only control-plane inventory (identifiers, ARNs, status, timestamps, AWS-managed vs. CMK KMS encryption, VPC config):

```
bedrock.ListFoundationModels                         # catalog/lifecycle status only (NOT activity)
bedrock.ListGuardrails / GetGuardrail
bedrock.GetModelInvocationLoggingConfiguration
bedrock.ListInferenceProfiles / GetInferenceProfile
bedrock.ListPromptRouters / GetPromptRouter
bedrock.ListProvisionedModelThroughputs / GetProvisionedModelThroughput
bedrock.ListCustomModels / GetCustomModel
bedrock.ListModelCustomizationJobs / GetModelCustomizationJob
bedrockagent.ListAgents / GetAgent
bedrockagent.ListAgentVersions / GetAgentVersion     # read ONLY model ID, orchestration type, and
                                                     # whether prompt override exists — NEVER read
                                                     # override base-prompt template text
bedrockagent.ListAgentAliases
bedrockagent.ListKnowledgeBases / GetKnowledgeBase
bedrockagent.ListDataSources / GetDataSource
bedrockagent.ListPrompts                             # metadata/counts ONLY — NEVER call GetPrompt
```

## Step 3: Collect CloudWatch Metrics (`AWS/Bedrock`)

**Before querying metrics, read [`references/metrics-thresholds.md`](references/metrics-thresholds.md)** and apply its Normal / Warning / Critical thresholds throughout Steps 3 and 4.

Discover invoked models with `cloudwatch.ListMetrics` (dimension `ModelId`), then batch `cloudwatch.GetMetricData` (up to 500 queries per call; default 7-day window):

| Metric | Stat | Signal |
|--------|------|--------|
| `Invocations` | Sum | Volume / denominator for rate calculations |
| `InvocationThrottles` | Sum | Throttling / quota pressure |
| `InvocationServerErrors` | Sum | Server-side failures |
| `InvocationClientErrors` | Sum | Bad input / blocked content |
| `InvocationLatency` | Average, p95 | End-to-end latency |
| `TimeToFirstToken` | Average, p95 | Perceived streaming latency |
| `InputTokenCount` / `OutputTokenCount` | Sum | Input and output token volume |
| `InvocationsIntervened` / `TextUnitCount` | Sum | Guardrail interventions & text-unit usage |
| `CacheReadInputTokenCount` / `CacheWriteInputTokenCount` | Sum | Prompt cache reads and writes |

Self-managed EC2 GPU workloads (`P4`/`P5`/`P5en`/`P6` with CloudWatch Agent + NVIDIA DCGM) emit `nvidia_smi_utilization_gpu` and `nvidia_smi_memory_util` in namespace `CWAgent`.

## Step 4: Analyze Against Best Practices

**Before evaluating findings, read [`references/best-practices-checklist.md`](references/best-practices-checklist.md)** (and [`references/report-template.md`](references/report-template.md) for remediation links). Mark each checklist item ✅ Pass, ⚠️ Warning, ❌ Fail, or ➖ Not Applicable, and assign `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, or `INFO` across the five pillars: **Security, Performance, Service Quotas, Cost Optimization, Resilience**.

### 4.1 Security
- **Guardrails:** Missing on high-volume workloads → `HIGH`. Filter hate, insult, sexual, violence, PII, and denied topics.
- **Guardrail signals:** `InvocationClientErrors > 5%` of `Invocations` → `MEDIUM` (filter upstream). Active guardrail `InvocationsIntervened < 5%` (under-configured) or `> 15%` (over-tuned) → review.
- **Model invocation logging:** Persisting prompts/outputs on PII/PCI/HIPAA workloads or logging mismatches → `MEDIUM`.
- **Knowledge Base & KMS encryption:** Missing chunking (`200–1000` tokens), embedding/access/VPC controls, or data sources lacking customer-managed KMS keys (`CMK`) on sensitive data → `MEDIUM`. Missing KB ingestion logs → `LOW`; missing CloudTrail/CloudWatch anomaly monitoring → `MEDIUM`.
- **VPC for model customization jobs (`us-east-1`, `us-west-2`):** Missing VPC exposes training data to the internet → `HIGH`.
- **Prompt injection defense:** No guardrail or missing prompt-attack filter → `MEDIUM` (never read prompt templates directly).
- **IAM & model access:** Agent/alias policies with unjustified `*` resource → `MEDIUM` (broader account IAM/SCP model-scoping gaps reported at `INFO`).

### 4.2 Performance
- **Latency & throttling:** High `InvocationThrottles / Invocations`, `InvocationLatency` p95, `TimeToFirstToken` p95, or server error rate → `HIGH` (use exponential backoff + jitter, CRIS, smaller models/streaming, or quota increases).
- **Agent flow & version drift:** Flag agents missing latency-optimized flow criteria (single KB, no action groups, no follow-ups, default orchestration). Aliases (`GetAgentVersion`) drifted from draft model ID or orchestration type → `MEDIUM`.
- **Model lifecycle:** Invocations hitting `Legacy` or `End-of-Life` models → `MEDIUM` (check model card EOL date; Legacy notice is 6 months or 45 days depending on model).
- **Data Automation & Service Tiers:** BDA success `< 95%`, error `> 5%`, or throttle `> 1%` → `MEDIUM`. Misaligned tier (`default`, `flex`, `priority`, `reserved` — e.g., latency-sensitive on `flex` or batch on `priority`) → `MEDIUM`.

### 4.3 Service Quotas
- **Model & Guardrail quotas:** Compare observed P95 RPM/TPM (including CRIS / Global CRIS) and `ApplyGuardrail` / text-unit consumption against `servicequotas.GetServiceQuota`. Utilization `> 75%` → `MEDIUM`; sustained near limit → `HIGH`.

### 4.4 Cost Optimization
- **Application inference profiles:** Unused for Cost Allocation Tagging → `LOW`.
- **Custom model distillation (`us-east-1`, `us-west-2`):** `InvocationLatency` p99 `> 3000 ms` AND `InputTokenCount > 1M/month` AND throttle rate `> 5%` on large premium models → `MEDIUM` opportunity.
- **Prompt caching:** Offload % = `CacheReadInputTokenCount / (CacheReadInputTokenCount + CacheWriteInputTokenCount)` (`Not Supported`, `Not Enabled`, `Misconfigured` [writes with 0 reads], `Underutilized < 50%`, `Optimized >= 50%`). Uncached repeated prefixes → `MEDIUM` (up to ~85% latency / ~90% prefix cost reduction).
- **Prompt management & routing:** Prompt Management presence → `INFO`; missing Intelligent Prompt Routing on mixed-complexity workloads → `LOW`.
- **Provisioned throughput & Batch inference:** Idle/expiring Provisioned Throughput or steady baseline left on-demand → `MEDIUM`. High-volume (`> 10K/day`) latency-tolerant jobs on on-demand or self-managed GPU batch → `MEDIUM` (up to ~50% Batch Inference savings).
- **EC2 GPU (`CWAgent`, 7-day min):** Avg GPU `< 40%` → migrate training to Trainium2 (~30–50% savings); GPU mem `> 90%` → OOM risk; usage `CV > 0.5` → Spot / Capacity Blocks; sustained `> 80%` → ML Savings Plans / RIs.

### 4.5 Resilience
- **Cross-Region Inference (CRIS):** Adoption % = `Profile InputTokenCount / (Profile InputTokenCount + Base Model InputTokenCount)`. Direct base-model traffic bypassing CRIS profiles reduces burst resilience and forgoes ~10% global-profile savings → `MEDIUM`.

## Step 5: Generate Report (Load [`references/report-template.md`](references/report-template.md))

**Read [`references/report-template.md`](references/report-template.md)** for the full Markdown layout and reference links, and **always render the complete Markdown report directly inline in your final response** (never rely solely on linking an external artifact file):
- **Report filename header:** Always display the canonical report filename `bedrock-review-<account-id>-<region>-<YYYY-MM-DD>.md` in the report header (including when reporting `No Bedrock activity detected — skipping pillar analysis` on an empty region; only write the file to disk if explicitly requested).
- **Required sections:** Report Header, Executive Summary (`✅ HEALTHY` / `⚠️ WARNINGS` / `❌ CRITICAL`), Findings by Pillar (`Security`, `Performance`, `Service Quotas`, `Cost Optimization`, `Resilience`), CloudWatch Metrics Summary, Service Quota Utilization, Cost Optimization Opportunities, Priority Matrix, Next Steps (7 / 30 / 90 days), and Appendix.

## Severity Definitions

| Severity | Definition | SLA |
|----------|------------|-----|
| CRITICAL | Immediate risk to availability, security, or data integrity | Fix within 24–48 hours |
| HIGH | Significant gap that could lead to incidents | Fix within 1 week |
| MEDIUM | Notable improvement opportunity | Plan within 30 days |
| LOW | Minor optimization or hardening | Address when convenient |
| INFO | Observation, no action required | N/A |

## Region-Restricted Checks & Known API Quirks

- **Region-restricted checks (skip silently outside supported regions):** Model Customization VPC & Custom Model Distillation (`us-east-1`, `us-west-2`); Application Inference Profiles (`us-east-1`, `us-east-2`, `us-west-2`, `ap-northeast-1`, `ap-northeast-2`, `ap-southeast-2`, `ap-south-1`, `eu-central-1`, `eu-west-1`, `eu-west-3`, `us-gov-east-1`, `us-gov-west-1`).
- **API quirks:** Guardrail CloudWatch metrics do not separate Classic vs. Standard policy versions (review manually when both exist); `GetMetricData` caps at 500 queries/call; CRIS-only models show `0` direct base-model tokens (`100%` CRIS by design); prompt cache TTL is ~5 minutes; EC2 GPU checks require CloudWatch Agent + NVIDIA DCGM.

## Data Source Boundaries

Collects data **exclusively** via read-only AWS APIs (`bedrock`, `bedrockagent`, `cloudwatch`, `servicequotas`, `ec2`). It **never** invokes foundation models (no data-plane calls) and **never** reads prompt or response content.
