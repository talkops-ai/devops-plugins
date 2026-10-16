---
name: model-selection
description: >-
  Selects a base model or ML algorithm pathway for the user's use case. Performs an Architectural
  Triage Gate first (routing Tabular/Time-Series to SageMaker Autopilot/Canvas and Custom Vision
  or Multimodal architectures to sagemaker-training-architect), then queries SageMaker Hub for
  Foundation Model selection (fine-tuning or direct base model deployment). Resolves exact Hub
  model IDs, filters deployable configs, checks JumpStart EULA GatedBucket status, and presents
  benchmarks and licenses.
metadata:
  version: "2.0.0"
---

# Model Selection

Guides the user through selecting the right model architecture or SageMaker Hub base model based on their use case.

## When to Use

- User asks which model to use for their problem
- User wants to select or change their base model
- User mentions a model name or family (e.g., "Llama", "Mistral", "Nova", "Qwen", "DeepSeek", "SAM", "XGBoost") — the exact Hub model ID or Estimator pathway must be resolved
- User wants to evaluate or deploy a base model before deciding whether to fine-tune

## Prerequisites

None — this skill can be entered directly (though recommending `use-case-specification` first is preferred when no `*_use_case_spec.md` exists).

---

## Step 0: Architectural Modality Triage Gate (Check FIRST)

Before querying the SageMaker JumpStart Hub LLM catalog, verify that a Foundation Model from JumpStart Hub is actually the right architecture for the user's modality:

1. **Tabular Classification, Regression, or Time-Series Forecasting** (structured CSV/Parquet rows, churn, fraud, demand forecasting):
   - Do **not** force an LLM from the JumpStart text catalog.
   - Recommend **SageMaker Autopilot (AutoML API v2 `CreateAutoMLJobV2`)** (`TabularJobConfig` or `TimeSeriesForecastingJobConfig`), **SageMaker Canvas**, or a managed **XGBoost / LightGBM Estimator**, and hand off to **`sagemaker-training-architect`** (or `sagemaker-solution-architect`).
2. **Custom Computer Vision, Segmentation, Detection, or Custom PyTorch/HuggingFace Architecture** (e.g., fine-tuning Meta's Segment Anything Model `facebook/sam-vit-base` / `sam-vit-large` / `sam-vit-huge` by freezing `vision_encoder` + `prompt_encoder` and training `mask_decoder`, or training YOLOv8/ViT/ResNet):
   - Do **not** restrict the user to Serverless LLM recipes.
   - Route to **`sagemaker-training-architect`** to configure a PyTorch/HuggingFace Estimator or `@remote` training job with GPU instances (`ml.g5` / `ml.g6` / `ml.p4d`) and Managed Spot checkpointing.
3. **Zero-Shot Foundation Model or RAG on Proprietary Documents** (no weight customization or dedicated GPU hosting needed):
   - Inform the user that **Amazon Bedrock** (Converse API + Knowledge Bases) can serve zero-shot or RAG workloads serverlessly without paying for 24/7 SageMaker GPU instances, unless they specifically require open-weight hosting on a SageMaker Endpoint or Serverless Model Customization.
4. **Foundation Model Customization (SFT, DPO, RLVR, RLAIF) or JumpStart Base Model Deployment**:
   - Proceed with the Routing Rules and Step 1 below.

---

### Routing Rules (Foundation Model Selection)

1. **Ambiguity gate:** If it is unclear whether the user wants to **fine-tune** a model or **deploy a base model as-is**, you MUST ask before proceeding. Do not assume either path. **Do NOT recommend, list, or name any models until this is resolved.**

2. **Recommend use-case-spec first:** If no `*_use_case_spec.md` file exists for this use case, recommend creating one via `use-case-specification` before filtering. This produces better results because the spec captures constraints that map to concrete filter values. If the user declines or provides a specific model name/ID, proceed without it. **After making this recommendation, stop and wait for the user's response. Do not continue with model selection in the same turn.**

3. **Base model filtering MUST use select-for-deployment:** When making a final model selection or recommendation for deployment, you MUST follow `references/select-for-deployment.md` and use its scripts (`get_deployable_models.py`, `filter_deployable_models.py`). Do not make a final model selection or recommendation for deployment ad-hoc from your own knowledge.

4. **Offer to create a use-case spec after filtering:** If filtering was done without a spec, and no `*_use_case_spec.md` file exists for this use case, offer to create one to refine the criteria for future iterations.

5. **No premature recommendations:** You may provide an initial quick-filtered list of models based on what you know, but do NOT make a recommendation or suggest a specific model as "the best choice" until the full selection workflow (`select-for-deployment` scripts or Step 3A) has been followed. If you have NOT run `get_deployable_models.py` or `get_model_names.py` in this session, you MUST prefix any model list with:

> ⚠️ This is a preliminary list based on general knowledge. I have not yet queried all available models in your Hub. There may be better matches once we run the full selection workflow.

NEVER present a model list without stating whether it came from the Hub scripts or from static reference data.

---

## Workflow

### Step 1: Check Region

Run:

```bash
python -c "import boto3; print(boto3.session.Session().region_name)"
```

- `None` → STOP. Tell user: "Set your region via `export AWS_DEFAULT_REGION=us-west-2` or `aws configure`."
- Set → store REGION in context, continue.

### Step 2: Discover Hub

1. List all available SageMaker Hubs in the user's region by calling the SageMaker `ListHubs` API using the `aws___call_aws` tool.
2. From the results, filter out any hub whose `HubDescription` contains "AI Registry" — these do not contain JumpStart models.
3. The remaining hubs are eligible (e.g., `SageMakerPublicHub` and any private hubs).
4. If exactly one eligible hub exists, use it automatically — do not ask the user.
5. If multiple eligible hubs exist, present them to the user and ask which one to use:

   ```
   I found the following model hubs:
   - SageMakerPublicHub — SageMaker Public Hub
   - Private-Hub-XYZ — Private Hub models
   Which hub would you like to use?
   ```

6. Store the selected hub name for use in subsequent steps.

### Step 3: Select Base Model

Determine the user's goal from the plan, conversation context, or `use_case_spec.md` (check the **## Intent** section):

- If the goal is **fine-tuning / model customization** (Intent says "Fine-tune") → follow [Step 3A: Select for Fine-tuning](#step-3a-select-for-fine-tuning) below.
- If the goal is **base model deployment** (Intent says "Deploy base model") → read `references/select-for-deployment.md` and follow it through all steps (including hosting configuration selection). Then proceed to Step 4 below.

If the intent is ambiguous, ask:

> "Would you like to fine-tune a model, or deploy a base model as-is?"

#### Step 3A: Select for Fine-tuning

First, retrieve all available SageMaker Hub model names by running: `python model-selection/scripts/get_model_names.py <hub-name>`. Note how many models the script returns.

Present all available models to the user with their licenses before making any recommendations. Cross-reference the model list with `references/model-licenses.md` and display each as `<model name> - [<license>](<url>)`. For example: "Qwen3-4B - [Apache 2.0](https://huggingface.co/Qwen/Qwen3-4B/blob/main/LICENSE)"

**Display every model — completeness is required:**

- `get_model_names.py` returns the models in a fixed, deterministic order: **alphabetical by name (A→Z, case-insensitive)**. Present them in exactly that order — do **not** re-sort or reorder the list. (This applies only to this raw availability list; the benchmark ranking tables in `references/model-selection.md` keep their performance order and must not be alphabetized.)
- List **each** model returned by `get_model_names.py` as its own separate line with its own license URL. The number of models you display MUST equal the number the script returned.
- Do **not** omit, drop, or skip any model — even when the list is long.
- Do **not** separate models into Text vs VLM categories. Do **not** exclude VLMs from text-only use cases. Present **all** models in a single unified list regardless of modality.
- Do **not** merge or group models under a shared license, and do **not** collapse similar-looking models into one entry.
- After presenting the list, verify your output: confirm the count of displayed models matches the count returned by the script.

If you already know the model the user wants to use (from conversation context or planning files), confirm that it's in the list, display its license, and move on. Otherwise, help the user pick a model following the instructions in `references/model-selection.md`.

**EULA disclaimer (REQUIRED — you MUST include this whenever you present this model list):**

After presenting the model list, always append this disclaimer:

> "ℹ️ **Note:** Some models in this list require accepting an End-User License Agreement (EULA) before deployment. This is a SageMaker JumpStart requirement that is independent of the model's open-source license. Once you choose a model, I'll tell you whether it requires EULA acceptance."

### Step 4: Confirm Selection

#### 4a. Check EULA gating status

After the user selects a model — on **both** the base model deployment path and the fine-tuning path — check whether that model requires a JumpStart hub EULA acknowledgment. If the `HubContentDocument` was already retrieved earlier in this session, reuse that response. Otherwise, call `describe-hub-content` and check the `GatedBucket` field in the `HubContentDocument` JSON:

```bash
aws sagemaker describe-hub-content \
    --region <region> \
    --hub-name <hub-name> \
    --hub-content-type Model \
    --hub-content-name <selected-model-id>
```

From the response, parse the `HubContentDocument` JSON string and read `GatedBucket`:

- If `GatedBucket` is `true`: the model is **gated** — tell the user this model requires accepting an EULA at deployment time.
- If `GatedBucket` is `false` or absent: the model is **not gated** — tell the user this model does not require accepting an EULA.

If the `describe-hub-content` call fails, do not block selection — tell the user the gating status could not be determined and recommend they verify the model's license terms independently.

#### 4b. Present confirmation summary

Present a summary to the user:

```
Here's what we've selected:
- Base model: <model name>
- EULA required at deploy: Yes / No
```

If the model is gated, add:

> "⚠️ This model requires accepting an End-User License Agreement (EULA) at deployment time."

For the **base model deployment path**, also carry forward the three fields resolved in `select-for-deployment.md` Step 6:

```
- Model ID (Hub ID): [model_id]
- Instance type: [instance_type]
- Hosting configuration: [inference_config_name, or "none (base config)"]
```

Ask if they'd like to proceed with this model.

## References

- `references/model-selection.md` — Fine-tuning model selection instructions and benchmark descriptions
- `references/select-for-deployment.md` — Base model deployment selection sub-workflow
- `references/model-licenses.md` — Model license information for display during model selection
