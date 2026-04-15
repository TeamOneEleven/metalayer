"""Tests for frontmatter parsing and wikilink extraction."""

from pathlib import Path

from metalayer.frontmatter import (
    extract_wikilinks,
    extract_wikilinks_from_value,
    parse_file,
)


def test_extract_wikilinks_from_text():
    text = "See [[orders]] and [[customers.name]] for details."
    assert extract_wikilinks(text) == ["orders", "customers.name"]


def test_extract_wikilinks_empty():
    assert extract_wikilinks("no links here") == []


def test_extract_wikilinks_in_sql():
    text = "${[[orders.revenue]]} - ${[[orders.refunds]]}"
    assert extract_wikilinks(text) == ["orders.revenue", "orders.refunds"]


def test_extract_wikilinks_from_value_string():
    assert extract_wikilinks_from_value("[[orders]]") == ["orders"]


def test_extract_wikilinks_from_value_list():
    value = ["[[orders.revenue]]", "[[customers.name]]"]
    assert extract_wikilinks_from_value(value) == ["orders.revenue", "customers.name"]


def test_extract_wikilinks_from_value_dict():
    value = {"field": "[[orders.status]]", "value": "completed"}
    assert extract_wikilinks_from_value(value) == ["orders.status"]


def test_extract_wikilinks_from_value_nested():
    value = {"filters": [{"field": "[[orders.status]]", "value": "completed"}]}
    assert extract_wikilinks_from_value(value) == ["orders.status"]


def test_extract_wikilinks_from_value_none():
    assert extract_wikilinks_from_value(None) == []
    assert extract_wikilinks_from_value(42) == []


def test_parse_file(vault_dir: Path):
    doc = parse_file(vault_dir / "views" / "orders.md")
    assert doc.doc_type == "view"
    assert doc.metadata["source"] == "snowflake"
    assert doc.metadata["table"] == "analytics.prod.orders"
    assert doc.stem == "orders"
    assert "orders.id" in doc.wikilinks


def test_parse_file_field_with_wikilinks(vault_dir: Path):
    doc = parse_file(vault_dir / "fields" / "orders.revenue.md")
    assert doc.doc_type == "field"
    assert doc.stem == "orders.revenue"
    assert "orders" in doc.wikilinks
    assert "orders.status" in doc.wikilinks


def test_parse_file_deduplicates_wikilinks(vault_dir: Path):
    doc = parse_file(vault_dir / "fields" / "orders.net_revenue.md")
    # orders.revenue appears in both SQL and body text, should be deduplicated
    assert doc.wikilinks.count("orders.revenue") == 1


def test_parse_file_unquoted_wikilink_in_frontmatter(tmp_path: Path):
    """YAML parses [[name]] as a nested list. We should fix it before parsing."""
    f = tmp_path / "test.md"
    f.write_text("---\ntype: view\nsource: [[snowflake]]\ntable: prod.orders\n---\n\n# Test\n")
    doc = parse_file(f)
    assert doc.metadata["source"] == "[[snowflake]]"
    assert "snowflake" in doc.wikilinks
