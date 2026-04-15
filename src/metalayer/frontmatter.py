"""Frontmatter parsing and wikilink extraction from .md files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import frontmatter

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

VALID_TYPES = frozenset({"view", "field", "relation", "concept", "topic", "lore", "source"})


@dataclass
class ParsedDocument:
    """A parsed .md file with metadata, content, and extracted wikilinks."""

    path: Path
    metadata: dict[str, Any]
    content: str
    doc_type: str | None = None
    wikilinks: list[str] = field(default_factory=list)

    @property
    def stem(self) -> str:
        """Identity stem: strips .md and optional __{type} suffix."""
        s = self.path.name.removesuffix(".md")
        if "__" in s:
            s = s.rsplit("__", 1)[0]
        return s


def extract_wikilinks(text: str) -> list[str]:
    """Extract all [[wikilink]] references from a string."""
    return WIKILINK_RE.findall(text)


def extract_wikilinks_from_value(value: Any) -> list[str]:
    """Recursively extract [[wikilinks]] from frontmatter values (dicts, lists, strings)."""
    if isinstance(value, str):
        return extract_wikilinks(value)
    if isinstance(value, list):
        results = []
        for item in value:
            results.extend(extract_wikilinks_from_value(item))
        return results
    if isinstance(value, dict):
        results = []
        for v in value.values():
            results.extend(extract_wikilinks_from_value(v))
        return results
    return []


UNQUOTED_WIKILINK_RE = re.compile(r"^(\s*\w+:\s*)(\[\[[^\]]+\]\])(.*)$", re.MULTILINE)


def _quote_wikilinks_in_frontmatter(text: str) -> str:
    """Quote unquoted [[wikilinks]] in YAML frontmatter so YAML doesn't parse them as lists.

    Transforms: `source: [[snowflake]]` → `source: "[[snowflake]]"`
    Leaves already-quoted values alone.
    """
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    fm = parts[1]
    fm = UNQUOTED_WIKILINK_RE.sub(r'\1"\2"\3', fm)
    return f"---{fm}---{parts[2]}"


def parse_file(path: Path) -> ParsedDocument:
    """Parse a .md file, extracting frontmatter, content, and all wikilinks."""
    raw_text = path.read_text(encoding="utf-8")
    fixed_text = _quote_wikilinks_in_frontmatter(raw_text)
    post = frontmatter.loads(fixed_text)
    metadata = dict(post.metadata)
    content = post.content

    # Extract wikilinks from both frontmatter values and body content
    all_links = extract_wikilinks_from_value(metadata) + extract_wikilinks(content)
    # Deduplicate while preserving order
    seen = set()
    unique_links = []
    for link in all_links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)

    doc_type = metadata.get("type")

    return ParsedDocument(
        path=path,
        metadata=metadata,
        content=content,
        doc_type=doc_type,
        wikilinks=unique_links,
    )
