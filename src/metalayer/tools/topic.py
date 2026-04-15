"""Topic tool: deep resolver for topics -> concepts -> fields -> views -> relations."""

from __future__ import annotations

from typing import Any

from metalayer.frontmatter import extract_wikilinks_from_value
from metalayer.resolver import Resolver


def get_topic(name: str, resolver: Resolver) -> dict[str, Any]:
    """Resolve a topic to all its constituent files.

    Resolution chain: topic -> concepts -> extends chains -> fields -> views -> relations.
    Returns all resolved files as a structured dict.
    """
    topic_doc = resolver.get_document(name)
    if topic_doc is None:
        return {"error": f"Topic '{name}' not found in vault"}
    if topic_doc.doc_type != "topic":
        return {"error": f"'{name}' is type '{topic_doc.doc_type}', not 'topic'"}

    collected: dict[str, dict[str, Any]] = {}
    concepts: list[str] = []
    fields: list[str] = []
    views: list[str] = []
    relations: list[str] = []

    # Collect the topic itself
    collected[name] = _doc_to_dict(name, resolver)

    # Resolve concepts from topic frontmatter
    topic_concepts = _extract_refs(topic_doc.metadata.get("concepts", []))
    topic_relations = _extract_refs(topic_doc.metadata.get("relations", []))
    topic_views = _extract_refs(topic_doc.metadata.get("views", []))

    # Follow concept extends chains
    all_concepts: set[str] = set()
    for concept_name in topic_concepts:
        _resolve_extends_chain(concept_name, resolver, all_concepts)

    concepts = sorted(all_concepts)

    # Collect fields from all concepts
    all_fields: set[str] = set()
    for concept_name in concepts:
        concept_doc = resolver.get_document(concept_name)
        if concept_doc:
            collected[concept_name] = _doc_to_dict(concept_name, resolver)
            concept_fields = _extract_refs(concept_doc.metadata.get("fields", []))
            all_fields.update(concept_fields)

    fields = sorted(all_fields)

    # Collect parent views from fields
    all_views: set[str] = set(topic_views)
    for field_name in fields:
        field_doc = resolver.get_document(field_name)
        if field_doc:
            collected[field_name] = _doc_to_dict(field_name, resolver)
            view_refs = _extract_refs(field_doc.metadata.get("view", ""))
            all_views.update(view_refs)

    views = sorted(all_views)

    # Collect views
    for view_name in views:
        if view_name not in collected:
            view_doc = resolver.get_document(view_name)
            if view_doc:
                collected[view_name] = _doc_to_dict(view_name, resolver)

    # Collect relations
    all_relations: set[str] = set(topic_relations)
    relations = sorted(all_relations)
    for rel_name in relations:
        if rel_name not in collected:
            rel_doc = resolver.get_document(rel_name)
            if rel_doc:
                collected[rel_name] = _doc_to_dict(rel_name, resolver)

    return {
        "topic": name,
        "concepts": concepts,
        "fields": fields,
        "views": views,
        "relations": relations,
        "files": collected,
    }


def _resolve_extends_chain(
    concept_name: str,
    resolver: Resolver,
    collected: set[str],
) -> None:
    """Follow extends chain for a concept, collecting all ancestors."""
    if concept_name in collected:
        return
    collected.add(concept_name)

    doc = resolver.get_document(concept_name)
    if doc is None:
        return

    extends_raw = doc.metadata.get("extends")
    if extends_raw is None:
        return

    parent_refs = _extract_refs(extends_raw)
    for parent in parent_refs:
        _resolve_extends_chain(parent, resolver, collected)


def _extract_refs(value: Any) -> list[str]:
    """Extract wikilink references from a frontmatter value."""
    if value is None:
        return []
    return extract_wikilinks_from_value(value)


def _doc_to_dict(name: str, resolver: Resolver) -> dict[str, Any]:
    """Convert a document to a simple dict for output."""
    doc = resolver.get_document(name)
    if doc is None:
        return {"error": f"not found: {name}"}
    return {
        "name": name,
        "type": doc.doc_type,
        "metadata": doc.metadata,
        "content": doc.content,
        "links_from": sorted(resolver.get_links_from(name)),
        "links_to": sorted(resolver.get_links_to(name)),
    }
