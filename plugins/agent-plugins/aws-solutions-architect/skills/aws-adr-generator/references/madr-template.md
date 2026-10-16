# MADR 3.0+ AWS Architectural Decision Record Template

Use this template when writing `docs/adr/ADR-NNNN-<kebab-case-slug>.md` for significant architectural decisions.

```markdown
# ADR-NNNN: <Short Imperative Title of Decision>

- **Status:** Proposed | Accepted | Rejected | Deprecated | Superseded by [ADR-MMMM](./ADR-MMMM-slug.md)
- **Date:** YYYY-MM-DD
- **Decision Makers:** <Engineering / Architecture / Security / FinOps Stakeholders>
- **Reversibility (Door Type):** Type 1 (One-Way Door — High Reversal Cost) | Type 2 (Two-Way Door — Easily Reversible)
- **Target AWS Region(s):** <e.g., us-east-1 (Primary), us-west-2 (DR)>
- **Well-Architected Pillars Impacted:** Operational Excellence | Security | Reliability | Performance Efficiency | Cost Optimization | Sustainability

---

## 1. Context and Problem Statement

<Describe the architectural context, current system state (or greenfield baseline), and the specific technical/business problem that forces a decision now. Cite repository files, IaC templates, or live AWS account findings.>

## 2. Decision Drivers & Quantitative Constraints

- **Throughput & Scale:** <e.g., 2,500 steady RPS, 12,000 peak RPS, 4 KB average payload>
- **Latency SLO:** <e.g., P50 < 25ms, P99 < 120ms>
- **Availability & DR Target:** <e.g., 99.99% SLA, RTO <= 15 min, RPO <= 1 min>
- **Security & Compliance:** <e.g., SOC2 Type II, PCI-DSS, KMS CMK encryption, PrivateLink-only traffic>
- **FinOps Budget Envelope:** <e.g., <= $1,500/month at baseline traffic; scale-to-zero in Dev/QA>
- **Team Operational Constraints:** <e.g., 6 backend engineers, no dedicated Kubernetes platform team>

## 3. Considered Options

1. **Option 1:** <AWS Service / Pattern A — e.g., Amazon ECS Fargate + ALB + Aurora PostgreSQL Serverless v2>
2. **Option 2:** <AWS Service / Pattern B — e.g., AWS Lambda + API Gateway HTTP API + Amazon Aurora DSQL>
3. **Option 3:** <AWS Service / Pattern C — e.g., Amazon EKS Auto Mode + Karpenter + RDS Provisioned Multi-AZ>

## 4. Six-Pillar Well-Architected & TCO Trade-Off Matrix

| Evaluation Dimension | Option 1: <Name> | Option 2: <Name> | Option 3: <Name> |
|---|---|---|---|
| **Operational Excellence** | <Day-2 toil, CI/CD, patching> | <Day-2 toil, CI/CD, patching> | <Day-2 toil, CI/CD, patching> |
| **Security** | <IAM isolation, network perimeter> | <IAM isolation, network perimeter> | <IAM isolation, network perimeter> |
| **Reliability (SLA / Quotas)** | <SLA, AZ fault tolerance, limits> | <SLA, AZ fault tolerance, limits> | <SLA, AZ fault tolerance, limits> |
| **Performance Efficiency** | <Latency, cold starts, scaling> | <Latency, cold starts, scaling> | <Latency, cold starts, scaling> |
| **Cost (Dev/QA Monthly)** | `$XX / mo` | `$XX / mo` | `$XX / mo` |
| **Cost (Prod Baseline Monthly)** | `$XXX / mo` | `$XXX / mo` | `$XXX / mo` |
| **Sustainability** | <Graviton arm64, idle waste> | <Graviton arm64, idle waste> | <Graviton arm64, idle waste> |

## 5. Decision Outcome

**Chosen Option:** **Option X (<Name>)**, because <concise synthesis linking the option's strengths directly to the top Decision Drivers>.

### Positive Consequences
- <Concrete architectural, operational, or cost benefit 1>
- <Concrete architectural, operational, or cost benefit 2>

### Negative Consequences & Technical Mitigations (Mandatory)
- **Risk / Trade-Off 1:** <Concrete limitation, quota ceiling, or cost vector>
  - *Mitigation:* <Specific IaC guardrail, alarm, caching layer, or architectural pattern>
- **Risk / Trade-Off 2:** <Concrete limitation, lock-in, or operational burden>
  - *Mitigation:* <Specific mitigation control>

## 6. Quantitative Re-Evaluation Triggers

This decision must be revisited and potentially superseded if any of the following thresholds are crossed:
- [ ] Monthly workload spend on <service> exceeds `$X,XXX/month` or unit cost exceeds `$0.XX per 1,000 requests`.
- [ ] P99 latency exceeds `<X> ms` or throttling rate exceeds `0.1%` over a 7-day rolling window.
- [ ] Sustained traffic exceeds `<X,XXX> RPS` where <Alternative Option> achieves a lower TCO crossover point.

## 7. Implementation & Compliance Verification Links

- **IaC Blueprints:** `<path/to/cdk-or-cfn-stack>` (Validated via `cfn-lint` and `cfn-guard`)
- **Threat Model:** `.threatmodel/<name>.md`
- **Architecture Diagram:** `docs/<name>.drawio`
```
