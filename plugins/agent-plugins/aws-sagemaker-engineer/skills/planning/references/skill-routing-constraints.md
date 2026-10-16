# Skill Routing Constraints

## Plan Completeness

- Generate the complete plan upfront. The plan presented to the user must include all steps needed to reach their goal. Do not generate a partial plan with the intent to add steps later.
- Each step must be executed by its designated skill. Do not perform a skill's work ad-hoc or inline within another skill.

## Architectural & FinOps Routing Rules

- **Architecture-First for Complex / Non-LLM / Platform Requests:** When the user asks to design an ML system, train tabular/time-series/vision models, build an enterprise Studio platform, or choose between Bedrock, Serverless Customization, Managed Training, and HyperPod, run `sagemaker-solution-architect` first to produce `ARCHITECTURE.md`.
- **IaC Validation Rule:** All SageMaker Studio Domain, VPC, PrivateLink, KMS, and IAM infrastructure generation MUST go through `sagemaker-domain-vpc-iac` and be validated with the `awsiac` MCP server (`cfn-lint` and `cfn-guard`).
- **Pre-Provisioning FinOps Gate:** Before provisioning paid GPU/Neuron training jobs, Real-Time Endpoints, Studio Spaces, or HyperPod clusters, include `sagemaker-cost-estimator` (unless the user explicitly declines cost estimation) to query live pricing via the `awspricing` MCP server and generate `COST_ESTIMATE.md`.
- **Production Deployment & Observability Gate:** When deploying models beyond LoRA/JumpStart single-model defaults (e.g., `InferenceComponent` multi-model bin-packing, Scale-to-Zero, Multi-Container, Serverless, Async, Batch Transform, FFT/custom weights), route to `sagemaker-inference-architect`, and pair production endpoints with `sagemaker-observability-governance` for Blue/Green guardrails and Model Monitor drift schedules.
- **Live Endpoint Troubleshooting:** Route unhealthy or high-latency endpoint investigations to `endpoint-diagnostics` (for deterministic status/metric/log collection) and `sagemaker-observability-governance`.

## Mandatory Inclusion for FM Customization & Base Model Deployment

- `use-case-specification`: Recommend by default in every FM customization or base model deployment plan unless the user explicitly declines or has an existing `use_case_spec.md`.

## Evaluate-First Path (FM Customization)

When the user chooses to evaluate the base model before fine-tuning:

- `model-selection` MUST run before `sdk-getting-started` and `dataset-evaluation`.
- `sdk-getting-started` MUST run after `model-selection` and before `dataset-evaluation`.
- `model-selection` runs before `model-evaluation`.
- `finetuning-technique` is NOT required unless the user decides to fine-tune after the evaluation decision gate.

## Direct Fine-Tuning Path (Serverless FM Customization)

When the user chooses to go straight to Serverless Model Customization:

- `model-selection` MUST run before `sdk-getting-started`.
- `sdk-getting-started` MUST run after `model-selection` and before `dataset-evaluation`.
- `model-selection` MUST run before `finetuning-technique`.
- `finetuning-technique` MUST run before `dataset-evaluation` (for training data) and `finetuning`.
- `dataset-evaluation` should run after `finetuning-technique` and before `finetuning`, to catch format issues before training.

## Ordering Constraints

- In FM customization and JumpStart deployment plans, `model-selection` MUST run before `sdk-getting-started`.
- `sdk-getting-started` MUST run before the first task that runs local Python SDK scripts or makes AWS API calls requiring an execution role (`dataset-evaluation`, `finetuning`, `sagemaker-training-architect`, `model-evaluation`, `model-deployment`, `sagemaker-inference-architect`).

## Skill Boundaries

- All dataset format changes for Serverless FM Customization MUST go through `dataset-transformation`. Do not write inline transformation code in other skills' notebooks.
- All JumpStart Hub model selection MUST go through `model-selection`. Do not resolve Hub model IDs ad-hoc.
- All Serverless FM technique selection MUST go through `finetuning-technique`. Do not select techniques ad-hoc.
- All Managed MLflow App lifecycle operations MUST go through `manage-mlflow` (or `sagemaker-mlops-pipelines` for IaC/Pipeline integration) using `CreateMlflowApp` APIs.

## Model-Selection Anti-Pattern

- **Do not resolve ambiguous constraints yourself when selecting or filtering JumpStart models.** Terms like "lightweight", "fast", "small", or "cheap" are resolved through the `use-case-specification` → `model-selection` (`select-for-deployment.md`) pipeline, not by agent guesswork. If the user has not gone through `use-case-specification`, activate it first.
