# Provider schema discovery

Provider CRDs are the source of truth for provider fields. Terraform names, AWS API names, and Upjet Kubernetes names are not interchangeable.

## Cluster inspection

```bash
kubectl api-resources | grep -E 'aws.upbound.io|ec2.aws.upbound.io|s3.aws.upbound.io|rds.aws.upbound.io'
kubectl explain <kind>.spec.forProvider --api-version=<api-version>
kubectl get crd <plural>.<group> -o yaml > /tmp/<kind>-crd.yaml
```

Inspect the CRD OpenAPI schema for field types, required fields, enum values, immutable behavior, reference fields, selectors, and status paths. Confirm the provider package and version that owns the CRD:

```bash
kubectl get provider.pkg.crossplane.io <provider-name> -o yaml
kubectl describe provider.pkg.crossplane.io <provider-name>
```

## Offline package inspection

When a provider package is available locally, inspect its CRDs before composing. Keep the package version, function versions, Crossplane version, and generated schema bundle together in CI. Do not use a schema from a different provider release.

## Required discovery record

For each Managed Resource used in a Composition, record:

- package and version
- `apiVersion` and `kind`
- required `spec.forProvider` fields
- supported references/selectors
- region/account/provider configuration fields
- status paths used for XR status
- connection-secret keys
- deletion and management-policy behavior
- encryption, backup, network, and observability fields

If any item is unknown, stop generation and mark it as an assumption rather than guessing.
