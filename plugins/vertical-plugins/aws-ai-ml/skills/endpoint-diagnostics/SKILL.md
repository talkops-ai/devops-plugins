---
name: endpoint-diagnostics
description: >-
  Collects deterministic, read-only diagnostic information from a SageMaker AI endpoint using
  documented AWS APIs and CloudWatch MCP tools. Returns endpoint status, ProductionVariant and
  InferenceComponent states, CloudWatch metrics (Invocations, ModelLatency, OverheadLatency,
  4XX/5XX errors, CPU/GPU/Memory utilization), and recent container logs for root-cause analysis.
  Use when the user reports endpoint errors, latency, inference failures, OOM crashes, or failed
  endpoint deployments. For Model Monitor drift schedules and Blue/Green deployment guardrails,
  coordinate with sagemaker-observability-governance.
metadata:
  version: "1.0.0"
---

# Endpoint Diagnostics

Collects diagnostic information from a SageMaker endpoint using documented AWS APIs (`scripts/collect_diagnostics.py`) and the `cloudwatch` MCP server. Returns endpoint status, CloudWatch metrics, and recent container logs for root-cause interpretation.

## Prerequisites

- AWS credentials configured with permissions described in [minimum_iam_policy.md](references/minimum_iam_policy.md)
- The SDK environment has been verified (SDK version, region, execution role). If not done, activate the `sdk-getting-started` skill first.

## Principles

1. **Read-only**: No mutations — only `DescribeEndpoint`, `DescribeInferenceComponent`, `GetMetricData`, and `FilterLogEvents` / `cloudwatch` MCP queries.
2. **Deterministic**: Collects structured facts first; the agent provides root-cause interpretation and remediation guidance.
3. **Graceful degradation**: Each collection step is independent; failures in one do not block others.
4. **Multi-Variant & InferenceComponent Aware**: `collect_diagnostics.py` collects instance-level metrics (CPU, Memory, GPU) for the first `ProductionVariant` automatically; when the endpoint hosts multiple `ProductionVariants` or `InferenceComponents`, supplement with `cloudwatch` MCP queries scoped by `VariantName` or `InferenceComponentName` (`InvocationsPerCopy`, `ModelLatency`, `OverheadLatency`) and inspect `/aws/sagemaker/InferenceComponents/<ic-name>`.

## Trigger

Activate when the user:

- Reports **endpoint** issues, `ModelError` (424), `InternalFailure` (500), `ServiceUnavailable` (503), or high latency
- Asks to check endpoint health, status, or metrics
- Wants to debug inference failures, CUDA OOM crashes, or timeouts on a **deployed endpoint**
- Reports a **deployment failure** (endpoint or inference component creation failed / rolled back)
- Asks about instance count, container logs, or resource utilization of an endpoint

### Do NOT activate for

- **Training job failures** — use `finetuning`, `sagemaker-training-architect`, or `hyperpod-Troubleshooting` instead.
- **Creating, updating, or deleting endpoints** — use `model-deployment` or `sagemaker-inference-architect`.
- **Configuring Model Monitor drift schedules or Blue/Green Deployment Guardrails** — use `sagemaker-observability-governance`.

## Requirements

- **Endpoint name**: The SageMaker endpoint to diagnose
- **AWS region**: The region where the endpoint is deployed

## Workflow

### Step 1: Collect inputs

For this step, you need the **endpoint name** and **AWS region**:

1. Check conversation history — the user may have already mentioned the endpoint name or region.
2. Silently read project files (e.g., deployment notebooks, config files, `sdk-getting-started` output) for the region or endpoint name.
3. Only if still unknown, ask the user for the missing values.

⏸ Wait for user response if any values are missing.

### Step 2: Run diagnostics

Execute `scripts/collect_diagnostics.py` with the endpoint name and region. Do not create a notebook — run the script directly:

```python
from collect_diagnostics import collect_endpoint_diagnostics
results = collect_endpoint_diagnostics(endpoint_name="my-endpoint", region="us-east-1")
```

The script collects:

- Endpoint status, `FailureReason`, and `ProductionVariants` via `DescribeEndpoint`
- CloudWatch metrics (`Invocations`, `Invocation4XXErrors`, `Invocation5XXErrors`, `ModelError`, `ModelLatency`, `OverheadLatency`, `CPUUtilization`, `MemoryUtilization`, `GPUUtilization`, `GPUMemoryUtilization`) for the last 5 minutes
- Container logs from `/aws/sagemaker/Endpoints/<endpoint-name>` from the last 15 minutes (up to 100 events)

If the endpoint uses **Inference Components** (`InferenceComponentName`), also query `/aws/sagemaker/InferenceComponents/<ic-name>` and `DescribeInferenceComponent` via the `cloudwatch` or `aws-mcp` tools.

### Step 3: Present results & Root-Cause Guidance

Present the collected data to the user and diagnose the failure pattern:

- **`ModelLatency` high vs `OverheadLatency` high**: High `ModelLatency` indicates slow container execution (batch size, uncompiled weights, KV-cache saturation, CPU/GPU bottleneck); high `OverheadLatency` indicates payload serialization/network overhead or cold-start scaling from zero.
- **`GPUMemoryUtilization > 95%` + container OOM / `CUDA out of memory`**: Recommend lowering `OPTION_MAX_ROLLING_BATCH_SIZE`, enabling tensor parallelism (`OPTION_TENSOR_PARALLEL_DEGREE`), quantizing (AWQ/GPTQ/FP8), or upgrading the instance / `InferenceComponent` `ComputeResourceRequirements.AcceleratorChips`.
- **`CapacityError` / `InsufficientInstanceCapacity`**: Recommend trying an alternate Availability Zone, switching instance family (`ml.g6` / `ml.g6e` / `ml.inf2` vs `ml.g5`), or checking `Service Quotas`.
- **Health check timeout (`/ping` failing)**: Check container startup logs for S3 weight download bottlenecks, missing `HF_TOKEN` for gated models, or incompatible CUDA/Neuron driver versions.

For any issues found, reference the official AWS troubleshooting guide:
https://docs.aws.amazon.com/sagemaker/latest/dg/deploy-model-troubleshoot.html

## References

- [Minimum IAM Policy](references/minimum_iam_policy.md)
- [AWS Endpoint Troubleshooting Guide](https://docs.aws.amazon.com/sagemaker/latest/dg/deploy-model-troubleshoot.html)
- [CloudWatch Metrics for SageMaker](https://docs.aws.amazon.com/sagemaker/latest/dg/monitoring-cloudwatch.html)
