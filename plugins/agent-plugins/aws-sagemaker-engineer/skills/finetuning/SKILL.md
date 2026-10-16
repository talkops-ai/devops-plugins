---
name: finetuning
description: >-
  Generates code that initiates a SageMaker Serverless Model Customization job and optionally
  creates a reward function for RLVR or configures RLAIF. Supports SFT, DPO, RLVR, and RLAIF
  trainers on SageMaker Hub models. Use when the user says "start training", "fine-tune my model",
  or reaches the fine-tuning step of a Serverless Model Customization plan. For custom PyTorch,
  HuggingFace, XGBoost, Computer Vision (SAM), distributed DDP/FSDP, Managed Spot training jobs,
  or Autopilot AutoMLv2, routes to sagemaker-training-architect; for HyperPod clusters, routes to
  hyperpod-Training.
metadata:
  version: "2.0.0"
---

# Prerequisites

Check that the following are available in the conversation context before starting:

1. A `use_case_spec.md` file exists
   - If missing: Load the `use-case-specification` skill to generate it first, then resume

2. A confirmed model and finetuning strategy (`SFT`, `DPO`, `RLAIF`, or `RLVR`)
   - If missing: Load the `model-selection` and/or `finetuning-technique` skills to collect what's missing, then resume
   - Don't make recommendations on the spot. You MUST load the appropriate skill.

3. A base model name available on SageMakerHub has been identified
   - If missing: Load the `model-selection` skill to get it
   - **Important:** Only use the model name that `model-selection` retrieves, as it may differ from other commonly used names for the same model

4. The SDK environment has been verified (SDK version, region, execution role)
   - If not done: Load the `sdk-getting-started` skill first, then resume

5. The region supports serverless model customization
   - Check the environment's region against `../planning/references/region-availability.md` (`us-west-2`, `us-east-1`, `ap-northeast-1`, `eu-west-1`). If it is NOT supported, STOP and give the user the blocking message from that file — or offer to run a standard Managed Training Job via **`sagemaker-training-architect`**.

6. A training dataset uploaded to a bucket in the environment's default region.
   - If not met: Help the user upload the dataset to the correct S3 bucket.

---

### Routing to Custom & Distributed Training Skills

This skill covers **SageMaker Serverless Model Customization** (`SFTTrainer`, `DPOTrainer`, `RLVRTrainer`, `RLAIFTrainer`). If the user's training workload involves any of the following, route immediately to the dedicated training skill rather than dead-ending:

- **Standard Managed Training Jobs (`CreateTrainingJob`), `@remote` decorator, custom PyTorch/HuggingFace/XGBoost Estimators, Computer Vision / Multimodal fine-tuning (e.g., Segment Anything Model `MaskDecoder`), Distributed Data Parallel (DDP) / FSDP / DeepSpeed, Managed Spot Training with S3 checkpointing, or SageMaker Autopilot AutoMLv2** → Activate **`sagemaker-training-architect`**.
- **SageMaker HyperPod multi-node EKS or Slurm cluster training** → Activate **`hyperpod-Training`**.
- **Provisioning or connecting a SageMaker Managed MLflow App (`CreateMlflowApp`)** → Activate **`manage-mlflow`**.

---

## Critical Rules

### Code Generation Rules

- ✅ Use EXACTLY the imports shown in each code template
- ❌ Do NOT add additional imports even if they seem helpful
- ❌ Do NOT create variables before they're needed in that section
- ❌ Do NOT add custom validation, error handling, or retry logic
- ❌ Do NOT add extra print statements beyond the template
- ❌ Do NOT modify variable names from the template
- ❌ Do NOT add helper functions
- ❌ Do NOT add extra markdown text to explain the code or any sections
- 🎯 Follow the minimal code principle strictly
- ✅ When writing code, make sure the indentation and f strings are correct

### User Communication Rules

- ❌ NEVER offer to move on to a downstream skill while training is in progress (logically impossible)
- ❌ NEVER set `ACCEPT_EULA` to `True` without explicit user confirmation in the conversation
- ✅ Always mention both the number AND title of sections you reference
- ✅ If user asks how to run (notebook): If `run_cell` is available, offer to run it. Otherwise, tell them to run cells one by one (mention ipykernel requirement).
- ✅ Wait for user confirmation before proceeding with actions

---

## Workflow

### 1. Code Generation Setup

#### 1.1 Directory Setup

1. Identify project directory from conversation context
   - If unclear (multiple relevant directories exist) → Ask user which folder to use
   - If no project directory exists → load the **directory-management** skill to set one up

⏸ Wait for user.

#### 1.2 Select Code Template

Read `references/code_output_guide.md` for output format rules, then read the code template matching the finetuning strategy:

- **SFT** → `code_templates/sft.py`
- **DPO** → `code_templates/dpo.py`
- **RLVR** → `code_templates/rlvr.py`
- **RLAIF (built-in prompt)** → `code_templates/rlaif_builtin.py`
- **RLAIF (custom prompt)** → `code_templates/rlaif_custom_prompt.py`

The template is a Python file where each `# Cell N: Label` comment marks the start of a new section. Split on these markers — everything between one marker and the next becomes one unit of output.

#### 1.3 Generate Code

1. Write the code from the template following the rules in `code_output_guide.md`
2. Use same order, dependencies, and imports as the template
3. Check if the selected model is from the Meta/Llama family (model ID starts with `meta-textgeneration-llama`)
4. If NOT a Meta/Llama model:
   - Omit the `ACCEPT_EULA` variable definition from the Configure Trainer section
   - Omit the `accept_eula=ACCEPT_EULA,` line from the trainer call
5. If the model is from the Nova family, omit any code containing `max_epochs` or `lr_warmup_steps_ratio` from the Configure Trainer section and the Hyperparameter Overrides section

#### 1.4 Auto-Generate Configuration Values

**In the 'Setup & Credentials' cell, populate:**

1. `SAGEMAKER_ROLE_ARN` = execution role ARN from conversation context (resolved by `sdk-getting-started`)
2. `S3_DATA_PATH` = S3 URI for the training dataset from conversation context (if known, otherwise leave placeholder)
3. `MODEL_ID` = SageMaker Hub model ID for the base model selected in `model-selection`
4. `MLFLOW_TRACKING_URI` = MLflow tracking server ARN:
   1. Run `python scripts/mlflow_reference.py <REGION>` using the region from conversation context
   2. Set `MLFLOW_TRACKING_URI` to the stdout output (the ARN string). If it prints `NONE` or fails, set `MLFLOW_TRACKING_URI = ""` (and optionally offer `manage-mlflow` if the user wants to create a Managed MLflow App).

Save the notebook.

### 2. RLVR Reward Function (for RLVR only, skip this section if technique is SFT or DPO)

#### 2.1 Check Reward Function Status

- Ask if user has a reward function already, or would like help creating one.
  - If user says they have one → Ask for the SageMaker Hub Evaluator ARN. Only proceed to Section 2.3 once the user provides a valid Evaluator ARN. If they don't have it registered as a SageMaker Hub Evaluator, continue to 2.2.
  - If user says they do not have one → Continue to 2.2

#### 2.2 Generate Reward Function From Template

1. Follow workflow in `references/rlvr_reward_function.md` section "Helping Users Create Custom Reward Functions"

#### 2.3 Set CUSTOM_REWARD_FUNCTION value

1. Set the value for `CUSTOM_REWARD_FUNCTION` in the Notebook with the ARN of the reward function (either given directly by the user, or from the function generation code as `evaluator.arn`).

### 3. RLAIF (for RLAIF only, skip this section if technique is not RLAIF)

Read `references/rlaif_guide.md` and follow its instructions.

### 4. EULA review and acceptance

1. Look up the official license link for the selected base model from `references/eula_links.md`
2. Display the license to the user following the phrasing in `references/eula_links.md`. For OSS models: "This model is licensed under **{License}**. Please review the license terms here: {URL}." For Nova models: "This model is subject to the AWS Service Terms: {URL}."
3. Check if the model is from the Meta/Llama family (model ID starts with `meta-textgeneration-llama`):
   - **If Meta/Llama**: Tell the user they must read and agree to the EULA before using this model. Ask: "Do you accept the license terms? (yes/no)". If the user confirms, set `ACCEPT_EULA = True` and uncomment `accept_eula=ACCEPT_EULA` in the generated notebook. If the user declines, leave `ACCEPT_EULA = False` and warn that training will fail without acceptance.
   - **If non-Meta**: Inform the user of the license for their awareness. No code-level action needed — the `ACCEPT_EULA` variable and `accept_eula` parameter should already be omitted from the notebook (see Step 1.3).

### 5. Post-Generation

After generating the code, offer to run it. Training can take hours depending on your dataset and model.

### 6. Continuous Customization

If the user wants to finetune a model they had already customized, follow the instructions in `references/continuous_customization.md`.

---

## References

- `references/rlvr_reward_function.md` — Lambda reward function creation guide (RLVR only)
- `templates/rlvr_reward_function_source_template.py` — Lambda reward function source template for open-weights models (RLVR only)
- `templates/nova_rlvr_reward_function_source_template.py` — Lambda reward function source template for Nova models (RLVR only)
- `references/rlaif_guide.md` — RLAIF setup: judge model selection and custom prompt creation (RLAIF only)
- `references/eula_links.md` — Official license URLs for supported base models
- `references/continuous_customization.md` — Instructions for training a previously customized model
