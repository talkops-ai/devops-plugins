#!/usr/bin/env sh
# Compact wrapper for awslabs.billing-cost-management-mcp-server so standalone MCP hosts
# that derive tool prefixes from the executable basename keep tool names under 64 chars.
exec uvx awslabs.billing-cost-management-mcp-server@latest "$@"
