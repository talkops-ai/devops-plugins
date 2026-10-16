# Elastic Beanstalk IAM Least Privilege & Safe SDK Import Scanning

## 1. Safe Source-Code Inspection Protocol (Remediation for `SEM-006` & `AR-003`)

When determining which AWS IAM permissions the application needs on its EC2 Instance Profile:

1. **Strict File Exclusion:** NEVER read `.env`, `.env.*`, `*.pem`, `*.key`, `credentials`, `secrets.*`, or fixture data files.
2. **Import & Client Symbol Matching Only:** Restrict `Grep` patterns strictly to AWS SDK import lines and client constructors:
   - Python: `boto3\.client\(['"][a-z0-9-]+['"]\)|boto3\.resource\(['"][a-z0-9-]+['"]\)`
   - JavaScript / TypeScript: `@aws-sdk/client-[a-z0-9-]+`
   - Go: `github\.com/aws/aws-sdk-go-v2/service/[a-z0-9]+`
   - Java: `software\.amazon\.awssdk\.services\.[a-z0-9]+`
   - .NET: `Amazon\.[A-Za-z0-9]+`
3. **Never Echo Literals:** Never output surrounding config lines, connection strings, or string literals into the conversation or logs.

## 2. Two Required IAM Roles for Elastic Beanstalk

Elastic Beanstalk requires two distinct IAM roles with separate trust policies:

### A. Service Role (`aws-elasticbeanstalk-service-role`)

Assumed by the Elastic Beanstalk control plane (`elasticbeanstalk.amazonaws.com`) to monitor instance health and orchestrate managed platform updates:

- **Trust Policy Principal:** `elasticbeanstalk.amazonaws.com` (with `sts:ExternalId: elasticbeanstalk`)
- **Managed Policies:**
  - `arn:aws:iam::aws:policy/service-role/AWSElasticBeanstalkEnhancedHealth`
  - `arn:aws:iam::aws:policy/AWSElasticBeanstalkManagedUpdatesCustomerRolePolicy`

### B. EC2 Instance Profile Role (`<app>-eb-ec2-role`)

Attached to EC2 instances (`ec2.amazonaws.com`) via an IAM Instance Profile:

- **Base Platform Managed Policies:**
  - `arn:aws:iam::aws:policy/AWSElasticBeanstalkWebTier` (for Web Server tier)
  - `arn:aws:iam::aws:policy/AWSElasticBeanstalkWorkerTier` (for Worker tier)
  - `arn:aws:iam::aws:policy/AWSElasticBeanstalkMulticontainerDocker` (only if running Docker on AL2023)
- **Scoped Custom Inline Policy (`<app>-workload-least-privilege`):**
  Grant only the specific API actions and resource ARNs required by the application and `environmentsecrets`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadEnvironmentSecrets",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "ssm:GetParameters"
      ],
      "Resource": [
        "arn:aws:secretsmanager:${AWS_REGION}:${ACCOUNT_ID}:secret:${APP_NAME}/*"
      ]
    },
    {
      "Sid": "AppSpecificS3BucketAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::${APP_BUCKET_NAME}/*"
      ]
    }
  ]
}
```

## 3. Mandatory Instance Metadata Service v2 (IMDSv2) Enforcement

Always enforce IMDSv2 (`HttpTokens=required`) on all Elastic Beanstalk EC2 instances to prevent SSRF credential theft:

```json
{
  "Namespace": "aws:autoscaling:launchconfiguration",
  "OptionName": "DisableIMDSv1",
  "Value": "true"
}
```
