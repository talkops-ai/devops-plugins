# Karpenter v1 Bootstrap: IAM, Pod Identity, SQS Interruption Queue & IaC

## 1. Architecture Overview (Self-Managed Karpenter v1)

A production self-managed Karpenter v1 deployment on Amazon EKS requires five AWS-side building blocks before installing the Helm chart:

1. **System Compute for the Controller (`Op20`):** A small 2-node EKS Managed Node Group (e.g., `m7g.large` across 2 AZs with taint `CriticalAddonsOnly=true:NoSchedule`) OR an EKS Fargate profile matching namespace `kube-system` / `karpenter` with label `app.kubernetes.io/name: karpenter`.
2. **Node IAM Role (`KarpenterNodeRole-<cluster>`):** Attached via EC2 Instance Profile (managed automatically by `EC2NodeClass.spec.role` in Karpenter v1!) with managed policies:
   - `AmazonEKSWorkerNodeMinimalPolicy` (or `AmazonEKSWorkerNodePolicy`)
   - `AmazonEKS_CNI_Policy` (omit on IPv6 if using dedicated CNI Pod Identity role; keep when nodes need IPv4 CNI calls)
   - `AmazonEC2ContainerRegistryPullOnly` (or `AmazonEC2ContainerRegistryReadOnly`)
   - `AmazonSSMManagedInstanceCore` (optional, for SSM node diagnostics without SSH)
3. **EKS Access Entry for `KarpenterNodeRole`:** Type `EC2_LINUX` (`aws eks create-access-entry --cluster-name <cluster> --principal-arn <node-role-arn> --type EC2_LINUX`) — replaces legacy `aws-auth` ConfigMap editing (`OpM4`).
4. **SQS Interruption Queue + 4 EventBridge Rules (`OpM1`):** Gives Karpenter immediate notice of EC2 Spot 2-minute interruption warnings, rebalance recommendations, instance terminations, and AWS Health scheduled maintenance so pods cordon/drain gracefully.
5. **Controller IAM Role (`KarpenterControllerRole-<cluster>`) Bound via EKS Pod Identity:** Grants scoped EC2 RunInstances/TerminateInstances (tag-conditioned to `karpenter.sh/nodepool`), `iam:PassRole` ONLY to `KarpenterNodeRole`, `pricing:GetProducts`, `ssm:GetParameter` (`/aws/service/eks/*`, `/aws/service/bottlerocket/*`), `eks:DescribeCluster`, and SQS queue access.
6. **VPC Subnet & Security Group Discovery Tags:** Tag private worker subnets and the node/cluster security group with:
   ```text
   karpenter.sh/discovery = <cluster-name>
   ```
   *(Important: Tag ONLY the specific cluster security group / shared node security group if AWS Load Balancer Controller also runs in the VPC — tagging multiple SGs without explicit SG selection on older LBC versions can cause LBC target SG ambiguity!)*

---

## 2. Least-Privilege `KarpenterControllerRole` IAM Policy (Karpenter v1)

Trust policy for **EKS Pod Identity** (`pods.eks.amazonaws.com`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowEksAuthToAssumeRoleForPodIdentity",
      "Effect": "Allow",
      "Principal": {
        "Service": "pods.eks.amazonaws.com"
      },
      "Action": [
        "sts:AssumeRole",
        "sts:TagSession"
      ]
    }
  ]
}
```

Scoped permissions policy (replace `<REGION>`, `<ACCOUNT_ID>`, `<CLUSTER_NAME>`, `<KARPENTER_NODE_ROLE_NAME>`, `<QUEUE_ARN>`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowScopedEC2InstanceAccessActions",
      "Effect": "Allow",
      "Resource": [
        "arn:aws:ec2:<REGION>::image/*",
        "arn:aws:ec2:<REGION>::snapshot/*",
        "arn:aws:ec2:<REGION>:*:security-group/*",
        "arn:aws:ec2:<REGION>:*:subnet/*",
        "arn:aws:ec2:<REGION>:*:capacity-reservation/*"
      ],
      "Action": [
        "ec2:RunInstances",
        "ec2:CreateFleet"
      ]
    },
    {
      "Sid": "AllowScopedEC2LaunchTemplateAccessActions",
      "Effect": "Allow",
      "Resource": "arn:aws:ec2:<REGION>:*:launch-template/*",
      "Action": [
        "ec2:RunInstances",
        "ec2:CreateFleet"
      ],
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/kubernetes.io/cluster/<CLUSTER_NAME>": "owned"
        },
        "StringLike": {
          "aws:ResourceTag/karpenter.sh/nodepool": "*"
        }
      }
    },
    {
      "Sid": "AllowScopedEC2InstanceActionsWithTags",
      "Effect": "Allow",
      "Resource": [
        "arn:aws:ec2:<REGION>:*:fleet/*",
        "arn:aws:ec2:<REGION>:*:instance/*",
        "arn:aws:ec2:<REGION>:*:volume/*",
        "arn:aws:ec2:<REGION>:*:network-interface/*",
        "arn:aws:ec2:<REGION>:*:launch-template/*",
        "arn:aws:ec2:<REGION>:*:spot-instances-request/*"
      ],
      "Action": [
        "ec2:RunInstances",
        "ec2:CreateFleet",
        "ec2:CreateLaunchTemplate"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/kubernetes.io/cluster/<CLUSTER_NAME>": "owned",
          "aws:RequestTag/eks:eks-cluster-name": "<CLUSTER_NAME>"
        },
        "StringLike": {
          "aws:RequestTag/karpenter.sh/nodepool": "*"
        }
      }
    },
    {
      "Sid": "AllowScopedResourceCreationTagging",
      "Effect": "Allow",
      "Resource": [
        "arn:aws:ec2:<REGION>:*:fleet/*",
        "arn:aws:ec2:<REGION>:*:instance/*",
        "arn:aws:ec2:<REGION>:*:volume/*",
        "arn:aws:ec2:<REGION>:*:network-interface/*",
        "arn:aws:ec2:<REGION>:*:launch-template/*",
        "arn:aws:ec2:<REGION>:*:spot-instances-request/*"
      ],
      "Action": "ec2:CreateTags",
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/kubernetes.io/cluster/<CLUSTER_NAME>": "owned",
          "aws:RequestTag/eks:eks-cluster-name": "<CLUSTER_NAME>",
          "ec2:CreateAction": [
            "RunInstances",
            "CreateFleet",
            "CreateLaunchTemplate"
          ]
        },
        "StringLike": {
          "aws:RequestTag/karpenter.sh/nodepool": "*"
        }
      }
    },
    {
      "Sid": "AllowScopedDeletion",
      "Effect": "Allow",
      "Resource": [
        "arn:aws:ec2:<REGION>:*:instance/*",
        "arn:aws:ec2:<REGION>:*:launch-template/*"
      ],
      "Action": [
        "ec2:TerminateInstances",
        "ec2:DeleteLaunchTemplate"
      ],
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/kubernetes.io/cluster/<CLUSTER_NAME>": "owned"
        },
        "StringLike": {
          "aws:ResourceTag/karpenter.sh/nodepool": "*"
        }
      }
    },
    {
      "Sid": "AllowRegionalReadActions",
      "Effect": "Allow",
      "Resource": "*",
      "Action": [
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeImages",
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceTypeOfferings",
        "ec2:DescribeInstanceTypes",
        "ec2:DescribeLaunchTemplates",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSpotPriceHistory",
        "ec2:DescribeSubnets",
        "ec2:DescribeCapacityReservations"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "<REGION>"
        }
      }
    },
    {
      "Sid": "AllowSSMAndPricingReads",
      "Effect": "Allow",
      "Resource": [
        "arn:aws:ssm:<REGION>::parameter/aws/service/*"
      ],
      "Action": "ssm:GetParameter"
    },
    {
      "Sid": "AllowPricingRead",
      "Effect": "Allow",
      "Resource": "*",
      "Action": "pricing:GetProducts"
    },
    {
      "Sid": "AllowInterruptionQueueActions",
      "Effect": "Allow",
      "Resource": "<QUEUE_ARN>",
      "Action": [
        "sqs:DeleteMessage",
        "sqs:GetQueueUrl",
        "sqs:ReceiveMessage"
      ]
    },
    {
      "Sid": "AllowPassingInstanceRole",
      "Effect": "Allow",
      "Resource": "arn:aws:iam::<ACCOUNT_ID>:role/<KARPENTER_NODE_ROLE_NAME>",
      "Action": "iam:PassRole",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": [
            "ec2.amazonaws.com",
            "ec2.amazonaws.com.cn"
          ]
        }
      }
    },
    {
      "Sid": "AllowScopedInstanceProfileActions",
      "Effect": "Allow",
      "Resource": "arn:aws:iam::<ACCOUNT_ID>:instance-profile/*",
      "Action": [
        "iam:CreateInstanceProfile",
        "iam:TagInstanceProfile",
        "iam:AddRoleToInstanceProfile",
        "iam:RemoveRoleFromInstanceProfile",
        "iam:DeleteInstanceProfile",
        "iam:GetInstanceProfile"
      ]
    },
    {
      "Sid": "AllowAPIServerEndpointDiscovery",
      "Effect": "Allow",
      "Resource": "arn:aws:eks:<REGION>:<ACCOUNT_ID>:cluster/<CLUSTER_NAME>",
      "Action": "eks:DescribeCluster"
    }
  ]
}
```

---

## 3. Terraform Golden Blueprint (`terraform-aws-modules/eks/aws//modules/karpenter`)

Using the official Terraform AWS EKS Karpenter submodule provisions `KarpenterControllerRole` (Pod Identity), `KarpenterNodeRole`, the `EC2_LINUX` EKS Access Entry, SQS encryption, and all 4 EventBridge interruption rules in one validated block:

```hcl
module "karpenter" {
  source  = "terraform-aws-modules/eks/aws//modules/karpenter"
  version = "~> 20.31"

  cluster_name = module.eks.cluster_name

  # EKS Pod Identity association for kube-system/karpenter
  enable_v1_permissions           = true
  enable_pod_identity             = true
  create_pod_identity_association = true
  namespace                       = "kube-system"
  service_account                 = "karpenter"

  # Automatically creates the EC2_LINUX Access Entry for Karpenter-launched nodes
  node_iam_role_additional_policies = {
    AmazonSSMManagedInstanceCore = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  }

  # SQS encryption for the Spot/Health interruption queue
  queue_managed_sse_enabled = true

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
```

---

## 4. Production Helm OCI Installation (Two-Chart Pattern: CRDs + Controller)

Always install/upgrade **`karpenter-crd` separately** before `karpenter` so cross-minor CRD upgrades are never skipped, and pin controller pods onto the dedicated system MNG (never Karpenter nodes):

```bash
# Verify Karpenter compatibility with your EKS version first:
# K8s 1.30 -> >=0.37 | 1.31 -> >=1.0.5 | 1.32 -> >=1.2 | 1.33 -> >=1.5 | 1.34 -> >=1.6 | 1.35 -> >=1.9 | 1.36 -> >=1.13

helm upgrade --install karpenter-crd oci://public.ecr.aws/karpenter/karpenter-crd \
  --version "${KARPENTER_VERSION}" \
  --namespace kube-system \
  --create-namespace

helm upgrade --install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --version "${KARPENTER_VERSION}" \
  --namespace kube-system \
  --set "settings.clusterName=${CLUSTER_NAME}" \
  --set "settings.interruptionQueue=${KARPENTER_QUEUE_NAME}" \
  --set "settings.featureGates.spotToSpotConsolidation=true" \
  --set "settings.featureGates.nodeRepair=true" \
  --set controller.resources.requests.cpu=1 \
  --set controller.resources.requests.memory=1Gi \
  --set controller.resources.limits.memory=1Gi \
  --set replicas=2 \
  --set "nodeSelector.eks\.amazonaws\.com/nodegroup=system" \
  --set "tolerations[0].key=CriticalAddonsOnly" \
  --set "tolerations[0].operator=Exists" \
  --wait
```

---

## 5. Enabling EKS Auto Mode Instead (Terraform / AWS CLI)

When choosing **EKS Auto Mode** (`eks.amazonaws.com/v1`), skip Steps 1–4 above and enable managed compute/storage/load-balancing on the cluster:

```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.31"

  cluster_name    = "prod-auto-eks"
  cluster_version = "1.34"

  cluster_compute_config = {
    enabled    = true
    node_pools = ["general-purpose", "system"]
  }
}
```
