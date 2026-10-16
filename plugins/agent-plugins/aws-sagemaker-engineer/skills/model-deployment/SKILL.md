---
name: model-deployment
description: >-
  Deploys fine-tuned models (Nova or OSS LoRA from SageMaker Serverless Model Customization) to
  SageMaker endpoints or Amazon Bedrock, deploys open-weight JumpStart foundation models to
  SageMaker real-time endpoints, and runs inference optimization sub-workflows (endpoint
  benchmarking and instance/serving recommendations). For Full Fine-Tuned (FFT) models, custom
  training job artifacts (model.tar.gz), InferenceComponent multi-model bin-packing, Scale-to-Zero
  auto-scaling, Multi-Container, Serverless, Async, or Batch Transform endpoints, seamlessly
  routes to sagemaker-inference-architect.
metadata:
  version: "2.0.0"
---

# Model Deployment

Identifies the correct deployment pathway based on model characteristics and generates deployment code. Also provides inference optimization sub-workflows for benchmarking endpoint performance and getting deployment recommendations, and delegates custom/advanced inference topologies to `sagemaker-inference-architect`.

## Scope

### Validated SDK v3 Deployment Pathways (Steps 1–6)

1. **Fine-tuned models** (Nova or OSS) that were fine-tuned through **SageMaker Serverless Model Customization** (LoRA) → SageMaker or Bedrock.
2. **Open-weight foundation (base) models from SageMaker JumpStart** → a SageMaker real-time endpoint (`references/deploy-jumpstart-sagemaker.md`), using the flat config resolved by `model-selection` (`model_id`, `instance_type`, `inference_config_name`).

### Inference Optimization Sub-Workflows (Step 0)

| Sub-workflow        | Purpose                                                                                | Model Requirements                                     |
| ------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| **Benchmarking**    | Measure inference performance (latency, throughput) on an existing SageMaker endpoint  | Any model on a SageMaker Managed Inference endpoint    |
| **Recommendations** | Find the best instance type, serving config, and optimizations for deploying a model   | OSS base models only (no Nova, no LoRA)                |

**Optimization applicability**:

- **Regions**: `us-east-1`, `us-west-2`, `us-east-2`, `ap-northeast-1`, `eu-west-1`, `ap-southeast-1`, `eu-central-1`. Confirm current availability in the [SageMaker AI Region availability docs](https://docs.aws.amazon.com/sagemaker/latest/dg/regions-quotas.html).
- **Benchmarking**: SageMaker Managed Inference endpoints — OpenAI ChatCompletions-compatible out of the box, plus custom (non-OpenAI) formats via template mode.
- **Recommendations**: OSS base models in HuggingFace format (not Nova or LoRA adapters; deploys to SageMaker endpoints).

### Architectural Delegation to `sagemaker-inference-architect` (Never Dead-End)

When the user's deployment request involves any of the following architectures, do **not** block or dead-end the user — immediately activate **`sagemaker-inference-architect`** (and pair with **`sagemaker-cost-estimator`** for FinOps sizing and **`sagemaker-observability-governance`** for production rollout guardrails):

- Deploying **Full Fine-Tuned (FFT)** models, custom `Estimator` / `@remote` training job `model.tar.gz` artifacts, or externally trained HuggingFace/PyTorch/XGBoost/ONNX/TensorRT models
- **SageMaker Inference Components (`InferenceComponent`)** for packing multiple models onto shared GPU instances with fractional GPU allocation (`ComputeResourceRequirements`) and **Scale-to-Zero (`MinCapacity=0`)** auto-scaling
- **Multi-Container Endpoints (MCE)** (Direct invocation or Serial Inference Pipelines) and **Multi-Model Endpoints (MME)**
- **Serverless Inference** (`MemorySizeInMB`, `MaxConcurrency`), **Asynchronous Inference** (`InvokeEndpointAsync` up to 1 GB payloads with S3 queues), or **Batch Transform** jobs
- **AWS Inferentia2 (`ml.inf2`)** Neuron compilation and **Bedrock Custom Model Import (`CreateModelImportJob`)** for custom S3 weights
- **HyperPod Inference** → route to **`hyperpod-Inference`**

## Prerequisites

- The SDK environment has been verified (SDK version, region, execution role). If not done, activate the `sdk-getting-started` skill first.

---

## Principles

1. **One thing at a time.** Each response advances exactly one decision.
2. **State your intent, don't re-ask.** When information is already available from conversation or session lookups, state the values you'll use and proceed. **This does not waive mandatory gates:** always pause for explicit approval before (a) an action with real cost or risk (provisioning paid GPU endpoints, sending load to a live endpoint, running a 30+ min recommendation job), or (b) any required license / EULA acceptance for a gated or licensed model.
3. **Don't read files until you need them.** Only read pathway references after the pathway is confirmed.
4. **Use what you know.** If conversation history or artifacts already answer a question, confirm your understanding instead of asking again.

## Workflow

### Step 0: Optimization (only when the user asks for it)

Optimization has two sub-workflows: **benchmarking** (measure latency/throughput on an existing endpoint) and **recommendations** (find the best instance + serving config before deploying). **Default is plain deployment** — if the user asked to deploy a model without mentioning performance, benchmarking, cost/latency/throughput goals, or instance-choice help, go straight to Step 1 and do not enter optimization.

**When to enter Step 0:**

- User asked to **benchmark**, **optimize**, **compare** runs, **load-test**, or measure performance → go straight to Step 0A (Benchmark) or Step 0B (Recommendations).
- User stated a **performance / cost / latency / throughput goal** for a *new* OSS base model deployment (e.g., "find the cheapest instance", "hit p99 under 200ms") → go to Step 0B (Recommendations).
- Otherwise → **skip Step 0 entirely, go to Step 1.**

#### Step 0A: Benchmark an Existing Endpoint

Read `references/optimization/benchmark-workflow.md` and follow its instructions.

#### Step 0B: Get Deployment Recommendations

Read `references/optimization/recommendation-workflow.md` and follow its instructions.

#### Optimization reference index (load only what the intent needs)

| Intent | Read |
|--------|------|
| Benchmark an endpoint / load test | `references/optimization/benchmark-workflow.md` (`benchmarking-guidance.md`) |
| Present / compare benchmark results | `references/optimization/interpreting-results.md` |
| Get deployment recommendations | `references/optimization/recommendation-workflow.md` (`recommendation-options.md`) |
| Deploy a recommendation's ModelPackage | `references/optimization/recommendation-deploy.md` |
| Deploy a HuggingFace-Hub (non-JumpStart) model | `references/optimization/huggingface-to-s3.md` |

---

### Step 1: Identify the Model and its Source

First determine which family this is (infer from the conversation before asking):

- **Custom / FFT / Non-Serverless Model or Advanced Hosting Topology (`InferenceComponent`, Serverless, Async, Batch, MCE, MME)** → Delegate immediately to **`sagemaker-inference-architect`**.
- **JumpStart foundation (base) model** — the user wants to deploy an open-weight foundation model from SageMaker JumpStart. There is **no training job**. The deployment config (`model_id`, `instance_type`, `inference_config_name`) comes from `model-selection` — use it as-is. Resolve `role_arn` and `region` from context (or ask if unknown), then proceed to Step 2.
- **Fine-tuned model** — the user is deploying a model fine-tuned via SageMaker Serverless Model Customization. Continue with the training-job identification below.

#### Fine-tuned model: identify the training job

Once you have the training job name or ARN, use the AWS MCP tool to look it up:

1. Use the AWS MCP tool `describe-training-job` and extract:
   - **S3 output path** (`ModelArtifacts.S3ModelArtifacts` or `OutputDataConfig.S3OutputPath`)
   - **IAM role ARN** (`RoleArn`)
   - **Region**
2. Use the AWS MCP tool `list-tags` on the training job ARN and extract:
   - **Model ID** from the `sagemaker-studio:jumpstart-model-id` tag
3. Determine the **model type** from the model ID:
   - Contains "nova" (`nova-micro`, `nova-lite`, `nova-pro`) → **Nova**
   - Llama, Mistral, Qwen, GPT-OSS, DeepSeek, etc. → **OSS**

If the training job was Full Fine-Tuned (FFT, `peft_config: null` in `.hydra/config.yaml`) or trained via custom Estimator/HyperPod, transition smoothly to **`sagemaker-inference-architect`** to deploy the weights via DJL Serving (LMI/vLLM) or Bedrock Custom Model Import (`CreateModelImportJob`).

### Step 2: Determine Eligible Deployment Targets

| Model Type                  | Eligible Targets   |
| --------------------------- | ------------------ |
| OSS (fine-tuned LoRA)       | SageMaker, Bedrock |
| Nova (fine-tuned)           | SageMaker, Bedrock |
| JumpStart foundation (base) | SageMaker          |

If only one target is eligible, confirm it with the user. If multiple targets are eligible, help the user decide in Step 3.

### Step 3: Let the User Choose a Deployment Target

Present the eligible options to the user:

**SageMaker Endpoint:**

- Dedicated compute resources for consistent performance
- Control instance types, `InferenceComponent` packing, and scaling
- Best for predictable workloads with strict latency SLAs

**Bedrock:**

- Fully managed serverless inference
- Auto-scales instantly with no capacity planning
- Pay per request (or Provisioned Throughput for Nova)
- Best for variable workloads with fluctuating demand

⏸ Wait for user to select a deployment option.

### Step 4: Display License Agreement

Before generating any code, present the model's license or service terms to the user and wait for explicit confirmation.

**Always perform this step for the deployment, even if the model's license was already shown or accepted earlier in the conversation.** A general "proceed" or "deploy now" instruction does NOT constitute EULA acceptance for a gated model — you must obtain explicit acceptance before setting `accept_eula=True`.

1. Read `references/model-licenses.md` and look up the model by its model ID.
2. Follow the instructions in the Notes column — use the exact phrasing provided. End your response there and wait for confirmation.
3. If the model ID is not found in the table, warn the user that license information could not be found in the static table and recommend verifying the license independently before proceeding.

⏸ Wait for the user to confirm before proceeding.

### Step 5: Follow Pathway Workflow

Read the reference file for the selected pathway and follow its instructions:

| Model Type                  | Deployment Target | Reference                                   |
| --------------------------- | ----------------- | ------------------------------------------- |
| OSS (fine-tuned)            | SageMaker         | `references/deploy-oss-sagemaker.md`        |
| OSS (fine-tuned)            | Bedrock           | `references/deploy-oss-bedrock.md`          |
| Nova (fine-tuned)           | SageMaker         | `references/deploy-nova-sagemaker.md`       |
| Nova (fine-tuned)           | Bedrock           | `references/deploy-nova-bedrock.md`         |
| JumpStart foundation (base) | SageMaker         | `references/deploy-jumpstart-sagemaker.md`  |

### Step 6: Post-Deployment Summary & Production Hardening Offer

After deployment completes, provide the user with a summary covering:

- **What was deployed** — endpoint or model name, ARN, status
- **How to use it** — sample invoke code for the specific deployment target
- **Cost & Optimization** — billing model (hourly instance vs pay-per-request), plus offer **`sagemaker-inference-architect`** if they want to pack multiple models onto the endpoint via `InferenceComponent` + Scale-to-Zero (`MinCapacity=0`), or **`sagemaker-observability-governance`** to attach Blue/Green guardrails and Model Monitor drift schedules
- **Cleanup** — how to delete the endpoint or model when done so idle GPU instances do not accrue charges

## Troubleshooting

### How to check if a model was LoRA or FFT fine-tuned

If Serverless LoRA deployment fails unexpectedly, check the training job's hydra config at `.hydra/config.yaml` in its S3 output path:

- `peft_config` populated (`r`, `alpha`, `dropout`, etc.) → **LoRA** (supported by `deploy-oss-sagemaker.md` / `deploy-oss-bedrock.md`)
- `peft_config: null` → **FFT** (delegate to `sagemaker-inference-architect` for LMI/vLLM container deployment or Bedrock Custom Model Import)
