# Getting started

## Prerequisites

- Kubernetes cluster with Crossplane installed.
- Crossplane CLI and Docker available for local rendering.
- EKS OIDC provider and IRSA role if AWS is the target.
- Pinned Crossplane, provider, and function versions compatible with one another.
- `kubectl` context explicitly set to the intended cluster.

## Install order

1. Install Crossplane.
2. Apply `assets/authentication/deployment-runtime-config.yaml` after replacing the role ARN.
3. Apply provider packages for every service used by the Compositions. The example set needs the provider-family coordinator plus EC2, S3, and RDS service packages. Replace `<pin-version>` with an approved release.
4. Apply the matching `ProviderConfig` and wait for each Provider to become healthy.
5. Install `function-patch-and-transform` and `function-auto-ready` at pinned versions.
6. Apply XRDs, wait for them to become established, then apply Compositions.
7. Apply a namespaced Claim only after the contract and provider dependencies are ready.

## Safe verification commands

```bash
kubectl get providers.pkg.crossplane.io
kubectl get functions.pkg.crossplane.io
kubectl get xrd
kubectl get compositions.apiextensions.crossplane.io
kubectl describe provider <provider-name>
kubectl describe <claim-kind> <claim-name> -n <namespace>
kubectl get managed
kubectl get events -A --sort-by=.lastTimestamp
```

Use `kubectl apply --dry-run=server` for Kubernetes admission validation. It does not create AWS infrastructure, but it requires cluster access and installed CRDs. `crossplane render` and schema validation are offline checks and do not verify IAM, quotas, AWS API access, or readiness.

Never commit role credentials, kubeconfigs, access keys, generated secrets, or unreviewed provider package versions.
