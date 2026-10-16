---
name: aws-brownfield-migration
description: Discovers unmanaged live AWS resources via Cloud Control API (aws-mcp) and CloudFormation IaC Generator, and executes zero-downtime brownfield imports and cross-engine migrations into Terraform/OpenTofu, AWS CDK, CloudFormation, Crossplane, and Pulumi.
---

# AWS Brownfield Discovery, Import & Cross-Engine Migration

Use this skill whenever bringing existing, console-created ("ClickOps"), or drifted live AWS resources under Infrastructure-as-Code management, or migrating between IaC engines without downtime or resource replacement.

## 1. Live AWS Resource Discovery (`aws-mcp` Bridge)

Because `awslabs.aws-iac-mcp-server` focuses on offline template validation and documentation, always use **`aws-mcp`** (`aws___call_aws` / `aws___run_script`) to inventory live AWS resources before generating import blocks or templates:

### Step 1: Enumerate Live Resources via AWS Cloud Control API
```bash
# List live resources of any CloudFormation Registry type (e.g., AWS::S3::Bucket, AWS::RDS::DBInstance, AWS::EC2::VPC)
aws cloudcontrol list-resources --type-name AWS::RDS::DBInstance --region us-east-1

# Fetch the exact live desired-state properties of a specific resource
aws cloudcontrol get-resource --type-name AWS::RDS::DBInstance --identifier mydb-prod --region us-east-1
```

### Step 2: CloudFormation IaC Generator Scan (Bulk Account Discovery)
For bulk discovery of unmanaged resources across an account/region:
```bash
# 1. Start a resource scan
aws cloudformation start-resource-scan --region us-east-1

# 2. List scanned resources filtered by tag or type prefix
aws cloudformation list-resource-scan-resources \
  --resource-scan-id <scan-arn> \
  --resource-type-prefix AWS::EC2

# 3. Generate a CloudFormation template + import Change Set from discovered resources
aws cloudformation create-generated-template \
  --generated-template-name brownfield-network-import \
  --resources '[{"ResourceType":"AWS::EC2::VPC","ResourceIdentifier":{"VpcId":"vpc-0abc12345def67890"}}]'
```

## 2. Engine-Specific Zero-Downtime Import Workflows

### A. Terraform / OpenTofu (`aws-terraform`)
1. **Terraform 1.14+ Search & Bulk Config Generation (`.tfquery.hcl`)**:
   Create `discover.tfquery.hcl` with `list "aws_<resource>" "<label>" { provider = aws }` and run:
   ```bash
   terraform query -generate-config-out=imported.tf
   ```
2. **Config-Driven `import {}` Blocks (Terraform 1.5+)**:
   Prefer declarative `import {}` blocks committed to version control over imperative `terraform import` CLI calls:
   ```hcl
   import {
     to = aws_s3_bucket.audit_logs
     id = "my-existing-audit-logs-bucket"
   }
   ```
   Run `terraform plan -generate-config-out=generated_resources.tf`, refine the generated HCL, and verify `terraform plan` reports **`0 to add, 0 to change, 0 to destroy`** before applying.

### B. AWS CDK (`aws-cdk`)
1. **Read-Only Lookups (`fromLookup` / `from*Arn`)**:
   If the stack only needs to reference an existing VPC,HostedZone, or KMS Key without managing its lifecycle, use `ec2.Vpc.fromLookup(this, 'Vpc', { vpcId })` instead of importing.
2. **Full Lifecycle Adoption (`cdk import`)**:
   - Add the L1/L2 construct to the stack matching the exact live configuration and set `RemovalPolicy.RETAIN`.
   - Run `cdk diff` to verify only the new resource addition appears.
   - Run `cdk import <StackName>` and provide the physical resource ID mapping.
   - Alternatively, synthesize a CloudFormation template via IaC Generator (`create-generated-template`) and run `cdk migrate --from-stack --stack-name <name> --language typescript`.

### C. AWS CloudFormation (`aws-cloudformation`)
1. Add the target resource to the template with `DeletionPolicy: Retain` and properties matching `aws cloudcontrol get-resource`.
2. Create an **`IMPORT` Change Set**:
   ```bash
   aws cloudformation create-change-set \
     --stack-name prod-storage \
     --change-set-name import-audit-bucket \
     --change-set-type IMPORT \
     --resources-to-import '[{"ResourceType":"AWS::S3::Bucket","LogicalResourceId":"AuditBucket","ResourceIdentifier":{"BucketName":"my-existing-audit-logs-bucket"}}]' \
     --template-body file://template.yaml
   ```
3. Run `aws cloudformation detect-stack-drift --stack-name prod-storage` immediately after executing the import Change Set to confirm `IN_SYNC`.

### D. Crossplane (`aws-crossplane`)
1. **Observe-Only Discovery**:
   Author the Managed Resource with `metadata.annotations["crossplane.io/external-name"]: "<physical-aws-id>"`, `spec.deletionPolicy: Orphan`, and `spec.managementPolicies: ["Observe"]`.
2. **Verify Live Status**:
   Inspect `kubectl get <mr> -o yaml` `.status.atProvider` to confirm all fields match your desired `spec.forProvider`.
3. **Transition to Full Management**:
   Update `spec.managementPolicies: ["Observe", "Create", "Update", "LateInitialize"]` (keeping `deletionPolicy: Orphan` so Kubernetes object deletion never destroys the underlying AWS resource).

### E. Pulumi (`aws-pulumi`)
1. **Direct Resource Import**:
   - CLI: `pulumi import aws:s3/bucketV2:BucketV2 audit-logs my-existing-audit-logs-bucket --protect`
   - Code-first: Add `import: "my-existing-audit-logs-bucket"` and `protect: true` in `pulumi.ResourceOptions`, run `pulumi preview --diff` to confirm zero diff, then remove the `import` option after state adoption.
2. **Cross-Engine Migration to Pulumi**:
   - From Terraform HCL/state: follow `pulumi-terraform-to-pulumi` (`pulumi convert --from terraform --language typescript`).
   - From AWS CDK: follow `pulumi-cdk-to-pulumi` or `@pulumi/cdk` adapter.
   - From CloudFormation: follow `cloudformation-to-pulumi` (`pulumi import --from cloudformation`).

## 3. Golden Safety Rules for Brownfield Imports

- **Zero-Diff Rule**: Never execute an import apply if the plan/preview/change-set shows **any** destructive replacement (`-/+` or `Replacement: True`) on the imported resource. Fix attribute mismatches in code until the import plan is a pure state-adoption operation.
- **Retention First**: Always attach `prevent_destroy = true` (Terraform), `RemovalPolicy.RETAIN` (CDK), `DeletionPolicy: Retain` (CloudFormation), `deletionPolicy: Orphan` (Crossplane), or `protect: true` / `retainOnDelete: true` (Pulumi) **before** importing stateful production infrastructure.
