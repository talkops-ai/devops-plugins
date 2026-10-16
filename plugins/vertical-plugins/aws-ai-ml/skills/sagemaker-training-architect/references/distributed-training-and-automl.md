# Production Training, Vision Fine-Tuning, Distributed DDP/FSDP & Autopilot v2 Patterns

## 1. SageMaker Python SDK v3 `@remote` Decorator with Managed Spot & Warm Pools

```python
import os
import torch
from sagemaker.remote_function import remote

@remote(
    instance_type="ml.g5.2xlarge",
    instance_count=1,
    dependencies="./requirements.txt",
    use_spot_instances=True,
    max_run=7200,
    max_wait=14400,
    keep_alive_period_in_seconds=1800,  # Warm pool for 30 mins during iteration
    volume_size=100,
    encrypt_inter_container_traffic=True,
    environment={
        "MLFLOW_TRACKING_URI": os.environ.get("MLFLOW_TRACKING_URI", ""),
    },
)
def train_custom_model(s3_train_uri: str, learning_rate: float = 1e-4, epochs: int = 5):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Running on {device} with BF16 AMP support: {torch.cuda.is_bf16_supported()}")
    # Training logic here...
    return {"status": "completed", "final_val_loss": 0.142}
```

---

## 2. Custom Computer Vision Fine-Tuning: Segment Anything Model (`SAM`) `MaskDecoder` with Spot Checkpointing

When fine-tuning Meta's Segment Anything Model (`facebook/sam-vit-base`, `sam-vit-large`, `sam-vit-huge`) on custom medical, geospatial, or industrial segmentation datasets:

- **Architecture Pattern**: Freeze `vision_encoder` and `prompt_encoder` so only `mask_decoder` (~4M parameters) is updated.
- **Loss Function**: Use `monai.losses.DiceFocalLoss(sigmoid=True, squared_pred=True)` to handle foreground/background class imbalance.
- **Spot Checkpointing**: Resume automatically from `/opt/ml/checkpoint/latest.pt` and save final weights + processor config to `/opt/ml/model`.

```python
# scripts/train_sam_mask_decoder.py
import os
import glob
import torch
from torch.utils.data import DataLoader
from transformers import SamModel, SamProcessor
import monai

CHECKPOINT_DIR = os.environ.get("SM_CHECKPOINT_DIR", "/opt/ml/checkpoint")
MODEL_DIR = os.environ.get("SM_MODEL_DIR", "/opt/ml/model")
TRAIN_DIR = os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train")

def main():
    model_id = os.environ.get("SAM_MODEL_ID", "facebook/sam-vit-base")
    processor = SamProcessor.from_pretrained(model_id)
    model = SamModel.from_pretrained(model_id)

    # 1. Freeze heavy backbone (vision_encoder + prompt_encoder)
    for name, param in model.named_parameters():
        if name.startswith("vision_encoder") or name.startswith("prompt_encoder"):
            param.requires_grad_(False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=1e-5, weight_decay=1e-4)
    seg_loss = monai.losses.DiceFocalLoss(sigmoid=True, squared_pred=True, reduction="mean")

    # 2. Resume from Spot Checkpoint if present
    start_epoch = 0
    ckpt_path = os.path.join(CHECKPOINT_DIR, "latest.pt")
    if os.path.exists(ckpt_path):
        ckpt = torch.load(ckpt_path, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        start_epoch = ckpt["epoch"] + 1
        print(f"Resumed from Spot checkpoint at epoch {start_epoch}")

    # 3. Mixed-Precision (BF16) + Gradient Accumulation Loop
    grad_accum_steps = 4
    num_epochs = int(os.environ.get("EPOCHS", "10"))
    # Assume `train_loader` yields batches with pixel_values, input_boxes, ground_truth_mask
    for epoch in range(start_epoch, num_epochs):
        model.train()
        optimizer.zero_grad()
        # ... iterate over train_loader with torch.amp.autocast("cuda", dtype=torch.bfloat16) ...

        # 4. Save Spot Checkpoint at end of each epoch
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)
        torch.save(
            {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
            },
            ckpt_path,
        )

    # 5. Export fine-tuned model to /opt/ml/model for S3 model.tar.gz packaging
    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save_pretrained(MODEL_DIR)
    processor.save_pretrained(MODEL_DIR)

if __name__ == "__main__":
    main()
```

---

## 3. Multi-Node Distributed Data Parallel (DDP / FSDP) with `CreateTrainingJob`

When launching multi-GPU / multi-node jobs (`ml.g6e.12xlarge`, `ml.p4d.24xlarge`, `ml.trn1.32xlarge`):

```python
import boto3

sm = boto3.client("sagemaker")

response = sm.create_training_job(
    TrainingJobName="custom-ddp-spot-train-001",
    RoleArn=ROLE_ARN,
    AlgorithmSpecification={
        "TrainingImage": f"763104351884.dkr.ecr.{REGION}.amazonaws.com/pytorch-training:2.4.0-gpu-py311-cu124-ubuntu22.04-sagemaker",
        "TrainingInputMode": "FastFile",  # Stream directly from S3 without full pre-download
        "MetricDefinitions": [
            {"Name": "train:loss", "Regex": r"train_loss=([0-9\.]+)"},
            {"Name": "val:loss", "Regex": r"val_loss=([0-9\.]+)"},
        ],
    },
    HyperParameters={
        "sagemaker_program": "train.py",
        "sagemaker_submit_directory": f"s3://{BUCKET}/code/sourcedir.tar.gz",
        "sagemaker_distributed_dataparallel_enabled": "true",
    },
    InputDataConfig=[
        {
            "ChannelName": "train",
            "DataSource": {
                "S3DataSource": {
                    "S3DataType": "S3Prefix",
                    "S3Uri": f"s3://{BUCKET}/datasets/train/",
                    "S3DataDistributionType": "ShardedByS3Key",  # Shard across nodes
                }
            },
            "InputMode": "FastFile",
        }
    ],
    OutputDataConfig={
        "S3OutputPath": f"s3://{BUCKET}/models/",
        "KmsKeyId": KMS_KEY_ARN,
    },
    ResourceConfig={
        "InstanceType": "ml.g6e.12xlarge",
        "InstanceCount": 2,
        "VolumeSizeInGB": 200,
        "VolumeKmsKeyId": KMS_KEY_ARN,
        "KeepAlivePeriodInSeconds": 900,
    },
    VpcConfig={
        "SecurityGroupIds": [SECURITY_GROUP_ID],
        "Subnets": SUBNET_IDS,
    },
    EnableManagedSpotTraining=True,
    StoppingCondition={
        "MaxRuntimeInSeconds": 14400,
        "MaxWaitTimeInSeconds": 28800,
    },
    CheckpointConfig={
        "S3Uri": f"s3://{BUCKET}/checkpoints/custom-ddp-spot-train-001/",
        "LocalPath": "/opt/ml/checkpoint",
    },
    EnableInterContainerTrafficEncryption=True,
)
```

---

## 4. SageMaker Autopilot AutoML API v2 (`CreateAutoMLJobV2`) — Tabular & Time-Series

Use `create_auto_ml_job_v2` for Tabular classification/regression or Time-Series forecasting (with holiday calendars and quantile predictions):

```python
import boto3

sm = boto3.client("sagemaker")

# Time-Series Forecasting with Holiday Calendar & Quantiles
response = sm.create_auto_ml_job_v2(
    AutoMLJobName="demand-forecast-automlv2-001",
    AutoMLJobInputDataConfig=[
        {
            "ChannelType": "training",
            "ContentType": "text/csv;header=present",
            "DataSource": {
                "S3DataSource": {
                    "S3DataType": "S3Prefix",
                    "S3Uri": f"s3://{BUCKET}/timeseries/sales_history.csv",
                }
            },
        }
    ],
    OutputDataConfig={
        "S3OutputPath": f"s3://{BUCKET}/automl-output/",
        "KmsKeyId": KMS_KEY_ARN,
    },
    AutoMLProblemTypeConfig={
        "TimeSeriesForecastingJobConfig": {
            "ForecastFrequency": "D",
            "ForecastHorizon": 14,
            "ForecastQuantiles": ["p10", "p50", "p90"],
            "TimeSeriesConfig": {
                "TargetAttributeName": "demand_units",
                "TimestampAttributeName": "date",
                "ItemIdentifierAttributeName": "store_sku_id",
            },
            "HolidayConfig": [
                {"CountryCode": "US"},
            ],
        }
    },
    RoleArn=ROLE_ARN,
    SecurityConfig={
        "VolumeKmsKeyId": KMS_KEY_ARN,
        "EnableInterContainerTrafficEncryption": True,
        "VpcConfig": {
            "SecurityGroupIds": [SECURITY_GROUP_ID],
            "Subnets": SUBNET_IDS,
        },
    },
)
```
