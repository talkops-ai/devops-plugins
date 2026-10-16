# AWS Service Quotas & Preflight Capacity Checks

Before provisioning new VPCs, NAT Gateways, Fargate services, or Lambda workloads, verify that the target account and region have sufficient quota headroom using read-only `awsapi` (`call_aws`) calls.

## 1. Critical Deployment Quotas by Service

| Service | Quota Name | Service Code | Quota Code | Typical Default | Common Failure Symptom |
| --- | --- | --- | --- | --- | --- |
| **VPC / Networking** | VPCs per Region | `vpc` | `L-F678F1CE` | 5 | `VpcLimitExceeded` during `cdk deploy` |
| **VPC / Networking** | Elastic IPs (for NAT Gateways) | `ec2` | `L-0263D0A3` | 5 | `AddressLimitExceeded` when creating Multi-AZ NAT Gateways |
| **VPC / Networking** | NAT Gateways per AZ | `vpc` | `L-FE5A380F` | 5 | `NatGatewayLimitExceeded` |
| **ECS Fargate** | Fargate On-Demand vCPU Resource Count | `fargate` | `L-3032A538` | 6–40 (new accounts) | ECS tasks stuck in `PROVISIONING` or `ResourceInitializationError` |
| **AWS Lambda** | Concurrent Executions | `lambda` | `L-B99A9384` | 1,000 (or 10 on new free-tier accounts) | `TooManyRequestsException` (HTTP 429) or rejected `ReservedConcurrentExecutions` |
| **ELB** | Application Load Balancers per Region | `elasticloadbalancing` | `L-53DA6B97` | 50 | `TooManyLoadBalancers` |
| **CloudFormation** | Stack count per Region | `cloudformation` | `L-0485CB21` | 2,000 | Stack creation rejected |

## 2. Read-Only Quota Inspection Commands

### Check Elastic IP Headroom (Critical for New VPCs with NAT Gateways)

```bash
aws service-quotas get-service-quota \
  --region "${AWS_REGION}" \
  --service-code ec2 \
  --quota-code L-0263D0A3 \
  --query 'Quota.{Name:QuotaName,Limit:Value}'

aws ec2 describe-addresses \
  --region "${AWS_REGION}" \
  --query 'length(Addresses)'
```

If `allocated_eips + planned_nat_gateways > limit`, either:
1. Reuse an existing VPC with NAT Gateways,
2. Configure `natGateways: 1` for dev environments, or
3. Request a quota increase before running `cdk deploy` / `terraform apply`.

### Check Fargate On-Demand vCPU Quota

```bash
aws service-quotas get-service-quota \
  --region "${AWS_REGION}" \
  --service-code fargate \
  --quota-code L-3032A538 \
  --query 'Quota.{Name:QuotaName,Limit:Value}'
```

### Check Lambda Account Concurrency Limit

```bash
aws lambda get-account-settings \
  --region "${AWS_REGION}" \
  --query 'AccountLimit.{ConcurrentExecutions:ConcurrentExecutions,UnreservedConcurrentExecutions:UnreservedConcurrentExecutions}'
```

> **Important:** AWS requires at least 100 unreserved concurrent executions to remain in the pool. If a newly created account has a reduced default concurrency limit (e.g., 10 concurrent executions), setting `ReservedConcurrentExecutions` on a function will fail CloudFormation deployment unless the quota is raised or `ReservedConcurrentExecutions` is omitted.

### Check CDK Bootstrap Status in Target Account/Region

Before running `cdk deploy`, verify whether the `CDKToolkit` bootstrap stack is present and up to date:

```bash
aws cloudformation describe-stacks \
  --region "${AWS_REGION}" \
  --stack-name CDKToolkit \
  --query 'Stacks[0].{Status:StackStatus,Version:Outputs[?OutputKey==`BootstrapVersion`]|[0].OutputValue}' 2>/dev/null || echo "NOT_BOOTSTRAPPED"
```

If `NOT_BOOTSTRAPPED` or version $< 21$, inform the user that `npx cdk bootstrap aws://<account>/<region>` is required and request confirmation before executing it.
