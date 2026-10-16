# SageMaker FinOps Formulas & `awspricing` MCP Query Recipes

## 1. Querying `awspricing` MCP Server for SageMaker

When calling `get_pricing` on the `awspricing` MCP server:

- **Service Code**: `"AmazonSageMaker"`
- **Common Filter Attributes**:
  - `regionCode`: e.g., `"us-east-1"`, `"us-west-2"`, `"eu-west-1"`, `"ap-northeast-1"`
  - `instanceType` or `component`: e.g., `"ml.g5.2xlarge"`, `"ml.g5.12xlarge"`, `"ml.g6e.2xlarge"`, `"ml.p4d.24xlarge"`, `"ml.inf2.xlarge"`, `"ml.trn1.32xlarge"`
- **Tip**: Because SageMaker uses different SKU attributes for Training (`ml.g5.2xlarge-Training` or `productFamily: "ML Instance"`) vs Real-Time Hosting vs Studio, first call `get_pricing_attribute_values` for `service_code="AmazonSageMaker"` and `attribute_names=["instanceType", "productFamily", "usagetype"]` if a narrow filter returns empty results, then filter by `regionCode` and the matching `instanceType` / `usagetype`.

---

## 2. Exact Mathematical Cost Models

### A. SageMaker Studio Space Monthly TCO

Stopped Studio `JupyterLab` and `CodeEditor` apps stop billing for EC2 compute (`RunInstance`), **but their dedicated EBS volume (`SpaceStorageSettings`) and Domain EFS home directory continue billing 24/7**:

$$\text{Cost}_{\text{Studio}} = \sum_{u=1}^{U} \left( R_{\text{instance}, u} \times H_{\text{active}, u} + \text{EBS}_{\text{GB}, u} \times R_{\text{EBS-GB-mo}} + \text{EFS}_{\text{GB}, u} \times R_{\text{EFS-GB-mo}} \right)$$

- **Guardrail**: Enable `AppLifecycleManagement.IdleSettings` (`IdleTimeoutInMinutes: 60`) so $H_{\text{active}, u}$ reflects actual coding hours (~160 hrs/mo) rather than 730 hrs/mo (**78% compute savings**).

---

### B. Managed Training Job TCO (On-Demand vs Spot vs Trainium)

$$\text{Cost}_{\text{Train}} = N_{\text{nodes}} \times T_{\text{hours}} \times R_{\text{train-instance}} \times (1 - D_{\text{spot}}) + \left( N_{\text{nodes}} \times \text{EBS}_{\text{GB}} \times \frac{T_{\text{hours}}}{730} \times R_{\text{EBS-GB-mo}} \right)$$

- Where $D_{\text{spot}} \in [0.60, 0.90]$ when `EnableManagedSpotTraining=True` and checkpoints are written to `/opt/ml/checkpoint`.
- **Warm Pool Cost (`KeepAlivePeriodInSeconds`)**: If Warm Pools are enabled for rapid iterative experiments, add $N_{\text{nodes}} \times \frac{\text{KeepAliveSeconds}}{3600} \times R_{\text{train-instance}}$ per final job termination.

---

### C. Multi-Model Hosting: Naive Dedicated Endpoints vs `InferenceComponent` Bin-Packing + Scale-to-Zero

Suppose an organization needs to serve $M$ fine-tuned or specialized models (e.g., $M = 8$ models, each requiring 1 GPU or 0.5 GPU and active for $H_{\text{active}}$ hours/month):

1. **Naive Architecture (1 Real-Time Endpoint per Model, 24/7)**:
   $$\text{Cost}_{\text{Naive}} = M \times N_{\text{min-AZ}} \times 730 \times R_{\text{single-gpu-instance}}$$
   *(e.g., $8 \text{ models} \times 1 \text{ instance} \times 730 \text{ hrs} \times R_{\text{ml.g5.2xlarge}}$)*

2. **Architect-Optimized Architecture (`InferenceComponent` Packing + Scale-to-Zero)**:
   - Pack multiple `InferenceComponent` objects onto a shared multi-GPU or high-VRAM endpoint (e.g., `ml.g5.12xlarge` with 4× A10G GPUs or `ml.g6e.12xlarge` with 4× L40S 48GB GPUs).
   - Required instances during active hours:
     $$N_{\text{packed}} = \left\lceil \frac{\sum_{i=1}^{M} \text{CopyCount}_i \times \text{AcceleratorChips}_i}{\text{AcceleratorsPerInstance}} \right\rceil$$
   - With `MinCapacity=0` configured on each `InferenceComponent` via Application Auto Scaling (`SageMakerVariantInvocationsPerCopy`), when all components scale to 0 copies during off-hours, SageMaker scales the underlying endpoint instances to **0 (`$0/hr`)**:
     $$\text{Cost}_{\text{Packed}} = N_{\text{packed}} \times H_{\text{active}} \times R_{\text{multi-gpu-instance}}$$
   - **Typical Savings**: **50%–85% lower monthly hosting bill**.

---

### D. Real-Time Endpoint vs Serverless Inference vs Bedrock Break-Even Formula

1. **CPU Models (Serverless Inference vs Real-Time `ml.m5.large` / `ml.c5.large`)**:
   - Serverless Inference charges per second of compute duration $\times$ memory tier (`$/sec` for 1 GB – 6 GB) plus `$0.20` per 1M requests.
   - Break-even utilization ratio:
     $$U_{\text{break-even}} = \frac{R_{\text{realtime-hr}}}{3600 \times R_{\text{serverless-sec}}}$$
   - When average endpoint utilization is below **~20%–25% of the day** (and model fits in ≤ 6 GB RAM without GPU), **Serverless Inference** is strictly cheaper.

2. **LLM Hosting (SageMaker Real-Time GPU/Inferentia2 Endpoint vs Amazon Bedrock On-Demand Tokens)**:
   - Monthly cost of a SageMaker Real-Time Endpoint: $C_{\text{SM}} = 730 \times N_{\text{instances}} \times R_{\text{instance}}$.
   - Monthly cost of Bedrock On-Demand:
     $$C_{\text{Bedrock}} = \frac{\text{Tokens}_{\text{in, mo}}}{10^6} \times P_{\text{in}} + \frac{\text{Tokens}_{\text{out, mo}}}{10^6} \times P_{\text{out}}$$
   - **Rule of Thumb**: Below the break-even token volume (or when traffic is highly bursty), **Amazon Bedrock On-Demand** (or Bedrock Custom Model Import with 5-minute active CMU billing) is cheaper; above the break-even volume with sustained high concurrency, a tuned **SageMaker Real-Time Endpoint** on `ml.inf2` or `ml.g6e` with vLLM/LMI continuous batching yields lower cost per million tokens.
