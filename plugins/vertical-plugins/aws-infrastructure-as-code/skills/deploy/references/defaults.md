# Service Defaults, Archetype Routing & Production Deployment Configuration Matrix

Default AWS service selections, specialist skill routing, and production deployment configuration baselines. Override whenever existing repository files (`template.yaml`, `Dockerfile`, `*.tf`, `cdk.json`, `buildspec.yml`, `appspec.yml`) or explicit user requirements dictate.

## 1. Compute & Delivery Routing Matrix (All 10 AWS Hosting Archetypes)

| App Pattern | Default Target | Specialist Skill(s) | Override Trigger |
| --- | --- | --- | --- |
| Web framework (Django, Rails, Express, FastAPI, Spring Boot, Go) | **ECS Fargate + ALB** (or **ECS Express Mode**) | `container-ecs-deploy` + `deploy` | `"serverless"` or `template.yaml` -> `serverless-sam-deploy` (Lambda Web Adapter + HTTP API); `"Elastic Beanstalk"` -> `elastic-beanstalk` |
| Event-driven API, webhook, or `template.yaml` project | **Lambda + API Gateway HTTP API** | `serverless-sam-deploy` | Stateful long-running connections / WebSockets at scale -> `container-ecs-deploy` (ECS Fargate) |
| Static site / SPA / Next.js SSR frontend | **AWS Amplify Hosting** or **S3 + CloudFront OAC** | `deploy` + `aws-deployment` | Custom edge WAF/routing/staging distribution -> Private S3 + CloudFront OAC + Continuous Deployment |
| Background queue/stream workers | **ECS Fargate** or **Lambda ESM** | `container-ecs-deploy` or `serverless-sam-deploy` | `< 15 min` bursty SQS/Kinesis/DynamoDB stream -> `serverless-sam-deploy`; `"Elastic Beanstalk"` -> `elastic-beanstalk` (Worker tier) |
| Scheduled cron jobs | **EventBridge Scheduler + Lambda** | `serverless-sam-deploy` | `> 15 min` execution -> EventBridge + ECS Fargate RunTask (`container-ecs-deploy`) |
| Heavy compute / ML batch / ETL jobs (`> 15 min` or GPU) | **AWS Batch (Fargate or EC2 Spot)** | `container-ecs-deploy` + `deploy` | Simple single-container job -> ECS Fargate Scheduled Task |
| Heroku / Render / Railway PaaS migration | **AWS Elastic Beanstalk** (AL2023) | `elastic-beanstalk` | `"containers"` / `"ECS"` -> `container-ecs-deploy`; `"serverless"` -> `serverless-sam-deploy` |
| Stateful VM, custom kernel, or GPU instance fleet | **EC2 Launch Template + Auto Scaling Group + ALB** | `deploy` + `aws-deployment` | Managed PaaS desired -> `elastic-beanstalk` |
| CI/CD pipeline, Blue/Green, Canary, or Feature Flag rollout | **CodePipeline V2 + CodeBuild + CodeDeploy + AppConfig** | `aws-deployment` + `verify-and-rollback` | GitHub/GitLab hosted runners -> GitHub Actions / GitLab CI OIDC workflow |
| Kubernetes manifests / Helm charts | **Amazon EKS (EKS Auto Mode / Fargate)** | Hand off cluster design to `aws-platform-engineer` | Non-K8s container app -> `container-ecs-deploy` (ECS Fargate) |

> **CRITICAL — AWS App Runner Guidance:** AWS App Runner is in maintenance mode for new greenfield architectures; prefer **Amazon ECS Express Mode** or **Amazon ECS Fargate + ALB** unless maintaining an existing brownfield App Runner service.

---

## 2. Service-by-Service Deployment Strategy & Production Configuration Matrix

| AWS Target Service | Dev Rollout Strategy | Production Rollout Strategy | Mandatory Health Check & Draining Config | Mandatory Rollback & Alarm Config |
| --- | --- | --- | --- | --- |
| **Amazon ECS Fargate + ALB** | Rolling (`minHealthy: 50%`, `max: 200%`) | **CodeDeploy Blue/Green** (`ECSCanary10Percent5Minutes` + `:8443` Test Listener) or Rolling (`100%/200%`) with Circuit Breaker | `healthCheckGracePeriodSeconds >= 60`; ALB `deregistration_delay = 30s`; Container `stopTimeout = 30s` | `deploymentCircuitBreaker: {enable: true, rollback: true}` OR CodeDeploy `DEPLOYMENT_STOP_ON_ALARM` + `terminationWaitTimeInMinutes: 30` |
| **ECS Express Mode** | Managed Rolling | Managed Rolling with Auto Scaling | Built-in HTTP `healthCheckPath` (`/health`), port `8080`, HTTPS ACM | Automatic task replacement on health check failure |
| **AWS Lambda (SAM / CDK)** | `AllAtOnce` (or `cdk deploy --hotswap-fallback`) | **CodeDeploy Alias Traffic Shifting** (`LambdaCanary10Percent10Minutes` or `LambdaLinear10PercentEvery1Minute`) | `AutoPublishAlias: live`; `PreTraffic` & `PostTraffic` validation Lambda hooks | `DeploymentPreference.Alarms` bound to `Errors` & `Throttles` (`DEPLOYMENT_STOP_ON_ALARM`) |
| **Elastic Beanstalk** | `AllAtOnce` (Single-Instance or Dev) | **`Immutable`** or **`RollingWithAdditionalBatch`** (`BatchSize: 30%`) or **Blue/Green (`eb swap`)** | Enhanced Health Reporting (`SystemType: enhanced`); Application `HealthCheckPath: /health` (`HTTP:200`); `Application Healthcheck URL` | `IgnoreHealthCheck: false`; `Timeout: 20–30 min`; previous application version retained in S3 for instant `eb deploy --version` |
| **S3 + CloudFront OAC** | Direct S3 sync + `CreateInvalidation` | **CloudFront Continuous Deployment** (Staging Distribution with Header or 5–10% Weight policy) | Origin Access Control (`sigv4`), `ResponseHeadersPolicy` (HSTS/CSP), custom `403/404 -> /index.html` for SPAs | S3 Versioning enabled; instant promotion/rollback via `update-distribution-with-staging-config` |
| **AWS Amplify Hosting** | Branch auto-build | Protected `main` branch + PR Preview Environments + Custom Domain ACM | Build-time SSR/SSG verification + post-build E2E smoke stage in `amplify.yml` | Instant 1-click redeploy of prior build artifact via `aws amplify start-job --job-type RELEASE` |
| **EC2 Auto Scaling Group (ASG)** | Launch Template update | **ASG Instance Refresh** (`MinHealthyPercentage: 90`, `MaxHealthyPercentage: 120`, `CheckpointPercentages: [20, 50, 100]`) or **CodeDeploy Blue/Green** | ELB health check (`HealthCheckType: ELB`, `HealthCheckGracePeriod: 300`); IMDSv2 `HttpTokens: required` | `AutoRollback: true` with `AlarmSpecification` bound to ALB 5xx alarm |
| **AWS AppConfig (Feature Flags)** | `AppConfig.AllAtOnce` | **`AppConfig.Canary10Percent20Minutes`** or **`Linear50PercentEvery30Seconds`** | JSON Schema validator + pre-deployment Lambda validator | `Environment.Monitors` bound to CloudWatch Alarms with `appconfig:StopDeployment` IAM role |
| **CloudFormation / CDK Stacks** | `cdk deploy` / `sam deploy` | **Change Set Execution** (`--no-execute-changeset` review -> execute) with `RollbackConfiguration` | `DeletionPolicy: Retain` & `UpdateReplacePolicy: Retain` on all stateful DBs/S3/ECR | `RollbackConfiguration` monitoring CloudWatch Alarms during stack update (`MonitoringTimeInMinutes: 10`) |

---

## 3. Database Selection & Zero-Downtime Cutover Matrix

| Data Pattern | Default (Dev) | Default (Prod) | Zero-Downtime Deployment & Upgrade Pattern |
| --- | --- | --- | --- |
| PostgreSQL / MySQL | **Aurora Serverless v2** (0.5–2 ACU) | **Aurora Serverless v2** (2–16 ACU, Multi-AZ) | **Expand-and-Contract** DDL for app releases; **RDS/Aurora Managed Blue/Green Deployment** for engine/major schema upgrades; **RDS Proxy** for Lambda connection pooling |
| Document / MongoDB | **DocumentDB Serverless** (0.5–2 DCU) | **DocumentDB Serverless** (2–8 DCU, Multi-AZ) | Backward-compatible document schema evolution with dual-read application adapters |
| NoSQL / Key-Value | **DynamoDB On-Demand** (`PAY_PER_REQUEST`) | **DynamoDB On-Demand** + PITR + Deletion Protection | Additive attributes & online GSI backfills; never delete/recreate tables in-place |
| Redis / Valkey Caching | **ElastiCache Serverless (Valkey)** | **ElastiCache Serverless (Valkey)** | Versioned cache keys (`v2:<key>`) to avoid serialization mismatches during Canary/Blue-Green |
| Full-Text / Vector Search | **OpenSearch Serverless** | **OpenSearch Serverless** | Index alias swap (`alias -> index_v2` after reindexing) for zero-downtime mapping changes |

---

## 4. Storage, Secrets & IaC Framework Baselines

| Component | Default Selection | Mandatory Security & Validation Baseline |
| --- | --- | --- |
| **Static Assets & Uploads** | **Amazon S3** | `BlockPublicAccess.BLOCK_ALL`, `BucketOwnerEnforced`, `SSE-S3`/`SSE-KMS`, `enforceSSL: true`, CloudFront OAC |
| **Secrets & Credentials** | **AWS Secrets Manager** | Runtime injection (`valueFrom` / `{{resolve:secretsmanager:...}}` / `environmentsecrets`); zero plaintext in IaC |
| **Non-Secret Config** | **SSM Parameter Store** | Standard parameter tier referenced by least-privilege IAM role; dynamic flags via **AWS AppConfig** |
| **Container Registry** | **Amazon ECR** | `scanOnPush: true`, `imageTagMutability: IMMUTABLE`, lifecycle policy keeping last 10–30 tagged images |
| **AWS CDK (TS/Python)** | Greenfield default or `cdk.json` | `npx cdk synth` -> `awsiac` (`validate_cloudformation_template` + `check_cloudformation_template_compliance`) + `cdk-nag` |
| **AWS SAM** | `template.yaml` / `samconfig.toml` | `PostToolUse` `validate-iac.sh` (`sam validate --lint`) + `awsiac` compliance |
| **Terraform / OpenTofu** | `*.tf` files or explicit request | `PostToolUse` `validate-iac.sh` (`terraform validate`) + `checkov` + S3 native state locking (`use_lockfile = true`) |
| **CloudFormation YAML** | `*.cfn.yaml` / `*.template.json` | `PostToolUse` `validate-iac.sh` (`cfn-lint`) + `awsiac` (`cfn-guard`) |

---

## 5. Sizing Defaults (Dev vs. Production)

Default to **dev-sized** (cost-conscious) unless the user specifies `"production"`, `"prod"`, or `"production-ready"`:

| Component | Dev Sizing | Production Sizing |
| --- | --- | --- |
| **ECS Fargate Task** | `0.5 vCPU, 1 GB` (`desiredCount: 1`, `ARM64`) | `1–2 vCPU, 2–4 GB` (`desiredCount >= 2`, Multi-AZ, Auto Scaling, Blue/Green) |
| **VPC NAT Gateway** | `1 NAT Gateway` (or reuse brownfield VPC) | `1 NAT Gateway per AZ` (2–3 AZs) + S3/DynamoDB Gateway VPC Endpoints (free) |
| **Aurora Serverless v2** | `0.5–2 ACU` (single writer) | `2–16 ACU` (writer + Multi-AZ failover reader + PITR + Deletion Protection) |
| **Elastic Beanstalk** | `1x t3.small` Single-Instance ($0 ALB) or ALB (`AllAtOnce`) | `2–4x t3.medium` Multi-AZ Cluster Mode + ALB (`Immutable` or `RollingWithAdditionalBatch`) |
| **AWS Lambda** | `512–1024 MB`, `arm64`, 7–14 day log retention | `1024–2048 MB`, `arm64`, DLQ + ESM `MaximumConcurrency`, Canary alias, 30–90 day KMS logs |
