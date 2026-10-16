# Sequential Aurora Cluster & Instance Provisioning (with AWS Secrets Manager)

## Overview

This reference defines the step-by-step Standard Operating Procedure (SOP) for creating a complete, VPC-backed (full configuration) Amazon Aurora PostgreSQL cluster by first creating an empty Aurora DB cluster with AWS Secrets Manager master password management (`--manage-master-user-password`), polling until the cluster reaches `available` status, and then provisioning one or more DB instances (Writer and optional Readers) attached to the cluster.

> **Note:** For single-API-call Express Configuration (`--with-express-configuration`), follow [express-create-instructions.md](express-create-instructions.md) instead. Use this two-step flow whenever full configuration is required (customer VPC, custom KMS key, custom parameter group at creation, or pinned engine version).

## Parameters

- **cluster_identifier** (required): Unique identifier for the Aurora DB cluster (`^[a-zA-Z][a-zA-Z0-9-]{0,62}$`)
- **instance_identifier** (required): Unique identifier for the primary Aurora writer instance
- **engine** (required): `aurora-postgresql`
- **engine_version** (optional): Specific Aurora PostgreSQL engine version (e.g., `16.4`; validate via `describe-db-engine-versions`)
- **master_username** (required): Non-default master username for the cluster
- **instance_class** (required): Compute class (`db.serverless` when using Aurora Serverless v2 with `--serverless-v2-scaling-configuration`, or a provisioned class such as `db.r7g.large` / `db.r6g.large`)
- **database_name** (optional): Initial database name to create on the cluster
- **vpc_security_group_ids** (optional): VPC security group IDs controlling inbound port `5432`
- **db_subnet_group_name** (optional): DB subnet group spanning at least 2 Availability Zones
- **db_cluster_parameter_group_name** (optional): Custom DB cluster parameter group (never modify the default group)
- **storage_type** (optional): `aurora` (Standard) or `aurora-iopt1` (I/O-Optimized when I/O exceeds 25% of cluster spend)
- **backup_retention_period** (optional, default: `7`): Automated backup retention days (1–35)
- **preferred_backup_window** (optional): Daily UTC backup window (e.g., `03:00-04:00`)
- **preferred_maintenance_window** (optional): Weekly UTC maintenance window (e.g., `sun:04:00-sun:05:00`)
- **storage_encrypted** (optional, default: `true`): Enable KMS encryption at rest
- **kms_key_id** (optional): Customer-managed KMS key ARN/ID for storage encryption

## Execution Steps

### 1. Verify Dependencies & AWS Identity

- Verify `aws___call_aws` (via `aws-mcp`) or the AWS CLI is available.
- Confirm the active AWS account and region with `aws sts get-caller-identity`.
- Never accept, generate, or print plaintext passwords; always use `--manage-master-user-password`.

### 2. Create the Aurora DB Cluster (`create-db-cluster`)

Execute `aws rds create-db-cluster` (after explicit user confirmation):

```bash
aws rds create-db-cluster \
  --db-cluster-identifier <cluster_identifier> \
  --engine aurora-postgresql \
  --engine-version <engine_version> \
  --master-username <master_username> \
  --manage-master-user-password \
  --master-user-secret-kms-key-id alias/aws/secretsmanager \
  --storage-encrypted \
  --kms-key-id <kms_key_id> \
  --db-subnet-group-name <db_subnet_group_name> \
  --vpc-security-group-ids <vpc_security_group_ids> \
  --backup-retention-period 7 \
  --deletion-protection \
  --enable-cloudwatch-logs-exports '["postgresql"]' \
  --tags Key=created_by,Value=aurora-skill Key=generation_model,Value=<model_id>
```

- If using **Aurora Serverless v2**, include `--serverless-v2-scaling-configuration MinCapacity=<min_acu>,MaxCapacity=<max_acu>` on the cluster and use `--db-instance-class db.serverless` on the instance.
- Capture `DBCluster.MasterUserSecret.SecretArn` from the response.

### 3. Monitor Cluster Creation Status

Poll cluster status until `DBClusters[0].Status` is `"available"`:

```bash
aws rds describe-db-clusters \
  --db-cluster-identifier <cluster_identifier> \
  --query 'DBClusters[0].{Status:Status,Endpoint:Endpoint,ReaderEndpoint:ReaderEndpoint,SecretArn:MasterUserSecret.SecretArn}'
```

- Abort and surface the failure reason if the cluster enters `"failed"` or remains pending beyond 20 minutes.

### 4. Provision the Writer (and Optional Reader) DB Instance (`create-db-instance`)

Once the cluster is available, attach the primary writer instance so the cluster becomes queryable:

```bash
aws rds create-db-instance \
  --db-instance-identifier <instance_identifier> \
  --db-cluster-identifier <cluster_identifier> \
  --engine aurora-postgresql \
  --db-instance-class <instance_class> \
  --no-publicly-accessible \
  --enable-performance-insights \
  --performance-insights-retention-period 7 \
  --tags Key=created_by,Value=aurora-skill Key=generation_model,Value=<model_id>
```

- Do **not** pass `--master-username` or password parameters to `create-db-instance` — authentication is inherited from the Aurora cluster.
- Never pass `--publicly-accessible`.

### 5. Monitor Instance Creation & Validate Final Setup

Poll `aws rds describe-db-instances --db-instance-identifier <instance_identifier>` until `DBInstanceStatus` reaches `"available"`. Then output a concise summary table with:
- Cluster Writer Endpoint (`Endpoint`) and Reader Endpoint (`ReaderEndpoint`)
- Port (`5432`) and Database Name
- Master Username and AWS Secrets Manager Secret ARN (`MasterUserSecret.SecretArn`)
- Reminder to create a least-privilege application role and read-only MCP inspection role (`ALTER ROLE ... SET default_transaction_read_only = on;`, no `rds_superuser` or `postgres_fdw` privileges) rather than connecting as `rds_superuser`.
