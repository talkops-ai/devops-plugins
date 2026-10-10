# Authoring a Crossplane API for any AWS service

This plugin cannot safely hardcode every AWS service schema because Upbound provider families and releases change. Use this procedure for EC2, Lambda, DynamoDB, EKS, IAM, KMS, SQS, SNS, EventBridge, CloudFront, Route 53, OpenSearch, and other services.

## 1. Select the service package

Map the AWS service to its modular provider package, for example `provider-aws-lambda`, `provider-aws-dynamodb`, or `provider-aws-kms`. Confirm the package exists for the selected release and install only required packages.

## 2. Discover the exact CRD

Use `kubectl api-resources`, `kubectl explain`, the installed CRD YAML, or the provider package schema. Record the exact `apiVersion`, `kind`, `spec.forProvider` fields, reference/selector fields, immutable fields, status paths, and connection-secret keys. Never infer Upjet field names from Terraform alone.

## 3. Design the platform contract

Expose a domain-oriented Claim such as `Queue`, `ApplicationKey`, or `ObjectStore`, not a raw provider kind. Keep provider-specific fields behind the Composition. Add descriptions, required fields, defaults, enums, ranges, patterns, status fields, and lifecycle semantics to the XRD.

## 4. Compose and secure the resource

Create a Pipeline Composition. Patch only supported fields. Add region/provider configuration, deterministic tags, encryption, private networking, backups, deletion behavior, and observability appropriate to the service. Use `matchControllerRef` selectors for sibling composed resources. Use `*Ref`/`*Selector` for external resources. Add connection details only when the service emits credentials and filter them at the XRD.

## 5. Validate and operate

Render against the exact functions used by the cluster, validate against the exact provider schemas, run Kubernetes server-side dry run, then observe conditions/events after applying through GitOps. Document asynchronous readiness, quotas, IAM requirements, and rollback/orphan behavior.

## Service design minimums

| Service category | Minimum review questions |
|---|---|
| Network | Routes, AZs, private/public semantics, SGs, flow logs, endpoints, egress, CIDR overlap |
| Storage | Encryption, public access, versioning, retention, lifecycle, ownership, replication |
| Database | Private subnets, SGs, encryption, backups, deletion protection, monitoring, secrets |
| Compute | IAM role, IMDS/security, networking, scaling, health checks, patching, logs |
| Messaging | Encryption, DLQ, retention, access policy, cross-account boundaries, delivery semantics |
| Identity/security | Least privilege, trust conditions, KMS key policy, rotation, no static credentials |
| Edge/DNS | TLS, origin access, health checks, WAF, routing, propagation, certificate region |
| Observability | Logs, metrics, alarms, retention, sensitive-data filtering, ownership |

A service is not considered covered merely because its provider CRD exists. Coverage requires a documented schema-discovery path and a tested Composition or an explicit statement that platform-specific abstraction is still required.
