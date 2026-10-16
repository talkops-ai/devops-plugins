# SRE Observability Cost Traps & Remediation Playbook

Observability spend (CloudWatch Custom Metrics, CloudWatch Logs ingestion, X-Ray traces, VPC Flow Logs, Amazon Managed Service for Prometheus, and NAT Gateway telemetry transit) frequently grows into **15–30% of total AWS infrastructure spend** when left unguarded. Use this playbook during SRE FinOps audits or telemetry bill spikes.

---

## 1. The 6 Highest-Impact Observability Cost Traps

| Cost Trap | Root Cause | Diagnostic Detection | Architectural Fix |
|---|---|---|---|
| **1. High-Cardinality Custom Metrics** | Passing `request_id`, `user_id`, `trace_id`, `container_id`, or `pod_ip` as a CloudWatch Metric Dimension ($0.30/metric/month for first 10,000 metrics). | `cost-explorer` grouped by `USAGE_TYPE` (`MetricMonitorUsage`, `CW:MetricMonitorUsage`) + `cloudwatch.get_metric_metadata` | Strip dynamic dimensions from metrics; emit high-cardinality attributes inside **Embedded Metric Format (EMF)** JSON logs or structured logs queried on-demand via Logs Insights. |
| **2. Duplicate Log Ingestion** | Shipping the same container/application stdout via **both** FluentBit/CloudWatch Agent AND an OpenTelemetry (ADOT) collector, or retaining `DEBUG` logging in production ($0.50/GB Standard ingestion). | Compare `DataProcessing-Bytes` across log groups (`describe-log-groups` `storedBytes` growth rate). | Consolidate to a single collector pipeline; move high-volume debug/access logs to **CloudWatch Logs Infrequent Access (`INFREQUENT_ACCESS` at $0.25/GB — 50% savings)**; enforce mandatory retention policies (`7`, `14`, or `30` days for non-compliance logs). |
| **3. X-Ray / ADOT 100% Trace Sampling** | Leaving default or `1.0` (100%) fixed-rate sampling on high-RPS production services ($5.00 per 1M traces recorded). | Inspect `X-Ray:TracesRecorded` usage type in Cost Explorer + `aws xray get-sampling-rules`. | Configure **X-Ray Reservoir + Fixed Rate Sampling** (e.g., `reservoir_size=1` trace/sec + `fixed_rate=0.05` (5%) for normal 2xx traffic) or **ADOT Tail-Based Sampling** (100% of 5xx/faults and high-latency traces, 1% of healthy 2xx traces). |
| **4. VPC Flow Logs Published to CloudWatch Logs** | Publishing high-throughput VPC Flow Logs directly to CloudWatch Logs Standard ($0.50/GB) instead of S3. | Inspect `DataProcessing-Bytes` on `/aws/vpc/flowlogs*` log groups. | Publish VPC Flow Logs directly to **Amazon S3 in Apache Parquet format with Hive-compatible prefixes and ZSTD/GZIP compression**, queried via Athena or `querying-aws-cloudwatch`. |
| **5. AMP Active Series Explosion** | Scraping unconstrained Kubernetes/cAdvisor/Istio labels (`pod_uid`, `endpoint`, `le` histogram buckets) in Amazon Managed Prometheus. | Run `prometheus.ExecuteQuery` with `topk(20, count by (__name__)({__name__=~".+"}))` to identify metric series cardinality leaders. | Apply Prometheus `metric_relabel_configs` (`action: drop`) for unused high-cardinality labels and migrate high-bucket classic histograms to **Prometheus Native Histograms**. |
| **6. Telemetry Routing Through NAT Gateways** | Private EKS/ECS/EC2 nodes pushing gigabytes of logs/metrics/traces to regional public endpoints via NAT Gateways ($0.045/GB processing). | Correlate `NatGateway-Bytes` with VPC Flow Logs destined for CloudWatch/X-Ray public IPs. | Provision **Interface VPC Endpoints (AWS PrivateLink)** for `com.amazonaws.<region>.logs`, `com.amazonaws.<region>.monitoring`, `com.amazonaws.<region>.xray`, and `com.amazonaws.<region>.aps-workspaces`. |

---

## 2. Diagnostic Commands for Observability Spend Triage

### Break Down CloudWatch Usage Types (Cost Explorer)
```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-03-01,End=2026-04-01 \
  --granularity MONTHLY \
  --metrics UnblendedCost UsageQuantity \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["AmazonCloudWatch"]}}' \
  --group-by Type=DIMENSION,Key=USAGE_TYPE
```

### Audit Log Groups Missing Retention Policies (`Never Expire`) or Using Standard Class
```bash
aws logs describe-log-groups \
  --query 'logGroups[?retentionInDays==`null`].[logGroupName,storedBytes,logGroupClass]' \
  --output table
```

### Identify Top 20 Highest-Cardinality Metric Names in AMP
```promql
topk(20, count by (__name__)({__name__=~".+"}))
```
