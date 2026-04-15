"""Static validation checks for the Metalayer vault."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from metalayer.frontmatter import VALID_TYPES
from metalayer.resolver import Resolver


@dataclass
class ValidationIssue:
    file: str
    check: str
    message: str
    severity: Literal["error", "warning"]


def validate_vault(resolver: Resolver) -> list[ValidationIssue]:
    """Run all static validation checks on the vault. Returns a list of issues."""
    issues: list[ValidationIssue] = []
    issues.extend(_check_missing_type(resolver))
    issues.extend(_check_invalid_type(resolver))
    issues.extend(_check_dangling_refs(resolver))
    issues.extend(_check_circular_extends(resolver))
    issues.extend(_check_circular_metrics(resolver))
    issues.extend(_check_view_sources(resolver))
    issues.extend(_check_conflicting_context(resolver))
    return issues


def _check_missing_type(resolver: Resolver) -> list[ValidationIssue]:
    """Every .md file must have a type field in frontmatter."""
    issues = []
    for stem in resolver.all_stems():
        doc = resolver.get_document(stem)
        if doc and doc.doc_type is None:
            issues.append(ValidationIssue(
                file=stem,
                check="missing_type",
                message=f"{stem}: missing 'type' in frontmatter",
                severity="error",
            ))
    return issues


def _check_invalid_type(resolver: Resolver) -> list[ValidationIssue]:
    """Type must be one of the six valid types."""
    issues = []
    for stem in resolver.all_stems():
        doc = resolver.get_document(stem)
        if doc and doc.doc_type is not None and doc.doc_type not in VALID_TYPES:
            issues.append(ValidationIssue(
                file=stem,
                check="invalid_type",
                message=f"{stem}: invalid type '{doc.doc_type}' (must be one of {sorted(VALID_TYPES)})",
                severity="error",
            ))
    return issues


def _check_dangling_refs(resolver: Resolver) -> list[ValidationIssue]:
    """Every [[ref]] must resolve to an existing file in the vault."""
    issues = []
    for stem in resolver.all_stems():
        for link in resolver.get_links_from(stem):
            if resolver.resolve(link) is None:
                issues.append(ValidationIssue(
                    file=stem,
                    check="dangling_ref",
                    message=f"{stem}: [[{link}]] referenced but not found",
                    severity="error",
                ))
    return issues


def _unwrap_yaml_list(value: object) -> str | None:
    """Unwrap YAML's interpretation of [[name]] as a nested list [["name"]].

    Returns the bare string if unwrappable, None otherwise.
    """
    # [[name]] → [["name"]] in YAML
    if isinstance(value, list) and len(value) == 1:
        inner = value[0]
        if isinstance(inner, list) and len(inner) == 1 and isinstance(inner[0], str):
            return inner[0]
        if isinstance(inner, str):
            return inner
    return None


def _check_view_sources(resolver: Resolver) -> list[ValidationIssue]:
    """Every view must have a source that resolves to a source-type file."""
    issues = []
    from metalayer.frontmatter import extract_wikilinks
    sources = set(resolver.stems_by_type("source"))

    for stem in resolver.stems_by_type("view"):
        doc = resolver.get_document(stem)
        if doc is None:
            continue
        source_raw = doc.metadata.get("source")
        if source_raw is None:
            issues.append(ValidationIssue(
                file=stem,
                check="missing_source",
                message=f"{stem}: view is missing 'source' in frontmatter",
                severity="warning",
            ))
            continue
        refs = extract_wikilinks(str(source_raw))
        if not refs:
            # YAML may have parsed [[name]] as a nested list [["name"]].
            # Unwrap it to get the bare string.
            source_name = _unwrap_yaml_list(source_raw)
            if source_name is None:
                # source is a plain string, not a [[ref]] — warn but don't block
                continue
        else:
            source_name = refs[0]
        if source_name not in sources:
            source_doc = resolver.get_document(source_name)
            if source_doc is None:
                issues.append(ValidationIssue(
                    file=stem,
                    check="dangling_source",
                    message=f"{stem}: source [[{source_name}]] not found in vault",
                    severity="error",
                ))
            elif source_doc.doc_type != "source":
                issues.append(ValidationIssue(
                    file=stem,
                    check="invalid_source",
                    message=f"{stem}: source [[{source_name}]] exists but is type '{source_doc.doc_type}', not 'source'",
                    severity="error",
                ))

    return issues


def _check_circular_extends(resolver: Resolver) -> list[ValidationIssue]:
    """Detect cycles in concept extends chains."""
    issues = []
    concepts = resolver.stems_by_type("concept")

    for concept in concepts:
        visited: set[str] = set()
        current = concept
        while current:
            if current in visited:
                issues.append(ValidationIssue(
                    file=concept,
                    check="circular_extends",
                    message=f"{concept}: circular extends chain detected (loop includes {current})",
                    severity="error",
                ))
                break
            visited.add(current)
            doc = resolver.get_document(current)
            if doc is None:
                break
            extends_raw = doc.metadata.get("extends")
            if extends_raw is None:
                break
            # extends value is a [[ref]] string like "[[parent_concept]]"
            from metalayer.frontmatter import extract_wikilinks
            refs = extract_wikilinks(str(extends_raw))
            current = refs[0] if refs else None

    return issues


def _check_circular_metrics(resolver: Resolver) -> list[ValidationIssue]:
    """Detect cycles in metric composition (field SQL referencing other fields via [[]])."""
    issues = []
    metrics = resolver.stems_by_type("field")

    def _has_cycle(stem: str, visited: set[str]) -> str | None:
        """Return the stem that creates a cycle, or None."""
        if stem in visited:
            return stem
        visited.add(stem)
        doc = resolver.get_document(stem)
        if doc is None:
            return None
        sql = doc.metadata.get("sql", "")
        if not isinstance(sql, str):
            return None
        from metalayer.frontmatter import extract_wikilinks
        refs = extract_wikilinks(sql)
        for ref in refs:
            cycle = _has_cycle(ref, visited.copy())
            if cycle:
                return cycle
        return None

    for metric in metrics:
        doc = resolver.get_document(metric)
        if doc is None:
            continue
        sql = doc.metadata.get("sql", "")
        if not isinstance(sql, str):
            continue
        from metalayer.frontmatter import extract_wikilinks
        if extract_wikilinks(sql):
            cycle = _has_cycle(metric, set())
            if cycle:
                issues.append(ValidationIssue(
                    file=metric,
                    check="circular_metric",
                    message=f"{metric}: circular metric composition detected (loop includes {cycle})",
                    severity="error",
                ))

    return issues


def _check_conflicting_context(resolver: Resolver) -> list[ValidationIssue]:
    """Detect conflicts between vault files that could cause wrong SQL."""
    issues: list[ValidationIssue] = []
    issues.extend(_check_duplicate_fields(resolver))
    issues.extend(_check_relation_cardinality_conflicts(resolver))
    issues.extend(_check_overlapping_lore(resolver))
    issues.extend(_check_lore_bloat(resolver))
    return issues


def _check_duplicate_fields(resolver: Resolver) -> list[ValidationIssue]:
    """Two fields on the same view with the same SQL but different names, or same column different SQL."""
    issues = []
    from metalayer.frontmatter import extract_wikilinks_from_value

    # Group fields by view
    view_fields: dict[str, list[tuple[str, dict]]] = {}
    for stem in resolver.stems_by_type("field"):
        doc = resolver.get_document(stem)
        if doc is None:
            continue
        view_refs = extract_wikilinks_from_value(doc.metadata.get("view", ""))
        for view_ref in view_refs:
            view_fields.setdefault(view_ref, []).append((stem, doc.metadata))

    for view_name, fields in view_fields.items():
        # Check for same SQL on different fields
        sql_to_fields: dict[str, list[str]] = {}
        for stem, meta in fields:
            sql = meta.get("sql", "")
            if isinstance(sql, str) and sql.strip():
                normalized = sql.strip().lower()
                sql_to_fields.setdefault(normalized, []).append(stem)

        for sql, stems in sql_to_fields.items():
            if len(stems) > 1:
                issues.append(ValidationIssue(
                    file=stems[0],
                    check="duplicate_field_sql",
                    message=f"Fields {', '.join(stems)} on [[{view_name}]] have identical SQL — possible duplicate definitions",
                    severity="warning",
                ))

    return issues


def _check_relation_cardinality_conflicts(resolver: Resolver) -> list[ValidationIssue]:
    """Relations between the same views with conflicting cardinality."""
    issues = []
    from metalayer.frontmatter import extract_wikilinks_from_value

    # Build a map of view pairs to their relations
    pair_relations: dict[frozenset[str], list[tuple[str, str]]] = {}
    for stem in resolver.stems_by_type("relation"):
        doc = resolver.get_document(stem)
        if doc is None:
            continue
        from_refs = extract_wikilinks_from_value(doc.metadata.get("from", ""))
        to_refs = extract_wikilinks_from_value(doc.metadata.get("to", ""))
        cardinality = doc.metadata.get("cardinality", "")

        # Get parent views of the from/to fields
        from_views: set[str] = set()
        to_views: set[str] = set()
        for ref in from_refs:
            ref_doc = resolver.get_document(ref)
            if ref_doc and ref_doc.doc_type == "field":
                from_views.update(extract_wikilinks_from_value(ref_doc.metadata.get("view", "")))
            elif ref_doc and ref_doc.doc_type == "view":
                from_views.add(ref)
        for ref in to_refs:
            ref_doc = resolver.get_document(ref)
            if ref_doc and ref_doc.doc_type == "field":
                to_views.update(extract_wikilinks_from_value(ref_doc.metadata.get("view", "")))
            elif ref_doc and ref_doc.doc_type == "view":
                to_views.add(ref)

        for fv in from_views:
            for tv in to_views:
                pair = frozenset([fv, tv])
                pair_relations.setdefault(pair, []).append((stem, str(cardinality)))

    for pair, relations in pair_relations.items():
        if len(relations) <= 1:
            continue
        cardinalities = {card for _, card in relations}
        if len(cardinalities) > 1:
            names = [name for name, _ in relations]
            views = sorted(pair)
            issues.append(ValidationIssue(
                file=names[0],
                check="conflicting_cardinality",
                message=f"Relations between {views[0]} and {views[1]} disagree on cardinality: {', '.join(f'{n} ({c})' for n, c in relations)}",
                severity="warning",
            ))

    return issues


def _check_overlapping_lore(resolver: Resolver) -> list[ValidationIssue]:
    """Lore files with the same trigger that might give conflicting advice."""
    issues = []

    # Group lore by trigger
    trigger_to_lore: dict[str, list[str]] = {}
    for stem in resolver.stems_by_type("lore"):
        doc = resolver.get_document(stem)
        if doc is None:
            continue
        when = doc.metadata.get("when")
        if when is None:
            continue
        # Normalize trigger to a comparable string
        trigger_key = str(when).strip().lower()
        trigger_to_lore.setdefault(trigger_key, []).append(stem)

    for trigger, stems in trigger_to_lore.items():
        if len(stems) > 1:
            issues.append(ValidationIssue(
                file=stems[0],
                check="overlapping_lore",
                message=f"Lore files {', '.join(stems)} share the same trigger — check for conflicting advice",
                severity="warning",
            ))

    return issues


def _check_lore_bloat(resolver: Resolver) -> list[ValidationIssue]:
    """Too many always-lore files bloat every query's context."""
    issues = []
    always_lore: list[str] = []
    for stem in resolver.stems_by_type("lore"):
        doc = resolver.get_document(stem)
        if doc is None:
            continue
        if doc.metadata.get("when") == "always":
            always_lore.append(stem)

    if len(always_lore) > 5:
        issues.append(ValidationIssue(
            file=always_lore[0],
            check="lore_bloat",
            message=f"{len(always_lore)} always-lore files ({', '.join(always_lore)}) — each one bloats every query's context. Consider narrowing triggers.",
            severity="warning",
        ))

    return issues
