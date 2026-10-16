# Connection secret propagation

For a credential-producing Managed Resource:

1. Set `writeConnectionSecretToRef` to a controlled namespace such as `crossplane-system` and generate its name from XR metadata.
2. In the Composition resource entry, list only approved `connectionDetails` keys.
3. In the XRD, use `spec.connectionSecretKeys` to allow only the consumer contract keys.
4. Let the Claim request projection with `spec.writeConnectionSecretToRef.name` in its own namespace.
5. Apply namespace RBAC and external secret encryption controls independently; Crossplane filtering is not a substitute for Kubernetes secret security.

Never print secret values during diagnosis. If the secret is absent, inspect conditions, events, provider logs, and key names without retrieving plaintext.
