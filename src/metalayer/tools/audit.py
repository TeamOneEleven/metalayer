"""Audit tools: context_audit, validate_refs."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from metalayer.paths import CONTEXT_WRITE_ROOTS, resolve_project_path
from metalayer.resolver import DuplicateStemError, Resolver
from metalayer.validation import validate_vault


def context_audit(
    resolver: Resolver,
    change: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run validation on the vault, or preflight-check a proposed change.

    Without args: full vault static checks.
    With change={'path': '...', 'content': '...'}: check proposed content against the vault.
    """
    if change is None:
        return _full_audit(resolver)
    return _preflight_audit(resolver, change)


def validate_refs(refs: list[str], resolver: Resolver) -> dict[str, Any]:
    """Check that every [[ref]] resolves to an existing file in the vault."""
    valid = []
    invalid = []
    for ref in refs:
        if resolver.resolve(ref) is not None:
            valid.append(ref)
        else:
            invalid.append(ref)

    return {
        "valid": valid,
        "invalid": invalid,
        "all_valid": len(invalid) == 0,
    }


def _full_audit(resolver: Resolver) -> dict[str, Any]:
    """Run full vault validation."""
    issues = validate_vault(resolver)

    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    if errors:
        status = "block"
    elif warnings:
        status = "warn"
    else:
        status = "clean"

    return {
        "status": status,
        "issues": [
            {"file": i.file, "check": i.check, "message": i.message, "severity": i.severity}
            for i in issues
        ],
        "summary": {
            "errors": len(errors),
            "warnings": len(warnings),
        },
    }


def _preflight_audit(
    resolver: Resolver,
    change: dict[str, str],
) -> dict[str, Any]:
    """Check a proposed change against the existing vault."""
    path_str = change.get("path", "")
    content = change.get("content", "")
    project_root = resolver.vault_path.parent

    try:
        resolved_change_path = resolve_project_path(
            project_root,
            path_str,
            allowed_roots=CONTEXT_WRITE_ROOTS,
        )
    except ValueError as exc:
        return {
            "status": "block",
            "issues": [{
                "check": "invalid_path",
                "message": str(exc),
                "severity": "error",
            }],
        }

    baseline_issues = _issues_to_dicts(validate_vault(resolver))
    baseline_issue_keys = {_issue_key(issue) for issue in baseline_issues}

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        temp_context_path = temp_root / resolver.vault_path.name
        if resolver.vault_path.exists():
            shutil.copytree(resolver.vault_path, temp_context_path)
        else:
            temp_context_path.mkdir(parents=True, exist_ok=True)

        relative_change_path = resolved_change_path.relative_to(project_root)
        temp_change_path = temp_root / relative_change_path
        temp_change_path.parent.mkdir(parents=True, exist_ok=True)
        temp_change_path.write_text(content, encoding="utf-8")

        temp_resolver = Resolver(temp_context_path)
        try:
            temp_resolver.scan()
            proposed_issues = _issues_to_dicts(validate_vault(temp_resolver))
        except DuplicateStemError as exc:
            proposed_issues = [{
                "file": exc.stem,
                "check": "duplicate_stem",
                "message": str(exc),
                "severity": "error",
            }]
        except Exception as exc:
            proposed_issues = [{
                "file": temp_change_path.name.removesuffix(".md"),
                "check": "parse_error",
                "message": f"Unable to parse proposed file: {exc}",
                "severity": "error",
            }]

    issues = [
        issue for issue in proposed_issues
        if _issue_key(issue) not in baseline_issue_keys
    ]

    errors = [i for i in issues if i["severity"] == "error"]
    if errors:
        status = "block"
    elif issues:
        status = "warn"
    else:
        status = "clean"

    return {
        "status": status,
        "issues": issues,
    }


def _issues_to_dicts(issues: list[Any]) -> list[dict[str, str]]:
    """Normalize validation issues into serializable dicts."""
    return [
        {"file": i.file, "check": i.check, "message": i.message, "severity": i.severity}
        for i in issues
    ]


def _issue_key(issue: dict[str, str]) -> tuple[str, str, str, str]:
    """Build a stable comparison key for validation issues."""
    return (
        issue.get("file", ""),
        issue.get("check", ""),
        issue.get("message", ""),
        issue.get("severity", ""),
    )
