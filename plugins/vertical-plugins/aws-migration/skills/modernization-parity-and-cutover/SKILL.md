---
name: modernization-parity-and-cutover
description: "Engineers functional, data, and performance parity for modernized workloads using automated unit tests, Testcontainers (PostgreSQL, Kafka), REST/event contract tests, mainframe batch/online record-replay equivalence testing (EBCDIC collation, COMP-3 precision), Gatling/k6 load baselines, OpenTelemetry/CloudWatch observability, and a deterministic Production Cutover & Rollback Runbook."
---

# Modernization Parity & Production Cutover

## Overview

Modernization projects fail most frequently at the finish line: transformed code compiles and passes local developer spot checks, but subtle functional regressions, data collation discrepancies, or performance bottlenecks emerge under real production loads.

This skill equips Principal Modernization Architects to enforce **deterministic parity verification** across functional, data, and performance dimensions prior to cutover, and to execute **zero-downtime canary production cutovers** with automated rollbacks.

### Mandatory Architectural Guardrail: Zero Big-Bang Cutovers

> **STRICT PROHIBITION: Unverified & Big-Bang Cutovers**
> Never execute an unverified cutover or an all-at-once "big bang" switch from legacy systems to modernized cloud services. 
> 
> All modernizations MUST establish:
> 1. **Functional & Contract Equivalence**: Proven via automated unit tests, Testcontainers integration suites, contract tests (OpenAPI / Pact), and mainframe record-replay testing.
> 2. **Data Parity & Collation Normalization**: Validating EBCDIC vs. ASCII character collation and COBOL `COMP-3` decimal precision against PostgreSQL / Java `BigDecimal`.
> 3. **Performance Baselines**: Proving p50, p95, and p99 latency matches or outperforms legacy systems under Gatling or k6 load tests.
> 4. **Incremental Canary Cutover**: Progressive traffic shifting (1% -> 10% -> 50% -> 100%) governed by automated CloudWatch alarms capable of immediate rollback.

---

## 1. The Three Pillars of Modernization Parity

```
+---------------------------------------------------------------------------------------------------+
| 1. Functional Parity                                                                              |
| - Automated unit & regression test suites covering legacy business logic edge cases.              |
| - Testcontainers ephemeral PostgreSQL and Apache Kafka integration tests in CI/CD.                |
| - REST API contract tests (Pact / OpenAPI) & asynchronous event schema validation.                |
| - Mainframe record-replay equivalence testing (AWS Mainframe Modernization Application Testing).  |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| 2. Data & Semantic Parity                                                                         |
| - Collation order reconciliation (EBCDIC vs ASCII numbers/uppercase/lowercase sorting).           |
| - Numeric precision verification (COBOL COMP-3 packed decimal vs Java BigDecimal/PostgreSQL).    |
| - Ongoing CDC replication lag monitoring via AWS DMS (`CDCLatencyTarget` < 5 seconds).            |
| - Database sequence synchronization (`setval`) preventing primary key collision upon cutover.    |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| 3. Performance & Operational Parity                                                               |
| - High-throughput load benchmarking via k6, Gatling, or Apache JMeter.                            |
| - Latency percentiles SLA gating (p50, p95, p99) under simulated peak concurrent load.           |
| - End-to-end distributed tracing via AWS Distro for OpenTelemetry (ADOT) or Dynatrace.          |
| - CloudWatch Container Insights & Aurora RDS Performance Insights telemetry baselines.          |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Test Execution Workflow

### 2.1 Ephemeral Integration Testing with Testcontainers

Never rely on shared development databases for integration validation. Testcontainers provisions isolated, reproducible containers in the CI/CD pipeline:

```java
@Testcontainers
class OrderServiceParityIT {
    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")
            .withDatabaseName("modernized_db")
            .withUsername("testuser")
            .withPassword("testpass");

    @Container
    static KafkaContainer kafka = new KafkaContainer(DockerImageName.parse("confluentinc/cp-kafka:7.5.0"));
    
    // Executes Flyway migrations and verifies REST + Event contracts against live containers
}
```

### 2.2 Mainframe Record-Replay Equivalence Testing

Mainframe refactoring (AWS Blu Age) or replatforming (Rocket Software) requires bit-level output validation:
1. **Capture Production Traces**: Record legacy batch file inputs (`SYSIN`), database snapshots, and online CICS terminal inputs.
2. **Replay on Modernized Target**: Execute transformed Spring Boot services or Rocket emulation regions against identical inputs.
3. **Collation & Precision Normalization**:
   - Compare outputs using collation-aware diff tools (`diff -u` with locale normalization).
   - Verify `COMP-3` signed fields against `BigDecimal` scale and rounding modes.

---

## 3. Load Benchmarking & Observability Baselining

Execute automated load sweeps using **k6** or **Gatling** against both legacy baseline and modernized targets:

```javascript
// k6 load test script: baseline SLA check
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 50 },  // warm-up
    { duration: '5m', target: 500 }, // peak sustained load
    { duration: '2m', target: 0 },   // cooldown
  ],
  thresholds: {
    'http_req_duration': ['p(95)<250', 'p(99)<500'], // Latency SLAs: p95 < 250ms, p99 < 500ms
    'http_req_failed': ['rate<0.001'],               // Error rate < 0.1%
  },
};
```

Instrument targets with **AWS Distro for OpenTelemetry (ADOT)** and Amazon CloudWatch to observe:
- Database connection pool exhaustion (HikariCP active vs idle connections).
- CPU throttling and memory garbage collection pauses on ECS/EKS/Lambda.
- Aurora PostgreSQL commit latency, cache hit ratios, and buffer pool efficiency.

---

## 4. Production Cutover & Rollback Protocol

Follow a strict, minute-by-minute cutover sequence:

```
[ Pre-Cutover Checks ]
1. Verify AWS DMS ongoing CDC replication lag: `CDCLatencyTarget` < 5 seconds.
2. Lock down legacy write operations / switch legacy app to read-only mode.
3. Wait for CDC queue to drain to 0 seconds.
4. Execute sequence alignment SQL (`SELECT setval(...)`) on target PostgreSQL.
         |
         v
[ Staged Canary Shifting ]
Stage 1: Shift 1% traffic via API Gateway Canary / VPC Lattice. Monitor 15 mins.
Stage 2: Shift 10% traffic. Monitor 30 mins.
Stage 3: Shift 50% traffic. Monitor 60 mins.
Stage 4: Shift 100% traffic. Final verification.
         |
         v
[ Automated CloudWatch Regressions Alarm ]
If 5XX rate > 0.5% OR p95 latency > 500ms -> Trigger automated rollback:
  aws apigateway update-stage --rest-api-id <id> --stage-name prod \
    --patch-operations op=replace,path=/canarySettings/percentTraffic,value=0.0
```

---

## Reference Library

Detailed implementations, test scripts, and operational procedures are documented in `references/`:
- [references/parity-testing-frameworks.md](references/parity-testing-frameworks.md) — Testcontainers setup for PostgreSQL/Kafka, OpenAPI/Pact contract testing, and mainframe record-replay testing architecture.
- [references/performance-benchmarking-observability.md](references/performance-benchmarking-observability.md) — Gatling, JMeter, and k6 load testing scripts, latency percentiles baselines, ADOT, and CloudWatch metrics.
- [references/production-cutover-runbook.md](references/production-cutover-runbook.md) — Minute-by-minute production cutover runbook, sequence synchronization SQL, canary progression, and automated rollback triggers.
