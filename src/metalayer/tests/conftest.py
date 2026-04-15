"""Shared test fixtures: temp vault with examples of all 6 types."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def vault_dir(tmp_path: Path) -> Path:
    """Create a minimal test vault with examples of all 7 types and some wikilinks."""
    context = tmp_path / "context"

    # Sources
    sources = context / "sources"
    sources.mkdir(parents=True)

    (sources / "snowflake.md").write_text("""---
type: source
tool: "snow sql -q \\"${SQL}\\" -c test"
---

# Snowflake (Test)

Test Snowflake connection.
""")

    # Views
    views = context / "views"
    views.mkdir(parents=True)

    (views / "orders.md").write_text("""---
type: view
source: snowflake
table: analytics.prod.orders
primary_key: "[[orders.id]]"
one_row_means: one shipment of one order
dedup_key: "[[orders.id]]"
restricted_columns:
  - internal_margin
---

# Orders

Customer orders from the dbt orders model.
Multiple shipments per order create fanout.
""")

    (views / "customers.md").write_text("""---
type: view
source: snowflake
table: analytics.prod.customers
primary_key: "[[customers.id]]"
one_row_means: one customer
---

# Customers

All registered customers.
""")

    # Fields
    fields = context / "fields"
    fields.mkdir(parents=True)

    (fields / "orders.id.md").write_text("""---
type: field
view: "[[orders]]"
kind: identifier
sql: ${TABLE}.order_id
---

# Order ID

Not unique per row due to the shipment grain.
""")

    (fields / "orders.revenue.md").write_text("""---
type: field
view: "[[orders]]"
kind: metric
sql: SUM(${TABLE}.amount)
agg: sum
filters:
  - field: "[[orders.status]]"
    value: completed
---

# Revenue

Completed order revenue in USD.
Users often say "sales" to mean this.
""")

    (fields / "orders.status.md").write_text("""---
type: field
view: "[[orders]]"
kind: dimension
sql: ${TABLE}.status
values:
  - pending
  - completed
  - cancelled
  - refunded
---

# Order Status

Finance considers only `completed` as revenue-bearing.
""")

    (fields / "orders.order_date.md").write_text("""---
type: field
view: "[[orders]]"
kind: time
sql: ${TABLE}.order_date
time_granularities: [day, week, month, quarter, year]
---
""")

    (fields / "customers.id.md").write_text("""---
type: field
view: "[[customers]]"
kind: identifier
sql: ${TABLE}.customer_id
---
""")

    (fields / "customers.name.md").write_text("""---
type: field
view: "[[customers]]"
kind: dimension
sql: ${TABLE}.name
values: high_cardinality
---
""")

    (fields / "orders.net_revenue.md").write_text("""---
type: field
view: "[[orders]]"
kind: metric
sql: ${[[orders.revenue]]} - ${[[orders.refunds]]}
agg: custom
---

# Net Revenue

Revenue after refunds. Do not sum with [[orders.revenue]].
""")

    # Relations
    relations = context / "relations"
    relations.mkdir(parents=True)

    (relations / "orders.customers.md").write_text("""---
type: relation
from: "[[orders.customer_id]]"
to: "[[customers.id]]"
cardinality: many_to_one
join_type: left
label: placed by
---

# Orders -> Customers

Every order belongs to one customer.
""")

    # Concepts
    concepts = context / "concepts"
    concepts.mkdir(parents=True)

    (concepts / "customer.md").write_text("""---
type: concept
fields:
  - "[[customers.name]]"
  - "[[orders.revenue]]"
  - "[[orders.order_date]]"
---

# Customer

A person or organization that has placed at least one order.
""")

    (concepts / "active_customer.md").write_text("""---
type: concept
extends: "[[customer]]"
filter:
  field: "[[orders.order_date]]"
  operator: ">="
  value: CURRENT_DATE - INTERVAL '90 days'
---

# Active Customer

A customer with at least one order in the last 90 days.
""")

    # Topics
    topics = context / "topics"
    topics.mkdir(parents=True)

    (topics / "order_analysis.md").write_text("""---
type: topic
concepts:
  - "[[customer]]"
  - "[[active_customer]]"
relations:
  - "[[orders.customers]]"
views:
  - "[[orders]]"
---

# Order Analysis

Analyze order volume, revenue, fulfillment, and customer behavior.
""")

    # Lore
    lore = context / "lore"
    lore.mkdir(parents=True)

    (lore / "sql_style.md").write_text("""---
type: lore
when: always
---

# SQL Style

Use CTEs. Qualify columns. Prefer explicit JOINs.
""")

    (lore / "revenue_rules.md").write_text("""---
type: lore
when:
  fields:
    - "[[orders.revenue]]"
    - "[[orders.net_revenue]]"
---

Never sum revenue and net_revenue together.
""")

    return context


@pytest.fixture
def vault_with_dangling_ref(vault_dir: Path) -> Path:
    """Add a file with a dangling [[ref]] to the vault."""
    (vault_dir / "lore" / "bad_ref.md").write_text("""---
type: lore
when: always
---

See [[nonexistent_view]] for details.
""")
    return vault_dir


@pytest.fixture
def vault_with_circular_extends(tmp_path: Path) -> Path:
    """Create a vault with circular concept extends."""
    context = tmp_path / "context"
    concepts = context / "concepts"
    concepts.mkdir(parents=True)

    (concepts / "a.md").write_text("""---
type: concept
extends: "[[b]]"
---
""")
    (concepts / "b.md").write_text("""---
type: concept
extends: "[[a]]"
---
""")
    return context


@pytest.fixture
def queries_dir(tmp_path: Path) -> Path:
    """Create an empty queries directory."""
    queries = tmp_path / "queries"
    queries.mkdir()
    return queries
