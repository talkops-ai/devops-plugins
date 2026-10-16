# C4 Model & Sequence Flow Cloud Mapping Reference

When documenting complex distributed systems on AWS, structure visual deliverables across the **C4 Model hierarchy** plus **Runtime Sequence Diagrams**:

## 1. C4 Level 1 — System Context View
- **Audience**: Executives, Product Managers, Security Reviewers, External Teams.
- **Scope**: Shows the target workload as a single central box, surrounded by external personas (Web/Mobile Users, Operations Engineers, Partner Webhooks) and external SaaS/Enterprise systems (IdP/Okta, Stripe, On-Premises ERP over Direct Connect).
- **Key Annotations**: Authentication protocol (OIDC/SAML/mTLS), peak traffic volume, SLA boundary, and data sensitivity classification (PII/PCI).

## 2. C4 Level 2 — Container & AWS Service View
- **Audience**: Solutions Architects, Application Developers, DevOps/SRE.
- **Scope**: Expands the workload boundary into individual runtime containers and managed AWS services:
  - Edge & API Layer (Route 53, CloudFront, WAFv2, API Gateway / ALB)
  - Compute Layer (Lambda Functions, ECS Fargate Services, EKS Workloads, Bedrock AgentCore Runtimes)
  - Asynchronous Backbone (EventBridge Buses, SQS Queues + DLQs, Step Functions State Machines, Kinesis/MSK)
  - Data & State Layer (Aurora PostgreSQL / DSQL, DynamoDB Tables, ElastiCache Valkey, S3 Buckets / S3 Tables Iceberg)
- **Key Annotations**: Protocol + Port/Auth on every arrow (`HTTPS :443 JWT`, `PostgreSQL :5432 IAM Auth via RDS Proxy`, `SigV4 PutEvents`), plus synchronous (solid line) vs. asynchronous (dashed line) distinction.

## 3. C4 Level 4 — AWS Multi-Account & Multi-AZ Deployment View
- **Audience**: Cloud Platform, Networking, Security, and Compliance Engineers.
- **Scope**: Maps C4 Level 2 containers onto physical/logical AWS infrastructure boundaries:
  - AWS Organizations OU & Account boundaries (`Network Account`, `Workload Prod Account`, `Shared Services Account`)
  - AWS Region(s) & Availability Zones (`us-east-1a`, `us-east-1b`, `us-east-1c`)
  - VPC CIDR blocks, Public/Private/Isolated Subnets, Route Tables, NAT Gateways, Transit Gateway / Cloud WAN / VPC Lattice attachments, and Gateway/Interface VPC Endpoints (`vpce-*`).

## 4. Runtime & Security Sequence Flows (`sequenceDiagram`)
Always accompany non-trivial authentication, Saga orchestration, or async failure-recovery designs with a Mermaid `sequenceDiagram` showing:
1. Happy-path request/response with token/credential exchange (e.g., Cognito JWT $\rightarrow$ API Gateway Authorizer $\rightarrow$ Lambda $\rightarrow$ STS Role / RDS Proxy).
2. Failure/Retry/DLQ path (e.g., SQS visibility timeout $\rightarrow$ `maxReceiveCount: 3` $\rightarrow$ DLQ $\rightarrow$ CloudWatch Alarm).
