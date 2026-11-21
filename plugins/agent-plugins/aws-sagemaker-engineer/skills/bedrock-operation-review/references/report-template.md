# Amazon Bedrock Operational Review — Report Template & Documentation Reference

Load this file during **Step 4** (remediation reference links) and **Step 5** (Markdown report generation) of `bedrock-operation-review`.

---

## 1. Report Artifact Naming & Verbatim Markdown Structure

- **Artifact filename:** `bedrock-review-<account-id>-<region>-<YYYY-MM-DD>.md`
- **Example:** `bedrock-review-123456789012-us-east-1-2026-04-29.md`

```markdown
# Amazon Bedrock Operational Review — <account-id> / <region>
Date: <YYYY-MM-DD> | Analysis window: <start> to <end>
Pillars reviewed: <Security, Performance, Service Quotas, Cost Optimization, Resilience>

## Executive Summary
- **Overall Health:** ✅ HEALTHY / ⚠️ WARNINGS / ❌ CRITICAL
- **Finding Counts by Severity:** CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n> | INFO: <n>
- **Top 3 Critical / High Priority Items:**
  1. <Item 1>
  2. <Item 2>
  3. <Item 3>

## Findings by Pillar

### Security
| # | Finding | Severity | Current State | Recommendation |
|---|---------|----------|---------------|----------------|

### Performance
| # | Finding | Severity | Current State | Recommendation |
|---|---------|----------|---------------|----------------|

### Service Quotas
| # | Finding | Severity | Current State | Recommendation |
|---|---------|----------|---------------|----------------|

### Cost Optimization
| # | Finding | Severity | Current State | Recommendation |
|---|---------|----------|---------------|----------------|

### Resilience
| # | Finding | Severity | Current State | Recommendation |
|---|---------|----------|---------------|----------------|

## CloudWatch Metrics Summary
| Metric | Model | Stat | Value | Status | Finding |
|--------|-------|------|-------|--------|---------|

## Service Quota Utilization
| Quota | Value | Observed P95 | Utilization % | Risk |
|-------|-------|--------------|---------------|------|

## Cost Optimization Opportunities
| Opportunity | Signal | Est. Impact | Effort |
|-------------|--------|-------------|--------|

## Priority Matrix
| # | Finding | Severity | Pillar | Effort | Impact |
|---|---------|----------|--------|--------|--------|

## Next Steps
- **Immediate (CRITICAL / HIGH — within 7 days):**
- **Short-term (MEDIUM — within 30 days):**
- **Long-term (LOW — within 90 days):**

## Appendix — Reference Links
- [Amazon Bedrock User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html)
- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)
- [Security in Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/security.html)
- [Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)
- [Model Invocation Logging](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html)
- [Bedrock Knowledge Bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html) & [KB Encryption](https://docs.aws.amazon.com/bedrock/latest/userguide/encryption-kb.html)
- [Configure a VPC for Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/usingVPC.html)
- [IAM for Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html) & [Model Access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)
- [Prompt Engineering Best Practices](https://docs.aws.amazon.com/prescriptive-guidance/latest/llm-prompt-engineering-best-practices/introduction.html)
- [Monitoring Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring.html) & [Improve Bedrock Performance](https://repost.aws/knowledge-center/bedrock-improve-performance-latency)
- [Optimize Agent Performance](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-optimize-performance.html) & [Model Lifecycle](https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle.html)
- [Bedrock Data Automation](https://docs.aws.amazon.com/bedrock/latest/userguide/bda.html) & [Service Tiers](https://docs.aws.amazon.com/bedrock/latest/userguide/service-tiers-inference.html)
- [Bedrock Quotas](https://docs.aws.amazon.com/bedrock/latest/userguide/quotas.html) & [Guardrail Quotas](https://docs.aws.amazon.com/general/latest/gr/bedrock.html#limits_bedrock)
- [Prompt Caching](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html), [Prompt Management](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-management.html), & [Intelligent Prompt Routing](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-routing.html)
- [Model Distillation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-distillation.html), [Provisioned Throughput](https://docs.aws.amazon.com/bedrock/latest/userguide/prov-throughput.html), & [Batch Inference](https://docs.aws.amazon.com/bedrock/latest/userguide/batch-inference.html)
- [Cross-Region Inference (CRIS)](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html)
```

---

## 2. Pillar Remediation Notes

- **Security:** Attach Bedrock Guardrails (content filters for hate/insult/sexual/violence/PII + denied topics + prompt-attack filter); disable or restrict model invocation logging where PII/PCI/HIPAA rules prohibit persisting prompts/outputs; enforce customer-managed KMS keys (`CMK`) on Knowledge Base data sources; run model customization jobs inside a private VPC (`us-east-1`, `us-west-2`); scope IAM/SCP model permissions to approved models and specific agent/alias ARNs.
- **Performance:** Mitigate throttling with exponential backoff + jitter, quota increases, load spreading, and CRIS profiles; enable latency-optimized agent flows where eligible (single KB, no action groups, no follow-up prompts, default orchestration template); align alias versions with draft models/orchestration; migrate off Legacy/EOL models (check model cards — Legacy notice is 6 months for most models or 45 days for select models); align `default` / `flex` / `priority` / `reserved` service tiers with workload latency needs.
- **Service Quotas:** Request proactive quota increases via Service Quotas when P95 RPM/TPM or Guardrail text-unit utilization exceeds `75%`; manually review Classic vs. Standard guardrail policy split when both exist.
- **Cost Optimization:** Adopt Application Inference Profiles for Cost Allocation Tagging; evaluate Custom Model Distillation (`p99 > 3000 ms`, `InputTokenCount > 1M/mo`, `throttle > 5%`), Prompt Caching (`>= 50%` offload target; up to ~85% latency and ~90% prefix cost savings), Intelligent Prompt Routing, Provisioned Throughput right-sizing, Managed Batch Inference (`> 10K/day` latency-tolerant jobs, up to ~50% savings), and EC2 GPU right-sizing (Trainium2 for `< 40%` avg GPU util, model parallelism for `> 90%` GPU mem, Spot/Capacity Blocks for `CV > 0.5`, ML Savings Plans/RIs for `> 80%` sustained util).
- **Resilience:** Route inference through Cross-Region Inference (CRIS) profiles (`us.`, `eu.`, `apac.`, `global.`) rather than invoking base model IDs directly (improves burst capacity and saves ~10% on global profiles).
