# Provider & Multi-Upstream Gateway Detection (`OpenRouter`, `LiteLLM`, Direct SDKs)

Use these codebase inspection patterns during `discover-ai` (and inside `heroku-to-aws`, `gcp-to-aws`, and `azure-to-aws` discovery phases) to detect direct LLM SDK usage as well as multi-upstream proxy gateways.

---

## 1. Multi-Upstream AI Gateways (`OpenRouter`, `LiteLLM`, Custom Proxies)

Startups frequently prototype with **OpenRouter** (`https://openrouter.ai/api/v1`) or **LiteLLM** using the standard OpenAI SDK (`new OpenAI({ baseURL: "https://openrouter.ai/api/v1" })`) to switch between Claude, GPT, Gemini, and DeepSeek models with a single API key.

### Detection Signatures

| Gateway | Code / Config Signatures | Env Var Signatures (`.env.example`, `app.json`, IaC) |
|---|---|---|
| **OpenRouter** | `openrouter.ai/api/v1`, `@openrouter/ai-sdk-provider`, `HTTP-Referer` + `X-Title` headers on OpenAI client, model strings formatted as `vendor/model` (`anthropic/claude-*`, `google/gemini-*`, `meta-llama/*`, `deepseek/*`) | `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `NEXT_PUBLIC_OPENROUTER_*` |
| **LiteLLM** | `litellm.completion`, `litellm.acompletion`, `Router(model_list=...)`, `litellm_params` | `LITELLM_MASTER_KEY`, `LITELLM_PROXY_URL` |
| **Vercel AI SDK** | `@ai-sdk/openai`, `@ai-sdk/anthropic`, `@ai-sdk/google`, `@ai-sdk/amazon-bedrock`, `generateText`, `streamText`, `generateObject` | `AI_GATEWAY_API_KEY` |

### Why Migrate OpenRouter to Amazon Bedrock?

1. **Eliminate Pass-Through Markup**: OpenRouter charges a ~5.5% credit purchase fee on top of underlying provider token rates.
2. **Unlock AWS Activate Credits**: OpenRouter invoices cannot be paid with AWS Activate credits. Moving `anthropic/*`, `openai/*`, `deepseek/*`, and `meta-llama/*` routes to Amazon Bedrock shifts 100% of token spend onto AWS Activate credits.
3. **Unified Multi-Vendor Access via Bedrock Converse**: Amazon Bedrock natively hosts Anthropic Claude, OpenAI GPT-5.x (`bedrock-mantle`), Meta Llama, DeepSeek, Mistral, and Amazon Nova behind a single IAM-authenticated API (`Converse` / `ConverseStream`) with zero static API keys to rotate.
4. **Minimal Diff Option for Vercel AI SDK**: If the startup uses Vercel AI SDK (`ai`), swapping `@openrouter/ai-sdk-provider` or `@ai-sdk/openai` to `@ai-sdk/amazon-bedrock` (`bedrock('us.anthropic.claude-sonnet-5')`) is a 3-line provider import change that preserves all existing `streamText` / `generateObject` call sites.

---

## 2. Direct Provider SDK Detection Matrix

| Provider | Python Packages | Node / TypeScript Packages | Go / Ruby / Rust / Java |
|---|---|---|---|
| **OpenAI (1P & Azure OpenAI)** | `openai`, `langchain-openai`, `llama-index-llms-openai` | `openai`, `@ai-sdk/openai`, `@langchain/openai` | `github.com/sashabaranov/go-openai`, `ruby-openai`, `async-openai` |
| **Anthropic (1P)** | `anthropic`, `langchain-anthropic` | `@anthropic-ai/sdk`, `@ai-sdk/anthropic` | `anthropic-sdk-go`, `anthropic` (gem) |
| **Google Gemini / Vertex AI** | `google-genai`, `google-generativeai`, `google-cloud-aiplatform`, `vertexai` | `@google/genai`, `@google/generative-ai`, `@google-cloud/vertexai`, `@ai-sdk/google` | `cloud.google.com/go/vertexai`, `google.golang.org/genai` |
| **Agent Frameworks** | `langgraph`, `crewai`, `autogen`, `pydantic-ai`, `smolagents`, `agents` (OpenAI Agents SDK) | `@langchain/langgraph`, `ai` (tool loops), `@mastra/core` | `langchaingo` |

---

## 3. OpenRouter Model String → Bedrock Target Mapping Table

When an OpenRouter routing table or config file lists multiple upstream models, map each `vendor/model` slug using this table:

| OpenRouter Model Slug | Recommended Bedrock Target ID | Endpoint / API | `same_model_family` |
|---|---|---|---|
| `anthropic/claude-3.5-sonnet`, `anthropic/claude-3.7-sonnet`, `anthropic/claude-sonnet-4*` | `us.anthropic.claude-sonnet-5` (or `us.anthropic.claude-sonnet-4-6`) | `bedrock-runtime` (`Converse`) | `true` |
| `anthropic/claude-3.5-haiku`, `anthropic/claude-3-haiku` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | `bedrock-runtime` (`Converse`) | `true` |
| `anthropic/claude-3-opus`, `anthropic/claude-opus-4*` | `us.anthropic.claude-opus-4-8` | `bedrock-runtime` (`Converse`) | `true` |
| `openai/gpt-4o`, `openai/gpt-4.1`, `openai/gpt-5*` | `us.anthropic.claude-sonnet-5` (cross-family default) OR `global.openai.gpt-5.6-terra` / `global.openai.gpt-5.6-sol` (same-family mantle) | `bedrock-runtime` (`Converse`) or `bedrock-mantle` | `false` (Claude) / `true` (Mantle GPT) |
| `openai/gpt-4o-mini`, `openai/gpt-4.1-mini`, `openai/gpt-4.1-nano` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` (or `amazon.nova-lite-v1:0` / `global.openai.gpt-5.6-luna`) | `bedrock-runtime` (`Converse`) or `bedrock-mantle` | `false` (Claude/Nova) / `true` (Mantle) |
| `google/gemini-2.5-pro`, `google/gemini-1.5-pro` | `us.anthropic.claude-sonnet-5` | `bedrock-runtime` (`Converse`) | `false` |
| `google/gemini-2.5-flash`, `google/gemini-2.0-flash` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` or `us.amazon.nova-lite-v1:0` | `bedrock-runtime` (`Converse`) | `false` |
| `deepseek/deepseek-r1` | `us.deepseek.r1-v1:0` | `bedrock-runtime` (`Converse`) | `true` |
