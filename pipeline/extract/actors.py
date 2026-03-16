from __future__ import annotations

from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR
from pipeline.llm.prompts import PromptPack
from pipeline.llm.schemas import ActorExtractionOutput
from pipeline.extract.utils import (
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

    prompt_evidence = select_prompt_evidence_items(evidence_items)
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
    max_tokens = 1800 if len(blocks) < 120 else 2400
    result = backend.invoke_structured(
        messages=messages,
        system=PromptPack.ACTOR_SYSTEM_PROMPT,
        output_schema=ActorExtractionOutput,
        max_tokens=max_tokens,
        model=model,
    )

    atomic_write_json(extract_dir / ACTOR_OUTPUT_FILENAME, result.output.model_dump(mode="json"))
    atomic_write_json(
        extract_dir / ACTOR_USAGE_FILENAME,
        {
            **summarize_usage(result),
            "deal_slug": deal_slug,
            "run_id": run_id,
            "evidence_item_count": len(prompt_evidence),
            "block_count": len(blocks),
        },
    )
    return {
        "deal_slug": deal_slug,
        "actor_count": len(result.output.actors),
        "count_assertion_count": len(result.output.count_assertions),
        "unresolved_mention_count": len(result.output.unresolved_mentions),
        **summarize_usage(result),
    }
