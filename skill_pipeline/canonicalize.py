"""Canonicalize quote-first v2 observation artifacts into span-backed outputs."""

from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.extract_artifacts_v2 import (
    RawObservationArtifactV2,
    load_observation_artifacts,
)
from skill_pipeline.models import QuoteEntry, SpanRegistryArtifact
from skill_pipeline.models_v2 import ObservationArtifactV2
from skill_pipeline.paths import build_skill_paths, ensure_output_directories
from skill_pipeline.pipeline_models.source import ChronologyBlock
from skill_pipeline.provenance import resolve_text_span


def _load_document_lines(filings_dir: Path) -> dict[str, list[str]]:
    if not filings_dir.exists():
        raise FileNotFoundError(
            f"Raw filings directory not found: {filings_dir}. "
            "Run 'skill-pipeline raw-fetch --deal <slug>' first."
        )
    return {
        path.stem: path.read_text(encoding="utf-8").splitlines()
        for path in filings_dir.glob("*.txt")
    }


def _load_chronology_blocks(path: Path) -> list[ChronologyBlock]:
    blocks: list[ChronologyBlock] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        blocks.append(ChronologyBlock.model_validate_json(line))
    return blocks


def _load_document_registry(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    documents = payload.get("documents", [])
    return {
        document["document_id"]: {
            "accession_number": document.get("accession_number"),
            "filing_type": document.get("filing_type", "UNKNOWN"),
        }
        for document in documents
        if document.get("document_id")
    }


def _resolve_quotes_to_spans(
    quotes: list[QuoteEntry],
    *,
    blocks_by_id: dict[str, ChronologyBlock],
    document_lines: dict[str, list[str]],
    document_meta: dict[str, dict],
) -> tuple[list[dict], dict[str, str]]:
    spans: list[dict] = []
    quote_to_span: dict[str, str] = {}
    span_id_by_key: dict[tuple[str, str], str] = {}
    seen_ids: set[str] = set()

    for quote in quotes:
        if quote.quote_id in seen_ids:
            raise ValueError(f"Duplicate quote_id {quote.quote_id!r} in quotes array")
        seen_ids.add(quote.quote_id)

    for quote in quotes:
        existing_span_id = span_id_by_key.get((quote.block_id, quote.text))
        if existing_span_id is not None:
            quote_to_span[quote.quote_id] = existing_span_id
            continue

        block = blocks_by_id.get(quote.block_id)
        if block is None:
            raise ValueError(
                f"Quote {quote.quote_id!r} references unknown block_id {quote.block_id!r}"
            )

        meta = document_meta.get(block.document_id, {})
        raw_lines = document_lines.get(block.document_id)
        if raw_lines is None:
            raise FileNotFoundError(f"Missing filing text for document_id {block.document_id!r}")

        span_id = f"span_{len(spans) + 1:04d}"
        span = resolve_text_span(
            raw_lines,
            start_line=block.start_line,
            end_line=block.end_line,
            block_ids=[block.block_id],
            evidence_ids=[],
            anchor_text=quote.text,
            document_id=block.document_id,
            accession_number=meta.get("accession_number"),
            filing_type=meta.get("filing_type", "UNKNOWN"),
            span_id=span_id,
        )
        spans.append(span.model_dump(mode="json"))
        quote_to_span[quote.quote_id] = span_id
        span_id_by_key[(quote.block_id, quote.text)] = span_id

    return spans, quote_to_span


def _upgrade_raw_observation_artifact_v2(
    raw_artifact: RawObservationArtifactV2,
    *,
    quote_to_span: dict[str, str],
) -> dict:
    payload = raw_artifact.model_dump(mode="json")
    payload.pop("quotes", None)

    for party in payload["parties"]:
        party["evidence_span_ids"] = [
            quote_to_span[qid]
            for qid in party.pop("quote_ids", [])
            if qid in quote_to_span
        ]

    for cohort in payload["cohorts"]:
        cohort["evidence_span_ids"] = [
            quote_to_span[qid]
            for qid in cohort.pop("quote_ids", [])
            if qid in quote_to_span
        ]

    for observation in payload["observations"]:
        observation["evidence_span_ids"] = [
            quote_to_span[qid]
            for qid in observation.pop("quote_ids", [])
            if qid in quote_to_span
        ]

    return payload


def run_canonicalize_v2(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Upgrade quote-first v2 observation artifacts to canonical span-backed form."""
    paths = build_skill_paths(deal_slug, project_root=project_root)

    prefer_raw = paths.observations_raw_path.exists()
    loaded = load_observation_artifacts(
        paths,
        mode="quote_first" if prefer_raw else "canonical",
    )

    if loaded.mode == "quote_first":
        if not paths.chronology_blocks_path.exists():
            raise FileNotFoundError(f"Missing required input: {paths.chronology_blocks_path}")
        if not paths.document_registry_path.exists():
            raise FileNotFoundError(f"Missing required input: {paths.document_registry_path}")

        blocks = _load_chronology_blocks(paths.chronology_blocks_path)
        document_lines = _load_document_lines(paths.raw_root / deal_slug / "filings")
        document_meta = _load_document_registry(paths.document_registry_path)
        blocks_by_id = {block.block_id: block for block in blocks}
        spans, quote_to_span = _resolve_quotes_to_spans(
            list(loaded.raw_artifact.quotes),
            blocks_by_id=blocks_by_id,
            document_lines=document_lines,
            document_meta=document_meta,
        )
        observations_dict = _upgrade_raw_observation_artifact_v2(
            loaded.raw_artifact,
            quote_to_span=quote_to_span,
        )
    else:
        observations_dict = loaded.observations.model_dump(mode="json")
        spans = loaded.spans.model_dump(mode="json")["spans"]

    canonical_observations = ObservationArtifactV2.model_validate(observations_dict)
    span_registry = SpanRegistryArtifact.model_validate({"spans": spans})

    ensure_output_directories(paths)
    paths.observations_path.write_text(
        canonical_observations.model_dump_json(indent=2),
        encoding="utf-8",
    )
    paths.spans_v2_path.write_text(
        span_registry.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return 0
