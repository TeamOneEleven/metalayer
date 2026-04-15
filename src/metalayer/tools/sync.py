"""Sync and update tools: sync_context, update_from."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from metalayer.config import MetalayerConfig
from metalayer.qmd import QMD_NOT_FOUND, run_qmd_command
from metalayer.resolver import Resolver
from metalayer.resources import list_bundled_markdown, read_bundled_markdown
from metalayer.validation import validate_vault


def sync_context(
    resolver: Resolver,
    config: MetalayerConfig,
    project_root: Path,
) -> dict[str, Any]:
    """Re-index QMD, rebuild resolver, regenerate meta-lore, run validation."""
    errors = []

    # 1. QMD re-index
    from metalayer.qmd import qmd_command
    for cmd, timeout in ((qmd_command("update"), 60), (qmd_command("embed"), 120)):
        error = run_qmd_command(cmd, cwd=project_root, timeout=timeout)
        if error is None:
            continue
        if error == QMD_NOT_FOUND:
            errors.append("QMD not found — skipping index update")
            break
        errors.append(error)

    # 2. Rebuild resolver
    resolver.scan()

    # 3. Regenerate meta-lore (vault_overview.md)
    _regenerate_meta_lore(resolver, project_root / config.context_path)

    # 4. Run validation
    issues = validate_vault(resolver)

    return {
        "status": "synced",
        "stems": len(resolver.all_stems()),
        "issues": [
            {"file": i.file, "check": i.check, "message": i.message, "severity": i.severity}
            for i in issues
        ],
        "errors": errors,
    }


def update_from(
    source: str,
    instructions: str | None,
    project_root: Path,
) -> dict[str, Any]:
    """Load an import preset and return it for the LLM to process.

    The LLM does the actual import work — this just loads the preset instructions.
    """
    import_dir = project_root / "utils" / "imports"
    project_presets = [p.stem for p in import_dir.glob("*.md")] if import_dir.exists() else []
    available = sorted({*project_presets, *list_bundled_markdown("imports")})

    preset_path = import_dir / f"{source}.md"
    if preset_path.exists():
        preset_content = preset_path.read_text(encoding="utf-8")
    else:
        preset_content = read_bundled_markdown("imports", source)
        if preset_content is None:
            return {
                "error": f"Import preset '{source}' not found",
                "available": available,
            }

    result: dict[str, Any] = {
        "source": source,
        "preset": preset_content,
    }
    if instructions:
        result["instructions"] = instructions

    return result


def _regenerate_meta_lore(resolver: Resolver, context_path: Path) -> None:
    """Regenerate the vault_overview.md meta-lore file."""
    counts: dict[str, int] = {}
    for doc_type in ["source", "view", "field", "relation", "concept", "topic", "lore"]:
        counts[doc_type] = len(resolver.stems_by_type(doc_type))

    total = sum(counts.values())

    if total == 0:
        body = (
            "This vault is empty. Run `metalayer update-from` to import your first "
            "context, or create .md files manually."
        )
    else:
        parts = []
        for doc_type, count in counts.items():
            if count > 0:
                parts.append(f"{count} {doc_type}{'s' if count != 1 else ''}")
        body = f"This vault has {', '.join(parts)}."

    content = f"""---
type: lore
when: always
---

# Vault Overview

{body}
"""
    lore_path = context_path / "lore" / "vault_overview.md"
    lore_path.parent.mkdir(parents=True, exist_ok=True)
    lore_path.write_text(content)
