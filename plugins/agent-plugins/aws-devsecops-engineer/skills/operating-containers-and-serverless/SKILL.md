---
name: operating-containers-and-serverless
description: >-
  Troubleshoots, secures, and optimizes AWS container (ECS Fargate, EKS, ECR) and serverless
  (Lambda, API Gateway, EventBridge, SQS) workloads: diagnoses `StoppedReason` / `ExitCode: 137`
  OOM kills, image pull failures, cold starts, concurrency throttling, and configures safe
  CodeDeploy Blue/Green and Canary rollouts. Use when the user asks to "debug ECS task failures",
  "fix Lambda timeouts or OOM", "configure blue-green deployment", or optimize runtime compute.
---

# Container (ECS/EKS) & Serverless (Lambda) Operations

## When to Use
Invoke this skill whenever a user needs to troubleshoot failing ECS Fargate tasks, EKS pods, or Lambda functions, harden container/function execution roles, optimize cold starts or memory/CPU sizing, or configure progressive Blue/Green and Canary deployments.

## 1. ECS Fargate & Container Troubleshooting Workflow

### Diagnose Stopped Tasks & Deployment Failures
Run `aws___run_script` to inspect stopped tasks, container exit codes, and service events:

```python
import boto3

ecs = boto3.client("ecs")
cluster = "<cluster-name>"
service = "<service-name>"

svc = ecs.describe_services(cluster=cluster, services=[service])["services"][0]
print("Recent Service Events:", [e["message"] for e in svc.get("events", [])[:5]])

stopped_arns = ecs.list_tasks(cluster=cluster, serviceName=service, desiredStatus="STOPPED", maxResults=10)["taskArns"]
if stopped_arns:
    tasks = ecs.describe_tasks(cluster=cluster, tasks=stopped_arns)["tasks"]
    for t in tasks:
        print(f"Task {t['taskArn'].split('/')[-1]}: stoppedReason={t.get('stoppedReason')} stopCode={t.get('stopCode')}")
        for c in t.get("containers", []):
            print(f"  Container {c['name']}: exitCode={c.get('exitCode')} reason={c.get('reason')}")
```

### Common ECS Failure Signatures & Fixes
- **`OutOfMemoryError: Container killed due to memory usage` (`ExitCode: 137`)**: Increase task `memory` in the task definition or set runtime heap limits (`NODE_OPTIONS="--max-old-space-size=..."`, `JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=75.0"`).
- **`CannotPullContainerError` (Timeout or AccessDenied)**:
  - **Timeout**: Task in a private subnet without a NAT Gateway or ECR VPC Endpoints (`com.amazonaws.<region>.ecr.api`, `ecr.dkr`, and S3 Gateway endpoint) — or `assignPublicIp: ENABLED` accidentally set on a private subnet without an IGW.
  - **AccessDenied**: Task Execution Role (`executionRoleArn`) is missing `AmazonECSTaskExecutionRolePolicy` or KMS `kms:Decrypt` permission for an encrypted ECR repository.
- **ALB Health Check Flapping (`Task failed ELB health checks`)**: Verify container `healthCheck.startPeriod` / ALB `health_check.grace_period_seconds` is long enough for application boot, and confirm the Task Security Group allows ingress from the ALB Security Group on the container port.

## 2. AWS Lambda Troubleshooting & Optimization Workflow

### Diagnose Timeouts, OOMs, Cold Starts & Throttles
Query `aws-cloudwatch` (`execute_log_insights_query`) against `/aws/lambda/<function-name>` using `REPORT` lines:

```sql
filter @type = "REPORT"
| stats
    count(*) as invocations,
    pct(@duration, 50) as p50_ms,
    pct(@duration, 99) as p99_ms,
    max(@maxMemoryUsed / 1000000) as max_mem_mb,
    avg(@memorySize / 1000000) as allocated_mem_mb,
    count(@initDuration) as cold_starts,
    pct(@initDuration, 99) as p99_init_ms
```

- **OOM (`max_mem_mb >= allocated_mem_mb` or `Runtime.ExitError`)**: Increase `MemorySize` (which proportionally increases vCPU and network bandwidth).
- **Timeouts (`Task timed out after X seconds`)**: Inspect X-Ray traces (`aws xray get-trace-summaries`) to determine whether a downstream call (RDS, external HTTP, or VPC blackhole) is hanging; always set SDK socket/connect timeouts shorter than the Lambda function timeout.
- **Event Source Mapping (SQS / Kinesis) DLQ & Retry Safety**: Ensure `FunctionResponseTypes: ["ReportBatchItemFailures"]` is enabled, `VisibilityTimeout >= 6 * FunctionTimeout`, and a Dead-Letter Queue (`RedrivePolicy`) is attached.

## 3. Progressive Rollout & Circuit Breaker Patterns
Always configure automated rollback gates in IaC (`template.yaml`, CDK, Terraform):
- **ECS Rolling Update**: Enable `deploymentCircuitBreaker: { enable: true, rollback: true }`.
- **ECS / Lambda Blue/Green & Canary (`AWS::CodeDeploy`)**: Use `ECSCanary10Percent5Minutes` or `LambdaCanary10Percent10Minutes` wired to CloudWatch `5XX` and `Errors` alarms with `autoRollbackConfiguration: { enabled: true, events: ["DEPLOYMENT_FAILURE", "DEPLOYMENT_STOP_ON_ALARM"] }`.
