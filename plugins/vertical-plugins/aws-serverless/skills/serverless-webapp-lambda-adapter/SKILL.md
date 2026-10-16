---
name: serverless-webapp-lambda-adapter
description: Deploy full-stack, backend, and frontend web applications (Express.js, Next.js, FastAPI, Flask, Django, Spring Boot, React/Vue/Vite) to AWS Lambda, API Gateway, S3, and CloudFront using AWS Lambda Web Adapter and aws-serverless-mcp (deploy_webapp, update_webapp_frontend, configure_domain). Use when running standard HTTP web frameworks on Lambda without rewriting routes into raw Lambda event handlers.
---

# Serverless Web Applications with AWS Lambda Web Adapter

Run standard HTTP web frameworks (Express.js, Next.js, FastAPI, Flask, Django, Go `net/http`, Rust Axum, Spring Boot) unmodified on AWS Lambda using **AWS Lambda Web Adapter** and the `aws-serverless-mcp` webapp tools (`deploy_webapp`, `update_webapp_frontend`, `configure_domain`, `webapp_deployment_help`).

## When to Use

- Lifting and shifting or building a greenfield web application using Express.js, Next.js (SSR), FastAPI, Flask, or Django on serverless compute without coupling code to `event, context` signatures
- Deploying a full-stack application (backend API on Lambda + API Gateway and static frontend on S3 + CloudFront) in a single workflow
- Streaming Server-Sent Events (SSE) or LLM token responses from FastAPI/Express/Next.js on Lambda using `RESPONSE_STREAM`
- Configuring custom domains, ACM TLS certificates, and Route 53 DNS records for serverless web apps

---

## 1. How AWS Lambda Web Adapter Works

AWS Lambda Web Adapter is a lightweight Rust-based Lambda Extension packaged as a Lambda Layer (or container binary `/opt/extensions/lambda-adapter`):
1. The Lambda Runtime API delivers an invocation payload (from API Gateway HTTP API, REST API, ALB, or Lambda Function URL) to the Web Adapter extension.
2. The Web Adapter translates the event into a standard HTTP/1.1 request and forwards it to your web server listening on `http://127.0.0.1:8080`.
3. It polls your readiness endpoint (`AWS_LWA_READINESS_CHECK_PATH`, default `/`) during cold start before dispatching traffic, and converts your HTTP response back into the Lambda response payload (buffered or streamed).

### Key Environment Variables & Layer ARNs

| Variable | Recommended Value | Purpose |
|---|---|---|
| `AWS_LAMBDA_EXEC_WRAPPER` | `/opt/bootstrap` | Allows Lambda to execute a standard startup script (`run.sh`) instead of a language runtime handler (for Zip packages) |
| `PORT` | `8080` | Port your HTTP server (Express, Uvicorn, Next.js, Gunicorn) listens on |
| `AWS_LWA_READINESS_CHECK_PATH` | `/health` or `/healthz` | Fast, dependency-free readiness check endpoint (`200 OK`) |
| `AWS_LWA_INVOKE_MODE` | `buffered` or `response_stream` | Set to `response_stream` when paired with Lambda Function URL `InvokeMode: RESPONSE_STREAM` |
| `AWS_LWA_ASYNC_INIT` | `true` | Allows frameworks with slow initialization (> 10s init phase limit) to complete startup in the invocation phase |
| `AWS_LWA_PASS_THROUGH_PATH` | `/events` | Endpoint that receives raw non-HTTP Lambda invocations (e.g., SQS or EventBridge events) as HTTP POST |

**Official Lambda Web Adapter Layer ARNs:**
- **`arm64` (Recommended)**: `arn:aws:lambda:${AWS::Region}:753240598075:layer:LambdaAdapterLayerArm64:24`
- **`x86_64`**: `arn:aws:lambda:${AWS::Region}:753240598075:layer:LambdaAdapterLayerX86:24`

---

## 2. MCP Tool Workflow (`aws-serverless-mcp`)

### Step 1: Inspect Requirements & Build Artifacts
Call `webapp_deployment_help` (`deployment_type: "backend" | "frontend" | "fullstack"`) if needed, then verify:
- **Backend (`backend` or `fullstack`)**:
  - Has a lightweight health check route (e.g., `GET /health` returning `200 OK`)
  - Has a startup script (e.g., `run.sh` with `chmod +x run.sh`) that launches the HTTP server on `$PORT`
  - Dependencies are installed in the `built_artifacts_path` directory
- **Frontend (`frontend` or `fullstack`)**:
  - Static assets are built (`npm run build` -> `dist/`, `build/`, or `out/`)

### Step 2: Deploy with `deploy_webapp`
Call `deploy_webapp` (only after user confirmation for cloud mutation):
- **`deployment_type`**: `"backend"`, `"frontend"`, or `"fullstack"`
- **`project_name`** & **`project_root`**: Absolute path to the workspace project
- **`region`**: Explicit AWS region (e.g., `us-east-1`)
- **`backend_configuration`** (for `backend` / `fullstack`):
  - `built_artifacts_path`: Absolute path to compiled backend artifacts
  - `runtime`: e.g., `nodejs22.x`, `python3.13`
  - `port`: `8080`
  - `startup_script`: Relative path inside `built_artifacts_path` (e.g., `run.sh`, must have `chmod +x`)
  - `architecture`: `"arm64"` (recommended) or `"x86_64"`
  - `memory_size`: `512` to `1769` MB
  - `timeout`: `30` seconds
  - `environment_variables`: App-specific config (`NODE_ENV: "production"`, `AWS_LWA_READINESS_CHECK_PATH: "/health"`)
- **`frontend_configuration`** (for `frontend` / `fullstack`):
  - `built_artifacts_path`: Absolute path to `dist/` or `build/`
  - `index_document`: `"index.html"`
  - `error_document`: `"index.html"` (for SPA client-side routing)

### Step 3: Fast Frontend Updates (`update_webapp_frontend`)
When only frontend UI code changes, avoid a full CloudFormation stack redeploy by calling `update_webapp_frontend`:
- Uploads modified static assets to S3 (`sync_to_s3`) and optionally invalidates the CloudFront distribution cache.

### Step 4: Custom Domain, ACM TLS & Route 53 (`configure_domain`)
To bind a custom domain (e.g., `app.example.com`) to the deployed CloudFront distribution:
- Call `configure_domain` with `project_name`, `domain_name`, `create_certificate: true`, `create_route53_record: true`, and `region`.

---

## 3. Production SAM Templates & Startup Scripts by Framework

### A. FastAPI (Python 3.13 + Uvicorn)

**`run.sh`** (must be executable: `chmod +x run.sh`):
```bash
#!/bin/bash
set -euo pipefail
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}" --workers 1
```

**`template.yaml`**:
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  FastApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: ./dist
      Handler: run.sh
      Runtime: python3.13
      Architectures:
        - arm64
      MemorySize: 1024
      Timeout: 29
      Layers:
        - !Sub arn:aws:lambda:${AWS::Region}:753240598075:layer:LambdaAdapterLayerArm64:24
      Environment:
        Variables:
          AWS_LAMBDA_EXEC_WRAPPER: /opt/bootstrap
          PORT: "8080"
          AWS_LWA_READINESS_CHECK_PATH: /health
      Events:
        HttpApiEvent:
          Type: HttpApi
          Properties:
            PayloadFormatVersion: "2.0"
```

### B. Next.js SSR (`output: 'standalone'`)

1. Set `output: 'standalone'` in `next.config.js`.
2. Build with `npm run build` and copy `.next/static` and `public` into `.next/standalone/`.
3. Create **`run.sh`** inside `.next/standalone/`:
   ```bash
   #!/bin/bash
   set -euo pipefail
   export HOSTNAME=0.0.0.0
   export PORT="${PORT:-8080}"
   exec node server.js
   ```

### C. Response Streaming (`RESPONSE_STREAM`) for SSE & LLM Endpoints

When streaming responses (> 6 MB up to 20 MB, or long-running token streams), configure a **Lambda Function URL** (or CloudFront OAC -> Function URL) with `InvokeMode: RESPONSE_STREAM` and set `AWS_LWA_INVOKE_MODE: response_stream`:

```yaml
  StreamingFunctionUrl:
    Type: AWS::Lambda::Url
    Properties:
      TargetFunctionArn: !GetAtt FastApiFunction.Arn
      AuthType: AWS_IAM
      InvokeMode: RESPONSE_STREAM
```
