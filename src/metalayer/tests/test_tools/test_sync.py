"""Tests for sync and import preset helpers."""

from __future__ import annotations

from pathlib import Path

from metalayer.config import MetalayerConfig
from metalayer.resolver import Resolver
from metalayer.tools.sync import sync_context, update_from


def test_sync_context_reports_qmd_failures(tmp_path: Path, monkeypatch):
    context = tmp_path / "context"
    (context / "lore").mkdir(parents=True)

    r = Resolver(context)
    r.scan()

    responses = iter([
        "qmd update failed: boom",
        "qmd embed failed: boom",
    ])
    monkeypatch.setattr(
        "metalayer.tools.sync.run_qmd_command",
        lambda *_args, **_kwargs: next(responses),
    )

    result = sync_context(r, MetalayerConfig(), tmp_path)

    assert result["errors"] == [
        "qmd update failed: boom",
        "qmd embed failed: boom",
    ]


def test_update_from_falls_back_to_bundled_presets(tmp_path: Path):
    result = update_from("warehouse_history", None, tmp_path)

    assert result["source"] == "warehouse_history"
    assert "warehouse" in result["preset"].lower()
