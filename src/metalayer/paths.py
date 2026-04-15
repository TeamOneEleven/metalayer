"""Shared path validation for project-scoped writes."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

CONTEXT_WRITE_ROOTS = (
    "context/views",
    "context/fields",
    "context/relations",
    "context/concepts",
    "context/topics",
    "context/lore",
)

DOCUMENTED_WRITE_ROOTS = (
    *CONTEXT_WRITE_ROOTS,
    "utils/imports",
    "utils/queries",
    "skills",
)


def resolve_project_path(
    project_root: Path,
    relative_path: str,
    *,
    allowed_roots: Iterable[str] = DOCUMENTED_WRITE_ROOTS,
    require_markdown: bool = True,
) -> Path:
    """Resolve a project-relative path and ensure it stays in allowed roots."""
    if not relative_path:
        raise ValueError("Path is required")

    path = Path(relative_path)
    if path.is_absolute():
        raise ValueError("Path must be relative to the project root")

    resolved_root = project_root.resolve()
    resolved_path = (resolved_root / path).resolve()

    try:
        relative_to_root = resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("Path must stay inside the project root") from exc

    if require_markdown and resolved_path.suffix != ".md":
        raise ValueError("Only .md files are allowed")

    normalized_allowed_roots = tuple(
        root.strip("/").rstrip("/")
        for root in allowed_roots
        if root.strip("/").rstrip("/")
    )
    relative_posix = relative_to_root.as_posix()
    if not any(
        relative_posix == allowed_root or relative_posix.startswith(f"{allowed_root}/")
        for allowed_root in normalized_allowed_roots
    ):
        allowed_str = ", ".join(normalized_allowed_roots)
        raise ValueError(f"Path must be inside one of: {allowed_str}")

    return resolved_path
