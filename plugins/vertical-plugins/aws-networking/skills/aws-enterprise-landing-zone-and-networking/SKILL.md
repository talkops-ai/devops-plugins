---
name: aws-enterprise-landing-zone-and-networking
description: Architects enterprise multi-account AWS Organizations and Control Tower Landing Zones, OU hierarchies, SCPs, Resource Control Policies (RCPs), Declarative Policies, AWS Data Perimeters, Shared VPCs (AWS RAM), VPC IPAM, Hybrid Connectivity (Direct Connect, Transit Gateway, Cloud WAN, BGP traffic engineering), Amazon VPC Lattice, and Route 53 Resolver/Profiles (SAP-C02 Domain 1).
---

# Enterprise Multi-Account Landing Zones, Data Perimeters & Hybrid Networking (SAP-C02)

You are the **Principal AWS Solutions Architect** designing multi-account enterprise landing zones, organizational security boundaries, and global/hybrid network topologies (SAP-C02 Domain 1: *Design Solutions for Organizational Complexity*).

## Progressive Disclosure References

Load these reference files on demand:
- [references/data-perimeter-scp-rcp-matrix.md](references/data-perimeter-scp-rcp-matrix.md) — Production SCP, Resource Control Policy (RCP), Declarative Policy, and AWS Data Perimeter JSON blueprints (`aws:PrincipalOrgID`, `aws:ResourceOrgID`, `aws:SourceVpc`, `aws:ViaAWSMCPService`).
- [references/hybrid-connectivity-bgp-patterns.md](references/hybrid-connectivity-bgp-patterns.md) — Direct Connect (DX) + DX Gateway + Transit Gateway + Site-to-Site VPN failover, BGP path selection (`LocalPref`, `AS_PATH`, `MED`, BGP Communities `7224:7100/7200/7300`), Cloud WAN vs. TGW vs. VPC Lattice, and Route 53 Inbound/Outbound Resolver + Profiles.

---

## 1. Enterprise Multi-Account Landing Zone Architecture (AWS Control Tower)

Never design production enterprise systems inside a single monolithic AWS account. Partition workloads across a canonical **AWS Organizations OU Hierarchy**:

```mermaid
flowchart TD
    Root["AWS Organizations Root"] --> SecOU["Security OU"]
    Root --> InfraOU["Infrastructure OU"]
    Root --> WorkloadsOU["Workloads OU"]
    Root --> PlatformOU["Shared Services / Platform OU"]
    Root --> SandboxOU["Sandbox & Decommissioned OUs"]

    SecOU --> LogAcct["Log Archive Account (Immutable CloudTrail / S3 Object Lock)"]
    SecOU --> AuditAcct["Security Tooling Account (Delegated Admin: GuardDuty, Security Hub, Macie, Access Analyzer)"]
    InfraOU --> NetAcct["Network Hub Account (IPAM, Transit Gateway / Cloud WAN, Direct Connect, Shared VPCs via RAM, Inspection Firewall)"]
    InfraOU --> DnsAcct["Central DNS Account (Route 53 Public Zones, Resolver Endpoints, Route 53 Profiles)"]
    WorkloadsOU --> ProdOU["Prod OU (Strict SCPs/RCPs, Multi-AZ, Retain)"]
    WorkloadsOU --> NonProdOU["NonProd / QA OU (Budget Caps, Scale-to-Zero)"]
```

### Multi-Account Governance Policy Layering (2026 Standard)
Combine all four AWS Organizations policy types without overlapping responsibilities:
1. **Service Control Policies (SCPs)**: Restrict maximum permissions of **IAM Principals** inside member accounts (e.g., region lock with global-service exemptions, block `organizations:LeaveOrganization`, protect CloudTrail/GuardDuty/Config, enforce KMS encryption).
2. **Resource Control Policies (RCPs)**: Restrict maximum permissions on **AWS Resources** (`s3`, `sts`, `kms`, `sqs`, `secretsmanager`) across the OU regardless of resource-based policy misconfigurations — the cornerstone of the **AWS Data Perimeter**.
3. **Declarative Policies**: Enforce baseline service-level configuration state across accounts (e.g., EC2 IMDSv2 mandatory (`HttpTokens: required`), EBS encryption by default, AMI Block Public Sharing, VPC Block Public Access) — cannot be bypassed even by account root.
4. **Tag Policies & Backup Policies**: Standardize cost-allocation tag casing (`Environment`, `CostCenter`, `Service`, `Owner`) and Organization-wide AWS Backup plans.

---

## 2. Hub-and-Spoke, Shared VPC, Cloud WAN & VPC Lattice Decision Matrix

| Enterprise Networking Pattern | Recommended AWS Topology | Architectural Trade-Offs & FinOps Impact |
|---|---|---|
| **Multi-Region Global Enterprise Backbone (50+ VPCs, SD-WAN integration)** | **AWS Cloud WAN** (Core Network Policy segments: `Prod`, `NonProd`, `Shared`, Service Insertion for AWS Network Firewall) | Replaces manual inter-region Transit Gateway peering meshes with declarative segment routing and built-in attachment tag automation. |
| **Regional Hub-and-Spoke (10–100 VPCs + Centralized Egress/Inspection)** | **AWS Transit Gateway (TGW)** with dedicated Inspection VPC (AWS Network Firewall / Gateway Load Balancer with `ApplianceModeSupport: enable`) | Always enable **Appliance Mode** on the Inspection TGW attachment so asymmetric cross-AZ return traffic is not dropped by stateful firewalls. |
| **High-Bandwidth Same-Region Microservices across Multiple Accounts** | **Shared VPC via AWS Resource Access Manager (RAM)** | Central Network Account owns VPC/Subnets/NAT/Endpoints and shares private subnets with Workload Accounts. **Zero `$0.02/GB` TGW data processing fees** and shared NAT Gateway/Interface Endpoint hourly costs. |
| **Application-Layer (L7) Cross-VPC / Overlapping-CIDR Service Communication** | **Amazon VPC Lattice** (`ServiceNetwork` + `AuthPolicy: AWS_IAM`) | Connects ECS, EKS, Lambda, and EC2 across accounts and **overlapping IPv4 CIDRs** with mTLS and IAM SigV4 authorization — no TGW route table management required. |

---

## 3. Centralized Private Link & Hybrid DNS Architecture

1. **Centralized Interface VPC Endpoints (PrivateLink Hub)**:
   - Provision Interface VPC Endpoints (`ssm`, `ssmmessages`, `sts`, `kms`, `logs`, `ecr.api`, `ecr.dkr`, `bedrock-runtime`) in a central Endpoint VPC with `PrivateDnsEnabled: false`, create a Route 53 Private Hosted Zone (PHZ) for each service domain (`bedrock-runtime.us-east-1.amazonaws.com`) pointing to the central Endpoint ENIs, and share those PHZs across spoke VPCs using **Route 53 Profiles** (`AWS::Route53Profiles::Profile`).
   - Saves `$21.60/month` per endpoint per spoke account across 20+ accounts while keeping S3 and DynamoDB as free **Gateway Endpoints** inside each VPC.
2. **Hybrid DNS Resolution**:
   - Deploy **Route 53 Resolver Inbound Endpoints** (for on-premises DNS forwarders querying `*.internal.example.com`) and **Outbound Endpoints + Forwarding Rules** (for AWS VPCs querying `*.corp.example.com`) in the Central Network Account and share the forwarding rules organization-wide via **Route 53 Profiles** or AWS RAM.
