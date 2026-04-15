"""Metalayer CLI — the primary interface for humans and agents."""

from __future__ import annotations

import json
from pathlib import Path

import click

from metalayer.config import (
    MetalayerConfig,
    find_project_root,
    load_config,
)
from metalayer.qmd import QMD_NOT_FOUND, qmd_command, run_qmd_command
from metalayer.resolver import Resolver
from metalayer.resources import copy_bundled_markdown


def _get_context_objects(
    config: MetalayerConfig,
    project_root: Path,
) -> tuple[Resolver, MetalayerConfig, Path]:
    """Load config, build resolver, return all three."""
    resolver = Resolver(project_root / config.context_path)
    resolver.scan()
    return resolver, config, project_root


@click.group()
def main():
    """Metalayer — a self-learning context layer for LLM analytics."""
    pass


@main.command()
@click.option("--root", type=click.Path(exists=False), default=".", help="Project root directory")
def init(root: str):
    """Initialize a new Metalayer project."""
    project_root = Path(root).resolve()

    # Create directory structure
    dirs = [
        "context/sources",
        "context/views",
        "context/fields",
        "context/relations",
        "context/concepts",
        "context/topics",
        "context/lore",
        "utils/imports",
        "utils/queries",
        "skills",
    ]
    for d in dirs:
        (project_root / d).mkdir(parents=True, exist_ok=True)
        click.echo(f"  Created {d}/")

    # Copy default config if not present
    config_path = project_root / "config.yaml"
    if not config_path.exists():
        # Write default config
        config_path.write_text("""# Metalayer configuration

# Paths (relative to project root)
context_path: ./context
utils_path: ./utils

# QMD search configuration
qmd:
  collections:
    vault:
      path: ./context
      mask: "**/*.md"
    queries:
      path: ./utils/queries
      mask: "**/*.md"

# Query memory
query_memory:
  ring_buffer_size: 500

# SQL consensus
consensus:
  sub_agents: 5
  max_rounds: 3
""")
        click.echo("  Created config.yaml")

    for skill_name in copy_bundled_markdown("skills", project_root / "skills"):
        click.echo(f"  Copied skills/{skill_name}")
    for import_name in copy_bundled_markdown("imports", project_root / "utils" / "imports"):
        click.echo(f"  Copied utils/imports/{import_name}")

    # Create default lore files if not present
    sql_style = project_root / "context" / "lore" / "sql_style.md"
    if not sql_style.exists():
        sql_style.write_text("""---
type: lore
when: always
---

# SQL Style

Write clean, readable SQL:
- Use CTEs (WITH clauses), not nested subqueries
- Always qualify column names with table aliases
- Use meaningful alias names (o for orders, c for customers)
- Prefer explicit JOINs over implicit comma joins
- Write JOIN conditions in the ON clause, not WHERE
- Put each major clause on its own line
- Use single quotes for string literals
- Use ISO date format (YYYY-MM-DD) for date literals
- Apply LIMIT unless the user specifically asks for all rows
""")
        click.echo("  Created context/lore/sql_style.md")

    vault_overview = project_root / "context" / "lore" / "vault_overview.md"
    if not vault_overview.exists():
        vault_overview.write_text("""---
type: lore
when: always
---

# Vault Overview

This vault is empty.
Run `metalayer update-from` to import your first context, or create .md files manually.
""")
        click.echo("  Created context/lore/vault_overview.md")

    # Install QMD via npm if package.json exists
    package_json = project_root / "package.json"
    if package_json.exists():
        click.echo("\nInstalling QMD...")
        import subprocess
        try:
            result = subprocess.run(
                ["npm", "install"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(project_root),
            )
            if result.returncode == 0:
                click.echo("  QMD installed via npm")
            else:
                click.echo(click.style(f"  Warning: npm install failed: {result.stderr.strip()}", fg="yellow"))
        except FileNotFoundError:
            click.echo(click.style("  Warning: npm not found — install Node.js to use QMD search", fg="yellow"))
        except subprocess.TimeoutExpired:
            click.echo(click.style("  Warning: npm install timed out", fg="yellow"))

    # Configure QMD collections
    click.echo("\nConfiguring QMD...")
    qmd_errors: list[str] = []
    for cmd, timeout in (
        (
            qmd_command(
                "collection",
                "add",
                str(project_root / "context"),
                "--name",
                "vault",
                "--mask",
                "**/*.md",
            ),
            30,
        ),
        (
            qmd_command(
                "collection",
                "add",
                str(project_root / "utils" / "queries"),
                "--name",
                "queries",
                "--mask",
                "**/*.md",
            ),
            30,
        ),
        (qmd_command("embed"), 120),
    ):
        error = run_qmd_command(cmd, cwd=project_root, timeout=timeout)
        if error is None:
            continue
        if error == QMD_NOT_FOUND:
            qmd_errors.append("QMD not found — install QMD for search capabilities")
            break
        qmd_errors.append(error)

    if qmd_errors:
        for error in qmd_errors:
            click.echo(click.style(f"  Warning: {error}", fg="yellow"))
    else:
        click.echo("  QMD collections configured")

    click.echo("\nMetalayer initialized. Next steps:")
    click.echo("  1. metalayer update-from warehouse_history  (bootstrap from query history)")
    click.echo("  2. metalayer validate                       (check vault integrity)")
    click.echo("  3. Start asking questions!                  (use the ask_data skill)")


@main.command()
def validate():
    """Run static validation checks on the vault."""
    project_root = find_project_root()
    config = load_config()
    resolver, _, _ = _get_context_objects(config, project_root)

    from metalayer.validation import validate_vault
    issues = validate_vault(resolver)

    # Print counts
    counts: dict[str, int] = {}
    for doc_type in ["source", "view", "field", "relation", "concept", "topic", "lore"]:
        counts[doc_type] = len(resolver.stems_by_type(doc_type))

    parts = [f"{count} {t}s" for t, count in counts.items() if count > 0]
    if parts:
        click.echo(f"  {', '.join(parts)}")
    else:
        click.echo("  Empty vault")

    # Print issues
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    for issue in errors:
        click.echo(click.style(f"  \u2717 {issue.message}", fg="red"))
    for issue in warnings:
        click.echo(click.style(f"  \u26a0 {issue.message}", fg="yellow"))

    if not issues:
        click.echo(click.style("  \u2713 All checks passed", fg="green"))

    raise SystemExit(1 if errors else 0)


@main.command("update-from")
@click.argument("source")
@click.option("--instructions", "-i", default=None, help="Additional instructions for the import")
def update_from(source: str, instructions: str | None):
    """Load an import preset and print it for the LLM to process."""
    project_root = find_project_root()

    from metalayer.tools.sync import update_from as _update_from
    result = _update_from(source, instructions, project_root)

    if "error" in result:
        click.echo(click.style(f"Error: {result['error']}", fg="red"))
        if result.get("available"):
            click.echo(f"Available presets: {', '.join(result['available'])}")
        raise SystemExit(1)

    click.echo(result["preset"])
    if result.get("instructions"):
        click.echo(f"\n---\nAdditional instructions: {result['instructions']}")


@main.command("get-context")
@click.argument("name")
def get_context_cmd(name: str):
    """Read a context file by stem name with its links."""
    project_root = find_project_root()
    config = load_config()
    resolver, _, _ = _get_context_objects(config, project_root)

    from metalayer.tools.context import get_context
    result = get_context(name, resolver)

    if "error" in result:
        click.echo(click.style(f"Error: {result['error']}", fg="red"))
        raise SystemExit(1)

    click.echo(json.dumps(result, indent=2, default=str))


@main.command("get-topic")
@click.argument("name")
def get_topic_cmd(name: str):
    """Resolve a topic to all its constituent files."""
    project_root = find_project_root()
    config = load_config()
    resolver, _, _ = _get_context_objects(config, project_root)

    from metalayer.tools.topic import get_topic
    result = get_topic(name, resolver)

    if "error" in result:
        click.echo(click.style(f"Error: {result['error']}", fg="red"))
        raise SystemExit(1)

    click.echo(json.dumps(result, indent=2, default=str))


@main.command("search")
@click.argument("query")
def search_cmd(query: str):
    """Search the vault via QMD."""
    from metalayer.tools.context import search_context
    result = search_context(query)

    if "error" in result:
        click.echo(click.style(f"Error: {result['error']}", fg="red"))
        raise SystemExit(1)

    if isinstance(result.get("results"), str):
        click.echo(result["results"])
    else:
        click.echo(json.dumps(result["results"], indent=2))


@main.command("audit")
@click.option("--change-path", default=None, help="Path of proposed file")
@click.option("--change-content", default=None, help="Content of proposed file")
def audit_cmd(change_path: str | None, change_content: str | None):
    """Run a context audit on the vault or a proposed change."""
    project_root = find_project_root()
    config = load_config()
    resolver, _, _ = _get_context_objects(config, project_root)

    from metalayer.tools.audit import context_audit

    change = None
    if change_path and change_content:
        change = {"path": change_path, "content": change_content}

    result = context_audit(resolver, change)
    click.echo(json.dumps(result, indent=2))

    if result["status"] == "block":
        raise SystemExit(1)


@main.command("log-query")
@click.option("--question", "-q", required=True, help="The user's original question")
@click.option("--sql", "-s", required=True, help="The executed SQL")
@click.option("--summary", "-r", required=True, help="Result summary")
@click.option("--in-model", "-i", multiple=True, help="Vault objects used (repeatable)")
@click.option("--not-in-model", "-n", multiple=True, help="Raw columns/tables used without vault files (repeatable)")
@click.option("--consensus-notes", "-c", default="", help="Notes from consensus phase")
def log_query_cmd(
    question: str,
    sql: str,
    summary: str,
    in_model: tuple[str, ...],
    not_in_model: tuple[str, ...],
    consensus_notes: str,
):
    """Log a completed query, detect vault gaps, and output proposed updates."""
    project_root = find_project_root()
    config = load_config()

    from metalayer.query_memory import QueryMemory
    qm = QueryMemory(project_root / config.utils_path / "queries", config.query_memory.ring_buffer_size)
    path = qm.write(
        question=question,
        sql=sql,
        result_summary=summary,
        objects_in=list(in_model),
        objects_not_in=list(not_in_model),
    )
    click.echo(f"Logged as {path.name}")

    # === GAP ANALYSIS ===
    # Check not_in_model items against the vault and propose concrete updates.
    resolver = Resolver(project_root / config.context_path)
    resolver.scan()

    missing_fields: list[str] = []
    missing_views: list[str] = []
    missing_other: list[str] = []

    for item in not_in_model:
        if resolver.resolve(item) is not None:
            continue  # already in vault
        if "." in item:
            # Looks like view.column — propose a field
            missing_fields.append(item)
        else:
            # Could be a view or a raw table name
            missing_views.append(item)

    # Check in_model items for joins that have no relation file
    in_model_list = list(in_model)
    used_views: set[str] = set()
    for item in in_model_list:
        doc = resolver.get_document(item)
        if doc and doc.doc_type == "view":
            used_views.add(item)

    missing_relations: list[tuple[str, str]] = []
    if len(used_views) > 1:
        relations = resolver.stems_by_type("relation")
        relation_pairs: set[frozenset[str]] = set()
        for rel_stem in relations:
            rel_doc = resolver.get_document(rel_stem)
            if rel_doc:
                from metalayer.frontmatter import extract_wikilinks_from_value
                from_refs = extract_wikilinks_from_value(rel_doc.metadata.get("from", ""))
                to_refs = extract_wikilinks_from_value(rel_doc.metadata.get("to", ""))
                # Get the parent views of these fields
                for fr in from_refs:
                    fr_doc = resolver.get_document(fr)
                    if fr_doc:
                        from_view_refs = extract_wikilinks_from_value(fr_doc.metadata.get("view", ""))
                        for tr in to_refs:
                            tr_doc = resolver.get_document(tr)
                            if tr_doc:
                                to_view_refs = extract_wikilinks_from_value(tr_doc.metadata.get("view", ""))
                                for fv in from_view_refs:
                                    for tv in to_view_refs:
                                        relation_pairs.add(frozenset([fv, tv]))

        used_view_list = sorted(used_views)
        for i, v1 in enumerate(used_view_list):
            for v2 in used_view_list[i + 1:]:
                pair = frozenset([v1, v2])
                if pair not in relation_pairs:
                    missing_relations.append((v1, v2))

    has_gaps = missing_fields or missing_views or missing_relations

    if not has_gaps:
        click.echo(click.style("\nNo vault gaps detected.", fg="green"))
        return

    # Output concrete gap analysis
    click.echo("")
    click.echo("=" * 60)
    click.echo("  VAULT GAPS DETECTED")
    click.echo("=" * 60)

    if missing_fields:
        click.echo(f"\n  Missing fields ({len(missing_fields)}):")
        for f in missing_fields:
            parts = f.split(".", 1)
            view_name = parts[0]
            field_name = parts[1] if len(parts) > 1 else f
            click.echo(f"    - {f}")
            click.echo(f"      Proposed file: context/fields/{f}__field.md")
            click.echo(f"      view: \"[[{view_name}]]\"")
            click.echo(f"      sql: ${{TABLE}}.{field_name}")

    if missing_views:
        click.echo(f"\n  Missing views ({len(missing_views)}):")
        for v in missing_views:
            click.echo(f"    - {v}")
            click.echo(f"      Proposed file: context/views/{v}__view.md")

    if missing_relations:
        click.echo(f"\n  Missing relations ({len(missing_relations)}):")
        for v1, v2 in missing_relations:
            click.echo(f"    - {v1} <-> {v2}")
            click.echo(f"      Proposed file: context/relations/{v1}_to_{v2}__relation.md")

    click.echo(f"\n  Total gaps: {len(missing_fields)} fields, {len(missing_views)} views, {len(missing_relations)} relations")
    click.echo("")
    click.echo("  ACTION REQUIRED: Verify each gap against real data, then create")
    click.echo("  the proposed files. Read skills/learn.md for the full workflow.")
    click.echo("  Launch a learning subagent (Agent tool) with these gaps.")
    click.echo("=" * 60)


@main.command("answer-card")
@click.option("--question", "-q", required=True, help="The user's original question")
@click.option("--known", "-k", multiple=True, help="Known field lines (repeatable, e.g. 'login' '  ↳ timestamp')")
@click.option("--new", "-n", multiple=True, help="New field lines (repeatable)")
@click.option("--source", "-s", required=True, help="Source name")
@click.option("--join", "-j", multiple=True, help="Join descriptions (repeatable)")
@click.option("--lore", "-l", multiple=True, help="Lore names applied (repeatable)")
@click.option("--notes", default=None, help="Methodology notes")
def answer_card_cmd(
    question: str,
    known: tuple[str, ...],
    new: tuple[str, ...],
    source: str,
    join: tuple[str, ...],
    lore: tuple[str, ...],
    notes: str | None,
):
    """Render an answer card with perfectly aligned ASCII borders."""
    from metalayer.answer_card import render_card
    card = render_card(
        question=question,
        known_fields=list(known),
        new_fields=list(new),
        source=source,
        joins=list(join),
        lore=list(lore),
        notes=notes,
    )
    click.echo(card)


@main.command("frequent")
@click.option("--limit", "-l", default=10, help="Number of top items to show")
def frequent_cmd(limit: int):
    """Show the most frequently used vault objects from query memory."""
    project_root = find_project_root()
    config = load_config()
    queries_path = project_root / config.utils_path / "queries"

    if not queries_path.exists():
        click.echo("No query memory yet.")
        return

    import frontmatter
    from collections import Counter

    counts: Counter[str] = Counter()
    query_files = sorted(queries_path.glob("q*.md"))

    for qf in query_files:
        post = frontmatter.load(str(qf))
        for ref in post.metadata.get("objects_in_data_model", []):
            # Strip [[ ]] wrappers if present
            clean = ref.strip().removeprefix("[[").removesuffix("]]")
            if clean:
                counts[clean] += 1

    if not counts:
        click.echo("No vault objects referenced in query memory yet.")
        return

    click.echo(f"Most used vault objects (from {len(query_files)} queries):\n")
    for name, count in counts.most_common(limit):
        click.echo(f"  {count:3d}x  {name}")


@main.command("sync")
def sync_cmd():
    """Re-index QMD, rebuild resolver, regenerate meta-lore, run validation."""
    project_root = find_project_root()
    config = load_config()
    resolver = Resolver(project_root / config.context_path)
    resolver.scan()

    from metalayer.tools.sync import sync_context
    result = sync_context(resolver, config, project_root)

    click.echo(f"  Synced: {result['stems']} files indexed")
    for error in result.get("errors", []):
        click.echo(click.style(f"  \u26a0 {error}", fg="yellow"))
    for issue in result.get("issues", []):
        severity = issue["severity"]
        symbol = "\u2717" if severity == "error" else "\u26a0"
        color = "red" if severity == "error" else "yellow"
        click.echo(click.style(f"  {symbol} {issue['message']}", fg=color))

    if not result.get("issues"):
        click.echo(click.style("  \u2713 All checks passed", fg="green"))
