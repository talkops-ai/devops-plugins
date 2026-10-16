---
name: provisioning-data-infrastructure-iac
description: >-
  Packages AWS data engineering pipelines, Amazon S3 Tables (Iceberg), AWS Glue Data Catalogs,
  Connections, Jobs, and Data Quality rulesets, Amazon Redshift Serverless workgroups, Kinesis/MSK/
  Firehose streams, AWS Step Functions, Amazon MWAA, and Lake Formation grants into repeatable AWS
  CDK (TypeScript/Python), CloudFormation, or Terraform templates with built-in FinOps cost
  guardrails.
version: 1
---

# Provisioning Data Infrastructure as Code (CDK, CloudFormation, Terraform) & Data FinOps

Use this skill when packaging data engineering resources (**Amazon S3 Tables**, **AWS Glue Jobs/Connections/Catalogs**, **Amazon Redshift Serverless**, **Amazon Data Firehose**, **AWS Step Functions**, **Amazon MWAA**, and **AWS Lake Formation**) into reproducible **AWS CDK**, **AWS CloudFormation**, or **Terraform** stacks, or when applying **Data FinOps guardrails** to prevent runaway analytical compute/storage spend.

## Reference Library (Load On-Demand)

- **[references/data-lakehouse-cdk-cfn-finops.md](references/data-lakehouse-cdk-cfn-finops.md)** — Load for production AWS CDK (TypeScript) and CloudFormation/Terraform blueprints covering S3 Tables (`AWS::S3Tables::TableBucket`), Glue 5.1+ Jobs with Auto Scaling, Athena Workgroups with `BytesScannedCutoffPerQuery`, Redshift Serverless Workgroups with RPU `maxCapacity` and usage limits, and S3 Intelligent-Tiering/Glacier lifecycle configurations.

---

## Deterministic Data IaC & FinOps Design Rules

1. **Separate Stateful Storage Stacks from Stateless Pipeline Stacks:**
   - **Stateful Foundation Stack (`RemovalPolicy.RETAIN` / `DeletionPolicy: Retain`):** S3 Data Lake buckets, S3 Table Buckets (`AWS::S3Tables::TableBucket`), KMS Customer Managed Keys, Glue Data Catalog databases, Redshift Serverless Namespaces, and Lake Formation permissions. Never allow `cdk destroy` or stack rollback to delete production analytical tables!
   - **Stateless Pipeline Stack:** Glue ETL Jobs, Data Quality rulesets, EMR Serverless applications, Data Firehose streams, Step Functions state machines, EventBridge schedules, and MWAA DAG configurations.
2. **Enforce Mandatory Data FinOps Cost Guardrails in Every IaC Template:**
   - **Amazon Athena Workgroups (`AWS::Athena::WorkGroup`):** Always set `EnforceWorkGroupConfiguration: true` and `BytesScannedCutoffPerQuery` (e.g., `107374182400` = 100 GB per query) so an unpartitioned `SELECT *` cannot scan 50 TB and incur $250+ in a single query.
   - **Amazon Redshift Serverless (`AWS::RedshiftServerless::Workgroup` & `UsageLimit`):** Always set `MaxCapacity` (RPU ceiling) alongside `baseCapacity` and attach a daily/monthly `UsageLimit` (`breachAction: "deactivate"` or `"emit-metric"`).
   - **AWS Glue Jobs (`AWS::Glue::Job`):** Always set `--enable-auto-scaling: "true"`, `Timeout` (e.g., `120` minutes instead of the 2,880-minute 48-hour default!), and `MaxConcurrentRuns` to prevent runaway stuck Spark jobs.
   - **Amazon S3 Lakehouse Buckets (`AWS::S3::Bucket`):** Configure `IntelligentTieringConfiguration` or `LifecycleConfiguration` rules to expire incomplete multipart uploads after 7 days (`AbortIncompleteMultipartUpload`) and transition cold Bronze/archive data to `GLACIER_IR`.
3. **Pre-Deployment Shift-Left Validation:**
   - Synthesize CDK stacks (`cdk synth`) and validate templates for syntax, least-privilege IAM, and KMS encryption before deployment. For complex multi-environment CI/CD pipeline deployment, coordinate with `aws-iac-engineer`.
