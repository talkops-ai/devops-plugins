---
name: sagemaker-observability-governance
description: >-
  Architects production observability, safe deployment guardrails, drift monitoring, and root-cause
  diagnostics for Amazon SageMaker AI. Covers Deployment Guardrails (Blue/Green Canary & Linear
  traffic shifting, Auto-Rollback CloudWatch Alarms, Shadow Production Variants), Data Capture,
  SageMaker Model Monitor (Data Quality, Model Quality with ground-truth joins, Clarify Bias Drift,
  and Clarify Feature Attribution / SHAP Drift schedules), EventBridge automated retraining triggers,
  and live CloudWatch MCP log/metric forensics across Endpoints, InferenceComponents, and Training
  Jobs. Coordinates with endpoint-diagnostics for read-only endpoint health snapshots. Use when
  configuring production rollouts, Model Monitor drift detection, CloudWatch alarms, or debugging
  SageMaker jobs/endpoints.
metadata:
  version: "1.0.0"
---

# SageMaker Observability, Deployment Guardrails, Drift Monitoring & Governance

Protects production ML endpoints from silent model degradation, bad deployments, and capacity/latency outages through automated guardrails, Model Monitor schedules, and CloudWatch MCP diagnostics.

## When to Activate

- User is deploying or updating a production endpoint and needs **Blue/Green Deployment Guardrails** (Canary or Linear traffic shifting), **Auto-Rollback CloudWatch Alarms**, or **Shadow Testing (`ShadowProductionVariants`)**
- User wants to enable **Endpoint Data Capture (`DataCaptureConfig`)** and configure **SageMaker Model Monitor** across any of the 4 monitoring pillars:
  1. **Data Quality Drift** (`CreateDataQualityJobDefinition`)
  2. **Model Quality Drift** (`CreateModelQualityJobDefinition` with ground-truth join)
  3. **Model Bias Drift** (`CreateModelBiasJobDefinition` via SageMaker Clarify)
  4. **Feature Attribution / Explainability Drift** (`CreateModelExplainabilityJobDefinition` via KernelSHAP)
- User wants to automate **drift-triggered retraining** via Amazon EventBridge → SageMaker Pipelines
- User needs deep **CloudWatch Logs Insights or Metric forensics** using the `cloudwatch` MCP server across `/aws/sagemaker/Endpoints/*`, `/aws/sagemaker/InferenceComponents/*`, or `/aws/sagemaker/TrainingJobs`
- *(For quick, deterministic read-only status/log/metric collection on a single failing endpoint, also run or coordinate with `endpoint-diagnostics` and its `scripts/collect_diagnostics.py`.)*

---

## Core Capabilities & Workflow

### 1. Safe Production Rollouts: Blue/Green Guardrails & Shadow Variants

Never overwrite a production endpoint in-place without traffic shifting and auto-rollback alarms:

| Rollout Strategy | Configuration | Best For |
|---|---|---|
| **Blue/Green Canary (`CANARY`)** | Shifts a small canary slice (e.g., `10%` of instances/traffic) for a bake window (`WaitIntervalInSeconds: 600`), then shifts `100%` if no `AutoRollbackConfiguration` alarms fire | Fast validation of new model versions with immediate blast-radius containment |
| **Blue/Green Linear (`LINEAR`)** | Shifts traffic in equal increments (e.g., `20%` every `300s`) while monitoring CloudWatch alarms at every step | High-traffic tier-1 endpoints where gradual cache warming and tail-latency observation are critical |
| **Shadow Testing (`ShadowProductionVariants`)** | Mirrors a configurable percentage (e.g., `25%`) of live production requests to a shadow candidate variant (`ShadowProductionVariants`) while returning only the primary production variant's response to callers | Zero-customer-impact validation of new LLM/vision models or `ml.inf2` compiled artifacts under real production payloads |

---

### 2. The 4 Pillars of SageMaker Model Monitor

1. **Step A — Enable `DataCaptureConfig` on the Endpoint**:
   - Set `EnableCapture: True`, `InitialSamplingPercentage` (e.g., `20`–`100`), `CaptureOptions: [{"CaptureMode": "Input"}, {"CaptureMode": "Output"}]`, and `KmsKeyId`.
2. **Step B — Run Baseline Profiling Job**:
   - Run the SageMaker Model Monitor Analyzer container (`sagemaker-model-monitor-analyzer`) or Clarify container against the training/validation baseline dataset to produce `statistics.json` and `constraints.json` in S3.
3. **Step C — Create Scheduled Monitoring Job (`CreateMonitoringSchedule`)**:
   - **Data Quality**: Runs hourly (`cron(0 * ? * * *)`) or daily (`cron(0 20 * * ? *)`) comparing captured endpoint inputs against `constraints.json`.
   - **Model Quality**: Merges captured endpoint predictions with delayed ground-truth labels (`StartTimeOffset: "-PT24H"`, `EndTimeOffset: "-PT1H"`) to alert when live F1/Accuracy/AUC/RMSE drops below threshold.
   - **Bias & Explainability (Clarify)**: Detects live demographic bias shift (`DPL`, `DI`) and SHAP feature attribution ranking drift.
4. **Step D — Automated EventBridge Retraining Loop**:
   - When Model Monitor emits `CompletedWithViolations` to CloudWatch / EventBridge, trigger `sagemaker:StartPipelineExecution` on the `sagemaker-mlops-pipelines` retraining DAG.

---

### 3. Live Diagnostics with `cloudwatch` MCP Server & `endpoint-diagnostics`

When diagnosing latency spikes, 4XX/5XX errors, or training/endpoint crashes:

1. **Run `endpoint-diagnostics`** (`scripts/collect_diagnostics.py`) for immediate `DescribeEndpoint`, 5-minute CloudWatch metrics, and recent container logs.
2. **Query `cloudwatch` MCP Server for Deep Forensics**:
   - **Log Groups**:
     - `/aws/sagemaker/Endpoints/<endpoint-name>`
     - `/aws/sagemaker/InferenceComponents/<inference-component-name>`
     - `/aws/sagemaker/TrainingJobs`
     - `/aws/sagemaker/ProcessingJobs`
   - **Key Metrics (`AWS/SageMaker` & `/aws/sagemaker/Endpoints`)**:
     - Latency breakdown: `ModelLatency` (µs inside container) vs `OverheadLatency` (µs SageMaker routing/serialization/cold-start)
     - Error rates: `Invocation4XXErrors`, `Invocation5XXErrors`, `ModelError` (HTTP 424), `NoCapacityInvocationFailures`
     - `InferenceComponent` density: `InvocationsPerCopy`, `CPUUtilizationNormalized`, `MemoryUtilizationNormalized`, `GPUUtilizationNormalized`, `GPUMemoryUtilizationNormalized`

Read `references/guardrails-model-monitor-cloudwatch.md` for complete production code templates.

## References

- `references/guardrails-model-monitor-cloudwatch.md` — Complete `boto3` code for Blue/Green Canary/Linear `DeploymentConfig` with `AutoRollbackConfiguration`, `ShadowProductionVariants`, `DataCaptureConfig`, Model Monitor Data/Model Quality schedules, EventBridge retraining rules, and CloudWatch Logs Insights queries.
