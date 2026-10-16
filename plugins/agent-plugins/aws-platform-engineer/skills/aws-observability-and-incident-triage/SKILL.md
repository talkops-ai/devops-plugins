---
name: aws-observability-and-incident-triage
description: Diagnoses production and staging incidents, 5xx errors, latency spikes, container crashes, network blackholes, and resource exhaustion across AWS services using CloudWatch Metrics, PromQL, Logs Insights, Alarms, CloudTrail API audit logs, and EKS/ECS/Network MCP servers.
metadata:
  version: "2.0"
---

# AWS Observability and Incident Triage

## Purpose

Enable structured, hypothesis-driven Site Reliability Engineering (SRE) root-cause analysis (RCA) so developers, QA engineers, and platform operators can isolate outages, deployment regressions, and performance bottlenecks without blindly restarting services or sifting manually through console logs.

---

## Triage Protocol: The "Four Golden Signals + Audit" Loop

Execute every incident investigation through these four ordered phases before proposing any infrastructure mutation:

### Phase 1: Alarm & Change Triage (Blast Radius & Onset Identification)

Most production incidents are triggered by a recent deployment, configuration mutation, or upstream dependency shift. Establish the timeline first:
1. **Active Alarm Sweep (`cloudwatch` MCP)**:
   - Call `get_active_alarms` on the `cloudwatch` MCP server to identify all currently firing `ALARM` and `INSUFFICIENT_DATA` states across the region/account.
   - For each firing alarm, call `get_alarm_history` to establish the **exact onset timestamp (UTC)** and determine whether the alarm is sustained, escalating, or flapping.
2. **60-Minute CloudTrail Change Lookback (`cloudtrail` MCP)**:
   - Query `lookup_events` on the `cloudtrail` MCP server across a **60-minute window preceding the alarm onset** to detect infrastructure or configuration mutations:
     - **Compute / Containers**: `UpdateService`, `RegisterTaskDefinition`, `UpdateNodegroupVersion`, `CreatePodIdentityAssociation`, `UpdateFunctionCode`, `UpdateFunctionConfiguration`, `PutFunctionConcurrency`, `RunInstances`, `TerminateInstances`, `StartInstanceRefresh`.
     - **Networking / Edge**: `AuthorizeSecurityGroupIngress`, `RevokeSecurityGroupIngress`, `ModifySecurityGroupRules`, `ReplaceRoute`, `ModifyVpcEndpoint`, `UpdateDistribution`, `UpdateWebACL`, `ChangeResourceRecordSets`.
     - **Data / IAM / KMS**: `ModifyDBCluster`, `ModifyDBInstance`, `FailoverDBCluster`, `UpdateTable`, `PutRolePolicy`, `AttachRolePolicy`, `DisableKey`, `PutSecretValue`.

---

### Phase 2: Multi-Signal Metric Correlation, PromQL & Logs Insights Analysis

Isolate the failing architectural layer using the **Four Golden Signals** (Latency, Traffic, Errors, Saturation):
1. **CloudWatch Metric Math & Percentiles (`cloudwatch` MCP)**:
   - Call `get_metric_data` with multi-metric batching, metric math expressions (e.g., `m_errors / m_requests * 100`), and percentile statistics (`p50`, `p90`, `p99`, `tm99`) rather than `Average` (which hides tail-latency spikes):
     - **Edge (`AWS/CloudFront`, `AWS/WAFV2`)**: `5xxErrorRate`, `4xxErrorRate`, `OriginLatency`, `BlockedRequests`.
     - **Load Balancer (`AWS/ApplicationELB`, `AWS/NetworkELB`)**: `HTTPCode_ELB_5XX_Count` (load balancer / no healthy targets / timeout issue) vs `HTTPCode_Target_5XX_Count` (application crash/error), `TargetResponseTime` (`p95`/`p99`), `UnHealthyHostCount`, `RejectedConnectionCount`.
     - **Compute (`AWS/ECS`, `ContainerInsights`, `AWS/Lambda`, `AWS/EC2`)**: `CPUUtilization`, `MemoryUtilization`, `ConcurrentExecutions`, `Throttles`, `IteratorAge` (for stream consumers), `CPUCreditBalance` (for `t3`/`t4g` instances).
     - **Storage & Data (`AWS/RDS`, `AWS/DynamoDB`, `AWS/ElastiCache`, `AWS/EFS`, `AWS/EBS`)**: `DatabaseConnections`, `ReadLatency`/`WriteLatency`, `FreeableMemory`, `SystemErrors`, `ThrottledRequests`, `EngineCPUUtilization`, `SwapUsage`, `Evictions`, `BurstCreditBalance`, `PercentIOLimit`, `VolumeQueueLength`.
   - Call `analyze_metric` on the `cloudwatch` MCP server to distinguish genuine anomalies from normal diurnal or weekly seasonality.
2. **PromQL Telemetry Analysis for Containers & OTLP Workloads (`cloudwatch` MCP)**:
   - For EKS, ECS, or OpenTelemetry (OTLP)-instrumented workloads, call `get_promql_labels`, `get_promql_series`, `execute_promql_query`, and `execute_promql_range_query` to inspect `@resource.service.name` and `@aws.*` enriched telemetry (pod restarts, container throttling `container_cpu_cfs_throttled_periods_total`, HTTP request duration histograms).
3. **Structured CloudWatch Logs Insights Queries (`cloudwatch` MCP)**:
   - Call `describe_log_groups` and `analyze_log_group`, then run targeted `execute_log_insights_query` + `get_logs_insight_query_results` queries:
     - **Exception & 5xx Signature Clustering**:
       ```sql
       fields @timestamp, @message, @logStream
       | filter @message like /(?i)(error|exception|fatal|panic|timeout|oom|denied)/
       | stats count(*) as errorCount by @logStream
       | sort errorCount desc
       | limit 25
       ```
     - **Lambda Timeout / OOM / Cold-Start Forensics**:
       ```sql
       filter @type = "REPORT"
       | fields @timestamp, @requestId, @duration, @billedDuration, @memorySize/1000000 as memAllocMB, @maxMemoryUsed/1000000 as memUsedMB, @initDuration
       | filter @maxMemoryUsed >= @memorySize * 0.90 or ispresent(@initDuration)
       | sort @duration desc
       | limit 25
       ```

---

### Phase 3: Domain-Specific Deep Dives

Once Phase 2 isolates the failing plane, execute the corresponding deep dive:
- **Amazon EKS (`eks` MCP + `aws-containers`)**:
  - Call `get_eks_insights` to check for upgrade readiness or cluster misconfigurations, `get_eks_vpc_config` to inspect subnet/endpoint reachability, `search_eks_troubleshoot_guide`, and `get_pod_logs` (requesting sensitive data access only if approved).
  - Check for **VPC CNI IP exhaustion** (`FailedCreatePodSandBox: failed to assign an IP address to container` -> enable Prefix Delegation `/28` or Custom Networking), **IMDSv2 hop-limit timeouts** (`HttpPutResponseHopLimit=1` breaking pod SDK calls -> set `HttpPutResponseHopLimit=2`), or **PDB drain deadlocks** (`minAvailable: 100%` or `maxUnavailable: 0`).
- **Amazon ECS / Fargate (`ecs` MCP + `aws-containers`)**:
  - Inspect failed tasks, stopped reasons, and deployment circuit-breaker events via `ecs` MCP tools and ECS Action Logs (`aws-containers`).
  - Common signatures:
    - `CannotPullContainerError` -> task in private subnet missing NAT route or missing `ecr.api` + `ecr.dkr` Interface Endpoints + `s3` Gateway Endpoint (required for ECR image layer pulls from S3!).
    - `ResourceInitializationError: unable to pull secrets or registry auth` -> `ExecutionRoleArn` missing `secretsmanager:GetSecretValue` / `kms:Decrypt` or missing `secretsmanager` VPC endpoint.
    - `OutOfMemoryError: Container killed due to memory usage` (exit code `137`) -> increase task/container memory limit or fix heap settings (`-XX:MaxRAMPercentage=75.0`).
- **Network Path & Hybrid Connectivity (`awsnetwork` MCP + `aws-network-monitoring`)**:
  - Use `awsnetwork` MCP tools to inspect VPC route tables, Security Groups, NACLs, Transit Gateway route tables, and VPC Reachability Analyzer paths.
  - Check for **NAT Gateway port allocation errors** (`ErrorPortAllocation > 0` in `AWS/NATGateway` -> attach additional secondary EIPs or add PrivateLink endpoints), **asymmetric routing across Multi-AZ stateful firewalls** (Transit Gateway attachment missing `ApplianceModeSupport: enable`), or **MTU blackholes** (`8500` jumbo frames dropped over VPN/DX/TGW links limited to `1500` bytes without TCP MSS clamping).
- **Shared File & Object Storage (`troubleshooting-efs`, `troubleshooting-s3-files`)**:
  - Load `troubleshooting-efs` when EFS mounts hang or latency spikes (check `BurstCreditBalance == 0` on Bursting Throughput mode -> switch to Elastic Throughput or Provisioned Throughput; check port `2049` security group rules on mount targets in each AZ).
  - Load `troubleshooting-s3-files` when S3 Files mounts fail or exhibit permission/sync lag.

---

### Phase 4: Declarative Remediation & Preventative Alarming

1. **Evidence-Backed Diagnosis**: Present the exact root cause backed by metric timestamps, log signatures, and CloudTrail event IDs.
2. **Minimal Reversible Fix + IaC Codification**: Propose the least disruptive mitigation first (e.g., Route 53 ARC Zonal Shift away from an impaired AZ, rolling back a bad deployment revision, scaling capacity) and codify the permanent fix in CloudFormation/CDK/Terraform via `aws-iac-cloudformation-cdk`.
3. **Close Observability Blind Spots**: Call `get_recommended_metric_alarms` on the `cloudwatch` MCP server to generate CloudWatch alarm definitions (including composite alarms or anomaly detection bands) for any metric blind spots uncovered during the incident.
