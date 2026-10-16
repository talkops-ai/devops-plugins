# AWS STRIDE Threat Modeling, EventBridge + Step Functions HITL Remediation & Multi-IaC Validation (`cfn-guard`, `cdk-nag`, Terraform)

Use this reference when:
1. Performing **Cloud Architectural Threat Modeling (STRIDE for AWS)** across trust boundaries and multi-service attack paths,
2. Designing automated, approval-gated security remediation pipelines (`EventBridge -> Step Functions waitForTaskToken -> Lambda`), or
3. Validating Infrastructure-as-Code across **CloudFormation Guard (`cfn-guard`)**, **AWS CDK (`cdk-nag`)**, and **Terraform (HCL)**.

---

## 1. AWS Cloud Architectural Threat Modeling Matrix (STRIDE)

When reviewing an AWS architecture or IaC repository, evaluate every trust boundary crossing using this AWS-specific STRIDE matrix:

| STRIDE Category | AWS Control/Data Plane Threat Scenario | Preventive Controls | Detective Controls |
|---|---|---|---|
| **Spoofing** | Cross-account service confused deputy (EventBridge, S3, SNS, Lambda, Bedrock, Shield SRT); direct ALB/S3 access bypassing CloudFront/WAF; OIDC wildcard `:sub` claims. | `aws:SourceArn` & `aws:SourceAccount` in all service trust policies; CloudFront OAC + custom secret header + `com.amazonaws.global.cloudfront.origin-facing` prefix list; `StringEquals` on OIDC `:sub` & `:aud`. | CloudTrail `AssumeRole` / `AssumeRoleWithWebIdentity` audit; IAM Access Analyzer external access findings. |
| **Tampering** | Attacker modifies S3 data/logs, overwrites ECR container tag `:latest`, or alters KMS ciphertext across contexts. | S3 Object Lock (`COMPLIANCE`/`GOVERNANCE`), CloudTrail digest file validation (`EnableLogFileValidation`), ECR `imageTagMutability = IMMUTABLE`, KMS `kms:EncryptionContext`. | `aws cloudtrail validate-logs`, GuardDuty S3 Protection, AWS Config drift tracking. |
| **Repudiation** | Actions performed via shared IAM role without caller attribution, or missing data-plane logs on S3/DNS/WAF/EKS/Bedrock. | Enforce `sts:SourceIdentity` propagation on federation; SCP denying `cloudtrail:StopLogging`, `guardduty:DeleteDetector`, `config:StopConfigurationRecorder`. | Multi-region Organization CloudTrail + S3/Lambda/DynamoDB Data Events, VPC Flow Logs v5+, Route 53 DNS Query Logs, EKS Audit Logs, Bedrock Model Invocation Logs. |
| **Information Disclosure** | SSRF -> IMDSv1 role theft; S3/RDS/EBS public sharing; cross-account S3 exfiltration from VPC; plaintext secrets in env vars. | EC2 IMDSv2 (`HttpTokens=required`, `HopLimit=1`); Account & RDS/EBS Block Public Access; RCPs + VPC Endpoint policies (`aws:PrincipalOrgID`, `s3:DataAccessPointAccount`); Secrets Manager `asm-exec` / dynamic references. | GuardDuty `UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS`, Macie sensitive data discovery, IAM Access Analyzer. |
| **Denial of Service** | L7 HTTP flood on CloudFront/ALB/API Gateway; wallet-denial attack on unthrottled Lambda or Bedrock endpoints. | WAFv2 rate-based rules + Bot Control; Shield Advanced Protection Groups + L7 auto-mitigation; API Gateway Usage Plans; Lambda reserved concurrency; VPC Endpoint private routing. | CloudWatch `DDoSDetected`, WAF `BlockedRequests` alarms, Billing/Cost Anomaly Monitors. |
| **Elevation of Privilege** | IAM privilege escalation (`iam:PassRole` + Lambda/EC2/ECS/Glue, `iam:CreatePolicyVersion`, `sts:AssumeRole` chains); Cognito writable custom attributes; shared ECS `executionRoleArn`/`taskRoleArn`. | IAM Permission Boundaries on delegated role creators; SCPs blocking root user & unprotected privilege actions; separate ECS `executionRoleArn` and `taskRoleArn`. | GuardDuty `PrivilegeEscalation:IAMUser/*`, `AttackSequence:IAM/*`, CloudTrail Lake privilege escalation queries. |

---

## 2. Event-Driven Human-in-the-Loop (HITL) Remediation Architecture

Never wire GuardDuty or Security Hub findings directly to a mutating Lambda function without a **blast-radius check**, **exemption tag check**, **state snapshot**, and **human approval gate (`waitForTaskToken`)** for production accounts.

```
[Security Hub / GuardDuty Finding]
        │
        ▼ (EventBridge Rule matching CRITICAL/HIGH or Custom Action)
[Step Functions State Machine]
        ├─► 1. CaptureCurrentStateAndCheckBlastRadius (Read-Only Lambda)
        │      • Snapshots current SG rules / Policy / Key state to DynamoDB
        │      • Queries Flow Logs / AccessKeyLastUsed for active prod traffic
        │      • Checks exemption tags + verifies tag wasn't added by unauthorized principal
        ├─► 2. RequestHumanApproval (SNS / Slack / PagerDuty with .waitForTaskToken)
        │      • Sends finding, blast radius, proposed CLI/IaC diff, and Approve/Reject callback URLs
        ├─► 3. ExecuteControlledRemediation (Scoped Per-Action Lambda Role)
        │      • Executes single atomic API call (e.g., PutPublicAccessBlock, RevokeSecurityGroupIngress)
        ├─► 4. VerifyControlPass (Read-Only Verification Lambda)
        │      • Re-queries resource state & updates Security Hub finding Workflow.Status = RESOLVED
        └─► 5. AutomaticRollbackOnFailure (Restores captured state from Step 1 if health check fails)
```

### 2.1 EventBridge Pattern for Security Hub Custom Action or High/Critical Findings

```json
{
  "source": ["aws.securityhub"],
  "detail-type": [
    "Security Hub Findings - Custom Action",
    "Security Hub Findings - Imported"
  ],
  "detail": {
    "findings": {
      "Severity": {
        "Label": ["CRITICAL", "HIGH"]
      },
      "Workflow": {
        "Status": ["NEW"]
      },
      "RecordState": ["ACTIVE"]
    }
  }
}
```

### 2.2 Step Functions `waitForTaskToken` Approval State Snippet (ASL)

```json
{
  "RequestOperatorApproval": {
    "Type": "Task",
    "Resource": "arn:aws:states:::sns:publish.waitForTaskToken",
    "Parameters": {
      "TopicArn": "arn:aws:sns:us-east-1:111122223333:security-remediation-approvals",
      "Message": {
        "TaskToken.$": "$$.Task.Token",
        "FindingId.$": "$.finding.Id",
        "ResourceArn.$": "$.finding.Resources[0].Id",
        "BlastRadiusSummary.$": "$.preFlightCheck.blastRadius",
        "ProposedAction.$": "$.preFlightCheck.proposedCli",
        "RollbackPayload.$": "$.preFlightCheck.previousStateSnapshot"
      }
    },
    "TimeoutSeconds": 86400,
    "Catch": [
      {
        "ErrorEquals": ["States.Timeout"],
        "Next": "NotifyApprovalExpiredNoMutation"
      }
    ],
    "Next": "EvaluateOperatorDecision"
  }
}
```

---

## 3. Multi-IaC Shift-Left Security Validation (`cfn-guard`, `cdk-nag`, Terraform)

### 3.1 CloudFormation Guard (`cfn-guard`) Rule Library (Validate via `awsiac` MCP)

Use these `cfn-guard` rules (or validate via the `awsiac` MCP server `check_cloudformation_template_compliance`) to shift-left validate CloudFormation and synthesized CDK templates (`cdk synth`) before deployment:

```guard
# 1. S3 Buckets must have BlockPublicAccess enabled,BucketOwnerEnforced, and SSE encryption configured
let s3_buckets = Resources.*[ Type == 'AWS::S3::Bucket' ]

rule s3_bucket_public_access_blocked when %s3_buckets !empty {
  %s3_buckets.Properties.PublicAccessBlockConfiguration.BlockPublicAcls == true
  %s3_buckets.Properties.PublicAccessBlockConfiguration.BlockPublicPolicy == true
  %s3_buckets.Properties.PublicAccessBlockConfiguration.IgnorePublicAcls == true
  %s3_buckets.Properties.PublicAccessBlockConfiguration.RestrictPublicBuckets == true
}

rule s3_bucket_acls_disabled when %s3_buckets !empty {
  %s3_buckets.Properties.OwnershipControls.Rules[*].ObjectOwnership == 'BucketOwnerEnforced'
}

rule s3_bucket_encryption_enabled when %s3_buckets !empty {
  %s3_buckets.Properties.BucketEncryption.ServerSideEncryptionConfiguration[*].ServerSideEncryptionByDefault.SSEAlgorithm in ['AES256', 'aws:kms', 'aws:kms:dsse']
}

# 2. Security Groups must not allow unrestricted 0.0.0.0/0 or ::/0 ingress on SSH (22) or RDP (3389)
let sg_resources = Resources.*[ Type == 'AWS::EC2::SecurityGroup' ]

rule sg_no_public_ssh_or_rdp when %sg_resources !empty {
  %sg_resources.Properties.SecurityGroupIngress[*] {
    when CidrIp == '0.0.0.0/0' or CidrIpv6 == '::/0' {
      IpProtocol != '-1'
      FromPort > 22 or ToPort < 22
      FromPort > 3389 or ToPort < 3389
    }
  }
}

# 3. KMS Customer Managed Keys must enable automatic annual rotation
let kms_keys = Resources.*[ Type == 'AWS::KMS::Key' ]

rule kms_key_rotation_enabled when %kms_keys !empty {
  %kms_keys.Properties.EnableKeyRotation == true
}

# 4. EC2 Launch Templates must enforce IMDSv2 (HttpTokens: required, HttpPutResponseHopLimit: 1)
let launch_templates = Resources.*[ Type == 'AWS::EC2::LaunchTemplate' ]

rule ec2_launch_template_imdsv2_required when %launch_templates !empty {
  %launch_templates.Properties.LaunchTemplateData.MetadataOptions.HttpTokens == 'required'
  %launch_templates.Properties.LaunchTemplateData.MetadataOptions.HttpPutResponseHopLimit == 1
}
```

### 3.2 AWS CDK Shift-Left Security Validation (`cdk-nag`)

When authoring or reviewing AWS CDK (TypeScript/Python) remediation code:
1. Enforce `AwsSolutionsChecks` (and `NIST80053R5Checks` or `HIPAASecurityChecks` for regulated workloads) at the `App` or `Stage` level:
   ```typescript
   import { Aspects } from 'aws-cdk-lib';
   import { AwsSolutionsChecks, NagSuppressions } from 'cdk-nag';

   Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));
   ```
2. Require documented `NagSuppressions.addResourceSuppressionsByPath(...)` with a concrete `appliesTo` condition rather than broad stack-wide wildcard suppressions for `AwsSolutions-IAM4` (managed policies) or `AwsSolutions-IAM5` (wildcard resources).
3. Synthesize the CDK stack (`npx cdk synth`) and pass the resulting CloudFormation template through `awsiac` (`validate_cloudformation_template` + `check_cloudformation_template_compliance`).

### 3.3 Terraform / HCL Shift-Left Security Checklist

When authoring or reviewing Terraform (`aws` provider) remediation code:
1. **IAM Policies (`data "aws_iam_policy_document"`):**
   - Prefer typed `data "aws_iam_policy_document"` blocks over raw `jsonencode` strings so condition operators (`StringEquals`, `ArnLike`) and principals are statically validated.
   - Always pass the rendered policy JSON to `accessanalyzer:ValidatePolicy` before proposing.
2. **S3 Buckets (`aws_s3_bucket_*`):**
   - Ensure separate resources are defined for `aws_s3_bucket_public_access_block`, `aws_s3_bucket_ownership_controls` (`BucketOwnerEnforced`), `aws_s3_bucket_server_side_encryption_configuration` (`aws:kms` + `bucket_key_enabled = true`), `aws_s3_bucket_versioning`, and `aws_s3_bucket_policy` (using `data.aws_iam_policy_document` with `aws:SecureTransport = "false"` deny).
3. **State & Ephemeral Secrets Safety:**
   - Use **Terraform 1.10+ `ephemeral` resources and `write-only` arguments** (`password_wo`) or `aws_secretsmanager_secret` + out-of-band `asm-exec` rotation so sensitive credentials are never persisted in `terraform.tfstate`.
