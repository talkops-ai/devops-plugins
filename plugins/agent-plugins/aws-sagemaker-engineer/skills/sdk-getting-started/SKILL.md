---
name: sdk-getting-started
description: >-
  Validates the user's local and cloud environment for SageMaker AI operations — checks
  SageMaker Python SDK v3 version (>=3.17.0,<4.0), AWS region, execution role trust/permissions,
  and local MCP/IaC platform prerequisites (Apple Silicon rustup x86_64-apple-darwin target for
  cfn-guard/awsiac, Windows uvx binary suffix). Use when the user says "set up", "getting started",
  "check my environment", "configure SDK", or before running SDK scripts or IaC validation.
metadata:
  version: "2.0.0"
---

# SDK Getting Started

Preflight checks to verify the user's environment can run SageMaker AI SDK operations and local MCP tooling. The agent runs these checks directly (no notebook generation) and stores `REGION` and `ROLE_ARN` in conversation context for downstream skills.

## Principles

1. **Don't ask for what you can look up.** Resolve SDK version, region, and execution role programmatically before asking the user.
2. **Surface platform-specific MCP prerequisites early.** When the plan includes IaC validation (`sagemaker-domain-vpc-iac` with `awsiac`) or local MCP troubleshooting, verify platform compatibility up front.

## Workflow

Read and follow `references/sagemaker-python-sdk-setup.md` and `references/execution-role-setup.md`.

## References

- `references/sagemaker-python-sdk-setup.md` — SageMaker Python SDK v3 version (`>=3.17.0,<4.0`), region, execution role, and Apple Silicon / Windows MCP environment checks
- `references/execution-role-setup.md` — Execution role resolution, trust policy (`sagemaker.amazonaws.com`, `bedrock.amazonaws.com`, `lambda.amazonaws.com`), and least-privilege IAM validation
