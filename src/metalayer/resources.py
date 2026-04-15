"""Packaged Markdown resources bundled with Metalayer."""

from __future__ import annotations

from importlib.abc import Traversable
from importlib.resources import files
from pathlib import Path

BUNDLED_SUBDIRECTORIES = frozenset({"imports", "skills"})


def iter_bundled_markdown(subdir: str) -> list[Traversable]:
    """Return bundled `.md` files from a known asset subdirectory."""
    if subdir not in BUNDLED_SUBDIRECTORIES:
        raise ValueError(f"Unknown bundled asset directory: {subdir}")

    resource_root = files("metalayer") / "assets" / subdir
    if not resource_root.is_dir():
        return []

    return sorted(
        (
            entry
            for entry in resource_root.iterdir()
            if entry.is_file() and entry.name.endswith(".md")
        ),
        key=lambda entry: entry.name,
    )


def copy_bundled_markdown(subdir: str, destination: Path) -> list[str]:
    """Copy packaged `.md` assets into a destination directory if absent."""
    copied: list[str] = []
    destination.mkdir(parents=True, exist_ok=True)

    for entry in iter_bundled_markdown(subdir):
        dest_path = destination / entry.name
        if dest_path.exists():
            continue
        dest_path.write_text(entry.read_text(encoding="utf-8"), encoding="utf-8")
        copied.append(entry.name)

    return copied


def list_bundled_markdown(subdir: str) -> list[str]:
    """List bundled markdown stems from a known asset subdirectory."""
    return [entry.name.removesuffix(".md") for entry in iter_bundled_markdown(subdir)]


def read_bundled_markdown(subdir: str, name: str) -> str | None:
    """Read one bundled markdown asset by filename stem."""
    filename = f"{name}.md"
    for entry in iter_bundled_markdown(subdir):
        if entry.name == filename:
            return entry.read_text(encoding="utf-8")
    return None
