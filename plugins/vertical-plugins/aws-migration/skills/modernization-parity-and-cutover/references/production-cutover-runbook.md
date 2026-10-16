# Production Cutover & Rollback Runbook

## 1. Overview

This document defines the deterministic, minute-by-minute execution runbook for transitioning production traffic from legacy systems to modernized AWS environments. 

By enforcing:
1. **Pre-Cutover Data Verification**: DMS ongoing Change Data Capture (CDC) replication lag checks (`CDCLatencyTarget` < 5s).
2. **Database Sequence Synchronization**: Updating PostgreSQL sequence state (`setval`) to prevent primary key collisions.
3. **Staged Canary Traffic Shifting**: Progressive canary weight escalation (1% -> 10% -> 50% -> 100%) via Amazon API Gateway and Amazon VPC Lattice.
4. **Automated CloudWatch Rollback Alarms**: Immediate, autonomous traffic rollback if 5XX errors or latency thresholds breach SLAs.
5. **DNS Finalization**: Updating Amazon Route 53 records with minimal TTL risk.

---

## 2. Pre-Cutover Checklist (T - 24 Hours to T - 1 Hour)

| Time | Action | Command / Query | Expected Output / SLA | Owner |
|---|---|---|---|---|
| **T-24h** | Lower Route 53 DNS TTL | Set TTL on `api.production.talkops.net` to `60` seconds | DNS TTL propagation complete across resolvers | Network Lead |
| **T-12h** | Verify Target Cluster Capacity | Check ECS/EKS autoscaling min/max pods and warm capacity | Target capacity scaled to handle 100% load | Infra Lead |
| **T-4h** | Verify DMS CDC Replication Lag | Inspect CloudWatch `CDCLatencyTarget` metric | `CDCLatencyTarget` < 5 seconds consistently | Data Architect |
| **T-2h** | Smoke Test Target Staging Stage | Execute automated test suite against target canary deployment | 100% tests pass, zero 5XX errors | QA Lead |
| **T-1h** | Go / No-Go Decision Gate | Stakeholder review of pre-requisites and rollback readiness | Explicit approval logged in change ticket | Incident Commander |

---

## 3. Minute-by-Minute Cutover Execution Timeline (T - 0 to T + 120 Minutes)

### T - 00:00: Freeze Writes on Legacy System
Place the legacy application in read-only maintenance mode or temporarily pause inbound transaction processing:
```bash
# Example: Disable write routes or set maintenance flag
curl -X POST https://legacy.internal/admin/maintenance-mode -d "enabled=true"
```

### T - 00:05: Drain DMS Ongoing CDC & Verify Zero Replication Lag
Monitor AWS DMS until `CDCLatencyTarget` reaches zero, ensuring all pending transactions from the legacy source database (Oracle / SQL Server) are committed to Amazon Aurora PostgreSQL:

```bash
# Query DMS replication task status via AWS CLI
aws dms describe-replication-tasks \
  --filters Name=replication-task-id,Values=monolith-to-aurora-cdc \
  --query "ReplicationTasks[0].[Status,ReplicationTaskStats.CDCLatencyTarget]"
```
**Gate Requirement**: Status must be `running`, and `CDCLatencyTarget` must equal `0` seconds.

### T - 00:10: Synchronize PostgreSQL Primary Key Sequences
Because heterogeneous replication tools (like AWS DMS) replicate raw table data without advancing underlying PostgreSQL sequences (`BIGSERIAL` / `nextval`), run the sequence alignment script to prevent duplicate key constraint violations (`23505`):

```sql
-- Sequence synchronization script executed on Amazon Aurora PostgreSQL
DO $$
DECLARE
    seq RECORD;
BEGIN
    FOR seq IN 
        SELECT 
            s.relname AS seq_name,
            t.relname AS table_name,
            c.attname AS column_name,
            n.nspname AS schema_name
        FROM pg_class s
        JOIN pg_depend d ON d.objid = s.oid
        JOIN pg_class t ON d.refobjid = t.oid
        JOIN pg_attribute c ON (d.refobjid = c.attrelid AND d.refobjsubid = c.attnum)
        JOIN pg_namespace n ON n.oid = s.relnamespace
        WHERE s.relkind = 'S' 
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
    LOOP
        EXECUTE format(
            'SELECT setval(%L, COALESCE((SELECT MAX(%I) FROM %I.%I), 0) + 1000, true);',
            seq.schema_name || '.' || seq.seq_name,
            seq.column_name,
            seq.schema_name,
            seq.table_name
        );
        RAISE NOTICE 'Updated sequence % for table %.%', seq.seq_name, seq.schema_name, seq.table_name;
    END LOOP;
END $$;
```

---

## 4. Staged Canary Traffic Shifting Progression

Rather than switching all traffic at once, route traffic incrementally using Amazon API Gateway Stage Canary deployments and Amazon VPC Lattice service network weights:

```
+---------------------------------------------------------------------------------------------------+
| T + 15m: Stage 1 (1% Canary Traffic)                                                              |
| - Route 1% of live requests to modernized container / microservice backend.                       |
| - Observe logs, error counts, and latency for 15 minutes.                                         |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| T + 30m: Stage 2 (10% Canary Traffic)                                                             |
| - Step up canary percentage to 10%.                                                               |
| - Monitor database connection pool usage, lock contention, and cache hit ratios.                  |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| T + 60m: Stage 3 (50% Canary Traffic)                                                             |
| - Step up canary percentage to 50%.                                                               |
| - Verify microservice autoscaling events and downstream event-bus propagation.                    |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| T + 90m: Stage 4 (100% Cutover)                                                                   |
| - Promote canary to 100% production traffic.                                                      |
| - Decommission canary split and stabilize monitoring.                                            |
+---------------------------------------------------------------------------------------------------+
```

### AWS CLI Commands for Canary Progression

```bash
# Stage 1: Shift 1% to Canary
aws apigateway update-stage \
  --rest-api-id abc123def \
  --stage-name prod \
  --patch-operations op=replace,path=/canarySettings/percentTraffic,value=1.0

# Stage 2: Shift 10% to Canary
aws apigateway update-stage \
  --rest-api-id abc123def \
  --stage-name prod \
  --patch-operations op=replace,path=/canarySettings/percentTraffic,value=10.0

# Stage 3: Shift 50% to Canary
aws apigateway update-stage \
  --rest-api-id abc123def \
  --stage-name prod \
  --patch-operations op=replace,path=/canarySettings/percentTraffic,value=50.0

# Stage 4: Promote Canary to 100% Production
aws apigateway update-stage \
  --rest-api-id abc123def \
  --stage-name prod \
  --patch-operations op=replace,path=/canarySettings/percentTraffic,value=100.0
```

---

## 5. Automated Rollback Configuration & Runbook

### 5.1 CloudWatch Automated Rollback Alarms

Configure CloudWatch alarms that trigger immediate, automated traffic rollbacks when error or latency limits are breached:

```bash
# Create CloudWatch Alarm for Canary 5XX Errors
aws cloudwatch put-metric-alarm \
  --alarm-name "ModernizedCanary-High5XXErrors" \
  --alarm-description "Triggers automatic rollback if canary 5XX error count exceeds threshold" \
  --metric-name 5XXError \
  --namespace AWS/ApiGateway \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 5 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --dimensions Name=ApiName,Value=OrderModernizationApi Name=Stage,Value=prod \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:modernization-rollback-sns

# Create CloudWatch Alarm for Canary High Latency
aws cloudwatch put-metric-alarm \
  --alarm-name "ModernizedCanary-HighLatency" \
  --alarm-description "Triggers rollback if canary p95 latency exceeds 500ms" \
  --metric-name IntegrationLatency \
  --namespace AWS/ApiGateway \
  --extended-statistic "p95" \
  --period 60 \
  --evaluation-periods 3 \
  --threshold 500 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ApiName,Value=OrderModernizationApi Name=Stage,Value=prod \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:modernization-rollback-sns
```

### 5.2 Emergency Instant Rollback Command

If an anomaly is detected during any canary stage, execute instant rollback within 5 seconds:

```bash
# Revert Canary Traffic immediately to 0.0%
aws apigateway update-stage \
  --rest-api-id abc123def \
  --stage-name prod \
  --patch-operations op=replace,path=/canarySettings/percentTraffic,value=0.0
```

---

## 6. Route 53 DNS Finalization

Once the modernized architecture runs stably at 100% for at least 60 minutes:
1. Update Amazon Route 53 alias records to point directly to the modernized API Gateway / CloudFront distribution.
2. Restore DNS TTL from 60 seconds back to standard production value (300 seconds).
3. Keep legacy infrastructure in read-only standby for 7 days before final decommissioning.
