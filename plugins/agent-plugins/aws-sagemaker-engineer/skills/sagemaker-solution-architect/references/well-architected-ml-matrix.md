# AWS Well-Architected Machine Learning Lens Reference Matrix

## 1. Accelerator & Instance Family Selection Matrix

Always verify live regional availability and pricing via `sagemaker-cost-estimator` (`awspricing` MCP server) and service quotas before committing to an instance family.

| Instance Family | Accelerator / GPU | VRAM per Chip (Total VRAM) | Network / EFA | Primary Sweet Spot |
|---|---|---|---|---|
| `ml.g5` (`xlarge` – `48xlarge`) | NVIDIA A10G (1 – 8 GPUs) | 24 GB (24 – 192 GB) | Up to 100 Gbps (EFA on `48xlarge`) | Cost-effective single-GPU/multi-GPU inference (7B–32B AWQ/FP16), LoRA fine-tuning, Vision/SAM fine-tuning |
| `ml.g6` (`xlarge` – `48xlarge`) | NVIDIA L4 (1 – 8 GPUs) | 24 GB (24 – 192 GB) | Up to 100 Gbps | High-efficiency video/vision inference, small/medium LLM serving, `InferenceComponent` multi-model packing |
| `ml.g6e` (`xlarge` – `48xlarge`) | NVIDIA L40S (1 – 8 GPUs) | 48 GB (48 – 384 GB) | Up to 400 Gbps EFA | 30B–70B LLM inference & QLoRA/LoRA fine-tuning without needing `p4d`; 2x VRAM per GPU vs `g5`/`g6` |
| `ml.p4d.24xlarge` / `ml.p4de.24xlarge` | NVIDIA A100 (8 GPUs) | 40 GB / 80 GB (320 / 640 GB HBM2e) | 400 Gbps EFA | Multi-GPU DDP/FSDP training, 70B+ FP16/BF16 training & high-concurrency LMI/vLLM serving |
| `ml.p5.48xlarge` / `ml.p5e.48xlarge` | NVIDIA H100 / H200 (8 GPUs) | 80 GB / 141 GB (640 GB / 1.1 TB HBM3e) | 3200 Gbps EFAv2 | Frontier LLM pre-training, massive FSDP on HyperPod, ultra-low-latency FP8 tensor-parallel serving |
| `ml.trn1.2xlarge` / `ml.trn1.32xlarge` / `ml.trn2.48xlarge` | AWS Trainium1 / Trainium2 (1 – 16 chips) | 32 GB / 96 GB HBM per chip | Up to 1600–3200 Gbps EFA | Up to 50% lower training cost vs comparable GPU instances for supported HuggingFace/Megatron/Neuron models |
| `ml.inf2` (`xlarge`, `8xlarge`, `24xlarge`, `48xlarge`) | AWS Inferentia2 (1 – 12 chips, 2 NeuronCores/chip) | 32 GB HBM per chip (32 – 384 GB) | Up to 200 Gbps | Up to 50% lower cost per token/inference for LLMs (Llama, Mistral, Qwen), embeddings, and diffusion/vision models compiled via `torch-neuronx` / DJL Neuron |
| `ml.m5` / `ml.c5` / `ml.c6i` / `ml.r5` | Intel Xeon CPU | System RAM (8 – 768 GB) | Up to 50 Gbps | Tabular XGBoost/LightGBM/Scikit-Learn training & inference, Data Wrangler/Spark Processing, Model Monitor jobs |

---

## 2. Training Data Input Channel Mode Matrix

Choosing the wrong S3 data input mode is a top cause of GPU starvation (`GPUUtilization < 20%` during epoch 1) and EBS `VolumeSizeInGB` exhaustion:

| Input Mode | Mechanism | When to Use | Critical Guardrail |
|---|---|---|---|
| **`FastFile` (Recommended Default)** | Exposes S3 objects via a POSIX-compliant virtual filesystem streamed on demand with local page caching | Datasets > 50 GB, thousands of medium/large files (Parquet, TFRecord, JSONL, WebDataset shards), rapid job startup | Avoid millions of tiny (< 64 KB) unsharded files (e.g., raw unarchived JPEG thumbnails); shard into WebDataset `.tar` or TFRecord/Parquet first |
| **`File`** | Downloads the entire S3 prefix to `/opt/ml/input/data/<channel>` on the instance EBS/NVMe volume before container starts | Small datasets (< 50 GB) requiring random local disk seeks | `VolumeSizeInGB` MUST exceed `1.5 × dataset_size + checkpoint_size`, or use instances with local NVMe (`ml.g5`, `ml.p4d`, `ml.p5`) |
| **`Pipe`** | Streams S3 objects directly into a named FIFO pipe without writing to disk | Streaming-compatible algorithms (SageMaker built-in XGBoost/Linear Learner, custom PipeModeDataset) | Requires sequential stream parsing; does not support random file seek |
| **Amazon FSx for Lustre** | High-throughput parallel POSIX filesystem hydrated from S3 | Multi-node DDP/FSDP training and **SageMaker HyperPod** clusters where multiple nodes read checkpoints and datasets concurrently at 10–100+ GB/s | Deploy inside the same private VPC subnet/AZ as training nodes; pair with an S3 Data Repository Association (DRA) |
| **Amazon S3 Express One Zone** | Single-AZ directory bucket (`--x-s3`) with single-digit millisecond latency | Ultra-high IOPS checkpointing and fine-grained dataset reads in the same AZ as compute | Co-locate the directory bucket AZ ID (e.g., `use1-az4`) with the SageMaker training subnet AZ |

---

## 3. AWS Well-Architected Machine Learning Lens — 6 Pillar Checklist

Include this checklist in `ARCHITECTURE.md` reviews:

1. **Operational Excellence**:
   - Every training run logs hyperparameters, metrics, and dataset S3 ETags/versions to **SageMaker Managed MLflow (`CreateMlflowApp`)**.
   - Production models are versioned in **SageMaker Model Registry (`ModelPackageGroup`)** with explicit `ModelApprovalStatus` (`PendingManualApproval` → `Approved`).
   - Orchestration uses **SageMaker Pipelines (`@step`, `Pipeline`)** rather than manual notebook execution.
2. **Security**:
   - Studio Domains run in **`VpcOnly`** mode in private subnets with PrivateLink interface/gateway endpoints.
   - Training jobs set `EnableNetworkIsolation=True` (when no external package downloads are needed) and `EnableInterContainerTrafficEncryption=True` for multi-node jobs.
   - Storage (`VolumeKmsKeyId`, `OutputKmsKeyId`, Studio EFS/EBS, Feature Store, S3) uses customer-managed KMS keys (CMKs).
   - Separate least-privilege IAM execution roles per persona (`StudioDomainExecutionRole`, `DataScientistProfileRole`, `TrainingJobRole`, `PipelineExecutionRole`, `EndpointInferenceRole`).
3. **Reliability**:
   - Long-running training jobs write periodic checkpoints to `/opt/ml/checkpoint` synced to S3 so Spot interruptions resume automatically without losing progress.
   - Real-time endpoints deploy across **≥ 2 Availability Zones** (configured via VPC subnets) with `DeploymentConfig` Blue/Green Canary/Linear traffic shifting and `AutoRollbackConfiguration`.
4. **Performance Efficiency**:
   - Right-size accelerator memory (`VRAM ≥ model_weights + KV_cache + activation_overhead`); use **SageMaker Inference Recommender** or the `model-deployment` benchmarking workflow to empirically validate p99 latency under load.
   - Use tensor parallelism (`OPTION_TENSOR_PARALLEL_DEGREE`), continuous batching (`vLLM` / `LMI`), FP8/AWQ quantization, or Neuron compilation (`ml.inf2`) for LLM serving.
5. **Cost Optimization**:
   - Always run `sagemaker-cost-estimator` (`awspricing` MCP server) before provisioning GPU/Neuron fleets.
   - Use **Managed Spot Training** (`MaxWaitTimeInSeconds > MaxRuntimeInSeconds`) for up to 90% training savings.
   - Consolidate multi-model endpoints with **SageMaker Inference Components (`InferenceComponent`)** and enable **Scale-to-Zero (`MinCapacity=0`)** on idle components.
   - Configure Studio idle auto-shutdown (`AppLifecycleManagement.IdleSettings`) so forgotten JupyterLab/CodeEditor spaces terminate automatically.
6. **Sustainability**:
   - Prefer high-efficiency silicon (`ml.inf2`, `ml.trn1`/`ml.trn2`, `ml.g6`/`ml.g6e`) and parameter-efficient fine-tuning (LoRA/QLoRA) over full fine-tuning when evaluation metrics are equivalent.
