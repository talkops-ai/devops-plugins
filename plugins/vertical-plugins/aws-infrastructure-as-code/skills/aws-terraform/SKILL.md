---
name: aws-terraform
description: Authors, refactors, tests, imports, and validates production AWS Terraform and OpenTofu configurations using the dual hashicorp/aws + hashicorp/awscc provider strategy, S3/HCP state locking, .tftest.hcl test suites, .tfquery.hcl search/import, and HashiCorp style/policy standards.
---

# AWS Terraform & OpenTofu Engineering

Use this skill whenever authoring, refactoring, testing, importing, or validating **Terraform** or **OpenTofu** HCL configurations targeting AWS.

## 1. Version-Aware MCP Research Protocol (`terraform` + `aws-mcp`)

Never guess resource arguments, nested block schemas, or module inputs from memory. Always use the bundled **`terraform` MCP server** ([`hashicorp/terraform-mcp-server`](https://github.com/hashicorp/terraform-mcp-server)) to inspect the exact provider or module version:

1. **Determine Target Provider Version (`latest` vs. Pinned Version)**:
   - Inspect `versions.tf` or `.terraform.lock.hcl` in the workspace to see if a specific provider version is pinned (e.g., `5.82.0`).
   - For greenfield configs or version upgrades, call **`get_latest_provider_version`** (`namespace: "hashicorp"`, `name: "aws"` or `"awscc"`) to retrieve the current release version.
   - To inspect what features a provider version supports (`resources`, `data-sources`, `functions`, `guides`, `actions`, `ephemeral resources`, `list-resources`), call **`get_provider_capabilities`** (`namespace: "hashicorp"`, `name: "aws"`, `version: "<x.y.z|latest>"`).
2. **Search & Fetch Resource / Data-Source / Guide Details (`search_provider_docs` → `get_provider_details`)**:
   - **Step A**: Call **`search_provider_docs`** with:
     - `provider_name`: `"aws"` or `"awscc"`
     - `provider_namespace`: `"hashicorp"`
     - `service_slug`: single-word or underscore resource/service slug (e.g., `"s3_bucket"`, `"eks_cluster"`, `"iam_role"`)
     - `provider_document_type`: `"resources"`, `"data-sources"`, `"functions"`, `"guides"`, `"overview"`, `"actions"`, or `"list-resources"` (for Terraform Search `.tfquery.hcl`)
     - `provider_version`: `"<x.y.z>"` (matching the repo's pinned version) or `"latest"`
   - **Step B**: Pass the returned numeric `provider_doc_id` into **`get_provider_details`** (`provider_doc_id: "<id>"`) to read the full markdown documentation, required/optional parameters, nested blocks, exported attributes, and `import` syntax for that exact version.
3. **Search Public & Private Registry Modules & Policies (`terraform` MCP)**:
   - Call **`search_modules`**, **`get_latest_module_version`**, and **`get_module_details`** for public Registry modules (`terraform-aws-modules/vpc/aws`, `terraform-aws-modules/eks/aws`, `terraform-aws-modules/rds/aws`) or **`search_private_modules`** / **`get_private_module_details`** / **`search_private_providers`** / **`get_private_provider_details`** for HCP Terraform private registries.
   - Call **`search_policies`** and **`get_policy_details`** for Registry policy libraries.
4. **Check Regional Availability (`aws-mcp`)**:
   - Call `aws___get_regional_availability` when deploying newer services or Cloud Control (`awscc`) resource types across regions.

## 2. Dual-Provider Architecture (`hashicorp/aws` + `hashicorp/awscc`)

Combine the mature **`hashicorp/aws`** provider (deep custom diffing, IAM policy document data sources, battle-tested lifecycle hooks) with **`hashicorp/awscc`** (auto-generated from the AWS CloudFormation Registry / Cloud Control API for Day-0 AWS feature support and uniform schema semantics):

```hcl
# versions.tf
terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
    awscc = {
      source  = "hashicorp/awscc"
      version = "~> 1.25"
    }
  }

  backend "s3" {
    bucket       = "my-org-tfstate-123456789012-us-east-1"
    key          = "workloads/prod/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    kms_key_id   = "alias/terraform-state-key"
    use_lockfile = true # Native S3 lockfile (Terraform >= 1.10); use dynamodb_table on older versions
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "Terraform"
      Repository  = var.repository_name
    }
  }
}

provider "awscc" {
  region = var.aws_region
}
```

## 3. Code Structure, Style, and Safe Refactoring

Follow the HashiCorp Style Guide (see [`references/terraform-style-guide.md`](references/terraform-style-guide.md)):
- **Standard File Layout**: `versions.tf`, `providers.tf`, `main.tf`, `variables.tf`, `outputs.tf`, `locals.tf`, and domain-sliced files (`networking.tf`, `iam.tf`, `database.tf`) for large root modules.
- **Variables & Outputs**: Every `variable` must declare explicit `type`, `description`, `validation {}` blocks for constrained inputs, and `sensitive = true` for secrets/tokens. Every `output` must include a `description`.
- **IAM Policies**: Always prefer `data "aws_iam_policy_document"` over raw `jsonencode()` or heredoc JSON so Terraform validates syntax and merges policy statements cleanly.
- **Stateful Resource Protection**: Set `lifecycle { prevent_destroy = true }` on production RDS instances/clusters, DynamoDB tables, S3 buckets, and KMS keys.
- **Zero-Downtime Refactoring**: When renaming resources, splitting modules, or converting `count` to `for_each`, always emit declarative `moved { from = ... to = ... }` blocks (see [`references/refactor-module.md`](references/refactor-module.md)) so state migrates without destroying live AWS infrastructure.

## 4. Testing, Policy-as-Code, and Pre-Deploy Verification

1. **Format & Static Validation**:
   ```bash
   terraform fmt -check -recursive
   terraform init -backend=false
   terraform validate
   ```
2. **Native `.tftest.hcl` Suites (`tests/*.tftest.hcl`)**:
   - Author unit tests (`command = plan`) with `mock_provider "aws" {}` (Terraform 1.7+) to verify variable validations, tag propagation, encryption flags, and IAM conditions without AWS credentials (see [`references/terraform-test.md`](references/terraform-test.md)).
   - Execute with `terraform test`.
3. **Shift-Left Security & Linting**:
   - Run `tflint --recursive` and `checkov -d . --framework terraform` (or Sentinel / `.policy.hcl` policies via [`references/terraform-policy.md`](references/terraform-policy.md)) to block wildcard IAM policies, unencrypted storage, and `0.0.0.0/0` ingress.
4. **Search & Bulk Import (`.tfquery.hcl`)**:
   - Use Terraform 1.14+ `list "aws_..."` blocks in `.tfquery.hcl` with `terraform query -generate-config-out=imported.tf` and `import {}` blocks to bring brownfield resources under state cleanly (see [`references/terraform-search-import.md`](references/terraform-search-import.md)).
5. **Approval Gate**:
   - Always generate and present `terraform plan` (highlighting any `# forces replacement` or `destroy` actions) and wait for explicit `APPROVED` confirmation before running `terraform apply` or triggering an HCP Terraform run (`create_run` / `action_run`).

## 5. Bundled Reference Guides

- **[`references/terraform-style-guide.md`](references/terraform-style-guide.md)**: Official HashiCorp HCL conventions, file organization, naming, and formatting rules.
- **[`references/terraform-test.md`](references/terraform-test.md)**: Authoring `.tftest.hcl` unit and integration tests with `mock_provider` and `override_resource`.
- **[`references/terraform-search-import.md`](references/terraform-search-import.md)**: Discovering unmanaged AWS resources with `.tfquery.hcl` (`list` blocks) and generating `import {}` blocks.
- **[`references/refactor-module.md`](references/refactor-module.md)**: Refactoring root configurations into reusable modules using `moved` blocks without resource replacement.
- **[`references/terraform-policy.md`](references/terraform-policy.md)**: Authoring `.policy.hcl` and Sentinel policy-as-code suites.
- **[`references/terraform-stacks.md`](references/terraform-stacks.md)**: Multi-region and multi-account orchestration with `.tfstack.hcl` and `.tfdeploy.hcl`.
