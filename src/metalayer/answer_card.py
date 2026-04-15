"""Render the answer card with perfect ASCII alignment."""

from __future__ import annotations


def render_card(
    question: str,
    known_fields: list[str],
    new_fields: list[str],
    source: str,
    joins: list[str],
    lore: list[str],
    notes: str | None = None,
) -> str:
    """Render an answer card as an ASCII box.

    known_fields/new_fields: lines like "login", "  ↳ timestamp", etc.
    joins: list of join descriptions like "login_to_workspaces (login → workspaces)"
    lore: list of lore names
    """
    total_width = 96

    # --- Question tab (2/3 width) ---
    tab_inner = total_width * 2 // 3
    body_inner = total_width - 2  # inside the full-width box

    q_text = f"Q: {question}"
    tab_lines = _wrap_text(q_text, tab_inner)

    # --- Known / New columns ---
    col_width = body_inner // 2
    left_col = col_width
    right_col = body_inner - left_col - 1  # -1 for the middle │

    known_header = "Known fields:"
    new_header = "New fields:"

    left_lines = [known_header, ""] + (known_fields if known_fields else ["none"])
    right_lines = [new_header, ""] + (new_fields if new_fields else ["none"])

    # Pad to same length
    max_field_lines = max(len(left_lines), len(right_lines))
    while len(left_lines) < max_field_lines:
        left_lines.append("")
    while len(right_lines) < max_field_lines:
        right_lines.append("")

    # --- Source / Joins / Lore block ---
    meta_lines = [f"Source: {source}"]
    if joins:
        meta_lines.append(f"Joins:  {', '.join(joins)}")
    else:
        meta_lines.append("Joins:  none")
    if lore:
        meta_lines.append(f"Lore:   {', '.join(lore)}")

    # Wrap long meta lines
    wrapped_meta: list[str] = []
    for line in meta_lines:
        wrapped_meta.extend(_wrap_text(line, body_inner))

    # --- Notes ---
    wrapped_notes: list[str] = []
    if notes and notes.strip():
        wrapped_notes = _wrap_text(notes.strip(), body_inner)

    # === BUILD THE CARD ===
    out: list[str] = []

    # Tab top border
    out.append("┌" + "─" * tab_inner + "┐")

    # Tab content (question, can wrap)
    for line in tab_lines:
        out.append("│" + _pad(line, tab_inner) + "│")

    # Transition: tab bottom + body top with step-down
    # Left part is tab width, then ┘, then ─ to fill, then ┐
    right_fill = body_inner - tab_inner
    out.append("├" + "─" * (left_col) + "┬" + "─" * (tab_inner - left_col - 1) + "┘" + "─" * (right_fill) + "┐")

    # Field columns
    for l_line, r_line in zip(left_lines, right_lines):
        out.append("│" + _pad(l_line, left_col) + "│" + _pad(r_line, right_col) + "│")

    # Separator: fields → meta
    out.append("├" + "─" * left_col + "┴" + "─" * right_col + "┤")

    # Meta lines
    for line in wrapped_meta:
        out.append("│" + _pad(line, body_inner) + "│")

    # Notes or close
    if wrapped_notes:
        out.append("├" + "─" * body_inner + "┤")
        for line in wrapped_notes:
            out.append("│" + _pad(line, body_inner) + "│")

    out.append("└" + "─" * body_inner + "┘")

    return "\n".join(out)


def _pad(text: str, width: int) -> str:
    """Pad text with a leading space and trailing spaces to fill width."""
    inner = f" {text}"
    if len(inner) < width:
        inner += " " * (width - len(inner))
    return inner[:width]


def _wrap_text(text: str, width: int) -> list[str]:
    """Wrap text to fit within width (accounting for 1-char left padding)."""
    max_chars = width - 2  # space on each side
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_chars:
            lines.append(current)
            current = word
        elif current:
            current += " " + word
        else:
            current = word
    if current:
        lines.append(current)
    return lines
