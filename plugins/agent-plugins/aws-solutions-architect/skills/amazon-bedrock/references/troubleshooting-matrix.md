# Amazon Bedrock Troubleshooting Matrix & Worked Workflow Examples

This reference contains the complete Bedrock error catalog, retry classification rules, SharePoint/KB connector failure diagnostics, and worked intent-to-workflow runbook examples referenced from `SKILL.md`.

> **MCP-Only Live Inspection Note:** Perform all live AWS diagnostics (such as listing foundation models, listing inference profiles, checking Service Quotas, or querying CloudWatch metrics) via connected MCP tools (`aws-mcp` `aws___run_script` with read-only `await call_boto3(...)`, `cloudwatch`, `agentcore`, `awspricing`, `awsknowledge`). Treat `aws ...` CLI snippets below as operator runbook examples rather than shell commands to run directly.

---

## 1. Error Retry Classification

| Retry (Transient) | Do NOT Retry (Client / Config / Auth) |
|---|---|
| `ThrottlingException` | `ValidationException` |
| `ModelTimeoutException` | `AccessDeniedException` |
| `ServiceUnavailableException` | `ResourceNotFoundException` |
| `InternalServerException` | |

Use adaptive retry in `botocore`:

```python
from botocore.config import Config

config = Config(retries={"max_attempts": 5, "mode": "adaptive"})
```

---

## 2. Detailed Bedrock Error & Symptom Reference

### AccessDeniedException
Multiple possible causes:
1. IAM user/role lacks `bedrock:InvokeModel` or `bedrock:InvokeModelWithResponseStream` permissions (note: when invoking a Cross-Region Inference Profile, IAM must allow **both** the `inference-profile/*` ARN and underlying `foundation-model/*` ARNs).
2. Model access is not enabled in the target region (or Anthropic First-Time-Use form has not been submitted).
3. A Service Control Policy (SCP) is blocking access — common when a cross-region inference profile routes traffic to a restricted destination region.
4. Expired temporary credentials.
5. **IAM role propagation delay** — if an IAM role was just created and immediately used in a Bedrock API call, IAM eventual consistency may cause transient `AccessDeniedException` (see [IAM eventual consistency](https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_general.html#troubleshoot_general_eventual-consistency)).

Check the error message for specifics (explicit deny vs. missing allow vs. model access). See [Resolve InvokeModel API errors](https://repost.aws/knowledge-center/bedrock-invokemodel-api-error).

### Malformed input request
Request body does not match the expected schema. Common causes: wrong provider-specific body format for `InvokeModel` (e.g., using Titan format for a Cohere or Anthropic model), malformed JSON, unsupported parameter names, or exceeding input constraints. Prefer the unified **Converse API** unless provider-specific parameters are required; inspect `"schema violations"` in the error payload and verify against [prompt-engineering-by-model.md](prompt-engineering-by-model.md).

### ThrottlingException
1. **Set `maxTokens` explicitly** — unset values default to the model's maximum (e.g., 64K for Claude Sonnet) and silently reserve up to ~43x more TPM quota upfront than needed before generation begins.
2. Enable **adaptive retry mode** (`Config(retries={"max_attempts": 5, "mode": "adaptive"})`).
3. Use **Cross-Region Inference Profiles** (`us.`, `eu.`, `apac.`, or `global.` prefix — see [Supported inference profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html)) to distribute burst traffic across regions.
4. Audit quota vs. peak usage via `service-quotas` (`GetServiceQuota` for `service-code="bedrock"`) and CloudWatch metrics — see [quota-health.md](quota-health.md).

### Prompt cache not working (zero `cacheReadInputTokens`)
Read [prompt-caching.md](prompt-caching.md) for the full diagnostic checklist: verify model support, minimum token threshold per model, exact prefix byte identity, TTL, and `cachePoint` placement. Common root cause: cache prefix invalidation caused by dynamic timestamps, UUIDs, whitespace differences, or non-deterministic JSON key ordering inside cached blocks.

### 400 error on assistant prefill with Claude 4.6+
Assistant message prefill was removed starting in Claude 4.6 and returns a hard HTTP 400 validation error. Read [model-migration.md](model-migration.md) for the complete breaking-changes matrix across Claude 4.5, 4.6, and 4.7 (prefill removal, adaptive thinking configuration, context window differences, and cache token thresholds).

### UnknownOperationException
Wrong boto3/SDK client endpoint (for example calling `Converse` on control-plane `bedrock` instead of data-plane `bedrock-runtime`, or calling Agent operations on `bedrock` instead of `bedrock-agent` / `bedrock-agent-runtime`), or outdated `boto3` (< `1.34.x`) / AWS CLI v1. Verify client mapping in the Bedrock API Landscape table in `SKILL.md`.

### Agent returns stale behavior
You **MUST** run `prepare-agent` (`PrepareAgent`) after **any** Bedrock Agent configuration, instruction, foundation model, or action group modification. Until `prepare-agent` completes, alias invocations continue serving the prior prepared state.

### KB returns empty results
Run `start-ingestion-job` (`StartIngestionJob`) and wait until ingestion status reaches `COMPLETE`. Querying a Knowledge Base before initial ingestion finishes returns zero chunks.

### KB retrieval quality is poor
Review chunking strategy (fixed-size, hierarchical, semantic, or custom). Enable **advanced parsing (FM-based)** for complex PDFs containing tables and figures, and configure **metadata filtering** to narrow retrieval scope.

### Cross-region model not found
The foundation model may not be available in the calling source region. Check [Supported foundation models](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html). When adopting Cross-Region Inference Profiles, treat the prefix as a **data residency decision**: geographic profiles (`us.`, `eu.`, `apac.`) keep inference traffic within that geographic boundary, whereas `global.` profiles can route to any commercial AWS region.

### On-demand throughput isn't supported
Error: *"Invocation of model ID `<model-id>` with on-demand throughput isn't supported. Retry your request with the ID or ARN of an inference profile that contains this model."*
Certain newer models cannot be invoked on-demand using bare foundation model IDs — they require a system-defined or application **inference profile ID/ARN**. Query `bedrock` `ListInferenceProfiles` in the target region, update `modelId` (or the agent's `foundationModel` followed by `prepare-agent`), and retry.

### KB storage configuration invalid
Verify the OpenSearch Serverless data access policy grants permissions to the Bedrock Knowledge Base execution role, and verify vector index field names (`vectorField`, `textField`, `metadataField`) match the Knowledge Base storage configuration exactly.

### Agent action group errors
Verify the target AWS Lambda function has a resource-based policy (`lambda:AddPermission`) allowing principal `bedrock.amazonaws.com` with `aws:SourceAccount` and `aws:SourceArn` conditions. **Do NOT use double underscores (`__`) in action group names** — valid names must match `([0-9a-zA-Z][_-]?){1,100}`.

### Multi-agent supervisor loops
Classic Bedrock multi-agent collaboration uses the built-in collaboration configuration (`agentCollaboration`), **NOT** custom action groups. Do not describe sub-agent routing as action groups inside supervisor instructions.

### `INVALID_PAYMENT_INSTRUMENT` on model access
Account-level AWS billing issue rather than a Bedrock IAM/API defect. Set a valid credit card as the default payment method or configure USD payment profiles in the AWS Organizations management account.

### Knowledge Base ingestion failures
Verify S3 bucket permissions on the KB execution role (`s3:GetObject`, `s3:ListBucket`, plus `kms:Decrypt` if SSE-KMS is enabled). Note that unsupported file formats and files exceeding per-document size limits are skipped during ingestion.

### SharePoint data source sync failures
Sync job finishes with failed document count > 0 — almost always authentication configuration:
- **Recommended: Microsoft Entra ID authentication (`OAUTH2_CLIENT_CREDENTIALS`).** Register an app in Microsoft Entra ID, grant Microsoft Graph application permission `Sites.Read.All` with admin consent, and store `clientId` and `clientSecret` in AWS Secrets Manager **in the same AWS Region as the Knowledge Base**. Pass `tenantId` in the data source configuration (not inside the secret).
- **Do NOT use Azure ACS SharePoint App-Only auth:** Microsoft retired Azure ACS SharePoint App-Only authentication on **April 2, 2026**; it no longer works.
- Legacy OAuth 2.0 delegated auth (`AllSites.Read`, often requiring Security Defaults / MFA exceptions on the service account) should be migrated to Entra ID client credentials. See [SharePoint data source connector docs](https://docs.aws.amazon.com/bedrock/latest/userguide/sharepoint-data-source-connector.html).

---

## 3. Worked Intent-to-Workflow Examples & Operator Runbook Snippets

| # | User Intent | Recommended Action & Reference |
|---|---|---|
| 1 | *"I'm getting `ThrottlingException` on Bedrock"* | Verify `maxTokens` is set explicitly in `inferenceConfig`. Inspect Service Quotas (`service-quotas` `GetServiceQuota` for `bedrock`) and CloudWatch metrics via [quota-health.md](quota-health.md). |
| 2 | *"Set up RAG for my PDF documents"* | Default to **Managed Knowledge Base (MKB)** (fully managed storage, parsing, chunking, and retrieval) via [managed-knowledge-bases-setup.md](managed-knowledge-bases-setup.md) and [knowledge-bases-decision-guide.md](knowledge-bases-decision-guide.md). Use Customer-managed KB only if explicitly requested. |
| 3 | *"Build an agent that looks up order status"* | For new builds, prefer **AgentCore Harness** ([agentcore-harness.md](agentcore-harness.md)); for classic Bedrock Agents maintenance, follow [agents-and-action-groups.md](agents-and-action-groups.md) and run `prepare-agent` after edits. |
| 4 | *"How do I call Claude on Bedrock?"* | Use `bedrock-runtime` **Converse API** with explicit `maxTokens` and a cross-region inference profile (e.g., `us.anthropic.claude-sonnet-4-6`). Read [sdk-converse-api-python.md](sdk-converse-api-python.md) or [sdk-converse-api-typescript.md](sdk-converse-api-typescript.md). |
| 5 | *"Deploy my agent to production"* | Route config-based loops to **AgentCore Harness** ([agentcore-harness.md](agentcore-harness.md)) and custom code loops to **AgentCore Runtime** ([agentcore-runtime.md](agentcore-runtime.md)), selecting HTTP vs. MCP protocol first. |
| 6 | *"Set up prompt caching for my Claude app"* | Follow [prompt-caching.md](prompt-caching.md) for TTL, per-model minimum token thresholds, break-even math, and verifying `cacheReadInputTokens > 0`. |
| 7 | *"ThrottlingException even at low RPS"* | Unset `maxTokens` is reserving full context output quota per call; audit via [quota-health.md](quota-health.md). |
| 8 | *"Track Bedrock costs by team"* | Configure application inference profile cost allocation tags, CUR 2.0 queries, and Cost Explorer grouping per [cost-tracking.md](cost-tracking.md) (confirm time range, grouping, and attribution method first). |
| 9 | *"Upgrading from Claude 4.5 to 4.6 — what breaks?"* | Check [model-migration.md](model-migration.md) for assistant prefill removal (400 error), thinking config updates, context window changes, and cache threshold shifts. |

### Operator CLI Reference: Converse Invocation & Streaming Modes

```bash
# Operator runbook reference (verify available models & invoke Converse with explicit maxTokens)
aws bedrock list-foundation-models --region us-east-1
aws bedrock-runtime converse \
  --region us-east-1 \
  --model-id us.anthropic.claude-sonnet-4-6 \
  --messages '[{"role":"user","content":[{"text":"Summarize zero-trust IAM boundaries for Bedrock."}]}]' \
  --inference-config '{"maxTokens":1024}'
```

- **`Converse` (non-streaming):** Best for batch/backend pipelines needing a single complete response payload.
- **`ConverseStream` (streaming — SDK only, not supported in AWS CLI):** Best for interactive chat UIs (`converse_stream()` in Python `boto3`, `ConverseStreamCommand` in AWS SDK for JavaScript v3).
