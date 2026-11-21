# Access-Only Mode Reference (`llm-to-bedrock`)

Entered from Step `0a-bis` when the user wants Amazon Bedrock **model access** checked or enabled for named models without migrating source code. Access-only mode does **not** require `gcp-to-aws`, never touches source code or git branches, never collects source-provider API keys, and stops after delivering per-model access verdicts and remediation steps.

> **MCP-Only & Read-Only Safety Note:** In strictly read-only environments (such as architecture audits or read-only evaluations where live `InvokeModel`/`Converse` probes are gated), inspect foundation model availability, inference profiles (`ListFoundationModels`, `ListInferenceProfiles`), and IAM policy posture via `aws-mcp` (`aws___run_script` using read-only `await call_boto3(...)`), and report unprobed runtime entitlements honestly as **access unverified (read-only mode)** rather than fabricating `enabled & working`.

---

## AC1 — Set Expectations First (Endpoint & Entitlement Mechanics)

Explain these distinctions upfront before collecting model names:

1. **Standard Bedrock Foundation Models (Claude, Llama, Nova, Mistral, etc. on `bedrock-runtime`):**
   - Inference uses `bedrock:InvokeModel` / `Converse`.
   - In **commercial AWS Regions**, access is **enabled automatically on first invoke** once the caller has AWS Marketplace permissions (`aws-marketplace:Subscribe`, `aws-marketplace:Unsubscribe`, `aws-marketplace:ViewSubscriptions`). The Bedrock console **Model access** page remains available for explicit catalog management and is mandatory in AWS GovCloud.
   - **Anthropic** models additionally require a one-time First-Time-Use form (`PutUseCaseForModelAccess`) per account before `bedrock-runtime` invocation (not required when reached via `bedrock-mantle`).
2. **OpenAI Models on Bedrock (Per-ID Endpoint & IAM Rules):**
   - **Open-weight `gpt-oss`** (`openai.gpt-oss-20b-1:0`, `openai.gpt-oss-120b-1:0`) → `bedrock-runtime` via `bedrock:InvokeModel` / `Converse` (Responses API also offered on `bedrock-mantle`).
   - **Bare proprietary GPT IDs** (`openai.gpt-5*`, excluding `gpt-oss`) → served on the **`bedrock-mantle`** endpoint (Responses API on `/openai/v1`).
   - **GPT-5.6 Cross-Region Inference Profile (CRIS) IDs** prefixed `us.` / `in.` / `global.` (e.g., `global.openai.gpt-5.6-sol`) → `bedrock-runtime` targets supporting `Converse`.
   - **Distinct IAM Action Set for Mantle:** `bedrock-mantle` uses `bedrock-mantle:*` (e.g., managed policy `AmazonBedrockMantleInferenceAccess`: `bedrock-mantle:CreateInference` + `bedrock-mantle:CallWithBearerToken`), completely separate from `bedrock:InvokeModel`.
   - Hosted `api.openai.com` remains OpenAI's external service; "GPT on Bedrock" refers strictly to AWS-hosted endpoints governed by AWS IAM.

---

## AC2 — Collect Requested Models & Target Region (Before Resolving Names)

1. **Models (`$REQUESTED_MODELS`):** If `$ARGUMENTS` already specifies model IDs or names, capture them; otherwise ask via **AskUserQuestion**: `"Which models do you want access to? Give Bedrock model IDs (e.g. anthropic.claude-sonnet-4-5-v1:0, openai.gpt-oss-120b-1:0) or provider + name and I'll resolve the ID."`
   - **Do NOT resolve friendly names yet** — catalog queries (`ListFoundationModels` / `ListInferenceProfiles`) depend on confirmed `$REGION` and AWS identity (`AC3`).
2. **Region (`$REGION`):** Ask `"Which AWS region? (default us-east-1)"`.

---

## AC3 — Confirm AWS Identity & Profile

Verify caller identity (`sts` `GetCallerIdentity` via `aws-mcp`) and confirm `Account`, `Arn`, and `UserId` with the user (same profile-selection contract as Phase `B2`, recording `$AWS_PROFILE_CHOICE` if non-default). Do not proceed until identity is confirmed.

---

## AC3.5 — Resolve Friendly Model Names

For each item in `$REQUESTED_MODELS` that is not already an exact Bedrock model/profile ID:
1. Follow `$HELPERS/resolve-bedrock-model-id/resolve-bedrock-model-id.md` against `$REGION` under the confirmed identity (`$AWS_PROFILE_CHOICE` if set).
2. Confirm resolved IDs with the user and store the final list in `$TARGET_MODELS`.
3. **Re-resolution rule:** If the user later changes `$REGION` or `$AWS_PROFILE_CHOICE`, re-run AC3.5 for any name-derived entries before re-probing.

---

## AC4 — Preflight Verdict Interpretation (`--dataset-size 0`)

When active probing is approved by the user:

```bash
uv run --project $SCRIPTS python $SCRIPTS/preflight_bedrock.py --region $REGION --models <comma-separated $TARGET_MODELS> --dataset-size 0
```

*(Prepend `AWS_PROFILE=$AWS_PROFILE_CHOICE` inline when using a non-default profile.)*

Interpret each per-model result strictly as follows:

- **`reason: model_access`** → Model exists in `$REGION`, but account entitlement is missing:
  - **Commercial Regions:** Grant caller `aws-marketplace:Subscribe`, `aws-marketplace:Unsubscribe`, and `aws-marketplace:ViewSubscriptions` so first invoke auto-subscribes.
  - **AWS GovCloud — Third-Party Models (two-account sequence, in order):**
    1. Switch to the **linked commercial AWS account** in `us-east-1` or `us-west-2` and invoke/enable the model once (allow several minutes for entitlement propagation).
    2. Switch back to the **GovCloud account** and enable the model on the Bedrock console **Model access** page in **`us-gov-west-1`** specifically (GovCloud's Model access console page exists only in `us-gov-west-1`, regardless of inference `$REGION`). Verify active identity before each step.
  - **AWS GovCloud — Amazon-Provided Models:** Only step 2 (`us-gov-west-1` console Model access page) is required (no commercial Marketplace step).
  - **Anthropic Models:** Submit the one-time First-Time-Use form (`PutUseCaseForModelAccess`) per account (unless invoking via `bedrock-mantle`).
- **`reason: authz`** → Entitlement is fine, but IAM denies inference. Follow `detail` to grant either `bedrock:InvokeModel` (Converse/InvokeModel models, including `gpt-oss` and CRIS profiles) or `bedrock-mantle:*` (`CreateInference`, `CallWithBearerToken` for bare `openai.gpt-5*`).
- **`reason: model_unavailable`** → Model ID is not offered in `$REGION`; suggest a Cross-Region Inference Profile or valid regional ID via `resolve-bedrock-model-id`, re-confirm, and re-test.
- **`reason: credentials` / `mantle_deps_missing` / other** → Surface `detail`, remediate (`uv sync --project $SCRIPTS` or refresh credentials), and re-run.
- **`ok == true` + `reason: embedding_unprobed`** → Unrecognized embedding family; **zero requests were sent**. Report strictly as **`access unverified — no request made`** (never `"enabled"` or `"enabled — unverified"`) and advise a manual console/invoke check.
- **`ok == true` + `reason: throttled_ok`** → Request reached the service and hit `ThrottlingException` / `ServiceQuotaExceededException` / HTTP 429. Report as **`authorized (probe throttled)`** — IAM/access is confirmed, though no model output was observed and quota should be reviewed.
- **`ok == true` (real response returned)** → Report **`enabled & working`** in `$REGION`.

---

## AC5 — Per-Model Summary & Stop

Present a clear per-model table/list mapping each `<model_id>` to its exact status (`enabled & working`, `access unverified — no request made`, `authorized (probe throttled)`, `enable access: <exact prerequisite>`, `grant <exact IAM action>`, or `not available in <region> — use <candidate>`).

- **First-Invoke Propagation Caveat:** For any third-party model newly auto-enabled on first invoke, note that AWS background subscription finalization takes up to ~15 minutes — if Marketplace permissions are incomplete, subsequent calls during/after that window can still surface `AccessDeniedException`.
- Run the **Contextual offers (final step)** check in [references/phase-b-c-execution.md](phase-b-c-execution.md), then **STOP** (no Assess, no git branch, no code changes).
