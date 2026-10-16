# Performance Benchmarking & Observability Baselines

## 1. Overview

Migrating or modernizing legacy workloads to AWS must not introduce performance regressions. Performance parity engineering establishes verifiable baselines for:
1. **Latency Percentiles**: Ensuring median (p50), 95th percentile (p95), and 99th percentile (p99) latencies are equal to or lower than the legacy baseline under identical load.
2. **Throughput (Transactions Per Second / RPS)**: Proving the target architecture supports peak business volumes with predictable autoscaling.
3. **Resource Efficiency**: Monitoring CPU, memory, database connection pools, and network I/O.
4. **Distributed Observability**: Instrumenting services with AWS Distro for OpenTelemetry (ADOT), Dynatrace, and Amazon CloudWatch Container Insights.

---

## 2. Load Testing Tools & Harnesses

### 2.1 k6 Distributed Load Test Script

k6 provides scriptable, lightweight JavaScript load generation with built-in threshold gating:

```javascript
// load-tests/api-parity-benchmark.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// Custom metric tracking
const failureRate = new Rate('failed_requests');
const transactionLatency = new Trend('transaction_duration');

export const options = {
  scenarios: {
    // Ramp up through peak load
    gradual_ramp: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '3m', target: 100 },  // Baseline ramp
        { duration: '5m', target: 500 },  // Sustained peak load
        { duration: '2m', target: 1000 }, // Stress spike
        { duration: '2m', target: 0 },    // Ramp-down
      ],
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    // Parity gates: Fail CI/CD if latency exceeds baseline SLAs
    'http_req_duration': [
      'p(50) < 50',   // Median latency under 50ms
      'p(95) < 200',  // 95% of requests under 200ms
      'p(99) < 500',  // 99% of requests under 500ms
    ],
    'failed_requests': ['rate < 0.001'], // Less than 0.1% failure rate
  },
};

const BASE_URL = __ENV.TARGET_URL || 'https://api-modernized.internal.talkops.net';

export default function () {
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-Correlation-ID': `k6-${__VU}-${__ITER}`,
    },
    timeout: '5s',
  };

  const payload = JSON.stringify({
    customerId: 'CUST-88392',
    lineItems: [
      { sku: 'ITEM-101', quantity: 2, unitPrice: 24.50 },
      { sku: 'ITEM-202', quantity: 1, unitPrice: 89.99 }
    ]
  });

  const res = http.post(`${BASE_URL}/api/v1/orders/checkout`, payload, params);

  const passed = check(res, {
    'status is 200 or 201': (r) => r.status === 200 || r.status === 201,
    'has transaction ID': (r) => r.json('orderId') !== undefined,
  });

  failureRate.add(!passed);
  transactionLatency.add(res.timings.duration);

  // Paced user think time
  sleep(0.5);
}
```

Execute k6 test:
```bash
# Run local k6 benchmark and output summary metrics
k6 run --env TARGET_URL=https://api.modernized.example.com load-tests/api-parity-benchmark.js
```

---

### 2.2 Gatling Simulation (Scala / Java)

For high-concurrency enterprise batch and online transaction benchmarking:

```scala
package simulations

import io.gatling.core.Predef._
import io.gatling.http.Predef._
import scala.concurrent.duration._

class ModernizedApiSimulation extends Simulation {

  val httpProtocol = http
    .baseUrl("https://api-modernized.internal.talkops.net")
    .acceptHeader("application/json")
    .userAgentHeader("Gatling/ModernizationParitySuite")

  val scn = scenario("Order Processing Workflow")
    .exec(
      http("Get Customer Profile")
        .get("/api/v1/customers/CUST-1001")
        .check(status.is(200))
    )
    .pause(200.milliseconds)
    .exec(
      http("Submit Order")
        .post("/api/v1/orders")
        .body(StringBody("""{"customerId":"CUST-1001","amount":199.50}""")).asJson
        .check(status.in(200, 201))
        .check(jsonPath("$.orderId").saveAs("orderId"))
    )

  setUp(
    scn.inject(
      rampUsersPerSec(10).to(300).during(5.minutes),
      constantUsersPerSec(300).during(10.minutes)
    ).protocols(httpProtocol)
  ).assertions(
    global.responseTime.percentile(95).lt(250),
    global.responseTime.percentile(99).lt(600),
    global.successfulRequests.percent.gt(99.9)
  )
}
```

---

### 2.3 Apache JMeter Parameter Sweeps

JMeter supports distributed test execution for legacy SOAP, JDBC, and REST interfaces simultaneously:
- Use **JMeter CLI** for automated execution in pipelines:
  ```bash
  jmeter -n -t test-plans/modernization-suite.jmx -l results/run.jtl -e -o results/html-report \
    -Jthreads=500 -Jrampup=120 -Jduration=600 -JtargetHost=aurora-pg.internal
  ```

---

## 3. Observability & Telemetry Instrumentation

### 3.1 AWS Distro for OpenTelemetry (ADOT)

Instrument ECS tasks and EKS pods with the ADOT collector to export traces and metrics to Amazon CloudWatch, AWS X-Ray, or Dynatrace.

#### ADOT Sidecar Configuration for Amazon ECS (`ecs-adot-collector.json`)

```json
{
  "name": "aws-otel-collector",
  "image": "public.ecr.aws/aws-observability/aws-otel-collector:v0.38.0",
  "essential": false,
  "environment": [
    {
      "name": "AWS_PROMETHEUS_ENDPOINT",
      "value": "https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-12345/api/v1/remote_write"
    }
  ],
  "command": ["--config=/etc/ecs/ecs-cloudwatch-xray.yaml"],
  "logConfiguration": {
    "logDriver": "awslogs",
    "options": {
      "awslogs-group": "/ecs/modernized-service-adot",
      "awslogs-region": "us-east-1",
      "awslogs-stream-prefix": "otel"
    }
  }
}
```

#### Application Auto-Instrumentation (Java Spring Boot)

Add the OpenTelemetry Java Agent to container entrypoints:

```dockerfile
# Dockerfile snippet
ENV JAVA_TOOL_OPTIONS="-javaagent:/opt/opentelemetry-javaagent.jar \
  -Dotel.service.name=order-service \
  -Dotel.traces.exporter=otlp \
  -Dotel.metrics.exporter=otlp \
  -Dotel.exporter.otlp.endpoint=http://localhost:4317"
```

---

### 3.2 CloudWatch Container Insights

Enable Container Insights on Amazon ECS clusters and Amazon EKS to capture CPU, memory, filesystem, and network interface saturation:

```bash
# Enable Container Insights on Amazon ECS cluster
aws ecs update-cluster-settings \
  --cluster modernized-production-cluster \
  --settings name=containerInsights,value=enabled

# For Amazon EKS, deploy the CloudWatch Observability EKS add-on
aws eks create-addon \
  --cluster-name modernized-production-eks \
  --addon-name amazon-cloudwatch-observability
```

---

### 3.3 Target Database Telemetry (Amazon Aurora PostgreSQL)

Monitor database health during load tests using CloudWatch and Aurora Performance Insights:

| Metric | Target SLA Threshold | Remediation if Exceeded |
|---|---|---|
| **CPUUtilization** | `< 65%` under peak load | Upsize DB instance class or enable Aurora Auto Scaling read replicas. |
| **DatabaseConnections** | `< 80%` of `max_connections` | Deploy **Amazon RDS Proxy** to multiplex connections. |
| **BufferCacheHitRatio** | `> 99.0%` | Increase instance memory; tune shared buffers and query indexing. |
| **CommitLatency** | `< 5 ms` | Check write IOPS, WAL storage throughput, and multi-AZ synchronous replication. |
| **FreeableMemory** | `> 2 GB` | Mitigate potential OOM issues; review `work_mem` and `maintenance_work_mem`. |

---

## 4. Latency Parity SLA Comparison Table

Prior to approving production cutover, compile and sign off on the comparison matrix:

| Metric / Scenario | Legacy Monolith Baseline | Modernized Target (EKS/ECS) | Delta (%) | Status |
|---|---|---|---|---|
| **P50 Latency (Normal Load)** | 42 ms | 28 ms | -33.3% (Faster) | **PASS** |
| **P95 Latency (Peak Load)** | 210 ms | 145 ms | -30.9% (Faster) | **PASS** |
| **P99 Latency (Peak Load)** | 520 ms | 380 ms | -26.9% (Faster) | **PASS** |
| **Max Throughput (RPS)** | 850 RPS | 2,400 RPS | +182% (Higher capacity) | **PASS** |
| **Error Rate (5XX)** | 0.04% | 0.008% | -80% (More reliable) | **PASS** |
| **Batch Job Duration (Daily)** | 4 hrs 12 mins | 1 hr 25 mins | -66.3% (Faster) | **PASS** |
