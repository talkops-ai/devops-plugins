# Service coverage policy

The plugin supports authoring against the full AWS provider surface through schema discovery and service-package routing. It does not ship a hand-written Composition for every AWS API because provider CRDs are versioned and provider-specific.

## Bundled tested fixtures

- EC2: VPC, Internet Gateway, Subnet, RouteTable, Route, RouteTableAssociation
- S3: Bucket, PublicAccessBlock, ServerSideEncryptionConfiguration, Versioning
- RDS: SubnetGroup, SecurityGroup, Instance, connection details
- Platform: Provider, ProviderConfig, DeploymentRuntimeConfig, Pipeline Functions

## Service-package routing examples

| AWS domain | Typical provider family package |
|---|---|
| EC2/VPC | `provider-aws-ec2` |
| S3 | `provider-aws-s3` |
| RDS/Aurora | `provider-aws-rds` |
| Lambda | `provider-aws-lambda` |
| DynamoDB | `provider-aws-dynamodb` |
| EKS | `provider-aws-eks` |
| IAM | `provider-aws-iam` |
| KMS | `provider-aws-kms` |
| SQS/SNS | `provider-aws-sqs`, `provider-aws-sns` |
| EventBridge | `provider-aws-cloudwatch` or the package exposed by the selected release |

Package names and resource coverage must be checked against the selected Upbound release. See `provider-schema-discovery.md`. A generated resource is only accepted when its schema, provider package, lifecycle, security, and validation path are recorded.
