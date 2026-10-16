# Enterprise 7 Rs Migration & Strangler-Fig Modernization Playbook (SAP-C02)

## 1. The 7 Rs Migration Tooling Matrix

| Strategy ("R") | Target Outcome | Primary AWS Migration Services |
|---|---|---|
| **1. Rehost** | Lift-and-shift VMs/servers to EC2 with minimal changes | **AWS Application Migration Service (MGN)** (continuous block-level replication, non-disruptive test launches, automated cutover) |
| **2. Relocate** | Move hypervisor workloads without buying hardware or rewriting | **VMware Cloud / Red Hat OpenShift Service on AWS (ROSA)** or **EKS Anywhere $\rightarrow$ EKS** |
| **3. Replatform** | Move to managed runtime/database without changing core app architecture | **AWS Database Migration Service (DMS)** (Full Load + CDC), **ECS Fargate / Managed Instances**, **RDS / Aurora** |
| **4. Refactor / Re-architect** | Decompose monoliths into cloud-native serverless, containers, or event-driven microservices | **AWS Transform** (.NET, Mainframe, Java/VMware modernization), **EventBridge**, **Lambda**, **Step Functions**, **Aurora DSQL / DynamoDB** |
| **5. Repurchase** | Replace custom/legacy software with SaaS | **AWS Marketplace** SaaS subscriptions, **Amazon Connect**, **Amazon QuickSight** |
| **6. Retain** | Keep on-premises temporarily due to latency, hardware dongles, or compliance | **AWS Outposts**, **AWS Local Zones**, **Storage Gateway** |
| **7. Retire** | Decommission redundant/unused servers discovered during assessment | **AWS Migration Evaluator** / discovery inventory retirement |

## 2. Large-Scale Data Migration Math (Network vs. Physical Appliance)

Always calculate network transfer duration before choosing between **AWS DataSync** (online over DX/VPN) and physical transfer:
$$\text{Transfer Days} = \frac{\text{Dataset Size (TB)} \times 8,000,000\text{ Mbits/TB}}{\text{Available Bandwidth (Mbps)} \times \text{Utilization (0.8)} \times 86,400\text{ sec/day}}$$
- **Rule of Thumb**:
  - `100 TB` over a `1 Gbps` link at 80% utilization takes **~11.6 days** $\rightarrow$ use **AWS DataSync** (with TLS encryption, inline checksum verification, and incremental delta sync before cutover).
  - `500 TB+` over a `<1 Gbps` link takes **>58 days** $\rightarrow$ upgrade Direct Connect bandwidth or stage initial seed + **AWS DataSync** incremental delta cutover.

## 3. Zero-Downtime Database & Monolith Cutover (Strangler-Fig Pattern)
1. **Front Door Routing**: Place **CloudFront** or **Application Load Balancer / API Gateway** in front of the legacy system.
2. **Database Continuous CDC**: Configure **AWS DMS** in `Full Load + Ongoing Replication (CDC)` mode from the legacy database to **Aurora / DynamoDB**, or stream CDC events into **Kinesis / EventBridge Pipes**.
3. **Shadow / Canary Read Validation**: Route read traffic to the new microservice while comparing responses, then cut over write paths domain-by-domain using weighted target groups or CloudFront Continuous Deployment.
