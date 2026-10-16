# VPC, Networking, Ingress & IAM Discovery Checks

Use these read-only `awsapi` (`call_aws`) queries to inspect an AWS account before designing or synthesizing infrastructure.

## 1. Identity & Region Verification

```bash
aws sts get-caller-identity
aws configure get region
```

Always record `Account`, principal `Arn`, and target `AWS_REGION`.

## 2. VPC & Subnet Topology

### List VPCs with Name, CIDR, and Default Status

```bash
aws ec2 describe-vpcs \
  --region "${AWS_REGION}" \
  --query 'Vpcs[*].{VpcId:VpcId,CidrBlock:CidrBlock,IsDefault:IsDefault,State:State,Name:Tags[?Key==`Name`]|[0].Value}' \
  --output table
```

### List Subnets with AZ, CIDR, Available IPs, and Public/Private Indicators

```bash
aws ec2 describe-subnets \
  --region "${AWS_REGION}" \
  --query 'Subnets[*].{SubnetId:SubnetId,VpcId:VpcId,AZ:AvailabilityZone,Cidr:CidrBlock,AvailIPs:AvailableIpAddressCount,PublicIP:MapPublicIpOnLaunch,Name:Tags[?Key==`Name`]|[0].Value}' \
  --output table
```

**Sizing Check:**
- ECS Fargate, ALB, RDS/Aurora, and Elastic Beanstalk require subnets across **at least 2 Availability Zones** (ALB strictly requires $\ge 2$ AZs with $\ge 8$ free IPs per subnet).
- If an existing enterprise VPC has $< 16$ available IPs in target private subnets, flag CIDR exhaustion before deploying Fargate tasks or Lambda VPC ENIs.

### Classify Public vs. Private Subnets via Route Tables

```bash
aws ec2 describe-route-tables \
  --region "${AWS_REGION}" \
  --query 'RouteTables[*].{RouteTableId:RouteTableId,VpcId:VpcId,Subnets:Associations[*].SubnetId,Routes:Routes[*].{Dest:DestinationCidrBlock,IGW:GatewayId,NAT:NatGatewayId,TGW:TransitGatewayId}}'
```

- **Public Subnet:** Route `0.0.0.0/0` targets an Internet Gateway (`igw-*`).
- **Private Subnet with Egress:** Route `0.0.0.0/0` targets a NAT Gateway (`nat-*`) or Transit Gateway (`tgw-*`).
- **Isolated Subnet:** Local routes only (requires VPC Interface Endpoints for ECR/Logs/Secrets Manager if hosting compute).

### Inspect Existing VPC Endpoints

```bash
aws ec2 describe-vpc-endpoints \
  --region "${AWS_REGION}" \
  --query 'VpcEndpoints[*].{Id:VpcEndpointId,VpcId:VpcId,Service:ServiceName,Type:VpcEndpointType,State:State}' \
  --output table
```

## 3. DNS (Route 53) & TLS Certificates (ACM)

### Check Hosted Zones

```bash
aws route53 list-hosted-zones \
  --query 'HostedZones[*].{Id:Id,Name:Name,Private:Config.PrivateZone,Records:ResourceRecordSetCount}' \
  --output table
```

### Check Issued ACM Certificates in Target Region

```bash
aws acm list-certificates \
  --region "${AWS_REGION}" \
  --certificate-statuses ISSUED \
  --query 'CertificateSummaryList[*].{Arn:CertificateArn,Domain:DomainName,SANs:SubjectAlternativeNameSummaries,InUse:InUse}' \
  --output table
```

> **Note:** CloudFront distributions require ACM certificates in **`us-east-1`**, whereas ALB and API Gateway Regional endpoints require ACM certificates in the **workload's target region**.

## 4. IAM Execution Roles, Boundaries & CloudFormation Exports

### Check Standard Execution Roles

```bash
aws iam get-role --role-name ecsTaskExecutionRole 2>/dev/null || true
aws iam get-role --role-name ecsInfrastructureRoleForExpressServices 2>/dev/null || true
aws iam get-role --role-name aws-elasticbeanstalk-service-role 2>/dev/null || true
```

### Inspect Shared CloudFormation Stack Exports

```bash
aws cloudformation list-exports \
  --region "${AWS_REGION}" \
  --query 'Exports[*].{Name:Name,Value:Value,StackId:ExportingStackId}' \
  --output table
```

## 5. Brownfield vs. Greenfield Decision Matrix

| Condition | Recommended Action |
| --- | --- |
| CloudFormation exports or shared non-default VPC exist | **Brownfield Reuse:** Import existing VPC (`ec2.Vpc.fromLookup` in CDK or `data "aws_vpc"` in Terraform) and deploy compute into private subnets. |
| Only the default VPC exists and user wants production deployment | **Greenfield VPC:** Provision a dedicated VPC (2 AZs, public + private subnets, NAT Gateway or VPC endpoints). |
| Only the default VPC exists and user wants low-cost dev prototype | **Dev VPC / Default VPC:** Use single-NAT dev VPC or ECS Express Mode / Elastic Beanstalk default networking after disclosing tradeoffs. |
