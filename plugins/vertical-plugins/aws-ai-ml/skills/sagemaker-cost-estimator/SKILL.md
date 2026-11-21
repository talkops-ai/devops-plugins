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

## MCP-Only Execution & Read-Only Safety

- **MCP-Only Live Queries:** Execute **all** live AWS discovery, Bedrock/SageMaker control-plane checks, pricing lookups, IaC compliance checks, CloudWatch telemetry queries, and documentation searches **exclusively via connected MCP tools**: `aws-mcp` (`aws___run_script` using read-only `await call_boto3(...)`, `aws___search_documentation`, `aws___read_documentation`), `sagemaker` (`describe_hp_cluster`), `agentcore`, `strands-agents`, `cloudwatch`, `awspricing` (`get_pricing`, `get_bedrock_patterns`), `awsiac`, and `awsknowledge`. Offline pure-Python bundled helper scripts in `scripts/*.py` that perform local math/schema rendering without live AWS credentials are permitted when inspecting local inputs, whereas live AWS API queries must go through MCP rather than raw `aws` CLI or boto3 shell scripts.
- **Strict Read-Only & Secret Safety:** **Never** run raw `aws ...` (not even `aws sts get-caller-identity` — always query `sts.GetCallerIdentity` inside `aws___run_script`) CLI commands in Bash/`run_command`, **never** mutate live AWS resources (`Create*`, `Update*`, `Delete*`, `InvokeModel`, `CreateEndpoint` — refuse unapproved mutations and present a safe, approval-gated FinOps/provisioning plan), and **never** read or expose plaintext secrets (`secretsmanager:GetSecretValue`, `ssm:GetParameter` with `WithDecryption=True`, or `.env` API keys).
- **Unmapped Edge Cases:** Query `awsknowledge` / `aws-mcp` documentation search tools (`aws___search_documentation`, `aws___read_documentation`) with 1–2 focused queries before recommending unverified pricing attributes or SKU filters.

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
   - **Optimization B (AWS Trainium)**: Always surface `ml.trn1` / `ml.trn2` vs `ml.p4d` / `ml.g5` (up to **50% lower cost-to-train**) as an architectural alternative whenever estimating GPU training jobs
2. **Inference Optimization**:
   - **Baseline (Naive 1-Model-Per-Endpoint)**: $M \times 730\,\text{hrs} \times \text{Rate}_{\text{Host}}$
   - **Optimization A (`InferenceComponent` Multi-Model Bin-Packing)**: Pack multiple models/adapters onto shared `ml.g5.12xlarge` / `ml.g6e.12xlarge` instances using `ComputeResourceRequirements` (`AcceleratorChips`, `MemoryInMB`) and `CopyCount` (**40%–80% reduction in instance count**)
   - **Optimization B (`InferenceComponent` Scale-to-Zero)**: Set `MinCapacity=0` on `SageMakerVariantInvocationsPerCopy` so idle models scale down to 0 copies and the underlying endpoint scales to **0 instances ($0/hr compute)** outside active traffic hours
   - **Optimization C (AWS Inferentia2 `ml.inf2`)**: Compile/serve on `ml.inf2.xlarge` / `ml.inf2.8xlarge` / `ml.inf2.24xlarge` for **35%–50% lower price-performance** vs comparable GPU instances
   - **Optimization D (Serverless / Async / Bedrock Crossover)**: Calculate the exact break-even utilization (`U_break-even = R_realtime_hr / (3600 × R_serverless_sec)` plus Serverless inference request charges `~$0.20 / 1M requests`, typically crossing over around **~20%–25% daily utilization**; always state Serverless limits: **`≤ 6 GB` RAM max, CPU-only, `≤ 4 MB` payload, `60s` timeout**) and Asynchronous Inference mechanics (**up to `1 GB` S3 payloads, up to `1 hr` timeout**, scaling `MinCapacity=0` to `$0/hr` when the S3 queue drains).
3. **Commitment & Credit Strategy**:
   - **SageMaker Savings Plans**: 1-year or 3-year commitment (No Upfront, Partial Upfront, All Upfront) offering **up to 64% discount** across Studio, Training, Real-Time Inference, and Batch Transform regardless of instance family or region.
   - **AWS Activate / POC Credits**: Note how startup/POC credits apply to SageMaker compute vs Marketplace third-party model subscriptions (Marketplace software fees are typically excluded from standard Activate credits).

### Step 4: Render Cost Estimate Report (`COST_ESTIMATE.md` Format)

**Always render the complete cost estimate report directly inline in your final response** (only write `COST_ESTIMATE.md` to disk if the user explicitly asks to save a file — never rely solely on an external artifact/file link):

1. **Live Pricing Table** (Region, Service Code, Instance/Resource Type, Unit Rate, Timestamp of `awspricing` lookup)
2. **Component Breakdown** (Studio Spaces + Storage, Training Jobs, Inference Hosting, MLOps/Observability)
3. **Baseline vs. Architect-Optimized Monthly TCO Comparison Table** (showing monthly `$` and `%` savings)
4. **Actionable FinOps Guardrails** (Idle Shutdown settings, Spot checkpoint config, `InferenceComponent` packing density, Scale-to-Zero alarms, Savings Plan recommendation)

## References

- `references/sagemaker-finops-formulas.md` — Exact `awspricing` MCP filter recipes, mathematical TCO equations for Studio, Training, `InferenceComponent` bin-packing, Scale-to-Zero, and Bedrock vs SageMaker break-even formulas.
