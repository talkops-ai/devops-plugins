# CloudFormation Linting (`cfn-lint`), Policy Compliance (`cfn-guard`) & `cdk-nag`

Every CloudFormation, AWS SAM, or synthesized AWS CDK template MUST pass both syntax/schema validation and preventive security compliance scanning before deployment.

## 1. Automated Two-Tier Validation Pipeline

### Tier 1: Automatic `PostToolUse` Hook (`scripts/validate-iac.sh`)

Whenever you `Write` or `Edit` a CloudFormation, SAM (`template.yaml` / `template.yml`), or Terraform (`*.tf`) file, the plugin's `PostToolUse` hook automatically executes `scripts/validate-iac.sh` (`sam validate --lint`, `cfn-lint`, or `terraform validate`) and returns any syntax or schema errors as a `systemMessage`. Fix all reported issues immediately before continuing.

### Tier 2: Pre-Deployment `awsiac` MCP Server Validation

Before prompting the user to approve deployment (`cdk deploy`, `sam deploy`, or `aws cloudformation deploy`):

1. **For AWS CDK Projects:** Synthesize the CloudFormation assembly first:
   ```bash
   npx cdk synth --quiet
   ```
   Locate the synthesized template at `cdk.out/<StackName>.template.json`.
2. **Run Syntax & Schema Validation (`cfn-lint`):**
   Call `awsiac` -> `validate_cloudformation_template` passing the template content and target `regions`.
3. **Run Preventive Policy-as-Code Compliance (`cfn-guard`):**
   Call `awsiac` -> `check_cloudformation_template_compliance` against the AWS Guard Rules Registry and AWS Control Tower proactive control rule sets.

## 2. Top `cfn-guard` & Control Tower Proactive Controls Enforced

| Control Domain | Rule Invariant | Required IaC Configuration |
| --- | --- | --- |
| **Amazon S3** | `S3_BUCKET_PUBLIC_READ_PROHIBITED`, `S3_BUCKET_PUBLIC_WRITE_PROHIBITED`, `S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED`, `S3_BUCKET_SSL_REQUESTS_ONLY` | `PublicAccessBlockConfiguration` (all 4 booleans `true`), `BucketEncryption` enabled, and bucket policy denying `aws:SecureTransport == false`. |
| **Amazon RDS / Aurora** | `RDS_STORAGE_encrypted`, `RDS_INSTANCE_PUBLIC_ACCESS_CHECK`, `RDS_MULTI_AZ_SUPPORT` (prod) | `StorageEncrypted: true`, `PubliclyAccessible: false`, `DBSubnetGroup` in private subnets, `DeletionProtection: true` (prod). |
| **Amazon ECS / Fargate** | `ECS_TASK_DEFINITION_USER_FOR_HOST_MODE_CHECK`, `ECS_CONTAINERS_NONPRIVILEGED`, `ECS_NO_ENVIRONMENT_SECRETS` | `Privileged: false`, secrets passed via `Secrets` (`ValueFrom`) rather than plaintext `Environment`. |
| **AWS IAM** | `IAM_POLICY_NO_STATEMENTS_WITH_ADMIN_ACCESS`, `IAM_NO_INLINE_POLICY_CHECK` | Never emit `"Effect": "Allow"` with `"Action": "*"` and `"Resource": "*"`. Scope actions and resource ARNs explicitly. |
| **Amazon EC2 / VPC** | `INCOMING_SSH_DISABLED`, `VPC_DEFAULT_SECURITY_GROUP_CLOSED`, `EC2_IMDSV2_CHECK` | No `0.0.0.0/0` ingress on port `22` or `3389` (use SSM Session Manager); `HttpTokens: required` on EC2 launch templates. |
| **AWS Lambda** | `LAMBDA_FUNCTION_PUBLIC_ACCESS_PROHIBITED`, `LAMBDA_INSIDE_VPC` (when accessing private DBs) | Restrict resource-based permissions with `SourceAccount` / `SourceArn`; set explicit `ReservedConcurrentExecutions` or ESM `MaximumConcurrency`. |
| **CloudWatch Logs** | `CLOUDWATCH_LOG_GROUP_ENCRYPTED`, `CW_LOGGROUP_RETENTION_PERIOD_CHECK` | Explicit `RetentionInDays` (e.g., `14`, `30`, or `90` days) and KMS encryption for sensitive production logs. |

## 3. Integrating `cdk-nag` in AWS CDK Projects

For production CDK TypeScript/Python stacks, wire `cdk-nag` (`AwsSolutionsChecks`) into the app entrypoint:

```typescript
import { Aspects } from 'aws-cdk-lib';
import { AwsSolutionsChecks, NagSuppressions } from 'cdk-nag';

Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));
```

When a rule must be suppressed for a documented architectural reason (e.g., an ALB security group intentionally accepting `0.0.0.0/0` on HTTPS port `443`), attach a scoped `NagSuppressions.addResourceSuppressions` with a clear justification—never suppress rules globally without rationale.
