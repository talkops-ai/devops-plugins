# Production Inference Architecture Code Patterns

## 1. Real-Time Endpoint with `InferenceComponent` Bin-Packing, `LEAST_OUTSTANDING_REQUESTS` & Scale-to-Zero (`MinCapacity=0`)

This pattern packs multiple models onto a shared multi-GPU endpoint (`ml.g5.12xlarge` = 4× A10G GPUs or `ml.g6e.12xlarge` = 4× L40S GPUs) and scales individual components (and underlying instances) down to **0** during idle periods.

```python
import json
import boto3

sm = boto3.client("sagemaker")
sm_runtime = boto3.client("sagemaker-runtime")
aas = boto3.client("application-autoscaling")
cw = boto3.client("cloudwatch")

ENDPOINT_CONFIG_NAME = "packed-llm-ic-epc-001"
ENDPOINT_NAME = "packed-llm-ic-ep-001"
IC_NAME = "qwen3-8b-finance-ic"

# 1. Create EndpointConfig with Managed Instance Scaling & LEAST_OUTSTANDING_REQUESTS
# Notice: No ModelName in ProductionVariants — models are attached as InferenceComponents!
sm.create_endpoint_config(
    EndpointConfigName=ENDPOINT_CONFIG_NAME,
    ExecutionRoleArn=ROLE_ARN,
    KmsKeyId=KMS_KEY_ARN,
    RoutingConfig={"RoutingStrategy": "LEAST_OUTSTANDING_REQUESTS"},
    ProductionVariants=[
        {
            "VariantName": "AllTraffic",
            "InstanceType": "ml.g5.12xlarge",  # 4x A10G GPUs (96 GB total VRAM), 48 vCPUs, 192 GB RAM
            "InitialInstanceCount": 1,
            "ManagedInstanceScaling": {
                "Status": "ENABLED",
                "MinInstanceCount": 0,  # Scales underlying instances to 0 when all ICs have 0 copies!
                "MaxInstanceCount": 4,
            },
            "RoutingConfig": {"RoutingStrategy": "LEAST_OUTSTANDING_REQUESTS"},
        }
    ],
)

# 2. Create the Shared Endpoint
sm.create_endpoint(
    EndpointName=ENDPOINT_NAME,
    EndpointConfigName=ENDPOINT_CONFIG_NAME,
)
sm.get_waiter("endpoint_in_service").wait(EndpointName=ENDPOINT_NAME)

# 3. Create an InferenceComponent with Fractional Hardware Requirements (1 GPU, 8 vCPUs, 32 GB RAM)
sm.create_inference_component(
    InferenceComponentName=IC_NAME,
    EndpointName=ENDPOINT_NAME,
    VariantName="AllTraffic",
    Specification={
        "Container": {
            "Image": f"763104351884.dkr.ecr.{REGION}.amazonaws.com/djl-inference:0.31.0-lmi13.0.0-cu124",
            "ArtifactUrl": f"s3://{BUCKET}/models/qwen3-8b-finance/model.tar.gz",
            "Environment": {
                "HF_MODEL_ID": "/opt/ml/model",
                "OPTION_ROLLING_BATCH": "vllm",
                "OPTION_TENSOR_PARALLEL_DEGREE": "1",
                "OPTION_MAX_MODEL_LEN": "8192",
                "OPTION_MAX_ROLLING_BATCH_SIZE": "32",
            },
        },
        "ComputeResourceRequirements": {
            "NumberOfAcceleratorDevicesRequired": 1.0,  # Uses 1 of the 4 GPUs on ml.g5.12xlarge
            "NumberOfCpuCoresRequired": 8.0,
            "MinMemoryRequiredInMb": 32768,
        },
    },
    RuntimeConfig={"CopyCount": 1},
)

# 4. Configure Scale-to-Zero (MinCapacity=0) + Step-Scaling Wakeup from 0 -> 1 Copy
resource_id = f"inference-component/{IC_NAME}"

aas.register_scalable_target(
    ServiceNamespace="sagemaker",
    ResourceId=resource_id,
    ScalableDimension="sagemaker:inference-component:DesiredCopyCount",
    MinCapacity=0,
    MaxCapacity=4,
)

# 4a. Target Tracking Policy (scales 1 <-> 4 and scales down to 0 after idle cooldown)
aas.put_scaling_policy(
    PolicyName=f"{IC_NAME}-target-tracking",
    ServiceNamespace="sagemaker",
    ResourceId=resource_id,
    ScalableDimension="sagemaker:inference-component:DesiredCopyCount",
    PolicyType="TargetTrackingScaling",
    TargetTrackingScalingPolicyConfiguration={
        "TargetValue": 5.0,
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "SageMakerVariantInvocationsPerCopy",
        },
        "ScaleOutCooldown": 60,
        "ScaleInCooldown": 600,  # Scale to 0 after 10 minutes of zero traffic
    },
)

# 4b. Step-Scaling Wakeup Policy + CloudWatch Alarm on NoCapacityInvocationFailures (0 -> 1 copy)
wakeup_resp = aas.put_scaling_policy(
    PolicyName=f"{IC_NAME}-wakeup-from-zero",
    ServiceNamespace="sagemaker",
    ResourceId=resource_id,
    ScalableDimension="sagemaker:inference-component:DesiredCopyCount",
    PolicyType="StepScaling",
    StepScalingPolicyConfiguration={
        "AdjustmentType": "ExactCapacity",
        "Cooldown": 60,
        "MetricAggregationType": "Maximum",
        "StepAdjustments": [
            {"MetricIntervalLowerBound": 0.0, "ScalingAdjustment": 1}
        ],
    },
)

cw.put_metric_alarm(
    AlarmName=f"{IC_NAME}-NoCapacityWakeupAlarm",
    Namespace="AWS/SageMaker",
    MetricName="NoCapacityInvocationFailures",
    Dimensions=[{"Name": "InferenceComponentName", "Value": IC_NAME}],
    Statistic="Sum",
    Period=60,
    EvaluationPeriods=1,
    Threshold=1.0,
    ComparisonOperator="GreaterThanOrEqualToThreshold",
    AlarmActions=[wakeup_resp["PolicyARN"]],
)

# 5. Invoke the Specific InferenceComponent (Streaming or Synchronous)
resp = sm_runtime.invoke_endpoint(
    EndpointName=ENDPOINT_NAME,
    InferenceComponentName=IC_NAME,
    ContentType="application/json",
    Body=json.dumps({"inputs": "Summarize Q3 operating margin drivers:", "parameters": {"max_new_tokens": 256}}),
)
print(json.loads(resp["Body"].read()))
```

---

## 2. AWS Inferentia2 (`ml.inf2`) Neuron LLM Serving via DJL Neuronx

Deploying open-weight LLMs (Llama, Mistral, Qwen) on `ml.inf2.8xlarge` / `ml.inf2.24xlarge` delivers up to 50% lower cost per token than comparable GPUs:

```python
sm.create_model(
    ModelName="llama3-8b-neuronx-model",
    ExecutionRoleArn=ROLE_ARN,
    PrimaryContainer={
        "Image": f"763104351884.dkr.ecr.{REGION}.amazonaws.com/djl-inference:0.31.0-neuronx-sdk2.21.0",
        "ModelDataUrl": f"s3://{BUCKET}/models/llama3-8b/",
        "Environment": {
            "OPTION_ENTRY_POINT": "djl_python.transformers_neuronx",
            "OPTION_TENSOR_PARALLEL_DEGREE": "2",  # 2 NeuronCores on ml.inf2.xlarge
            "OPTION_N_POSITIONS": "4096",
            "OPTION_ROLLING_BATCH": "auto",
            "OPTION_MAX_ROLLING_BATCH_SIZE": "8",
            "OPTION_DTYPE": "fp16",
        },
    },
)
```

---

## 3. Asynchronous Inference (Up to 1 GB Payload, 1-Hour Timeout & Scale-to-Zero)

Ideal for high-resolution computer vision (e.g., `Segment Anything` whole-slide/satellite imagery), large document extraction, or long-running reasoning tasks:

```python
sm.create_endpoint_config(
    EndpointConfigName="sam-async-epc-001",
    KmsKeyId=KMS_KEY_ARN,
    ProductionVariants=[
        {
            "VariantName": "AllTraffic",
            "ModelName": "sam-vit-large-custom-model",
            "InstanceType": "ml.g5.2xlarge",
            "InitialInstanceCount": 1,
        }
    ],
    AsyncInferenceConfig={
        "ClientConfig": {
            "MaxConcurrentInvocationsPerInstance": 4,
        },
        "OutputConfig": {
            "S3OutputPath": f"s3://{BUCKET}/async-inference/output/",
            "S3FailurePath": f"s3://{BUCKET}/async-inference/failures/",
            "KmsKeyId": KMS_KEY_ARN,
            "NotificationConfig": {
                "SuccessTopic": SNS_SUCCESS_TOPIC_ARN,
                "ErrorTopic": SNS_ERROR_TOPIC_ARN,
                "IncludeInferenceResponseIn": ["SUCCESS_NOTIFICATION_TOPIC", "ERROR_NOTIFICATION_TOPIC"],
            },
        },
    },
)

# Invoke asynchronously with an S3 input pointer (supports payloads up to 1 GB!)
async_resp = sm_runtime.invoke_endpoint_async(
    EndpointName="sam-async-ep-001",
    InputLocation=f"s3://{BUCKET}/async-inference/inputs/high_res_tile_001.json",
    ContentType="application/json",
    InvocationTimeoutSeconds=3600,  # Up to 1 hour
)
print("Queued output location:", async_resp["OutputLocation"])
```

---

## 4. Multi-Container Endpoints (Serial Pipeline vs Direct Invocation) & Multi-Model Endpoints (MME)

- **Multi-Container Serial Pipeline (`Mode: "Serial"`)**:
  ```python
  sm.create_model(
      ModelName="serial-preprocess-predict-model",
      ExecutionRoleArn=ROLE_ARN,
      Containers=[
          {"ContainerHostname": "preprocess", "Image": SKLEARN_IMAGE, "ModelDataUrl": S3_PREPROC_URI},
          {"ContainerHostname": "xgboost", "Image": XGBOOST_IMAGE, "ModelDataUrl": S3_XGB_URI},
      ],
      InferenceExecutionConfig={"Mode": "Serial"},
  )
  ```
- **Multi-Container Direct (`Mode: "Direct"`)**: Set `InferenceExecutionConfig={"Mode": "Direct"}` and pass `TargetContainerHostname="xgboost"` in `invoke_endpoint`.
- **Multi-Model Endpoint (`Mode: "MultiModel"`)**: Set `PrimaryContainer={"Image": IMAGE, "ModelDataUrl": f"s3://{BUCKET}/mme-models/", "Mode": "MultiModel"}` and pass `TargetModel="tenant_042_model.tar.gz"` in `invoke_endpoint`.

---

## 5. Serverless Inference & Batch Transform

- **Serverless Inference**:
  ```python
  sm.create_endpoint_config(
      EndpointConfigName="tabular-serverless-epc",
      ProductionVariants=[
          {
              "VariantName": "AllTraffic",
              "ModelName": "xgboost-churn-model",
              "ServerlessConfig": {
                  "MemorySizeInMB": 4096,      # 1024, 2048, 3072, 4096, 5120, or 6144 MB
                  "MaxConcurrency": 50,
                  "ProvisionedConcurrency": 2, # Optional warm capacity
              },
          }
      ],
  )
  ```
- **Batch Transform (Offline Bulk Scoring)**:
  ```python
  sm.create_transform_job(
      TransformJobName="nightly-churn-scoring-20261015",
      ModelName="xgboost-churn-model",
      MaxConcurrentTransforms=16,
      MaxPayloadInMB=10,
      BatchStrategy="MultiRecord",
      TransformInput={
          "DataSource": {"S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": f"s3://{BUCKET}/batch/input/"}},
          "ContentType": "text/csv",
          "SplitType": "Line",
      },
      TransformOutput={
          "S3OutputPath": f"s3://{BUCKET}/batch/output/",
          "AssembleWith": "Line",
          "Accept": "text/csv",
          "KmsKeyId": KMS_KEY_ARN,
      },
      DataProcessing={"InputFilter": "$[1:]", "JoinSource": "Input", "OutputFilter": "$[0,-1]"},
      TransformResources={"InstanceType": "ml.m5.2xlarge", "InstanceCount": 2},
  )
  ```

---

## 6. Amazon Bedrock Custom Model Import (`CreateModelImportJob`)

When deploying custom Full Fine-Tuned (FFT) or HuggingFace safetensors weights (< 200 GB) in supported regions (`us-east-1`, `us-east-2`, `us-west-2`, `eu-central-1`) for serverless Bedrock invocation:

```python
bedrock = boto3.client("bedrock", region_name=REGION)

resp = bedrock.create_model_import_job(
    jobName="import-qwen3-custom-fft-001",
    importedModelName="qwen3-custom-fft-prod",
    roleArn=ROLE_ARN,
    modelDataSource={"s3DataSource": {"s3Uri": f"s3://{BUCKET}/hf-weights/qwen3-custom-fft/"}},
    importedModelKmsKeyId=KMS_KEY_ARN,
    vpcConfig={"subnetIds": SUBNET_IDS, "securityGroupIds": [SECURITY_GROUP_ID]},
)
```
