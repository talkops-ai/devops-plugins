---
name: planning
description: >-
  Discovers user intent and generates a structured, step-by-step execution and architectural plan
  across the entire Amazon SageMaker AI lifecycle — including Well-Architected ML solution design,
  Studio Domain VPC/IAM/KMS IaC, pre-provisioning FinOps cost estimation, Foundation Model
  customization (SFT, DPO, RLVR, RLAIF), JumpStart base model deployment, custom/distributed
  training (Estimators, @remote, DDP/FSDP, Autopilot AutoMLv2, HyperPod), inference architecture
  (InferenceComponent bin-packing, Scale-to-Zero, Multi-Container, Serverless, Async, Batch),
  MLOps pipelines (Pipelines DAGs, Feature Store, Model Registry, Managed MLflow, Catalog SQL),
  and production observability/diagnostics. Always activate alongside other skills when a request
  spans multiple steps or requires architectural planning.
metadata:
  version: "3.0.0"
---

## Principles

- **One question at a time.** Each question should resolve a branching decision in the plan. Avoid generic or out-of-domain questions.
- **Surface constraints early.** If a user decision (region, model family, VPC isolation, latency/budget target) constrains downstream options, flag it before finalizing the plan.
- **Right-size the plan.** Match the plan depth to the user's goal — a narrow diagnostic request needs a short plan, while an enterprise platform or production deployment includes architecture, FinOps cost estimation, and observability guardrails.
- **Don't ask what you already know.** Check conversation history and project files before asking the user.

---

## Phase 1: Brainstorming & 5-Stage Architectural Triage

**Goal:** Understand what the user wants to accomplish, triage the workload against the 5-Stage SageMaker Architectural Decision Engine, and identify which skills belong in the plan.

Read `references/input-output-contracts.md`, `references/model-customization-plan.md`, `references/evaluate-first-plan.md`, and `references/deploy-base-model-plan.md` to:

- Determine whether the user's request aligns with an existing plan template (Evaluate-First FM Customization, Direct FM Fine-Tuning, Deploy Base Model) or requires an **Architectural / Custom ML / Platform / MLOps Plan**.
- Identify which skills are required for the user's stated goal and check whether prerequisite artifacts (`ARCHITECTURE.md`, `use_case_spec.md`, `COST_ESTIMATE.md`, verified SDK environment) exist.
- Order skills to allow a smooth transition from one to the next and avoid dead ends.

### The 5-Stage Architectural Decision Engine

When the user's request goes beyond single-step troubleshooting, evaluate which of the 5 lifecycle stages belong in `PLAN.md`:

1. **Stage 1: Problem Framing & Compute Triage (`sagemaker-solution-architect` / `use-case-specification`)**
   - **When to include `sagemaker-solution-architect`**: The user asks "how should I architect/train/deploy X?", has a non-LLM modality (Tabular, Time-Series, Computer Vision / SAM, Multimodal), needs multi-service design, or hasn't chosen between Bedrock, Serverless Customization, Managed Training Jobs, or HyperPod.
   - **Compute Tier Triage**:
     - **Skip SageMaker?** If zero-shot FM or RAG suffices with variable traffic → recommend Amazon Bedrock / Bedrock Knowledge Bases. If stateless lightweight CPU inference (<15 min, <10 GB RAM) → AWS Lambda container.
     - **Tier A (Tabular / Time-Series / AutoML)**: Route to `sagemaker-training-architect` (SageMaker Autopilot AutoML API v2 `CreateAutoMLJobV2` or Canvas).
     - **Tier B (Serverless FM Customization / JumpStart Base Deployment)**: Route to `use-case-specification` → `model-selection` → (`finetuning-technique` → `finetuning` OR `model-deployment`).
     - **Tier C (Managed Training Jobs & Custom Architectures)**: Custom PyTorch/HuggingFace/XGBoost training, Vision/Multimodal fine-tuning (e.g., Segment Anything Model `MaskDecoder`), `@remote` decorator, DDP/FSDP/DeepSpeed, Managed Spot with S3 checkpointing → route to `sagemaker-training-architect`.
     - **Tier D (HyperPod Distributed Cluster)**: Multi-node foundation model pre-training or massive FSDP on EKS/Slurm with EFA and FSx for Lustre → route to `hyperpod-ClusterCreation`, `hyperpod-Training`, `hyperpod-Inference`, `hyperpod-Observability`, `hyperpod-Troubleshooting`.

2. **Stage 2: Platform Foundation, VPC Isolation & IAM (`sagemaker-domain-vpc-iac`)**
   - **When to include**: The user needs a SageMaker Studio Domain, `VpcOnly` network isolation, PrivateLink endpoints, custom Docker images (`CfnImage` / SOCI), or least-privilege persona IAM roles (`CfnDomain`, `CfnUserProfile`, `CfnSpace`), validated with `awsiac` (`cfn-lint` + `cfn-guard`).

3. **Stage 3: Pre-Provisioning FinOps & Cost Estimation (`sagemaker-cost-estimator`)**
   - **When to include**: Before provisioning paid GPU/Neuron training jobs, Real-Time Endpoints, Studio Spaces, or HyperPod clusters, or whenever the user asks about pricing, cost optimization, Spot savings, Trainium/Inferentia (`ml.trn1`/`ml.inf2`), or `InferenceComponent` bin-packing + Scale-to-Zero (`MinCapacity=0`). Queries live prices via the `awspricing` MCP server and generates `COST_ESTIMATE.md`.

4. **Stage 4: Workload Execution (Training, Inference, or MLOps Pipeline)**
   - **Serverless FM Customization**: `finetuning-technique` → `dataset-evaluation` → `dataset-transformation` → `finetuning` → `model-evaluation` → `model-deployment`.
   - **Custom / Distributed / AutoML Training**: `sagemaker-training-architect`.
   - **Production Inference Engineering**: `sagemaker-inference-architect` (Real-Time Endpoints with `InferenceComponent` fractional GPU packing & Scale-to-Zero, Multi-Container, Multi-Model, LMI/vLLM/Neuron, Serverless, Async, Batch Transform, Bedrock Custom Model Import, Inference Recommender) or `model-deployment` (Serverless LoRA & JumpStart base models + endpoint benchmarking/recommendations).
   - **MLOps, Feature Store, Registry, MLflow & Catalog Governance**: `sagemaker-mlops-pipelines`, `manage-mlflow`, and `querying-aws-sagemaker-catalog`.

5. **Stage 5: Production Guardrails, Drift Monitoring & Diagnostics (`sagemaker-observability-governance` & `endpoint-diagnostics`)**
   - **When to include**: Production endpoint rollout (Blue/Green Canary/Linear traffic shifting, auto-rollback alarms, Shadow Variants), Model Monitor drift schedules (Data Quality, Model Quality, Bias, Feature Attribution), or live endpoint troubleshooting (`endpoint-diagnostics` + `cloudwatch` MCP server).

---

### Specific Gates for Serverless FM Customization & JumpStart Base Deployment

- **Serverless customization region gate (check FIRST for Serverless FM fine-tuning).** If the user's request involves Serverless Model Customization (`finetuning`) AND their region is already known, check it against `references/region-availability.md` (`us-west-2`, `us-east-1`, `ap-northeast-1`, `eu-west-1`). If the region is NOT supported:
  - Inform the user with the blocking message from `references/region-availability.md` for Serverless Model Customization, AND offer either: (a) switching to a supported region, (b) deploying a base model instead, or (c) running a standard Managed Training Job (`sagemaker-training-architect`) which is available across standard AWS regions.
- **Workflow choice gate (for FM customization/deployment):** Determine which FM workflow the user needs:
  1. **Deploy a base model** — select and deploy a model from the catalog without fine-tuning (`references/deploy-base-model-plan.md`).
  2. **Evaluate-first** — evaluate a base model before deciding whether to fine-tune (`references/evaluate-first-plan.md`). Always present this option alongside direct fine-tuning when the user asks to fine-tune an LLM.
  3. **Direct fine-tuning** — committed to fine-tuning (`references/model-customization-plan.md`).
  4. **Custom Architecture / Managed Training / MLOps / IaC / Inference Architecture** — compose a tailored multi-stage plan using the 5-Stage Architectural Decision Engine above.
- **Disambiguation for "deploy":**
  - Already have a Serverless LoRA training job → `model-deployment`.
  - Want to select and deploy a JumpStart base model without fine-tuning → `deploy-base-model-plan.md` (`use-case-specification` → `model-selection` → `sdk-getting-started` → `model-deployment`).
  - Have custom model weights (S3 `model.tar.gz`, FFT, HuggingFace, PyTorch, XGBoost, ONNX) or need `InferenceComponent` packing, Scale-to-Zero, Serverless, Async, Batch Transform, or Multi-Container endpoints → `sagemaker-inference-architect` (preceded by `sagemaker-cost-estimator` when estimating hosting costs).
- Do NOT ask the user about JumpStart base model selection in `planning` — model selection is handled by `model-selection` (after `sagemaker-solution-architect` confirms an FM is the right modality).

---

## Phase 2: Plan Generation

**Goal:** Propose a structured plan for the user to review.

Generate a plan as a numbered list of tasks. Each task has:

- A short name
- A one-sentence description of what happens
- Which skill handles it

**Format:**

```
Based on what you've described, here's what I propose:

1. ⬜ **[Task Name]** — [What happens]. *(Skill: [skill-name])*
2. ⬜ **[Task Name]** — [What happens]. *(Skill: [skill-name])*
3. ⬜ **[Task Name]** — [What happens]. *(Skill: [skill-name])*

Does this plan look right, or would you like to change anything?
```

**Rules for plan generation:**

- Infer ordering from the Prerequisites column in `references/input-output-contracts.md` and `references/skill-routing-constraints.md`.
- Tailor the plan to the user's actual intent. Not every plan needs every skill.
- If the user already has input artifacts (e.g., `use_case_spec.md`, `ARCHITECTURE.md`, or a trained model), skip the steps that produce them.

When the user approves the plan, write it to `PLAN.md` and save it under the project directory structure defined by the `directory-management` skill.

```markdown
# Plan

1. ⬜ **[Task Name]** — [Description]. _(Skill: [skill-name])_
2. ⬜ **[Task Name]** — [Description]. _(Skill: [skill-name])_
3. ⬜ **[Task Name]** — [Description]. _(Skill: [skill-name])_
```

**Status indicators:**

- ⬜ Not Started
- 🔄 In Progress
- ✅ Completed

Update `PLAN.md` whenever a task's status changes.

---

## Phase 3: Plan Iteration

**Goal:** Refine the plan until the user approves it.

- If the user suggests changes, regenerate the plan incorporating their feedback.
- If the user approves, begin execution by handing off to the first task's skill.

---

## Execution

Once the plan is approved:

1. **Pre-execution region check (MANDATORY for Serverless Model Customization plans).** If the plan includes the `finetuning` skill (Serverless Model Customization), check the user's region by running:

   ```bash
   python -c "import boto3; print(boto3.session.Session().region_name)"
   ```

   If `None`, skip this check and continue — `sdk-getting-started` will prompt the user later. Otherwise, check the region against `references/region-availability.md`. If unsupported for Serverless Model Customization, STOP and present the blocking message from `references/region-availability.md` (and offer switching regions or routing to `sagemaker-training-architect` for standard Managed Training Jobs). If supported, confirm (`Your region (<region>) supports serverless model customization ✅`) and continue.

2. Before starting a task, update its status in `PLAN.md` to 🔄 (In Progress).
3. Load the designated skill's full `SKILL.md` before doing any work. Always defer to the skill's instructions.
4. Execute the task by following the loaded skill's workflow.
5. When the task completes:
   - Update its status in `PLAN.md` to ✅ (Completed) and record generated output files (`ARCHITECTURE.md`, `COST_ESTIMATE.md`, scripts, notebooks, CloudFormation/CDK templates, manifests):

     ```markdown
     - [x] Fine-tune model
       - Output: `scripts/01_sft_finetuning.py`
       - Output: `manifests/sft-llama-20260515.json`
     ```

   - Briefly confirm completion and move to the next task.
6. If the user interrupts with a new request mid-execution:
   - Completed tasks are immutable — do NOT modify them.
   - Regenerate the remaining tasks to incorporate the user's new input and present for approval.

---

## Plan Completion

When all tasks in the plan are done, present to the user:

> "We've completed everything in the plan. What would you like to do next?"

This re-enters Phase 1 (Brainstorming) for a new goal.

---

## References

- `references/evaluate-first-plan.md` — Evaluate a base model before deciding whether to fine-tune.
- `references/model-customization-plan.md` — Direct fine-tuning plan for Serverless Model Customization.
- `references/deploy-base-model-plan.md` — Select and deploy a JumpStart base model without fine-tuning.
- `references/input-output-contracts.md` — Complete input/output contracts across all 30 skills.
- `references/skill-routing-constraints.md` — Ordering rules, architectural triage gates, and skill boundaries.
- `references/region-availability.md` — Single source of truth for Serverless Model Customization region availability.
