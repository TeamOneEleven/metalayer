# Setup

Initialization workflow for a new Metalayer vault. Run this when starting from scratch or verifying an existing installation.

## Step 1: Verify Structure

Check that the required directory structure and files exist:

- `context/` — vault root for .md files (views, fields, relations, lore, concepts, topics).
- `utils/` — utilities directory.
- `utils/queries/` — query memory directory.
- `utils/imports/` — import preset directory.
- `config.yaml` — project configuration.
- `skills/` — this directory (skill files).

If any are missing, create them.

## Step 2: Create Source Files

**This step is required before any import or context writing.** Sources are vault files (type: source) that tell the agent how to access data for verification and query execution.

Check if any source files exist in `context/`. If not, create one:

1. Check what tools are available in your environment — MCP servers (Snowflake, Postgres, BigQuery, dbt), CLI tools (snow, psql, bq), or other data access methods.
2. For each available data connection, create a source file per the writing-context skill. Example:

```markdown
---
type: source
tool: "snow sql -q \"${SQL}\" -c my_connection"
---

# Snowflake

Uses the Snowflake CLI with the `my_connection` profile.
```

3. Test each source by running a simple query (e.g., `SELECT 1`) using the tool command to confirm it works.

**Do not proceed to import until at least one source file exists and is tested.** Every view must reference a source with `source: [[source_name]]`, and every claim in a context file must be verified against real data using that source.

## Step 3: Discover What to Import

With a working source configured, explore what's available:

- **List schemas/tables**: use the source to see what data exists.
- **Check query history**: if available, see which tables analysts actually use most.
- **Check for existing models**: dbt models, LookML, or other semantic layer definitions.

Report what you find. Recommend starting with the 3-5 most important tables.

## Step 4: Guide First Import

Walk the user through the first import using the update-from skill:

1. Confirm which tables/models to import.
2. **Verify each one against real data** using the configured source (see the writing-context skill — Verify Before Writing). Run queries to confirm grains, keys, cardinality, column values.
3. Draft context files based on verified data.
4. Present proposed files for approval.

Focus on the most important tables first. Don't try to import everything at once.

## Step 5: Validate After Import

After the first import is written:

1. Run static validation (duplicate filenames, dangling refs, circular extends, missing type).
2. Run semantic validation per the context-audit skill.
3. Report results clearly: what passed, what needs attention.
4. Suggest next steps:
   - Import more tables.
   - Add lore for business rules not captured in the source.
   - Create a topic for the imported domain.
   - Try an ask_data query to test the vault.

## No Sources Available

If no data connections are available:

1. Explain that Metalayer requires at least one source to verify data. Without a source, context files would contain unverified claims.
2. Help the user set up a connection (install an MCP server, configure a CLI tool, etc.).
3. If they explicitly want to proceed without verification, they can create files manually — but every property must be marked `# UNVERIFIED` in the body text.
