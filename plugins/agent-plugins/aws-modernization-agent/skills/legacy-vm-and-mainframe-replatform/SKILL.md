---
name: legacy-vm-and-mainframe-replatform
description: "Guides legacy VM containerization via AWS App2Container (A2C 5-stage workflow for Java and .NET to ECS, EKS Standard/Auto Mode, App Runner) standalone and via AWS MGN SSM automation. Directs mainframe modernization via AWS Transform (aws-transform-mcp), comparing AWS Blu Age automated refactoring vs Rocket Software replatforming with EBCDIC-to-ASCII and dataset conversion. Prohibits M2 Managed Runtime for new customers."
---

# Legacy VM & Mainframe Replatforming

## Overview

Enterprises running legacy virtual machine estates (Windows Server / IIS, Linux / Tomcat / JBoss / WebLogic) and on-premises mainframes (IBM z/OS, Unisys) face high operating costs, scarce specialized talent, and slow deployment lifecycles.

This skill equips Principal Modernization Architects to:
1. Containerize legacy virtual machines using **AWS App2Container (A2C)** without source code modification, deploying to **Amazon ECS**, **Amazon EKS (Standard & EKS Auto Mode)**, or **AWS App Runner**.
2. Automate post-migration containerization during lift-and-shift using **AWS Application Migration Service (AWS MGN)** Systems Manager post-launch automation.
3. Evaluate and replatform stateful, sessionful, or long-running (up to 8-hour) workloads onto **AWS Lambda MicroVMs** with `/ready` and `/validate` snapshot restore hooks.
4. Modernize mainframe estates using **AWS Transform for mainframe (`aws-transform-mcp`)**, comparing automated refactoring via **AWS Blu Age** against replatforming via **Rocket Software** (formerly Micro Focus).

### Mandatory 2026 Architectural Guardrail

> **STRICT PROHIBITION: AWS Mainframe Modernization (M2) Managed Runtime Environment**
> The standalone AWS Mainframe Modernization (M2) Managed Runtime Environment experience is **closed to new customers**.
> 
> **Standard 2026 AWS Mainframe Modernization Architecture**:
> Route all mainframe modernization workflows through **AWS Transform for mainframe (`aws-transform-mcp`)**, selecting between:
> 1. **Automated Refactoring (AWS Blu Age)**: Automatically transforms legacy COBOL, PL/I, CICS, and JCL into modular, cloud-native Java and Spring Boot microservices deployed on Amazon ECS or Amazon EKS.
> 2. **Replatforming (Rocket Software / Micro Focus Enterprise Server)**: Preserves legacy COBOL/PL/I code while moving execution to AWS compute, automating EBCDIC-to-ASCII conversion, and mapping sequential, indexed (VSAM), or relative datasets to Amazon EFS, Amazon FSx, or Amazon RDS.

---

## 1. AWS App2Container (A2C) 5-Stage Containerization Workflow

```
[ Stage 1: init ]           Configure workspace S3 bucket, AWS region, and KMS encryption key.
         |
         v
[ Stage 2: inventory ]      Enumerate running Java and .NET (IIS) web applications on the VM.
         |
         v
[ Stage 3: analyze ]        Inspect application runtime, OS dependencies, network ports,
         |                  and generate customizable `analysis.json`.
         v
[ Stage 4: containerize ]   Build OCI/Docker container image in Amazon ECR with AWS base image.
         |
         v
[ Stage 5: generate ]       Generate AWS CloudFormation or CDK templates for deployment
                            to Amazon ECS, Amazon EKS, or AWS App Runner (`generate app-deployment`).
```

### CLI Quick Reference

```bash
# 1. Initialize A2C workspace
app2container init --workspace-directory /var/app2container --target-bucket my-modernization-bucket

# 2. Inventory processes
app2container inventory

# 3. Analyze discovered application
app2container analyze --application-id java-tomcat-abc12345

# 4. Containerize application (builds image & pushes to ECR)
app2container containerize --application-id java-tomcat-abc12345

# 5. Generate target deployment artifacts (ECS Fargate or EKS)
app2container generate app-deployment --application-id java-tomcat-abc12345 --target-runtime ecs
```

---

## 2. AWS MGN Post-Launch SSM Containerization

For large-scale VM migrations, integrate A2C directly into the **AWS Application Migration Service (AWS MGN)** replication pipeline:
- Attach the `ApplicationTransformationAnalyzerPolicy` IAM role to the target EC2 launch template.
- Configure the SSM Automation Document `AWSMGN-App2Container-Containerize` as a post-launch action to automatically trigger inventory, analysis, and containerization upon cutover.

---

## 3. Stateful & Long-Lived Workloads: AWS Lambda MicroVMs

For legacy services that require:
- Up to 8-hour execution lifetimes (e.g. batch jobs, long-running reports)
- Stateful in-memory caches or session affinity
- Listening on arbitrary TCP/WebSocket/gRPC ports
- Sub-second memory and disk snapshot restore on Amazon Linux 2023

Load the `aws-lambda-microvms` skill and package container images with lifecycle hooks:
- `/ready`: Executed when the service has initialized its in-memory state and is ready for snapshot capture.
- `/validate`: Executed upon snapshot restoration to verify socket connectivity, database connection pools, and hardware clock drift before processing requests.

---

## 4. Mainframe Modernization: Blu Age vs. Rocket Software

| Dimension | AWS Blu Age (Automated Refactoring) | Rocket Software (Replatforming) |
|---|---|---|
| **Core Philosophy** | Transform legacy code into modern, maintainable Java / Spring Boot. | Preserve existing COBOL / PL/I source code; modernize runtime infrastructure. |
| **Source Languages** | COBOL, PL/I, Natural, RPG, JCL, CICS, IMS-DB. | COBOL, PL/I, JCL, CICS, Assembler. |
| **Output Code** | Cloud-native Java 17/21, Spring Boot, Angular/React UI. | Preserved COBOL/PL/I compiled for Linux x86 or ARM64 (Graviton). |
| **Target Compute** | Amazon ECS, Amazon EKS (Standard / Auto Mode), AWS Fargate. | Amazon EC2, Amazon ECS Fargate. |
| **Data Architecture** | Heterogeneous relational migration (VSAM/Db2 to Aurora PostgreSQL). | VSAM mapped to Rocket indexed files on Amazon EFS / FSx or relational DB. |
| **Data Encoding** | Complete ASCII conversion. | Dynamic EBCDIC <-> ASCII conversion utilities. |
| **Ideal Candidate** | High-velocity applications where future feature evolution is strategic. | Stable batch processing systems with low feature change frequency. |

---

## Reference Library

Comprehensive execution procedures and configuration templates are available in `references/`:
- [references/app2container-workflow.md](references/app2container-workflow.md) — Detailed 5-stage A2C workflow, `analysis.json` parameters, and deployment targets.
- [references/mgn-post-launch-containerization.md](references/mgn-post-launch-containerization.md) — AWS MGN post-launch Systems Manager automation setup and IAM policies.
- [references/mainframe-blu-age-refactoring.md](references/mainframe-blu-age-refactoring.md) — AWS Blu Age transformation lifecycle, Spring Boot architecture, and JCL-to-Step Functions orchestration.
- [references/mainframe-rocket-software-replatform.md](references/mainframe-rocket-software-replatform.md) — Rocket Software Enterprise Server deployment, EBCDIC-to-ASCII collation, and VSAM dataset mapping.
