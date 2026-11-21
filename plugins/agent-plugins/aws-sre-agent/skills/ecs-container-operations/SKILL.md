---
name: ecs-container-operations
description: Diagnose and remediate Amazon ECS and AWS Fargate production incidents across stopped tasks (OutOfMemoryError, CannotPullContainerError, ResourceInitializationError), ALB target group health check failures, ECS Deployment Circuit Breaker rollbacks, Capacity Provider scaling stalls, ECS Service Connect, and ECS Express Mode. Use when the user asks about ECS task failures, Fargate troubleshooting, ECS deployment rollbacks, or container exit codes.
---

# Amazon ECS & AWS Fargate Production Operations & Troubleshooting Guide

Use this skill whenever triaging or operating workloads on **Amazon ECS** (AWS Fargate, EC2 Capacity Providers, Managed Instances, or **ECS Express Mode**). Combine the `ecs` MCP server (`ecs_resource_management`, `ecs_troubleshooting_tool`) with `cloudwatch`, `network`, and `cloudtrail`.

---

## 1. Mandatory 5-Action `ecs_troubleshooting_tool` Diagnostic Sequence

When an ECS service deployment fails, tasks repeatedly stop, or ALB target health checks fail, run the `ecs_troubleshooting_tool` actions in this exact order:

| Step | `ecs_troubleshooting_tool` Action | What It Inspects |
|---|---|---|
| **1. Initial Discovery** | `get_ecs_troubleshooting_guidance` | Collects cluster status, service events, task definitions, and generates an initial symptom assessment. |
| **2. Infrastructure & Stack State** | `fetch_cloudformation_status` | Checks the underlying CloudFormation stack, Service, TaskSet, and deployment circuit breaker status. |
| **3. Network & ALB / Security Groups** | `fetch_network_configuration` | Inspects VPC, Subnets, Route Tables, NAT Gateways, VPC Endpoints, Security Groups, and ALB Target Group health check settings (`HealthCheckPort`, `HealthCheckGracePeriodSeconds`). |
| **4. Task Stop Codes & Exit Reasons** | `fetch_task_failures` | Retrieves recently `STOPPED` tasks (`stopCode`, `stoppedReason`, `containers[].exitCode`, `containers[].reason`). |
| **5. Application & Runtime Logs** | `fetch_task_logs` | Queries the `awslogs` CloudWatch Log Group for startup exceptions, stack traces, or health check timeouts. |

*(Use `ecs_resource_management` for direct read-only ECS API calls: `DescribeClusters`, `DescribeServices`, `DescribeTasks`, `DescribeTaskDefinition`, `ListTasks` with `desiredStatus="STOPPED"`.)*

---

## 2. Stopped Task Forensics Matrix (`stopCode` & `stoppedReason`)

| `stopCode` / `stoppedReason` | Root Cause | Diagnostic Verification | Remediation |
|---|---|---|---|
| **`OutOfMemoryError`** (`Exit Code 137`) | Container exceeded `memory` (hard limit) in task definition. | `fetch_task_failures` + `cloudwatch.get_metric_data` (`MemoryUtilized` vs `MemoryReserved` in `AWS/ECS/ContainerInsights`). | Increase task/container `memory` in Task Definition and cap runtime heap (`-XX:MaxRAMPercentage=75.0`, `NODE_OPTIONS="--max-old-space-size=..."`). |
| **`CannotPullContainerError` / `ResourceInitializationError`** | Fargate task in a private subnet lacks route to NAT Gateway OR lacks VPC Endpoints (`com.amazonaws.<region>.ecr.api`, `ecr.dkr`, `logs`, and **S3 Gateway Endpoint** for ECR image layers); or `executionRoleArn` lacks `ecr:GetAuthorizationToken` / `kms:Decrypt`. | `fetch_network_configuration` + `network.get_vpc_network_details` + verify `assignPublicIp` (`DISABLED` requires NAT or PrivateLink). | Provision ECR Interface Endpoints + S3 Gateway Endpoint + CloudWatch Logs Endpoint, or attach NAT Gateway route; verify `executionRoleArn` permissions. |
| **`TaskFailedToStart` (`SecretsManager` / `SSM` error)** | `executionRoleArn` (not `taskRoleArn`!) lacks `secretsmanager:GetSecretValue`, `ssm:GetParameters`, or `kms:Decrypt` for injected `secrets` in the container definition. | Inspect `stoppedReason` (`AccessDeniedException` fetching secret ARN). | Grant `secretsmanager:GetSecretValue` and `kms:Decrypt` on the **Task Execution Role (`executionRoleArn`)**. |
| **`ServiceSchedulerInitiated` (ALB Health Check Failed)** | Container listens on `127.0.0.1` instead of `0.0.0.0`, Security Group blocks ALB -> Task port, app boots slower than `healthCheckGracePeriodSeconds`, or `/health` endpoint checks a slow DB and times out. | `fetch_network_configuration` + compare container port mapping with ALB Target Group health check path/port/timeout. | Increase `healthCheckGracePeriodSeconds` (e.g., `60`–`120`s), bind to `0.0.0.0`, allow ALB SG inbound on container port, and make `/health` a fast local readiness check. |
| **`EssentialContainerExited` (`Exit Code 1` / `143`)** | Main application process crashed (`Exit 1`) or was killed by `SIGTERM` (`Exit 143`) after failing container-level `healthCheck`. | `fetch_task_logs` around task `stoppedAt` timestamp. | Fix application startup exception or container `healthCheck` `startPeriod`. |

---

## 3. ECS Deployment Circuit Breaker & Graceful Drain (`stopTimeout`)

1. **Deployment Circuit Breaker (`deploymentCircuitBreaker`)**:
   - Always enable `enable=true, rollback=true` on production ECS `REPLICA` services so failed rollouts automatically revert to the last stable Task Definition revision instead of looping forever.
2. **Preventing 502/504 Errors During Scale-In or Rolling Deployments**:
   - Set ALB Target Group `deregistration_delay.timeout_seconds` (e.g., `30s`) and set container `stopTimeout` (`>= 30s`, max `120s` on Fargate) so in-flight HTTP requests finish draining before `SIGKILL`.

---

## Reference Files

- [references/stopped-task-codes.md](references/stopped-task-codes.md) — Complete ECS `stopCode`, `stoppedReason`, and Fargate `ResourceInitializationError` decision tree
- [references/fargate-and-capacity-providers.md](references/fargate-and-capacity-providers.md) — Fargate vs. Fargate Spot interruption handling, EC2 Capacity Provider Managed Scaling, Ephemeral Storage (`20 GiB`–`200 GiB`), and `executionRoleArn` vs `taskRoleArn`
- [references/express-mode-troubleshooting.md](references/express-mode-troubleshooting.md) — Troubleshooting ECS Express Mode (`DescribeExpressGatewayService`) and ECS Service Connect Envoy sidecar telemetry

## MCP-First Execution, Guardrails & `awsknowledge` Fallback

- **MCP-Only Execution (Zero Raw AWS CLI in Shell)**: When querying live AWS state, telemetry, pricing, or IaC compliance, always use connected MCP tools (`ecs`, `aws-mcp` `aws___call_aws`, `cloudwatch`, `awspricing`, `awsiac`, `awsknowledge`) in strictly read-only mode. NEVER execute raw `aws`, `docker`, or `finch` CLI commands via `run_command` / `Bash`.
- **Honest Zero-Resource Reporting**: If `0` ECS clusters, services, or log groups exist in the queried region, report `0` matching resources honestly without fabricating cluster ARNs, task IDs, or log lines, and then provide the complete diagnostic runbook.
- **Vague Workload Sizing & Cost Guard**: If the user asks for Fargate task CPU/memory sizing, capacity provider weights, or monthly ECS cost estimates without providing concrete workload metrics (`CPUUtilized`, `MemoryUtilized`, task count, RPS), refuse to fabricate or guess specific sizing numbers or monthly dollar totals and state which CloudWatch Container Insights metrics must be gathered first.
- **Read-Only & Secret Safety (`aws-mutation-gate.py`, `secret-safety.py`)**: Never run mutating ECS operations (`aws ecs stop-task`, `update-service`, `delete-service`, `register-task-definition`) or fetch plaintext secrets (`aws secretsmanager get-secret-value`, `curl localhost:2773/secretsmanager/get`); recommend `DescribeSecret` metadata checks and `secrets.valueFrom` on `executionRoleArn` instead.
- **`awsknowledge` Edge-Case Fallback**: Only when **no** local `references/*.md` file covers the user's specific edge-case question (e.g., ECS Task Scale-in Protection via `$ECS_AGENT_URI/task-protection/v1/state`), query the connected `awsknowledge` MCP server (`aws___search_documentation` and `aws___read_documentation` — max 1–2 focused searches) and answer directly. Never call `awsknowledge` for topics already covered in local `references/*.md`.
- **Fast, Bounded Discovery & Pricing Calls (Avoid Tool Loops)**: Limit live AWS discovery in the target region to 1–3 read-only MCP calls (`ecs`, `cloudwatch`, or `aws-mcp` `aws___call_aws`). Only call `awspricing` (`get_pricing`) if the user explicitly asks for pricing, and make at most 2–3 filtered `get_pricing` calls total.
