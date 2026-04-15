# SQL Consensus

5-sub-agent SQL generation protocol. Do not skip this — every data question goes through consensus.

## Step 1: Context Assembly

Assemble all vault files gathered during navigation into a single clean context block. Include:

- View table names (the `table` frontmatter value for each view).
- Field SQL expressions, aggregation types, filters, kind.
- Relation join keys (from/to), cardinality, join type.
- All relevant lore (always-lore and triggered lore).
- ${TABLE} substitution rule: in field SQL, ${TABLE} refers to the current view's table.
- ${[[ref]]} substitution rule: references to other fields resolve to their SQL expression.

Do NOT include raw search results, navigation metadata, similarity scores, or any intermediate artifacts. The context block must be self-contained — a reader with no vault access should be able to write the query from it alone.

## Step 2: Sub-Agent Prompt

Spawn 5 sub-agents. Each receives an identical prompt containing:

1. The assembled context block from Step 1.
2. The user's question, verbatim.
3. These rules:
   - Use ONLY tables and columns described in the context. If a needed column is not described, list it under not_in_data_model.
   - Apply ${TABLE} substitutions in field SQL before using.
   - Resolve ${[[ref]]} references by inlining the referenced field's SQL.
   - Respect restricted_columns — never SELECT or filter on them unless the question explicitly requires it and lore permits it.
   - Apply default metric filters (from field `filters` frontmatter) whenever using that metric.
   - Fully qualify all column references (schema.table.column or alias.column).
   - Use LEFT JOIN unless the relation specifies a different join_type.

Each sub-agent returns:

- **sql**: the complete executable SQL.
- **in_data_model**: list of [[refs]] to vault files used.
- **not_in_data_model**: list of raw column or table names used that have no vault file.

## Step 3: Compare

Check all 5 SQL outputs for semantic equivalence. Ignore whitespace, alias naming, and column ordering differences. Two queries are semantically equivalent if they use the same tables, same joins, same aggregation logic, same filters, and same grouping.

If all 5 (or nearly all) agree: done. Take the cleanest version and proceed to output.

If they disagree: go to Step 4.

## Step 4: Diagnose Disagreement

Do NOT vote, pick a winner, or average the results. Instead, figure out WHY they disagree. Common causes:

- **Ambiguous question.** The user's question can be interpreted multiple ways (e.g., "revenue" could mean gross or net). The sub-agents made different assumptions.
- **Missing context.** The vault doesn't have enough information to answer definitively (e.g., no relation defined between two views, so agents guessed different join paths).
- **Conflicting context.** Two vault files give contradictory guidance (e.g., lore says one thing, a field definition says another).
- **Grain confusion.** Agents disagree on deduplication, grouping, or which table drives the grain.

For each disagreement, identify:
1. What specifically differs between the SQL outputs.
2. What assumption each variant is making.
3. Whether the vault context is sufficient to resolve it, or whether the user needs to clarify.

## Step 5: Resolve and Retry

Based on the diagnosis:

- **If the user needs to clarify**: ask them. Explain the ambiguity concisely — "Some agents interpreted 'revenue' as gross, others as net. Which do you mean?" Once they answer, incorporate their answer into the context block and go back to Step 2.

- **If the context is missing or conflicting**: refine the context block. Fetch additional vault files (get_context calls), resolve the conflict, add clarifying notes to the context block, and go back to Step 2.

- **If the grain is ambiguous**: check the view's `one_row_means` and `dedup_key` fields. Add explicit grain instructions to the context block and go back to Step 2.

Each retry is a full 5-agent quorum with the refined context — not a partial fix or a vote on the old results.

## Step 3–5 Loop

Maximum 3 full quorum rounds. Track what changed between rounds:

- Round 1: initial context.
- Round 2: refined context based on diagnosis (and/or user clarification).
- Round 3: further refined context.

If after 3 rounds the agents still produce meaningfully different SQL, stop. Do not guess. Tell the user:

> "I wasn't able to get a consistent answer after 3 attempts. The disagreement is about [specific issue]. This likely means the question needs to be more specific, or the data model needs more context in this area. Here's what I tried: [brief summary of refinements]."

Note the unresolved disagreement in the scratchpad for the reflection phase — it's a strong signal that the vault needs work in this area.

## Output

Return:

- **sql**: the consensus SQL query.
- **in_data_model**: deduplicated union of all in_data_model lists from the agreeing agents.
- **not_in_data_model**: deduplicated union of all not_in_data_model lists.
- **consensus_round**: 1, 2, or 3.
- **refinements**: what was changed between rounds (if any).
- **unresolved**: null if consensus reached, or a description of the remaining disagreement if giving up.
