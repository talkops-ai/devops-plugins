# Amazon Aurora PostgreSQL — Troubleshooting & Additional Resources

> Extracted verbatim from `SKILL.md` for progressive disclosure. Relative paths (`references/...`, `scripts/...`) resolve from the skill root directory.

## Troubleshooting

- **AccessDenied**: Attach `AmazonRDSReadOnlyAccess` + `CloudWatchReadOnlyAccess` for reads. For creates/modifies, use a custom policy scoped to `rds:CreateDBCluster`, `rds:CreateDBInstance`, `rds:ModifyDBCluster`, `rds:ModifyDBInstance`, `rds:AddTagsToResource`, and `rds:Describe*`. See [Identity and access management for Amazon Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/UsingWithRDS.IAM.html).
- **ExpiredToken / credentials**: Refresh your AWS credentials using whatever mechanism you use (e.g. re-run your SSO/`aws sso login`, assume-role, or refresh the profile), then retry. Do not assume a specific credential tool.
- **DBClusterNotFoundFault**: Verify region and cluster ID.
- **Throttling**: Retry once, then narrow scope.

## Additional Resources

- [Aurora User Guide](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/)
- [Aurora pricing](https://aws.amazon.com/rds/aurora/pricing/)
- [Aurora serverless](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html)
- [Aurora PostgreSQL upgrades](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/USER_UpgradeDBInstance.PostgreSQL.html)

## Handoff from aws-database-selection

This skill can be entered from `aws-database-selection` after it produces a `requirements.json`. When you see a path matching `aws_dbs_requirements/*/requirements.json` in conversation:

1. Read the artifact. Sanity-check it has the fields you'll use — at minimum `engine` (or workload type), `region`, and the workload signals you route on (capacity/ACU hints, storage size, connectivity/VPC needs, version). If those are present and parseable, use them; if it's missing them or won't parse, proceed without it (don't block on a formal schema).
2. Acknowledge relevant facts in 1-2 bold sentences.
3. Scope-check: if the artifact doesn't match Aurora (e.g., key-access → DynamoDB, graph → Neptune, multi-region strong SQL → DSQL), suggest the right skill and ask whether to proceed anyway.
4. Continue with this skill's sub-skill routing.
