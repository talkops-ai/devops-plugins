# Production SageMaker Pipelines, Feature Store & Model Registry Code Patterns

## 1. SageMaker Pipeline with SDK v3 `@step` Decorator, MLflow Tracking & Model Registry Gate

```python
import os
import json
import boto3
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.function_step import step
from sagemaker.workflow.parameters import ParameterString, ParameterFloat
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.fail_step import FailStep

ROLE_ARN = os.environ["SAGEMAKER_ROLE_ARN"]
BUCKET = os.environ["SAGEMAKER_ARTIFACT_BUCKET"]
MLFLOW_ARN = os.environ.get("MLFLOW_TRACKING_URI", "")
MODEL_PACKAGE_GROUP = "churn-prediction-models"

input_data_uri = ParameterString(name="InputDataUri", default_value=f"s3://{BUCKET}/raw/churn.parquet")
f1_threshold = ParameterFloat(name="MinF1Threshold", default_value=0.82)

@step(
    name="PreprocessFeatures",
    instance_type="ml.m5.xlarge",
    role=ROLE_ARN,
    keep_alive_period_in_seconds=600,
)
def preprocess(raw_s3_uri: str) -> dict:
    # Perform feature cleaning and train/test split
    return {
        "train_uri": f"s3://{BUCKET}/curated/train.parquet",
        "test_uri": f"s3://{BUCKET}/curated/test.parquet",
    }

@step(
    name="TrainModel",
    instance_type="ml.g5.2xlarge",
    role=ROLE_ARN,
    use_spot_instances=True,
    max_run=3600,
    max_wait=7200,
    environment={"MLFLOW_TRACKING_URI": MLFLOW_ARN},
)
def train(splits: dict) -> str:
    import mlflow
    if os.environ.get("MLFLOW_TRACKING_URI"):
        mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
        mlflow.set_experiment("churn-pipeline-exp")
        with mlflow.start_run():
            mlflow.log_param("train_uri", splits["train_uri"])
            mlflow.log_metric("val_f1", 0.86)
    return f"s3://{BUCKET}/models/churn-v1/model.tar.gz"

@step(
    name="EvaluateModel",
    instance_type="ml.m5.xlarge",
    role=ROLE_ARN,
)
def evaluate(model_artifact_uri: str, splits: dict) -> dict:
    # Compute holdout evaluation metrics
    return {"f1_score": 0.86, "roc_auc": 0.91, "model_uri": model_artifact_uri}

@step(
    name="RegisterApprovedCandidate",
    instance_type="ml.m5.large",
    role=ROLE_ARN,
)
def register_model(eval_result: dict, model_uri: str) -> str:
    sm = boto3.client("sagemaker")
    sm.create_model_package_group(
        ModelPackageGroupName=MODEL_PACKAGE_GROUP,
        ModelPackageGroupDescription="Production Churn Models",
    ) if MODEL_PACKAGE_GROUP not in [
        g["ModelPackageGroupName"]
        for g in sm.list_model_package_groups(NameContains=MODEL_PACKAGE_GROUP)["ModelPackageGroupSummaryList"]
    ] else None

    resp = sm.create_model_package(
        ModelPackageGroupName=MODEL_PACKAGE_GROUP,
        ModelPackageDescription=f"Pipeline candidate F1={eval_result['f1_score']}",
        ModelApprovalStatus="PendingManualApproval",
        InferenceSpecification={
            "Containers": [
                {
                    "Image": os.environ["INFERENCE_IMAGE_URI"],
                    "ModelDataUrl": model_uri,
                }
            ],
            "SupportedContentTypes": ["application/json", "text/csv"],
            "SupportedResponseMIMETypes": ["application/json"],
        },
        CustomerMetadataProperties={
            "f1_score": str(eval_result["f1_score"]),
            "roc_auc": str(eval_result["roc_auc"]),
        },
    )
    return resp["ModelPackageArn"]

# Assemble DAG
splits_out = preprocess(input_data_uri)
model_uri_out = train(splits_out)
eval_out = evaluate(model_uri_out, splits_out)

cond_step = ConditionStep(
    name="CheckF1QualityGate",
    conditions=[
        ConditionGreaterThanOrEqualTo(
            left=eval_out["f1_score"],
            right=f1_threshold,
        )
    ],
    if_steps=[register_model(eval_out, model_uri_out)],
    else_steps=[
        FailStep(
            name="FailBelowF1Threshold",
            error_message="Model F1 score fell below minimum production threshold.",
        )
    ],
)

pipeline = Pipeline(
    name="ChurnEndToEndMLOpsPipeline",
    parameters=[input_data_uri, f1_threshold],
    steps=[cond_step],
)
```

---

## 2. `ModelBuilder` Local-to-Cloud Container Packaging

Test inference serialization inside a local Docker container before waiting on cloud endpoint creation:

```python
import numpy as np
from sagemaker.serve.builder.model_builder import ModelBuilder
from sagemaker.serve.builder.schema_builder import SchemaBuilder
from sagemaker.serve.mode.function_pointers import Mode

schema_builder = SchemaBuilder(
    sample_input={"inputs": "Analyze customer sentiment: Great service!"},
    sample_output=[{"label": "POSITIVE", "score": 0.99}],
)

model_builder = ModelBuilder(
    model_path="/tmp/local-model-artifacts",
    schema_builder=schema_builder,
    role_arn=ROLE_ARN,
    mode=Mode.LOCAL_CONTAINER,  # Step 1: Test locally in Docker!
)
local_model = model_builder.build()
local_endpoint = local_model.deploy()
print("Local test prediction:", local_endpoint.invoke({"inputs": "Fast delivery!"}))

# Step 2: Promote identical artifact to SageMaker Real-Time Endpoint
model_builder.mode = Mode.SAGEMAKER_ENDPOINT
cloud_model = model_builder.build()
cloud_endpoint = cloud_model.deploy(instance_type="ml.g5.2xlarge", initial_instance_count=1)
```

---

## 3. SageMaker Feature Store (`OnlineStore` + `OfflineStore` Apache Iceberg)

```python
import time
import boto3

sm = boto3.client("sagemaker")
fs_runtime = boto3.client("sagemaker-featurestore-runtime")

# 1. Create FeatureGroup with Online Store (Standard or InMemory) + Offline Iceberg Store
sm.create_feature_group(
    FeatureGroupName="customer-realtime-features-v1",
    RecordIdentifierFeatureName="customer_id",
    EventTimeFeatureName="event_time",
    FeatureDefinitions=[
        {"FeatureName": "customer_id", "FeatureType": "String"},
        {"FeatureName": "event_time", "FeatureType": "Fractional"},
        {"FeatureName": "txn_count_24h", "FeatureType": "Integral"},
        {"FeatureName": "avg_ticket_30d", "FeatureType": "Fractional"},
    ],
    OnlineStoreConfig={
        "EnableOnlineStore": True,
        "StorageType": "Standard",  # Or "InMemory" for sub-millisecond high-QPS serving
        "SecurityConfig": {"KmsKeyId": KMS_KEY_ARN},
        "TtlDuration": {"Unit": "Days", "Value": 90},
    },
    OfflineStoreConfig={
        "S3StorageConfig": {
            "S3Uri": f"s3://{BUCKET}/feature-store/offline/",
            "KmsKeyId": KMS_KEY_ARN,
        },
        "TableFormat": "Iceberg",  # Enables ACID transactions & Athena time-travel!
    },
    RoleArn=ROLE_ARN,
)

# 2. Real-Time Feature Ingestion (PutRecord)
fs_runtime.put_record(
    FeatureGroupName="customer-realtime-features-v1",
    Record=[
        {"FeatureName": "customer_id", "ValueAsString": "cust_9812"},
        {"FeatureName": "event_time", "ValueAsString": str(time.time())},
        {"FeatureName": "txn_count_24h", "ValueAsString": "7"},
        {"FeatureName": "avg_ticket_30d", "ValueAsString": "142.50"},
    ],
)

# 3. Low-Latency Online Feature Retrieval during Inference (GetRecord / BatchGetRecord)
online_rec = fs_runtime.get_record(
    FeatureGroupName="customer-realtime-features-v1",
    RecordIdentifierValueAsString="cust_9812",
    FeatureNames=["txn_count_24h", "avg_ticket_30d"],
)
```

---

## 4. EventBridge Rule for Automated Model Registry Approval Promotion

```json
{
  "source": ["aws.sagemaker"],
  "detail-type": ["SageMaker Model Package State Change"],
  "detail": {
    "ModelPackageGroupName": ["churn-prediction-models"],
    "ModelApprovalStatus": ["Approved"]
  }
}
```
