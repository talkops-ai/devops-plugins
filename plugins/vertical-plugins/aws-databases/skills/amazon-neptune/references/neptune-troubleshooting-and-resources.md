# Amazon Neptune — Troubleshooting & Additional Resources

> Extracted verbatim from `SKILL.md` for progressive disclosure. Relative paths (`references/...`, `scripts/...`) resolve from the skill root directory.

## Troubleshooting

### Supernode — slow traversals on high-cardinality vertices

A "supernode" is a vertex with millions of edges (e.g., a popular tag, a celebrity user). Unfiltered `.out()` / `.in()` traversals fan out over every edge and time out.

**You MUST apply ALL of the following when a supernode is diagnosed:**

1. **Filter early** — use `.hasLabel()` and `.has('prop', value)` immediately after `.out()/.in()` to prune.
2. **Add `.limit(N)`** on exploratory traversals to bound the fan-out.
3. **Consider splitting the supernode** — e.g., partition by time bucket (a `Month` vertex per period) so each child vertex has bounded cardinality.
4. **Use edge indexes** where available on frequently filtered edge properties.

Rewritten Gremlin with filters applied before expansion:

```
g.V(popularTagId).inE('TAGGED').has('year', targetYear).outV().hasLabel('Post').limit(100)
```

### Connection errors / 403 / timeout

VPC reachability (Neptune Database is deployed inside a VPC; optional public endpoints require IAM auth — see Neptune userguide for the minimum engine version), IAM auth signing (IAM auth requires SigV4-signed requests), security group inbound on port 8182 (Database) / varies (Analytics). See [connectivity.md](references/connectivity.md).

### openCypher query fails on Neptune but works on Neo4j

Check the incompatibilities in §Task 5. Most common: `apoc.*` calls, exotic path-expressions, and label predicates inside `CASE` / `WHEN` (Neptune Analytics silently returns 0 rows in that case). `CALL { }` subqueries support read queries but not Cypher update clauses; top-level Neptune Analytics `.mutate` procedures are separate and can write result properties.

### Slow load / bulk loader errors

See [troubleshooting.md](references/troubleshooting.md). Common causes: S3 permissions, CSV schema mismatch, IAM role not attached.

### When NOT to use Neptune

Not for pure documents (DocumentDB), time-series (Timestream), relational (RDS/Aurora), or key-value at scale (DynamoDB). Neptune is for **multi-hop traversal over relationships**.

## Additional Resources

- [Amazon Neptune Developer Guide](https://docs.aws.amazon.com/neptune/latest/userguide/)
- [Neptune Analytics User Guide](https://docs.aws.amazon.com/neptune-analytics/latest/userguide/)
- [Neptune Pricing](https://aws.amazon.com/neptune/pricing/)
- [Neptune openCypher Reference](https://docs.aws.amazon.com/neptune/latest/userguide/access-graph-opencypher.html)
- [Neo4j-to-Neptune Migration Tool](https://github.com/awslabs/amazon-neptune-tools/tree/master/neo4j-to-neptune)

Deep dives (load on demand): [data-modeling](references/data-modeling.md), [querying](references/querying.md), [connectivity](references/connectivity.md), [performance](references/performance.md), [troubleshooting](references/troubleshooting.md), [migration](references/migration.md), [graphrag](references/graphrag.md), [agentic-memory](references/agentic-memory.md), [analytics-vs-database](references/analytics-vs-database.md), [decision-guide](references/decision-guide.md), [use-cases](references/use-cases.md), [artifact-delivery](references/artifact-delivery.md), [action-safety](references/action-safety.md), [security](references/security.md), [boundary-doc](references/boundary-doc.md).

## Handoff from aws-database-selection

This skill can be invoked directly, or it can be entered from the `aws-database-selection` parent skill after that skill has run a requirements interview and produced a `requirements.json` artifact. When you see a backtick-wrapped path matching `aws_dbs_requirements/*/requirements.json` in recent conversation, follow the entry protocol in `aws-database-selection/handoff-contract.md`:

1. Read the artifact using `file_read`.
2. Validate it against `aws-database-selection/workload-primary-artifact.schema.json`. If malformed or unreadable, tell the user and proceed without it.
3. Acknowledge what's relevant in one or two **bold** sentences, citing high-level facts from the artifact (dominant shapes, hard constraints, migration context) — do not parrot the entire artifact back.
4. Scope-check: this skill is scoped to Amazon Neptune graph database and Neptune Analytics — Gremlin/openCypher/SPARQL, graph use cases, Neo4j migration. If the artifact's `workload_primaries.dominant_shapes` or `migration_context` don't match that scope, emit weak backpressure per the handoff contract: suggest `amazon-aurora` for relational workloads with graph-like self-joins, `dynamodb-skill` for shallow adjacency-list modeling, or go back to `aws-database-selection` if the dominant shape isn't graph traversal, then ask the user whether to go back or proceed anyway. Do not silently misuse the artifact.
5. Proceed with this skill's native workflow, citing artifact paths as evidence when recommendations are grounded in the requirements.

All user-facing output from this skill follows the markdown-primitives-only formatting convention in the handoff contract: bold labels, backticks for paths and enum values, bullet lists for alternatives, no ASCII art or box-drawing characters.
