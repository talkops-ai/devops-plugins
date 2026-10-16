# ECS Stopped Task Codes & `ResourceInitializationError` Decision Tree

## 1. Complete `stopCode` Reference (`DescribeTasks`)

| `stopCode` | Initiator | Typical Root Cause & Investigation Path |
|---|---|---|
| **`TaskFailedToStart`** | ECS Agent / Fargate | Image pull failure, missing secret/SSM parameter permission on `executionRoleArn`, ENI attachment timeout, or missing `awslogs` log group. |
| **`EssentialContainerExited`** | Container Runtime | Essential container exited on its own (`exitCode != 0` crash or `exitCode == 0` unexpected completion) or was killed by `OutOfMemoryError` (`exitCode == 137`). |
| **`ServiceSchedulerInitiated`** | ECS Service Scheduler | Failed ELB/ALB target group health check, container healthCheck failure, deployment scale-in, or deployment circuit breaker rollback. |
| **`SpotInterruption`** | AWS EC2 / Fargate Spot | Fargate Spot or EC2 Spot capacity reclaimed (`SIGTERM` sent with 2-minute warning). |
| **`TerminationNotice`** | ECS Control Plane | Underlying Fargate infrastructure maintenance retirement or EC2 instance termination. |
| **`UserInitiated`** | IAM Principal / CI-CD | Explicit `StopTask` or `UpdateService --force-new-deployment` call in CloudTrail. |

---

## 2. Fargate `ResourceInitializationError` Exact String Decoder

| `stoppedReason` Substring | Exact Root Cause | Required Fix |
|---|---|---|
| `unable to pull secrets or registry auth: execution resource retrieval failed: unable to retrieve ecr registry auth: ... i/o timeout` | Task ENI in private subnet cannot reach `api.ecr.<region>.amazonaws.com` on TCP 443. | Add NAT Gateway route OR create `com.amazonaws.<region>.ecr.api` Interface VPC Endpoint with Private DNS enabled and Security Group allowing TCP 443 from Task SG. |
| `unable to pull image ... layers: ... s3.<region>.amazonaws.com:443: i/o timeout` | Task authenticated with `ecr.api`/`ecr.dkr`, but ECR stores actual Docker image layers in **Amazon S3**, and the private subnet route table lacks an **S3 Gateway VPC Endpoint**. | Create `com.amazonaws.<region>.s3` Gateway VPC Endpoint and associate it with the private subnet route tables, or allow S3 prefix-list outbound in Task SG. |
| `failed to create CloudWatch log stream: ... logs.<region>.amazonaws.com:443: i/o timeout` | Task cannot reach CloudWatch Logs endpoint to initialize the `awslogs` driver. | Create `com.amazonaws.<region>.logs` Interface VPC Endpoint or verify `logs:CreateLogStream` on `executionRoleArn`. |
| `unable to pull secrets ... secretsmanager: ... AccessDeniedException` | `executionRoleArn` lacks `secretsmanager:GetSecretValue` or `kms:Decrypt` on the CMK encrypting the secret. | Add `secretsmanager:GetSecretValue` and `kms:Decrypt` to `executionRoleArn` (note: startup secrets injection uses `executionRoleArn`, NOT `taskRoleArn`). |
