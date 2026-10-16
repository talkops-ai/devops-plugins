# AWS MGN Post-Launch Systems Manager Containerization Automation

## 1. Overview

AWS Application Migration Service (AWS MGN) enables lift-and-shift server replication to AWS. By integrating Systems Manager (SSM) post-launch action automation, migrated virtual machines can automatically trigger AWS App2Container (A2C) upon test or cutover instance launch, accelerating modernization from Rehost to Replatform.

---

## 2. IAM Role & Permissions

The target EC2 instance profile must include permissions to execute SSM Automation and allow A2C to interact with S3 and ECR:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowMGNPostLaunchSSM",
      "Effect": "Allow",
      "Action": [
        "ssm:SendCommand",
        "ssm:GetAutomationExecution",
        "ssm:ListCommands",
        "ssm:ListCommandInvocations"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowApp2ContainerOperations",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:GetRepositoryPolicy",
        "ecr:DescribeRepositories",
        "ecr:ListImages",
        "ecr:DescribeImages",
        "ecr:BatchGetImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:PutImage",
        "ecr:CreateRepository",
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": "*"
    }
  ]
}
```

Attach the AWS-managed policy `ApplicationTransformationAnalyzerPolicy` alongside `AmazonSSMManagedInstanceCore`.

---

## 3. Configuring the Post-Launch Action in AWS MGN

Using the AWS CLI or AWS MCP server (`aws-mcp`):

```bash
# 1. Create a Post-Launch Action Template for A2C
aws mgn put-source-server-action \
  --account-id "123456789012" \
  --source-server-id "s-1234567890abcdef0" \
  --action-id "app2container-automated-containerization" \
  --action-name "App2Container Automation" \
  --document-identifier "AWSMGN-App2Container-Containerize" \
  --order 1 \
  --active true \
  --timeout-seconds 3600 \
  --parameters '{
    "TargetBucket": ["my-modernization-bucket"],
    "TargetRuntime": ["ecs"],
    "AppId": ["ALL"]
  }'
```

### Automation Execution Flow
1. **Launch Test Instance**: AWS MGN launches a replica EC2 instance in the staging subnet.
2. **SSM Agent Execution**: Upon first boot, SSM Agent downloads and executes `AWSMGN-App2Container-Containerize`.
3. **Automated Inventory & Packaging**: A2C runs inventory on IIS or Java processes, generates the container image, pushes it to Amazon ECR, and uploads CloudFormation deployment templates to the target S3 bucket.
4. **Validation Checkpoint**: Review the generated container artifacts in ECR before scheduling production cutover.
