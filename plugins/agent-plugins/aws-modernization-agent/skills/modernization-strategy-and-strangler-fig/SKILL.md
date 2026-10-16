---
name: modernization-strategy-and-strangler-fig
description: "Executes 7 Rs portfolio triage, bounded-context domain decomposition, distributed data patterns (Saga, Outbox, Idempotent Consumer), and multi-account Strangler Fig incremental routing using API Gateway Canary + SigV4 forwarder Lambda + VPC Lattice + AWS RAM with CloudWatch auto-rollback. Prohibits deprecated Migration Hub Refactor Spaces."
---

# Modernization Strategy & Strangler Fig Pattern

## Overview

This skill equips Principal Modernization Architects to triage legacy workload portfolios using the **7 Rs** framework, decompose monoliths into bounded contexts, implement distributed data patterns, and execute zero-downtime, incremental traffic migration using the **Strangler Fig pattern**.

### Mandatory 2026 Architectural Guardrails

> **STRICT PROHIBITION: AWS Migration Hub Refactor Spaces**
> AWS Migration Hub Refactor Spaces closed to new customers on **November 7, 2025**. Under no circumstances should Refactor Spaces be provisioned or recommended for new environments.
> 
> **Standard 2026 AWS Architecture**:
> 1. **Amazon API Gateway** stage-level Canary deployments (0% to 100% weighted traffic routing) fronting external and internal consumers.
> 2. **VPC-attached forwarder AWS Lambda function** utilizing SigV4 request signing (`AuthType: AWS_IAM`) for secure inter-service transit.
> 3. **Amazon VPC Lattice Service Network** shared across AWS accounts via **AWS Resource Access Manager (AWS RAM)** to provide service discovery, least-privilege auth policies, and cross-VPC communication without complex Transit Gateway peering or CIDR management.
> 4. **Automated CloudWatch Alarm Rollback**: CloudWatch metric alarms monitoring `5XXError` and `Latency` on API Gateway stages trigger immediate canary dial-back to 0%.

---

## 7 Rs Portfolio Triage & Business-Case Gating

Before writing any code or provisioning infrastructure, execute the 7 Rs decision matrix to prevent costly, misaligned refactoring projects.

| Strategy | Primary Trigger Criteria | Target Architecture | AWS Modernization Services |
|---|---|---|---|
| **Retire** | Workload has zero active users, redundant business functionality, or deprecated regulatory obligations. | Decommission, archive data to S3 Glacier Flexible/Deep Archive. | S3 Lifecycle, AWS Backup |
| **Retain** | High migration risk with zero business upside; pending contract expiration > 24 months; recent heavy on-premises capital investment. | Maintain on-premises or existing hosting; reassess in 12 months. | AWS Systems Manager (hybrid nodes) |
| **Rehost** ("Lift-and-Shift") | Hard data-center exit deadline (< 6 months); M&A integration timeline; legacy COTS software without source code; stable zero-velocity systems. | Amazon EC2 with EBS gp3; exact OS/kernel mirroring. | AWS Application Migration Service (MGN) |
| **Replatform** ("Lift-and-Reshape") | Reduce OS/database license overhead; containerize VMs without code modifications; move to managed DB or directory services. | Amazon RDS / Aurora, Amazon ECS / EKS (A2C containerized), AWS App Runner, AWS Directory Service. | AWS App2Container (A2C), AWS MGN post-launch SSM, Amazon RDS |
| **Repurchase** ("Drop-and-Shop") | Commodity business capabilities (CRM, HR, payroll, issue tracking); legacy bespoke tool has standard SaaS replacement. | SaaS or AWS Marketplace partner solutions. | AWS Marketplace |
| **Refactor** ("Re-architect") | Core revenue-generating engine; deployment velocity bottlenecks; scaling limits; prohibitive proprietary licensing requiring cloud-native redesign. | Serverless (Lambda, Fargate), Event-driven (EventBridge, SQS, MSK), Aurora PostgreSQL / DSQL, Microservices. | AWS Transform (ATX), DMS Schema Conversion, VPC Lattice, API Gateway |
| **Relocate** | VMware vSphere estate needing immediate cloud adjacency without modifying VM configuration or storage formats. | VMware Cloud on AWS, Amazon EC2 Dedicated Hosts. | VMware Cloud on AWS, AWS MGN |

### The "Match, Do Not Interrogate" Protocol

When presented with a repository or environment:
1. Automatically inspect build manifests (`pom.xml`, `package.json`, `*.csproj`, `build.gradle`, `requirements.txt`, Dockerfiles, COBOL copybooks).
2. Scan for anti-patterns: embedded connection strings, local disk persistence, in-memory session state, proprietary database vendor extensions.
3. Formulate the triage assessment proactively. Present recommendations with concrete ROI justifications.

---

## Strangler Fig Routing Architecture

```
                    +-----------------------------------------+
                    |           Amazon Route 53               |
                    +-----------------------------------------+
                                         |
                                         v
                    +-----------------------------------------+
                    |    Amazon API Gateway (REST / HTTP)     |
                    |    Stage: Production (Canary: 10%)      |
                    +-----------------------------------------+
                           /                           \
         (90% Default)    /                             \   (10% Canary)
                         v                               v
          +-----------------------------+ +-----------------------------+
          | Legacy Monolith Integration | | VPC-Attached Forwarder Lambda|
          | (Direct / Existing ALB)     | | (SigV4 IAM Auth Signing)     |
          +-----------------------------+ +-----------------------------+
                         |                               |
                         v                               v
             [ On-Prem / EC2 Monolith ]   +-----------------------------+
                                          | Amazon VPC Lattice Network  |
                                          | (Shared via AWS RAM)        |
                                          +-----------------------------+
                                                         |
                                                         v
                                          +-----------------------------+
                                          | Target Microservice         |
                                          | (ECS Fargate / EKS / Lambda)|
                                          +-----------------------------+
```

### Traffic Shifting Workflow

1. **Deploy Canary Stage**: Create a canary deployment on the API Gateway stage targeting the newly extracted microservice endpoint.
2. **Initial Split (1%)**: Verify health metrics, synthetic canaries, and latency percentiles (p95/p99).
3. **Progressive Ramp**: Increment canary weight: `1% -> 10% -> 50% -> 100%`.
4. **Automated Rollback**: If CloudWatch alarms fire (`5XXError >= 1%` or `Latency >= 1.5x baseline` over two consecutive 1-minute evaluation periods), immediately trigger the rollback hook to set canary traffic percentage to `0%`.

---

## Distributed Data Patterns

Monolith decomposition requires decoupling shared databases without compromising consistency.

### 1. Database-per-Service
- Each microservice exclusively owns its datastore. Direct cross-service database access is strictly prohibited.
- Data queries across boundaries must use REST APIs, GraphQL, or asynchronous event feeds.

### 2. Transactional Outbox Pattern
- To guarantee atomicity between local database mutations and message publication, write domain events into an `outbox` table in the same local ACID transaction.
- An asynchronous relay worker (e.g., Debezium CDC via Amazon MSK Connect, or DynamoDB Streams / Aurora Lambda trigger) polls the `outbox` table and publishes events to Amazon EventBridge or Apache Kafka.

### 3. Saga Pattern (Compensating Transactions)
- For long-running distributed business transactions spanning multiple microservices, implement orchestrator-based Sagas using **AWS Step Functions**.
- Every forward step MUST define an idempotent compensating step (e.g., `ReserveInventory` -> `CancelInventoryReservation`).
- Handle failure scenarios deterministically by executing reverse compensating actions when any step fails.

### 4. Idempotent Consumer Pattern
- Enforce idempotency using unique deduplication identifiers (e.g., `idempotency_key` or event message ID).
- Store processed IDs in Amazon DynamoDB with a Time-to-Live (TTL) attribute to protect against duplicate event delivery.

---

## Reference Library

Detailed architectural blueprints, CloudFormation/CDK templates, and code samples are available in the `references/` directory:
- [references/seven-rs-decision-matrix.md](references/seven-rs-decision-matrix.md) — Exhaustive evaluation criteria, TCO calculation models, and gating checklists.
- [references/strangler-fig-lattice-apigateway.md](references/strangler-fig-lattice-apigateway.md) — Complete CloudFormation/CDK configurations for API Gateway Canary + SigV4 Lambda + VPC Lattice + AWS RAM + CloudWatch Auto-Rollback.
- [references/distributed-data-patterns.md](references/distributed-data-patterns.md) — Implementation guides for Saga Step Functions, Transactional Outbox CDC pipelines, and Idempotent Consumers.
