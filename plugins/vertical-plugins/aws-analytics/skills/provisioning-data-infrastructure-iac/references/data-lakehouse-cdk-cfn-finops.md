# AWS CDK & CloudFormation Lakehouse Blueprints and FinOps Cost Guardrails

Use this reference when generating AWS CDK (TypeScript/Python), CloudFormation, or Terraform templates for data lakehouse infrastructure with built-in cost and security guardrails.

---

## 1. AWS CDK (TypeScript) Lakehouse Foundation Blueprint (S3 Tables + Athena Cost-Capped Workgroup + Glue 5.1 Job)

```typescript
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3tables from 'aws-cdk-lib/aws-s3tables';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as athena from 'aws-cdk-lib/aws-athena';
import * as glue from 'aws-cdk-lib/aws-glue';
import * as iam from 'aws-cdk-lib/aws-iam';

export class LakehouseDataPlatformStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // 1. Customer-Managed KMS Key with Annual Rotation
    const dataLakeKmsKey = new kms.Key(this, 'DataLakeKmsKey', {
      enableKeyRotation: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      alias: 'alias/lakehouse-data-platform',
    });

    // 2. Managed Apache Iceberg Table Bucket (Amazon S3 Tables) with Unreferenced File Removal
    const tableBucket = new s3tables.CfnTableBucket(this, 'AnalyticsTableBucket', {
      tableBucketName: `${cdk.Stack.of(this).account}-${cdk.Stack.of(this).region}-lakehouse`,
      encryptionConfiguration: {
        sseAlgorithm: 'aws:kms',
        kmsKeyArn: dataLakeKmsKey.keyArn,
      },
      unreferencedFileRemoval: {
        status: 'Enabled',
        unreferencedDays: 3,
        noncurrentDays: 7,
      },
    });
    tableBucket.applyRemovalPolicy(cdk.RemovalPolicy.RETAIN);

    // 3. Raw Landing & Athena Results S3 Bucket with FinOps Multipart Cleanup & Intelligent-Tiering
    const rawBucket = new s3.Bucket(this, 'RawLandingBucket', {
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: dataLakeKmsKey,
      bucketKeyEnabled: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      objectOwnership: s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
      enforceSSL: true,
      versioned: true,
      eventBridgeEnabled: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      lifecycleRules: [
        {
          id: 'AbortIncompleteMultipartUploads7d',
          abortIncompleteMultipartUploadAfter: cdk.Duration.days(7),
        },
        {
          id: 'TransitionRawArchiveAfter90d',
          transitions: [
            {
              storageClass: s3.StorageClass.GLACIER_INSTANT_RETRIEVAL,
              transitionAfter: cdk.Duration.days(90),
            },
          ],
        },
      ],
    });

    // 4. Cost-Bounded Amazon Athena Workgroup (100 GB Per-Query Scan Limit + Enforced KMS)
    new athena.CfnWorkGroup(this, 'AnalyticsWorkGroup', {
      name: 'analytics-production',
      state: 'ENABLED',
      workGroupConfiguration: {
        enforceWorkGroupConfiguration: true,
        publishCloudWatchMetricsEnabled: true,
        bytesScannedCutoffPerQuery: 107_374_182_400, // 100 GiB hard ceiling per query
        engineVersion: {
          selectedEngineVersion: 'Athena engine version 3',
        },
        resultConfiguration: {
          outputLocation: `s3://${rawBucket.bucketName}/athena-results/`,
          encryptionConfiguration: {
            encryptionOption: 'SSE_KMS',
            kmsKey: dataLakeKmsKey.keyArn,
          },
        },
      },
    });

    // 5. AWS Glue 5.1 PySpark Job with Auto Scaling & 120-Minute Timeout Ceiling
    const glueRole = new iam.Role(this, 'GlueEtlExecutionRole', {
      assumedBy: new iam.ServicePrincipal('glue.amazonaws.com'),
    });
    rawBucket.grantReadWrite(glueRole);
    dataLakeKmsKey.grantEncryptDecrypt(glueRole);

    new glue.CfnJob(this, 'BronzeToSilverIcebergJob', {
      name: 'orders-bronze-to-silver-iceberg',
      role: glueRole.roleArn,
      glueVersion: '5.1',
      workerType: 'G.1X',
      numberOfWorkers: 10,
      timeout: 120, // Never leave at 2880 min (48h) default!
      executionProperty: {
        maxConcurrentRuns: 2,
      },
      command: {
        name: 'glueetl',
        pythonVersion: '3',
        scriptLocation: `s3://${rawBucket.bucketName}/scripts/bronze_to_silver.py`,
      },
      defaultArguments: {
        '--enable-auto-scaling': 'true',
        '--enable-metrics': 'true',
        '--enable-observability-metrics': 'true',
        '--enable-continuous-cloudwatch-log': 'true',
        '--enable-job-insights': 'true',
        '--job-bookmark-option': 'job-bookmark-enable',
        '--datalake-formats': 'iceberg',
      },
    });
  }
}
```

---

## 2. Redshift Serverless FinOps Guardrails (CloudFormation Snippet)

Always cap `MaxCapacity` and attach a `RedshiftServerless::Workgroup` / `Redshift::EndpointAccess` usage limit so ad-hoc BI concurrency spikes cannot exhaust monthly budgets:

```yaml
Resources:
  AnalyticsRedshiftWorkgroup:
    Type: AWS::RedshiftServerless::Workgroup
    Properties:
      WorkgroupName: analytics-serverless-wg
      NamespaceName: !Ref AnalyticsRedshiftNamespace
      BaseCapacity: 32
      MaxCapacity: 128
      PubliclyAccessible: false
      EnhancedVpcRouting: true
      SubnetIds: !Ref PrivateDataSubnetIds
      SecurityGroupIds:
        - !Ref RedshiftPrivateSecurityGroup
```

---

## 3. Amazon MSK & Amazon OpenSearch Service Terraform Blueprints (Zero-Trust Security & Stateful Guardrails)

Never allow unauthenticated plaintext ports (`client_broker = "PLAINTEXT"` on port `9092`), `0.0.0.0/0` ingress, or public unencrypted OpenSearch endpoints without Fine-Grained Access Control (FGAC). Always place stateful streaming and search clusters in 3-AZ private subnets with KMS CMK encryption, IAM authentication, audit/slow logs, and `lifecycle { prevent_destroy = true }` (or `RemovalPolicy.RETAIN` in CDK).

```hcl
# 1. Amazon MSK Cluster (3-AZ Private Subnets, KMS CMK, TLS 1.2+ Only, IAM Auth)
resource "aws_msk_cluster" "analytics_kafka" {
  cluster_name           = "analytics-events-msk"
  kafka_version          = "3.7.x.kraft"
  number_of_broker_nodes = 3

  broker_node_group_info {
    instance_type   = "kafka.m7g.large"
    client_subnets  = var.private_subnet_ids # 3 AZs
    security_groups = [aws_security_group.msk_private_sg.id]
    storage_info {
      ebs_storage_info {
        volume_size = 500
      }
    }
  }

  encryption_info {
    encryption_at_rest_kms_key_arn = aws_kms_key.data_platform_cmk.arn
    encryption_in_transit {
      client_broker = "TLS" # Reject PLAINTEXT (9092) and TLS_PLAINTEXT
      in_cluster    = true
    }
  }

  client_authentication {
    unauthenticated = false
    sasl {
      iam = true
    }
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.msk_broker_logs.name
      }
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

# 2. Amazon OpenSearch Service Domain (3-AZ Zone Awareness, 3 Dedicated Masters, KMS, HTTPS TLS 1.2+, FGAC)
resource "aws_opensearch_domain" "analytics_search" {
  domain_name    = "analytics-search-prod"
  engine_version = "OpenSearch_2.17"

  cluster_config {
    instance_type            = "r7g.large.search"
    instance_count           = 3
    dedicated_master_enabled = true
    dedicated_master_type    = "m7g.large.search"
    dedicated_master_count   = 3
    zone_awareness_enabled   = true
    zone_awareness_config {
      availability_zone_count = 3
    }
  }

  vpc_options {
    subnet_ids         = var.private_subnet_ids # 3 AZs
    security_group_ids = [aws_security_group.opensearch_private_sg.id]
  }

  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = 200
  }

  encrypt_at_rest {
    enabled    = true
    kms_key_id = aws_kms_key.data_platform_cmk.arn
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  advanced_security_options {
    enabled                        = true
    anonymous_auth_enabled         = false
    internal_user_database_enabled = false
    master_user_options {
      master_user_arn = var.opensearch_admin_iam_role_arn
    }
  }

  log_publishing_options {
    log_type                 = "AUDIT_LOGS"
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_audit_logs.arn
  }

  lifecycle {
    prevent_destroy = true
  }
}
```


---

## 3. Amazon MSK & Amazon OpenSearch Service Terraform Blueprints (Zero-Trust Security & Stateful Guardrails)

Never allow unauthenticated plaintext ports (`client_broker = "PLAINTEXT"` on port `9092`), `0.0.0.0/0` ingress, or public unencrypted OpenSearch endpoints without Fine-Grained Access Control (FGAC). Always place stateful streaming and search clusters in 3-AZ private subnets with KMS CMK encryption, IAM authentication, audit/slow logs, and `lifecycle { prevent_destroy = true }` (or `RemovalPolicy.RETAIN` in CDK).

```hcl
# 1. Amazon MSK Cluster (3-AZ Private Subnets, KMS CMK, TLS 1.2+ Only, IAM Auth)
resource "aws_msk_cluster" "analytics_kafka" {
  cluster_name           = "analytics-events-msk"
  kafka_version          = "3.7.x.kraft"
  number_of_broker_nodes = 3

  broker_node_group_info {
    instance_type   = "kafka.m7g.large"
    client_subnets  = var.private_subnet_ids # 3 AZs
    security_groups = [aws_security_group.msk_private_sg.id]
    storage_info {
      ebs_storage_info {
        volume_size = 500
      }
    }
  }

  encryption_info {
    encryption_at_rest_kms_key_arn = aws_kms_key.data_platform_cmk.arn
    encryption_in_transit {
      client_broker = "TLS" # Reject PLAINTEXT (9092) and TLS_PLAINTEXT
      in_cluster    = true
    }
  }

  client_authentication {
    unauthenticated = false
    sasl {
      iam = true
    }
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.msk_broker_logs.name
      }
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

# 2. Amazon OpenSearch Service Domain (3-AZ Zone Awareness, 3 Dedicated Masters, KMS, HTTPS TLS 1.2+, FGAC)
resource "aws_opensearch_domain" "analytics_search" {
  domain_name    = "analytics-search-prod"
  engine_version = "OpenSearch_2.17"

  cluster_config {
    instance_type            = "r7g.large.search"
    instance_count           = 3
    dedicated_master_enabled = true
    dedicated_master_type    = "m7g.large.search"
    dedicated_master_count   = 3
    zone_awareness_enabled   = true
    zone_awareness_config {
      availability_zone_count = 3
    }
  }

  vpc_options {
    subnet_ids         = var.private_subnet_ids # 3 AZs
    security_group_ids = [aws_security_group.opensearch_private_sg.id]
  }

  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = 200
  }

  encrypt_at_rest {
    enabled    = true
    kms_key_id = aws_kms_key.data_platform_cmk.arn
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  advanced_security_options {
    enabled                        = true
    anonymous_auth_enabled         = false
    internal_user_database_enabled = false
    master_user_options {
      master_user_arn = var.opensearch_admin_iam_role_arn
    }
  }

  log_publishing_options {
    log_type                 = "AUDIT_LOGS"
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_audit_logs.arn
  }

  lifecycle {
    prevent_destroy = true
  }
}
```

