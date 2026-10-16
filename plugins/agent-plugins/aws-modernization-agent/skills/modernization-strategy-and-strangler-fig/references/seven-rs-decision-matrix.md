# 7 Rs Modernization Decision Matrix & Portfolio Gating

## Overview

The 7 Rs framework categorizes legacy applications into actionable migration and modernization pathways. A Principal AWS Modernization Solutions Architect must enforce strict business-case gating to prevent unnecessary, risky refactoring where replatforming or rehosting delivers superior return on investment.

---

## 1. Decision Matrix & Selection Flowchart

```
                          [ Legacy Workload ]
                                  |
                   Is the application actively used?
                             /          \
                           No            Yes
                          /                \
                     [ RETIRE ]       Does it deliver differentiating
                                      business value or customer IP?
                                         /               \
                                       No                 Yes
                                      /                     \
                      Is there a COTS SaaS            Is there an urgent
                      or Marketplace product?         datacenter exit deadline?
                           /          \                     /          \
                         Yes           No                 Yes           No
                         /              \                 /              \
                   [ REPURCHASE ]    [ RETAIN ]     [ REHOST ]    Can we containerize or
                                                    (AWS MGN)     move to managed DB without
                                                                  rewriting business logic?
                                                                      /          \
                                                                    Yes           No
                                                                    /              \
                                                             [ REPLATFORM ]   [ REFACTOR ]
                                                             (A2C / RDS)      (Strangler Fig / ATX)
```

---

## 2. In-Depth Evaluation Criteria

### 2.1 Retire
- **Definition**: Decommissioning redundant, duplicate, or unutilized workloads.
- **Indicators**:
  - Application CPU utilization < 1% sustained across 90 days.
  - Zero active authenticated sessions in identity logs.
  - Source data replicated elsewhere in the corporate data lake.
- **AWS Execution Protocol**:
  1. Export compliance data to Amazon S3.
  2. Apply S3 Lifecycle rule to transition to S3 Glacier Deep Archive (costing ~$0.00099 per GB/month).
  3. Delete compute resources, DNS records, and EBS volumes.

### 2.2 Retain
- **Definition**: Keeping applications on-premises or in current hosting with zero modifications.
- **Indicators**:
  - Legacy mainframe/AS400 hardware tied to specialized non-IP protocols.
  - Multi-year capital depreciation remaining on physical infrastructure.
  - Workload scheduled for vendor-managed end-of-life within 6–12 months.
- **AWS Execution Protocol**:
  - Enroll hybrid servers into AWS Systems Manager via SSM Agent to establish unified patch and compliance visibility.

### 2.3 Rehost ("Lift-and-Shift")
- **Definition**: Moving applications to AWS without modifying the underlying OS, kernel, or application code.
- **Indicators**:
  - Urgent datacenter lease termination (< 6 months).
  - Rapid M&A migration requirements.
  - Legacy third-party software (COTS) where source code is unavailable.
  - Stable, zero-velocity applications where code modifications introduce unacceptable regression risks.
- **AWS Execution Protocol**:
  - Use **AWS Application Migration Service (AWS MGN)** for continuous block-level block replication.
  - Target: Amazon EC2 with EBS gp3 storage and AWS Systems Manager management.

### 2.4 Replatform ("Lift-and-Reshape")
- **Definition**: Moving to managed AWS services or containerizing without rewriting core application logic.
- **Indicators**:
  - Commercial database licensing overhead (Oracle / SQL Server) can be reduced by moving to Amazon RDS.
  - Web applications (IIS / Tomcat / WebLogic) running on static VMs can be packaged as Docker containers.
- **AWS Execution Protocol**:
  - Compute: **AWS App2Container (A2C)** to package VMs into Amazon ECS or Amazon EKS (Standard / Auto Mode).
  - Database: Native backup/restore or DMS to Amazon RDS (PostgreSQL/MySQL/SQL Server).

### 2.5 Repurchase ("Drop-and-Shop")
- **Definition**: Replacing custom legacy systems with cloud-native SaaS or AWS Marketplace solutions.
- **Indicators**:
  - Non-core business operations (HR, CRM, Helpdesk, Billing).
  - Legacy bespoke systems requiring high maintenance.
- **AWS Execution Protocol**:
  - Subscribe via AWS Marketplace for consolidated billing and GovCloud/FedRAMP compliance.

### 2.6 Refactor ("Re-architect")
- **Definition**: Decomposing monoliths, rewriting legacy codebases, and adopting serverless or microservices.
- **Indicators**:
  - Deployment velocity constraints directly impacting time-to-market.
  - Scaling bottlenecks where one hot module forces scaling the entire monolith.
  - End-of-life proprietary frameworks (.NET Framework 4.x, Java 8, Python 2.7) preventing security compliance.
- **AWS Execution Protocol**:
  - Strangler Fig routing via Amazon API Gateway and Amazon VPC Lattice.
  - Automated code/SDK transformations via AWS Transform (`aws-transform-mcp`).
  - Target: AWS Lambda, Amazon ECS Fargate, Amazon Aurora PostgreSQL / DSQL.

### 2.7 Relocate
- **Definition**: Migrating VMware vSphere clusters to VMware Cloud on AWS without modifying VM formats.
- **Indicators**:
  - VMware-specific operational tooling, NSX network policies, and administrative staff skills that must be preserved.
- **AWS Execution Protocol**:
  - VMware HCX vMotion live migration into VMware Cloud on AWS software-defined data centers (SDDCs).

---

## 3. TCO Calculation & Right-Sizing Gating Checklist

Before approving a Refactor business case, run the following quantitative gating checklist:

1. **Calculate Baseline Operational Cost (Run Cost)**:
   - Current infrastructure cost (compute, storage, network) + hypervisor licenses + OS licenses + database licenses.
2. **Estimate Modernization Effort (Migration Cost)**:
   - Engineering hours x loaded contractor/employee rate + temporary dual-run cloud costs + tooling licenses.
3. **Projected Target Cost**:
   - Query AWS Cost Explorer and Pricing API for target compute/database sizing.
   - Apply AWS Compute Optimizer recommendations to size EC2/Fargate instances to > 65% target utilization.
4. **ROI Hurdle Rate**:
   - Payback period must be < 24 months for Refactoring. If payback period > 36 months, mandate Replatforming or Rehosting first.
