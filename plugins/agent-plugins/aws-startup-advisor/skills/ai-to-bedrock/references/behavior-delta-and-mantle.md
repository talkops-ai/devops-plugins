# Behavior-Delta Detection, `bedrock-mantle` GPT Models & Bedrock Runtime Known Fixes

This reference consolidates the mandatory code-safety guardrails shared between `ai-to-bedrock` and `llm-to-bedrock`.

---

## 1. `bedrock-mantle` Proprietary OpenAI Models vs. Cross-Family Converse Models

Amazon Bedrock supports two distinct target paths for migrating OpenAI workloads:

| Path | Target Model IDs | Endpoint / API Surface | `same_model_family` | Parameter-Surface Deltas (`temperature`, `presence_penalty`, `frequency_penalty`, `stop`) |
|---|---|---|---|---|
| **Path A: Proprietary GPT on Bedrock (`bedrock-mantle` / CRIS)** | `openai.gpt-5.6-sol`, `openai.gpt-5.6-terra`, `openai.gpt-5.6-luna`, `openai.gpt-5.5`, `openai.gpt-5.4`, plus `us.openai.gpt-5.6-*`, `in.openai.gpt-5.6-*`, `global.openai.gpt-5.6-*` | `bedrock-mantle` / OpenAI Responses API surface (or `bedrock-runtime` for CRIS) | `true` | **DO NOT APPLY.** The underlying model is unchanged. Prompting the user to cap `temperature` or drop penalty parameters is a false positive. Only check API-surface deltas (Chat Completions → Responses and reasoning item echo across turns). |
| **Path B: Cross-Family Migration to Claude / Nova / DeepSeek / `gpt-oss`** | `us.anthropic.claude-sonnet-5`, `us.anthropic.claude-haiku-4-5-20251001-v1:0`, `us.anthropic.claude-opus-4-8`, `us.amazon.nova-*`, `openai.gpt-oss-*` | `bedrock-runtime` (`Converse` / `ConverseStream`) | `false` | **APPLY FULL DELTA DETECTION.** Inspect `temperature ∈ [0, 2]` → `[0, 1]`, `presence_penalty` / `frequency_penalty` removal, `logprobs`, `n > 1`, and `seed`. |

### Pricing & Residency Nuance for `openai.gpt-5.6-*`

- **Global CRIS (`global.openai.gpt-5.6-sol`, `-terra`, `-luna`)**: 1.0x OpenAI standard list price (exact cost parity, plus eligible for AWS Activate credits). Recommend for startups without strict single-geography residency requirements.
- **Geo CRIS (`us.openai.gpt-5.6-*`, `in.openai.gpt-5.6-*`) and bare mantle IDs**: 1.10x OpenAI standard list price (parity with OpenAI's Data Residency tier).
- **PriceList API Caveat**: The live AWS PriceList API (`pricing:GetProducts`) does **not** return rows for `openai.gpt-5*` models. Never report them as "unavailable" when `GetProducts` returns empty — always read their rates from [`../../shared/pricing/bedrock-pricing.json`](../../shared/pricing/bedrock-pricing.json) or `skills/llm-to-bedrock/scripts/bedrock_pricing.py`.

---

## 2. Preventing Silent UX Changes (Behavior-Delta Protocol)

Never silently clamp a UI slider or delete a user-facing parameter during a cross-family migration (`same_model_family == false` and `user_visible == true`):

1. **One Question Per Location**: Present a separate question for each file:line hit so the user knows every UI surface affected.
2. **Fixed Option Sets**:
   - **`range_narrowed`** (e.g., `temperature` `0..2` → `0..1`):
     1. *Cap UI to target range (Recommended)*
     2. *Linear rescale source range to target range* (`target = source * (target_max / source_max)`)
     3. *Keep UI + add description note*
     4. *Keep UI + fail loud on out-of-range*
   - **`parameter_removed`** (e.g., `presence_penalty`, `frequency_penalty`, Gemini `candidate_count > 1`):
     1. *Drop UI control + remove from API call (Recommended)*
     2. *Hide UI control + ignore in API call*
     3. *Keep UI control as inert decoration*
3. **Defense-in-Depth Fallback**: If an unlisted user-visible parameter is encountered mid-rewrite, leave the original code intact, add `# TODO: Bedrock incompatibility — needs manual review`, and record `source: "missing_confirmation_safe_default"`.

---

## 3. Critical Bedrock Runtime Known Fixes

Always verify these three invariants in every generated or rewritten Bedrock file:

1. **Lowercase `response["body"]` on `boto3` `invoke_model`**:
   - `boto3.client("bedrock-runtime").invoke_model(...)` returns a dict with lowercase `"body"` (`StreamingBody`), whereas `"ResponseMetadata"` is PascalCase.
   - **Correct**: `payload = json.loads(response["body"].read())`
   - **Wrong (Runtime Crash)**: `response["Body"].read()` → raises `KeyError: 'Body'`.
2. **Converse API Stream Unpacking**:
   - `converse_stream()` returns `response["stream"]`, where text chunks arrive under `event["contentBlockDelta"]["delta"]["text"]`.
3. **Dual-ARN IAM Policy for Cross-Region Inference Profiles**:
   - Any IAM role invoking `us.anthropic.*`, `eu.anthropic.*`, or `global.openai.*` must allow `bedrock:InvokeModel*` on both:
     - `arn:aws:bedrock:*:<account-id>:inference-profile/*`
     - `arn:aws:bedrock:*::foundation-model/*`
