# Multi-Region Disaster Recovery (RTO/RPO) & Stateful Replication Reference

## 1. Stateful Multi-Region Database Replication Comparison

| Service / Capability | RPO | RTO | Write Model | Key Architectural Considerations |
|---|---|---|---|---|
| **Amazon Aurora DSQL (Multi-Region)** | `0` (Zero data loss — synchronous multi-region quorum) | Seconds (Automatic active-active) | **Active-Active Multi-Region Strong Consistency** | Two regions linked via a witness region; ideal when zero RPO and active-active SQL writes across regions are mandatory. |
| **Amazon DynamoDB Global Tables (MRSC vs. MREC)** | `0` (MRSC) or `<1s` (MREC) | Seconds | **Active-Active** (Multi-Region Strong Consistency or Eventual Consistency) | Use **MRSC** for financial/inventory ledgers requiring zero RPO across regions; use **MREC** for lowest write latency within each local region. |
| **Amazon Aurora Global Database** | `<1 second` (storage-level replication) | `<1 minute` (Managed Planned Switchover or Unplanned Failover) | **Single Primary Writer Region** + up to 5 Secondary Read Regions (supports **Write Forwarding** from secondary to primary) | Pair with **Aurora Global Database Endpoint (CNAME)** so applications reconnect automatically after region switchover without changing connection strings. |
| **Amazon S3 Cross-Region Replication (CRR) + Replication Time Control (RTC)** | `<15 minutes` (99.99% of objects replicated within 15 min SLA) | Immediate via **S3 Multi-Region Access Points (MRAP)** | Active-Passive or Active-Active bucket replication | Combine **S3 MRAP** (`arn:aws:s3::account:accesspoint/mrap.alias`) with Route 53 ARC fail-over controls for global active-active/active-passive object access. |

## 2. Route 53 Application Recovery Controller (ARC) Blueprint

- **Readiness Checks**: Continuously audit that DR region capacity (Aurora ACUs, ECS task limits, Service Quotas, KMS keys, Secrets Manager replicas) matches the primary region before an outage occurs.
- **Routing Controls**: Expose 5 regionally isolated data-plane cluster endpoints. Never trigger failover by calling `route53:ChangeResourceRecordSets` (control plane); call `route53-recovery-cluster:UpdateRoutingControlStates` against the ARC cluster endpoints.
