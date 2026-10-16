# GPU Capacity, Quotas & Accelerator Strategy for Startups

AI/ML startups frequently hit a wall not on code, but on **AWS GPU Service Quotas (`All G and VT Spot/On-Demand Instance Requests`, `All P Instance Requests`)** and capacity availability. Use this reference whenever a startup asks about GPUs, fine-tuning, custom model hosting, or quota rejections.

---

## 1. First Question: Do You Actually Need Raw GPUs?

Before requesting GPU quotas, run this stage check:
- **Text / Multimodal LLM Inference (<50M tokens/day)**: Use **Amazon Bedrock On-Demand (Cross-Region Inference Profiles)** or **Bedrock Batch Inference (50% discount)**. Zero GPU quota needed, $0 idle cost, 100% covered by AWS Activate credits.
- **Fine-Tuning Open-Weight Models (Llama, Mistral, Qwen)**: Prefer **Amazon Bedrock Custom Model Fine-Tuning** or **SageMaker JumpStart Training Jobs** (ephemeral GPUs spun up only for the training window and terminated automatically at job completion).
- **Custom Vision / Audio / Diffusion / Proprietary Weights**: Requires GPU or AWS Neuron instances — follow the instance selection and quota playbook below.

---

## 2. Startup GPU & Accelerator Selection Matrix (us-east-1 Reference Rates)

| Instance Family | Accelerator | VRAM / Memory | Approx. On-Demand Rate | Best Startup Use Case | Quota Difficulty |
|---|---|---|---|---|---|
| **`g6.xlarge` – `g6.12xlarge`** | NVIDIA L4 (1–4 GPUs) | 24 GB per GPU | ~$0.80/hr (`g6.xlarge`) | Small vision models, Whisper ASR, embeddings, 7B–8B quantized LLMs | **Low** (Fastest approval for Seed startups) |
| **`g6e.xlarge` – `g6e.12xlarge`** | NVIDIA L40S (1–4 GPUs) | 48 GB per GPU | ~$1.86/hr (`g6e.xlarge`) | 8B–70B vLLM inference, Flux/SDXL image generation, LoRA fine-tuning | **Low–Medium** |
| **`inf2.xlarge` – `inf2.48xlarge`** | AWS Inferentia2 | 32–384 GB HBM | ~$0.76/hr (`inf2.xlarge`) | High-throughput, low-cost production inference (`optimum-neuron` / vLLM Neuron) | **Low** (High availability, stretches Activate credits ~40% further) |
| **`trn1.2xlarge` / `trn1.32xlarge`** | AWS Trainium | 32–512 GB HBM | ~$1.34/hr (`trn1.2xlarge`) | Pre-training and full-parameter fine-tuning on Activate credits | **Low–Medium** |
| **`p4d.24xlarge` / `p5.48xlarge`** | 8x NVIDIA A100 / H100 | 320–640 GB HBM | ~$21.96–$55+/hr | Foundation model training & massive multi-node distributed clusters | **Very High** (Use **EC2 Capacity Blocks for ML**) |

---

## 3. How to Get GPU Quotas Approved on a New Startup Account

New AWS accounts often start with `0 vCPUs` for `Running On-Demand G and VT instances` and `Running On-Demand P instances`. If a founder requests 64 vCPUs on a brand-new account with $0 spend history, automated checks often reject it.

### Step-by-Step Quota Approval Playbook:
1. **Verify Current Quota via `aws-mcp` (Read-Only)**:
   - ServiceCode: `ec2`
   - `L-DB2E81BA` (`Running On-Demand G and VT instances`)
   - `L-3819A6DF` (`All G and VT Spot Instance Requests`)
   - `L-417A185B` (`Running On-Demand P instances`)
2. **Start with a Progressive Request (4–16 vCPUs first)**:
   - Request `4 vCPUs` (`g6.xlarge` or `g6e.xlarge`) or `16 vCPUs` (`g6e.4xlarge`) first rather than 128 vCPUs.
3. **Include Concrete Justification in the Support Case**:
   - State the exact instance type (`g6e.2xlarge` = 8 vCPUs), target region (`us-east-1` or `us-west-2`), workload type (e.g., "Hosting vLLM inference for 8B model during Seed beta"), and mention **AWS Activate Portfolio ID** if enrolled.
4. **Use Multi-Region Flexibility**:
   - `us-east-2` (Ohio), `us-west-2` (Oregon), and `eu-north-1` (Stockholm) frequently have higher G6/G6e/P5 Spot and On-Demand availability than `us-east-1`.

---

## 4. Purchasing Mechanisms by Workload Pattern

1. **SageMaker Managed Spot Training (`use_spot_instances=True` + S3 Checkpointing)**:
   - Cuts training cost by up to **70%** and does not leave an interactive EC2 instance idling overnight when training finishes at 3 AM.
2. **EC2 Capacity Blocks for ML (For H100 `p5` / A100 `p4d` / `trn2`)**:
   - Reserve 1 to 64 GPUs for 1 to 182 days with guaranteed start dates for scheduled training runs — no long-term 1-year Savings Plan lock-in required.
3. **Mandatory Idle-GPU Guardrail**:
   - Never deploy an interactive GPU EC2 instance or SageMaker Notebook (`ml.g5.*` / `ml.g6e.*`) without an automated **CloudWatch GPU/CPU idle alarm** or lifecycle auto-stop script (`60 minutes idle → stop-instance`). A single forgotten `g6e.12xlarge` ($10.49/hr) burns **$7,657/month** of Activate credits.
