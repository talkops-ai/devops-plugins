---
name: braket-cost-governance-and-security
description: "Enforce pre-execution QPU and simulator cost estimation, per-device spending limits, S3 KMS encryption, VPC private networking, and IAM least-privilege execution roles for Amazon Braket quantum workloads. Query live AWS state via MCP tools only (never raw aws CLI)."
---

# Amazon Braket Cost Governance, Security & Operations

Use this skill to prevent runaway quantum computing bills, calculate exact QPU/simulator costs before running tasks, and secure Braket Hybrid Jobs with least-privilege IAM, KMS, and VPC isolation.

## 1. Mandatory Pre-Execution Cost Calculation Formula

**NEVER submit a QPU task (`create_quantum_task`) or Hybrid Job (`create_job`) without calculating and presenting the estimated cost first.**

1. **Gate-Based QPU Cost per Task**:
   $$\text{Task Cost} = \text{Per-Task Fee} + (\text{Shots} \times \text{Per-Shot Price})$$
   - For variational algorithms (VQE/QAOA) using parameter-shift gradients:
     $$\text{Total Tasks} = \text{Iterations} \times (2 \times \text{Parameters} + 1)$$
     *(Warning: 100 iterations with 20 parameters = 4,100 QPU tasks! Always prototype on local simulator + SV1 first.)*
2. **Managed Simulator (`SV1`, `DM1`, `TN1`) Cost**:
   - Billed per **minute/second of task execution duration** (minimum 3 seconds per task).
3. **Hybrid Job Classical Instance Cost**:
   - Billed for the `ml.*` instance duration from container start to completion (plus any idle wait time while queued on a QPU unless using checkpointed runs).
4. **In-Session Cost Estimation (`Tracker`) vs. Hard Server-Side Enforcement (`SpendingLimits`)**:
   - **Client-Side Estimate (`braket.tracking.Tracker`):** Tracks near-real-time session estimates (`qpu_tasks_cost()`, `simulator_tasks_cost()`, `quantum_tasks_statistics()`) so an algorithm loop can check estimated spend between steps and `break`, **but `Tracker` is an estimate only and never rejects tasks server-side**.
     ```python
     from braket.tracking import Tracker
     cost_tracker = Tracker().start()
     # ... check cost_tracker.qpu_tasks_cost() between loop steps ...
     print(f"Estimated Quantum Task Cost: ${cost_tracker.qpu_tasks_cost() + cost_tracker.simulator_tasks_cost():.2f}")
     ```
   - **Hard Server-Side Cap (`CreateSpendingLimit` / `SearchSpendingLimits`):** The **only** control that rejects QPU `CreateQuantumTask` calls server-side when a budget is reached. Spending limits are scoped **per `deviceArn` (QPU ARNs only, not simulators)** with an optional `timePeriod` (`startAt`, `endAt`); restrict `braket:UpdateSpendingLimit` and `braket:DeleteSpendingLimit` in IAM and audit changes in CloudTrail.

## 2. Security, Encryption & IAM Guardrails

- **S3 Bucket Naming & Encryption**:
  - Braket writes task results to `amazon-braket-<region>-<account-id>` by default. Configure default **SSE-KMS** encryption and `PublicAccessBlock` on all `amazon-braket-*` S3 buckets.
- **Private VPC Isolation & AWS PrivateLink (`CreateJob` Has No `VpcConfig`)**:
  - Unlike SageMaker `CreateTrainingJob`, Amazon Braket `CreateJob` runs in Braket-managed infrastructure and **does NOT accept `VpcConfig` (`SecurityGroupIds` / `Subnets`)**. Never invent `VpcConfig` on `CreateJob`.
  - To eliminate public internet (`0.0.0.0/0` NAT/IGW) egress for **caller/orchestrator workloads** (notebooks, ECS/EKS, EC2, or SageMaker jobs submitting tasks/jobs and pulling results), place caller compute in private subnets with **VPC Interface Endpoints** for `com.amazonaws.<region>.braket`, `com.amazonaws.<region>.logs`, `com.amazonaws.<region>.ecr.api`, `com.amazonaws.<region>.ecr.dkr`, and `com.amazonaws.<region>.kms` plus a **VPC Gateway Endpoint** for `com.amazonaws.<region>.s3`.
  - When running Braket Hybrid Jobs, enforce isolation via pre-built BYOC images in private ECR (no runtime `pip` internet pulls), `outputDataConfig.kmsKeyId` SSE-KMS encryption, and least-privilege `roleArn` + `aws:SourceAccount`/`aws:SourceArn` S3 bucket policies (or run the classical loop inside your own VPC-isolated ECS/EKS/SageMaker container calling `CreateQuantumTask` over PrivateLink if customer-VPC container ENI control is mandatory, trading off Hybrid Job QPU priority queueing).
- **EventBridge Monitoring**:
  - Route `Braket Task State Change` and `Braket Job State Change` events (`COMPLETED`, `FAILED`, `CANCELLED`) via EventBridge to SNS/Slack so researchers never poll in a billable compute loop.
