# AWS App2Container (A2C) 5-Stage Modernization Workflow

## 1. Overview

**AWS App2Container (A2C)** is a specialized command-line modernization tool designed to containerize existing legacy applications running on Windows and Linux virtual machines (VMs) without requiring application source code changes. 

A2C automatically analyzes running application processes on VMs, extracts runtime dependencies, packages the application into Open Container Initiative (OCI) / Docker images, registers them in Amazon Elastic Container Registry (Amazon ECR), and generates complete Infrastructure as Code (IaC) deployment pipelines targeting:
- **Amazon Elastic Container Service (Amazon ECS)** with AWS Fargate or Amazon EC2 compute.
- **Amazon Elastic Kubernetes Service (Amazon EKS)** including both Standard and **EKS Auto Mode**.
- **AWS App Runner** for fully managed web applications and microservices.

---

## 2. Supported Workloads & Prerequisites

### 2.1 Supported Application Platforms

| Operating System | Application Runtime | Application Server / Host | Target Output |
|---|---|---|---|
| **Linux** (Amazon Linux 2/2023, RHEL, CentOS, Ubuntu, SLES) | Java 7, 8, 11, 17, 21 | Apache Tomcat (7+), Red Hat JBoss EAP (6+), Oracle WebLogic (12c+), Spring Boot standalone fat JAR/WAR | Linux x86_64 or ARM64 (Graviton) container images |
| **Windows** (Windows Server 2012, 2012 R2, 2016, 2019, 2022) | .NET Framework 3.5, 4.x | Microsoft IIS (7.5+), Windows Services, WCF | Windows Server Core / Nano Server container images |

### 2.2 System Prerequisites
- **Local Container Engine**: Docker 19.03+ or Finch installed and running on the VM or worker machine.
- **AWS CLI & Credentials**: AWS IAM credentials configured with permissions for Amazon S3, Amazon ECR, Amazon ECS, Amazon EKS, and AWS CloudFormation.
- **Root / Administrative Access**: `sudo` access on Linux or Administrator PowerShell session on Windows.
- **Disk Space**: At least 20–50 GB free disk space in the working directory for image layering and tarball extraction.

---

## 3. The 5-Stage A2C Modernization Workflow

```
+---------------------------------------------------------------------------------------------------+
| Stage 1: init                                                                                     |
| Configure S3 workspace bucket, target AWS Region, KMS encryption, and local Docker environment.   |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| Stage 2: inventory                                                                                |
| Scan OS process table; discover running Java and IIS processes; generate unique application IDs.  |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| Stage 3: analyze                                                                                  |
| Inspect runtime dependencies, bound sockets, and configuration files; generate `analysis.json`.   |
| * Operator customizes ports, container base images, env vars, and storage mount points.           |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| Stage 4: containerize                                                                             |
| Build Dockerfile, create container image layers, tag, and publish image to Amazon ECR repository. |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| Stage 5: generate app-deployment                                                                  |
| Generate CloudFormation/CDK templates, Kubernetes manifests, or App Runner service definitions.   |
+---------------------------------------------------------------------------------------------------+
```

---

## 4. Stage-by-Stage CLI Execution & Configuration

### Stage 1: Initialize Workspace (`app2container init`)

Sets up local storage and AWS account parameters. Run once per VM.

```bash
# Interactive setup
app2container init

# Non-interactive / scripted execution
sudo app2container init \
  --workspace-directory /var/app2container \
  --target-bucket a2c-modernization-artifacts-123456789012-us-east-1 \
  --aws-region us-east-1 \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/a2c-modernization-key \
  --enable-telemetry false
```

**Parameters Initialized:**
- `workspace-directory`: Local path storing container build contexts and temporary artifacts.
- `target-bucket`: Amazon S3 bucket used to store extracted application archives and generated IaC templates.
- `aws-region`: Primary AWS region for Amazon ECR and deployment infrastructure.
- `kms-key-id`: KMS Customer Managed Key (CMK) for encrypting archives at rest in S3.

---

### Stage 2: Inventory Applications (`app2container inventory`)

Scans the operating system to detect candidates for containerization.

```bash
# On Linux (Java applications)
sudo app2container inventory

# On Windows (PowerShell as Administrator)
app2container.exe inventory
```

**Output Example (`inventory.json`):**
```json
{
  "inventory": [
    {
      "appId": "java-tomcat-8a4b3c2d",
      "appType": "Java-Tomcat",
      "applicationName": "ecommerce-storefront",
      "runtime": "Java 11",
      "processId": 14220,
      "processPath": "/opt/tomcat/bin/bootstrap.jar",
      "port": [8080, 8443]
    },
    {
      "appId": "iis-dotnet-9f8e7d6c",
      "appType": "IIS",
      "applicationName": "ClaimsManagementWeb",
      "runtime": ".NET Framework 4.8",
      "siteName": "ClaimsSite",
      "bindings": ["http/*:80:", "https/*:443:"]
    }
  ]
}
```

---

### Stage 3: Analyze Application & Customize `analysis.json` (`app2container analyze`)

Inspects file dependencies, open ports, libraries, and application server configuration for a specific `appId`.

```bash
# Analyze discovered application
sudo app2container analyze --application-id java-tomcat-8a4b3c2d
```

This generates `analysis.json` in `/var/app2container/<appId>/analysis.json`.

#### Customizing `analysis.json`

Before proceeding to containerization, inspect and edit `analysis.json` to fine-tune the container configuration:

```json
{
  "applicationId": "java-tomcat-8a4b3c2d",
  "appType": "Java-Tomcat",
  "containerBaseImage": "public.ecr.aws/amazoncorretto/amazoncorretto:11-al2023",
  "containerParameters": {
    "containerMemory": 2048,
    "containerCpu": 1024,
    "ports": [
      {
        "containerPort": 8080,
        "protocol": "TCP",
        "exposed": true
      }
    ],
    "environment": [
      {
        "name": "SPRING_PROFILES_ACTIVE",
        "value": "production-aws"
      },
      {
        "name": "DB_SECRET_ARN",
        "value": "arn:aws:secretsmanager:us-east-1:123456789012:secret:rds/aurora-pg-app"
      }
    ],
    "mountPoints": [
      {
        "containerPath": "/opt/app/shared-reports",
        "sourceVolume": "efs-reports-volume",
        "readOnly": false
      }
    ]
  },
  "logging": {
    "logFormat": "json",
    "logDestinations": [
      {
        "destinationType": "CloudWatchLogs",
        "logGroup": "/aws/modernization/ecommerce-storefront"
      }
    ]
  }
}
```

**Key Customization Fields:**
- `containerBaseImage`: Select standard Amazon Linux 2023 Corretto images or custom corporate golden images. For Windows, specify matching OS build (`mcr.microsoft.com/dotnet/framework/aspnet:4.8-windowsservercore-ltsc2022`).
- `ports`: Ensure all internal application ports are properly declared and mapped.
- `environment`: Inject environment variables referencing AWS Secrets Manager ARNs rather than plaintext credentials.
- `mountPoints`: Configure Amazon EFS persistent mounts for stateful files, uploads, or batch outputs.

---

### Stage 4: Build & Publish Container (`app2container containerize`)

Extracts application binaries, builds the OCI image locally using Docker, and pushes the image to Amazon ECR.

```bash
# Containerize application
sudo app2container containerize --application-id java-tomcat-8a4b3c2d

# Containerize with explicit ECR push
sudo app2container containerize \
  --application-id java-tomcat-8a4b3c2d \
  --repository-prefix legacy-modernized \
  --deploy
```

**What Occurs Under the Hood:**
1. A2C generates an optimized `Dockerfile` in `/var/app2container/<appId>/Artifacts/`.
2. Packages the application directory, excluding OS temporary files, log directories, and socket files.
3. Builds the Docker image: `legacy-modernized/ecommerce-storefront:latest`.
4. Creates an Amazon ECR repository if it does not already exist: `123456789012.dkr.ecr.us-east-1.amazonaws.com/legacy-modernized/ecommerce-storefront`.
5. Authenticates via Docker credentials helper and pushes the image layers.

---

### Stage 5: Generate Target Deployment Artifacts (`app2container generate app-deployment`)

Generates deployment pipelines and manifests customized for the target container orchestrator.

```bash
# Target: Amazon ECS (Fargate)
sudo app2container generate app-deployment \
  --application-id java-tomcat-8a4b3c2d \
  --target-runtime ecs

# Target: Amazon EKS (Kubernetes manifests & Helm chart)
sudo app2container generate app-deployment \
  --application-id java-tomcat-8a4b3c2d \
  --target-runtime eks

# Target: AWS App Runner
sudo app2container generate app-deployment \
  --application-id java-tomcat-8a4b3c2d \
  --target-runtime apprunner
```

---

## 5. Deployment Target Architectural Comparison

### 5.1 Amazon ECS (AWS Fargate or EC2)
- **Best For**: Microservices and decoupled monolithic applications where team requires simple operational overhead without managing Kubernetes control planes.
- **Artifacts Generated**:
  - `ecs-task-definition.json`: Declaring CPU, memory, logConfiguration, Secrets Manager secret injections, and IAM execution/task roles.
  - `ecs-service-cfn.yaml`: CloudFormation template provisioning Application Load Balancer (ALB), Target Groups, Security Groups, and ECS Service with Auto Scaling.

### 5.2 Amazon EKS (Standard & EKS Auto Mode)
- **Best For**: Enterprise microservice ecosystems running standardized Kubernetes tooling, service meshes (Istio/Linkerd), and complex ingress controllers.
- **EKS Auto Mode Integration**:
  - Automatically provisions compute infrastructure using AWS managed node pools with integrated Karpenter scaling.
  - Provisions AWS VPC CNI, CoreDNS, and AWS EBS CSI drivers automatically without manual add-on maintenance.
- **Artifacts Generated**:
  - `deployment.yaml` & `service.yaml`: Standard Kubernetes resources with readiness/liveness probes mapped to `/health`.
  - `kustomization.yaml` or Helm Chart directory (`/Artifacts/eks/helm/`).

### 5.3 AWS App Runner
- **Best For**: HTTP/HTTPS web applications, APIs, and microservices requiring automatic scale-to-zero, built-in TLS termination, and zero VPC/cluster management.
- **Artifacts Generated**:
  - `apprunner-service-cfn.yaml`: CloudFormation template defining App Runner service directly referencing ECR image with automatic deployment on image push.

---

## 6. Windows .NET Framework Containerization Specifics

Containerizing legacy ASP.NET (.NET Framework 3.5/4.x) IIS applications involves Windows-specific constraints:

### 6.1 OS Version Matching Matrix
The container host's Windows kernel version must match the container base image version unless running with Hyper-V isolation:

| Host OS Version | Recommended Container Base Image | Isolation Mode |
|---|---|---|
| Windows Server 2019 (Build 17763) | `mcr.microsoft.com/dotnet/framework/aspnet:4.8-windowsservercore-ltsc2019` | Process or Hyper-V |
| Windows Server 2022 (Build 20348) | `mcr.microsoft.com/dotnet/framework/aspnet:4.8-windowsservercore-ltsc2022` | Process or Hyper-V |
| Windows Server 2025 (Build 26100) | `mcr.microsoft.com/dotnet/framework/aspnet:4.8-windowsservercore-ltsc2025` | Process or Hyper-V |

### 6.2 Windows IIS Analysis Customization
Ensure the IIS application pool identity, virtual directories, and registry keys are reviewed in `analysis.json`:
- Check for Windows Authentication (`NTLM`/`Kerberos`): If the application uses domain authentication, configure **gMSA (Group Managed Service Accounts)** on Amazon ECS or Amazon EKS Windows node pools.
- Verify machine keys and session state: Configure external session providers (such as Amazon ElastiCache for Redis) if scaling across multiple container replicas.

---

## 7. AWS MGN Post-Launch SSM Integration

For automated enterprise-scale migrations:
1. Replicate on-premises VMs to AWS via **AWS Application Migration Service (AWS MGN)**.
2. Configure **SSM Automation Document `AWSMGN-App2Container-Containerize`** in MGN Post-Launch Actions.
3. Upon launching test or cutover EC2 instances, the SSM agent executes the A2C 5-stage workflow autonomously, storing container images in ECR and posting deployment templates to S3, transforming the migration from Rehost to Replatform in a single automated step.
