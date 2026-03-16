from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR
from pipeline.models.source import ChronologyBlock, ChronologySelection, EvidenceItem, SeedDeal
from pipeline.seeds import entry_to_seed_artifact, load_seed_registry


def load_source_inputs(
    deal_slug: str,
    *,
    run_id: str,
    deals_dir: Path = DEALS_DIR,
) -> tuple[SeedDeal, ChronologySelection, list[ChronologyBlock], list[EvidenceItem]]:
    seed = load_seed_artifact(deal_slug, run_id=run_id)
    source_dir = deals_dir / deal_slug / "source"
    selection = ChronologySelection.model_validate_json(
        (source_dir / "chronology_selection.json").read_text(encoding="utf-8")
    )
    blocks = load_jsonl(source_dir / "chronology_blocks.jsonl", ChronologyBlock)
    evidence_path = source_dir / "evidence_items.jsonl"
    evidence_items = load_jsonl(evidence_path, EvidenceItem) if evidence_path.exists() else []
    return seed, selection, blocks, evidence_items


def load_seed_artifact(deal_slug: str, *, run_id: str) -> SeedDeal:
    for entry in load_seed_registry():
        if entry.deal_slug == deal_slug:
            return entry_to_seed_artifact(entry, run_id=run_id)
    raise ValueError(f"Unknown deal slug: {deal_slug}")


def load_jsonl(path: Path, model_cls):
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []
    return [model_cls.model_validate_json(line) for line in text.splitlines()]


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, default=str))


def atomic_write_jsonl(path: Path, payloads: list[dict[str, Any]]) -> None:
    atomic_write_text(path, "\n".join(json.dumps(payload, default=str) for payload in payloads))


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def summarize_usage(result) -> dict[str, Any]:
    usage = getattr(result, "usage", None)
    if usage is None:
        return {}
    return {
        "input_tokens": usage.input_tokens,
        "cache_creation_input_tokens": usage.cache_creation_input_tokens,
        "cache_read_input_tokens": usage.cache_read_input_tokens,
        "output_tokens": usage.output_tokens,
        "cost_usd": usage.cost_usd,
        "latency_ms": usage.latency_ms,
        "request_id": usage.request_id,
        "model": usage.model,
        "prompt_version": result.prompt_version,
    }


def select_prompt_evidence_items(
    evidence_items: list[EvidenceItem],
    *,
    max_total: int = 40,
    max_per_type: int = 10,
) -> list[EvidenceItem]:
    priority = {"high": 0, "medium": 1, "low": 2}
    per_type_counts: dict[str, int] = {}
    selected: list[EvidenceItem] = []
    for item in sorted(
        evidence_items,
        key=lambda value: (
            priority[value.confidence],
            value.evidence_type.value,
            value.start_line,
            value.evidence_id,
        ),
    ):
        type_key = item.evidence_type.value
        if per_type_counts.get(type_key, 0) >= max_per_type:
            continue
        selected.append(item)
        per_type_counts[type_key] = per_type_counts.get(type_key, 0) + 1
        if len(selected) >= max_total:
            break
    return selected
