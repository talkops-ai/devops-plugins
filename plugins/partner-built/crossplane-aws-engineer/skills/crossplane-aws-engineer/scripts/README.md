# Verification scripts

## Static checks

```bash
./check-manifests.sh
```

Parses all bundled YAML, validates shell syntax, optionally runs ShellCheck, and parses plugin JSON. It does not prove provider compatibility.

## Render

```bash
./render-test.sh ../assets/s3-bucket/claim.yaml ../assets/s3-bucket/composition.yaml
```

The default function versions are pinned in the script and can be overridden after compatibility review:

```bash
PATCH_FUNCTION_VERSION=vX.Y.Z AUTO_READY_VERSION=vX.Y.Z ./render-test.sh <claim> <composition>
```

For reproducible CI, pass a checked-in functions manifest whose versions match the target cluster.

## Provider schema validation

```bash
./validate-schemas.sh <claim> <composition> <provider-schema-bundle> <functions-manifest>
```

The schema bundle must come from the exact Upbound provider release used by the Composition. Crossplane CLI 2.x uses `crossplane resource validate`; the script retains a compatibility fallback for older CLIs. The script does not access AWS, but the CLI may download provider schemas when the supplied extensions file contains Provider package manifests. Verify the command against the installed Crossplane CLI version in CI.

## Live cluster checks

After offline checks, use a reviewed Kubernetes server-side dry run and inspect conditions/events. None of these scripts creates AWS infrastructure.
