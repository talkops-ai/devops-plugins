# Production PromQL SRE Query Library (`kube-state-metrics`, `cAdvisor`, `node_exporter`)

Use these exact PromQL templates with `prometheus.ExecuteQuery` and `prometheus.ExecuteRangeQuery` during EKS, ECS, and EC2 incident investigations.

---

## 1. Kubernetes Pod & Deployment Failure Queries (`kube-state-metrics`)

### Pods in CrashLoopBackOff, ImagePullBackOff, or CreateContainerConfigError
```promql
sum by (namespace, pod, container, reason) (
  kube_pod_container_status_waiting_reason{reason=~"CrashLoopBackOff|ImagePullBackOff|ErrImagePull|CreateContainerConfigError|CreateContainerError"}
) > 0
```

### Pods Terminated by OOMKilled (`Exit Code 137`) in the Last 30 Minutes
```promql
sum by (namespace, pod, container) (
  kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}
) > 0
```

### Container Restart Rate Spike (Last 15 Minutes)
```promql
sum by (namespace, pod, container) (
  increase(kube_pod_container_status_restarts_total[15m])
) > 2
```

### Unschedulable / Pending Pods (> 5 Minutes)
```promql
sum by (namespace, pod, reason) (
  kube_pod_status_scheduled{condition="false"}
) > 0
```

### Deployment Unavailable Replicas (Rollout Stuck / ProgressDeadlineExceeded)
```promql
(
  kube_deployment_spec_replicas
  - kube_deployment_status_replicas_available
) > 0
```

---

## 2. Node USE Method Saturation Queries (`node_exporter`)

### Node CPU Utilization % by Instance
```promql
100 - (
  avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100
)
```

### Node CPU Pressure Stall Information (PSI)
```promql
rate(node_pressure_cpu_waiting_seconds_total[5m])
```

### Node Available Memory % (< 10% Indicates Imminent Kernel OOM Killer Invocation)
```promql
(
  node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes
) * 100 < 10
```

### Node Disk I/O Saturation (`io_time` > 80%) & Filesystem Fullness (< 15% Free)
```promql
rate(node_disk_io_time_seconds_total[5m]) > 0.80
```
```promql
(
  node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"}
  / node_filesystem_size_bytes{fstype!~"tmpfs|overlay"}
) * 100 < 15
```

### Linux Conntrack Table Exhaustion (> 85% Full Causes Silent Packet Drops)
```promql
(
  node_nf_conntrack_entries / node_nf_conntrack_entries_limit
) * 100 > 85
```
