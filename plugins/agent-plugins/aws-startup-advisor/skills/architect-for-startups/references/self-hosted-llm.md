# Self-Hosted Open-Weight LLMs vs. Amazon Bedrock: Break-Even & Architecture Guide

Founders often assume hosting open-weight models (`Llama 4`, `DeepSeek-R1`, `Qwen`, `Mistral`) on their own GPU instances (`EC2` / `EKS` / `SageMaker Endpoints` running `vLLM` or `TGI`) is cheaper than managed API tokens. **For 90% of Pre-Revenue and Seed startups, self-hosting is 5x–20x MORE expensive because GPUs bill 24/7 during idle hours.**

Load this reference whenever a startup asks to self-host an LLM on EC2, EKS, or SageMaker, or asks for the financial break-even between Amazon Bedrock and self-managed GPUs.

---

## 1. The Startup Break-Even Math (24/7 GPU Floor vs. Pay-Per-Token)

### Baseline Minimum Self-Hosted Production Cost (Single-Replica vs. HA)
- **7B–14B Model (`vLLM` on 1x `g6e.xlarge` L40S 48GB)**:
  - Single instance (no HA): `$1.86/hr * 730 hrs = $1,358/month`
  - 2-AZ Production HA: **`$2,716/month` minimum floor** (before a single token is served)
- **70B Model (`vLLM` FP8/AWQ on `g6e.12xlarge` 4x L40S 192GB)**:
  - Single instance: `$10.49/hr * 730 hrs = $7,658/month`
  - 2-AZ Production HA: **`$15,316/month` minimum floor**

### What That Same Money Buys on Amazon Bedrock On-Demand
Using [`../../shared/pricing/bedrock-pricing.json`](../../shared/pricing/bedrock-pricing.json):
- **`$1,358/month` on Bedrock buys**:
  - **~6.7 Billion tokens/month** (~225M tokens/day) on **Amazon Nova Lite** (`$0.06/1M input`, `$0.24/1M output`), OR
  - **~679 Million tokens/month** (~22M tokens/day) on **Claude Haiku 4.5** (`$1.00/1M input`, `$5.00/1M output`), OR
  - **~226 Million tokens/month** (~7.5M tokens/day) on **Claude Sonnet 5** (`$2.00/1M input`, `$10.00/1M output`).

### Decision Rule by Daily Token Volume

| Sustained Traffic Volume | Verdict | Why |
|---|---|---|
| **< 20M tokens/day** (Pre-Revenue / Seed) | **100% Amazon Bedrock On-Demand (CRIS)** | Pay-per-token costs `$10–$300/mo`. Self-hosting wastes `$1,350+/mo` on idle GPU hours and engineering maintenance. |
| **20M – 100M tokens/day** (Seed / Series A) | **Bedrock Prompt Caching + Batch Inference (50% off) + Model Routing** | Routing classification/extraction to Nova Lite / Haiku 4.5 and enabling Prompt Caching cuts Bedrock spend by 60–80% with zero GPU ops. |
| **> 100M tokens/day sustained** OR **Custom Fine-Tuned Weights** | **Self-Hosted `vLLM` on EC2/EKS (`g6e` / `inf2`) or Bedrock Custom Model Import** | High utilization (>50% around the clock) amortizes the 24/7 GPU floor below per-token pricing. |

---

## 2. Architecture Options When Self-Hosting Is Required

When a startup genuinely needs custom weights (LoRA adapters, domain-specific fine-tunes, or >100M tokens/day sustained throughput), recommend in order of operational simplicity:

### Option 1: Amazon Bedrock Custom Model Import (Serverless Custom Weights)
- **Best for**: Spiky or moderate traffic with custom fine-tuned Llama / Mistral / Qwen weights.
- **How it works**: Import custom safetensors weights from S3 into Bedrock Custom Model Import; billed in 5-minute active model-copy windows rather than 24/7 static instances, invoked via the standard Bedrock `InvokeModel` / `Converse` API.

### Option 2: Amazon SageMaker AI Real-Time Endpoints with Scale-to-Zero
- **Best for**: Seed/Series A teams (2–5 engineers) without a dedicated Kubernetes platform team.
- **How it works**: Deploy the official AWS DJL (`LMI` / `vLLM`) container on `ml.g6e.xlarge` or `ml.inf2.xlarge` with SageMaker Inference Component scale-to-zero (`MinCapacity = 0` during off-hours, waking on request via CloudWatch alarm).

### Option 3: `vLLM` on ECS Fargate/EC2 GPU or EKS with Karpenter (Series B+)
- **Best for**: Series B+ AI-native startups with dedicated ML infra engineers serving high-QPS traffic.
- **Key optimizations**:
  - Enable **prefix caching** (`--enable-prefix-caching`) and **chunked prefill** (`--enable-chunked-prefill`) in `vLLM`.
  - Store model weights on **Amazon S3 Express One Zone** or pre-baked **EBS Snapshot AMIs** (with EBS Fast Snapshot Restore on critical prod weights) to cut cold-start node boot times from 12 minutes to <90 seconds.
  - Pair with **AWS Inferentia2 (`inf2`)** via `vLLM-Neuron` for 30–50% lower price-performance than comparable GPU instances.
