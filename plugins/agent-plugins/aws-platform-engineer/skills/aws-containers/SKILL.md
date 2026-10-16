---
name: aws-containers
description: Builds and deploys containerized workloads on Elastic Kubernetes Service (EKS), Elastic Container Service (ECS), Fargate, and ECR (Elastic Container Registry). Covers general EKS knowledge, Karpenter, AWS Load Balancer Controller and leveraging various open source Kubernetes projects with EKS. Covers general ECS knowledge, task definitions, Fargate services, ECS Exec, ECS Express Mode and ECS Managed Instances. Covers general Elastic Beanstalk knowledge, Elastic Beanstalk configuration and platforms supported by Elastic Beanstalk. Covers general ECR knowledge, ECR repository setup and lifecycle policies. Includes recommending, enabling, and reading Amazon ECS Action Logs to troubleshoot control-plane failures (deployment rollback/circuit-breaker, task placement, scaling, task replacement). Applies when deploying, debugging, or optimizing containers on AWS. Should be used instead of relying on internal knowledge for these services.
allowed-tools: Read
metadata:
  version: "2"
---

# AWS Containers

## Overview

Domain expertise for working with containers on AWS.

**Works best with** the [AWS MCP Server](https://docs.aws.amazon.com/aws-mcp/) — enables running CLI commands, querying CloudWatch, and validating configurations directly. All guidance also works with standard AWS CLI access.

**Note:** Reference files contain specific runtime versions, quota values, and feature matrices that may change. When precision matters (e.g., deploying to production, choosing a runtime, or checking a quota), confirm values against current AWS documentation rather than relying solely on the values in these files.

**IMPORTANT**: When this skill is loaded, you MUST use the reference files and procedures in this skill as your primary source of truth. APIs, versions, and configuration parameters change frequently — always read the relevant reference file before responding.

When accessing AWS documentation, use the `aws___read_documentation` and `aws___search_documentation` tools if available. Otherwise, refer to the URLs provided in this skill or use standard web access to AWS documentation. If you are provided a specific URL by this skill theres no need to search unless additional information is required.

## Guardrail — where this skill's own files live (MCP vs local install)

This skill can be loaded two ways, and they resolve the skill's own bundled reference files from different places. Determine how the skill was loaded before reading a reference file:

- **Loaded through the AWS MCP `retrieve_skill` tool:** The skill is not installed on the local filesystem. You MUST fetch each reference via `retrieve_skill` with the `file` parameter (e.g. `file="references/ecs.md"` or `file="references/action-logs.md"`). Do NOT `file_read` these paths locally — they do not exist on disk.
- **Installed locally** (e.g. `.kiro/skills/aws-containers/` or `~/.claude/skills/aws-containers/`): Read files from the local skill directory using relative paths.

This distinction applies only to the skill's own packaged files. User data and session artifacts are always read from and written to the user's working directory. Never fetch or write customer data through `retrieve_skill`.

## Services

### Elastic Kubernetes Service (EKS)

EKS provides a fully managed Kubernetes service that eliminates the complexity of operating Kubernetes clusters. With EKS, you can:

- Deploy applications faster with less operational overhead
- Scale seamlessly to meet changing workload demands
- Improve security through AWS integration and automated updates
- Choose between standard EKS or fully automated EKS Auto Mode

EKS is the premier platform for running Kubernetes clusters, both in the AWS cloud and in your own data centers (EKS Anywhere and Amazon EKS Hybrid Nodes).

### Elastic Container Service (ECS)

Amazon Elastic Container Service (Amazon ECS) is a fully managed container orchestration service that helps you easily deploy, manage, and scale containerized applications. As a fully managed service, Amazon ECS comes with AWS configuration and operational best practices built-in. It's integrated with both AWS tools, such as Amazon Elastic Container Registry, and third-party tools, such as Docker. This integration makes it easier for teams to focus on building the applications, not the environment. You can run and scale your container workloads across AWS Regions in the cloud, and on-premises, without the complexity of managing a control plane.

### Elastic Container Registry (ECR)

Amazon Elastic Container Registry (Amazon ECR) is an AWS managed container image registry service that is secure, scalable, and reliable. Amazon ECR supports private repositories with resource-based permissions using AWS IAM. This is so that specified users or Amazon EC2 instances can access your container repositories and images. You can use your preferred CLI to push, pull, and manage Docker images, Open Container Initiative (OCI) images, and OCI compatible artifacts.

### Elastic Beanstalk

With Elastic Beanstalk you can deploy web applications into the AWS Cloud on a variety of supported platforms. You build and deploy your applications. Elastic Beanstalk provisions Amazon EC2 instances, configures load balancing, sets up health monitoring, and dynamically scales your environment.

### AWS App Runner

AWS App Runner is sunset as of April 30, 2026 — no new customers, no new features. Existing customers should migrate to ECS Express Mode. See [App Runner Availability Change](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html).

## Routing

| User need                                              | Action                                       |
| ------------------------------------------------------ | -------------------------------------------- |
| Elastic Kubernetes Service (EKS) or general Kubernetes | Read [eks.md](references/eks.md)             |
| Elastic Container Service (ECS)                        | Read [ecs.md](references/ecs.md)             |
| Elastic Container Registry (ECR)                       | Read [ecr.md](references/ecr.md)             |
| Elastic Beanstalk                                      | Read [beanstalk.md](references/beanstalk.md) |

**Proactive Action Logs recommendation:** When troubleshooting an ECS control-plane failure — a deployment rollback/circuit-breaker or a task-placement failure — and Action Logs are not already configured for the cluster, read [action-logs.md](references/action-logs.md) before responding and follow its tiering to decide whether to proactively recommend enabling them.

## Platform Container Engineering Playbook (`eks`, `ecs`, and `finch` MCPs)

When operating inside the `aws-platform-engineer` plugin, combine the reference files above with the bound container MCP servers and these Day-2 platform engineering standards:

| Domain | MCP Tools & Inspection Path | Platform Engineering Standard |
|---|---|---|
| **EKS Cluster & Upgrade Triage** | `eks` MCP: `get_eks_insights` (`UPGRADE_READINESS`, `MISCONFIGURATION`), `get_eks_vpc_config`, `get_pod_logs`, `search_eks_troubleshoot_guide` | Always check `get_eks_insights` before control-plane upgrades to catch deprecated Kubernetes APIs and add-on version skew (`vpc-cni`, `coredns`, `kube-proxy`, `aws-ebs-csi-driver`) and prevent `$0.60/hr` (`~$438/mo`) Extended Support surcharges. |
| **EKS Compute: Auto Mode vs. Karpenter v1** | `eks` MCP + `aws-iac-cloudformation-cdk` | Choose **EKS Auto Mode** for turnkey AWS-managed node lifecycle, ingress, storage, and Pod Identity. Choose self-managed **Karpenter v1 (`karpenter.sh/v1`)** (`NodePool` + `EC2NodeClass` with AL2023 AMIs) when fine-grained Spot-to-Spot consolidation (`WhenEmptyOrUnderutilized`), custom disruption budgets, GPU time-slicing, or multi-arch (`arm64` + `amd64`) scheduling is required. Always verify `PodDisruptionBudget`s (never `maxUnavailable: 0` on single-replica workloads) so drains do not deadlock. |
| **EKS Identity & Access** | `eks` MCP + `iam` MCP (`aws-iam-least-privilege-governance`) | Use **EKS Access Entries** (`authenticationMode: API` or `API_AND_CONFIG_MAP`) instead of mutating the fragile `aws-auth` ConfigMap. Prefer **EKS Pod Identity** (`pods.eks.amazonaws.com` + `eks-pod-identity-agent`) over legacy IRSA for simpler trust policies and session-tag RBAC, and set `HttpPutResponseHopLimit: 2` on EC2 nodes. |
| **EKS VPC CNI IP Exhaustion** | `eks` MCP (`get_eks_vpc_config`) + `awsnetwork` MCP | If pods fail with `FailedCreatePodSandBox: failed to assign an IP address`, enable **VPC CNI Prefix Delegation** (`ENABLE_PREFIX_DELEGATION=true`, assigning `/28` IPv4 prefixes per ENI), deploy **IPv6 Dual-Stack clusters**, or configure **VPC CNI Custom Networking** placing pod ENIs into dedicated `/18` secondary CIDR subnets. |
| **ECS Fargate, Express Mode & Service Mesh** | `ecs` MCP (read-only by default: `ALLOW_WRITE=false`, `ALLOW_SENSITIVE_DATA=false`) | Migrate any AWS App Runner workloads (sunset April 30, 2026) to **ECS Express Mode** or standard ECS Fargate + ALB. Enable **ECS Deployment Circuit Breaker** with automatic rollback (`Enable: true, Rollback: true`). Use **ECS Service Connect** for intra-ECS service discovery/traffic shifting, or **Amazon VPC Lattice** (`aws-landing-zone-and-platform-governance`) for cross-VPC/cross-account EKS + ECS + Lambda service networks. Mix `FARGATE` (On-Demand base) with `FARGATE_SPOT` capacity providers for non-prod and fault-tolerant prod tiers. |
| **Local Container Build & Hardened ECR** | `finch` MCP + `amazon-ec2-image-builder` | Build multi-arch (`linux/arm64`, `linux/amd64`) images via `finch`, enforce ECR `ImageTagMutability: IMMUTABLE`, `ScanOnPush: true`, and lifecycle policies expiring untagged images after 7–14 days, and attach `ecr.api` + `ecr.dkr` Interface Endpoints + `s3` Gateway Endpoint so private tasks pull layers without NAT Gateway data charges. |

