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
