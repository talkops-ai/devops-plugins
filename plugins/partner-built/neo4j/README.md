# Neo4j Support Specialist

Official Neo4j 2026.x read-only diagnostics and `A1`–`A12` support runbooks for self-managed Neo4j on Amazon EKS, ECS, and EC2 with bundled Neo4j MCP configuration (`NEO4J_MCP_URL`, `NEO4J_MCP_AUTH`).

Maintained by **Neo4j, Inc.** (skills redistributed unmodified from [`aws/tools-for-devops-agent`](https://github.com/aws/tools-for-devops-agent) under Apache-2.0).

## Install

| Host | How |
|---|---|
| Claude Code | `/plugin marketplace add talkops-ai/devops-plugins`, then `/plugin install neo4j@talkops-devops-plugins` |
| Codex | `codex plugin marketplace add talkops-ai/devops-plugins`, then install `neo4j` |
| Other Agent Plugins hosts | Load this directory (`plugin.json`, `skills/`, `mcp.json`) |

## Configuration

Set `NEO4J_MCP_URL` (e.g. `https://<host>:7474/db/neo4j/mcp`) and `NEO4J_MCP_AUTH` (Base64 `user:password`) before starting your session. See [`CONNECTORS.md`](./CONNECTORS.md) for endpoint details.

## Skills (1)

| Skill | Description |
|---|---|
| `neo4j-support-specialist` | Diagnoses self-managed Neo4j 2026.x on Amazon EKS (Neo4j Helm chart), Amazon ECS or Amazon EC2 from read-only evidence: container output, pod and task state, Helm ConfigMaps, ta... |

## Slash commands (2)

| Command | Purpose |
|---|---|
| `/neo4j:diagnose-cluster` | Run read-only Neo4j 2026.x health, Raft cluster topology, memory/pagecache, and lock diagnostics |
| `/neo4j:triage-query` | Investigate slow Cypher queries, lock contention, GC pauses, and OOM symptoms using Neo4j A1–A12 runbooks |

## Hooks

- **`hooks/secret-safety.py`** (`PreToolUse`): Prevents reading or echoing local credentials, `.env` files, private keys, and tokens.
