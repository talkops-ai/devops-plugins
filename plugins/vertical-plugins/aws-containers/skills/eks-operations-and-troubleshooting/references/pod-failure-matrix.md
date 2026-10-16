# EKS Pod Exit Codes, Probe Anti-Patterns, and Container Insights Queries

## 1. Container Exit Code Forensics

| Exit Code | Signal / Meaning | Common Root Causes in EKS |
|---|---|---|
| **`0`** | Clean exit | Job/initContainer completed; if on a Deployment, the main process exited instead of running in foreground. |
| **`1`** | Application error | Unhandled runtime exception, failed DB connection at startup, invalid configuration file. |
| **`126`** | Command cannot execute | Binary lacks `+x` executable permission or architecture mismatch (`exec format error`: `amd64` image on Graviton `arm64` node). |
| **`127`** | Command not found | Typo in `command`/`args` or missing shared library (`musl` vs `glibc` in distroless/alpine images). |
| **`137`** | `SIGKILL` (`128 + 9`) | **Container OOMKilled** (`memory.max` cgroup v2 limit exceeded), node OOM killer, or `livenessProbe` failed and container did not exit within `terminationGracePeriodSeconds`. |
| **`139`** | `SIGSEGV` (`128 + 11`) | Segmentation fault in native C/C++/Rust/CGO code or corrupted shared memory (`/dev/shm` default 64MB exhausted). |
| **`143`** | `SIGTERM` (`128 + 15`) | Graceful shutdown initiated by Kubelet (rolling update, scale-in, Karpenter consolidation, Spot interruption, or `livenessProbe` failure). |

---

## 2. CloudWatch Logs Insights Queries for EKS Control Plane & Container Insights

### Control Plane Audit Logs (`/aws/eks/<cluster-name>/cluster`) — Who Deleted or Evicted Pods?
```sql
fields @timestamp, user.username, verb, objectRef.namespace, objectRef.resource, objectRef.name, responseStatus.code
| filter @logStream like /^kube-apiserver-audit/
| filter verb in ["delete", "deletecollection", "patch", "update", "create"]
| filter objectRef.resource in ["pods", "deployments", "nodes", "nodeclaims", "evictions"]
| sort @timestamp desc
| limit 100
```

### Container Insights Application Logs (`/aws/containerinsights/<cluster-name>/application`) — Crash & Exception Search
```sql
fields @timestamp, kubernetes.namespace_name as ns, kubernetes.pod_name as pod, kubernetes.container_name as container, log
| filter log like /(?i)(Exception|FATAL|panic:|OOM|OutOfMemory|ECONNREFUSED|ETIMEDOUT)/
| sort @timestamp desc
| limit 100
```

### Container Insights Performance Logs (`/aws/containerinsights/<cluster-name>/performance`) — Top Memory-Saturated Pods
```sql
fields @timestamp, Namespace, PodName, pod_memory_utilization_over_pod_limit as mem_pct, pod_cpu_utilization_over_pod_limit as cpu_pct
| filter ispresent(pod_memory_utilization_over_pod_limit) and pod_memory_utilization_over_pod_limit > 80
| stats max(mem_pct) as max_mem_pct, max(cpu_pct) as max_cpu_pct by Namespace, PodName
| sort max_mem_pct desc
| limit 25
```
