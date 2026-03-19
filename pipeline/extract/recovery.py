from __future__ import annotations

from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR
from pipeline.llm.prompts import PromptPack
from pipeline.llm.schemas import EventExtractionOutput, RecoveryAuditOutput
from pipeline.extract.merge import merge_event_outputs
from pipeline.extract.utils import (
    appendix_evidence_items,
    atomic_write_json,
    select_prompt_evidence_items,
    summarize_usage,
)
from pipeline.models.common import EventType
from pipeline.models.source import ChronologyBlock, EvidenceItem


RECOVERY_OUTPUT_FILENAME = "recovery_raw.json"
RECOVERY_USAGE_FILENAME = "recovery_usage.json"


def needs_recovery_audit(
    event_output: EventExtractionOutput,
    *,
    evidence_items: list[EvidenceItem],
) -> bool:
    proposal_count = sum(1 for event in event_output.events if event.event_type == EventType.PROPOSAL)
    nda_count = sum(1 for event in event_output.events if event.event_type == EventType.NDA)
    outcome_count = sum(
        1
        for event in event_output.events
        if event.event_type in {EventType.EXECUTED, EventType.TERMINATED}
    )

    financial_items = [item for item in evidence_items if item.evidence_type.value == "financial_term"]
    process_items = [item for item in evidence_items if item.evidence_type.value == "process_signal"]
    outcome_items = [item for item in evidence_items if item.evidence_type.value == "outcome_fact"]

    if proposal_count == 0 and financial_items:
        return True
    if nda_count == 0 and any("confidentiality" in item.raw_text.lower() or "nda" in item.raw_text.lower() for item in process_items):
        return True
    if outcome_count == 0 and outcome_items:
        return True
    if len(event_output.events) < 3 and (financial_items or process_items):
        return True
    return False


def run_recovery_audit(
    blocks: list[ChronologyBlock],
    *,
    deal_slug: str,
    run_id: str,
    backend,
    extracted_events_summary: Any,
    evidence_items: list[EvidenceItem],
    chronology_blocks: list[ChronologyBlock],
    deals_dir: Path = DEALS_DIR,
    model: str | None = None,
) -> dict[str, Any]:
    extract_dir = deals_dir / deal_slug / "extract"
    extract_dir.mkdir(parents=True, exist_ok=True)

    prompt_evidence = select_prompt_evidence_items(
        appendix_evidence_items(evidence_items, chronology_blocks=chronology_blocks),
        max_total=30,
        max_per_type=8,
    )
    messages = [
        {
            "role": "user",
            "content": PromptPack.render_recovery_user_message(
                blocks,
                extracted_events_summary,
                evidence_items=prompt_evidence,
            ),
        }
    ]
    result = backend.invoke_structured(
        messages=messages,
        system=PromptPack.RECOVERY_SYSTEM_PROMPT,
        output_schema=RecoveryAuditOutput,
        max_tokens=1500,
        model=model,
    )
    atomic_write_json(extract_dir / RECOVERY_OUTPUT_FILENAME, result.output.model_dump(mode="json"))
    atomic_write_json(
        extract_dir / RECOVERY_USAGE_FILENAME,
        {
            **summarize_usage(result),
            "deal_slug": deal_slug,
            "run_id": run_id,
            "recovery_target_count": len(result.output.recovery_targets),
        },
    )
    return {
        "output": result.output,
        **summarize_usage(result),
    }


def build_recovery_block_subset(
    recovery_output: RecoveryAuditOutput,
    blocks: list[ChronologyBlock],
) -> list[ChronologyBlock]:
    by_id = {block.block_id: block for block in blocks}
    selected: list[ChronologyBlock] = []
    seen: set[str] = set()
    for target in recovery_output.recovery_targets:
        for block_id in target.block_ids:
            if block_id not in by_id or block_id in seen:
                continue
            seen.add(block_id)
            selected.append(by_id[block_id])
    selected.sort(key=lambda block: block.ordinal)
    return selected


def recover_missing_events(
    existing_output: EventExtractionOutput,
    recovered_output: EventExtractionOutput,
) -> EventExtractionOutput:
    return merge_event_outputs([existing_output, recovered_output])
