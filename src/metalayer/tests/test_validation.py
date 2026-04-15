"""Tests for vault validation."""

from pathlib import Path

from metalayer.resolver import Resolver
from metalayer.validation import validate_vault


def test_clean_vault_passes(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    issues = validate_vault(r)
    # The fixture vault has some dangling refs (orders.customer_id, orders.refunds)
    # but no missing type or circular issues
    errors = [i for i in issues if i.check not in ("dangling_ref",)]
    assert len(errors) == 0


def test_dangling_ref_detected(vault_with_dangling_ref: Path):
    r = Resolver(vault_with_dangling_ref)
    r.scan()
    issues = validate_vault(r)
    dangling = [i for i in issues if i.check == "dangling_ref" and "nonexistent_view" in i.message]
    assert len(dangling) == 1


def test_missing_type_detected(tmp_path: Path):
    context = tmp_path / "context"
    context.mkdir()
    (context / "bad.md").write_text("---\nfoo: bar\n---\nNo type here.\n")

    r = Resolver(context)
    r.scan()
    issues = validate_vault(r)
    missing = [i for i in issues if i.check == "missing_type"]
    assert len(missing) == 1
    assert missing[0].file == "bad"


def test_invalid_type_detected(tmp_path: Path):
    context = tmp_path / "context"
    context.mkdir()
    (context / "bad.md").write_text("---\ntype: invalid_type\n---\n")

    r = Resolver(context)
    r.scan()
    issues = validate_vault(r)
    invalid = [i for i in issues if i.check == "invalid_type"]
    assert len(invalid) == 1


def test_circular_extends_detected(vault_with_circular_extends: Path):
    r = Resolver(vault_with_circular_extends)
    r.scan()
    issues = validate_vault(r)
    circular = [i for i in issues if i.check == "circular_extends"]
    assert len(circular) >= 1


def test_view_missing_source_warns(tmp_path: Path):
    context = tmp_path / "context"
    context.mkdir()
    (context / "orders.md").write_text('---\ntype: view\ntable: prod.orders\n---\n')

    r = Resolver(context)
    r.scan()
    issues = validate_vault(r)
    missing = [i for i in issues if i.check == "missing_source"]
    assert len(missing) == 1
    assert missing[0].severity == "warning"


def test_view_dangling_source_errors(tmp_path: Path):
    context = tmp_path / "context"
    context.mkdir()
    (context / "orders.md").write_text('---\ntype: view\nsource: "[[nonexistent_source]]"\ntable: prod.orders\n---\n')

    r = Resolver(context)
    r.scan()
    issues = validate_vault(r)
    dangling = [i for i in issues if i.check == "dangling_source"]
    assert len(dangling) == 1
    assert dangling[0].severity == "error"


def test_view_with_valid_source_passes(tmp_path: Path):
    context = tmp_path / "context"
    context.mkdir()
    (context / "snowflake.md").write_text('---\ntype: source\ntool: "snow sql -q \\"${SQL}\\""\n---\n')
    (context / "orders.md").write_text('---\ntype: view\nsource: "[[snowflake]]"\ntable: prod.orders\n---\n')

    r = Resolver(context)
    r.scan()
    issues = validate_vault(r)
    source_issues = [i for i in issues if "source" in i.check]
    assert len(source_issues) == 0


def test_circular_metric_detected(tmp_path: Path):
    context = tmp_path / "context"
    fields = context / "fields"
    fields.mkdir(parents=True)

    (fields / "a.md").write_text("""---
type: field
kind: metric
sql: ${[[b]]}
---
""")
    (fields / "b.md").write_text("""---
type: field
kind: metric
sql: ${[[a]]}
---
""")

    r = Resolver(context)
    r.scan()
    issues = validate_vault(r)
    circular = [i for i in issues if i.check == "circular_metric"]
    assert len(circular) >= 1


def test_duplicate_field_sql_detected(tmp_path: Path):
    context = tmp_path / "context"
    fields = context / "fields"
    fields.mkdir(parents=True)
    (context / "orders.md").write_text('---\ntype: view\ntable: prod.orders\n---\n')
    (fields / "orders.revenue.md").write_text('---\ntype: field\nview: "[[orders]]"\nkind: metric\nsql: SUM(${TABLE}.amount)\nagg: sum\n---\n')
    (fields / "orders.total_sales.md").write_text('---\ntype: field\nview: "[[orders]]"\nkind: metric\nsql: SUM(${TABLE}.amount)\nagg: sum\n---\n')

    r = Resolver(context)
    r.scan()
    issues = validate_vault(r)
    dupes = [i for i in issues if i.check == "duplicate_field_sql"]
    assert len(dupes) == 1


def test_overlapping_lore_detected(tmp_path: Path):
    context = tmp_path / "context"
    context.mkdir()
    (context / "lore1.md").write_text('---\ntype: lore\nwhen: always\n---\nUse CTEs.\n')
    (context / "lore2.md").write_text('---\ntype: lore\nwhen: always\n---\nUse subqueries.\n')

    r = Resolver(context)
    r.scan()
    issues = validate_vault(r)
    overlap = [i for i in issues if i.check == "overlapping_lore"]
    assert len(overlap) >= 1


def test_lore_bloat_detected(tmp_path: Path):
    context = tmp_path / "context"
    context.mkdir()
    for i in range(7):
        (context / f"lore{i}.md").write_text(f'---\ntype: lore\nwhen: always\n---\nRule {i}.\n')

    r = Resolver(context)
    r.scan()
    issues = validate_vault(r)
    bloat = [i for i in issues if i.check == "lore_bloat"]
    assert len(bloat) == 1
    assert "7 always-lore" in bloat[0].message
