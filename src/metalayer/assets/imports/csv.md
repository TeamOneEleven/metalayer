# Import: CSV Files

Read CSV files specified by the user. Infer structure and generate a starting data model.

## What to read

Read headers and sample approximately 100 rows. Use the sample to infer column types, cardinality, value distributions, and null rates.

## Mapping

- CSV file -> view (source: csv). Use the filename (minus extension) as the view name.
- Each column -> field. Infer kind from the data:
  - Numeric column with many unique values -> metric. Set agg to sum, or avg if the values look like rates/percentages/averages.
  - String column with few unique values (< ~50 distinct in sample) -> dimension. Include a values list in the field description.
  - Date or timestamp column -> time.
  - Column named like an ID (*_id, id, key) or with all unique values -> identifier.
  - String column with many unique values (names, descriptions) -> dimension, but note it may be unsuitable for grouping.

## Gotchas

- Mixed types in a column (e.g., numbers and strings) need manual review. Default to dimension.
- Large CSVs (100k+ rows) may need to be loaded into the warehouse first. Note this in the generated view.
- Headers may have spaces, special characters, or inconsistent casing. Normalize to snake_case for field names and preserve the original as the sql reference.
- CSV imports are a starting point. The generated model will need refinement — flag low-confidence inferences explicitly.
- Check for a header row. If the first row looks like data (not headers), flag it.
