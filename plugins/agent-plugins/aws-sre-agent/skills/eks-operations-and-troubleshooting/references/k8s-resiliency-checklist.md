# Production EKS Workload Resiliency Checklist & Golden Manifest

Use this checklist and reference manifest when auditing EKS workloads for Well-Architected Reliability (`REL`) or remediating deployment/AZ-outage incidents.

---

## 1. The 8-Point Production EKS Resiliency Checklist

| # | Guardrail | Failure Prevented | Required Spec |
|---|---|---|---|
| **1** | **Multi-AZ Topology Spread** | Single-AZ outage taking down 100% of replicas | `topologySpreadConstraints` across `topology.kubernetes.io/zone` (`maxSkew: 1`) AND `kubernetes.io/hostname`. |
| **2** | **PodDisruptionBudget (PDB)** | Karpenter consolidation or node drain evicting all replicas at once | `minAvailable: "50%"` or `maxUnavailable: 1` (never `maxUnavailable: 0`, which blocks node drains). |
| **3** | **Memory `requests == limits`** | Node-level memory overcommit and unpredictable kernel OOM kills | Set `resources.requests.memory == resources.limits.memory`; set `requests.cpu` accurately and avoid aggressive `limits.cpu` that cause CFS throttling. |
| **4** | **Decoupled `startupProbe`, `readinessProbe`, `livenessProbe`** | Cascading restart storms when a downstream dependency slows down | Never check downstream DBs/APIs in `livenessProbe`! Use `startupProbe` for slow boot, `readinessProbe` to gate traffic, and lightweight local deadlock checks in `livenessProbe`. |
| **5** | **Graceful Drain (`preStop` + Readiness Gate)** | ALB 502/504 errors during rolling updates or scale-in | Namespace label `elbv2.k8s.aws/pod-readiness-gate-inject: enabled` + `lifecycle.preStop.exec.command: ["sh", "-c", "sleep 15"]`. |
| **6** | **IMDSv2 Hop Limit & Pod Identity** | Credential theft via SSRF (`IMDSv1`) | Enforce `httpPutResponseHopLimit = 1` on nodes when using EKS Pod Identity / IRSA so pods cannot access node-level EC2 instance profile credentials. |
| **7** | **CoreDNS & NodeLocal DNSCache** | DNS lookup timeouts (`5s` delay) under high connection churn | Run `node-local-dns` or set `ndots: "2"` in `dnsConfig`. |
| **8** | **PriorityClass for Critical Workloads** | Critical payment/auth pods preempted before batch jobs | Assign higher `priorityClassName` to tier-1 customer-facing services and `system-cluster-critical` to CNI/DNS/CSI add-ons. |

---

## 2. Golden Production Deployment + PDB Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: checkout-service
  namespace: production
spec:
  replicas: 6
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 0
  selector:
    matchLabels:
      app: checkout-service
  template:
    metadata:
      labels:
        app: checkout-service
    spec:
      serviceAccountName: checkout-service-sa
      terminationGracePeriodSeconds: 60
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: checkout-service
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: checkout-service
      containers:
        - name: app
          image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/checkout-service:v1.4.2
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              memory: "1Gi"
          startupProbe:
            httpGet:
              path: /healthz/startup
              port: 8080
            failureThreshold: 30
            periodSeconds: 2
          readinessProbe:
            httpGet:
              path: /healthz/ready
              port: 8080
            periodSeconds: 5
            failureThreshold: 3
          livenessProbe:
            httpGet:
              path: /healthz/live
              port: 8080
            periodSeconds: 10
            failureThreshold: 3
          lifecycle:
            preStop:
              exec:
                command: ["sh", "-c", "sleep 15"]
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: checkout-service-pdb
  namespace: production
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: checkout-service
```
