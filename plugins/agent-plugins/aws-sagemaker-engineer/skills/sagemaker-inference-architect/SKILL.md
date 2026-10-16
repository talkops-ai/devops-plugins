---
name: sagemaker-inference-architect
description: >-
  Architects and generates production inference and model-hosting solutions across all Amazon
  SageMaker AI deployment patterns. Covers Real-Time Endpoints with SageMaker Inference Components
  (CreateInferenceComponent fractional GPU/CPU/RAM bin-packing, CopyCount, RoutingConfig
  LEAST_OUTSTANDING_REQUESTS, and Managed Instance Auto Scaling with Scale-to-Zero MinCapacity=0),
  DJL Serving / LMI (vLLM, TensorRT-LLM, multi-adapter LoRA), AWS Inferentia2 (ml.inf2) Neuron
  compilation, Multi-Container Endpoints (Serial Inference Pipelines & Direct invocation),
  Multi-Model Endpoints (MME), Serverless Inference, Asynchronous Inference (up to 1 GB payload &
  1-hr timeout with S3 queues), Batch Transform, Bedrock Custom Model Import (CreateModelImportJob),
  and SageMaker Inference Recommender load testing. Use whenever deploying custom models, FFT
  weights, or production multi-model endpoints.
metadata:
  version: "1.0.0"
---

# SageMaker Production Inference & Hosting Architect

Designs and generates production-ready code and IaC for every Amazon SageMaker AI hosting topology, optimizing GPU utilization, tail latency (p99), and monthly hosting TCO.

## When to Activate

- User wants to deploy **multiple models or fine-tuned adapters** onto shared GPU instances using **SageMaker Inference Components (`InferenceComponent`)** with **Scale-to-Zero (`MinCapacity=0`)**
- User is deploying **Full Fine-Tuned (FFT)** weights, custom `Estimator` / `@remote` `model.tar.gz` artifacts, HuggingFace safetensors, PyTorch, XGBoost, ONNX, or custom Docker inference containers
- User needs **Serverless Inference**, **Asynchronous Inference** (large payloads up to 1 GB / long timeouts up to 1 hour), **Batch Transform**, **Multi-Container Endpoints (MCE)**, or **Multi-Model Endpoints (MME)**
- User wants to compile and serve models on **AWS Inferentia2 (`ml.inf2`)** or import custom weights into **Amazon Bedrock Custom Model Import (`CreateModelImportJob`)**
- User wants to right-size instances using **SageMaker Inference Recommender (`CreateInferenceRecommendationsJob`)**

*(Note: For simple LoRA fine-tuned models from Serverless Model Customization or single JumpStart base models, `model-deployment` handles the turnkey path and delegates advanced topologies here.)*

---

## Core Architectural Patterns & Workflow

### 1. Choose the Right Hosting Topology

| Pattern | API / Mechanism | When to Choose |
|---|---|---|
| **Real-Time + `InferenceComponent` Bin-Packing** | `CreateEndpointConfig` (`ExecutionRoleArn`, `LEAST_OUTSTANDING_REQUESTS`) + `CreateInferenceComponent` (`ComputeResourceRequirements`, `CopyCount`) | **Default production pattern for ≥ 2 models** or when you need fractional GPU allocation and **Scale-to-Zero (`MinCapacity=0`)** on Real-Time Endpoints |
| **Real-Time Single-Model LMI / vLLM / TensorRT-LLM** | DJL Serving (`djl-inference:*-lmi*`) with `OPTION_ROLLING_BATCH=vllm`, `OPTION_TENSOR_PARALLEL_DEGREE` | Dedicated high-QPS LLM endpoint saturating 1–8 GPUs (`ml.g5`, `ml.g6e`, `ml.p4d`, `ml.p5`) |
| **AWS Inferentia2 (`ml.inf2`) Neuron Serving** | `djl-inference:*-neuronx*` or `pytorch-inference-neuronx` with `OPTION_TENSOR_PARALLEL_DEGREE` | **35%–50% lower cost per token/request** vs GPU instances for Llama, Mistral, Qwen, BERT, Whisper, SDXL |
| **Multi-Container Endpoint (MCE)** | `CreateModel` with `Containers=[...]` + `InferenceExecutionConfig.Mode = "Serial"` or `"Direct"` | **Serial**: chaining `preprocessor` → `model` → `postprocessor` in one hop. **Direct**: up to 15 heterogeneous containers invoked via `TargetContainerHostname` |
| **Multi-Model Endpoint (MME)** | `CreateModel` with `Mode="MultiModel"` pointing to `s3://<bucket>/models-prefix/` | 100s–1,000s of homogeneous CPU/Triton models dynamically loaded via `TargetModel` header |
| **Serverless Inference** | `ProductionVariants[].ServerlessConfig` (`MemorySizeInMB`: 1024–6144, `MaxConcurrency`: 1–200) | Spiky CPU-only inference (< 6 GB RAM, ≤ 4 MB payload, 60s timeout) with automatic scale-to-zero |
| **Asynchronous Inference** | `AsyncInferenceConfig` (`S3OutputPath`, `MaxConcurrentInvocationsPerInstance`) + `InvokeEndpointAsync` | Payloads up to **1 GB** (high-res images/SAM segmentation, PDFs, audio/video) or inference taking **1–60 minutes**, with Scale-to-Zero on empty S3 queue |
| **Batch Transform** | `CreateTransformJob` (`BatchStrategy="MultiRecord"`, `JoinSource="Input"`) | Offline bulk dataset scoring on S3 with zero persistent endpoint cost |
| **Bedrock Custom Model Import (CMI)** | `bedrock.create_model_import_job` | Serving custom S3 HuggingFace safetensors weights (< 200 GB) through the serverless Bedrock `InvokeModel` / `Converse` API |

---

### 2. Mandatory Production Inference Standards

1. **Always Configure `LEAST_OUTSTANDING_REQUESTS` for LLM & Variable-Latency Endpoints**:
   - In `CreateEndpointConfig`, set `RoutingConfig={"RoutingStrategy": "LEAST_OUTSTANDING_REQUESTS"}` so long-prompt requests do not head-of-line block short requests (unlike random routing).
2. **Use `InferenceComponent` + Scale-to-Zero (`MinCapacity=0`) to Eliminate Idle GPU Waste**:
   - Allocate exact `NumberOfAcceleratorDevicesRequired` (e.g., `1` GPU out of 4 on `ml.g5.12xlarge`), `NumberOfCpuCoresRequired`, and `MinMemoryRequiredInMb`.
   - Register an Application Auto Scaling target on `sagemaker:inference-component:DesiredCopyCount` with `MinCapacity=0`, tracking `SageMakerVariantInvocationsPerCopy`, plus a Step Scaling wakeup policy on `NoCapacityInvocationFailures` to scale `0 → 1` copy when traffic arrives.
   - Always pass `InferenceComponentName="<ic-name>"` in `invoke_endpoint` or `invoke_endpoint_with_response_stream`.
3. **VPC Isolation & KMS Encryption**:
   - Configure `VpcConfig` (`Subnets` across ≥ 2 AZs, `SecurityGroupIds`) on `CreateModel` and `KmsKeyId` on `CreateEndpointConfig` (and `AsyncInferenceConfig.OutputConfig.KmsKeyId`).
4. **Right-Size via SageMaker Inference Recommender**:
   - Before locking in production instance types, offer to run `CreateInferenceRecommendationsJob` (`JobType="Default"` or `"Advanced"`) or the `model-deployment` benchmarking workflow.

Read `references/inference-components-and-routing.md` for complete `boto3` and SDK v3 implementations of all 9 patterns.

## References

- `references/inference-components-and-routing.md` — Complete production code for `InferenceComponent` bin-packing + Scale-to-Zero (`MinCapacity=0`), LMI/vLLM & `ml.inf2` Neuron serving, Multi-Container (`Serial`/`Direct`), Multi-Model (`TargetModel`), Serverless, Asynchronous (`InvokeEndpointAsync`), Batch Transform, Bedrock Custom Model Import (`CreateModelImportJob`), and Inference Recommender.
