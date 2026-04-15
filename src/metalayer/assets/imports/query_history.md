# Import: Query Memory

Read existing query files from utils/queries/ and generate data model objects for things that appear repeatedly but are not yet modeled.

## What to read

All .md files in utils/queries/. Parse frontmatter for objects_in_data_model, objects_not_in_data_model, the SQL body, and accepted status.

Focus on objects_not_in_data_model across multiple queries — these are the gaps.

## What to generate

- New fields for raw columns appearing in 3+ queries' objects_not_in_data_model lists.
- New views for raw tables appearing in 3+ queries' objects_not_in_data_model lists.
- New relations for repeated join patterns not yet captured.
- New lore from patterns observed in accepted queries (common filters, business logic, naming conventions).

## Priority

Weight accepted queries more heavily than unaccepted ones. Require 2+ accepted queries or 5+ total queries before proposing a new object. This prevents modeling one-off ad hoc columns that will never be queried again.

## Gotchas

- A column in objects_not_in_data_model may already exist under a different name — check before creating duplicates.
- Some queries reference temporary CTEs or derived columns that should not become fields.
- Accepted queries represent validated business logic; prefer their patterns over unaccepted ones when there is a conflict.
