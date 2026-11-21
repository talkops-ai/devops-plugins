# CloudWatch Alarms, Application Signals SLOs & OpenTelemetry Reference

## 1. Golden Signals SLO & Alarm Architecture

Every production architecture designed by the Solutions Architect must specify **Service Level Objectives (SLOs)** in **Amazon CloudWatch Application Signals** alongside multi-window burn-rate alarms:

| Golden Signal | Target AWS Metric / Telemetry Source | Recommended Alarm Threshold |
|---|---|---|
| **Latency** | `AWS/ApplicationELB TargetResponseTime` (`p99`), `AWS/ApiGateway Latency` (`p99`), Application Signals `Latency` | `p99 > SLO_MS` for `3 out of 5` datapoints (`Period: 60s`) |
| **Traffic / Demand** | `AWS/ApplicationELB RequestCount`, `AWS/Lambda Invocations`, `AWS/SQS NumberOfMessagesSent` | CloudWatch **Metric Anomaly Detection** (`ANOMALY_DETECTION_BAND(m1, 3)`) |
| **Errors** | `HTTPCode_Target_5XX_Count / RequestCount * 100`, `AWS/Lambda Errors`, Application Signals `Fault` | Error rate `> 1.0%` (fast burn) or `> 0.1%` sustained |
| **Saturation** | `ECS CPUUtilization / MemoryUtilization`, `RDS DatabaseConnections`, `SQS ApproximateAgeOfOldestMessage` | Saturation `> 80%` or `ApproximateAgeOfOldestMessage > SLA_SECONDS` |

## 2. AWS Distro for OpenTelemetry (ADOT) & X-Ray Pipeline

- **Zero-Code Auto-Instrumentation**: Enable **CloudWatch Application Signals** on EKS (via EKS Add-on `amazon-cloudwatch-observability`), ECS (sidecar ADOT collector), and Lambda (ADOT Layer + `Tracing: Active`) to automatically populate service maps, RED metrics (Rate, Errors, Duration), and X-Ray trace spans correlated with database and Bedrock calls.
- **High-Cardinality Container Metrics**: Route Prometheus scrape targets from EKS/ECS through the ADOT Collector to **Amazon Managed Service for Prometheus (AMP)** with `sigv4auth`, and visualize via **Amazon Managed Grafana (AMG)**.
