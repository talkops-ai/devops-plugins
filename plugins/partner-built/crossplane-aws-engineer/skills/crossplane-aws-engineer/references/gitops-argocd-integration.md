# Argo CD integration

Crossplane resources are asynchronous. Configure Argo CD deliberately rather than marking every progressing XR as failed. Annotation tracking avoids collisions caused by Crossplane labels when parent and composed resources are tracked together. Exclude ephemeral `ProviderConfigUsage` only if it is not part of the desired platform inventory.

Use sync waves for dependency intent, for example provider packages before XRDs, XRDs/compositions before Claims, and network Claims before stateful services. Sync waves do not replace Crossplane references or readiness checks.

Register a health customization for provider resources that maps `Ready=True` and `Synced=True` to Healthy, `Synced=False` to Degraded, and absent conditions to Progressing. Validate the Lua against the Argo CD version. Tune API QPS/Burst only after measuring API-server load; do not copy performance values blindly.
