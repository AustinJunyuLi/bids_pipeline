"""Deterministic chronology block annotation helpers.

Annotates ChronologyBlock instances with date mentions, entity mentions,
evidence density, and temporal phase metadata.
"""

from __future__ import annotations

import re
from typing import Literal

from skill_pipeline.models import SeedEntry
from skill_pipeline.normalize.dates import parse_resolved_date
from skill_pipeline.pipeline_models.source import (
    BlockDateMention,
    BlockEntityMention,
    ChronologyBlock,
    EvidenceItem,
)
from skill_pipeline.source.evidence import DATE_FRAGMENT_RE


# ── Entity matching patterns ──

_PARTY_ALIAS_RE = re.compile(r"\bParty\s+[A-Z]\b")
_COMPANY_ALIAS_RE = re.compile(r"\bthe\s+Company\b", re.IGNORECASE)
_BOARD_RE = re.compile(r"\bthe\s+Board\b", re.IGNORECASE)
_SPECIAL_COMMITTEE_RE = re.compile(r"\bSpecial\s+Committee\b", re.IGNORECASE)
_TRANSACTION_COMMITTEE_RE = re.compile(r"\bTransaction\s+Committee\b", re.IGNORECASE)

# Evidence type families used for temporal phase inference
_INITIATION_TYPES = {"actor_identification"}
_BIDDING_TYPES = {"dated_action", "financial_term", "process_signal"}
_OUTCOME_TYPES = {"outcome_fact"}


def annotate_chronology_blocks(
    blocks: list[ChronologyBlock],
    evidence_items: list[EvidenceItem],
    seed: SeedEntry,
) -> list[ChronologyBlock]:
    """Annotate blocks with date mentions, entity mentions, evidence density, and temporal phase.

    Returns new ChronologyBlock instances with metadata populated. The input
    blocks must already have base fields set; this function adds the annotation
    layer.
    """
    total_blocks = len(blocks)
    annotated: list[ChronologyBlock] = []
    for block in blocks:
        overlapping = _overlapping_evidence(block, evidence_items)
        phase = _assign_temporal_phase(block, overlapping, total_blocks)
        annotated.append(
            ChronologyBlock(
                block_id=block.block_id,
                document_id=block.document_id,
                ordinal=block.ordinal,
                start_line=block.start_line,
                end_line=block.end_line,
                raw_text=block.raw_text,
                clean_text=block.clean_text,
                is_heading=block.is_heading,
                page_break_before=block.page_break_before,
                page_break_after=block.page_break_after,
                date_mentions=_extract_date_mentions(block.clean_text),
                entity_mentions=_extract_entity_mentions(block.clean_text, seed),
                evidence_density=len(overlapping),
                temporal_phase=phase,
            )
        )
    return annotated


# ── Date extraction ──


def _extract_date_mentions(text: str) -> list[BlockDateMention]:
    """Extract date fragment mentions from block text and resolve each."""
    mentions: list[BlockDateMention] = []
    seen: set[str] = set()
    for match in DATE_FRAGMENT_RE.finditer(text):
        raw = match.group(0).strip()
        if not raw or raw in seen:
            continue
        seen.add(raw)
        resolved = parse_resolved_date(raw)
        normalized: str | None = None
        if resolved.sort_date is not None:
            normalized = resolved.sort_date.isoformat()
        mentions.append(
            BlockDateMention(
                raw_text=raw,
                normalized=normalized,
                precision=resolved.precision,
            )
        )
    return mentions


# ── Entity extraction ──


def _extract_entity_mentions(
    text: str,
    seed: SeedEntry,
) -> list[BlockEntityMention]:
    """Extract entity mentions from block text using seed names and filing aliases."""
    mentions: list[BlockEntityMention] = []
    seen: set[str] = set()

    def _add(raw: str, entity_type: Literal["target", "acquirer", "party_alias", "committee"]) -> None:
        key = raw.lower()
        if key in seen:
            return
        seen.add(key)
        mentions.append(BlockEntityMention(raw_text=raw, entity_type=entity_type))

    # Target name match (case-insensitive substring)
    if seed.target_name and seed.target_name.lower() in text.lower():
        _add(seed.target_name, "target")

    # Acquirer name match (case-insensitive substring)
    if seed.acquirer and seed.acquirer.lower() in text.lower():
        _add(seed.acquirer, "acquirer")

    # Party aliases: Party A, Party B, etc.
    for m in _PARTY_ALIAS_RE.finditer(text):
        _add(m.group(0), "party_alias")

    # "the Company"
    for m in _COMPANY_ALIAS_RE.finditer(text):
        _add(m.group(0), "party_alias")

    # "the Board"
    for m in _BOARD_RE.finditer(text):
        _add(m.group(0), "party_alias")

    # Committees
    for m in _SPECIAL_COMMITTEE_RE.finditer(text):
        _add(m.group(0), "committee")

    for m in _TRANSACTION_COMMITTEE_RE.finditer(text):
        _add(m.group(0), "committee")

    return mentions


# ── Evidence density ──


def _overlapping_evidence(
    block: ChronologyBlock,
    evidence_items: list[EvidenceItem],
) -> list[EvidenceItem]:
    """Return evidence items whose line ranges overlap with the block."""
    overlapping: list[EvidenceItem] = []
    for item in evidence_items:
        if item.start_line <= block.end_line and item.end_line >= block.start_line:
            overlapping.append(item)
    return overlapping


# ── Temporal phase ──


def _assign_temporal_phase(
    block: ChronologyBlock,
    overlapping: list[EvidenceItem],
    total_blocks: int,
) -> Literal["initiation", "bidding", "outcome", "other"]:
    """Assign temporal phase based on overlapping evidence types with ordinal fallback."""
    if overlapping:
        types = {item.evidence_type.value for item in overlapping}
        # Outcome takes precedence if present
        if types & _OUTCOME_TYPES:
            return "outcome"
        # Bidding signals (proposals, NDAs, financial terms, process signals)
        if types & _BIDDING_TYPES:
            return "bidding"
        # Initiation signals (actor identification without bidding context)
        if types & _INITIATION_TYPES:
            return "initiation"

    # Ordinal fallback when no evidence cues overlap
    if total_blocks == 0:
        return "other"

    position = block.ordinal / total_blocks
    if position <= 0.15:
        return "initiation"
    elif position >= 0.85:
        return "outcome"
    else:
        return "other"
