# Production Deployment Guardrails, Shadow Testing, Model Monitor & CloudWatch Forensics

## 1. Blue/Green Canary & Linear Deployment Guardrails with Auto-Rollback Alarms

```python
import boto3

sm = boto3.client("sagemaker")
cw = boto3.client("cloudwatch")

ENDPOINT_NAME = "prod-fraud-scorer-ep"
VARIANT_NAME = "AllTraffic"

# 1. Create CloudWatch Alarms for 5XX Errors & p99 ModelLatency
cw.put_metric_alarm(
    AlarmName=f"{ENDPOINT_NAME}-5xx-rollback-alarm",
    Namespace="AWS/SageMaker",
    MetricName="Invocation5XXErrors",
    Dimensions=[
        {"Name": "EndpointName", "Value": ENDPOINT_NAME},
        {"Name": "VariantName", "Value": VARIANT_NAME},
    ],
    Statistic="Sum",
    Period=60,
    EvaluationPeriods=2,
    Threshold=5.0,
    ComparisonOperator="GreaterThanOrEqualToThreshold",
)

cw.put_metric_alarm(
    AlarmName=f"{ENDPOINT_NAME}-p99-latency-rollback-alarm",
    Namespace="AWS/SageMaker",
    MetricName="ModelLatency",
    Dimensions=[
        {"Name": "EndpointName", "Value": ENDPOINT_NAME},
        {"Name": "VariantName", "Value": VARIANT_NAME},
    ],
    ExtendedStatistic="p99",
    Period=60,
    EvaluationPeriods=3,
    Threshold=250000.0,  # 250 ms in microseconds (ModelLatency is reported in microseconds!)
    ComparisonOperator="GreaterThanThreshold",
)

# 2. Update Endpoint with Blue/Green Linear Traffic Shifting + Auto-Rollback
sm.update_endpoint(
    EndpointName=ENDPOINT_NAME,
    EndpointConfigName="prod-fraud-scorer-epc-v2",
    DeploymentConfig={
        "BlueGreenUpdatePolicy": {
            "TrafficRoutingConfiguration": {
                "Type": "LINEAR",  # Or "CANARY"
                "LinearStepSize": {"Type": "CAPACITY_PERCENT", "Value": 20},
                "WaitIntervalInSeconds": 300,  # 5 minutes per 20% step
            },
            "TerminationWaitInSeconds": 600,  # Keep old blue fleet warm for 10 mins post-cutover
            "MaximumExecutionTimeoutInSeconds": 3600,
        },
        "AutoRollbackConfiguration": {
            "Alarms": [
                {"AlarmName": f"{ENDPOINT_NAME}-5xx-rollback-alarm"},
                {"AlarmName": f"{ENDPOINT_NAME}-p99-latency-rollback-alarm"},
            ]
        },
    },
)
```

---

## 2. Shadow Testing (`ShadowProductionVariants`) + `DataCaptureConfig`

Test a new candidate model (e.g., an `ml.inf2` compiled model or quantized LLM) against live production traffic without affecting caller responses:

```python
sm.create_endpoint_config(
    EndpointConfigName="prod-with-shadow-candidate-epc",
    KmsKeyId=KMS_KEY_ARN,
    ProductionVariants=[
        {
            "VariantName": "PrimaryProdV1",
            "ModelName": "fraud-scorer-v1",
            "InstanceType": "ml.g5.2xlarge",
            "InitialInstanceCount": 2,
            "InitialVariantWeight": 1.0,
        }
    ],
    ShadowProductionVariants=[
        {
            "VariantName": "ShadowCandidateV2Inf2",
            "ModelName": "fraud-scorer-v2-neuron",
            "InstanceType": "ml.inf2.xlarge",
            "InitialInstanceCount": 1,
            "InitialVariantWeight": 0.25,  # Replicate 25% of live traffic to ShadowCandidateV2Inf2
        }
    ],
    DataCaptureConfig={
        "EnableCapture": True,
        "InitialSamplingPercentage": 100,
        "DestinationS3Uri": f"s3://{BUCKET}/data-capture/{ENDPOINT_NAME}/",
        "KmsKeyId": KMS_KEY_ARN,
        "CaptureOptions": [
            {"CaptureMode": "Input"},
            {"CaptureMode": "Output"},
        ],
        "CaptureContentTypeHeader": {
            "CsvContentTypes": ["text/csv"],
            "JsonContentTypes": ["application/json"],
        },
    },
)
```

---

## 3. SageMaker Model Monitor: Scheduled Data Quality & Model Quality Drift Jobs

```python
# 1. Create Data Quality Job Definition
sm.create_data_quality_job_definition(
    JobDefinitionName="fraud-scorer-data-quality-def",
    DataQualityBaselineConfig={
        "ConstraintsResource": {"S3Uri": f"s3://{BUCKET}/baseline/constraints.json"},
        "StatisticsResource": {"S3Uri": f"s3://{BUCKET}/baseline/statistics.json"},
    },
    DataQualityAppSpecification={
        "ImageUri": MODEL_MONITOR_ANALYZER_IMAGE_URI,
    },
    DataQualityJobInput={
        "EndpointInput": {
            "EndpointName": ENDPOINT_NAME,
            "LocalPath": "/opt/ml/processing/input/endpoint",
            "S3DataDistributionType": "FullyReplicated",
            "S3InputMode": "File",
        }
    },
    DataQualityJobOutputConfig={
        "MonitoringOutputs": [
            {
                "S3Output": {
                    "S3Uri": f"s3://{BUCKET}/monitoring/data-quality-reports/",
                    "LocalPath": "/opt/ml/processing/output",
                    "S3UploadMode": "EndOfJob",
                }
            }
        ],
        "KmsKeyId": KMS_KEY_ARN,
    },
    JobResources={
        "ClusterConfig": {
            "InstanceCount": 1,
            "InstanceType": "ml.m5.xlarge",
            "VolumeSizeInGB": 50,
            "VolumeKmsKeyId": KMS_KEY_ARN,
        }
    },
    NetworkConfig={
        "EnableInterContainerTrafficEncryption": True,
        "EnableNetworkIsolation": False,
        "VpcConfig": {"SecurityGroupIds": [SECURITY_GROUP_ID], "Subnets": SUBNET_IDS},
    },
    RoleArn=ROLE_ARN,
)

# 2. Schedule Nightly Drift Check at 20:00 UTC
sm.create_monitoring_schedule(
    MonitoringScheduleName="fraud-scorer-nightly-drift-schedule",
    MonitoringScheduleConfig={
        "ScheduleConfig": {"ScheduleExpression": "cron(0 20 * * ? *)"},
        "MonitoringJobDefinitionName": "fraud-scorer-data-quality-def",
        "MonitoringType": "DataQuality",
    },
)
```

---

## 4. High-Signal CloudWatch Logs Insights Queries (`cloudwatch` MCP Server)

Use `execute_log_insights_query` on the `cloudwatch` MCP server against `/aws/sagemaker/Endpoints/<endpoint-name>` or `/aws/sagemaker/InferenceComponents/<ic-name>`:

```sql
fields @timestamp, @logStream, @message
| filter @message like /(?i)(ERROR|Exception|Traceback|CUDA out of memory|OOM|Killed|Timeout|ModelError|Worker died)/
| sort @timestamp desc
| limit 50
```
