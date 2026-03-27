"""Provider-neutral prompt packet renderer.

Renders prompt packet sections in a fixed body order:

1. ``<deal_context>``
2. ``<chronology_blocks>``
3. ``<overlap_context>`` (chunked packets only)
4. ``<evidence_checklist>``
5. ``<actor_roster>`` (event packets only)
6. ``<task_instructions>``

Each section is wrapped in explicit XML tags for deterministic parsing.
"""

from __future__ import annotations

from pathlib import Path

from skill_pipeline.pipeline_models.prompt import PromptChunkWindow
from skill_pipeline.pipeline_models.source import ChronologyBlock, EvidenceItem
from skill_pipeline.prompts.checklist import build_evidence_checklist


def _render_deal_context(
    deal_slug: str,
    target_name: str,
    accession_number: str | None,
    filing_type: str | None,
    chunk_mode: str,
    window_id: str,
) -> str:
    """Render the deal context section."""
    lines = [
        "<deal_context>",
        f"deal_slug: {deal_slug}",
        f"target_name: {target_name}",
    ]
    if accession_number:
        lines.append(f"source_accession_number: {accession_number}")
    if filing_type:
        lines.append(f"source_form_type: {filing_type}")
    lines.append(f"chunk_mode: {chunk_mode}")
    lines.append(f"window_id: {window_id}")
    lines.append("</deal_context>")
    return "\n".join(lines)


def _render_blocks_section(
    tag: str,
    blocks: list[ChronologyBlock],
    block_ids: list[str],
) -> str:
    """Render chronology blocks filtered to *block_ids* inside *tag*."""
    id_set = set(block_ids)
    filtered = [b for b in blocks if b.block_id in id_set]
    # Sort by ordinal to preserve document order
    filtered.sort(key=lambda b: b.ordinal)
    lines = [f"<{tag}>"]
    for b in filtered:
        lines.append(f"{b.block_id} [L{b.start_line}-L{b.end_line}]: {b.clean_text}")
    lines.append(f"</{tag}>")
    return "\n".join(lines)


def _render_evidence_section(items: list[EvidenceItem]) -> str:
    """Render the evidence checklist section."""
    checklist = build_evidence_checklist(items)
    lines = ["<evidence_checklist>"]
    if checklist:
        lines.append(checklist)
    lines.append("</evidence_checklist>")
    return "\n".join(lines)


def _render_actor_roster_section(actor_roster_json: str) -> str:
    """Render the actor roster section (event packets only)."""
    lines = [
        "<actor_roster>",
        actor_roster_json.strip(),
        "</actor_roster>",
    ]
    return "\n".join(lines)


def _load_asset(asset_path: Path) -> str:
    """Load a prompt asset file.  Fail fast if missing."""
    if not asset_path.exists():
        raise FileNotFoundError(f"Missing prompt asset: {asset_path}")
    return asset_path.read_text(encoding="utf-8").strip()


def render_actor_packet(
    *,
    deal_slug: str,
    target_name: str,
    accession_number: str | None,
    filing_type: str | None,
    window: PromptChunkWindow,
    blocks: list[ChronologyBlock],
    evidence_items: list[EvidenceItem],
    prefix_asset_path: Path,
    task_instructions: str,
) -> tuple[str, str, str]:
    """Render an actor extraction prompt packet.

    Returns:
        A tuple of (prefix_text, body_text, rendered_text) where
        rendered_text is the full concatenated packet.
    """
    chunk_mode = "single_pass" if window.chunk_count == 1 else "chunked"

    prefix_text = _load_asset(prefix_asset_path)

    body_parts: list[str] = []

    # 1. Deal context
    body_parts.append(_render_deal_context(
        deal_slug=deal_slug,
        target_name=target_name,
        accession_number=accession_number,
        filing_type=filing_type,
        chunk_mode=chunk_mode,
        window_id=window.window_id,
    ))

    # 2. Chronology blocks (target)
    body_parts.append(_render_blocks_section(
        "chronology_blocks", blocks, window.target_block_ids,
    ))

    # 3. Overlap context (chunked only)
    if window.overlap_block_ids:
        body_parts.append(_render_blocks_section(
            "overlap_context", blocks, window.overlap_block_ids,
        ))

    # 4. Evidence checklist
    body_parts.append(_render_evidence_section(evidence_items))

    # 5. No actor roster for actor packets

    # 6. Task instructions
    body_parts.append(f"<task_instructions>\n{task_instructions}\n</task_instructions>")

    body_text = "\n\n".join(body_parts)
    rendered_text = f"{prefix_text}\n\n{body_text}"

    return prefix_text, body_text, rendered_text


def render_event_packet(
    *,
    deal_slug: str,
    target_name: str,
    accession_number: str | None,
    filing_type: str | None,
    window: PromptChunkWindow,
    blocks: list[ChronologyBlock],
    evidence_items: list[EvidenceItem],
    actor_roster_json: str,
    prefix_asset_path: Path,
    event_examples_asset_path: Path | None = None,
    task_instructions: str,
) -> tuple[str, str, str]:
    """Render an event extraction prompt packet.

    Returns:
        A tuple of (prefix_text, body_text, rendered_text) where
        rendered_text is the full concatenated packet.
    """
    chunk_mode = "single_pass" if window.chunk_count == 1 else "chunked"

    prefix_parts: list[str] = [_load_asset(prefix_asset_path)]
    if event_examples_asset_path and event_examples_asset_path.exists():
        prefix_parts.append(_load_asset(event_examples_asset_path))
    prefix_text = "\n\n".join(prefix_parts)

    body_parts: list[str] = []

    # 1. Deal context
    body_parts.append(_render_deal_context(
        deal_slug=deal_slug,
        target_name=target_name,
        accession_number=accession_number,
        filing_type=filing_type,
        chunk_mode=chunk_mode,
        window_id=window.window_id,
    ))

    # 2. Chronology blocks (target)
    body_parts.append(_render_blocks_section(
        "chronology_blocks", blocks, window.target_block_ids,
    ))

    # 3. Overlap context (chunked only)
    if window.overlap_block_ids:
        body_parts.append(_render_blocks_section(
            "overlap_context", blocks, window.overlap_block_ids,
        ))

    # 4. Evidence checklist
    body_parts.append(_render_evidence_section(evidence_items))

    # 5. Actor roster (event packets only)
    body_parts.append(_render_actor_roster_section(actor_roster_json))

    # 6. Task instructions
    body_parts.append(f"<task_instructions>\n{task_instructions}\n</task_instructions>")

    body_text = "\n\n".join(body_parts)
    rendered_text = f"{prefix_text}\n\n{body_text}"

    return prefix_text, body_text, rendered_text
