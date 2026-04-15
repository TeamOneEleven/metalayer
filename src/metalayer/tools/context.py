"""Context tools: get_context, search_context, write_context."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from metalayer.paths import DOCUMENTED_WRITE_ROOTS, resolve_project_path
from metalayer.resolver import Resolver


def get_context(name: str, resolver: Resolver) -> dict[str, Any]:
    """Read a context file by stem name, return content + metadata + links."""
    doc = resolver.get_document(name)
    if doc is None:
        return {"error": f"'{name}' not found in vault"}

    return {
        "name": name,
        "path": str(doc.path),
        "type": doc.doc_type,
        "metadata": doc.metadata,
        "content": doc.content,
        "links_from": sorted(resolver.get_links_from(name)),
        "links_to": sorted(resolver.get_links_to(name)),
    }


def search_context(query: str, collections: list[str] | None = None) -> dict[str, Any]:
    """Search the vault via QMD. Returns search results."""
    from metalayer.qmd import qmd_command
    cmd = qmd_command("search", query)
    if collections:
        for col in collections:
            cmd.extend(["--collection", col])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return {"error": f"QMD search failed: {result.stderr.strip()}"}
        # Try to parse as JSON, fall back to raw text
        try:
            return {"results": json.loads(result.stdout)}
        except json.JSONDecodeError:
            return {"results": result.stdout.strip()}
    except FileNotFoundError:
        return {"error": "QMD is not installed or not in PATH"}
    except subprocess.TimeoutExpired:
        return {"error": "QMD search timed out"}


def write_context(path: str, content: str, project_root: Path) -> dict[str, Any]:
    """Write a .md file to the vault. Path is relative to project root."""
    try:
        full_path = resolve_project_path(
            project_root,
            path,
            allowed_roots=DOCUMENTED_WRITE_ROOTS,
        )
    except ValueError as exc:
        return {"error": str(exc)}

    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    return {"status": "written", "path": str(full_path)}
