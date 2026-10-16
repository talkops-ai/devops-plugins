# Michael Nygard Concise ADR Template (AWS Edition)

Use this concise format for rapid **Type 2 (Two-Way Door)** decisions or tactical architecture refinements where full MADR tables are unnecessary.

```markdown
# ADR-NNNN: <Title — Short Noun Phrase>

Date: YYYY-MM-DD

## Status

Accepted (Supersedes [ADR-MMMM](./ADR-MMMM.md)) | Reversibility: Type 2 (Two-Way Door)

## Context

<Describe the forces at play: technical, security, cost, operational, and organizational. Explain what AWS service limits, latency targets, or cost anomalies triggered this decision.>

## Decision

We will use **<AWS Service / Configuration / Pattern>** configured with **<key architectural parameters, e.g., Graviton4 arm64, KMS CMK, Multi-AZ, S3 Gateway Endpoint>**.

## Consequences

### Positive
- <Benefit 1 with quantified latency/availability/cost impact>
- <Benefit 2>

### Negative & Mitigations
- <Downside 1> — Mitigated by <control/alarm>.
- <Downside 2> — Mitigated by <control/rollback path>.

### Re-Evaluation Trigger
- Revisit if <specific CloudWatch metric, Cost Explorer threshold, or traffic volume> exceeds <value>.
```
