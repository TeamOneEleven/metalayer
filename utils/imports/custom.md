# Import: Custom Source

Blank template for user-defined imports. The user provides --instructions describing what source to read, how to access it, and what to look for.

## Approach

Follow the user's --instructions alongside the general update_from workflow:

1. Access the source using whatever method the instructions specify (API, file system, database, MCP server, etc.).
2. Identify entities that map to Metalayer types:
   - Datasets, tables, models -> views
   - Columns, attributes, properties -> fields
   - Foreign keys, joins, references -> relations
   - Business rules, conventions, caveats -> lore
3. Draft .md files following Metalayer conventions.
4. Present the draft for approval before writing.

## When instructions are ambiguous

- Ask for clarification rather than guessing.
- If the source has a schema or catalog, read that first to orient.
- Start with the most-referenced or most-central entities and work outward.
- Default to conservative mappings: only create objects you are confident about, flag uncertain ones for review.
