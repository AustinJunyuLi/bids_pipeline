from __future__ import annotations

from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR
from pipeline.llm.prompts import PromptPack
from pipeline.llm.schemas import ActorExtractionOutput, EventExtractionOutput
from pipeline.llm.token_budget import classify_complexity, estimate_max_output_tokens, plan_event_chunks
from pipeline.extract.merge import merge_event_outputs
from pipeline.extract.recovery import (
    build_recovery_block_subset,
    needs_recovery_audit,
    recover_missing_events,
    run_recovery_audit,
)
from pipeline.extract.utils import (
    appendix_evidence_items,
    atomic_write_json,
    atomic_write_jsonl,
    load_source_inputs,
    select_prompt_evidence_items,
    summarize_usage,
)
from pipeline.models.common import EventType


EVENT_OUTPUT_FILENAME = "events_raw.json"
EVENT_CHUNKS_FILENAME = "event_chunks.jsonl"
EVENT_USAGE_FILENAME = "event_usage.json"


def run_event_extraction(
    deal_slug: str,
    *,
    run_id: str,
    backend,
    deals_dir: Path = DEALS_DIR,
    model: str | None = None,
) -> dict[str, Any]:
    seed, selection, blocks, evidence_items = load_source_inputs(deal_slug, run_id=run_id, deals_dir=deals_dir)
    extract_dir = deals_dir / deal_slug / "extract"
    extract_dir.mkdir(parents=True, exist_ok=True)

    actor_output = ActorExtractionOutput.model_validate_json(
        (extract_dir / "actors_raw.json").read_text(encoding="utf-8")
    )
    actor_roster = actor_output.actors
    prompt_evidence = select_prompt_evidence_items(
        appendix_evidence_items(evidence_items, chronology_blocks=blocks)
    )
    rendered_prompt = PromptPack.render_event_user_message(
        {
            "deal_slug": deal_slug,
            "target_name": seed.target_name,
            "accession_number": selection.accession_number,
            "filing_type": selection.filing_type,
        },
        actor_roster,
        blocks,
        chunk_mode="single_pass",
        chunk_id="all",
        prior_round_context=[],
        evidence_items=prompt_evidence,
    )
    token_count = backend.count_tokens(
        messages=[{"role": "user", "content": rendered_prompt}],
        system=PromptPack.EVENT_SYSTEM_PROMPT,
        model=model,
    )
    line_count = sum((block.end_line - block.start_line + 1) for block in blocks)
    complexity = classify_complexity(token_count, line_count, len(actor_roster))

    chunk_groups = [blocks]
    chunk_mode = "single_pass"
    if complexity != "simple":
        chunk_groups = plan_event_chunks(blocks)
        chunk_mode = "chunked"

    chunk_outputs: list[EventExtractionOutput] = []
    chunk_usage_records: list[dict[str, Any]] = []
    prior_round_context: list[str] = []

    for index, chunk in enumerate(chunk_groups, start=1):
        result = _invoke_event_call(
            backend,
            seed_context={
                "deal_slug": deal_slug,
                "target_name": seed.target_name,
                "accession_number": selection.accession_number,
                "filing_type": selection.filing_type,
            },
            actor_roster=actor_roster,
            blocks=chunk,
            chunk_mode=chunk_mode,
            chunk_id=f"chunk-{index}" if chunk_mode == "chunked" else "all",
            prior_round_context=prior_round_context,
            evidence_items=prompt_evidence,
            model=model,
            complexity=complexity,
        )
        chunk_outputs.append(result.output)
        chunk_usage_records.append({
            "chunk_id": f"chunk-{index}" if chunk_mode == "chunked" else "all",
            **summarize_usage(result),
        })
        prior_round_context.extend(_round_context_lines(result.output))

    merged_output = merge_event_outputs(chunk_outputs)

    recovery_usage: dict[str, Any] | None = None
    if needs_recovery_audit(merged_output, evidence_items=evidence_items):
        recovery_result = run_recovery_audit(
            blocks,
            deal_slug=deal_slug,
            run_id=run_id,
            backend=backend,
            extracted_events_summary=_event_summary_for_recovery(merged_output),
            evidence_items=evidence_items,
            chronology_blocks=blocks,
            deals_dir=deals_dir,
            model=model,
        )
        recovery_usage = {k: v for k, v in recovery_result.items() if k != "output"}
        subset = build_recovery_block_subset(recovery_result["output"], blocks)
        if subset:
            recovered = _invoke_event_call(
                backend,
                seed_context={
                    "deal_slug": deal_slug,
                    "target_name": seed.target_name,
                    "accession_number": selection.accession_number,
                    "filing_type": selection.filing_type,
                },
                actor_roster=actor_roster,
                blocks=subset,
                chunk_mode="recovery",
                chunk_id="recovery",
                prior_round_context=prior_round_context,
                evidence_items=prompt_evidence,
                model=model,
                complexity=complexity,
            )
            merged_output = recover_missing_events(merged_output, recovered.output)
            chunk_usage_records.append({"chunk_id": "recovery", **summarize_usage(recovered)})

    atomic_write_json(extract_dir / EVENT_OUTPUT_FILENAME, merged_output.model_dump(mode="json"))
    atomic_write_jsonl(
        extract_dir / EVENT_CHUNKS_FILENAME,
        [output.model_dump(mode="json") for output in chunk_outputs],
    )
    atomic_write_json(
        extract_dir / EVENT_USAGE_FILENAME,
        {
            "deal_slug": deal_slug,
            "run_id": run_id,
            "token_count": token_count,
            "line_count": line_count,
            "complexity": complexity.value,
            "chunk_mode": chunk_mode,
            "chunk_count": len(chunk_groups),
            "calls": chunk_usage_records,
            "recovery": recovery_usage,
        },
    )
    return {
        "deal_slug": deal_slug,
        "event_count": len(merged_output.events),
        "exclusion_count": len(merged_output.exclusions),
        "unresolved_mention_count": len(merged_output.unresolved_mentions),
        "complexity": complexity.value,
        "chunk_mode": chunk_mode,
        "chunk_count": len(chunk_groups),
    }


def _invoke_event_call(
    backend,
    *,
    seed_context: dict[str, Any],
    actor_roster,
    blocks,
    chunk_mode: str,
    chunk_id: str,
    prior_round_context: list[str] | str | None,
    evidence_items,
    model: str | None,
    complexity,
):
    effective_model = (model or getattr(backend, "model", "") or "").strip().lower()
    provider = (getattr(backend, "provider", "") or "").strip().lower()
    max_tokens = estimate_max_output_tokens(complexity, "event")
    if provider == "openai" and effective_model.startswith("gpt-5"):
        # GPT-5 event extraction can defer visible JSON until late in the
        # completion. Give it a larger output cap than the provider-neutral
        # defaults or moderately complex chunks can terminate with no text.
        gpt5_minimums = {
            "simple": 8_000,
            "moderate": 12_000,
            "complex": 16_000,
        }
        max_tokens = max(max_tokens, gpt5_minimums[complexity.value])
    if provider == "anthropic" and effective_model.startswith("claude-"):
        # Anthropic can also truncate long event chunks mid-object in prompted
        # JSON mode. Give moderate/complex chunks extra room so the first pass
        # can finish the top-level object instead of exhausting repairs.
        anthropic_minimums = {
            "simple": 3_000,
            "moderate": 10_000,
            "complex": 14_000,
        }
        max_tokens = max(max_tokens, anthropic_minimums[complexity.value])

    messages = [
        {
            "role": "user",
            "content": PromptPack.render_event_user_message(
                seed_context,
                actor_roster,
                blocks,
                chunk_mode=chunk_mode,
                chunk_id=chunk_id,
                prior_round_context=prior_round_context,
                evidence_items=evidence_items,
            ),
        }
    ]
    return backend.invoke_structured(
        messages=messages,
        system=PromptPack.EVENT_SYSTEM_PROMPT,
        output_schema=EventExtractionOutput,
        max_tokens=max_tokens,
        model=model,
    )


def _round_context_lines(output: EventExtractionOutput) -> list[str]:
    lines: list[str] = []
    for event in output.events:
        if event.event_type in {
            EventType.FINAL_ROUND_INF_ANN,
            EventType.FINAL_ROUND_INF,
            EventType.FINAL_ROUND_ANN,
            EventType.FINAL_ROUND,
            EventType.FINAL_ROUND_EXT_ANN,
            EventType.FINAL_ROUND_EXT,
        }:
            lines.append(f"{event.event_type.value} on {event.date.raw_text}")
    return lines


def _event_summary_for_recovery(output: EventExtractionOutput) -> list[dict[str, Any]]:
    summary = []
    for event in output.events:
        summary.append(
            {
                "event_type": event.event_type.value,
                "date": event.date.raw_text,
                "actor_ids": event.actor_ids,
                "summary": event.summary,
                "evidence_refs": [ref.model_dump(mode="json") for ref in event.evidence_refs],
            }
        )
    return summary
