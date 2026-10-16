---
name: braket-cost-governance-and-security
description: "Enforce pre-execution QPU and simulator cost estimation, budget circuit breakers, S3 KMS encryption, VPC private networking, and IAM least-privilege execution roles for Amazon Braket quantum workloads."
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
4. **Programmatic Cost Tracking**:
   - Use `braket.tracking.Tracker` inside every Python script or notebook to monitor live session costs and abort automatically if a threshold is exceeded:
     ```python
     from braket.tracking import Tracker
     cost_tracker = Tracker().start()
     # ... run tasks ...
     print(f"Estimated Quantum Task Cost: ${cost_tracker.qpu_tasks_cost() + cost_tracker.simulator_tasks_cost():.2f}")
     ```

## 2. Security, Encryption & IAM Guardrails

- **S3 Bucket Naming & Encryption**:
  - Braket writes task results to `amazon-braket-<region>-<account-id>` by default. Configure default **SSE-KMS** encryption and `PublicAccessBlock` on all `amazon-braket-*` S3 buckets.
- **VPC Isolation for Hybrid Jobs**:
  - Pass `VpcConfig` (`SecurityGroupIds`, `Subnets`) in `create-job` with VPC Interface Endpoints for `com.amazonaws.<region>.braket`, `com.amazonaws.<region>.logs`, `com.amazonaws.<region>.ecr.api`, `com.amazonaws.<region>.ecr.dkr`, and Gateway Endpoint for `s3`.
- **EventBridge Monitoring**:
  - Route `Braket Task State Change` and `Braket Job State Change` events (`COMPLETED`, `FAILED`, `CANCELLED`) via EventBridge to SNS/Slack so researchers never poll in a billable compute loop.
