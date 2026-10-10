# Provider authentication fixture

This fixture covers the bundled VPC, S3, and RDS examples. Replace every `<pin-version>` with the same approved and mutually compatible release family after checking the target Crossplane version and Upbound package metadata. Provider package names and API versions can change; verify them before applying.

Required packages for the bundled examples:

- `provider-family-aws`
- `provider-aws-ec2`
- `provider-aws-s3`
- `provider-aws-rds`

The `DeploymentRuntimeConfig` ServiceAccount annotation must reference an IAM role trusted by the EKS OIDC provider and scoped to the APIs used by each provider family. Split roles by service family when the platform security model requires it. `ProviderConfig` uses IRSA and must not reference static credentials.

Recommended sequence:

```bash
kubectl apply -f deployment-runtime-config.yaml
kubectl apply -f provider.yaml
kubectl wait --for=condition=Healthy provider.pkg.crossplane.io --all --timeout=10m
```

The wait command is a live-cluster operation. Inspect provider events and pods if it fails. Do not commit role credentials or generated secrets.
