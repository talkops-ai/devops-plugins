#!/usr/bin/env bash
set -euo pipefail

CLAIM_FILE="${1:?usage: validate-schemas.sh <claim-or-xr> <composition> <provider-schema-bundle> [functions-manifest]}"
COMPOSITION_FILE="${2:?usage: validate-schemas.sh <claim-or-xr> <composition> <provider-schema-bundle> [functions-manifest]}"
SCHEMAS="${3:?provider CRD schema bundle/path is required}"
FUNCTIONS_MANIFEST="${4:-}"
RENDERED="$(mktemp)"
trap 'rm -f "${RENDERED}"' EXIT

[[ -e "${SCHEMAS}" ]] || { echo "Provider schema bundle not found: ${SCHEMAS}" >&2; exit 2; }
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/render-test.sh" "${CLAIM_FILE}" "${COMPOSITION_FILE}" "${FUNCTIONS_MANIFEST}" >"${RENDERED}"
command -v crossplane >/dev/null || { echo "crossplane CLI is required" >&2; exit 127; }
# The schema bundle and rendered object stream must come from the same provider release.
# Crossplane CLI 2.x uses `resource validate`; older CLIs used `beta validate schemas`.
if crossplane resource validate --help >/dev/null 2>&1; then
  crossplane resource validate "${SCHEMAS}" "${RENDERED}" --error-on-missing-schemas
else
  crossplane beta validate schemas "${SCHEMAS}" "${RENDERED}"
fi
echo "Composition rendered and provider schema validation completed."
