"""SQL execution tool: passthrough to warehouse."""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any

ALLOWED_QUERY_START = frozenset({"describe", "desc", "explain", "select", "show", "with"})
FORBIDDEN_SQL_KEYWORDS = frozenset({
    "alter",
    "call",
    "copy",
    "create",
    "delete",
    "drop",
    "grant",
    "insert",
    "merge",
    "put",
    "remove",
    "replace",
    "revoke",
    "truncate",
    "undrop",
    "update",
})

BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
LINE_COMMENT_RE = re.compile(r"--[^\n]*")
SINGLE_QUOTE_RE = re.compile(r"'(?:''|[^'])*'")
DOUBLE_QUOTE_RE = re.compile(r'"(?:[^"]|"")*"')


def _sanitize_sql(sql: str) -> str:
    """Strip comments and quoted strings before safety checks."""
    stripped = BLOCK_COMMENT_RE.sub(" ", sql)
    stripped = LINE_COMMENT_RE.sub(" ", stripped)
    stripped = SINGLE_QUOTE_RE.sub("''", stripped)
    stripped = DOUBLE_QUOTE_RE.sub('""', stripped)
    return stripped


def _first_keyword(sql: str) -> str | None:
    """Return the first SQL keyword from a sanitized statement."""
    match = re.match(r"\s*([a-zA-Z]+)", sql)
    if match is None:
        return None
    return match.group(1).lower()


def _validate_sql(sql: str) -> str | None:
    """Reject destructive or non-read-only SQL."""
    if not sql.strip():
        return "SQL is empty"

    if ";" in sql.strip().rstrip(";"):
        return "Only a single SQL statement is allowed"

    sanitized = _sanitize_sql(sql)
    first_keyword = _first_keyword(sanitized)
    if first_keyword not in ALLOWED_QUERY_START:
        return "Only read-only SQL statements are allowed"

    blocked = sorted({
        keyword
        for keyword in FORBIDDEN_SQL_KEYWORDS
        if re.search(rf"\b{keyword}\b", sanitized, flags=re.IGNORECASE)
    })
    if blocked:
        return f"Read-only SQL only; blocked keyword(s): {', '.join(blocked)}"

    return None


def execute_sql(sql: str, limit: int = 100) -> dict[str, Any]:
    """Execute SQL against the warehouse.

    This is a passthrough — it calls whatever warehouse tool is configured
    in the agent platform (e.g., Snowflake MCP, a CLI tool, etc.).

    For now, this shells out to a configurable command. The actual warehouse
    connection is owned by the agent platform, not by Metalayer.
    """
    validation_error = _validate_sql(sql)
    if validation_error is not None:
        return {"error": validation_error}

    # Apply limit if not already present
    sql_trimmed = sql.strip().rstrip(";")
    sanitized_sql = _sanitize_sql(sql_trimmed)
    first_keyword = _first_keyword(sanitized_sql)

    if first_keyword in {"select", "with"} and "limit" not in sanitized_sql.lower():
        sql_with_limit = f"{sql_trimmed}\nLIMIT {limit}"
    else:
        sql_with_limit = sql_trimmed

    # Try snowsql as a default warehouse CLI
    # This should be made configurable — for now it's a reasonable default
    cmd = ["snowsql", "-q", sql_with_limit, "-o", "output_format=json", "-o", "friendly=false"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return {"error": f"SQL execution failed: {result.stderr.strip()}"}
        try:
            rows = json.loads(result.stdout)
            return {
                "columns": list(rows[0].keys()) if rows else [],
                "rows": rows,
                "row_count": len(rows),
            }
        except (json.JSONDecodeError, IndexError):
            return {"raw_output": result.stdout.strip()}
    except FileNotFoundError:
        return {
            "error": (
                "No warehouse CLI found. Configure your warehouse connection in the "
                "agent platform."
            )
        }
    except subprocess.TimeoutExpired:
        return {"error": "SQL execution timed out (120s)"}
