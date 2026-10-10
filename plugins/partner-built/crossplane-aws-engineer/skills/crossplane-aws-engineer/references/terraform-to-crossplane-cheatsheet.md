# Terraform to Crossplane cheatsheet

| Terraform | Crossplane | Operational meaning |
|---|---|---|
| `module` | XRD + Composition | Contract is separated from implementation. |
| `variable` | XRD OpenAPI parameter | Validate and default at the Kubernetes API boundary. |
| module call | namespaced Claim | Consumer-facing self-service API. |
| resource | Managed Resource | 1:1 cloud object continuously reconciled. |
| `depends_on` | `*Ref`, `*Selector`, or composed status patch | Let controllers wait on observed identifiers. |
| output | XR status or connection detail | Do not expose provider internals by default. |
| `prevent_destroy` | `deletionPolicy: Orphan` plus deletion protection | Kubernetes deletion must not destroy data. |
| `ignore_changes` | narrowly scoped management/ownership policy | Document which system owns the field. |
| plan | `crossplane render` + schema validation | Offline shape check; not an AWS readiness check. |

Crossplane stores desired and observed state in Kubernetes and reconciles continuously. A rendered manifest can still fail because of IAM, quotas, provider versions, network reachability, or AWS eventual consistency. Use `kubectl describe` and events for live diagnosis.
