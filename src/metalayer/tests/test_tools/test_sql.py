"""Tests for SQL execution safety checks."""

from __future__ import annotations

from types import SimpleNamespace

import metalayer.tools.sql as sql_tools


def test_execute_sql_rejects_destructive_queries():
    result = sql_tools.execute_sql("DELETE FROM users")
    assert result["error"].startswith("Only read-only SQL")


def test_execute_sql_rejects_multiple_statements():
    result = sql_tools.execute_sql("SELECT 1; SELECT 2")
    assert result["error"] == "Only a single SQL statement is allowed"


def test_execute_sql_adds_limit_to_select_queries(monkeypatch):
    seen: dict[str, list[str]] = {}

    def fake_run(cmd: list[str], **_: object) -> SimpleNamespace:
        seen["cmd"] = cmd
        return SimpleNamespace(returncode=0, stdout="[]", stderr="")

    monkeypatch.setattr(sql_tools.subprocess, "run", fake_run)
    result = sql_tools.execute_sql("SELECT * FROM users")

    assert result["row_count"] == 0
    assert seen["cmd"][2].endswith("LIMIT 100")


def test_execute_sql_allows_comments_with_blocked_words(monkeypatch):
    seen: dict[str, list[str]] = {}

    def fake_run(cmd: list[str], **_: object) -> SimpleNamespace:
        seen["cmd"] = cmd
        return SimpleNamespace(returncode=0, stdout="[]", stderr="")

    monkeypatch.setattr(sql_tools.subprocess, "run", fake_run)
    result = sql_tools.execute_sql("-- update later\nSELECT 'delete' AS word")

    assert result["row_count"] == 0
    assert seen["cmd"][2].startswith("-- update later\nSELECT 'delete' AS word")
