# Propose Checklist

Read this BEFORE drafting any vault change proposal. Answer each question for every proposed file.

## 1. Is this a column or a prose note?

- **Column with queryable properties** (SQL expression, enumerated values, aggregation, filters, join key) → create a **field file**. Not a body note, not lore. If the agent needs this to write correct SQL, it's a field.
- **Prose context about behavior** (e.g., "messages don't always alternate", "this table refreshes daily") → put it in the **body of the relevant view or field file**.
- **Cross-cutting rule spanning multiple objects** (e.g., "always exclude internal workspaces", "joins must include data_region") → create a **lore file**.
- **Join between two views** → create a **relation file**, not lore.

The most common mistake: putting column information in the view body instead of creating a field file. If you learned that a column has specific values, specific SQL, or specific aggregation logic, that's a field.

## 2. What type? Create freely or hold back?

**Create freely** — these are the building blocks. Every query teaches you about them. Don't hesitate:

- A table or data source → **view**
- A column on a view (with SQL, values, aggregation, or kind) → **field**
- A join between two views → **relation**
- A cross-cutting rule spanning multiple objects → **lore**
- A data connection → **source**

**Hold back** — these require human judgment about business domains. Flag candidates but don't create without user direction:

- A business entity grouping fields → **concept**
- An analytical domain grouping concepts → **topic**

## 3. Is this structural or temporal?

The vault stores **structure** — what exists, how it connects, what it means. Never store **temporal data** that changes over time:

- **Store**: "revenue is SUM(amount) WHERE status = 'completed'" (structural — the definition)
- **Don't store**: "revenue was $2.3M last quarter" (temporal — will be stale tomorrow)
- **Store**: "this table refreshes daily at 6am UTC" (structural — the schedule)
- **Don't store**: "the latest refresh was 2024-03-15" (temporal — stale immediately)
- **Store**: "exclude internal workspaces from customer metrics" (structural — a rule)
- **Don't store**: "we had 500 logins last week" (temporal — a data point)
- **Store**: "high_cardinality" for a dimension with many values (structural — the characteristic)
- **Don't store**: "there are currently 47,000 distinct customers" (temporal — a count)

If the information would be wrong next week, it doesn't belong in the vault. Query results, benchmarks, row counts, totals, percentages, "current" values, and time-specific facts are all temporal. Let the agent query for those fresh each time.

Common mistake: putting row counts or data quality percentages in view body text (e.g., "1,253 rows", "~7% have null workspace_id", "~5% contain artifacts"). These are verification results you used to confirm structure — they belong in your verification notes, not in the vault file. The vault should say *what* to watch for ("some rows have null workspace_id", "SCHEDULE_CHANNEL contains injection artifacts — filter to EMAIL/SLACK"), not *how many*.

## 4. Dependencies resolved?

- Does this file reference any [[wikilinks]]?
- Does every referenced object exist in the vault?
- If not, are you creating the missing objects in the same batch?
- Dependency order: sources → views → fields → relations → lore

## 4. Verified against real data?

- Have you run a query to confirm every claim in this file?
- Grain, primary key, cardinality, column values, join behavior, metric output?
- If not, do not propose. Run the verification query first.

## 5. Source set?

- If this is a view, does it have `source: [[source_name]]`?
- Does that source file exist?
