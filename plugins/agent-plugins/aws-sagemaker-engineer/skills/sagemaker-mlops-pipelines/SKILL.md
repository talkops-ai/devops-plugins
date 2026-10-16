---
name: sagemaker-mlops-pipelines
description: >-
  Architects and generates end-to-end MLOps automation on Amazon SageMaker AI. Covers SageMaker
  Pipelines DAGs (sagemaker.workflow.pipeline.Pipeline, SDK v3 @step decorator, ProcessingStep,
  TrainingStep, TransformStep, ConditionStep, FailStep, ClarifyCheckStep, QualityCheckStep, Data
  Wrangler .flow steps), ModelBuilder local-to-cloud container testing, SageMaker Feature Store
  (CfnFeatureGroup Online InMemory/Standard & Offline Iceberg/Glue stores, PutRecord/GetRecord/
  BatchGetRecord), SageMaker Model Registry (ModelPackageGroup approval gates & EventBridge CI/CD
  promotion), SageMaker Managed MLflow integration, and SageMaker Unified Studio Catalog governance.
  Use when building ML pipelines, feature stores, model registries, or CI/CD workflows.
metadata:
  version: "1.0.0"
---

# SageMaker MLOps, Pipelines, Feature Store & Model Registry Architect

Automates reproducible ML workflows from feature ingestion and experiment tracking through conditional quality gates and cross-environment deployment.

## When to Activate

- User wants to build or debug a **SageMaker Pipeline (`sagemaker.workflow.pipeline.Pipeline`)** using the SDK v3 `@step` decorator or classic step primitives (`ProcessingStep`, `TrainingStep`, `ConditionStep`, `FailStep`)
- User needs a **SageMaker Feature Store (`FeatureGroup` / `CfnFeatureGroup`)** with low-latency Online retrieval (`Standard` or `InMemory`) and Offline Apache Iceberg / Glue tables for point-in-time training joins
- User wants to register models in **SageMaker Model Registry (`ModelPackageGroup`)** with approval gates (`PendingManualApproval` → `Approved`) and EventBridge-triggered CI/CD pipelines (GitHub Actions / CodePipeline)
- User wants to package and test inference containers locally before cloud deployment using **`ModelBuilder`** (`Mode.LOCAL_CONTAINER` → `Mode.SAGEMAKER_ENDPOINT`)
- User wants to integrate **SageMaker Managed MLflow Apps** (coordinate with `manage-mlflow`) or audit **SageMaker Unified Studio Catalog** assets (coordinate with `querying-aws-sagemaker-catalog`)

---

## Core Capabilities & Workflow

### 1. SageMaker Pipelines (`@step` Decorator & Conditional Quality Gates)

Every production SageMaker Pipeline should include:

1. **Parameterized Inputs (`ParameterString`, `ParameterFloat`, `ParameterInteger`)**: Never hardcode S3 dataset URIs, instance counts, or accuracy thresholds inside pipeline definitions.
2. **Data Processing / Feature Engineering Step (`@step` or `ProcessingStep`)**: Validates schema, splits train/val/test, and optionally runs Data Wrangler `.flow` or Spark processing.
3. **Training Step (`@step` or `TrainingStep`)**: Logs metrics and parameters to **SageMaker Managed MLflow** (`MLFLOW_TRACKING_URI` resolved via `manage-mlflow`).
4. **Evaluation Step (`@step` or `ProcessingStep`)**: Computes quantitative metrics (`accuracy`, `f1`, `auc`, `rmse`, or LLM-as-a-Judge scores) and writes `evaluation.json`.
5. **Conditional Registration Gate (`ConditionStep` + `JsonGet` / `@step` condition)**:
   - **If metrics ≥ threshold**: Register the model in **SageMaker Model Registry (`ModelPackageGroup`)** with `ModelMetrics` attached and `ModelApprovalStatus="PendingManualApproval"`.
   - **If metrics < threshold**: Route to `FailStep` with a descriptive failure message so bad models never reach staging/production.
6. **Step Caching (`CacheConfig(enable_caching=True, expire_after="P30D")`)**: Avoid re-running expensive preprocessing or training steps when inputs and code are unchanged.

---

### 2. SageMaker Feature Store (`OnlineStore` + `OfflineStore` Iceberg)

| Tier | Storage Mode | Latency / Use Case |
|---|---|---|
| **Online Store (`Standard`)** | DynamoDB-backed managed key-value store | Single-digit millisecond `GetRecord` / `BatchGetRecord` lookup during real-time inference |
| **Online Store (`InMemory`)** | ElastiCache-backed in-memory tier | Sub-millisecond ultra-high-throughput real-time feature lookup; configure `TtlDuration` to bound memory cost |
| **Offline Store (`Iceberg`)** | S3 + Glue Data Catalog in `Iceberg` table format | Point-in-time accurate (`EventTime`) historical joins via Athena/Spark for training dataset generation and time-travel |

---

### 3. Local-to-Cloud Container Verification via `ModelBuilder`

Before deploying custom inference code to a cloud GPU endpoint (which takes 5–10 minutes to provision), use `sagemaker.serve.builder.model_builder.ModelBuilder` with `mode=Mode.LOCAL_CONTAINER` and a `SchemaBuilder(sample_input, sample_output)` to validate serialization and container health locally, then switch to `mode=Mode.SAGEMAKER_ENDPOINT`.

---

### 4. Event-Driven CI/CD Promotion & Catalog Governance

- **Model Approval Promotion**: Configure an Amazon EventBridge rule matching `source: ["aws.sagemaker"]`, `detail-type: ["SageMaker Model Package State Change"]`, and `detail.ModelApprovalStatus: ["Approved"]` to trigger a deployment pipeline (CodePipeline, Step Functions, or GitHub Actions via OIDC).
- **Experiment Tracking & Catalog Governance**:
  - Use **`manage-mlflow`** to provision or discover Serverless Managed MLflow Apps (`CreateMlflowApp`).
  - Use **`querying-aws-sagemaker-catalog`** to run SQL governance and ownership audits over SageMaker Unified Studio Catalog Iceberg tables (`s3tablescatalog/aws-sagemaker-catalog`.`asset_metadata`.`asset`).

Read `references/pipelines-featurestore-mlflow-catalog.md` for complete production code templates.

## References

- `references/pipelines-featurestore-mlflow-catalog.md` — Complete Python SDK v3 `@step` Pipeline DAG with MLflow tracking and Model Registry gate, `ModelBuilder` local-to-cloud workflow, `CfnFeatureGroup` (`InMemory`/`Standard` + `Iceberg`) setup & `GetRecord`/`PutRecord` client code, and EventBridge Model Registry CI/CD rule.
