---
name: serverless-vpc-and-private-networking
description: Architect, troubleshoot, and cost-optimize VPC networking for AWS Lambda, MicroVMs, API Gateway Private Integrations, and VPC Endpoints. Enforces a FinOps decision gate prioritizing free S3/DynamoDB Gateway Endpoints, Interface Endpoint break-even analysis, and IPv6 Egress-Only Internet Gateways before provisioning expensive NAT Gateways.
---

# Serverless VPC & Private Networking (FinOps-First)

Design and troubleshoot private VPC connectivity, AWS PrivateLink endpoints, security groups, route tables, and internet egress for AWS Lambda, Lambda MicroVMs, and API Gateway while preventing unexpected NAT Gateway bill shock.

## When to Use

- A Lambda function inside a VPC times out silently when calling S3, DynamoDB, Secrets Manager, SQS, or external HTTPS APIs
- Designing private connectivity from Lambda to Amazon RDS, Aurora, ElastiCache, MSK, OpenSearch, or internal microservices
- Configuring outbound VPC/internet access for Lambda MicroVMs (Lambda Network Connectors)
- Exposing private APIs via API Gateway Private REST APIs or HTTP API VPC Links
- Auditing and eliminating unnecessary NAT Gateway hourly and per-GB data processing costs

---

## 1. The Serverless VPC FinOps Decision Gate (MANDATORY)

Attaching a Lambda function to a VPC strips its default public internet access because AWS Hyperplane ENIs sit inside your VPC subnets and never receive public IPv4 addresses—even in a "public" subnet with an Internet Gateway.

**Before provisioning a NAT Gateway (~$32.40/month per AZ + $0.045/GB processed), walk through this hierarchy in exact order:**

| Priority | Scenario | Recommended Architecture | Fixed Monthly Cost | Data Processing Cost |
|---|---|---|---|---|
| **1. No Private VPC Dependency** | Function only accesses DynamoDB, S3, SQS, SNS, EventBridge, Bedrock, or public APIs | **Do NOT attach Lambda to a VPC.** Use IAM auth, KMS, and VPC Endpoint Policies if needed. | **$0.00** | **$0.00** |
| **2. VPC Lambda -> S3 or DynamoDB** | Function is in a VPC (e.g., for RDS) and also accesses S3 or DynamoDB | **VPC Gateway Endpoint** (`com.amazonaws.<region>.s3` / `dynamodb`) attached to private route tables | **$0.00 (Free)** | **$0.00 (Free)** |
| **3. VPC Lambda -> 1 to 3 AWS Services** | Function is in a VPC and calls Secrets Manager, SQS, KMS, STS, or Step Functions | **VPC Interface Endpoint (AWS PrivateLink)** (`~$7.20/mo/AZ` + `$0.01/GB`) | ~$7.20/AZ per service | $0.01/GB |
| **4. VPC Lambda -> Public IPv6 Endpoints** | Function calls external APIs or AWS endpoints that support IPv6 | **Dual-Stack Subnet + Egress-Only Internet Gateway (EIGW)** (`AllowAllIpv6Outbound: true`) | **$0.00 (Free)** | Standard egress only (no NAT fee) |
| **5. VPC Lambda -> Public IPv4-Only Internet** | Function must call third-party IPv4-only webhooks/APIs or >4 AWS services lacking Gateway Endpoints | **NAT Gateway in Public Subnet** + Private Subnet Route (`0.0.0.0/0 -> nat-xxx`) | **~$32.40/mo per AZ** (~$65–$97/mo HA) | **$0.045/GB** |

> **Hard FinOps Guardrail:** Never silently add `AWS::EC2::NatGateway` to a SAM or CDK template without explicitly warning the user of the **~$32.40/month per AZ fixed cost** and presenting free Gateway Endpoints or IPv6 EIGW alternatives first.

---

## 2. Diagnosing VPC Connectivity Blackholes

When a VPC-attached Lambda times out with zero error logs after `START RequestId`:

1. **Inspect Function VPC Configuration**:
   ```bash
   aws lambda get-function-configuration \
     --function-name <function-name> \
     --query '{Subnets:VpcConfig.SubnetIds,SecurityGroups:VpcConfig.SecurityGroupIds,Ipv6Allowed:VpcConfig.Ipv6AllowedForDualStack}'
   ```
2. **Audit Subnet Route Tables**:
   - Check the route table associated with each Lambda subnet (`references/lambda-vpc-internet-access.md`).
   - **Broken configuration**: Lambda is placed in a subnet whose route table points `0.0.0.0/0` directly to an Internet Gateway (`igw-xxxx`). Because Lambda Hyperplane ENIs have no public IPv4 address, the IGW drops all packets silently.
   - **Valid configurations**:
     - `pl-xxxxxx` prefix list routes to free S3/DynamoDB **Gateway Endpoints** (`vpce-xxxx`)
     - Local VPC routes (`10.0.0.0/16 -> local`) to reach Interface Endpoints, RDS, or ElastiCache
     - `::/0 -> eigw-xxxx` (Egress-Only Internet Gateway for dual-stack IPv6)
     - `0.0.0.0/0 -> nat-xxxx` (NAT Gateway placed in a separate public subnet whose route table has `0.0.0.0/0 -> igw-xxxx`)
3. **Audit Security Group Rules**:
   - **Lambda SG Egress**: Must allow outbound TCP `443` (for HTTPS/VPC Interface Endpoints/S3/DynamoDB) or database ports (`5432`, `3306`, `6379`, `9092–9098`).
   - **Target SG Ingress**: The RDS/ElastiCache/MSK/Interface-Endpoint Security Group must allow inbound traffic **from the Lambda Security Group ID** (`SourceSecurityGroupId: !Ref LambdaSG`), not just an IP CIDR block.
   - **Private DNS on Interface Endpoints**: Ensure `PrivateDnsEnabled: true` is set on VPC Interface Endpoints so standard AWS SDK calls (`secretsmanager.<region>.amazonaws.com`) automatically resolve to private ENI IPs without custom endpoint URLs in code.

---

## 3. AWS SAM / CloudFormation Blueprint: Free S3 & DynamoDB Gateway Endpoints

```yaml
Resources:
  S3GatewayEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      VpcId: !Ref VpcId
      ServiceName: !Sub "com.amazonaws.${AWS::Region}.s3"
      VpcEndpointType: Gateway
      RouteTableIds:
        - !Ref PrivateRouteTableAz1
        - !Ref PrivateRouteTableAz2

  DynamoDBGatewayEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      VpcId: !Ref VpcId
      ServiceName: !Sub "com.amazonaws.${AWS::Region}.dynamodb"
      VpcEndpointType: Gateway
      RouteTableIds:
        - !Ref PrivateRouteTableAz1
        - !Ref PrivateRouteTableAz2
```

---

## 4. Dual-Stack IPv6 Outbound Internet Access (Zero NAT Gateway Cost)

To give VPC-attached Lambda functions outbound internet access to IPv6-capable endpoints without paying for a NAT Gateway:

```yaml
Resources:
  EgressOnlyIgw:
    Type: AWS::EC2::EgressOnlyInternetGateway
    Properties:
      VpcId: !Ref VpcId

  PrivateIpv6DefaultRoute:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref PrivateRouteTableAz1
      DestinationIpv6CidrBlock: "::/0"
      EgressOnlyInternetGatewayId: !Ref EgressOnlyIgw

  OrderProcessorFunction:
    Type: AWS::Serverless::Function
    Properties:
      Runtime: python3.13
      Handler: app.handler
      VpcConfig:
        SubnetIds:
          - !Ref DualStackPrivateSubnetAz1
          - !Ref DualStackPrivateSubnetAz2
        SecurityGroupIds:
          - !Ref LambdaSecurityGroup
        Ipv6AllowedForDualStack: true
```

---

## 5. Lambda MicroVMs & VPC Egress (Lambda Network Connectors)

Unlike standard Lambda functions (which have public internet access by default when not attached to a VPC), **Lambda MicroVMs have NO internet or VPC access by default** unless `VpcConfig` is configured:
- Attaching `VpcConfig` to a MicroVM function provisions **Lambda Network Connectors (LNCs)** (2 LNCs per subnet for HA, 20 Gbps bandwidth each, supporting up to 250 concurrent MicroVMs per LNC).
- Always provide at least **2 private subnets across distinct AZs** with sufficient `/24` or larger IPv4 CIDR blocks and route outbound traffic through VPC Endpoints or NAT Gateways.

---

## Reference Files

- `references/lambda-vpc-internet-access.md` — Complete AWS CLI diagnostic commands and step-by-step NAT Gateway + route table setup.
