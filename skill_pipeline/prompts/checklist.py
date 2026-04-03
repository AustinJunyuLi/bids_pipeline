"""Convert evidence items into a concise active checklist grouped by type.

The checklist steers extraction attention toward filing-grounded anchors
rather than dumping evidence as a passive appendix.
"""

from __future__ import annotations

from collections import defaultdict

from skill_pipeline.pipeline_models.source import EvidenceItem, EvidenceType


# Imperative checklist header per evidence type
_TYPE_HEADERS: dict[EvidenceType, str] = {
    EvidenceType.DATED_ACTION: "Dated actions to extract",
    EvidenceType.FINANCIAL_TERM: "Financial terms to capture",
    EvidenceType.ACTOR_IDENTIFICATION: "Actors to identify",
    EvidenceType.PROCESS_SIGNAL: "Process signals to check",
    EvidenceType.OUTCOME_FACT: "Outcome facts to verify",
}


def build_evidence_checklist(items: list[EvidenceItem]) -> str:
    """Render *items* as a grouped active checklist in Markdown.

    Groups items by ``evidence_type``, each with an imperative header.
    Each bullet includes the ``evidence_id``, line range, and a short
    imperative prompt derived from the evidence text.

    Args:
        items: Evidence items from ``evidence_items.jsonl``.

    Returns:
        A Markdown string with grouped checklist sections.  Empty string
        if *items* is empty.
    """
    if not items:
        return ""

    grouped: dict[EvidenceType, list[EvidenceItem]] = defaultdict(list)
    for item in items:
        grouped[item.evidence_type].append(item)

    sections: list[str] = []

    # Render in a stable order matching the enum declaration order
    for etype in EvidenceType:
        group = grouped.get(etype)
        if not group:
            continue
        header = _TYPE_HEADERS.get(etype, etype.value)
        lines: list[str] = [f"### {header}"]
        for ei in group:
            bullet = _format_checklist_bullet(ei)
            lines.append(bullet)
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def _format_checklist_bullet(item: EvidenceItem) -> str:
    """Format a single evidence item as a concise checklist bullet."""
    parts: list[str] = [f"- [ ] **{item.evidence_id}**"]
    parts.append(f"L{item.start_line}-L{item.end_line}")

    # Build a short imperative description
    hint_parts: list[str] = []
    if item.date_text:
        hint_parts.append(f"date: {item.date_text}")
    if item.actor_hints:
        hint_parts.append(f"actors: {', '.join(item.actor_hints)}")
    elif item.actor_hint:
        hint_parts.append(f"actor: {item.actor_hint}")
    if item.value_hint:
        hint_parts.append(f"value: {item.value_hint}")
    if item.matched_terms:
        hint_parts.append(f"terms: {', '.join(item.matched_terms[:3])}")

    if hint_parts:
        parts.append(f"({'; '.join(hint_parts)})")

    return " ".join(parts)
