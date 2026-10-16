---
name: use-case-specification
description: >-
  Creates a reusable use case specification file (*_use_case_spec.md) that defines the business
  problem, stakeholders, measurable success criteria (Success Tenets for fine-tuning), deployment
  constraints (for base model deployment), and quantitative architectural SLAs (latency, RPS,
  data modality, budget, compliance) as recommended by the AWS Responsible AI and Well-Architected
  ML Lenses. Use as the default first step in model customization or deployment plans.
metadata:
  version: "2.0.0"
---

# Use Case Specification

Multi-turn conversation to gather use case details and produce a structured use case specification document (`[relevant_title]_use_case_spec.md`).

## Principles

1. **One thing at a time.** Each response advances exactly one decision or collects one piece of information.
2. **Confirm before proceeding.** Wait for the user to approve the spec before considering this skill complete.
3. **Infer, don't interrogate.** Use what's already known from the conversation. Only ask when you truly can't infer.
4. **Do NOT ask about JumpStart base model selection.** Model selection is handled exclusively by the `model-selection` skill (or `sagemaker-solution-architect` for non-LLM modalities).

## Workflow

### Step 0: Check for Existing Spec

Before starting discovery, check if a `*_use_case_spec.md` file already exists in the project. If it does, present it to the user and ask whether they want to reuse it, modify it, or start fresh.

### Step 1: Determine Intent & Modality

Check the plan (`PLAN.md`), `ARCHITECTURE.md`, or conversation context to determine whether the user wants to:

- **Fine-tune a Foundation Model** → read `references/spec-for-finetuning.md` and follow it.
- **Deploy a Base Foundation Model as-is** → read `references/spec-for-deployment.md` and follow it.
- **Architect / Train / Deploy a Custom ML, Tabular, Time-Series, or Computer Vision Model** → follow `references/spec-for-finetuning.md` to capture the business problem and stakeholders, AND include the **Quantitative SLA & Architecture Constraints** section below so `sagemaker-solution-architect`, `sagemaker-training-architect`, `sagemaker-cost-estimator`, and `sagemaker-inference-architect` have concrete engineering parameters.

If the intent is ambiguous and not already resolved by the `planning` or `sagemaker-solution-architect` skill, ask:

> "Are you looking to fine-tune a model for your use case, deploy a base model as-is, or train a custom ML/vision/tabular model?"

⏸ Wait for user response.

### Optional Architectural SLA Extension (When Applicable)

Whenever the user has mentioned (or needs production sizing for) latency, traffic, modality, or budget constraints, record an additional `## Quantitative SLA & Architecture Constraints` section in `[relevant_title]_use_case_spec.md` (without breaking the core fields required by `spec-for-finetuning.md` or `spec-for-deployment.md`):

- **Data Modality & Volume**: Text/JSONL, Tabular CSV/Parquet, Time-Series, Image/Video (`Segment Anything` / ViT), Multimodal; dataset size and labeled record count.
- **Latency & Throughput Targets**: Target p99 latency (ms), peak requests per second (RPS), average input/output payload or token size, and traffic pattern (steady 24/7, spiky/scale-to-zero, async queue, or offline batch).
- **Budget & Compliance Constraints**: Target monthly compute budget, VPC isolation (`VpcOnly`), KMS customer-managed key requirements, and regulatory boundaries (HIPAA, PCI, FedRAMP).

## Edit Protocol

- If the user requests changes pertaining to any information covered by `use_case_spec.md`, edit it accordingly and ask for confirmation again.
- The user can edit `use_case_spec.md` directly if they want to. If the user says they've updated the file directly, read it to get the latest in your context.

## References

- `references/spec-for-finetuning.md` — Discovery and spec generation workflow for fine-tuning (Business Problem, Primary Users, Success Tenets)
- `references/spec-for-deployment.md` — Discovery and spec generation workflow for base model deployment (Business Problem, Primary Users, Deployment Constraints)
