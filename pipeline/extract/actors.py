from __future__ import annotations

from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR
from pipeline.llm.prompts import PromptPack
from pipeline.llm.schemas import ActorExtractionOutput
from pipeline.llm.token_budget import classify_complexity, estimate_max_output_tokens
from pipeline.extract.utils import (
    appendix_evidence_items,
    atomic_write_json,
    load_source_inputs,
    select_prompt_evidence_items,
    summarize_usage,
)


ACTOR_OUTPUT_FILENAME = "actors_raw.json"
ACTOR_USAGE_FILENAME = "actor_usage.json"


def run_actor_extraction(
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

    prompt_evidence = select_prompt_evidence_items(
        appendix_evidence_items(evidence_items, chronology_blocks=blocks)
    )
    deal_context = {
        "deal_slug": deal_slug,
        "target_name": seed.target_name,
        "acquirer_seed": seed.acquirer_seed,
        "date_announced_seed": seed.date_announced_seed,
        "accession_number": selection.accession_number,
        "filing_type": selection.filing_type,
    }
    messages = [
        {
            "role": "user",
            "content": PromptPack.render_actor_user_message(
                deal_context,
                blocks,
                evidence_items=prompt_evidence,
            ),
        }
    ]
    token_count = backend.count_tokens(
        messages=messages,
        system=PromptPack.ACTOR_SYSTEM_PROMPT,
        model=model,
    )
    line_count = sum((block.end_line - block.start_line + 1) for block in blocks)
    complexity = classify_complexity(token_count, line_count, actor_count=0)
    max_tokens = estimate_max_output_tokens(complexity, "actor")
    effective_model = (model or getattr(backend, "model", "") or "").strip().lower()
    provider = (getattr(backend, "provider", "") or "").strip().lower()
    if provider == "openai" and effective_model.startswith("gpt-5"):
        gpt5_actor_floors = {
            "simple": 3_000,
            "moderate": 4_500,
            "complex": 6_500,
        }
        max_tokens = max(max_tokens, gpt5_actor_floors[complexity.value])
    result = backend.invoke_structured(
        messages=messages,
        system=PromptPack.ACTOR_SYSTEM_PROMPT,
        output_schema=ActorExtractionOutput,
        max_tokens=max_tokens,
        model=model,
    )
    if not result.output.actors and not result.output.count_assertions and not result.output.unresolved_mentions:
        raise ValueError(
            "Actor extraction returned an empty structured payload; "
            "this usually indicates a truncated or under-budget LLM response."
        )

    atomic_write_json(extract_dir / ACTOR_OUTPUT_FILENAME, result.output.model_dump(mode="json"))
    atomic_write_json(
        extract_dir / ACTOR_USAGE_FILENAME,
        {
            **summarize_usage(result),
            "deal_slug": deal_slug,
            "run_id": run_id,
            "token_count": token_count,
            "line_count": line_count,
            "complexity": complexity.value,
            "evidence_item_count": len(prompt_evidence),
            "block_count": len(blocks),
        },
    )
    return {
        "deal_slug": deal_slug,
        "actor_count": len(result.output.actors),
        "count_assertion_count": len(result.output.count_assertions),
        "unresolved_mention_count": len(result.output.unresolved_mentions),
        "complexity": complexity.value,
        **summarize_usage(result),
    }
