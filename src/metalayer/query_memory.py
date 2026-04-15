"""Query memory: write, read, and rotate query result files."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import frontmatter


class QueryMemory:
    """Manages the query memory ring buffer in utils/queries/."""

    def __init__(self, queries_path: Path, max_files: int = 500):
        self.queries_path = queries_path
        self.max_files = max_files

    def write(
        self,
        question: str,
        sql: str,
        result_summary: str,
        objects_in: list[str] | None = None,
        objects_not_in: list[str] | None = None,
        accepted: bool = False,
    ) -> Path:
        """Write a query result to a new .md file. Returns the path."""
        self.queries_path.mkdir(parents=True, exist_ok=True)

        number = self._next_number()
        filename = f"q{number:05d}.md"
        path = self.queries_path / filename

        metadata = {
            "status": "success",
            "accepted": accepted,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "objects_in_data_model": [f"[[{ref}]]" for ref in (objects_in or [])],
            "objects_not_in_data_model": objects_not_in or [],
        }

        content = f"# {question}\n\n```sql\n{sql}\n```\n\n{result_summary}"

        post = frontmatter.Post(content, **metadata)
        path.write_text(frontmatter.dumps(post))

        self.rotate()
        return path

    def rotate(self) -> None:
        """Remove oldest non-accepted files if over the buffer limit."""
        all_files = self._list_query_files()
        non_accepted = []
        for path in all_files:
            post = frontmatter.load(str(path))
            if not post.metadata.get("accepted", False):
                non_accepted.append(path)

        # Delete oldest non-accepted files to get under the limit
        accepted_count = len(all_files) - len(non_accepted)
        max_non_accepted = self.max_files - accepted_count
        if len(non_accepted) > max_non_accepted:
            to_delete = non_accepted[:len(non_accepted) - max_non_accepted]
            for path in to_delete:
                path.unlink()

    def list_queries(self, accepted_only: bool = False) -> list[Path]:
        """List query files, optionally filtering to accepted only."""
        files = self._list_query_files()
        if not accepted_only:
            return files
        result = []
        for path in files:
            post = frontmatter.load(str(path))
            if post.metadata.get("accepted", False):
                result.append(path)
        return result

    def _next_number(self) -> int:
        """Get the next sequential number for a query file."""
        files = self._list_query_files()
        if not files:
            return 1
        # Extract numbers from filenames like q00001.md
        numbers = []
        for f in files:
            stem = f.stem  # e.g. "q00001"
            try:
                numbers.append(int(stem[1:]))  # strip the 'q' prefix
            except (ValueError, IndexError):
                continue
        return max(numbers, default=0) + 1

    def _list_query_files(self) -> list[Path]:
        """List all query files sorted by name (oldest first)."""
        if not self.queries_path.exists():
            return []
        return sorted(self.queries_path.glob("q*.md"))
