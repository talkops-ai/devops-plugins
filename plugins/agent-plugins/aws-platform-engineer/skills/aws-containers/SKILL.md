---
name: aws-containers
description: "Builds and deploys containerized workloads on Elastic Kubernetes Service (EKS), Elastic Container Service (ECS), Fargate, and ECR (Elastic Container Registry). Covers general EKS knowledge, Karpenter, AWS Load Balancer Controller and leveraging various open source Kubernetes projects with EKS. Covers general ECS knowledge, task definitions, Fargate services, ECS Exec, ECS Express Mode and ECS Managed Instances. Covers general Elastic Beanstalk knowledge, Elastic Beanstalk configuration and platforms supported by Elastic Beanstalk. Covers general ECR knowledge, ECR repository setup and lifecycle policies. Includes recommending, enabling, and reading Amazon ECS Action Logs to troubleshoot control-plane failures (deployment rollback/circuit-breaker, task placement, scaling, task replacement). Applies when deploying, debugging, or optimizing containers on AWS. Should be used instead of relying on internal knowledge for these services. Query live AWS state via MCP tools only (never raw aws CLI)."
allowed-tools: Read
metadata:
  version: "2"
---

# AWS Containers

> **MCP-Only Live AWS Execution:** Execute ALL live AWS API discovery, account/region preflight checks (`sts:GetCallerIdentity`), stack/cluster/resource inspection, pricing (`awspricing`/`billing`), IaC validation (`awsiac`), and documentation lookups (`awsknowledge`) strictly via connected MCP tools (`aws-mcp` `aws___run_script` `call_boto3`, `awsknowledge`, `awsiac`, `awspricing`, `eks`, `ecs`, `cloudwatch`) — **never invoke raw `aws ...` CLI commands in shell (`run_command`)**. Offline local linters/synthesizers (`cdk synth`, `terraform validate`, `python3`) may run locally without mutating live AWS.

## Overview

Domain expertise for working with containers on AWS.

**Works best with** the connected AWS MCP servers (`aws-mcp`, `eks`, `ecs`, `finch`, `cloudwatch`, `awspricing`, `awsiac`, `awsknowledge`) — always execute live AWS discovery, telemetry, pricing, and documentation lookups through connected MCP tools (`call_mcp_tool`) rather than running raw `aws`, `eksctl`, `kubectl`, `helm`, or `docker` CLI commands in the shell (`run_command`). Present CLI commands as Markdown code blocks in your response for the operator to run.

**IMPORTANT — Authoritative Local Reference Files First**: When this skill is loaded, you MUST read and rely on the local `references/*.md` files in this skill as your primary, authoritative source of truth. **Do NOT** call `aws___read_documentation` or `aws___search_documentation` to fetch URLs linked inside `references/*.md` when the local reference files already answer the question — reserve `awsknowledge` (`aws___search_documentation` / `aws___read_documentation`, max 1–2 focused calls) strictly for edge-case topics not covered in the local `references/*.md` files.

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

Combine the reference files above with the bound container MCP servers (`eks`, `ecs`, `finch`, `aws-mcp`, `cloudwatch`, `awspricing`, `awsiac`, `awsknowledge`) and these Day-2 platform engineering standards (if no local reference matches an edge-case question, immediately query `awsknowledge` via `aws___search_documentation` / `aws___read_documentation`):

| Domain | MCP Tools & Inspection Path | Platform Engineering Standard |
|---|---|---|
| **EKS Cluster & Upgrade Triage** | `eks` MCP: `get_eks_insights` (`UPGRADE_READINESS`, `MISCONFIGURATION`), `get_eks_vpc_config`, `get_pod_logs`, `search_eks_troubleshoot_guide` | Always check `get_eks_insights` before control-plane upgrades to catch deprecated Kubernetes APIs and add-on version skew (`vpc-cni`, `coredns`, `kube-proxy`, `aws-ebs-csi-driver`) and prevent `$0.60/hr` (`~$438/mo`) Extended Support surcharges. |
| **EKS Compute: Auto Mode vs. Karpenter v1** | `eks` MCP + `eks-karpenter-autoscaling` + `aws-iac-cloudformation-cdk` | Load **`eks-karpenter-autoscaling`** for full Karpenter v1 & EKS Auto Mode bootstrap (Pod Identity `KarpenterControllerRole`, `EC2_LINUX` Access Entry, SQS Spot Interruption Queue + 4 EventBridge rules), multi-arch Graviton + x86 `NodePool`/`EC2NodeClass` authoring, `SpotToSpotConsolidation`, CAS→Karpenter migration, and `KP-01..16` / `:8080/metrics` audits. |
| **EKS Identity & Access** | `eks` MCP + `iam` MCP (`aws-iam-least-privilege-governance`) | Use **EKS Access Entries** (`authenticationMode: API` or `API_AND_CONFIG_MAP`) instead of mutating the fragile `aws-auth` ConfigMap. Prefer **EKS Pod Identity** (`pods.eks.amazonaws.com` + `eks-pod-identity-agent`) over legacy IRSA for simpler trust policies and session-tag RBAC, and set `HttpPutResponseHopLimit: 2` on EC2 nodes. |
| **EKS VPC CNI IP Exhaustion** | `eks` MCP (`get_eks_vpc_config`) + `awsnetwork` MCP | If pods fail with `FailedCreatePodSandBox: failed to assign an IP address`, enable **VPC CNI Prefix Delegation** (`ENABLE_PREFIX_DELEGATION=true`, assigning `/28` IPv4 prefixes per ENI), deploy **IPv6 Dual-Stack clusters**, or configure **VPC CNI Custom Networking** placing pod ENIs into dedicated `/18` secondary CIDR subnets. |
| **ECS Fargate, Express Mode & Service Mesh** | `ecs` MCP (read-only by default: `ALLOW_WRITE=false`, `ALLOW_SENSITIVE_DATA=false`) | Migrate any AWS App Runner workloads (sunset April 30, 2026) to **ECS Express Mode** or standard ECS Fargate + ALB. Enable **ECS Deployment Circuit Breaker** with automatic rollback (`Enable: true, Rollback: true`). Use **ECS Service Connect** for intra-ECS service discovery/traffic shifting, or **Amazon VPC Lattice** (`aws-landing-zone-and-platform-governance`) for cross-VPC/cross-account EKS + ECS + Lambda service networks. Mix `FARGATE` (On-Demand base) with `FARGATE_SPOT` capacity providers for non-prod and fault-tolerant prod tiers. |
| **Local Container Build & Hardened ECR** | `finch` MCP + `amazon-ec2-image-builder` | Build multi-arch (`linux/arm64`, `linux/amd64`) images via `finch`, enforce ECR `ImageTagMutability: IMMUTABLE`, `ScanOnPush: true`, and lifecycle policies expiring untagged images after 7–14 days, and attach `ecr.api` + `ecr.dkr` Interface Endpoints + `s3` Gateway Endpoint so private tasks pull layers without NAT Gateway data charges. |

## Mandatory Execution, Guardrail & Vague-Workload Rules

1. **MCP-Only Execution (Zero Raw AWS CLI in Shell):** When querying live AWS state, pricing, telemetry, or documentation, ALWAYS use connected MCP tools (`aws-mcp` `aws___call_aws`, `eks`, `ecs`, `finch`, `cloudwatch`, `awspricing`, `awsiac`, `awsknowledge`). NEVER invoke raw `aws ...`, `eksctl ...`, `kubectl ...`, `helm ...`, or `docker ...` commands via `run_command` / `Bash`.
2. **Strictly Read-Only & Secret Safety (`aws-mutation-gate.py`, `secret-safety.py`):** Never execute mutating operations (`eksctl upgrade/create/delete`, `kubectl delete/apply/patch/drain`, `helm install/upgrade/uninstall`, `aws ecs update-service`, `cdk deploy`) or fetch plaintext secrets (`aws secretsmanager get-secret-value`, `curl localhost:2773/secretsmanager/get`). When asked to fetch a secret value, refuse and recommend `DescribeSecret` metadata inspection and runtime secret injection (`secrets.valueFrom` or Secrets Store CSI Driver).
3. **Honest Zero-Resource Reporting:** When querying live AWS state in the target region and `0` EKS clusters, ECS clusters, or ECR repositories exist, report `0` resources honestly without fabricating cluster ARNs, task IDs, or log lines, and then provide the complete architectural or diagnostic runbook.
4. **Vague Workload Sizing & Cost Guard:** If a user asks for container sizing (vCPU, memory, node/task count, Karpenter `NodePool` limits) or monthly dollar cost estimates without providing concrete workload metrics (CPU/memory utilization, replica/task count, or RPS), refuse to fabricate or guess specific sizing numbers or monthly dollar totals; list the required metrics (`CPUUtilized`, `MemoryUtilized`, `pod_cpu_utilization`, `pod_memory_working_set`, RPS) and explain how to gather them from CloudWatch Container Insights / Prometheus before sizing.
5. **`awsknowledge` Edge-Case Fallback:** Only when no local `references/*.md` covers a niche or edge-case feature (such as EKS Hybrid Nodes), query `awsknowledge` (`aws___search_documentation` / `aws___read_documentation` — max 1–2 focused calls) and answer directly. Never crawl external documentation URLs for topics already covered in local `references/*.md`.
6. **Fast, Bounded Pricing & Discovery Calls (Avoid Tool Loops):**
   - When querying `awspricing` (`get_pricing`), make **at most 2–3 targeted `get_pricing` calls** with explicit `filters` (e.g., `service_code="AmazonEKS"` with `Field="operation", Type="EQUALS", Value="CreateOperation"` or `service_code="AmazonECS"` with `Field="cputype", Type="EQUALS", Value="perCPU"`). Never call unfiltered `get_pricing` or make more than 3 pricing calls total — compute the monthly TCO comparison immediately after 1–3 filtered pricing lookups (noting EKS Standard Control Plane is `$0.10/hr` / `~$73/month`, ECS Control Plane is `$0/month`, and ECS Managed Instances / EKS Auto Mode charge a per-instance management fee in addition to EC2 instance rates).
   - When inspecting live AWS resources in the target region, make 1–3 fast read-only MCP calls (`eks`, `ecs`, or `aws-mcp` `aws___call_aws` for `eks list-clusters`, `ecs list-clusters`, `ecr describe-repositories`) and immediately write the full architectural response once `0` resources are confirmed.

