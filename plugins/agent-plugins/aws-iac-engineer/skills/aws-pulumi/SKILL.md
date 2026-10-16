---
name: aws-pulumi
description: Authors, previews, validates, and troubleshoots AWS infrastructure in TypeScript, Python, or Go using Pulumi ComponentResource abstractions, dual pulumi-aws + pulumi-aws-native providers, Pulumi ESC OIDC credential brokering, and CrossGuard Policy-as-Code.
---

# AWS Pulumi Infrastructure Engineering

Use this skill whenever authoring, migrating, previewing, or troubleshooting **Pulumi** infrastructure programs (`Pulumi.yaml`, `Pulumi.<stack>.yaml`) in TypeScript, Python, or Go targeting AWS.

## 1. Dual-Provider Strategy (`@pulumi/aws` + `@pulumi/aws-native`)

Combine the classic **`@pulumi/aws`** (`pulumi_aws` in Python) provider with **`@pulumi/aws-native`** (`pulumi_aws_native`, backed by the AWS Cloud Control API) and **`@pulumi/awsx`** (`pulumi_awsx` high-level multi-AZ VPC, ECS Fargate, and ALB abstractions):

- Use **`awsx`** / **`aws`** for mature higher-level patterns (`awsx.ec2.Vpc`, `awsx.ecs.FargateService`, `aws.iam.getPolicyDocument`).
- Use **`aws-native`** when provisioning Day-0 AWS services/features exposed immediately on the Cloud Control API (`aws_native.bedrock.*`, `aws_native.opensearchserverless.*`) or when enforcing CloudFormation-aligned schema semantics.

## 2. Dynamic Credentials & Secrets with Pulumi ESC

Eliminate static IAM access keys and plaintext secrets in `Pulumi.<stack>.yaml`:

1. **AWS OIDC via Pulumi ESC**:
   Configure a Pulumi ESC environment using the `aws-login` provider to broker short-lived STS credentials dynamically via OIDC:
   ```yaml
   # Pulumi ESC environment definition
   values:
     aws:
       login:
         fn::open::aws-login:
           oidc:
             duration: 1h
             roleArn: arn:aws:iam::123456789012:role/PulumiDeploymentRole
             sessionName: pulumi-${context.pulumi.user.login}
     environmentVariables:
       AWS_ACCESS_KEY_ID: ${aws.login.accessKeyId}
       AWS_SECRET_ACCESS_KEY: ${aws.login.secretAccessKey}
       AWS_SESSION_TOKEN: ${aws.login.sessionToken}
       AWS_REGION: us-east-1
   ```
2. **Secret Configuration**:
   Always store sensitive stack inputs via `pulumi config set --secret <key> <value>` and wrap computed sensitive outputs with `pulumi.secret(...)` so values are encrypted in state and redacted in CLI/MCP output.

## 3. ComponentResource Authoring & Production Guardrails

Encapsulate reusable platform patterns as `pulumi.ComponentResource` classes with secure defaults and explicit `ResourceOptions`:

```typescript
import * as pulumi from "@pulumi/pulumi";
import * as aws from "@pulumi/aws";

export interface SecureBucketArgs {
    versioned?: boolean;
    kmsKeyArn?: pulumi.Input<string>;
    retainOnDelete?: boolean;
}

export class SecureBucket extends pulumi.ComponentResource {
    public readonly bucket: aws.s3.BucketV2;

    constructor(name: string, args: SecureBucketArgs, opts?: pulumi.ComponentResourceOptions) {
        super("custom:storage:SecureBucket", name, {}, opts);

        this.bucket = new aws.s3.BucketV2(`${name}-bucket`, {}, {
            parent: this,
            protect: args.retainOnDelete ?? true,
            retainOnDelete: args.retainOnDelete ?? true,
        });

        new aws.s3.BucketPublicAccessBlock(`${name}-pab`, {
            bucket: this.bucket.id,
            blockPublicAcls: true,
            blockPublicPolicy: true,
            ignorePublicAcls: true,
            restrictPublicBuckets: true,
        }, { parent: this });

        new aws.s3.BucketServerSideEncryptionConfigurationV2(`${name}-sse`, {
            bucket: this.bucket.id,
            rules: [{
                applyServerSideEncryptionByDefault: {
                    sseAlgorithm: args.kmsKeyArn ? "aws:kms" : "AES256",
                    kmsMasterKeyId: args.kmsKeyArn,
                },
                bucketKeyEnabled: true,
            }],
        }, { parent: this });

        this.registerOutputs({ bucketName: this.bucket.id, bucketArn: this.bucket.arn });
    }
}
```

### Mandatory Resource Options for Stateful Infrastructure
- Set `protect: true` and `retainOnDelete: true` on production RDS/Aurora clusters, DynamoDB tables, S3 buckets, and KMS keys.
- Use `aliases: [{ name: "old-logical-name" }]` whenever renaming resources or moving them inside a `ComponentResource` to prevent destructive replacement.

## 4. Validation, CrossGuard Policy-as-Code, and Preview Gate

1. **Typecheck & Unit Test**:
   - TypeScript: `tsc --noEmit` and `npm test` (using `pulumi.runtime.setMocks` for fast offline unit tests).
   - Python: `pytest` with `pulumi.runtime.set_mocks`.
2. **CrossGuard Policy-as-Code (`@pulumi/policy` / `pulumi_policy`)**:
   - Run `pulumi preview --policy-pack <path>` to enforce mandatory encryption, private-subnet placement, least-privilege IAM, and required tags before provisioning.
3. **Preview & Approval Gate**:
   - Run `pulumi preview --diff` (or use the `pulumi` MCP server tools) and call out every `replace`, `delete`, IAM change, and security-group modification.
   - **Never run `pulumi up --yes` or `pulumi destroy --yes` without explicit user `APPROVED` confirmation** of the preview diff.
4. **Failure Diagnosis & Neo Handoff**:
   - On failed updates or interrupted stack operations, inspect pending operations (`pulumi stack export`) and run structured root-cause analysis (`pulumi-debug-failed-operation`).
   - For autonomous cloud-hosted pull request workflows or multi-stack migrations (`pulumi-terraform-to-pulumi`, `pulumi-cdk-to-pulumi`, `cloudformation-to-pulumi`), coordinate with the `pulumi` MCP server (`neo-bridge`).
