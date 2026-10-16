# Amazon DynamoDB Hot Partitions, GSI Backpressure & Warm Throughput Reference

## 1. Hard Physical Partition Limits (Provisioned AND On-Demand!)

Every physical DynamoDB storage partition has hard hardware limits regardless of whether the table uses **Provisioned** or **On-Demand** billing mode:
- **Maximum Read Throughput per Partition**: **3,000 RCU/sec** (3,000 strongly consistent 4 KB reads/sec or 6,000 eventually consistent 4 KB reads/sec).
- **Maximum Write Throughput per Partition**: **1,000 WCU/sec** (1,000 x 1 KB writes/sec).

If a table has 50,000 WCU provisioned (or is On-Demand) across 50 partitions, but 1,500 writes/sec target a **single Partition Key** (`PK = "TENANT#mega-corp"` or `PK = "STATUS#PENDING"`), `WriteThrottleEvents` (`ProvisionedThroughputExceededException`) will fire immediately!

---

## 2. The GSI Write Backpressure Cascading Outage

Global Secondary Indexes (GSIs) are updated asynchronously from the base table via an internal replication buffer.
- **What happens when a GSI is under-provisioned or has a hot GSI Partition Key?**
  1. `OnlineIndexThrottleEvents` / `WriteThrottleEvents` on the GSI spike.
  2. Once the internal base-table-to-GSI replication buffer fills up, **DynamoDB throttles ALL writes to the Base Table** (`WriteThrottleEvents` on the table with `ConsumedWriteCapacityUnits` well below table limits!).
- **Diagnostic Check**:
  Always query `WriteThrottleEvents` and `OnlineIndexThrottleEvents` grouped by **both** `TableName` AND `GlobalSecondaryIndexName` in `cloudwatch.get_metric_data`.

---

## 3. CloudWatch Contributor Insights & Warm Throughput

1. **Identify the Exact Hot Key (`Contributor Insights`)**:
   ```bash
   aws dynamodb describe-contributor-insights --table-name "$TABLE_NAME"
   ```
   When enabled, CloudWatch Contributor Insights generates rules `DynamoDBContributorInsights-PKC-...` and `DynamoDBContributorInsights-THROTTLED-...` showing the top accessed and top throttled Partition + Sort Keys without scanning table items.
2. **Pre-Warming Tables & GSIs (`WarmThroughput`)**:
   Before a major flash sale or data migration, inspect and pre-warm partition capacity using `WarmThroughput`:
   ```bash
   aws dynamodb describe-table --table-name "$TABLE_NAME" --query 'Table.WarmThroughput'
   ```
