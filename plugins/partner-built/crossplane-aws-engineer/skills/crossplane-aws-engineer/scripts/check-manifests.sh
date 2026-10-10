#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
command -v ruby >/dev/null || { echo "ruby is required for YAML parsing" >&2; exit 127; }

ruby -e '
require "yaml"
files = Dir[ARGV[0] + "/assets/**/*.yaml"]
abort "No YAML assets found" if files.empty?
files.each do |file|
  YAML.load_stream(File.read(file))
  puts "YAML OK #{file}"
end
' "${ROOT}"

for file in "${ROOT}"/scripts/*.sh; do
  bash -n "${file}"
  echo "Shell syntax OK ${file}"
done

if command -v shellcheck >/dev/null; then
  shellcheck "${ROOT}"/scripts/*.sh
  echo "Shellcheck OK"
else
  echo "shellcheck not installed; skipped" >&2
fi

ruby -e '
require "json"
ARGV.each { |file| JSON.parse(File.read(file)); puts "JSON OK #{file}" }
' "${ROOT}/../..//plugin.json" "${ROOT}/../../.claude-plugin/plugin.json" "${ROOT}/../../.codex-plugin/plugin.json"

echo "Manifest checks completed. Crossplane rendering and provider schema validation require their pinned toolchain."
