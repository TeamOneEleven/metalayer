"""Tests for the vault resolver."""

from pathlib import Path

import pytest

from metalayer.resolver import DuplicateStemError, Resolver


def test_scan_builds_index(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    assert "orders" in r.all_stems()
    assert "customers" in r.all_stems()
    assert "orders.revenue" in r.all_stems()


def test_resolve_returns_path(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    path = r.resolve("orders")
    assert path is not None
    assert path.name == "orders.md"


def test_resolve_dotted_name(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    path = r.resolve("orders.revenue")
    assert path is not None
    assert path.name == "orders.revenue.md"


def test_resolve_missing_returns_none(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    assert r.resolve("nonexistent") is None


def test_forward_links(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    links = r.get_links_from("orders.revenue")
    assert "orders" in links
    assert "orders.status" in links


def test_backlinks(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    links = r.get_links_to("orders")
    # Fields that reference [[orders]] as their view
    assert "orders.revenue" in links
    assert "orders.id" in links


def test_get_document(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    doc = r.get_document("orders")
    assert doc is not None
    assert doc.doc_type == "view"
    assert "analytics.prod.orders" == doc.metadata["table"]


def test_stems_by_type(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    views = r.stems_by_type("view")
    assert "orders" in views
    assert "customers" in views
    fields = r.stems_by_type("field")
    assert "orders.revenue" in fields


def test_duplicate_stem_raises(tmp_path: Path):
    context = tmp_path / "context"
    dir1 = context / "a"
    dir2 = context / "b"
    dir1.mkdir(parents=True)
    dir2.mkdir(parents=True)

    (dir1 / "orders.md").write_text("---\ntype: view\n---\n")
    (dir2 / "orders.md").write_text("---\ntype: view\n---\n")

    r = Resolver(context)
    with pytest.raises(DuplicateStemError):
        r.scan()


def test_type_suffix_stripped_from_stem(tmp_path: Path):
    context = tmp_path / "context"
    context.mkdir()
    (context / "orders__view.md").write_text("---\ntype: view\n---\n")
    (context / "orders.status__field.md").write_text("---\ntype: field\nview: '[[orders]]'\nkind: dimension\nsql: ${TABLE}.status\n---\n")
    (context / "snowflake__source.md").write_text("---\ntype: source\ntool: snow\n---\n")

    r = Resolver(context)
    r.scan()
    assert r.resolve("orders") is not None
    assert r.resolve("orders.status") is not None
    assert r.resolve("snowflake") is not None
    # The __{type} suffix should not be in the stem
    assert r.resolve("orders__view") is None
    assert r.resolve("orders.status__field") is None


def test_type_suffix_duplicate_detection(tmp_path: Path):
    """orders.md and orders__view.md both resolve to stem 'orders' — should conflict."""
    context = tmp_path / "context"
    context.mkdir()
    (context / "orders.md").write_text("---\ntype: view\n---\n")
    (context / "orders__view.md").write_text("---\ntype: view\n---\n")

    r = Resolver(context)
    with pytest.raises(DuplicateStemError):
        r.scan()


def test_scan_empty_vault(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    r = Resolver(empty)
    r.scan()
    assert r.all_stems() == []


def test_scan_nonexistent_path(tmp_path: Path):
    r = Resolver(tmp_path / "does_not_exist")
    r.scan()
    assert r.all_stems() == []
