# Composition functions

Pipeline execution is ordered. `function-patch-and-transform` receives the XR and observed state and returns desired composed resources; later steps receive the accumulated desired state. `function-auto-ready` should normally be last so the XR becomes Ready only after composed resources meet readiness conditions.

Use patch-and-transform for straightforward field mapping, tags, status propagation, and transforms. Use a maintained function such as KCL or Go templating only for logic that cannot be expressed safely with patches. Pin OCI function versions. Keep functions deterministic and avoid embedding credentials or cloud-side imperative calls.

Every composed resource needs a stable logical name. Cross-resource dependencies should use provider references/selectors and composed-resource readiness rather than ordering assumptions. Render with the same function package versions used by the cluster.
