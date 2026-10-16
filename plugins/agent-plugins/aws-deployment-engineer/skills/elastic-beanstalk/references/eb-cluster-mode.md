# Elastic Beanstalk Single-Instance vs. Load-Balanced Cluster Mode

## 1. Architecture Comparison

| Capability | Single-Instance Mode (`EnvironmentType=SingleInstance`) | Load-Balanced Cluster Mode (`EnvironmentType=LoadBalanced`) |
| --- | --- | --- |
| **Topology** | 1 EC2 instance with an Elastic IP (no Load Balancer) | Auto Scaling Group (`min..max` EC2 instances) in private subnets behind a Multi-AZ ALB |
| **Approx. Monthly Base Cost (us-east-1)** | ~$16–20/mo (`1x t3.small` + gp3 EBS) | ~$38–45/mo (Dev `1x t3.small` + ALB) / ~$150–200/mo (Prod `2–4x t3.medium` + ALB) |
| **HTTPS / TLS Termination** | Requires on-instance certbot or CloudFront in front | Native ACM certificate termination on ALB listener (Port 443) |
| **Zero-Downtime Deploys** | No (brief interruption during `AllAtOnce` update) | Yes (`RollingWithAdditionalBatch`, `Immutable`, or `TrafficSplitting`) |
| **When to Choose** | Strictly budget-constrained dev/sandbox prototypes or single-node internal tools | Default for all web apps needing ACM HTTPS, private subnet placement, or production HA |

## 2. Progressive Deployment Policies (Cluster Mode)

Configure `aws:elasticbeanstalk:command` -> `DeploymentPolicy`:

| Policy | Rollout Mechanism | Rollback Speed | Recommended Tier |
| --- | --- | --- | --- |
| `AllAtOnce` | Updates all instances simultaneously; brief service interruption | Fast (redeploy previous version) | Dev (`min=1, max=1`) |
| `RollingWithAdditionalBatch` | Launches an extra batch first so full capacity is maintained throughout rollout | Fast | Production standard |
| `Immutable` | Launches a parallel Auto Scaling Group with the new version and swaps only after health checks pass | Instant (terminates new ASG on failure) | Mission-critical production |
| `TrafficSplitting` | Shifts a canary percentage (e.g., `10%`) of ALB traffic for `EvaluationTime` minutes before full cutover | Instant ALB weight revert on enhanced health failure | High-traffic production |

## 3. Multi-AZ VPC Placement Options (`aws:ec2:vpc`)

Always place cluster instances in private subnets and the ALB in public subnets across at least 2 Availability Zones:

```json
[
  {
    "Namespace": "aws:ec2:vpc",
    "OptionName": "VPCId",
    "Value": "vpc-0123456789abcdef0"
  },
  {
    "Namespace": "aws:ec2:vpc",
    "OptionName": "ELBSubnets",
    "Value": "subnet-publicAz1,subnet-publicAz2"
  },
  {
    "Namespace": "aws:ec2:vpc",
    "OptionName": "Subnets",
    "Value": "subnet-privateAz1,subnet-privateAz2"
  },
  {
    "Namespace": "aws:ec2:vpc",
    "OptionName": "AssociatePublicIpAddress",
    "Value": "false"
  }
]
```

## 4. Worker Environment Tier (`Tier: Worker / SQS/HTTP`)

When deploying background job processors:
- Set `--tier Name=Worker,Type=SQS/HTTP`.
- Configure `aws:elasticbeanstalk:sqsd` options (`WorkerQueueURL`, `HttpPath`, `HttpConnections`, `InactivityTimeout`, `VisibilityTimeout`, `RetentionPeriod`, `MaxRetries`).
- Attach a Dead-Letter Queue (DLQ) to capture messages that fail processing after `MaxRetries`.
