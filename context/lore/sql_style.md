---
type: lore
when: always
---

# SQL Style

Write clean, readable SQL:
- Use CTEs (WITH clauses), not nested subqueries
- Always qualify column names with table aliases
- Use meaningful alias names (o for orders, c for customers)
- Prefer explicit JOINs over implicit comma joins
- Write JOIN conditions in the ON clause, not WHERE
- Put each major clause on its own line (SELECT, FROM, JOIN, WHERE, GROUP BY, ORDER BY)
- Put each column on its own line in SELECT if more than 3 columns
- Use single quotes for string literals
- Use ISO date format (YYYY-MM-DD) for date literals
- Apply LIMIT unless the user specifically asks for all rows
