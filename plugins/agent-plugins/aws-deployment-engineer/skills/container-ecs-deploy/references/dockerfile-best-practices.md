# Hardened Multi-Stage Dockerfile & Finch/Docker Build Practices

## 1. Mandatory Container Security Rules

1. **Multi-Stage Builds:** Compile dependencies and build artifacts in a `builder` stage; copy only compiled artifacts and production runtime dependencies into a minimal final runtime image (`-slim`, `distroless`, or Amazon Linux 2023 minimal).
2. **Non-Root Execution:** Always create and switch to an unprivileged user (`USER appuser` / UID `10001`) before `CMD` or `ENTRYPOINT`.
3. **Mandatory `.dockerignore`:** Always generate `.dockerignore` before building:
   ```gitignore
   .git
   .gitignore
   .env
   .env.*
   *.pem
   *.key
   .aws
   node_modules
   .venv
   venv
   __pycache__
   cdk.out
   .terraform
   *.drawio
   reports/
   ```
4. **Explicit CPU Architecture Matching:** On Apple Silicon (`arm64`) workstations, always match `--platform` to the ECS Task Definition `runtimePlatform.cpuArchitecture`:
   - Prefer `ARM64` (AWS Graviton) for ~20% lower Fargate cost when all native dependencies support Linux ARM64.
   - Otherwise pass `--platform linux/amd64` during `docker build` / `finch build` and set `CpuArchitecture.X86_64` in CDK/CloudFormation.
5. **PID 1 Signal Handling:** Use `exec` form `ENTRYPOINT`/`CMD` (e.g., `["node", "dist/server.js"]` or `["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]`) so `SIGTERM` from ECS graceful task draining (`stopTimeout`) reaches the process cleanly.

## 2. Production Reference Templates

### Node.js / TypeScript ( Multi-Stage )

```dockerfile
FROM public.ecr.aws/docker/library/node:22-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build && npm prune --omit=dev

FROM public.ecr.aws/docker/library/node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production PORT=8080
RUN groupadd -g 10001 appgroup && useradd -u 10001 -g appgroup -s /sbin/nologin -M appuser
COPY --from=builder --chown=appuser:appgroup /app/package*.json ./
COPY --from=builder --chown=appuser:appgroup /app/node_modules ./node_modules
COPY --from=builder --chown=appuser:appgroup /app/dist ./dist
USER 10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:8080/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]
CMD ["node", "dist/index.js"]
```

### Python (FastAPI / Django / Flask with uv or pip)

```dockerfile
FROM public.ecr.aws/docker/library/python:3.12-slim AS builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM public.ecr.aws/docker/library/python:3.12-slim AS runner
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
RUN groupadd -g 10001 appgroup && useradd -u 10001 -g appgroup -s /sbin/nologin -M appuser
COPY --from=builder /install /usr/local
COPY --chown=appuser:appgroup . .
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]
CMD ["gunicorn", "main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "2"]
```

### Go (Static Binary)

```dockerfile
FROM public.ecr.aws/docker/library/golang:1.23-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/server ./cmd/server

FROM public.ecr.aws/eks-distro-build-tooling/eks-distro-minimal-base-nonroot:latest
WORKDIR /app
COPY --from=builder /out/server /app/server
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/app/server"]
```

## 3. Docker vs. Finch CLI Parity

Detect whichever container engine is active on the user's host:

```bash
if command -v finch >/dev/null 2>&1 && finch info >/dev/null 2>&1; then
  CONTAINER_CLI="finch"
elif command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  CONTAINER_CLI="docker"
fi
```

Both `docker` and `finch` accept identical `build --platform <arch> -t <uri>:<tag> .`, `tag`, `login`, and `push` syntax. Use `public.ecr.aws/docker/library/...` base images to prevent Docker Hub anonymous rate-limit (`429 Too Many Requests`) failures during local or CodeBuild builds.
