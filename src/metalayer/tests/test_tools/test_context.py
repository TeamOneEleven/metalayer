"""Tests for context tools."""

from pathlib import Path

from metalayer.resolver import Resolver
from metalayer.tools.context import get_context, write_context


def test_get_context_returns_content(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    result = get_context("orders", r)
    assert result["name"] == "orders"
    assert result["type"] == "view"
    assert "analytics.prod.orders" == result["metadata"]["table"]
    assert "orders.id" in result["links_from"]
    assert len(result["links_to"]) > 0  # fields link back to orders


def test_get_context_dotted_name(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    result = get_context("orders.revenue", r)
    assert result["name"] == "orders.revenue"
    assert result["type"] == "field"
    assert result["metadata"]["kind"] == "metric"


def test_get_context_not_found(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    result = get_context("nonexistent", r)
    assert "error" in result


def test_write_context_creates_file(tmp_path: Path):
    content = """---
type: view
source: snowflake
table: analytics.prod.new_table
---

# New Table

A new table.
"""
    result = write_context("context/views/new_table.md", content, tmp_path)
    assert result["status"] == "written"
    assert (tmp_path / "context" / "views" / "new_table.md").exists()


def test_write_context_rejects_path_outside_project(tmp_path: Path):
    result = write_context("../outside.md", "# nope", tmp_path)
    assert "error" in result
    assert not (tmp_path.parent / "outside.md").exists()


def test_write_context_rejects_undocumented_directory(tmp_path: Path):
    result = write_context("notes/random.md", "# nope", tmp_path)
    assert "error" in result
