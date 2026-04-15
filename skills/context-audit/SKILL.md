# Context Audit

Semantic checks the LLM performs on vault content. Static validation (duplicate filenames, dangling refs, circular extends, missing type) is handled by Python. This skill covers the checks that require understanding meaning.

## Contradiction Detection

Check for these conflicts. Any contradiction is a potential source of wrong SQL.

- **Competing definitions**: two fields both claiming to be the "correct" version of a metric but with different SQL. Example: `orders.total_revenue` uses `SUM(amount)` but `orders.revenue` uses `SUM(amount - discount)`. If both exist, one must be marked as the canonical version and the other hidden or relabeled.
- **Lore vs field conflicts**: lore says "always filter to completed orders" but a field's `filters` frontmatter includes `status IN ('completed', 'pending')`. Which is correct?
- **Grain mismatches**: a view's `one_row_means` says "one order" but the body text describes it as "one order line item." The grain must be unambiguous.
- **Inverse relation conflicts**: relation A says orders-to-customers is many_to_one, but relation B (the inverse) says customers-to-orders is one_to_one. These must be consistent.

## Overlapping Lore

Check for redundancy that confuses context assembly.

- **Same trigger, different advice**: two lore files both trigger on [[orders.total_revenue]] but give contradictory or redundant guidance.
- **Lore duplicating body text**: a lore file repeats what's already in a field or view's body. Remove the lore — the body is the canonical location.
- **Over-broad always-lore**: an always-lore file that only applies to one view or field should be narrowed to a conditional trigger or moved into the relevant file's body.

## Bloat Risk

Check for scale problems that degrade search and context quality.

- **Too many always-lore files**: more than 5 always-lore files means too much is injected into every query. Audit and narrow triggers or move content into file bodies.
- **Lore too long**: any single lore file over 500 words. Shorten or split into focused files.
- **Topic resolves to too many fields**: a topic that resolves (through concepts and extends) to more than 50 fields. Split into sub-topics.
- **Concept too large**: a concept with more than 20 fields. Split into focused concepts.

## Stale References

Check for outdated content.

- **Deprecated columns**: columns or fields with names containing `_old`, `_deprecated`, `_legacy`, `_v1`. Flag for removal or confirmation that they're still needed.
- **Lore referencing dead patterns**: lore that references query patterns, table names, or column names not found anywhere in query memory or the current vault. Likely outdated.

## Coverage Gaps

Check for missing context that will cause agents to guess.

- **Views with no fields**: a view file exists but no field files reference it. Agents will use raw columns.
- **Isolated views**: a view with no relations to any other view. Agents cannot join to it.
- **Completely empty files**: a file with no frontmatter and no body text at all. This is an error — the file serves no purpose. Fields with frontmatter/SQL but no body text are fine; the SQL is the content.
- **Relations with no label**: a relation with from/to but no label. Agents may not understand the business meaning of the join.

## Output Format

Return:

- **status**: `clean`, `warn`, or `block`.
  - `block`: contradictions that will cause wrong SQL. Must be resolved before querying.
  - `warn`: bloat, overlap, coverage gaps, stale references. Should be resolved but won't break queries.
  - `clean`: no issues found.
- **issues**: list of findings, each with category, severity, affected files, and recommended fix.

## Preflight Mode

When called as context_audit(change) with a proposed new or edited file:

1. Parse the proposed file's frontmatter and body.
2. Check all [[refs]] in the file resolve to existing vault files (or other files in the same batch).
3. Check the filename is not a duplicate of any existing vault file.
4. Check for contradictions between the proposed file and existing vault content (competing definitions, conflicting lore, grain mismatches).
5. If the proposed file is lore, check for overlap with existing lore.

If issues are found, report them and iterate on the proposed file before writing. Do not write a file that would move the vault status from clean to block.
