---
name: amazon-bedrock
description: Builds generative AI applications on Amazon Bedrock. Covers model invocation (Converse API, InvokeModel), RAG with Knowledge Bases, Bedrock Agents, Guardrails, and AgentCore (including Harness). Applies when invoking models, configuring Knowledge Bases, applying guardrails, migrating classic/inline Bedrock Agents to AgentCore Harness, troubleshooting Bedrock errors (ThrottlingException, AccessDeniedException), prompt caching, quota/throttling math, cost tracking, Claude model migrations (4.5 to 4.6/4.7), chunking strategies, API selection, model selection (Claude, Llama, Nova, Titan), and AgentCore Payments (x402, Payment Manager, Connector, Instrument, Coinbase CDP, Stripe Privy). NOT for custom model training, Rekognition, or Comprehend. Query live AWS state via MCP tools only (never raw aws CLI).
metadata:
  version: "6"
---

# Amazon Bedrock

Domain expertise for building generative AI applications on Amazon Bedrock — covering model invocation, RAG with Knowledge Bases, Guardrails, classic Bedrock Agents migration, and agent deployment on Amazon Bedrock AgentCore. Always read the relevant `references/*.md` file before generating SDK code, configurations, or troubleshooting steps.

## MCP-Only Execution & Read-Only Safety

- **MCP-Only Live Queries:** Execute **all** live AWS discovery, Bedrock/SageMaker control-plane checks, pricing lookups, IaC compliance checks, CloudWatch telemetry queries, and documentation searches **exclusively via connected MCP tools**: `aws-mcp` (`aws___run_script` using read-only `await call_boto3(...)`, `aws___search_documentation`, `aws___read_documentation`), `sagemaker` (`describe_hp_cluster`), `agentcore`, `strands-agents`, `cloudwatch`, `awspricing` (`get_pricing`, `get_bedrock_patterns`), `awsiac`, and `awsknowledge`. Offline pure-Python bundled helper scripts in `scripts/*.py` that perform local math/schema rendering without live AWS credentials are permitted when inspecting local inputs, whereas live AWS API queries must go through MCP rather than raw `aws` CLI or boto3 shell scripts (emit `aws ...` CLI snippets in markdown for operator runbooks only).
- **Strict Read-Only & Secret Safety:** **Never** run raw `aws ...` (not even `aws sts get-caller-identity` — always query `sts.GetCallerIdentity` inside `aws___run_script`) CLI commands in Bash/`run_command`, **never** mutate live AWS resources (`Create*`, `Update*`, `Delete*`, `InvokeModel`, `CreateEndpoint` — refuse unapproved mutations and present a safe, approval-gated plan with verification and rollback steps; when migrating Classic Agents/shims to AgentCore Harness, **never** run `lambda add-permission` to modify customer source Lambda resource policies — grant `lambda:InvokeFunction` on the Harness/shim execution role instead, and always enforce `runtimeSessionId >= 33` chars on Harness invocations), and **never** read or expose plaintext secrets (`secretsmanager:GetSecretValue`, `ssm:GetParameter` with `WithDecryption=True`, or `.env` API keys — inspect `secretsmanager:DescribeSecret` metadata or `.env.example` only).
- **Unmapped Edge Cases:** Query `awsknowledge` / `aws-mcp` documentation search tools (`aws___search_documentation`, `aws___read_documentation`) with 1–2 focused queries before recommending unverified parameters (for **Intelligent Prompt Routing**, note invoking `Converse` / `InvokeModel` by passing the prompt router ARN directly as `modelId` alongside `responseQualityDifference` and same-family model pairs).

## Guardrail — Resolving Skill Files (MCP vs. Local Install)

- **Loaded via AWS MCP `retrieve_skill`:** Fetch bundled references or scripts via `retrieve_skill` using `file="references/..."` or `file="scripts/fetch_bedrock_agent.py"` rather than local file reads. Never pass customer data through `retrieve_skill`.
- **Installed locally:** Read bundled files directly from this skill directory using relative paths (`references/...`, `scripts/...`, `assets/...`).

## Bedrock & AgentCore API Landscape

Using the wrong service client is a leading cause of `UnknownOperationException`. Check [Bedrock endpoints and quotas](https://docs.aws.amazon.com/general/latest/gr/bedrock.html) and [AgentCore endpoints and quotas](https://docs.aws.amazon.com/general/latest/gr/bedrock_agentcore.html) for regional availability.

| Endpoint / Service Client | Plane | Primary Operations |
|---|---|---|
| `bedrock` | Control plane | `ListFoundationModels`, `ListInferenceProfiles`, Guardrails, Provisioned Throughput |
| `bedrock-runtime` | Data plane | `Converse`, `ConverseStream`, `InvokeModel` (plus `/openai/v1` client-side Chat Completions; prefer `bedrock-mantle` for new OpenAI-compatible workloads) |
| `bedrock-mantle` | Data plane | OpenAI-compatible Responses API, Chat Completions, and Messages API with server-side built-in tool support |
| `bedrock-agent` | Agent/KB control | Create/configure Knowledge Bases, data sources, classic Agents, and action groups |
| `bedrock-agent-runtime` | Agent/KB data | `Retrieve`, `AgenticRetrieveStream`, `RetrieveAndGenerate`, classic `InvokeAgent` |
| `bedrock-agentcore-control` | AgentCore control | Manage Harnesses, Runtimes, Gateways, Memories, Registries, Evaluations |
| `bedrock-agentcore` | AgentCore data | Invoke AgentCore Runtimes and Harnesses |
| `{gatewayId}.gateway.bedrock-agentcore` | Gateway data | Invoke MCP tools exposed through an AgentCore Gateway |

## Critical Warnings & Security Baselines

1. **`maxTokens` Quota Reservation:** **ALWAYS** set `maxTokens` explicitly in every `Converse` / `InvokeModel` call. Leaving it unset reserves the model's full maximum output window (e.g., 64K tokens on Claude Sonnet) upfront against TPM quota, triggering premature `ThrottlingException`.
2. **Guardrails PII Logging Gap:** Guardrails PII masking applies only to the API response; unmasked PII can still appear in invocation logs. For HIPAA/GDPR workloads, encrypt CloudWatch Logs with customer-managed KMS keys, restrict log IAM access, set retention policies, and pair with Amazon Macie.
3. **SDK Version Floor:** Require `boto3 >= 1.34.x` and AWS CLI v2 for `Converse`, `bedrock-mantle`, and AgentCore APIs.
4. **Classic Bedrock Agents Maintenance Mode:** `bedrock-agent` classic Agents are in maintenance mode and closed to new customers ([announcement](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-classic-maintenance-mode.html)). Build new managed agent loops on **AgentCore Harness** ([references/agentcore-harness.md](references/agentcore-harness.md)) and migrate existing classic agents via [references/migrate-bedrock-agents-to-agentcore-harness.md](references/migrate-bedrock-agents-to-agentcore-harness.md).
5. **Zero-Trust IAM & Input Hygiene:** Use least-privilege IAM roles (never IAM user keys, `bedrock:*`, or `AmazonBedrockFullAccess`), enforce `aws:SourceAccount` + `aws:SourceArn` confused-deputy conditions on resource policies, store OAuth/API credentials in AWS Secrets Manager with rotation, enable CloudTrail across Bedrock + AgentCore, and validate all model-generated tool arguments as untrusted input.

## Converse API vs. InvokeModel

- Prefer **`Converse` / `ConverseStream`** (`bedrock-runtime`) for unified messages, tool use, guardrails, and prompt caching across providers (`ConverseStream` is SDK-only; AWS CLI supports non-streaming `Converse` only). Read [references/sdk-converse-api-python.md](references/sdk-converse-api-python.md) or [references/sdk-converse-api-typescript.md](references/sdk-converse-api-typescript.md) before generating SDK code, and [references/model-invocation.md](references/model-invocation.md) for quota mechanics.
- Use **`InvokeModel`** only for provider-specific capabilities absent from Converse (e.g., embeddings or image generation); verify exact body schemas in [references/prompt-engineering-by-model.md](references/prompt-engineering-by-model.md).

## Capability & Workflow Routing

Present your planned workflow clearly before acting, respect user stop/abort decisions immediately, and never execute mutating or billable operations without explicit approval. Worked intent examples and CLI runbooks are in [references/troubleshooting-matrix.md](references/troubleshooting-matrix.md).

| Capability / Workflow | Mandatory Rules & Key Constraints | Primary Reference |
|---|---|---|
| **Model Invocation** | Verify model/profile availability via MCP (`ListFoundationModels` / `ListInferenceProfiles`); always set explicit `maxTokens` and adaptive retries. | [references/model-invocation.md](references/model-invocation.md) |
| **Knowledge Bases (RAG)** | **Default to Managed Knowledge Base (MKB)** (fully managed storage, parsing, chunking, retrieval). Query MKB via `Retrieve` or SDK-only `AgenticRetrieveStream`. Use Customer-managed KB (`RetrieveAndGenerate`) **only** if the user explicitly asks to bring their own vector store. | [references/knowledge-bases-decision-guide.md](references/knowledge-bases-decision-guide.md), [references/managed-knowledge-bases-setup.md](references/managed-knowledge-bases-setup.md), [references/managed-knowledge-bases-retrieval.md](references/managed-knowledge-bases-retrieval.md), [references/knowledge-bases-setup.md](references/knowledge-bases-setup.md), [references/knowledge-bases-retrieval.md](references/knowledge-bases-retrieval.md) |
| **Guardrails** | Present the 3 integration modes + decision guide first so the user picks the mode; always surface the PII CloudWatch logging compliance warning when PII filters are used. | [references/guardrails.md](references/guardrails.md) |
| **AgentCore Harness (Default Agent Loop)** | Config-based managed loop (no custom container). Cover all 5 steps: (1) `create-harness`, (2) poll `get-harness` until `READY`, (3) invoke data plane with `runtimeSessionId` (≥33 chars) + `messages` list (not `--input-text`), (4) read streamed events, (5) `agentcore` CLI (`create`/`deploy`/`invoke`). | [references/agentcore-harness.md](references/agentcore-harness.md) |
| **Migrate Classic Bedrock Agent → Harness** | Audit eligibility, export config (`scripts/fetch_bedrock_agent.py` pattern via read-only MCP), map action groups/KBs (`assets/*.tmpl`), and generate Harness config. | [references/migrate-bedrock-agents-to-agentcore-harness.md](references/migrate-bedrock-agents-to-agentcore-harness.md) |
| **Classic Bedrock Agents (Maintenance)** | Follow step-by-step action group setup; **always** run `prepare-agent` after any configuration change. | [references/agents-and-action-groups.md](references/agents-and-action-groups.md) |
| **Prompt Caching** | Check per-model minimum token thresholds, TTL, and prefix determinism; walk the zero-hit debug checklist (`cacheReadInputTokens`). | [references/prompt-caching.md](references/prompt-caching.md) |
| **Quota Health & Throttling** | Explain `maxTokens` reservation math; compare `service-quotas` limits against peak CloudWatch token/invocation metrics. | [references/quota-health.md](references/quota-health.md) |
| **Cost Tracking** | Ask for time range, grouping, and attribution method before building Cost Explorer / CUR 2.0 / inference-profile tag queries. | [references/cost-tracking.md](references/cost-tracking.md) |
| **Claude Generation Migration (4.5 → 4.6 → 4.7)** | Flag assistant prefill removal (400 error in 4.6+), adaptive thinking config changes, context window shifts, and cache thresholds. | [references/model-migration.md](references/model-migration.md) |

## AgentCore Services

Always read the linked service reference before answering AgentCore architecture or implementation questions:

| Service | Use For | Reference |
|---|---|---|
| **Harness** | Config-based managed agent loop without custom orchestration code | [references/agentcore-harness.md](references/agentcore-harness.md) |
| **Runtime & Container** | Host custom agent loops (HTTP or MCP protocol) in serverless ARM64 containers | [references/agentcore-runtime.md](references/agentcore-runtime.md), [references/agentcore-runtime-container-build.md](references/agentcore-runtime-container-build.md) |
| **Gateway & Auth** | Expose REST APIs, Lambda functions, or MCP servers as authenticated agent tools | [references/agentcore-gateway.md](references/agentcore-gateway.md), [references/agentcore-gateway-auth.md](references/agentcore-gateway-auth.md) |
| **Memory & Observability** | Short-term/long-term agent memory plus OpenTelemetry + CloudWatch tracing | [references/agentcore-memory-observability.md](references/agentcore-memory-observability.md) |
| **Identity & Credentials** | OAuth2/OIDC IdP integration (Okta, Entra ID, Cognito) and credential vaults | [references/agentcore-credentials-and-security.md](references/agentcore-credentials-and-security.md) |
| **Payments (x402)** | Microtransactions for paid APIs/MCP tools via Payment Manager (Coinbase CDP, Stripe Privy) | [references/agentcore-payments.md](references/agentcore-payments.md), [references/agentcore-payments-wiring.md](references/agentcore-payments-wiring.md), [references/agentcore-payments-setup-script.md](references/agentcore-payments-setup-script.md) |
| **Registry & Evaluations** | Org-wide catalog for agents/tools/skills + automated LLM-as-a-Judge evaluation | [references/agentcore-registry-evaluations.md](references/agentcore-registry-evaluations.md) |
| **Policy / Code Interpreter / Browser** | Cedar/NL tool-call boundaries, sandboxed code execution, and managed web automation | [AgentCore Developer Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html) |

## Troubleshooting Summary

Retry **only** `ThrottlingException`, `ModelTimeoutException`, `ServiceUnavailableException`, and `InternalServerException` using `Config(retries={"max_attempts": 5, "mode": "adaptive"})`; **do NOT retry** `ValidationException`, `AccessDeniedException`, or `ResourceNotFoundException`. Read [references/troubleshooting-matrix.md](references/troubleshooting-matrix.md) for full diagnostic procedures.

| Error / Symptom | Primary Root Causes & Immediate Remediation |
|---|---|
| `AccessDeniedException` | Missing `bedrock:InvokeModel*` (on both inference-profile + foundation-model ARNs), unenabled model/FTU form, regional SCP block on CRIS destination, expired credentials, or IAM propagation delay. |
| `ThrottlingException` | Unset `maxTokens` reserving max context tokens; switch to `us.`/`eu.`/`apac.`/`global.` inference profiles, enable adaptive retry, and audit quotas ([references/quota-health.md](references/quota-health.md)). |
| `Malformed input request` / `400` on prefill | Provider body mismatch in `InvokeModel` (switch to `Converse`), or assistant prefill used on Claude 4.6+ ([references/model-migration.md](references/model-migration.md)). |
| `On-demand throughput isn't supported` / Cross-region not found | Model requires an Inference Profile ID/ARN (`ListInferenceProfiles`); choose geographic (`us.`, `eu.`) vs `global.` profile based on data residency. |
| `UnknownOperationException` | Wrong client (`bedrock` vs `bedrock-runtime` / `bedrock-agent`) or outdated `boto3` (< 1.34.x). |
| Zero `cacheReadInputTokens` | Below model min-token floor, dynamic timestamps/key reordering breaking prefix match, or wrong `cachePoint` placement ([references/prompt-caching.md](references/prompt-caching.md)). |
| Stale classic Agent / Action Group error / Supervisor loop | Run mandatory `prepare-agent` after edits; add `bedrock.amazonaws.com` Lambda permission; avoid `__` in action group names; use `agentCollaboration` (not action groups) for multi-agent routing. |
| KB empty / poor quality / storage / ingestion / SharePoint errors | Wait for `StartIngestionJob` completion; use FM advanced parsing + metadata filters; verify OpenSearch & S3 (`GetObject`/`ListBucket`) roles; for SharePoint use Entra ID `OAUTH2_CLIENT_CREDENTIALS` (`Sites.Read.All`) — Azure ACS App-Only retired April 2, 2026. |
| `INVALID_PAYMENT_INSTRUMENT` | AWS account billing/payment method issue in Organizations management account (not IAM). |

## Model Selection

Read [references/model-selection-guide.md](references/model-selection-guide.md) and verify live regional availability via MCP (`bedrock` `ListFoundationModels` / `ListInferenceProfiles`) before recommending specific IDs:
- **General purpose:** Claude Sonnet (balanced quality/cost) · **Fast & low-cost:** Claude Haiku or Amazon Nova Micro
- **KB Embeddings:** Titan Text Embeddings V2 · **Open-weight:** Llama · **Image generation:** Nova Canvas / Titan Image Generator
- **Data residency:** Geographic inference profiles (`us.`, `eu.`, `apac.`) keep inference in-boundary; `global.` profiles route across any commercial AWS region.
