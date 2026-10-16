---
name: aws-landing-zone-and-platform-governance
description: Architects and operates multi-account AWS Landing Zones, AWS Organizations (SCPs, RCPs, Declarative Policies), Control Tower guardrails, Shared VPCs via AWS RAM, hierarchical Amazon VPC IPAM, Amazon VPC Lattice zero-trust service networks, Route 53 Profiles, Service Quotas governance, and multi-AZ resilience with Route 53 ARC Zonal Shift and AWS Backup Vault Lock.
metadata:
  version: "2.0"
---

# AWS Multi-Account Landing Zone, Service Mesh & Platform Resilience Governance

## Purpose

In real-world engineering organizations, a Principal AWS Platform Engineer does not operate workloads inside a single flat AWS account. Platform engineering encompasses the **Multi-Account Landing Zone**, **Organization-Wide Guardrails (SCPs, RCPs, Declarative Policies)**, **Shared Network Fabric (AWS RAM, VPC IPAM, Amazon VPC Lattice, Route 53 Profiles)**, **Proactive Service Quotas Governance**, and **Multi-AZ / Multi-Region Disaster Recovery (Route 53 ARC, AWS Backup Vault Lock, AWS Resilience Hub)**.

Activate this skill whenever designing or operating multi-account foundations, cross-VPC/cross-account service connectivity, IP address management, quota exhaustion prevention, or AZ evacuation and ransomware recovery.

---

## 1. Multi-Account Landing Zone & AWS Control Tower Architecture

Structure enterprise AWS estates using the canonical AWS Security Reference Architecture (SRA) Organizational Unit (OU) hierarchy:

| Organizational Unit (OU) | Core Accounts & Purpose | Mandatory Organization Policy Guardrails |
|---|---|---|
| **Security OU** | `Log Archive` (immutable CloudTrail/Config/WAF S3 buckets with Object Lock) + `Security Tooling` (delegated admin for GuardDuty, Security Hub, Inspector, Access Analyzer, Macie) | SCP denying modification/deletion of organization CloudTrail trails, Config recorders, Security Hub standards, or S3 Object Lock retention policies. |
| **Infrastructure / Network OU** | `Network Hub` (Transit Gateway / Cloud WAN, AWS Network Firewall inspection VPC, VPC IPAM, Route 53 Profiles, Shared VPC owner via AWS RAM) + `Shared Services / Toolchain` (ECR, CodePipeline,Image Builder) | SCP enforcing approved regions (`aws:RequestedRegion`), requiring Transit Gateway `ApplianceModeSupport: enable` on inspection attachments, and restricting direct Internet Gateway creation in spoke accounts. |
| **Workloads OU (`Prod` & `NonProd`)** | Isolated per-domain or per-team application workload accounts (`payments-prod`, `payments-staging`, `checkout-prod`) | **EC2 Declarative Policies** enforcing `HttpTokens: required` (IMDSv2) and blocking public AMI/EBS snapshot sharing; **Resource Control Policies (RCPs)** enforcing S3/KMS/SQS Data Perimeters (`aws:PrincipalOrgID`); SCPs blocking root user actions and requiring KMS encryption. |
| **Sandbox / Developer OU** | Ephemeral experimentation accounts with strict budget enforcement | AWS Budgets auto-alerts/actions via `billing-cost` MCP + SCP restricting expensive instance families (e.g., `p5.*`, `u-*`) and disallowing production data access. |

---

## 2. Shared VPCs (AWS RAM), VPC IPAM & Route 53 Profiles

Eliminate VPC sprawl, overlapping CIDRs, and duplicated NAT/Endpoint charges across workload accounts:

1. **Hierarchical Amazon VPC IPAM (`AWS::EC2::IPAMPool`)**:
   - Allocate a top-level `/12` or `/14` IPAM pool in the Network Hub account, carve out regional `/16` sub-pools, and further segment into `Prod (/17)` and `NonProd (/17)` pools.
   - Mandate `Ipv4IpamPoolId` and `Ipv4NetmaskLength` on every `AWS::EC2::VPC` so no developer ever hardcodes an overlapping `10.0.0.0/16` CIDR that breaks Transit Gateway or VPC Peering later.
   - Enable **Dual-Stack IPv6** (`AmazonProvidedIpv6CidrBlock: true` or IPAM IPv6 pool) on all new VPCs to prevent EKS/container IPv4 exhaustion and allow free outbound IPv6 egress via Egress-Only Internet Gateways (`$0.00`).
2. **Shared VPC Subnets via AWS Resource Access Manager (AWS RAM)**:
   - Provision the VPC, subnets, NAT Gateways, and Transit Gateway attachments centrally in the `Network Hub` account and share private application subnets to workload accounts via `AWS::RAM::ResourceShare`.
   - Participant accounts launch ECS tasks, EKS nodes, RDS databases, and Lambda functions into the shared subnets while retaining strict account-level IAM and Security Group isolation—eliminating duplicate `$32.40/mo/AZ` NAT Gateway and `$7.20/mo/AZ` Interface Endpoint fees across dozens of accounts.
3. **Centralized DNS via Amazon Route 53 Profiles (`AWS::Route53Profiles::Profile`)**:
   - Bind Private Hosted Zones (`*.internal.example.com`), Route 53 Resolver forwarding rules (for hybrid on-prem DNS), and **Route 53 DNS Firewall** rule groups (blocking known malware/C2 domains) to a single **Route 53 Profile** shared via AWS RAM and associated with every spoke VPC.

---

## 3. Zero-Trust East-West Microservice Mesh: Amazon VPC Lattice vs. Transit Gateway

When connecting microservices across multiple VPCs, accounts, and compute runtimes (EKS pods + ECS Fargate tasks + Lambda functions):

| Requirement | Choose **Amazon VPC Lattice** | Choose **AWS Transit Gateway / Cloud WAN** |
|---|---|---|
| **Primary Layer & Granularity** | **Layer 7 (HTTP/HTTPS, gRPC, TLS Passthrough)** per-service zero-trust routing | **Layer 3 (IP Packet Routing)** full VPC-to-VPC and hybrid BGP/VPN/Direct Connect network fabric |
| **Overlapping CIDRs** | **Supported natively** — connects services across VPCs with identical `10.0.0.0/16` CIDRs without complex NAT | **Not supported natively** without Private NAT Gateway translation |
| **Identity & AuthZ** | **Fine-grained `AWS_IAM` SigV4 Auth Policies** per service/path/method (`aws:PrincipalOrgID`, `aws:PrincipalTag/team`, EKS Pod Identity role ARN) | Network-level Security Groups, NACLs, and centralized **AWS Network Firewall** (L3–L7 deep packet/SNI inspection) |
| **Canary & Weighted Traffic** | Built-in weighted target groups across EKS (`AWS Gateway API Controller`), ECS, Lambda, and ALB | Requires ALB / Route 53 / CloudFront above the L3 transport |

- **Centralized Inspection Guardrail**: Whenever routing East-West or North-South traffic through a stateful firewall appliance or **AWS Network Firewall** attached to AWS Transit Gateway, **always set `ApplianceModeSupport: enable`** on the inspection VPC's Transit Gateway attachment so symmetric return traffic stays in the same Availability Zone and is not dropped by stateful connection tracking.

---

## 4. Proactive Service Quotas & Capacity Governance

Deployment rollouts and auto-scaling events frequently fail in production due to silent regional **Service Quotas** (`InstanceLimitExceeded`, `VpcLimitExceeded`, `NatGatewayLimitExceeded`, `TooManyRequestsException`).
1. **Preflight Quota Audit (`aws-mcp`)**:
   - Before provisioning or scaling large fleets, inspect applied quotas and current usage via `aws service-quotas list-service-quotas --service-code <ec2|eks|ecs|vpc|lambda|rds>`:
     - `ec2`: Running On-Demand Standard (`A, C, D, H, I, M, R, T, Z`) vCPUs (`L-1216C47A`) and Spot vCPUs (`L-34B43A08`).
     - `vpc`: NAT Gateways per AZ (`L-FE5A380F`, default `5`), VPCs per Region (`L-F678F1CE`, default `5`), Interface Endpoints per VPC, Network Interfaces (ENIs) per region.
     - `lambda`: Concurrent executions (`L-B99A9384`, default `1,000` — note new accounts often start lower at `10`–`100`!).
2. **Proactive Quota Alarming**:
   - Create CloudWatch alarms using `AWS/Usage` (`Resource`, `Service`, `Type: Resource`, `Class`) or Service Quotas utilization metrics to alert at **75% utilization** and request increases via `aws service-quotas request-service-quota-increase` before hitting limits.

---

## 5. Multi-AZ Evacuation, Chaos Validation & Ransomware-Resilient Recovery

1. **Rapid Single-AZ Grey-Failure Evacuation (Route 53 ARC Zonal Shift & Zonal Autoshift)**:
   - Grey failures in a single Availability Zone (e.g., elevated packet loss, EBS latency degradation, or power events) often do not trip simple instance health checks.
   - Enable **Zonal Shift** and **Zonal Autoshift** (`AWS::ARCZonalShift::ZonalAutoshiftConfiguration`) on Multi-AZ Application Load Balancers (ALBs) and Network Load Balancers (NLBs) with Cross-Zone Load Balancing disabled, allowing operators (`aws arc-zonal-shift start-zonal-shift`) or AWS practice runs to drain traffic from an impaired AZ in seconds.
2. **Immutable Ransomware Recovery (AWS Backup Vault Lock & S3 Object Lock)**:
   - Centralize backups across EC2, EBS, EFS, RDS, Aurora, DynamoDB, and S3 using **AWS Backup** (`AWS::Backup::BackupPlan`) with scheduled cross-region and cross-account copy into an isolated recovery vault.
   - Enforce **AWS Backup Vault Lock** (`AWS::Backup::BackupVault` `LockConfiguration` with `ChangeableForDays` cooling-off period) and **S3 Object Lock (`COMPLIANCE` or `GOVERNANCE` mode)** on critical state and log buckets so even a compromised administrator credential cannot delete backups before retention expiry.
3. **Resilience Verification (AWS Resilience Hub & AWS FIS)**:
   - Validate target RTO/RPO against **AWS Resilience Hub** resiliency policies.
   - Before running any **AWS Fault Injection Service (FIS)** chaos experiment (AZ power interruption, EKS node termination, RDS failover, network latency injection), configure mandatory **CloudWatch Stop Conditions** (alarm-triggered automatic halt) and require explicit human approval.
