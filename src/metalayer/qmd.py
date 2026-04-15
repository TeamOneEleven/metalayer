"""Helpers for invoking QMD with consistent error handling."""

from __future__ import annotations

import subprocess
from pathlib import Path

QMD_NOT_FOUND = "QMD not found — install with: npm install @tobilu/qmd"

# Use npx to resolve project-local QMD, avoiding global collisions.
QMD_CMD = ["npx", "--yes", "@tobilu/qmd"]


def qmd_command(*args: str) -> list[str]:
    """Build a QMD command with the correct prefix."""
    return [*QMD_CMD, *args]


def run_qmd_command(cmd: list[str], *, cwd: Path, timeout: int) -> str | None:
    """Run a QMD command and return an error message on failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
        )
    except FileNotFoundError:
        return QMD_NOT_FOUND
    except subprocess.TimeoutExpired:
        return f"{' '.join(cmd)} timed out after {timeout}s"

    if result.returncode == 0:
        return None

    detail = (
        result.stderr.strip()
        or result.stdout.strip()
        or f"exited with code {result.returncode}"
    )
    return f"{' '.join(cmd)} failed: {detail}"
