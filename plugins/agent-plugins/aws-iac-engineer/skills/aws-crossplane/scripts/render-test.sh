#!/usr/bin/env bash
set -euo pipefail

CLAIM_FILE="${1:?usage: render-test.sh <claim-or-xr> <composition> [functions-manifest]}"
COMPOSITION_FILE="${2:?usage: render-test.sh <claim-or-xr> <composition> [functions-manifest]}"
FUNCTIONS_MANIFEST="${3:-}"
PATCH_FUNCTION_VERSION="${PATCH_FUNCTION_VERSION:-v0.8.2}"
AUTO_READY_VERSION="${AUTO_READY_VERSION:-v0.5.0}"
TMP_FUNCTIONS=""
trap 'if [[ -n "${TMP_FUNCTIONS}" ]]; then rm -f "${TMP_FUNCTIONS}"; fi' EXIT

[[ -f "${CLAIM_FILE}" ]] || { echo "Claim/XR file not found: ${CLAIM_FILE}" >&2; exit 2; }
[[ -f "${COMPOSITION_FILE}" ]] || { echo "Composition file not found: ${COMPOSITION_FILE}" >&2; exit 2; }

if [[ -z "${FUNCTIONS_MANIFEST}" ]]; then
  TMP_FUNCTIONS="$(mktemp)"
  cat >"${TMP_FUNCTIONS}" <<YAML
apiVersion: pkg.crossplane.io/v1
kind: Function
metadata:
  name: function-patch-and-transform
spec:
  package: xpkg.crossplane.io/crossplane-contrib/function-patch-and-transform:${PATCH_FUNCTION_VERSION}
---
apiVersion: pkg.crossplane.io/v1
kind: Function
metadata:
  name: function-auto-ready
spec:
  package: xpkg.crossplane.io/crossplane-contrib/function-auto-ready:${AUTO_READY_VERSION}
YAML
  FUNCTIONS_MANIFEST="${TMP_FUNCTIONS}"
else
  [[ -f "${FUNCTIONS_MANIFEST}" ]] || { echo "Function manifest not found: ${FUNCTIONS_MANIFEST}" >&2; exit 2; }
fi

command -v crossplane >/dev/null || { echo "crossplane CLI is required" >&2; exit 127; }
crossplane composition render "${CLAIM_FILE}" "${COMPOSITION_FILE}" "${FUNCTIONS_MANIFEST}" --include-full-xr
