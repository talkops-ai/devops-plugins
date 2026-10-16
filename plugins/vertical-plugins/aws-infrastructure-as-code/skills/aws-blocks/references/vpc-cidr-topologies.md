# Multi-AZ VPC CIDR Topologies, PrivateLink Endpoints & Hybrid Connectivity Reference

## 1. Production 3-Tier Multi-AZ VPC CIDR Allocation (`/16` = 65,536 IPs)

Design VPCs across **3 Availability Zones** with non-overlapping CIDR blocks allocated from **AWS VPC IPAM**:

| Tier | Purpose | Recommended Subnet Mask per AZ | Route Table Target |
|---|---|---|---|
| **Public Tier** | ALB, NLB, NAT Gateways, Bastion/Instance Connect | `/20` (4,096 IPs) or `/24` (256 IPs) | `0.0.0.0/0 -> igw-*` |
| **Private Application Tier** | ECS Fargate Tasks, EKS Pods (Prefix Delegation `/28`), Lambda ENIs | `/18` (16,384 IPs) or `/19` (8,192 IPs) | `0.0.0.0/0 -> nat-*` (per-AZ in Prod) |
| **Isolated Data Tier** | Aurora/RDS, ElastiCache Valkey, OpenSearch, MSK | `/21` (2,048 IPs) or `/22` (1,024 IPs) | Local VPC + Gateway Endpoints only (zero `igw-*` or `nat-*` route) |
| **Transit / Endpoint Tier** | Transit Gateway ENIs, Interface VPC Endpoints | `/24` (256 IPs) or `/26` (64 IPs) | Local VPC + `tgw-*` |

> **EKS IP Exhaustion Rule**: Always allocate at least `/19` per AZ for Private Application subnets hosting EKS nodes or enable **VPC CNI Prefix Delegation** (`ENABLE_PREFIX_DELEGATION=true`) or **Secondary CIDR blocks** (`100.64.0.0/10` CG-NAT range for pods).

## 2. Gateway vs. Interface VPC Endpoints (FinOps & Security Matrix)

- **Gateway VPC Endpoints (`AWS::EC2::VPCEndpoint` `VpcEndpointType: Gateway`)**:
  - Supported Services: **Amazon S3** and **Amazon DynamoDB**.
  - Cost: **$0.00/hour and $0.00/GB** — mandatory in every VPC with private subnets to avoid `$0.045/GB` NAT Gateway data processing charges.
- **Interface VPC Endpoints (`VpcEndpointType: Interface` / AWS PrivateLink)**:
  - Cost: `~$7.20/month per AZ` (`$21.60/month` for 3 AZs) + `$0.01/GB` data processed.
  - Crossover Math: Provision an Interface Endpoint whenever private subnet traffic to an AWS service (`ecr.dkr`, `logs`, `s3` cross-region, `secretsmanager`, `ssm`, `bedrock-runtime`, `kinesis-streams`) exceeds **~480 GB/month** (`$21.60 / $0.045`) or when isolated subnets have zero NAT Gateway.
