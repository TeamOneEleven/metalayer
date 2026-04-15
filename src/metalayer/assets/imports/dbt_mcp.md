# Import: dbt Models via MCP

Read dbt models, metrics, sources, and relationships via the dbt MCP server.

## What to read

Use the dbt MCP to list all models. For each model, retrieve columns, descriptions, tests, tags, and refs. Also retrieve metrics, sources, and relationship definitions.

## Mapping

- dbt model -> view. Use the model's materialized table/view as the source. Pull description into the view's one_row_means or description.
- dbt metric -> field (kind: metric). Translate the metric's expression into sql and agg.
- Described column -> field. Infer kind from the column's type, tests, and usage:
  - Numeric columns with aggregation tests or metric references -> metric
  - Date/timestamp columns -> time
  - ID columns appearing in relationship tests -> identifier
  - Everything else -> dimension
- Time column (especially those with freshness checks or partitioning) -> field (kind: time).
- ref() between models -> relation. Set from/to and infer cardinality from relationship tests.

## Gotchas

- Skip staging models (stg_*) — they are intermediate and not meant for direct querying.
- Translate Jinja ({{ ref('...') }}, {{ source('...', '...') }}) into plain SQL table references.
- Some ref() calls are just dependency ordering for dbt's DAG, not actual join relationships. Only create a relation when there is a real foreign key or join condition.
- dbt descriptions may contain markdown — strip formatting when pulling into Metalayer fields.
