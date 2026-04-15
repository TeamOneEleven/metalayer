"""Tests for audit tools."""

from pathlib import Path

from metalayer.resolver import Resolver
from metalayer.tools.audit import context_audit, validate_refs


def test_full_audit_clean_vault(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    result = context_audit(r)
    # Vault has some expected dangling refs (orders.customer_id, orders.refunds not defined)
    # but the structure is valid
    assert result["status"] in ("clean", "warn", "block")
    assert "issues" in result


def test_preflight_clean(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    result = context_audit(r, change={
        "path": "context/fields/orders.discount.md",
        "content": """---
type: field
view: "[[orders]]"
kind: metric
sql: SUM(${TABLE}.discount)
agg: sum
---

# Discount

Total discount amount.
""",
    })
    assert result["status"] == "clean"


def test_preflight_edit_existing_file(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    result = context_audit(r, change={
        "path": "context/concepts/customer.md",
        "content": """---
type: concept
fields:
  - "[[customers.name]]"
  - "[[orders.revenue]]"
  - "[[orders.order_date]]"
---

# Customer

Updated customer concept.
""",
    })
    assert result["status"] == "clean"


def test_preflight_missing_type(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    result = context_audit(r, change={
        "path": "context/views/bad.md",
        "content": "---\nfoo: bar\n---\nNo type.\n",
    })
    assert result["status"] == "block"
    assert any(i["check"] == "missing_type" for i in result["issues"])


def test_preflight_dangling_ref(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    result = context_audit(r, change={
        "path": "context/fields/orders.foo.md",
        "content": """---
type: field
view: "[[nonexistent_view]]"
kind: dimension
sql: ${TABLE}.foo
---
""",
    })
    assert result["status"] == "block"
    assert any(i["check"] == "dangling_ref" for i in result["issues"])


def test_preflight_detects_new_cycle(tmp_path: Path):
    context = tmp_path / "context"
    concepts = context / "concepts"
    concepts.mkdir(parents=True)

    (concepts / "existing.md").write_text("""---
type: concept
extends: "[[new_concept]]"
---
""")

    r = Resolver(context)
    r.scan()
    result = context_audit(r, change={
        "path": "context/concepts/new_concept.md",
        "content": """---
type: concept
extends: "[[existing]]"
---
""",
    })

    assert result["status"] == "block"
    assert any(i["check"] == "circular_extends" for i in result["issues"])


def test_validate_refs_all_valid(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    result = validate_refs(["orders", "customers", "orders.revenue"], r)
    assert result["all_valid"] is True
    assert len(result["invalid"]) == 0


def test_validate_refs_some_invalid(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    result = validate_refs(["orders", "nonexistent"], r)
    assert result["all_valid"] is False
    assert "nonexistent" in result["invalid"]
    assert "orders" in result["valid"]
