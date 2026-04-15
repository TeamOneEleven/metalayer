# Reflection

Post-execution quality checks. Run these after every execute_sql call.

## Plausibility Checks

Check each of these against the result set. If any check fails, flag it.

- **Row count**: 0 rows usually means a filter is too restrictive or a join key doesn't match. Millions of rows usually means a fanout from a bad join. Both require investigation before presenting.
- **Value ranges**: revenue and monetary values should be positive (negative only if refunds/credits are expected). Percentages should be 0-1 or 0-100 consistently — check which convention the field uses. Counts should be non-negative.
- **Date bounds**: all dates should fall within a reasonable range. No future dates unless the question asks for forecasts. No dates before the business existed.
- **Grain**: the result grain must match the question. If the user asked for monthly totals, each row should represent one month. If daily, one row per day. Duplicated grain rows indicate a join fanout.
- **Magnitude vs past queries**: search query memory for similar past queries. If the new result is 10x or more different from a past result for a comparable time period, something is wrong. Flag and investigate.
- **Null counts**: high null rates in key columns suggest a join issue or missing data. Report null rates if above 10%.

If any check fails, adjust the query and re-execute. You may re-execute up to 2 times. After 2 retries, present the best result with caveats.

## Validation Rules

Check for `validation` fields on both **lore files** and **field files** that were used in this query. These are domain-specific rules that catch errors generic checks miss.

1. **Field-level validation**: for every field used in the query, check its frontmatter for a `validation` key. Example: a revenue field with `validation: "should always be positive"` — check the revenue column in the result set.
2. **Lore-level validation**: for every lore file triggered by the views/fields in this query, check for a `validation` key. Example: lore with `validation: "login counts should exclude internal workspaces"` — check the WHERE clause.

If any validation rule is violated, flag it prominently before presenting results. This is a stronger signal than a generic plausibility check — someone wrote this rule because they knew this specific mistake happens.

## Scratchpad

Maintain a scratchpad throughout the entire ask_data flow. Accumulate notes about:

- **Raw columns used (not_in_data_model)**: columns or tables that sub-agents referenced but have no vault file. Track which agents used them and whether the results were correct.
- **Guessed joins**: joins that agents constructed without a relation file. Track whether the join produced correct results.
- **Contradictions**: cases where lore said one thing but the data showed another. Cases where two vault files disagree.
- **Missing context**: questions the user asked that the vault had no information about. Fields that should exist but don't.

## When to Propose Changes

**Always propose changes when any of these are true** — this is not optional:

- You joined two tables and no relation file exists for that join. Propose one.
- You used a column that has no field file and it was important to the answer. Propose one.
- You queried a table that has no view file. Propose one.
- You applied a business rule (filter, aggregation logic, etc.) that isn't captured in any vault file. Propose lore or a field-level note.
- Anything appeared in not_in_data_model from the consensus output. Each item is a gap in the vault.

The threshold for proposing is low: if the query needed it and it worked, it belongs in the vault. The user can always reject proposals.

Do NOT propose a change when:

- The query results are suspicious or unverified.
- The user gave negative feedback on the query (fix the query first, then learn).

## How to Propose

**Before drafting any proposal, read the propose-checklist skill and answer every question.** This is the most common source of mistakes — the checklist catches them.

After presenting the query results, batch all proposals together. For each:

1. Run the propose checklist. In particular: does this belong in an existing file's body, or is it a new file?
2. Run verification queries to confirm every claim (see the writing-context skill — Verify Before Writing).
3. Resolve all dependencies — if your file references [[objects]] that don't exist, create them in the same batch.
4. Show the proposed .md file content, formatted per the writing-context skill.
5. Explain what you verified and why this change helps future queries.
6. Ask for approval.

Never write vault files without explicit user approval. Never interrupt the answer to propose — always batch proposals at the end.
