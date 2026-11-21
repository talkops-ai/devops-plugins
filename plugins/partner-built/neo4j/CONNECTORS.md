# Connector setup: Neo4j Support Specialist

This partner-built plugin bundles [`.mcp.json`](./.mcp.json) and [`mcp.json`](./mcp.json) pre-wired for the official **Neo4j Support Specialist** remote MCP server (`neo4j`). Supply `NEO4J_MCP_URL` (e.g. `https://<host>:7474/db/neo4j/mcp`) and `NEO4J_MCP_AUTH` (Base64 `user:password`) in your shell environment before launching your agent host.

## Connectors

| Key | Server | Use it for |
|---|---|---|
| `neo4j` | [Neo4j Support Specialist MCP](https://neo4j.com) | Official Neo4j 2026.x read-only diagnostics and A1–A12 support runbooks for Neo4j on EKS, ECS, and EC2. |

### `neo4j`

Endpoint: `https://<host>:<port>/db/neo4j/mcp` (`Authorization: Basic ${NEO4J_MCP_AUTH}`)
