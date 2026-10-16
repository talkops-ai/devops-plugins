# Production CDK L1 & CloudFormation Patterns for SageMaker Studio Domains

## 1. Complete TypeScript CDK L1 Pattern (`VpcOnly` Domain + KMS + PrivateLink + Spaces)

```typescript
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sagemaker from 'aws-cdk-lib/aws-sagemaker';
import { Construct } from 'constructs';

export interface SageMakerStudioPlatformProps extends cdk.StackProps {
  readonly authMode: 'SSO' | 'IAM';
  readonly ssoUserName?: string;
}

export class SageMakerStudioPlatformStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: SageMakerStudioPlatformProps) {
    super(scope, id, props);

    // 1. Customer-Managed KMS Key for Studio EFS, Space EBS, S3, and Training Volumes
    const kmsKey = new kms.Key(this, 'SageMakerPlatformKmsKey', {
      enableKeyRotation: true,
      description: 'CMK for SageMaker Studio EFS, Space EBS, S3 artifacts, and Endpoints',
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // 2. Private VPC with Isolated/Private Subnets across >= 2 AZs
    const vpc = new ec2.Vpc(this, 'SageMakerVpc', {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        { name: 'Public', subnetType: ec2.SubnetType.PUBLIC, cidrMask: 24 },
        { name: 'PrivateMl', subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS, cidrMask: 20 },
      ],
    });

    // 3. Security Groups: Domain SG (Self-referencing NFS 2049 + Ephemeral 8192-65535) & VPC Endpoint SG
    const domainSg = new ec2.SecurityGroup(this, 'StudioDomainSg', {
      vpc,
      description: 'SageMaker Studio Domain and Space Security Group',
      allowAllOutbound: true,
    });
    // Mandatory: EFS mount between Domain EFS and Studio Apps/Spaces
    domainSg.addIngressRule(domainSg, ec2.Port.tcp(2049), 'Allow NFS 2049 within Studio Domain SG');
    // Mandatory: Inter-app / KernelGateway / Spark communication
    domainSg.addIngressRule(domainSg, ec2.Port.tcpRange(8192, 65535), 'Allow inter-app ephemeral ports');

    const vpceSg = new ec2.SecurityGroup(this, 'VpcEndpointSg', {
      vpc,
      description: 'PrivateLink Interface Endpoints SG for SageMaker',
      allowAllOutbound: false,
    });
    vpceSg.addIngressRule(domainSg, ec2.Port.tcp(443), 'Allow HTTPS from Studio Domain SG');

    // 4. Mandatory VPC Endpoints for VpcOnly Mode
    vpc.addGatewayEndpoint('S3GatewayEndpoint', {
      service: ec2.GatewayVpcEndpointAwsService.S3,
    });

    const interfaceServices: Array<[string, ec2.InterfaceVpcEndpointAwsService]> = [
      ['SageMakerApi', ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_API],
      ['SageMakerRuntime', ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_RUNTIME],
      ['SageMakerStudio', ec2.InterfaceVpcEndpointAwsService.SAGEMAKER_STUDIO],
      ['EcrApi', ec2.InterfaceVpcEndpointAwsService.ECR],
      ['EcrDkr', ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER],
      ['Sts', ec2.InterfaceVpcEndpointAwsService.STS],
      ['CloudWatchLogs', ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS],
      ['BedrockRuntime', ec2.InterfaceVpcEndpointAwsService.BEDROCK_RUNTIME],
    ];

    for (const [name, service] of interfaceServices) {
      vpc.addInterfaceEndpoint(`${name}Endpoint`, {
        service,
        subnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
        securityGroups: [vpceSg],
        privateDnsEnabled: true,
      });
    }

    // 5. Encrypted Artifact S3 Bucket
    const artifactBucket = new s3.Bucket(this, 'SageMakerArtifactBucket', {
      encryption: s3.BucketEncryption.KMS,
      encryptionKey: kmsKey,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // 6. Least-Privilege Studio Execution Role (Avoid AmazonSageMakerFullAccess in Prod)
    const studioExecutionRole = new iam.Role(this, 'StudioDomainExecutionRole', {
      assumedBy: new iam.ServicePrincipal('sagemaker.amazonaws.com'),
      description: 'Least-privilege execution role for SageMaker Studio Domain and Spaces',
    });

    artifactBucket.grantReadWrite(studioExecutionRole);
    kmsKey.grantEncryptDecrypt(studioExecutionRole);

    studioExecutionRole.addToPolicy(
      new iam.PolicyStatement({
        sid: 'ScopedSageMakerWorkloadActions',
        actions: [
          'sagemaker:CreateTrainingJob',
          'sagemaker:DescribeTrainingJob',
          'sagemaker:StopTrainingJob',
          'sagemaker:CreateProcessingJob',
          'sagemaker:DescribeProcessingJob',
          'sagemaker:CreateModel',
          'sagemaker:CreateEndpointConfig',
          'sagemaker:CreateEndpoint',
          'sagemaker:CreateInferenceComponent',
          'sagemaker:UpdateInferenceComponent',
          'sagemaker:DescribeEndpoint',
          'sagemaker:InvokeEndpoint',
          'sagemaker:CreateApp',
          'sagemaker:DeleteApp',
          'sagemaker:DescribeApp',
          'sagemaker:DescribeSpace',
        ],
        resources: [`arn:aws:sagemaker:${this.region}:${this.account}:*`],
      }),
    );

    studioExecutionRole.addToPolicy(
      new iam.PolicyStatement({
        sid: 'PassRoleStrictlyToSageMaker',
        actions: ['iam:PassRole'],
        resources: [studioExecutionRole.roleArn],
        conditions: {
          StringEquals: { 'iam:PassedToService': 'sagemaker.amazonaws.com' },
        },
      }),
    );

    const privateSubnetIds = vpc.selectSubnets({
      subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
    }).subnetIds;

    // 7. L1 CfnDomain (VpcOnly + KMS + Idle Auto-Shutdown Lifecycle)
    const domain = new sagemaker.CfnDomain(this, 'SageMakerStudioDomain', {
      domainName: 'enterprise-ml-domain',
      authMode: props.authMode,
      appNetworkAccessType: 'VpcOnly',
      vpcId: vpc.vpcId,
      subnetIds: privateSubnetIds,
      kmsKeyId: kmsKey.keyArn,
      defaultUserSettings: {
        executionRole: studioExecutionRole.roleArn,
        securityGroups: [domainSg.securityGroupId],
        studioWebPortal: 'ENABLED',
        defaultLandingUri: 'studio::',
        jupyterLabAppSettings: {
          appLifecycleManagement: {
            idleSettings: {
              lifecycleManagement: 'ENABLED',
              idleTimeoutInMinutes: 60,
              minIdleTimeoutInMinutes: 60,
              maxIdleTimeoutInMinutes: 240,
            },
          },
        },
        codeEditorAppSettings: {
          appLifecycleManagement: {
            idleSettings: {
              lifecycleManagement: 'ENABLED',
              idleTimeoutInMinutes: 60,
              minIdleTimeoutInMinutes: 60,
              maxIdleTimeoutInMinutes: 240,
            },
          },
        },
      },
      defaultSpaceSettings: {
        executionRole: studioExecutionRole.roleArn,
        securityGroups: [domainSg.securityGroupId],
      },
    });

    // 8. L1 CfnUserProfile (Conditional SSO fields based on AuthMode)
    const userProfile = new sagemaker.CfnUserProfile(this, 'LeadMlEngineerProfile', {
      domainId: domain.attrDomainId,
      userProfileName: 'lead-ml-engineer',
      ...(props.authMode === 'SSO' && props.ssoUserName
        ? {
            singleSignOnUserIdentifier: 'UserName',
            singleSignOnUserValue: props.ssoUserName,
          }
        : {}),
    });

    // 9. Private CodeEditor Space (CodeEditor ONLY supports SharingType: 'Private')
    const codeEditorSpace = new sagemaker.CfnSpace(this, 'PrivateCodeEditorSpace', {
      domainId: domain.attrDomainId,
      spaceName: 'lead-ml-code-editor',
      ownershipSettings: {
        ownerUserProfileName: userProfile.userProfileName,
      },
      spaceSharingSettings: {
        sharingType: 'Private',
      },
      spaceSettings: {
        appType: 'CodeEditor',
        spaceStorageSettings: {
          ebsStorageSettings: {
            ebsVolumeSizeInGb: 50,
          },
        },
        codeEditorAppSettings: {
          defaultResourceSpec: {
            instanceType: 'ml.t3.medium',
          },
        },
      },
    });
    codeEditorSpace.addDependency(userProfile);

    // 10. Shared JupyterLab Space (JupyterLab supports SharingType: 'Shared' without OwnershipSettings)
    new sagemaker.CfnSpace(this, 'SharedJupyterLabSpace', {
      domainId: domain.attrDomainId,
      spaceName: 'team-shared-jupyterlab',
      spaceSharingSettings: {
        sharingType: 'Shared',
      },
      spaceSettings: {
        appType: 'JupyterLab',
        spaceStorageSettings: {
          ebsStorageSettings: {
            ebsVolumeSizeInGb: 100,
          },
        },
        jupyterLabAppSettings: {
          defaultResourceSpec: {
            instanceType: 'ml.m5.large',
          },
        },
      },
    });
  }
}
```

---

## 2. 5-Persona Least-Privilege IAM Boundary Matrix

Never attach `AmazonSageMakerFullAccess` in regulated production environments. Separate IAM roles into 5 distinct personas:

| Persona Role | Principal (`AssumedBy`) | Allowed Actions & Guardrail Conditions |
|---|---|---|
| **1. `StudioDomainExecutionRole`** | `sagemaker.amazonaws.com` | Domain/Space lifecycle (`CreateApp`, `DeleteApp`, `DescribeSpace`), CloudWatch Logs, KMS decrypt on Domain EFS key |
| **2. `DataScientistProfileRole`** | `sagemaker.amazonaws.com` | Interactive experimentation in Studio Spaces; `CreateTrainingJob`, `CreateProcessingJob`, `StartPipelineExecution` with mandatory conditions: `sagemaker:VpcSubnets`, `sagemaker:VpcSecurityGroupIds`, `sagemaker:VolumeKmsKey`; **DENY** `CreateEndpoint` / `UpdateEndpoint` in prod accounts |
| **3. `TrainingJobExecutionRole`** | `sagemaker.amazonaws.com` | Assumed by the training container itself; read-only S3 access to `s3://<dataset-bucket>/curated/*`, read/write S3 access to `s3://<artifact-bucket>/models/*` and `/checkpoints/*`, ECR `BatchGetImage`, CloudWatch Logs, MLflow `sagemaker-mlflow:*` |
| **4. `PipelineExecutionRole`** | `sagemaker.amazonaws.com` | Orchestrates `CreateTrainingJob`, `CreateProcessingJob`, `CreateTransformJob`, `CreateModelPackage`, and `iam:PassRole` strictly for `TrainingJobExecutionRole` and `EndpointInferenceRole` |
| **5. `EndpointInferenceRole`** | `sagemaker.amazonaws.com` | Minimal runtime footprint: read-only S3 access to `s3://<artifact-bucket>/models/*`, ECR pull for serving container, KMS `Decrypt` on model artifact key, CloudWatch Logs `/aws/sagemaker/Endpoints/*` and `/aws/sagemaker/InferenceComponents/*`, zero write access to training datasets |

### Mandatory `CreateTrainingJob` Network & KMS Condition Policy Snippet

Attach this condition block to `DataScientistProfileRole` to guarantee no data scientist can launch an unencrypted or non-VPC training job:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EnforceVpcAndKmsOnTrainingAndProcessing",
      "Effect": "Allow",
      "Action": [
        "sagemaker:CreateTrainingJob",
        "sagemaker:CreateProcessingJob",
        "sagemaker:CreateTransformJob"
      ],
      "Resource": "arn:aws:sagemaker:*:*:*",
      "Condition": {
        "Null": {
          "sagemaker:VpcSubnets": "false",
          "sagemaker:VpcSecurityGroupIds": "false",
          "sagemaker:VolumeKmsKey": "false"
        }
      }
    }
  ]
}
```

---

## 3. Custom Studio Image (BYOI) + SOCI Fast-Launch Pattern

When data scientists need pre-baked Conda/pip environments in Studio `JupyterLab` or `CodeEditor`:

1. **Dockerfile Requirements**:
   - Base image: `public.ecr.aws/sagemaker/sagemaker-distribution:latest-cpu` (or `-gpu`)
   - Must run as UID `1000` / GID `100` (`sagemaker-user`) with `/home/sagemaker-user` writable.
2. **SOCI (Seekable OCI) Index Generation**:
   - Large ML images (5–15 GB) take 4–8 minutes to pull on Studio startup unless indexed with **AWS SOCI** (lazy-loading container layers over ECR).
   - Build and push the SOCI index using `soci create` + `soci push` (or deploy the AWS SOCI Index Builder Serverless Application on ECR `ImagePush` EventBridge events).
3. **Register via L1 Constructs (`CfnImage` → `CfnImageVersion` → `CfnAppImageConfig`)**:
   - Attach the `AppImageConfig` (`JupyterLabAppImageConfig` or `KernelGatewayAppImageConfig`) to `CfnDomain.defaultUserSettings.jupyterLabAppSettings.customImages`.

---

## 4. External Auth (`AuthMode: 'IAM'`) via Cognito + `CreatePresignedDomainUrl`

When an enterprise uses Amazon Cognito, Okta (without Identity Center), or a custom portal with `AuthMode: 'IAM'`:

```python
import os
import boto3

sm = boto3.client("sagemaker")

def lambda_handler(event, context):
    # Verify Cognito JWT claims from API Gateway Authorizer
    claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
    user_profile_name = claims["custom:sagemaker_profile"]

    resp = sm.create_presigned_domain_url(
        DomainId=os.environ["SAGEMAKER_DOMAIN_ID"],
        UserProfileName=user_profile_name,
        SessionExpirationDurationInSeconds=43200,  # 12 hours max session
        ExpiresInSeconds=300,                      # URL must be opened within 5 minutes
    )
    return {
        "statusCode": 302,
        "headers": {"Location": resp["AuthorizedUrl"]},
    }
```
