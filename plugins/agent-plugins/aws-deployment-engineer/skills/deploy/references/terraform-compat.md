# Terraform / OpenTofu Parity & Checkov Compliance Guide

When a repository contains `.tf` files or the user requests **Terraform** or **OpenTofu**, match the existing workflow rather than forcing a migration to AWS CDK.

## 1. State Management & Backend Hardening (`terraform {}`)

1. **Remote State in S3 with Native S3 Lockfile (`Terraform >= 1.10` / OpenTofu):**
   Always configure encrypted S3 remote state with native lockfile support (`use_lockfile = true`, replacing deprecated DynamoDB state lock tables):
   ```hcl
   terraform {
     required_version = ">= 1.10.0"

     required_providers {
       aws = {
         source  = "hashicorp/aws"
         version = "~> 5.80"
       }
     }

     backend "s3" {
       bucket       = "my-org-tfstate-111122223333-us-east-1"
       key          = "workloads/my-app/terraform.tfstate"
       region       = "us-east-1"
       encrypt      = true
       use_lockfile = true
     }
   }
   ```
2. **Never Commit State or Secret `.tfvars`:**
   Ensure `.gitignore` excludes `.terraform/`, `*.tfstate`, `*.tfstate.*`, `crash.log`, and `*.auto.tfvars` / `terraform.tfvars` containing sensitive values.
3. **Mark Sensitive Variables & Avoid Plaintext Secrets in State:**
   Never generate secret values via `random_password` and pass them into RDS/ECS if you can use AWS-managed secret rotation (`manage_master_user_password = true` on `aws_db_instance` / `aws_rds_cluster`), which stores the master password directly in AWS Secrets Manager without ever writing it to `terraform.tfstate`!

## 2. Cost Estimation & Validation Workflow for Terraform

1. **FinOps Cost Scan:**
   Call `awspricing` -> `analyze_terraform_project` on the workspace directory, then query `get_pricing` for the target region to build the mandatory monthly cost breakdown table (`hourly_rate * 730`).
2. **Syntax & Formatting Check (`PostToolUse` Hook):**
   Editing `.tf` files triggers `scripts/validate-iac.sh`, which runs `terraform fmt -check` and `terraform validate` (when initialized).
3. **Static Security Policy Scanning (`checkov`):**
   Before running `terraform plan` or `terraform apply`, scan the configuration with Checkov if installed:
   ```bash
   checkov -d . --framework terraform --quiet --compact
   ```
   Remediate any failed `CKV_AWS_*` controls (public S3 buckets, unencrypted EBS/RDS/SNS/SQS, overly permissive security groups, missing IMDSv2 `http_tokens = "required"`).

## 3. Approval-Gated Execution

1. Run a saved, deterministic plan:
   ```bash
   terraform plan -out=tfplan
   ```
2. Summarize the planned additions, in-place updates, and replacements (`-/+` destructive replacements must be highlighted in bold!).
3. **WAIT** for explicit user confirmation before executing:
   ```bash
   terraform apply tfplan
   ```
4. Invoke `verify-and-rollback` immediately after `terraform apply` completes.
