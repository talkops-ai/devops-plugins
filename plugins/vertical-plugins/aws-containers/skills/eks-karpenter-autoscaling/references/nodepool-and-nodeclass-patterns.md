# Production `NodePool`, `EC2NodeClass` & EKS Auto Mode `NodeClass` Patterns

## 1. Self-Managed Karpenter v1: Multi-Arch Tiered `EC2NodeClass` + Weighted `NodePool`s

In production, pair a hardened **AL2023 `EC2NodeClass`** (pinned tested AMI alias `Op11`, encrypted `gp3` root volume, IMDSv2 `httpPutResponseHopLimit: 1` when using Pod Identity/IRSA) with **weighted or tainted `NodePool`s (`Op27`)**:
- **Pool 1 (`general-spot`, `weight: 50`):** Preferred cost-optimized pool across diversified Graviton (`c7g`, `m7g`, `r7g`, `c8g`, `m8g`, `r8g`) and x86 (`c6i`, `m6i`, `r6i`, `c7i`, `m7i`, `r7i`) families (`Op22`, `Sc4`).
- **Pool 2 (`general-ondemand`, `weight: 10`):** Automatic fallback if Spot capacity is exhausted (`InsufficientCapacityError`), plus target for stateful/tier-1 pods setting `nodeSelector: {"karpenter.sh/capacity-type": "on-demand"}`.

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default-al2023
spec:
  amiFamily: AL2023
  role: "KarpenterNodeRole-prod-eks"   # Karpenter v1 creates & manages the InstanceProfile automatically
  amiSelectorTerms:
    # Op11: Pin a staging-tested AL2023 release in production (use al2023@latest in dev/staging)
    - alias: al2023@v20260807
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "prod-eks"
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "prod-eks"
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 1   # Enforce 1 with EKS Pod Identity / IRSA; set 2 only for legacy IMDS pods
    httpTokens: required
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 80Gi
        volumeType: gp3
        iops: 3000
        throughput: 125
        encrypted: true
        deleteOnTermination: true
  tags:
    Environment: prod
    ManagedBy: karpenter
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: general-spot
spec:
  weight: 50   # Op27: Higher weight tried first; falls back to general-ondemand (weight: 10) on Spot ICE
  template:
    metadata:
      labels:
        workload-tier: general
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default-al2023
      expireAfter: 720h   # Op13: 30-day max node lifetime for continuous AMI/kernel hygiene
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
        - key: kubernetes.io/arch
          operator: In
          values: ["arm64", "amd64"]   # Multi-arch Graviton + x86 (~20% lower $/vCPU on arm64)
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r"]      # Op22/Sc5: Diversified families; excludes burstable T-series
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]                # Nitro 6th/7th/8th-gen only
        - key: karpenter.k8s.aws/instance-cpu
          operator: In
          values: ["4", "8", "16", "32"]
  limits:                              # Op10: Mandatory runaway-spend ceiling
    cpu: "800"
    memory: 3200Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized   # Op12
    consolidateAfter: 1m
    budgets:
      # Allow 10% concurrent node disruption normally, but freeze voluntary consolidation during peak business hours
      - nodes: "0"
        schedule: "0 13 * * mon-fri"   # 13:00 UTC
        duration: 8h
        reasons: ["Underutilized"]
      - nodes: "10%"
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: general-ondemand
spec:
  weight: 10
  template:
    metadata:
      labels:
        workload-tier: general
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default-al2023
      expireAfter: 720h
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["arm64", "amd64"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["5"]
  limits:
    cpu: "400"
    memory: 1600Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 2m
    budgets:
      - nodes: "10%"
```

---

## 2. Dedicated GPU / AI-ML Training `NodePool` (`M4`, `M8`)

GPU training and LLM inference nodes have slow container pulls (10–30 GB) and cannot tolerate mid-epoch consolidation (`M8`). Isolate them with:
1. A taint (`nvidia.com/gpu=Exists:NoSchedule`) so general CPU pods never land on expensive `g5`/`g6`/`p4d`/`p5` nodes (`Op27` mutual exclusivity).
2. `consolidationPolicy: WhenEmpty` (reclaims idle GPU nodes once jobs finish, **never** evicts active GPU pods to bin-pack!).
3. Larger encrypted `gp3` root/ephemeral storage (`200Gi`+, higher throughput `500` MB/s for fast OCI image extraction).

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: gpu-al2023
spec:
  amiFamily: AL2023
  role: "KarpenterNodeRole-prod-eks"
  amiSelectorTerms:
    - alias: al2023@v20260807   # Karpenter automatically selects the NVIDIA/Neuron accelerated variant for GPU/Inf instances
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "prod-eks"
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "prod-eks"
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 250Gi
        volumeType: gp3
        iops: 6000
        throughput: 500
        encrypted: true
        deleteOnTermination: true
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-workloads
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: gpu-al2023
      taints:
        - key: nvidia.com/gpu
          effect: NoSchedule
      expireAfter: 720h
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["g", "p"]
        - key: karpenter.k8s.aws/instance-gpu-manufacturer
          operator: In
          values: ["nvidia"]
  limits:
    nvidia.com/gpu: "32"
    cpu: "512"
  disruption:
    consolidationPolicy: WhenEmpty   # M8: Never consolidate non-empty GPU nodes mid-job!
    consolidateAfter: 5m
```

---

## 3. EKS Auto Mode `NodeClass` + `NodePool` (`eks.amazonaws.com/v1`)

**CRITICAL DIFFERENCES from Self-Managed Karpenter:**
- `NodeClass` uses `apiVersion: eks.amazonaws.com/v1`, `kind: NodeClass` (NOT `karpenter.k8s.aws/v1` `EC2NodeClass`!).
- Requirement label keys use **`eks.amazonaws.com/instance-category`**, **`eks.amazonaws.com/instance-generation`**, **`eks.amazonaws.com/instance-cpu`** (NOT `karpenter.k8s.aws/*`!).
- Maximum `expireAfter` on EKS Auto Mode is **`504h` (21 days)** (enforced by AWS).
- Subnet/Security Group selectors support `id`, `tags`, without requiring custom AMI selectors (AWS manages the hardened OS image automatically).

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: auto-custom
spec:
  role: "arn:aws:iam::111122223333:role/AmazonEKSAutoNodeRole"
  subnetSelectorTerms:
    - tags:
        kubernetes.io/role/internal-elb: "1"
  securityGroupSelectorTerms:
    - tags:
        aws:eks:cluster-name: "prod-auto-eks"
  ephemeralStorage:
    size: "100Gi"
    iops: 3000
    throughput: 125
  snatPolicy: Random
  networkPolicy: DefaultAllow
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: auto-graviton-spot
spec:
  template:
    spec:
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: auto-custom
      expireAfter: 336h   # 14 days (must be <= 504h on EKS Auto Mode)
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["arm64", "amd64"]
        - key: eks.amazonaws.com/instance-category
          operator: In
          values: ["c", "m", "r"]
        - key: eks.amazonaws.com/instance-generation
          operator: Gt
          values: ["5"]
  limits:
    cpu: "500"
    memory: 2000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
```
