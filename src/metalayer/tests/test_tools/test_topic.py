"""Tests for the topic deep resolver."""

from pathlib import Path

from metalayer.resolver import Resolver
from metalayer.tools.topic import get_topic


def test_get_topic_resolves_full_tree(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    result = get_topic("order_analysis", r)

    assert result["topic"] == "order_analysis"
    # Should include both concepts (customer + active_customer via extends)
    assert "customer" in result["concepts"]
    assert "active_customer" in result["concepts"]
    # Should include fields from concepts
    assert "customers.name" in result["fields"]
    assert "orders.revenue" in result["fields"]
    # Should include views
    assert "orders" in result["views"]
    assert "customers" in result["views"]
    # Should include relations
    assert "orders.customers" in result["relations"]
    # All resolved files should be in the files dict
    assert "order_analysis" in result["files"]
    assert "customer" in result["files"]


def test_get_topic_not_found(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    result = get_topic("nonexistent", r)
    assert "error" in result


def test_get_topic_wrong_type(vault_dir: Path):
    r = Resolver(vault_dir)
    r.scan()
    result = get_topic("orders", r)  # orders is a view, not a topic
    assert "error" in result
    assert "not 'topic'" in result["error"]
