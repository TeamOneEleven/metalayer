# Import: Warehouse Query History

Read recent query history from the warehouse and generate context files.

## What to read

Query QUERY_HISTORY from Snowflake INFORMATION_SCHEMA or ACCOUNT_USAGE. Focus on successful SELECTs from the last 90 days. Exclude system queries, admin queries, and DDL. Sample up to 500 queries.

## What to extract

- Tables referenced in FROM and JOIN clauses.
- Columns referenced in SELECT, WHERE, GROUP BY, and ON clauses.
- Join conditions (table pairs, join keys, join types).
- Aggregation functions applied to columns.
- Common filter patterns (WHERE clauses that repeat across queries).

## What to generate

### Views

One per table appearing in 3+ queries. Set source, table, one_row_means, primary_key. Skip tables appearing in fewer than 3 queries unless they are clearly important (e.g., a core fact or dimension table referenced in key joins).

### Fields

One per column appearing in 5+ queries. Infer kind from usage:
- SUM or AVG applied to it -> metric
- GROUP BY -> dimension
- date_trunc or date filter -> time
- ON clause (join key) -> identifier

Set sql and agg. Pick the most common aggregation when a column is used multiple ways.

### Relations

One per join pattern appearing in 3+ queries. Extract from/to tables, infer cardinality from the data, set join_type.

### Lore

Capture repeated patterns as lore entries:
- "Always filter out test data" patterns (e.g., WHERE NOT is_test).
- Common join chains that represent standard query paths.
- SQL dialect notes (Snowflake-specific functions, casting patterns).

## Gotchas

- Weight frequent patterns more heavily than rare ones.
- When a column is aggregated multiple ways, pick the most common aggregation.
- Skip staging tables, tmp tables, and system tables.
- Query history may contain incomplete SQL — skip unparseable queries rather than guessing.
