# Import: LookML Files

Scan for *.lkml files on the filesystem. Parse view definitions, explore definitions, and model definitions.

## What to read

- View files: sql_table_name, derived_table SQL, dimensions, measures, dimension_groups, sets, parameters.
- Explore files: joins (sql_on, type, relationship), always_filter, access_filter, conditionally_filter.
- Model files: connection, includes, datagroups.

## Mapping

- LookML view -> view. Use sql_table_name as source. If derived_table, use the SQL as the view's sql definition.
- dimension -> field (kind: dimension). Set sql from the dimension's sql parameter.
- measure -> field (kind: metric). Set sql and agg from the measure's type (count, sum, average, etc.).
- dimension_group type: time -> field (kind: time). Use the dimension_group's sql as the base time expression.
- dimension_group type: duration -> generate start/end time fields.
- explore join -> relation. Map relationship (many_to_one, one_to_many, etc.) to cardinality. Translate sql_on to the join condition.

## Syntax translation

- `${TABLE}.column_name` stays as-is (it refers to the current view's table).
- `${view_name.field_name}` translates to `${[[view_name.field_name]]}` in Metalayer syntax.
- Liquid templating (`{% if %}`, `{% else %}`) cannot be directly translated. Flag any field using Liquid for manual review and include the original LookML as a comment.

## Gotchas

- Apply LookML refinements (files with `+:` syntax) before importing — the refined version is the canonical one.
- LookML extends create inheritance chains. Resolve extends fully before generating fields.
- `always_filter` on an explore should become lore ("this explore always requires a filter on X").
- Hidden dimensions/measures (hidden: yes) may still be important for joins or other fields. Import them but mark as hidden.
- Sets define reusable field groups — do not import sets as standalone objects, but use them to understand field organization.
