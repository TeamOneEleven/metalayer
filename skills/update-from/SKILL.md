# Update From

General import workflow for bringing external schema, model, or metadata into the vault.

## Step 1: Load Preset

Load the import preset from `utils/imports/{source}.md`. The source name comes from the user (e.g., "update from snowflake", "update from dbt", "update from lookml").

The preset file contains:

- How to connect to the source (MCP server, CLI command, file path).
- What to extract (tables, columns, descriptions, joins, tests, tags).
- Source-specific mapping rules (e.g., dbt model -> view, dbt dimension -> field).
- Any custom instructions.

Also apply any `--instructions` the user passed alongside the command.

## Step 2: Access the Source

Call the appropriate MCP tool, CLI command, or read the source files as specified by the preset. Collect:

- Tables/models with their columns, types, and descriptions.
- Relationships/joins with keys and cardinality.
- Business logic (calculated fields, filters, tests).
- Documentation and descriptions.

## Step 3: Verify Against Real Data

Before drafting any vault files, verify every claim against the actual data. Source metadata (column names, schema definitions, model configs) is a starting point, not ground truth. Do not trust it without checking.

Resolve the source file for the views being imported (e.g., `source: [[snowflake]]` → read `snowflake.md`). Use the tool described in the source file to run verification queries. If no source file exists, stop and ask the user to create one first (see the setup skill, Step 2).

For each table/model discovered, run queries to confirm:

- What one row actually represents (grain).
- Whether the assumed primary key is actually unique.
- What columns actually contain (types, distributions, null rates).
- Whether joins produce the expected cardinality (check for fanout and orphaned rows).
- Whether metric expressions produce reasonable numbers.
- Whether filter conditions and value lists match reality.

This is not optional. Every property you write into a context file must be backed by a query result. If you cannot run queries (no warehouse connection), do not write context files — tell the user you need warehouse access to verify. The only exception is if the user explicitly says to proceed unverified, in which case mark every claim with `# UNVERIFIED` in the body text.

## Step 4: Draft Vault Files

For each entity found in the source, check if a corresponding vault file already exists.

- **Exists**: compare the source data against the vault file. Note differences.
- **New**: draft a new .md file per the writing-context skill.

What to generate:

- **Views**: one per table/model. Include table, source, primary_key, one_row_means (verified in Step 3, not inferred).
- **Fields**: one per important column. Skip trivial columns (created_at, updated_at, id) unless they have business logic or descriptions. Include SQL, kind, agg (for metrics).
- **Relations**: one per foreign key or explicit join. Include from, to, cardinality, label. **Also create the field files for the from/to keys if they don't exist yet** — a relation must not reference fields that aren't in the vault.
- **Lore**: one per non-obvious business rule found in the source (e.g., "this table excludes deleted records", "revenue is net of refunds"). Only create lore for rules that span multiple objects — put single-object rules in that file's body.

**No dangling references.** Every `[[wikilink]]` in your proposed files must resolve. If a relation references `[[orders.customer_id]]`, then `orders.customer_id.md` must exist or be included in the same batch. See the writing-context skill — No Dangling References.

What NOT to generate:

- **Concepts and topics**: these require human understanding of the business domain. Flag candidates but don't create them.
- **Lore for obvious things**: "this is the orders table" is not lore.
- **Fields for every column**: skip boilerplate columns with no business meaning. Focus on columns that answer questions.

## Step 5: Present to User

Show the proposed changes in a batch, ordered by dependency (sources → views → fields → relations → lore):

1. Views (new and modified)
2. Fields (new and modified)
3. Relations (new and modified)
4. Lore (new and modified)

**Before drafting, read the propose-checklist skill for every proposed file.** Check: does it belong in an existing file's body? Are all dependencies resolved? Is every claim verified?

For each file, show the full proposed content. For modified files, highlight what changed.

## Step 6: Write Approved Changes

For each change the user approves:

1. Run context_audit(change) as a preflight check.
2. If preflight passes, call write_context().
3. If preflight flags issues, report them and ask the user how to proceed.

After all approved changes are written, call sync_context() once to re-index.

## Conflict Resolution

Never silently overwrite existing vault content. Handle conflicts explicitly:

- **Different SQL**: source says `SUM(amount)`, vault says `SUM(amount - discount)`. Show both versions, explain the difference, let the user pick.
- **Additional columns**: source has columns not in the vault. Propose new field files for important ones.
- **Cardinality disagreement**: source says one_to_many, vault says many_to_many. Flag it, show evidence from both sides, don't auto-change.
- **Aggregation disagreement**: source says AVG, vault says SUM. Flag it, don't auto-change.
- **Description changes**: source has a new or different description. Show both, suggest merging if they're complementary.

When in doubt, preserve the vault version and flag the discrepancy. The vault represents human-verified understanding; the source represents raw metadata.
