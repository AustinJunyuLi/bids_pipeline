"""Prompt builders for LLM-backed skill-pipeline stages."""

from __future__ import annotations

import json

from skill_pipeline.schemas.runtime import RawSkillActorsArtifact, SeedEntry
from skill_pipeline.schemas.source import ChronologyBlock, EvidenceItem

ACTOR_SYSTEM_PROMPT = """You extract actors from SEC merger-background text.

Rules:
- The filing text is the single source of truth.
- Return one JSON object only.
- Extract named bidders, advisors, activists, target-side actors, and grouped unnamed parties.
- Use verbatim anchor_text in evidence_refs.
- Add count_assertions for explicit counts of bidders, NDA signers, or round invitees.
- Do not consult benchmark materials.
"""

EVENT_SYSTEM_PROMPT = """You extract M&A process events from SEC merger-background text.

Rules:
- The filing text is the single source of truth.
- Return one JSON object only.
- Use the 20-event taxonomy already defined by the output schema.
- Proposal events must include terms and formality_signals.
- Record taxonomy sweep coverage_notes and note missing event families explicitly.
- Exclude partial-company bids and unsigned NDAs from final events.
- Do not consult benchmark materials.
"""

OMISSION_AUDIT_SYSTEM_PROMPT = """You audit uncovered merger-background text for likely omitted process events.

Rules:
- The filing text is the single source of truth.
- Return one JSON object only.
- Focus on structural omissions that are explicitly or strongly supported by the uncovered text.
- Prefer event families such as round events, target-caused drops, adviser retention, and go-shop endings.
- Use severity='error' only for explicit filing support.
- Use repairability='repairable' for findings that can be fixed by adding or correcting extracted actors/events.
- suggested_event_types must use the existing event taxonomy.
- Do not consult benchmark materials.
"""

REPAIR_SYSTEM_PROMPT = """You repair raw extraction artifacts using filing-grounded deterministic findings.

Rules:
- The filing text is the single source of truth.
- Return one JSON object only.
- Edit only the raw extract artifacts provided in the prompt.
- Fix every repairable error that is supported by the filing context.
- Preserve unaffected records and schema shape.
- Do not invent benchmark-driven events or actors.
- Do not write canonical spans; the deterministic materialize stage will rebuild them.
"""

ENRICH_INTERPRET_SYSTEM_PROMPT = """You perform interpretive enrichment over filing-grounded M&A extraction artifacts.

Rules:
- The filing text is the single source of truth.
- Return one JSON object only.
- Use only the provided actors, events, deterministic enrichment, and filing context.
- Do not alter deterministic fields; provide only the task-specific interpretive output.
- Do not consult benchmark materials.
"""


def build_actor_prompt(
    seed: SeedEntry,
    blocks: list[ChronologyBlock],
    evidence_items: list[EvidenceItem],
) -> tuple[str, str]:
    user = (
        "<deal_context>\n"
        f"target_name: {seed.target_name}\n"
        f"acquirer: {seed.acquirer or 'unknown'}\n"
        f"date_announced: {seed.date_announced or 'unknown'}\n"
        "</deal_context>\n\n"
        "<chronology_blocks>\n"
        f"{render_blocks(blocks)}\n"
        "</chronology_blocks>\n\n"
        "<evidence_items>\n"
        f"{_render_evidence_items(evidence_items)}\n"
        "</evidence_items>"
    )
    return ACTOR_SYSTEM_PROMPT, user


def build_event_prompt(
    seed: SeedEntry,
    blocks: list[ChronologyBlock],
    evidence_items: list[EvidenceItem],
    actors: RawSkillActorsArtifact,
) -> tuple[str, str]:
    user = (
        "<deal_context>\n"
        f"target_name: {seed.target_name}\n"
        f"acquirer: {seed.acquirer or 'unknown'}\n"
        f"date_announced: {seed.date_announced or 'unknown'}\n"
        "</deal_context>\n\n"
        "<actor_roster>\n"
        f"{json.dumps(actors.model_dump(mode='json'), indent=2)}\n"
        "</actor_roster>\n\n"
        "<chronology_blocks>\n"
        f"{render_blocks(blocks)}\n"
        "</chronology_blocks>\n\n"
        "<evidence_items>\n"
        f"{_render_evidence_items(evidence_items)}\n"
        "</evidence_items>\n\n"
        "<coverage_instructions>\n"
        "List extracted event families in coverage_notes and write NOT FOUND with a filing-based reason for missing families.\n"
        "</coverage_instructions>"
    )
    return EVENT_SYSTEM_PROMPT, user


def build_omission_audit_prompt(
    uncovered_blocks: str,
    coverage_findings: str,
) -> tuple[str, str]:
    user = (
        "<task>\n"
        "Review the uncovered chronology blocks and deterministic coverage findings. "
        "Identify likely omitted filing-grounded events only when the text explicitly or strongly supports them.\n"
        "</task>\n\n"
        "<uncovered_blocks>\n"
        f"{uncovered_blocks}\n"
        "</uncovered_blocks>\n\n"
        "<coverage_findings>\n"
        f"{coverage_findings}\n"
        "</coverage_findings>"
    )
    return OMISSION_AUDIT_SYSTEM_PROMPT, user


def build_repair_prompt(
    *,
    findings: str,
    filing_context: str,
    actors_json: str,
    events_json: str,
) -> tuple[str, str]:
    user = (
        "<repair_findings>\n"
        f"{findings}\n"
        "</repair_findings>\n\n"
        "<filing_context>\n"
        f"{filing_context}\n"
        "</filing_context>\n\n"
        "<actors_raw>\n"
        f"{actors_json}\n"
        "</actors_raw>\n\n"
        "<events_raw>\n"
        f"{events_json}\n"
        "</events_raw>"
    )
    return REPAIR_SYSTEM_PROMPT, user


def build_enrich_interpret_prompt(task_name: str, context: str) -> tuple[str, str]:
    user = f"<task_name>\n{task_name}\n</task_name>\n\n<context>\n{context}\n</context>"
    return ENRICH_INTERPRET_SYSTEM_PROMPT, user


def render_blocks(blocks: list[ChronologyBlock]) -> str:
    return "\n".join(
        f"{block.block_id} [L{block.start_line}-L{block.end_line}]: {(block.clean_text or block.raw_text).strip()}"
        for block in blocks
    )


def _render_evidence_items(evidence_items: list[EvidenceItem]) -> str:
    return "\n".join(
        (
            f"{item.evidence_id} ({item.evidence_type}) "
            f"[{item.document_id}:L{item.start_line}-L{item.end_line}]: {item.raw_text.strip()}"
        )
        for item in evidence_items
    )
