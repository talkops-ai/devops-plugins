---
name: sagemaker-solution-architect
description: >-
  Designs end-to-end Amazon SageMaker AI architectures grounded in the AWS Well-Architected Machine
  Learning Lens and Responsible AI Lens. Performs structured discovery across modality, scale,
  latency SLAs, security boundaries, and budget; evaluates when to skip SageMaker in favor of
  Amazon Bedrock, AWS Lambda, or managed AI services; selects the optimal training compute tier
  (Tier A Autopilot AutoMLv2/Canvas, Tier B Serverless FM Customization, Tier C Managed Training
  Jobs with @remote/Estimators/Spot, Tier D HyperPod EKS/Slurm clusters) and inference hosting
  pattern (InferenceComponent bin-packing with Scale-to-Zero, Real-Time LMI/vLLM, Multi-Container,
  Multi-Model, Serverless, Async, Batch Transform, Bedrock Custom Model Import); and produces a
  versioned ARCHITECTURE.md blueprint. Use when the user asks "how should I architect X on
  SageMaker", "Bedrock vs SageMaker", "which training or inference option should I use", or starts
  a multi-service ML platform/workload design.
metadata:
  version: "1.0.0"
---

# SageMaker Solution Architect

Acts as a Principal AWS Solutions Architect (Machine Learning Lens) to triage workloads, prevent over-provisioning, and produce an actionable `ARCHITECTURE.md` before infrastructure or training code is written.

## When to Activate

- User asks "how should I build/train/deploy X on AWS or SageMaker?"
- User is deciding between **Amazon Bedrock**, **SageMaker Serverless Model Customization**, **SageMaker Managed Training Jobs**, **SageMaker Autopilot**, or **SageMaker HyperPod**
- User needs to choose an inference hosting pattern (Real-Time, `InferenceComponent` packing, Serverless, Asynchronous, Batch Transform, Multi-Model, Multi-Container, or Bedrock Custom Model Import)
- User has a non-LLM workload (Tabular, Time-Series, Computer Vision / `Segment Anything`, Multimodal, Classical ML) or an enterprise multi-model platform requirement

---

## Phase 1: Structured Architectural Intake (Infer First, Ask Only Missing Branching Points)

Review conversation history and any existing `*_use_case_spec.md` first. Only ask clarifying questions for dimensions that change the architectural decision:

1. **Problem & Modality**: Text/LLM generation, Tabular classification/regression, Time-Series forecasting, Computer Vision (detection/segmentation e.g., SAM), Multimodal, or Embeddings/Reranking?
2. **Customization Need**: Zero-shot / prompt engineering / RAG on documents, parameter-efficient adapter tuning (LoRA), full-weight fine-tuning (FFT), domain-adaptive continual pre-training, or training a custom architecture from scratch?
3. **Dataset Scale & Storage**: Dataset size (MB/GB/TB), record count, storage backend (S3, Iceberg/S3 Tables, Redshift, Snowflake, FSx for Lustre), and labeling readiness (Ground Truth / Clarify)?
4. **Inference SLA & Traffic Shape**:
   - Latency budget (e.g., p99 < 100 ms, < 1 s, or minutes/hours?)
   - Traffic profile (24/7 steady RPS, business-hours spiky with idle periods, bursty event-driven queue, or nightly offline batch?)
   - Payload size (< 6 MB synchronous vs up to 1 GB asynchronous/batch) and streaming token requirement?
5. **Multi-Model Density**: Hosting a single model or dozens/hundreds of fine-tuned models/adapters concurrently?
6. **Security & Compliance**: `VpcOnly` network isolation (no public internet), PrivateLink endpoints, customer-managed KMS keys (CMKs), HIPAA/PCI/FedRAMP boundaries, cross-account model promotion?
7. **Budget & FinOps Constraints**: Target monthly run-rate, tolerance for Spot preemption during training, willingness to use AWS Trainium (`ml.trn1`/`ml.trn2`) or AWS Inferentia2 (`ml.inf2`)?

---

## Phase 2: The "Should You Even Use SageMaker?" Gate

Before designing a SageMaker topology, evaluate whether a simpler or lower-cost AWS service solves the problem directly:

| Workload Pattern | Recommended Service | Why Skip Dedicated SageMaker Compute? |
|---|---|---|
| Zero-shot Foundation Model, Prompt Engineering, or RAG over enterprise documents | **Amazon Bedrock** (Converse API + Knowledge Bases + Guardrails) | Pay-per-token with zero idle GPU cost, no endpoint management, native citation/chunking |
| Standard OCR, Document Table Extraction, Face/Label Detection, Speech-to-Text | **Amazon Textract / Rekognition / Transcribe / Comprehend** | Pre-built managed APIs with no model training or hosting maintenance |
| Lightweight CPU-only model (< 10 GB container image, < 15 min execution, low/bursty RPS, tolerant of 1–5s cold start) | **AWS Lambda (Container Image)** or **SageMaker Serverless Inference** | True pay-per-millisecond compute with zero idle cost |
| Existing Kubernetes platform team standardizing on KServe / Ray Serve across clouds | **Amazon EKS** (or **SageMaker HyperPod on EKS**) | Use HyperPod on EKS when you want AWS-managed node health healing + EFA + Slurm/Kueue on top of EKS |

If SageMaker AI is the right fit (or part of a hybrid SageMaker + Bedrock architecture), proceed to Phase 3.

---

## Phase 3: 4-Tier Training Compute Decision Matrix

Select the lowest-operational-overhead tier that satisfies the user's customization depth and scale (see `references/well-architected-ml-matrix.md` for full specifications):

| Compute Tier | Target Workloads | Key AWS Primitives | Downstream Skill |
|---|---|---|---|
| **Tier A: AutoML & No-Code/Low-Code** | Tabular classification/regression, Time-Series forecasting (with holiday calendars), rapid baseline benchmarking | `CreateAutoMLJobV2` (`TabularJobConfig`, `TimeSeriesForecastingJobConfig`), SageMaker Canvas, Clarify feature attribution | `sagemaker-training-architect` |
| **Tier B: Serverless FM Customization** | Fine-tuning supported JumpStart Hub Foundation Models (Llama, Qwen, Mistral, DeepSeek, Nova) via SFT, DPO, RLVR, or RLAIF in supported regions (`us-west-2`, `us-east-1`, `ap-northeast-1`, `eu-west-1`) | `SFTTrainer`, `DPOTrainer`, `RLVRTrainer`, `RLAIFTrainer`, Serverless Evaluator | `finetuning-technique` → `finetuning` |
| **Tier C: Managed Training Jobs** | Custom PyTorch/HuggingFace/XGBoost/Lightning scripts, Computer Vision / Multimodal fine-tuning (e.g., Segment Anything `MaskDecoder`), FFT in any region, multi-GPU single/multi-node DDP/FSDP, Managed Spot Training (60–90% savings) | `CreateTrainingJob`, SDK v3 `@remote` decorator, `PyTorch`/`HuggingFace` Estimator, `use_spot_instances=True` + S3 checkpointing, `KeepAlivePeriodInSeconds` Warm Pools, `FastFile` / FSx for Lustre | `sagemaker-training-architect` |
| **Tier D: SageMaker HyperPod** | Multi-week foundation model pre-training or massive multi-node FSDP/Megatron-LM across 8–1,000+ accelerators (`ml.p5.48xlarge`, `ml.trn1.32xlarge`, `ml.g6e.48xlarge`) requiring automatic faulty-node replacement and 400–3200 Gbps EFA | HyperPod EKS or Slurm cluster, EFA, FSx for Lustre, Kueue task governance, `sagemaker` MCP server | `hyperpod-ClusterCreation`, `hyperpod-Training` |

---

## Phase 4: 8-Way Inference Hosting Decision Matrix

Select the hosting pattern that minimizes cost while meeting latency and payload SLAs:

| Hosting Pattern | Payload & Timeout | Scaling & Cold Start | Best For | Downstream Skill |
|---|---|---|---|---|
| **1. Real-Time + `InferenceComponent` Bin-Packing** | ≤ 6 MB (or streaming), 60s | `MinCapacity=0` (Scale-to-Zero) to N copies; fractional GPU/CPU/RAM per model; `LEAST_OUTSTANDING_REQUESTS` | **Default recommendation for multi-model GPU/CPU hosting** (40–60% cheaper than 1 endpoint per model) | `sagemaker-inference-architect` |
| **2. Real-Time Single-Model Endpoint** | ≤ 6 MB (or streaming), 60s | 1 to N instances (`ml.g5`, `ml.g6e`, `ml.inf2`, `ml.p4d`) | High-throughput single LLM/vision model using DJL Serving (LMI/vLLM/TensorRT-LLM) or JumpStart | `model-deployment` or `sagemaker-inference-architect` |
| **3. Multi-Container Endpoint (MCE)** | ≤ 6 MB, 60s | Instance-level scaling (up to 15 containers per instance) | **Serial Inference Pipelines** (`preprocessor` → `predictor` → `postprocessor`) or **Direct** multi-framework serving without cold-eviction | `sagemaker-inference-architect` |
| **4. Multi-Model Endpoint (MME)** | ≤ 6 MB, 60s | Dynamic S3-to-RAM/GPU loading & LRU eviction across 100s–1,000s of models | Hundreds of homogeneous models (e.g., per-tenant XGBoost/sklearn/Triton models) with long-tail traffic | `sagemaker-inference-architect` |
| **5. Serverless Inference** | ≤ 4 MB, 60s | Automatic scale-to-zero; `MemorySizeInMB` (1024–6144 MB), `MaxConcurrency` (up to 200); optional `ProvisionedConcurrency` | Intermittent CPU workloads (< 6 GB RAM) that cannot justify 24/7 instance cost | `sagemaker-inference-architect` |
| **6. Asynchronous Inference** | **Up to 1 GB**, **up to 1 hour** | Scales down to **0 instances (`MinCapacity=0`)** when S3 queue is empty; built-in SNS success/error topics | Large document/video/image payloads (e.g., high-res SAM segmentation, batch LLM reasoning, long audio) with near-real-time queue tolerance | `sagemaker-inference-architect` |
| **7. Batch Transform** | Multi-GB S3 datasets, hours/days | Ephemeral job cluster (`CreateTransformJob`), terminates immediately on completion | Nightly/weekly offline scoring, backfills, S3 Event Notification + Lambda triggered batch pipelines | `sagemaker-inference-architect` |
| **8. Bedrock Custom Model Import (CMI) / Bedrock Deployment** | Converse / InvokeModel API | Managed serverless (CMI uses Custom Model Units billed in 5-min windows when active) | Fine-tuned Nova/OSS LoRA or custom S3 HuggingFace weights (< 200 GB) needing unified Bedrock API + Guardrails | `model-deployment` or `sagemaker-inference-architect` |

---

## Phase 5: Produce `ARCHITECTURE.md` Blueprint

Write `ARCHITECTURE.md` in the project directory containing:

1. **Executive Summary & Workload Classification** (Modality, Tier selection, SLA targets)
2. **Architecture Diagram** (Mermaid `flowchart LR` showing Data Ingestion → Training Tier → Model Registry/MLflow → Hosting Topology → Observability/Guardrails + VPC/KMS boundary)
3. **Well-Architected ML Lens Tradeoff Analysis** (Why the chosen training tier and inference pattern beat alternatives on Performance, Cost, Security, and Operational Excellence)
4. **Network, Identity & Encryption Posture** (`VpcOnly` vs Public, required VPC Interface/Gateway Endpoints, KMS CMKs, Persona Execution Roles)
5. **FinOps & Capacity Strategy** (Recommended instance families including `ml.g6e`/`ml.trn1`/`ml.inf2` comparison, Spot checkpointing strategy, and `InferenceComponent` packing density)
6. **Ordered Execution Hand-off Plan** mapping each implementation step to its specialist skill (`sagemaker-domain-vpc-iac`, `sagemaker-cost-estimator`, `sagemaker-training-architect`, `sagemaker-inference-architect`, `sagemaker-mlops-pipelines`, `sagemaker-observability-governance`).

Present `ARCHITECTURE.md` to the user and ask for confirmation before proceeding to implementation or cost estimation.

## References

- `references/well-architected-ml-matrix.md` — Deep-dive AWS Well-Architected ML Lens pillar checklist, instance family selection matrix (`ml.g5`, `ml.g6`, `ml.g6e`, `ml.p4d`, `ml.p5`, `ml.trn1`, `ml.trn2`, `ml.inf2`), and storage I/O decision tree (`FastFile`, `Pipe`, `File`, `FSx for Lustre`, `S3 Express One Zone`).
