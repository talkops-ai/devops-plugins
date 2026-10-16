# Six-Pillar AWS Well-Architected Automated Evidence Checklist

When executing `aws-well-architected-review`, cross-verify the frozen live framework corpus (`corpus/manifest.json`) against these deterministic MCP evidence sources:

| Pillar | Local IaC & Code Evidence (`iac` MCP + `Grep`/`Read`) | Live AWS Account Evidence (`aws-mcp` + `bcm` MCP) |
|---|---|---|
| **1. Operational Excellence (`OPS`)** | IaC modularity, parameterized environments, X-Ray/ADOT tracing enabled, structured logging, alarm definitions, runbook links | CloudFormation stack drift status, CloudWatch Application Signals SLOs, active alarm coverage |
| **2. Security (`SEC`)** | `cfn-guard` compliance (`check_cloudformation_template_compliance`), IAM least privilege, `aws:SourceArn` confused-deputy guards, KMS CMK encryption, S3 Block Public Access, WAFv2 rules, `.threatmodel/` STRIDE coverage | IAM role trust policies, S3 public access blocks, Security Group `0.0.0.0/0` exposure, unencrypted EBS/RDS resources |
| **3. Reliability (`REL`)** | Multi-AZ subnet placement, RDS Multi-AZ, SQS DLQ `RedrivePolicy`, Lambda `ReservedConcurrentExecutions`, `DeletionPolicy: Retain` on stateful stores, Route 53 ARC readiness | Single-AZ SPOFs, Service Quotas utilization >75%, ASG/ECS health check grace periods, backup plans |
| **4. Performance Efficiency (`PERF`)** | Graviton (`arm64`) architecture selection, CloudFront/ElastiCache Valkey caching layers, RDS Proxy for serverless DB connections, S3 Tables Iceberg partitioning | Compute Optimizer right-sizing recommendations (`get_ec2_instance_recommendations`, `get_lambda_function_recommendations`, `get_rds_database_recommendations`) |
| **5. Cost Optimization (`COST`)** | S3 Gateway Endpoints (avoiding NAT Gateway fees), S3 Intelligent-Tiering & Multipart Abort lifecycle rules, Dev/QA scale-to-zero tiering, cost allocation tags | `bcm` Cost Explorer MoM spend drivers (`get_cost_comparison_drivers`), Cost Anomalies (`get_anomalies`), Idle resources (`get_idle_recommendations`), Savings Plans coverage |
| **6. Sustainability (`SUS`)** | Graviton3/4 (`arm64`) compute, serverless/scale-to-zero runtimes, CloudWatch log retention policies (`RetentionInDays`), S3 lifecycle expiration of transient data | Over-provisioned idle compute instances, unattached EBS volumes, uncompressed Parquet/JSON data lakes |
