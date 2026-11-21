---
name: ai-to-bedrock
description: >-
  Provider-neutral AI and LLM migration engine that decouples application-code AI/LLM discovery,
  target model mapping, token cost estimation, behavior-delta detection, and SDK/gateway rewrites
  to Amazon Bedrock and Amazon Bedrock AgentCore from cloud infrastructure migrations. Use when
  migrating OpenAI, Anthropic, Google Gemini/Vertex AI, Azure OpenAI, or multi-upstream gateways
  (OpenRouter, LiteLLM) to Amazon Bedrock — either standalone or as the AI track alongside
  heroku-to-aws, gcp-to-aws, or azure-to-aws.
  Always query live AWS state via connected MCP tools (never raw aws CLI).
---

# AI-to-Bedrock — Decoupled Provider-Neutral AI Migration Engine

`ai-to-bedrock` is the unified, source-cloud-agnostic AI migration engine for `aws-startup-advisor`. It separates **application-code AI/LLM migration** (`.saws-migrate/aws-design-ai.json`) from **cloud infrastructure migration** (`.saws-migrate/aws-design.json`), enabling:

1. **PaaS + AI Co-Migrations (`heroku-to-aws`, `gcp-to-aws`, `azure-to-aws`)**: A Heroku or Cloud Run app calling OpenAI, Anthropic, Gemini, or OpenRouter can migrate its compute/database via the infrastructure track while `ai-to-bedrock` migrates its AI SDKs and gateway endpoints to Amazon Bedrock so 100% of LLM token spend is covered by AWS Activate credits.
2. **Multi-Upstream AI Gateway Consolidation**: Detects `OpenRouter` (`https://openrouter.ai/api/v1`, `OPENROUTER_API_KEY`), `LiteLLM`, and custom OpenAI-compatible routers, mapping multi-model routing tables onto Bedrock Cross-Region Inference Profiles (`us.anthropic.*`, `us.amazon.nova-*`, `global.openai.gpt-5.6-*`) and eliminating 5.5% gateway pass-through fees.
3. **Standalone App-Code AI Rewrites**: Coordinates directly with `llm-to-bedrock` worker sub-agents (`llm2bedrock-code-analyzer`, `llm2bedrock-code-rewriter`, `llm2bedrock-prompt-evaluator`, `llm2bedrock-log-ingestor`, `llm2bedrock-report-generator`) when the user only wants to migrate LLM calls without touching hosting infrastructure.

## MCP-Only Execution & Read-Only Safety

- **MCP-Only Live Queries:** Execute **all** live AWS discovery, Bedrock/SageMaker control-plane checks, pricing lookups, IaC compliance checks, CloudWatch telemetry queries, and documentation searches **exclusively via connected MCP tools**: `aws-mcp` (`aws___run_script` using read-only `await call_boto3(...)`, `aws___search_documentation`, `aws___read_documentation`), `sagemaker` (`describe_hp_cluster`), `agentcore`, `strands-agents`, `cloudwatch`, `awspricing` / `aws-pricing` (`get_pricing`, `get_bedrock_patterns`), `awsiac`, and `awsknowledge`. Offline pure-Python bundled helper scripts in `scripts/*.py` that perform local math/schema rendering without live AWS credentials are permitted when inspecting local inputs, whereas live AWS API queries must go through MCP rather than raw `aws` CLI or boto3 shell scripts.
- **Strict Read-Only & Secret Safety:** **Never** run raw `aws ...` (not even `aws sts get-caller-identity` — always query `sts.GetCallerIdentity` inside `aws___run_script`) CLI commands in Bash/`run_command`, **never** mutate live AWS resources (`Create*`, `Update*`, `Delete*`, `InvokeModel`, `CreateEndpoint` — refuse unapproved mutations and present a safe, approval-gated plan with verification and rollback steps), and **never** read or expose plaintext secrets (`secretsmanager:GetSecretValue`, `ssm:GetParameter` with `WithDecryption=True`, or `.env` API keys — inspect `.env.example` only).
- **Unmapped Edge Cases:** Query `awsknowledge` / `aws-mcp` documentation search tools (`aws___search_documentation`, `aws___read_documentation`) with 1–2 focused queries before recommending unverified parameters.

---

## Progressive-Disclosure References

Load only the reference file needed for the active phase:

| Phase / Topic | Reference File | When to Load |
|---|---|---|
| **Contract & State Schema** | [`references/aws-design-ai-contract.md`](./references/aws-design-ai-contract.md) | When reading or writing `.saws-migrate/discover-ai.json` and `.saws-migrate/aws-design-ai.json` |
| **Provider & Gateway Discovery** | [`references/provider-gateway-detection.md`](./references/provider-gateway-detection.md) | During codebase scan for OpenAI, Anthropic, Gemini, Azure OpenAI, OpenRouter, LiteLLM, or agent frameworks |
| **Behavior Deltas & Bedrock Mantle** | [`references/behavior-delta-and-mantle.md`](./references/behavior-delta-and-mantle.md) | Before prompting the user on parameter differences or selecting `bedrock-mantle` (`openai.gpt-5*`) vs Converse |
| **Shared Canonical AI Guardrails** | [`references/shared/ai/ai-migration-guardrails.md`](./references/shared/ai/ai-migration-guardrails.md) | Before generating any Bedrock client, IAM policy, or AgentCore runtime code |
| **Model Lifecycle & 90-Day Rule** | [`references/shared/ai/ai-model-lifecycle.md`](./references/shared/ai/ai-model-lifecycle.md) | When validating that no Legacy or <90-day-to-EOL Bedrock model is recommended |
| **Shared Bedrock Token Pricing** | [`references/shared/pricing/bedrock-pricing.json`](./references/shared/pricing/bedrock-pricing.json) | During the `estimate` phase for token cost comparison and Activate credit burn projection |

---

## End-to-End Workflow

### Phase 1: Codebase-First AI Discovery (`discover-ai`)

1. **Inspect Dependency Manifests & Env Templates First**:
   - Check `package.json`, `pyproject.toml`, `requirements.txt`, `go.mod`, `Gemfile`, `Cargo.toml`, and `.env.example` (never read live `.env` files — blocked by `secret-safety.py`).
   - Run the detection patterns in [`references/provider-gateway-detection.md`](./references/provider-gateway-detection.md) using [`references/shared/ai/sdk-capability-map.json`](./references/shared/ai/sdk-capability-map.json).
2. **Classify Each Call Site**:
   - **Track 1 (Same-Model-Family Swap)**: Anthropic 1P SDK (`@anthropic-ai/sdk`, `anthropic`) → `AnthropicBedrock` client or Bedrock `Converse`; or OpenAI SDK → proprietary GPT-5.x on `bedrock-mantle` (`openai.gpt-5.6-sol`, `openai.gpt-5.6-terra`, `openai.gpt-5.6-luna`, `openai.gpt-5.5`, `openai.gpt-5.4`).
   - **Track 2 (Cross-Family Model + SDK Rewrite)**: OpenAI (`gpt-4o`, `gpt-4o-mini`, `o3-mini`), Google Gemini (`gemini-2.5-pro`, `gemini-2.5-flash`), or OpenRouter multi-model routes → Bedrock `Converse` / `ConverseStream` with Claude 4.5 Haiku / Sonnet 5 / Opus 4.8 or Amazon Nova Micro/Lite/Pro.
   - **Track 3 (Agentic Harness / Runtime Migration)**: LangGraph, CrewAI, AutoGen, OpenAI Assistants/Responses API, or custom tool loops → Strands Agents SDK + Amazon Bedrock AgentCore Runtime (delegate runtime architecture decisions to `agent-advisor`).
3. **Write `.saws-migrate/discover-ai.json`**:
   - Emit the normalized discovery payload defined in [`references/aws-design-ai-contract.md`](./references/aws-design-ai-contract.md).

### Phase 2: Target Model Mapping & Cost Estimation (`design-ai` + `estimate-ai`)

1. **Enforce the 90-Day EOL Exclusion Rule**:
   - Check [`references/shared/ai/ai-model-lifecycle.md`](./references/shared/ai/ai-model-lifecycle.md). Never recommend a model marked `Legacy` or within 90 days of EOL.
2. **Always Prefer Cross-Region Inference Profiles (CRIS) for Converse Models**:
   - Use `us.anthropic.claude-sonnet-5`, `us.anthropic.claude-haiku-4-5-20251001-v1:0`, `us.anthropic.claude-opus-4-8`, or `us.amazon.nova-pro-v1:0` (or `apac.*` / `in.*` / `global.*` matching the target region) rather than bare single-region foundation model IDs so startups get higher default RPM/TPM burst capacity without Provisioned Throughput commitments.
   - **Never recommend Provisioned Model Throughput (`bedrock:CreateProvisionedModelThroughput`) to Pre-Revenue or Seed startups** — on-demand CRIS is pay-per-token with $0 idle burn.
3. **Check `bedrock-mantle` Eligibility for OpenAI Workloads**:
   - When the startup requires exact GPT-5.x prompt parity (`openai.gpt-5.6-sol`, `openai.gpt-5.6-terra`, `openai.gpt-5.6-luna`, `openai.gpt-5.5`, `openai.gpt-5.4`), evaluate whether `global.openai.gpt-5.6-*` (1.0x OpenAI list-price parity) or `us.openai.gpt-5.6-*` / `in.openai.gpt-5.6-*` / bare mantle ID (1.10x data-residency parity, invoked at `https://bedrock-mantle.{region}.api.aws/openai/v1` via `BedrockOpenAI` + `aws_bedrock_token_generator` / `provide_token`) fits their compliance posture.
4. **Price Token Spend Against [`references/shared/pricing/bedrock-pricing.json`](./references/shared/pricing/bedrock-pricing.json)**:
   - Compute monthly input/output token cost on source provider vs. Bedrock, highlight **Batch Inference (`50%` discount, backed by a separate quota pool that does not consume real-time on-demand RPM/TPM quotas)** for async/offline jobs and **On-Demand CRIS (`global.*` ~10% savings where residency permits) + Prompt Caching (`cachePoint`, up to `90%` read discount)** for interactive workloads **rather than premature Provisioned Model Throughput lock-in**, and show how many months of AWS Activate credits the AI workload consumes.
5. **Always Reference & Persist Decoupled `.saws-migrate/discover-ai.json` & `.saws-migrate/aws-design-ai.json`**:
   - Explicitly mention both `.saws-migrate/discover-ai.json` and `.saws-migrate/aws-design-ai.json` in consolidation/migration plans — `ai-to-bedrock` aligns target region/roles with `.saws-migrate/aws-design.json` when present without overwriting it, and companion infra generators (`heroku-to-aws`, `gcp-to-aws`, `azure-to-aws`) read `aws-design-ai.json` (`iam_policy_statements`, `required_env_vars`) to wire workload IAM roles and env vars cleanly.

### Phase 3: Behavior-Delta Detection & Code Rewrite (`rewrite-ai`)

1. **Run Behavior-Delta Detection Before Modifying Any Code**:
   - Follow [`references/behavior-delta-and-mantle.md`](./references/behavior-delta-and-mantle.md) and `skills/llm-to-bedrock/references/helpers/behavior-delta-detection/behavior-delta-detection.md`.
   - **Critical Guardrail**: When `same_model_family == true` (Anthropic 1P → Bedrock OR OpenAI → `openai.gpt-5*` on `bedrock-mantle`), **skip** parameter-surface range prompts (`temperature`, `presence_penalty`, `frequency_penalty`, `stop` limits) to avoid prompting the user for range changes that are not happening. Only check API-surface and statefulness deltas:
     - **Bedrock Responses Endpoint (`bedrock-mantle` `/openai/v1` — never bare `/v1` — via `BedrockOpenAI` + `aws_bedrock_token_generator` / `aws-bedrock-token-generator`, or `bedrock-runtime` `/openai/v1`)**: `store: true` and `previous_response_id` work for server-side chaining (review Bedrock retention/ZDR posture), whereas with `store: false` or manual multi-turn `input` arrays **`response.output` reasoning items MUST round-trip (`reasoning-items-must-round-trip` — append full `response.output` items across turns rather than extracting text strings alone)**.
     - **Stateless `bedrock-runtime` `Converse` / `ConverseStream` (`in.*` / `us.*` / `global.*` CRIS)**: `previous_response_id` and `store: true` do not exist on `Converse`; the caller or **Amazon Bedrock AgentCore Memory** must persist and replay conversation history across turns.
   - When `same_model_family == false` and `user_visible == true`, present the exact numbered option set (`range_narrowed`, `parameter_removed`, or `fallback`) via `ask_question` and record the user's choice in `behavior_delta_decisions`.
2. **Enforce Bedrock Runtime Known Fixes**:
   - **Lowercase `response["body"]` Rule**: `boto3` `bedrock-runtime` `invoke_model()` returns `response["body"]` (lowercase), whereas `ResponseMetadata` uses PascalCase. Never generate `response["Body"]` (raises `KeyError: 'Body'` at runtime).
   - **IAM Dual-ARN Policy Rule**: When using Cross-Region Inference Profiles (`us.anthropic.*`, `global.openai.*`), the IAM policy MUST grant `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` on **both** `arn:aws:bedrock:*:<account_id>:inference-profile/*` AND `arn:aws:bedrock:*::foundation-model/*`.
3. **Delegate Heavy Multi-File Rewrites & Prompt Evaluation**:
   - For multi-file SDK rewrites, baseline prompt comparison, or production log replay, dispatch the specialized `llm-to-bedrock` worker sub-agents (`llm2bedrock-code-analyzer`, `llm2bedrock-code-rewriter`, `llm2bedrock-prompt-evaluator`, `llm2bedrock-report-generator`).
