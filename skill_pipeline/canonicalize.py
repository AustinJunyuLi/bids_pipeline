"""Canonicalize quote-first v2 observation artifacts into span-backed outputs."""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT

logger = logging.getLogger(__name__)
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


def _parse_sort_date(date_value) -> date | None:
    """Extract a date from a ResolvedDate dict or object."""
    if date_value is None:
        return None
    if isinstance(date_value, dict):
        raw = date_value.get("sort_date")
    else:
        raw = getattr(date_value, "sort_date", None)
    if raw is None:
        return None
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw))
    except (ValueError, TypeError):
        return None


def _repair_forward_requested_by(observations_dict: dict) -> dict:
    """Null out requested_by_observation_id when it points to a future solicitation."""
    obs_list = observations_dict.get("observations", [])
    obs_index = {obs["observation_id"]: obs for obs in obs_list}

    for obs in obs_list:
        if obs.get("obs_type") != "proposal":
            continue
        linked_id = obs.get("requested_by_observation_id")
        if not linked_id:
            continue
        linked_obs = obs_index.get(linked_id)
        if linked_obs is None:
            continue
        if linked_obs.get("obs_type") != "solicitation":
            logger.info(
                "Repair: %s requested_by_observation_id %r is not a solicitation — nullified",
                obs["observation_id"],
                linked_id,
            )
            obs["requested_by_observation_id"] = None
            continue
        proposal_date = _parse_sort_date(obs.get("date"))
        solicitation_date = _parse_sort_date(linked_obs.get("date"))
        if proposal_date is None or solicitation_date is None:
            continue
        if solicitation_date > proposal_date:
            logger.info(
                "Repair: %s requested_by_observation_id %r points forward "
                "(%s > %s) — nullified",
                obs["observation_id"],
                linked_id,
                solicitation_date.isoformat(),
                proposal_date.isoformat(),
            )
            obs["requested_by_observation_id"] = None

    return observations_dict


def _repair_outcome_bidder_refs(observations_dict: dict) -> dict:
    """Populate missing bidder refs on executed/restarted outcomes from summary text."""
    parties = observations_dict.get("parties", [])
    cohorts = observations_dict.get("cohorts", [])

    # Build name → party_id index for bidders only
    bidder_names: dict[str, str] = {}
    bidder_party_ids: set[str] = set()
    for party in parties:
        if party.get("role") != "bidder":
            continue
        pid = party["party_id"]
        bidder_party_ids.add(pid)
        for name_field in ("display_name", "canonical_name"):
            name = party.get(name_field)
            if name:
                bidder_names[name.lower()] = pid
        for alias in party.get("aliases", []):
            if alias:
                bidder_names[alias.lower()] = pid

    cohort_ids = {c["cohort_id"] for c in cohorts}

    for obs in observations_dict.get("observations", []):
        if obs.get("obs_type") != "outcome":
            continue
        if obs.get("outcome_kind") not in ("executed", "restarted"):
            continue

        all_refs = obs.get("subject_refs", []) + obs.get("counterparty_refs", [])
        has_bidder = any(
            ref in bidder_party_ids or ref in cohort_ids for ref in all_refs
        )
        if has_bidder:
            continue

        summary = (obs.get("summary") or "").lower()
        matched_ids: list[str] = []
        for name, pid in bidder_names.items():
            if name in summary and pid not in matched_ids:
                matched_ids.append(pid)

        if matched_ids:
            obs.setdefault("subject_refs", []).extend(matched_ids)
            logger.info(
                "Repair: %s (%s) missing bidder refs — added %s from summary",
                obs["observation_id"],
                obs["outcome_kind"],
                matched_ids,
            )

    return observations_dict


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
        observations_dict = _repair_forward_requested_by(observations_dict)
        observations_dict = _repair_outcome_bidder_refs(observations_dict)
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
