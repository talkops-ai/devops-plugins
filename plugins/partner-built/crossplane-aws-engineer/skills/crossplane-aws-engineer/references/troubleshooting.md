# Troubleshooting Crossplane AWS resources

| Symptom | First checks | Common root causes |
|---|---|---|
| Provider not healthy | `kubectl describe provider`, provider pod logs | Package incompatibility, missing family package, image pull, RBAC |
| `CannotInitializeManaged` | Managed Resource conditions/events | IRSA trust, missing IAM permission, invalid ProviderConfig, region |
| `CannotResolveResourceReference` | `kubectl describe` child and parent | Wrong ref kind/name, selector labels, sibling name assumption, dependency not ready |
| `Synced=False` | Events and provider logs | AWS validation, quota, immutable field, API throttling, network |
| Function error | `kubectl get functions`, Crossplane/function pod logs | Function version mismatch, invalid pipeline input, malformed patch |
| XR never Ready | All composed-resource conditions | One child not ready, readiness checks, secret publication, dependency cycle |
| Argo CD Degraded | Health customization and conditions | Lua mismatch, status not observed, sync wave ordering, resource exclusions |
| Delete does not finish | `deletionPolicy`, `managementPolicies`, AWS deletion protection | Intentional Orphan, provider-side protection, finalizer, dependent resource |

Use read-only diagnosis first. Do not solve an IAM failure with AdministratorAccess or wildcard policies. Do not retrieve or print plaintext connection secrets. For every correction, identify the exact resource ARN, provider role, field, condition, and ownership boundary.
