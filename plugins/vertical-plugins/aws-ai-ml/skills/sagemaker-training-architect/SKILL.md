---
name: sagemaker-training-architect
description: >-
  Architects and generates production training code for Amazon SageMaker AI Managed Training Jobs,
  Distributed Training, Custom Vision/Multimodal Fine-Tuning, and AutoML. Covers SageMaker Python
  SDK v3 @remote decorator and Local Mode Docker testing, custom PyTorch/HuggingFace/XGBoost
  Estimators, Computer Vision & Segment Anything Model (SAM sam-vit-base/large/huge MaskDecoder)
  fine-tuning, Distributed Data Parallel (DDP) / FSDP / DeepSpeed, Mixed Precision (AMP FP16/BF16
  with FP32 master weights) & gradient accumulation, Managed Spot Training with S3 checkpointing,
  Managed Warm Pools, FastFileMode / FSx for Lustre high-throughput I/O, and SageMaker Autopilot
  AutoML API v2 (CreateAutoMLJobV2 for Tabular & Time-Series with Holiday Calendars and Clarify
  explainability). Use when training custom models, running non-serverless training jobs, or using
  Autopilot.
metadata:
  version: "1.0.0"
---

# SageMaker Training, Distributed Compute & AutoML Architect

Covers the entire spectrum of custom, distributed, multimodal, and AutoML training on Amazon SageMaker AI beyond Serverless LLM recipes.

## When to Activate

- User wants to run a standard **SageMaker Managed Training Job (`CreateTrainingJob`)** or use the **SageMaker Python SDK v3 `@remote` decorator**
- User is training or fine-tuning **Computer Vision, Multimodal, Audio, or Custom PyTorch/HuggingFace architectures** (e.g., Meta's Segment Anything Model `facebook/sam-vit-base` / `sam-vit-large` / `sam-vit-huge`, YOLOv8, ViT, Whisper, SDXL)
- User needs **Tabular Classification, Regression, or Time-Series Forecasting** via **SageMaker Autopilot (`CreateAutoMLJobV2`)** or **XGBoost / LightGBM Estimators**
- User needs **Multi-GPU / Multi-Node Distributed Training** (PyTorch DDP, FSDP, DeepSpeed ZeRO, AWS Trainium `torch-neuronx`)
- User wants to cut training costs by 60–90% with **Managed Spot Training + S3 Checkpointing**, speed up iteration with **Managed Warm Pools (`KeepAlivePeriodInSeconds`)**, or fix GPU I/O bottlenecks with **`FastFile` mode / FSx for Lustre**

---

## Core Capabilities & Workflow

### 1. Choose the Right Training Execution Paradigm

| Paradigm | Best For | Key Mechanism |
|---|---|---|
| **SDK v3 `@remote` Decorator** | Turning local Python functions into cloud SageMaker Training Jobs with zero boilerplate | `@remote(instance_type="ml.g5.2xlarge", dependencies="./requirements.txt", use_spot_instances=True)` |
| **Local Mode (`instance_type="local_gpu"`)** | Fast local Docker container debugging before launching cloud GPU jobs | Runs the SageMaker DLC container locally to catch import, CUDA, or `/opt/ml/model` serialization bugs in seconds |
| **Script Mode (`PyTorch` / `HuggingFace` / `XGBoost`)** | Production training jobs with custom `train.py` entrypoints, distributed launchers (`torchrun`), and metric regex extraction | `sagemaker.pytorch.PyTorch` / `boto3.client('sagemaker').create_training_job` |
| **SageMaker Autopilot (`CreateAutoMLJobV2`)** | Tabular classification/regression, Time-Series forecasting (with holiday calendars), or supervised text/image baselines | Automated feature engineering, ensemble/HPO candidate search, Clarify SHAP explainability |
| **SageMaker HyperPod** | Multi-week frontier model pre-training or 8–1000+ node FSDP/Slurm/EKS jobs | Delegate cluster provisioning and job submission to `hyperpod-ClusterCreation` & `hyperpod-Training` |

---

### 2. Mandatory Production Training Engineering Standards

Whenever you generate a SageMaker training script or job configuration, enforce these 6 production invariants:

1. **Managed Spot + S3 Checkpointing by Default**:
   - Configure `use_spot_instances=True` (`EnableManagedSpotTraining=True`), `max_wait >= max_run`, and `checkpoint_s3_uri="s3://<bucket>/checkpoints/<job-prefix>/"` (`checkpoint_local_path="/opt/ml/checkpoint"`).
   - Inside `train.py`, always check if `/opt/ml/checkpoint` contains a saved checkpoint on startup and resume from the latest epoch/step before starting the training loop!
2. **Mixed Precision (AMP) + Gradient Accumulation for VRAM Efficiency**:
   - Use `torch.amp.autocast("cuda", dtype=torch.bfloat16)` (on Ampere/Hopper `ml.g5`, `ml.g6`, `ml.g6e`, `ml.p4d`, `ml.p5`) or `torch.float16` with `GradScaler`, keeping master weights in FP32.
   - Use gradient accumulation (`gradient_accumulation_steps`) to achieve large effective batch sizes without CUDA OOM.
3. **Selective Layer Freezing for Vision & Multimodal Foundation Models (e.g., SAM)**:
   - When fine-tuning vision foundation models like **Segment Anything (`facebook/sam-vit-base`, `sam-vit-large`, `sam-vit-huge`)**, freeze `vision_encoder` and `prompt_encoder` (`param.requires_grad = False`) and fine-tune only `mask_decoder` using a combined **Dice + Focal loss** (`monai.losses.DiceFocalLoss`), reducing trainable parameters by >95% and enabling fast training on a single `ml.g5.2xlarge`.
4. **High-Throughput Data Channels (`FastFile` & FSx for Lustre)**:
   - Set `input_mode="FastFile"` (`TrainingInputMode: "FastFile"`) for S3 datasets > 50 GB so training starts immediately without downloading the entire dataset to EBS.
   - For millions of small image files, shard into **WebDataset (`.tar`)** or Parquet/TFRecord, or mount **Amazon FSx for Lustre**.
5. **Managed Warm Pools for Rapid Iteration**:
   - During interactive hyperparameter tuning or script debugging, set `keep_alive_period_in_seconds=1800` (30 minutes) so subsequent training jobs reuse the warm container environment in < 30 seconds instead of waiting 4–6 minutes for instance provisioning.
6. **VPC Isolation, KMS Encryption & MLflow Tracking**:
   - Pass `subnets`, `security_group_ids`, `volume_kms_key`, `output_kms_key`, and `encrypt_inter_container_traffic=True`.
   - Pass `MLFLOW_TRACKING_URI` (from `manage-mlflow`) in `environment` to log metrics and artifacts automatically.

Read `references/distributed-training-and-automl.md` for complete, copy-pasteable code templates.

## References

- `references/distributed-training-and-automl.md` — Complete code patterns for SDK v3 `@remote` decorator, Distributed PyTorch (`torchrun` DDP/FSDP) with Spot Checkpointing, Segment Anything (`SAM`) `MaskDecoder` fine-tuning, and SageMaker Autopilot AutoML API v2 (`CreateAutoMLJobV2`) with Holiday Calendars and Clarify explainability.
