# ECS Fargate + ALB vs. ECS Express Mode & Networking Architecture

## 1. Choosing Between ECS Express Mode and Standard ECS Fargate + ALB

| Dimension | ECS Express Mode | ECS Fargate + ALB (CDK / CFN / Terraform) |
| --- | --- | --- |
| **Target Use Case** | Single-container HTTP web apps and APIs needing rapid turnkey setup (replaces maintenance-mode App Runner) | Multi-tier production apps, background workers, custom VPC topologies, WAF/custom listener rules |
| **Required IAM Roles** | `ecsTaskExecutionRole`, `ecsInfrastructureRoleForExpressServices`, plus optional `taskRole` | `ecsTaskExecutionRole` and least-privilege `taskRole` |
| **Networking** | Automated ALB/target group/autoscaling orchestration via Express Mode | Explicit VPC public/private subnets, Security Group chaining, Target Group health checks |

## 2. IAM Role Separation (Execution Role vs. Task Role)

Never combine execution and application permissions into a single over-privileged role:

1. **Task Execution Role (`executionRoleArn` / `ecsTaskExecutionRole`):**
   - Trusted entity: `ecs-tasks.amazonaws.com`
   - Managed policy: `arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy`
   - Inline additions: `secretsmanager:GetSecretValue` and `ssm:GetParameters` scoped strictly to the exact ARNs referenced in the container definition's `secrets` block, plus `kms:Decrypt` if encrypted with a customer-managed KMS key.
2. **Task Role (`taskRoleArn`):**
   - Trusted entity: `ecs-tasks.amazonaws.com` (with `aws:SourceAccount` and `aws:SourceArn` confused-deputy conditions)
   - Permissions: Scoped strictly to the AWS services called by the application code (e.g., `dynamodb:GetItem`, `s3:PutObject`, `bedrock:InvokeModel` on specific resource ARNs).
3. **ECS Express Mode Infrastructure Role (`ecsInfrastructureRoleForExpressServices`):**
   - Trusted entity: `ecs.amazonaws.com`
   - Managed policy: `arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices`

## 3. Hardened CDK TypeScript Pattern (Fargate + ALB + Circuit Breaker)

```typescript
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecs_patterns from 'aws-cdk-lib/aws-ecs-patterns';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';

const cluster = new ecs.Cluster(this, 'AppCluster', {
  vpc,
  containerInsightsV2: ecs.ContainerInsights.ENHANCED,
});

const service = new ecs_patterns.ApplicationLoadBalancedFargateService(this, 'WebService', {
  cluster,
  cpu: 512,
  memoryLimitMiB: 1024,
  desiredCount: isProd ? 2 : 1,
  runtimePlatform: {
    cpuArchitecture: ecs.CpuArchitecture.ARM64,
    operatingSystemFamily: ecs.OperatingSystemFamily.LINUX,
  },
  taskSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
  publicLoadBalancer: true,
  redirectHTTP: true,
  circuitBreaker: { rollback: true },
  enableExecuteCommand: false,
  taskImageOptions: {
    image: ecs.ContainerImage.fromEcrRepository(repo, imageTag),
    containerPort: 8080,
    logDriver: ecs.LogDrivers.awsLogs({
      streamPrefix: 'web',
      logRetention: logs.RetentionDays.ONE_MONTH,
    }),
    secrets: {
      DATABASE_URL: ecs.Secret.fromSecretsManager(dbSecret),
    },
  },
});

service.targetGroup.configureHealthCheck({
  path: '/health',
  healthyHttpCodes: '200',
  interval: cdk.Duration.seconds(30),
  timeout: cdk.Duration.seconds(5),
  healthyThresholdCount: 2,
  unhealthyThresholdCount: 3,
});
```

## 4. Common ECS Fargate Deployment Pitfalls & Remediations

| Symptom | Root Cause | Fix |
| --- | --- | --- |
| `ResourceInitializationError: unable to pull secrets or registry auth` | Fargate task in private subnet lacks route to NAT Gateway or VPC Endpoints (`ecr.api`, `ecr.dkr`, `s3`, `secretsmanager`, `logs`), or `assignPublicIp: false` in a public subnet. | Place tasks in `PRIVATE_WITH_EGRESS` subnets with NAT Gateway (or interface/gateway VPC endpoints), and ensure `ecsTaskExecutionRole` has `secretsmanager:GetSecretValue` on the secret ARN. |
| `exec /app/server: exec format error` | Image built for `arm64` on Apple Silicon but Task Definition specifies `X86_64` (or vice versa). | Align `--platform linux/arm64` with `CpuArchitecture.ARM64` or `--platform linux/amd64` with `CpuArchitecture.X86_64`. |
| Tasks start then terminate every 60–90 seconds (`Task failed ELB health checks`) | App binds to `127.0.0.1` instead of `0.0.0.0`, listens on wrong port, or `/health` returns 301/404/500. | Bind to `0.0.0.0:<containerPort>`, set `healthCheckGracePeriod` (60s+), and match `configureHealthCheck.path`. |
