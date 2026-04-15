"""Vault resolver: filename-to-path index, forward links, and backlinks."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from metalayer.frontmatter import ParsedDocument, parse_file


class DuplicateStemError(Exception):
    """Raised when two .md files in the vault share the same stem."""

    def __init__(self, stem: str, path1: Path, path2: Path):
        self.stem = stem
        self.path1 = path1
        self.path2 = path2
        super().__init__(
            f"Duplicate stem '{stem}': {path1} and {path2}"
        )


def _filename_to_stem(filename: str) -> str:
    """Extract the identity stem from a filename.

    Strips the .md extension and the optional __{type} suffix.
    Examples:
        orders__view.md        → orders
        orders.revenue__field.md → orders.revenue
        snowflake__source.md   → snowflake
        old_style.md           → old_style  (no __ suffix, still works)
    """
    stem = filename.removesuffix(".md")
    if "__" in stem:
        stem = stem.rsplit("__", 1)[0]
    return stem


class Resolver:
    """Indexes a vault of .md files by stem name with forward/back link tracking."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.stem_to_path: dict[str, Path] = {}
        self.forward_links: dict[str, set[str]] = defaultdict(set)
        self.backlinks: dict[str, set[str]] = defaultdict(set)
        self._parsed_cache: dict[str, ParsedDocument] = {}

    def scan(self) -> None:
        """Walk the vault recursively, build all indexes."""
        self.stem_to_path.clear()
        self.forward_links.clear()
        self.backlinks.clear()
        self._parsed_cache.clear()

        if not self.vault_path.exists():
            return

        # Pass 1: build stem-to-path index
        for md in self.vault_path.rglob("*.md"):
            stem = _filename_to_stem(md.name)
            if stem in self.stem_to_path:
                raise DuplicateStemError(stem, self.stem_to_path[stem], md)
            self.stem_to_path[stem] = md

        # Pass 2: parse files, build link indexes
        for stem, path in self.stem_to_path.items():
            doc = parse_file(path)
            self._parsed_cache[stem] = doc
            for link in doc.wikilinks:
                self.forward_links[stem].add(link)
                self.backlinks[link].add(stem)

    def resolve(self, name: str) -> Path | None:
        """Look up a stem name, return its file path or None."""
        return self.stem_to_path.get(name)

    def get_links_from(self, name: str) -> set[str]:
        """Get all stems this file links to (forward links)."""
        return set(self.forward_links.get(name, set()))

    def get_links_to(self, name: str) -> set[str]:
        """Get all stems that link to this file (backlinks)."""
        return set(self.backlinks.get(name, set()))

    def get_document(self, name: str) -> ParsedDocument | None:
        """Get the parsed document for a stem name."""
        if name in self._parsed_cache:
            return self._parsed_cache[name]
        path = self.resolve(name)
        if path is None:
            return None
        doc = parse_file(path)
        self._parsed_cache[name] = doc
        return doc

    def all_stems(self) -> list[str]:
        """Return all known stems, sorted."""
        return sorted(self.stem_to_path.keys())

    def stems_by_type(self, doc_type: str) -> list[str]:
        """Return stems filtered by frontmatter type, sorted."""
        results = []
        for stem in sorted(self.stem_to_path.keys()):
            doc = self.get_document(stem)
            if doc and doc.doc_type == doc_type:
                results.append(stem)
        return results
