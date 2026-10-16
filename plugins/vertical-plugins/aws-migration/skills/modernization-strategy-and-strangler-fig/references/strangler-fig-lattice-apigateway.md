# Strangler Fig Routing Architecture: API Gateway, SigV4 Lambda, VPC Lattice & AWS RAM

## 1. Architectural Guardrail & Background

> **2026 Mandate**: AWS Migration Hub Refactor Spaces is closed to new customers since November 7, 2025.
> All new incremental traffic migration architectures must use **Amazon API Gateway Canary Deployments** paired with **Amazon VPC Lattice Service Networks** shared across AWS accounts using **AWS Resource Access Manager (AWS RAM)**.

---

## 2. Multi-Account End-to-End Traffic Architecture

```
+-----------------------------------------------------------------------------------------+
| AWS Account: Edge / API Gateway (Account A - Ingress Account)                           |
|                                                                                         |
|   Client Request --> [ Amazon API Gateway REST API ]                                    |
|                             |                                                           |
|             Stage: "prod" (Deployment Canary: 10% weight)                               |
|                            /                           \                                |
|          Default (90%)    /                             \   Canary (10%)                |
|                          v                               v                              |
|           +-------------------------------+   +------------------------------------+    |
|           | Legacy Integration            |   | Forwarder Lambda                   |    |
|           | (HTTP Proxy to On-Prem / EC2) |   | (VPC-attached, SigV4 IAM Signer)   |    |
|           +-------------------------------+   +------------------------------------+    |
|                          |                                       |                      |
+--------------------------|---------------------------------------|----------------------+
                           |                                       | (HTTPS / SigV4)
                           v                                       v
        [ On-Prem / Legacy Datacenter ]         +-----------------------------------------+
                                                | Amazon VPC Lattice Service Network      |
                                                | (Shared across Org via AWS RAM)         |
                                                +-----------------------------------------+
                                                                   |
                                    +------------------------------+----------------------+
                                    |                                                     |
                                    v                                                     v
+-------------------------------------------------------+ +-------------------------------------------------------+
| AWS Account: Workload Account B (Service A)           | | AWS Account: Workload Account C (Service B)           |
|                                                       | |                                                       |
|   VPC Lattice Service Association:                    | |   VPC Lattice Service Association:                    |
|   "orders-service.lattice.internal"                   | |   "customers-service.lattice.internal"                |
|                      |                                | |                      |                                |
|                      v                                | |                      v                                |
|   Target Group: ECS Fargate Task / Lambda Function    | |   Target Group: EKS Service / ECS Fargate Task        |
+-------------------------------------------------------+ +-------------------------------------------------------+
```

---

## 3. Step-by-Step Implementation Guide

### Step 1: Create Amazon VPC Lattice Service Network & Share via AWS RAM

In the centralized networking or shared services account:

```bash
# 1. Create the VPC Lattice Service Network with AWS_IAM auth type
aws vpc-lattice create-service-network \
  --name "enterprise-modernization-network" \
  --auth-type "AWS_IAM"

# 2. Extract the Service Network ARN
SERVICE_NETWORK_ARN=$(aws vpc-lattice list-service-networks \
  --query "items[?name=='enterprise-modernization-network'].arn" --output text)

# 3. Share the Service Network across AWS Organizations using AWS RAM
aws ram create-resource-share \
  --name "lattice-modernization-share" \
  --resource-arns "${SERVICE_NETWORK_ARN}" \
  --principals "arn:aws:organizations::123456789012:organization/o-exampleorgid" \
  --permission-arns "arn:aws:ram::aws:permission/AWSRAMPermissionVpcLatticeServiceNetwork"
```

### Step 2: Register Microservices into the Lattice Service Network

In the microservice workload account (Account B):

```bash
# 1. Create a VPC Lattice Target Group targeting the new ECS Fargate IP targets or Lambda
aws vpc-lattice create-target-group \
  --name "orders-service-tg" \
  --type "IP" \
  --config '{
    "port": 8080,
    "protocol": "HTTP",
    "vpcIdentifier": "vpc-0123456789abcdef0",
    "ipAddressType": "IPV4"
  }'

# 2. Create the Lattice Service
aws vpc-lattice create-service \
  --name "orders-microservice" \
  --auth-type "AWS_IAM"

# 3. Associate the Target Group to the Service listener rule
aws vpc-lattice create-listener \
  --service-identifier "orders-microservice" \
  --name "http-listener" \
  --protocol "HTTP" \
  --port 80 \
  --default-action '{"forward": {"targetGroups": [{"targetGroupIdentifier": "orders-service-tg"}]}}'

# 4. Associate the Service to the shared Service Network
aws vpc-lattice create-service-network-service-association \
  --service-network-identifier "${SERVICE_NETWORK_ARN}" \
  --service-identifier "orders-microservice"
```

### Step 3: Deploy the VPC-Attached Forwarder Lambda with SigV4 Signing

The forwarder Lambda sits in the ingress account VPC, receives canary traffic from API Gateway, signs the request with SigV4 using the Lambda execution role's IAM credentials, and delivers it to the VPC Lattice service DNS.

```python
# forwarder_lambda.py
import os
import json
import urllib3
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

session = boto3.Session()
credentials = session.get_credentials().get_frozen_credentials()
region = os.environ.get("AWS_REGION", "us-east-1")
service_name = "vpc-lattice-svcs"
target_lattice_dns = os.environ["TARGET_LATTICE_DNS"] # e.g. orders-microservice-0abc123.7sk9.vpc-lattice-svcs.us-east-1.on.aws
http = urllib3.PoolManager()

def lambda_handler(event, context):
    method = event.get("httpMethod", "GET")
    path = event.get("path", "/")
    headers = event.get("headers", {}) or {}
    query_params = event.get("queryStringParameters", {}) or {}
    body = event.get("body", "")

    url = f"https://{target_lattice_dns}{path}"
    
    # Strip host header before SigV4 signing
    headers.pop("Host", None)
    headers.pop("host", None)
    
    request = AWSRequest(method=method, url=url, data=body, headers=headers, params=query_params)
    SigV4Auth(credentials, service_name, region).add_auth(request)

    response = http.request(
        method=method,
        url=request.url,
        headers=dict(request.headers),
        body=body.encode("utf-8") if isinstance(body, str) else body,
        retries=False
    )

    return {
        "statusCode": response.status,
        "headers": dict(response.headers),
        "body": response.data.decode("utf-8")
    }
```

### Step 4: Configure API Gateway Canary & CloudWatch Alarm Rollback

```bash
# 1. Enable Canary on the API Gateway Stage with 10% initial weight
aws apigateway update-stage \
  --rest-api-id "api-id-12345" \
  --stage-name "prod" \
  --patch-operations \
    op=replace,path=/canarySettings/percentTraffic,value=10.0 \
    op=replace,path=/canarySettings/useStageCache,value=false

# 2. Create CloudWatch Alarms for Canary 5XX Errors
aws cloudwatch put-metric-alarm \
  --alarm-name "orders-api-canary-5xx-rollback" \
  --metric-name "5XXError" \
  --namespace "AWS/ApiGateway" \
  --statistic "Sum" \
  --period 60 \
  --threshold 5 \
  --comparison-operator "GreaterThanOrEqualToThreshold" \
  --evaluation-periods 2 \
  --dimensions Name=ApiName,Value=enterprise-orders-api Name=Stage,Value=prod \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:canary-rollback-topic"

# 3. Canary Rollback Hook (Executed on Alarm Trigger)
# Immediately resets canary traffic to 0%
aws apigateway update-stage \
  --rest-api-id "api-id-12345" \
  --stage-name "prod" \
  --patch-operations \
    op=replace,path=/canarySettings/percentTraffic,value=0.0
```
