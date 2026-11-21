---
name: dms-schema-conversion
description: "Handles the full DMS Schema Conversion lifecycle including creating migration projects, converting database schemas to a target engine, running compatibility assessments, navigating metadata trees, exporting converted DDL to S3, applying schema changes to a target database, and converting SQL statements between database engines. Applies when migrating database schemas between heterogeneous engines using AWS DMS Schema Conversion. Query live AWS state via MCP tools only (never raw aws CLI)."
version: 3
---

# DMS Schema Conversion

> **MCP-Only Live AWS Execution:** Perform ALL live AWS API discovery, account/region checks (`sts:GetCallerIdentity`), cluster/instance/table inspection, CloudWatch telemetry, pricing (`awspricing`), and docs (`awsknowledge`) strictly via connected MCP tools (`aws-mcp` `aws___run_script` `call_boto3`, `dynamodb`, `elasticache`, `postgres`, `mysql`, `cloudwatch`, `awspricing`, `awsknowledge`) — **never invoke raw `aws ...` CLI commands (such as `aws --version` or `aws sts get-caller-identity`) in shell (`run_command`)**. Local offline helper scripts under `scripts/` may be run via `python3` or `node`.

## Overview

This skill handles the full DMS Schema Conversion lifecycle — from first-time setup to running conversions on an existing project.

> The AWS MCP server is recommended for streamlined execution, audit logging, and observability. When the MCP server is not available, all operations can be performed via AWS CLI directly.

**Key documentation:**

- [Selection rules in DMS Schema Conversion](https://docs.aws.amazon.com/dms/latest/userguide/sc-selection-rules.html) — scoping operations to specific objects
- [Transformation rules in DMS Schema Conversion](https://docs.aws.amazon.com/dms/latest/userguide/sc-transformation-rules.html) — renaming schemas, tables, columns during conversion

**Global constraint:** You MUST fetch and read any linked documentation before acting on it — do NOT rely on memory for any referenced material (selection rules, transformation rules, troubleshooting guides, network configuration, etc.). Documentation contains vendor-specific details that change between engines and API versions.

---

## Guardrail — where this skill's own files live (MCP vs local install)

This skill can be loaded two ways, and they resolve the skill's own bundled files from different places. Determine how the skill was loaded before reading a reference:

- **Loaded through the AWS MCP `retrieve_skill` tool:** The skill is not installed on the local filesystem. You MUST fetch each reference via `retrieve_skill` with the `file` parameter (e.g. `file="references/setup-wizard.md"`). Do NOT `file_read` these paths locally — they do not exist on disk.
- **Installed locally** (e.g. `.kiro/skills/dms-schema-conversion/` or `~/.claude/skills/dms-schema-conversion/`): Read files from the local skill directory using relative paths.

This distinction applies only to the skill's own packaged files. User data and session artifacts are always read from and written to the user's working directory. Never fetch or write customer data through `retrieve_skill`.

---

## Verify Dependencies

Before starting, check that AWS CLI commands can be executed.

**Constraints:**

- You MUST verify that AWS CLI commands can be run (via MCP server tools or directly via shell)
- You MUST inform the customer if no execution method is available and ask whether to proceed
- You MUST ask the customer which AWS region to use — do NOT attempt to infer it from the STS response (it does not contain a region field). If the customer is unsure, suggest checking the `AWS_DEFAULT_REGION` environment variable or the `--region` flag they are using.

---

## Project Selection

Check for existing migration projects:

```
aws dms describe-migration-projects
```

- **If exactly one project exists** → ask the customer: "Found migration project `<name>`. Would you like to use it, or create a new one?" If they confirm, store `migration_project_identifier` and proceed to [Actions Menu](#actions-menu). If they want a new one, run the setup wizard.
- **If multiple projects exist** → list them and ask the customer to pick one, or offer to create a new project. Store `migration_project_identifier`, proceed to [Actions Menu](#actions-menu).
- **If no projects exist** → ask: "No migration projects found. Would you like to create one?" If yes, load [setup-wizard.md](references/setup-wizard.md) and run the full setup wizard from Phase 1. After wizard completes, run [Auto Import](#auto-import), then proceed to [Actions Menu](#actions-menu).

---

## Auto Import

> This section runs only after the setup wizard creates a new project. Do NOT run for existing projects.

1. Build selection rules to import **all schemas** from the source server. For `server-name`, use the data provider identifier (the short ID from the ARN, e.g., `JIFET2LUZJEJZPDYSOSGANOA2M`) or the literal `ServerName` value from the data provider settings (e.g., `"offline"` for offline sources). For SQL Server, you MUST include `database-name` in the object locator. See [Selection rules in DMS Schema Conversion](https://docs.aws.amazon.com/dms/latest/userguide/sc-selection-rules.html) for JSON format.

2. Run `start-metadata-model-import` with `--origin SOURCE --refresh` and the selection rules from step 1. Extract `RequestIdentifier` from the response.

3. Wait for import completion using the DMS waiter:

   ```
   aws dms wait metadata-model-imported \
     --migration-project-identifier <migration_project_identifier> \
     --filter 'Name=schema-conversion-operation-id,Values=<RequestIdentifier>'
   ```

   If the waiter fails or is unavailable, fall back to polling `describe-metadata-model-imports` every 30 seconds with `--filter Name=request-id,Values=<RequestIdentifier>`. Terminal statuses: **SUCCESS** (proceed) or **FAILED** (check error via the `Error` field in the response).

4. **Show discovered schemas:** On success, call `describe-metadata-model-children` with `--origin SOURCE` at the root level to list the imported schemas/databases. Present the discovered names to the customer so they can confirm the correct database connection was established:
   > "Import complete. I found the following schemas/databases: `<list>`. Does this look correct?"

5. Proceed to [Actions Menu](#actions-menu).

---

## Actions Menu

Present the actions menu using a structured selection tool (e.g., `AskUserQuestion`) if available — this gives the customer a clickable/selectable list.

**For SQL Server → PostgreSQL/Aurora PostgreSQL projects** (present as a single-select question "What would you like to do?"):

1. **Convert database** — convert schema objects to the target engine (also produces an conversion assessment report)
2. **Assess database** — run a compatibility assessment (also produces an conversion assessment report)
3. **Convert statement** — convert a single SQL statement
4. **Clean up** — delete migration project and related DMS resources

**For all other engine combinations** (present as a single-select question "What would you like to do?"):

1. **Convert database** — convert schema objects to the target engine (also produces an conversion assessment report)
2. **Assess database** — run a compatibility assessment (also produces an conversion assessment report)
3. **Work with tree** — browse the metadata model tree
4. **Clean up** — delete migration project and related DMS resources

The customer can always type a custom request via "Other" (e.g., "work with tree", "show database statistics", or "exit"). If the customer selects "Other" and describes an action covered by this skill, handle it accordingly.

After each action completes, return to this menu by presenting the same selection again.

> **Note on metadata loading:** `start-metadata-model-import` (with `Refresh=false`), `start-metadata-model-assessment`, and `start-metadata-model-conversion` all load the source tree for the scoped objects. If metadata was already imported in the current session for a given subtree, it does not need to be re-imported — these operations will work with what is already loaded.

---

### Convert Database

1. **Ask what to convert:** Ask the customer what they want to convert (e.g., "all schemas", "schema public", "tables starting with PROD_").

2. **Build selection rules:** Translate the customer's natural language to selection rules JSON. Refer to [Selection rules in DMS Schema Conversion](https://docs.aws.amazon.com/dms/latest/userguide/sc-selection-rules.html) for format, wildcards, and vendor-specific locators.

3. **Run conversion:** Call `start-metadata-model-conversion` with the migration project and selection rules. Extract `RequestIdentifier` from the response.

4. **Wait for completion:** Wait using the DMS waiter:

   ```
   aws dms wait metadata-model-converted \
     --migration-project-identifier <migration_project_identifier> \
     --filter 'Name=schema-conversion-operation-id,Values=<RequestIdentifier>'
   ```

   If the waiter fails or is unavailable, fall back to polling `describe-metadata-model-conversions` every 30 seconds with `--filter Name=request-id,Values=<RequestIdentifier>`. Terminal statuses: **SUCCESS** (proceed) or **FAILED** (check error).

5. **Export conversion assessment report:** On conversion success, call `export-metadata-model-assessment` with selection rules using `rule-action: "explicit"` (this API requires explicit rules, not `include`). Provide the customer with S3 links for both PDF and CSV reports (`PdfReport.S3ObjectKey` and `CsvReport.S3ObjectKey`).

6. **Show summary:** Download the Summary CSV from S3 using `aws s3 cp s3://<bucket>/<CsvReport.S3ObjectKey> ./Summary.csv`. Present its contents to the customer — show the number of objects per category, how many converted automatically, and how many have Action Items at each complexity level.

7. **Post-convert sub-menu:** After showing the summary, present options. Only show "Apply to target" if the target is a live target (not virtual):
   > "What would you like to do next?
   > 1. **Fix Action Items** — review and fix Action Items from the conversion assessment report
   > 2. **Export as script** — export converted DDL as SQL script to S3
   > 3. **Apply to target** — apply converted objects to the target database *(live targets only)*
   > 4. **Back** — return to actions menu"

   - **Fix Action Items:** Load [action-items.md](references/action-items.md) and follow the fixing workflow there.
   - **Export as script:** Run `aws dms start-metadata-model-export-as-script --migration-project-identifier <migration_project_identifier> --origin TARGET --selection-rules '<json>'`. Extract `RequestIdentifier`. Wait via `aws dms wait metadata-model-exported-as-script --migration-project-identifier <id> --filter 'Name=schema-conversion-operation-id,Values=<RequestIdentifier>'`. Provide the S3 link on completion.
   - **Apply to target:** Run `aws dms start-metadata-model-export-to-target --migration-project-identifier <migration_project_identifier> --selection-rules '<json>'`. Optionally pass `--overwrite-extension-pack` if the customer confirms. Extract `RequestIdentifier`. Wait via `aws dms wait metadata-model-exported-to-target --migration-project-identifier <id> --filter 'Name=schema-conversion-operation-id,Values=<RequestIdentifier>'`. Inform the customer on completion.
   - **Back:** Return to [Actions Menu](#actions-menu).

After completing schema export or target application, ask the customer what they'd like to do next — and if they are ready to migrate table data (Full Load, CDC, or Full Load + CDC), load the **`dms-data-migration-execution`** skill to size the DMS Replication Instance, profile source LOB distributions, and configure the migration task.

---

## Extended Reference & Troubleshooting

For the complete verbatim continuation of this guide — including detailed workflows, troubleshooting matrices, security checklists, and resource catalogs — read [`references/dms-sc-actions-and-cleanup.md`](references/dms-sc-actions-and-cleanup.md).
