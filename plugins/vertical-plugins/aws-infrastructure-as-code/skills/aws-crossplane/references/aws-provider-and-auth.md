# Upbound AWS providers and IRSA

Use only the service packages required by the platform, for example `xpkg.upbound.io/upbound/provider-aws-ec2`, `provider-aws-s3`, and `provider-aws-rds`, plus the provider family package when required by the selected release. Pin versions and verify package compatibility with the target Crossplane release.

Production authentication should use EKS OIDC and IRSA:

```yaml
apiVersion: pkg.crossplane.io/v1beta1
kind: DeploymentRuntimeConfig
metadata:
  name: provider-aws-runtime
spec:
  serviceAccountTemplate:
    metadata:
      annotations:
        eks.amazonaws.com/role-arn: arn:aws:iam::<account-id>:role/<least-privilege-role>
---
apiVersion: pkg.crossplane.io/v1
kind: Provider
metadata:
  name: provider-aws-s3
spec:
  package: xpkg.upbound.io/upbound/provider-aws-s3:<pinned-version>
  runtimeConfigRef:
    name: provider-aws-runtime
---
apiVersion: aws.upbound.io/v1beta1
kind: ProviderConfig
metadata:
  name: default
spec:
  credentials:
    source: IRSA
```

The role trust policy must bind the EKS OIDC subject to the provider ServiceAccount and use least-privilege AWS permissions. Scope roles by service family where practical. Never place access keys in a Kubernetes Secret or generated manifest. Confirm the exact API versions and fields against the installed provider CRDs before applying.
