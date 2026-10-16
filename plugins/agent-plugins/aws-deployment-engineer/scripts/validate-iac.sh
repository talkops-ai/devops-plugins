#!/usr/bin/env bash
# validate-iac.sh - PostToolUse hook for validating CloudFormation, AWS SAM, and Terraform files
# Receives JSON on stdin with tool_input.file_path
# Outputs JSON with systemMessage field so the agent can immediately self-correct syntax/schema issues

set -euo pipefail

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    path = data.get('tool_input', {}).get('file_path', '')
    print(path)
except Exception:
    print('')
" 2>/dev/null || echo "")

if [[ -z "$FILE_PATH" ]] || [[ ! -f "$FILE_PATH" ]]; then
    exit 0
fi

emit_message() {
    local msg="$1"
    local escaped
    escaped=$(printf '%s' "$msg" | python3 -c "import sys, json; print(json.dumps(sys.stdin.read().strip()))" 2>/dev/null || echo '"IaC validation completed."')
    echo "{\"systemMessage\": ${escaped}}"
    exit 0
}

BASENAME=$(basename "$FILE_PATH")
DIRNAME=$(dirname "$FILE_PATH")

# 1. Terraform (.tf) validation
if [[ "$FILE_PATH" =~ \.tf$ ]]; then
    if command -v terraform >/dev/null 2>&1; then
        FMT_OUT=$(terraform fmt -check "$FILE_PATH" 2>&1) && FMT_STATUS=0 || FMT_STATUS=$?
        if [[ -d "${DIRNAME}/.terraform" ]]; then
            VAL_OUT=$(terraform -chdir="$DIRNAME" validate -no-color 2>&1) && VAL_STATUS=0 || VAL_STATUS=$?
            if [[ $VAL_STATUS -ne 0 ]]; then
                emit_message "Terraform validation failed in ${DIRNAME}:
${VAL_OUT}"
            fi
        fi
        if [[ $FMT_STATUS -ne 0 ]]; then
            emit_message "Terraform formatting check flagged ${BASENAME} (run 'terraform fmt'):
${FMT_OUT}"
        fi
        emit_message "Terraform syntax check passed for ${BASENAME}."
    fi
    exit 0
fi

# 2. Check if YAML/JSON file is an AWS SAM or CloudFormation template
if [[ ! "$FILE_PATH" =~ \.(yaml|yml|json|template)$ ]]; then
    exit 0
fi

TEMPLATE_KIND=$(python3 - "$FILE_PATH" <<'PY' 2>/dev/null || echo "NONE"
import sys, pathlib

p = pathlib.Path(sys.argv[1])
name = p.name.lower()
try:
    text = p.read_text(errors="ignore")[:16384]
except Exception:
    sys.exit(0)

if "AWS::Serverless-2016-10-31" in text or name in ("template.yaml", "template.yml") or name.endswith((".sam.yaml", ".sam.yml")):
    print("SAM")
elif "AWSTemplateFormatVersion" in text or ("Resources:" in text and "Type: AWS::" in text) or ('"Resources"' in text and '"AWS::' in text) or name.endswith((".cfn.yaml", ".cfn.yml", ".cfn.json", ".template.json", ".template.yaml")):
    print("CFN")
else:
    print("NONE")
PY
)

if [[ "$TEMPLATE_KIND" == "NONE" ]]; then
    exit 0
fi

if [[ "$TEMPLATE_KIND" == "SAM" ]]; then
    if command -v sam >/dev/null 2>&1; then
        OUTPUT=$(sam validate --template "$FILE_PATH" --lint 2>&1) && STATUS=0 || STATUS=$?
        if [[ $STATUS -eq 0 ]]; then
            emit_message "AWS SAM template validation and linting passed for ${BASENAME}."
        else
            emit_message "AWS SAM template validation/linting failed for ${BASENAME}:
${OUTPUT}"
        fi
    elif command -v cfn-lint >/dev/null 2>&1; then
        OUTPUT=$(cfn-lint "$FILE_PATH" 2>&1) && STATUS=0 || STATUS=$?
        if [[ $STATUS -eq 0 ]]; then
            emit_message "cfn-lint validation passed for ${BASENAME}."
        else
            emit_message "cfn-lint validation failed for ${BASENAME}:
${OUTPUT}"
        fi
    fi
    exit 0
fi

if [[ "$TEMPLATE_KIND" == "CFN" ]]; then
    if command -v cfn-lint >/dev/null 2>&1; then
        OUTPUT=$(cfn-lint "$FILE_PATH" 2>&1) && STATUS=0 || STATUS=$?
        if [[ $STATUS -eq 0 ]]; then
            emit_message "CloudFormation cfn-lint validation passed for ${BASENAME}."
        else
            emit_message "CloudFormation cfn-lint validation failed for ${BASENAME}:
${OUTPUT}"
        fi
    fi
    exit 0
fi

exit 0
