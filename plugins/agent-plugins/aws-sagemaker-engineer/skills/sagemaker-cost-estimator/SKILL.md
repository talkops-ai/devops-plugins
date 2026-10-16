---
name: sagemaker-cost-estimator
description: >-
  Calculates pre-provisioning FinOps cost estimates and architectural savings comparisons for
  Amazon SageMaker AI workloads using live queries to the awspricing MCP server. Covers Studio
  Spaces (EC2 + 24/7 EBS/EFS storage), Managed Training Jobs (On-Demand vs Managed Spot 60-90%
  savings vs AWS Trainium ml.trn1/trn2), Real-Time Endpoints (dedicated 1-model-per-endpoint vs
  InferenceComponent multi-model bin-packing + Scale-to-Zero MinCapacity=0 vs Inferentia2 ml.inf2),
  Serverless vs Asynchronous vs Batch Transform vs Bedrock token crossover math, and SageMaker
  Savings Plans. Produces a structured COST_ESTIMATE.md report. Use before provisioning paid
  compute or whenever the user asks about SageMaker pricing, TCO, cost optimization, or FinOps.
metadata:
  version: "1.0.0"
---

# SageMaker FinOps & Pre-Provisioning Cost Estimator

Protects engineering teams from runaway GPU bills by querying live regional rates from the `awspricing` MCP server and modeling architectural cost optimizations before any compute is provisioned.

## Core Principles

1. **Never Hallucinate Static Prices**: Always query the `awspricing` MCP server (`get_pricing`, `get_pricing_service_codes`, `get_pricing_service_attributes`, `get_pricing_attribute_values`) for the user's target AWS region (`us-east-1`, `us-west-2`, `eu-west-1`, etc.).
2. **Surface Hidden 24/7 Storage & Idle Costs**: Never report only the hourly GPU rate — include Studio Space EBS + EFS storage (which bills 24/7 even when the Space app is stopped!), training EBS volume charges, S3 storage/requests, Managed MLflow, and NAT Gateway / PrivateLink data processing where relevant.
3. **Always Present a Side-by-Side Optimization Comparison**: Every `COST_ESTIMATE.md` must compare the **Baseline (Naive On-Demand)** architecture against the **Architect-Optimized** architecture (Managed Spot, Trainium/Inferentia2, `InferenceComponent` fractional GPU bin-packing + Scale-to-Zero `MinCapacity=0`, or Serverless/Async/Bedrock).

---

## Workflow

### Step 1: Extract Workload Sizing Parameters

Gather from `ARCHITECTURE.md`, `PLAN.md`, or user context:

- **AWS Region** (e.g., `us-east-1` -> `"US East (N. Virginia)"`, `us-west-2` -> `"US West (Oregon)"`)
- **Studio Footprint**: Number of users, Space instance types (`ml.t3.medium`, `ml.g5.xlarge`), active hours/day, EBS volume size (GB), EFS storage (GB)
- **Training Footprint**: Instance type (`ml.g5.2xlarge`, `ml.g6e.12xlarge`, `ml.p4d.24xlarge`, `ml.trn1.32xlarge`), instance count ($N$), estimated wall-clock hours ($T$), runs per month, EBS volume size per node
- **Inference Footprint**: Number of models ($M$), instance family (`ml.g5`, `ml.g6`, `ml.g6e`, `ml.inf2`), memory/GPU requirement per model, active traffic hours per day, daily request/token volume

### Step 2: Query Live Prices via `awspricing` MCP Server

Query the relevant AWS service codes using the `awspricing` MCP server:

- **`AmazonSageMaker`**: Studio (`RunInstance`), Training (`Train`), Hosting (`Host`), Serverless Inference, Inference Accelerator / Neuron (`ml.trn1`, `ml.inf2`, `ml.g5`, `ml.g6`, `ml.g6e`, `ml.p4d`, `ml.p5`)
- **`AmazonEC2` / `AmazonEKS`**: When pricing HyperPod underlying cluster nodes or comparing raw EC2 rates
- **`AmazonEFS` & `AmazonFSx`**: Studio Domain EFS storage (`$/GB-month`) and HyperPod / Training FSx for Lustre (`$/GB-month` + throughput `MB/s/TiB`)
- **`AmazonS3`**: Standard storage (`$/GB-month`) or S3 Express One Zone directory buckets
- **`AmazonBedrock`**: On-demand input/output token rates or Custom Model Import (CMU — Custom Model Unit) rates when comparing SageMaker endpoints against Bedrock

Read `references/sagemaker-finops-formulas.md` for exact query filter patterns and TCO equations.

### Step 3: Compute Baseline vs. Optimized Scenarios

Apply the formulas in `references/sagemaker-finops-formulas.md`:

1. **Training Optimization**:
   - **Baseline**: On-Demand `CreateTrainingJob` ($N \times \text{Rate}_{\text{OD}} \times T$)
   - **Optimization A (Managed Spot Training)**: `EnableManagedSpotTraining=True` with S3 checkpointing (typically **60%–90% discount**; query current Spot savings or model conservative 65%–70% discount)
   - **Optimization B (AWS Trainium)**: `ml.trn1` / `ml.trn2` vs `ml.p4d` / `ml.g5` (up to **50% lower cost-to-train**)
2. **Inference Optimization**:
   - **Baseline (Naive 1-Model-Per-Endpoint)**: $M \times 730\,\text{hrs} \times \text{Rate}_{\text{Host}}$
   - **Optimization A (`InferenceComponent` Multi-Model Bin-Packing)**: Pack multiple models/adapters onto shared `ml.g5.12xlarge` / `ml.g6e.12xlarge` instances using `ComputeResourceRequirements` (`AcceleratorChips`, `MemoryInMB`) and `CopyCount` (**40%–80% reduction in instance count**)
   - **Optimization B (`InferenceComponent` Scale-to-Zero)**: Set `MinCapacity=0` on `SageMakerVariantInvocationsPerCopy` so idle models scale down to 0 copies and the underlying endpoint scales to **0 instances ($0/hr compute)** outside active traffic hours
   - **Optimization C (AWS Inferentia2 `ml.inf2`)**: Compile/serve on `ml.inf2.xlarge` / `ml.inf2.8xlarge` / `ml.inf2.24xlarge` for **35%–50% lower price-performance** vs comparable GPU instances
   - **Optimization D (Serverless / Async / Bedrock Crossover)**: Calculate the exact daily request/token threshold below which Serverless Inference, Asynchronous Inference (with `MinCapacity=0`), or Amazon Bedrock is cheaper than a 24/7 Real-Time Endpoint.
3. **Commitment & Credit Strategy**:
   - **SageMaker Savings Plans**: 1-year or 3-year commitment (No Upfront, Partial Upfront, All Upfront) offering **up to 64% discount** across Studio, Training, Real-Time Inference, and Batch Transform regardless of instance family or region.
   - **AWS Activate / POC Credits**: Note how startup/POC credits apply to SageMaker compute vs Marketplace third-party model subscriptions (Marketplace software fees are typically excluded from standard Activate credits).

### Step 4: Write `COST_ESTIMATE.md`

Save `COST_ESTIMATE.md` in the project directory with:

1. **Live Pricing Table** (Region, Service Code, Instance/Resource Type, Unit Rate, Timestamp of `awspricing` lookup)
2. **Component Breakdown** (Studio Spaces + Storage, Training Jobs, Inference Hosting, MLOps/Observability)
3. **Baseline vs. Architect-Optimized Monthly TCO Comparison Table** (showing monthly `$` and `%` savings)
4. **Actionable FinOps Guardrails** (Idle Shutdown settings, Spot checkpoint config, `InferenceComponent` packing density, Scale-to-Zero alarms, Savings Plan recommendation)

## References

- `references/sagemaker-finops-formulas.md` — Exact `awspricing` MCP filter recipes, mathematical TCO equations for Studio, Training, `InferenceComponent` bin-packing, Scale-to-Zero, and Bedrock vs SageMaker break-even formulas.
