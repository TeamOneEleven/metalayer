# Import: Snowflake Semantic Views

Read Snowflake native semantic layer definitions via the Snowflake MCP.

## What to read

Use the Snowflake MCP to list semantic models and their contents: dimensions, measures, time dimensions, and relationships. Also check INFORMATION_SCHEMA for supplementary table structure (column types, primary keys, foreign keys) that the semantic layer may not fully describe.

## Mapping

- Semantic model -> view. Use the underlying table as source.
- Dimension -> field (kind: dimension).
- Measure -> field (kind: metric). Translate the aggregation expression into sql and agg.
- Time dimension -> field (kind: time).
- Relationship between semantic models -> relation. Set from/to, cardinality, and join_type.

## Gotchas

- Some Snowflake aggregation types (e.g., MEDIAN, PERCENTILE_CONT) may not map cleanly to standard Metalayer agg values. Flag these for manual review.
- Filter syntax in Snowflake semantic views uses a different expression language than raw SQL — translate or note the difference.
- A semantic model may reference views or CTEs rather than base tables. Trace back to the underlying table when possible.
- INFORMATION_SCHEMA supplements but does not override the semantic layer definitions. Use it to fill gaps (e.g., missing column types), not to contradict explicit semantic definitions.
