# Ask Data

Master workflow for answering data questions. Follow each phase in order.

## Phase 1: Retrieval (already done)

The system has already run search_context and injected results, always-lore, structural lore, and the vault summary index into your context. Do not re-run search_context unless you explicitly need to broaden the search later.

## Phase 2: Navigation

**Start with domain context.** Before diving into search results, run `metalayer frequent` to see which views and fields have been used most in recent queries. Load those first — they're likely relevant. Most questions use the same core tables repeatedly.

Then read the injected search results. For each result that looks relevant to the question, call get_context(name) to load the full file. Make 1-5 calls typically. If a result matches a topic, call get_topic() instead — it resolves the full chain (topic -> concepts -> extends -> fields -> views -> relations).

Follow [[wikilinks]] found in loaded files. Chase links until you have:

- **Views**: table name, source, grain (one_row_means), primary key, dedup key, restricted columns.
- **Fields**: SQL expression, aggregation, filters, kind, values (if enumerated).
- **Relations**: join keys (from/to fields), cardinality, join type, join SQL if custom.
- **Lore**: any always-lore or triggered lore relevant to the question's views/fields.

Stop navigating when you can write the query. Do not over-fetch — if you have the tables, joins, columns, and business rules, move on.

## Phase 3: Consensus

Read the sql-consensus skill and follow it exactly:

1. Assemble all gathered vault context into a single clean context block.
2. Spawn 5 sub-agents, each producing SQL independently.
3. Reconcile per the consensus protocol (majority wins, then arbiter, then user).

Before executing the winning SQL, call validate_refs() on every [[ref]] from the combined in_data_model list. If any ref fails validation, fix the SQL before proceeding.

## Phase 4: Execute

Execute the winning SQL using the source referenced by the relevant view(s). Resolve the view's `source: [[source_name]]` to find the source file, then use the tool it describes (CLI command, MCP server, etc.). You have access to these tools in your environment.

Also call search_context() for similar past queries in utils/queries/. Compare results against past query outputs for consistency. If the new result differs dramatically from a similar past query (order of magnitude off, opposite sign, etc.), flag it before presenting.

## Phase 5: Reflect

Read the reflection skill and follow it:

1. Run plausibility checks on the result set.
2. Check validation rules from lore (see the reflection skill — Validation Rules).
3. If anything is suspicious, adjust the query and re-execute. You may re-execute up to 2 times.
4. Review the scratchpad accumulated during the flow.
5. Present the answer card followed by results (see Answer Card below).

## Answer Card

**Do not draw the card yourself.** Run `metalayer answer-card` and it will render a perfectly aligned ASCII card. Example:

```bash
metalayer answer-card \
  -q "How many logins last week and which workspaces were top 3?" \
  -k "login" -k "  ↳ timestamp" -k "  ↳ workspace_id" -k "workspaces" -k "  ↳ name" \
  -n "login" -n "  ↳ user_id" \
  -s "snowflake" \
  -j "login_to_workspaces (login → workspaces)" \
  -l "internal_workspaces" -l "sql_style" \
  --notes "Excluded internal workspaces. Calendar week (Mon-Sun)."
```

Arguments:
- `-q` — the user's original question
- `-k` — known field lines (repeatable). Views as plain text, fields indented with `  ↳`
- `-n` — new field lines (repeatable). Same format. A view can appear on both sides.
- `-s` — source name
- `-j` — join descriptions (repeatable), e.g. `"login_to_workspaces (login → workspaces)"`
- `-l` — lore names applied (repeatable)
- `--notes` — methodology notes (omit for simple queries)

Run this command immediately before presenting results. Display its output, then follow with the data and a plain-language summary.

## Phase 6: Log and Learn

After presenting results, run `metalayer log-query` with the query details. This logs the query AND outputs instructions for the learning phase. Example:

```bash
metalayer log-query \
  --question "How many logins last week?" \
  --sql "SELECT COUNT(*) FROM login WHERE ..." \
  --summary "3615 total logins" \
  --in-model orders --in-model login \
  --not-in-model login.workspace_id --not-in-model login.user_id \
  --consensus-notes "All 5 agents agreed"
```

The command will output a LEARNING REQUIRED block. **Follow its instructions** — launch a learning subagent using the Agent tool with the context it provides. Read the learn skill. This is not optional; the tool output tells you exactly what to do.

## Handling Feedback

When the user says the answer is wrong, classify the error:

- **Asker error**: the question was ambiguous or the user meant something different. Clarify and re-run from Phase 2.
- **Data model error**: the vault context is wrong or missing (bad SQL, wrong join, missing lore). Fix the query, re-run, and propose a vault correction in Phase 7.

When the user says the answer is correct ("accepted query"), log it with a confidence flag so future queries can reference it as a validated baseline.
