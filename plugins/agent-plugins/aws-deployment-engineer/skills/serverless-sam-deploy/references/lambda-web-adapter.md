# AWS Lambda Web Adapter (LWA) for Full-Stack Web Applications

The **AWS Lambda Web Adapter** allows standard HTTP web frameworks (FastAPI, Express, Next.js, Flask, Django, Spring Boot, Go `net/http`, Rust Axum) to run on AWS Lambda without changing application code to use `mangum` or `serverless-http` wrappers.

## 1. How Lambda Web Adapter Works

- Runs as a Lambda Extension (`AWS_LAMBDA_EXEC_WRAPPER=/opt/bootstrap` for zip functions, or `COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter` for container images).
- Starts your HTTP server on `PORT` (default `8080`), polls `AWS_LWA_READINESS_CHECK_PATH` (default `/`), translates incoming API Gateway / ALB / Function URL events into standard HTTP requests to `127.0.0.1:<PORT>`, and supports response streaming (`AWS_LWA_INVOKE_MODE=response_stream`).

## 2. Official Lambda Layer ARNs

- **ARM64 (Graviton2 — Recommended):**
  `arn:aws:lambda:${AWS::Region}:753240598075:layer:LambdaAdapterLayerArm64:25`
- **x86_64:**
  `arn:aws:lambda:${AWS::Region}:753240598075:layer:LambdaAdapterLayerX86:25`

## 3. SAM Template Pattern (Zip Archive + HTTP API)

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: FastAPI / Express web service via AWS Lambda Web Adapter

Globals:
  Function:
    Timeout: 29
    MemorySize: 1024
    Architectures:
      - arm64
    Tracing: Active
    LoggingConfig:
      LogFormat: JSON

Resources:
  WebAppFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: src/
      Handler: run.sh
      Runtime: python3.12
      Layers:
        - !Sub arn:aws:lambda:${AWS::Region}:753240598075:layer:LambdaAdapterLayerArm64:25
      Environment:
        Variables:
          AWS_LAMBDA_EXEC_WRAPPER: /opt/bootstrap
          PORT: '8080'
          AWS_LWA_READINESS_CHECK_PATH: /health
          AWS_LWA_READINESS_CHECK_PORT: '8080'
      Events:
        HttpApiRoot:
          Type: HttpApi
          Properties:
            PayloadFormatVersion: '2.0'
```

Where `src/run.sh` (executable `chmod +x src/run.sh`) launches the web server:

```bash
#!/usr/bin/env bash
exec python3 -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"
```

## 4. OCI Container Image Pattern with Lambda Web Adapter

```dockerfile
FROM public.ecr.aws/docker/library/python:3.12-slim
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter
WORKDIR /var/task
ENV PORT=8080 AWS_LWA_READINESS_CHECK_PATH=/health
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

## 5. Key Tuning Variables

| Environment Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` / `AWS_LWA_PORT` | `8080` | Port your HTTP server listens on inside the execution environment |
| `AWS_LWA_READINESS_CHECK_PATH` | `/` | Health check path polled before forwarding the first request (always set to `/health`) |
| `AWS_LWA_INVOKE_MODE` | `buffered` | Set to `response_stream` when using Lambda Function URLs or REST API response streaming for SSE/LLM streams |
| `AWS_LWA_ASYNC_INIT` | `false` | Set to `true` if server initialization takes $> 10\text{s}$ to avoid Lambda init timeout |
