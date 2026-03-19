from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from skill_pipeline.config import DEALS_DIR, RAW_DIR
from skill_pipeline.pipeline_models.raw import RawDiscoveryManifest, RawDocumentRegistry
from skill_pipeline.pipeline_models.source import ChronologySelection, EvidenceItem, FilingCandidate, FrozenDocument
from skill_pipeline.source.blocks import build_chronology_blocks
from skill_pipeline.source.evidence import scan_document_evidence
from skill_pipeline.source.locate import select_chronology
from skill_pipeline.source.supplementary import evidence_items_to_snippets


CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2, "none": 3}


def preprocess_source_deal(
    deal_slug: str,
    *,
    run_id: str,
    raw_dir: Path = RAW_DIR,
    deals_dir: Path = DEALS_DIR,
) -> dict[str, Any]:
    raw_deal_dir = raw_dir / deal_slug
    discovery = RawDiscoveryManifest.model_validate_json(
        (raw_deal_dir / "discovery.json").read_text(encoding="utf-8")
    )
    registry = RawDocumentRegistry.model_validate_json(
        (raw_deal_dir / "document_registry.json").read_text(encoding="utf-8")
    )

    project_root = raw_dir.parent
    documents = {
        document.accession_number or document.document_id: document for document in registry.documents
    }
    documents.update({document.document_id: document for document in registry.documents})

    document_lines: dict[str, list[str]] = {}
    primary_candidates = sorted(discovery.primary_candidates, key=_candidate_sort_key)
    evaluations: list[tuple[FilingCandidate, FrozenDocument, ChronologySelection, list[str]]] = []
    for candidate in primary_candidates:
        document = _lookup_document(candidate, documents)
        if document is None:
            continue
        lines = _load_lines(project_root, document, deal_slug=deal_slug, deals_dir=deals_dir)
        if not lines:
            continue
        document_lines[document.document_id] = lines
        selection = select_chronology(
            lines,
            document_id=document.document_id,
            accession_number=document.accession_number,
            filing_type=document.filing_type,
            run_id=run_id,
            deal_slug=deal_slug,
        )
        evaluations.append((candidate, document, selection, lines))

    if not evaluations:
        raise FileNotFoundError(f"No local raw primary filings available for {deal_slug}")

    best_candidate, best_document, best_selection, best_lines = min(
        evaluations,
        key=lambda item: _selection_sort_key(item[2], item[0]),
    )

    blocks = build_chronology_blocks(best_lines, selection=best_selection)

    all_evidence_items: list[EvidenceItem] = []
    all_candidates = [*discovery.primary_candidates, *discovery.supplementary_candidates]
    seen_document_ids: set[str] = set()
    for candidate in sorted(all_candidates, key=_candidate_sort_key):
        document = _lookup_document(candidate, documents)
        if document is None or document.document_id in seen_document_ids:
            continue
        seen_document_ids.add(document.document_id)
        lines = document_lines.get(document.document_id)
        if lines is None:
            lines = _load_lines(project_root, document, deal_slug=deal_slug, deals_dir=deals_dir)
            if not lines:
                continue
            document_lines[document.document_id] = lines
        all_evidence_items.extend(
            scan_document_evidence(
                lines,
                document_id=document.document_id,
                accession_number=document.accession_number,
                filing_type=document.filing_type,
            )
        )
    all_evidence_items = _dedupe_evidence_items(all_evidence_items)
    snippets = evidence_items_to_snippets([item for item in all_evidence_items if item.document_id != best_document.document_id])

    source_dir = deals_dir / deal_slug / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    _materialize_source_filings(project_root, source_dir, registry.documents)
    _atomic_write_json(source_dir / "chronology_selection.json", best_selection.model_dump(mode="json"))
    _atomic_write_jsonl(
        source_dir / "chronology_blocks.jsonl",
        [block.model_dump(mode="json") for block in blocks],
    )
    _atomic_write_jsonl(
        source_dir / "evidence_items.jsonl",
        [item.model_dump(mode="json") for item in all_evidence_items],
    )
    _atomic_write_jsonl(
        source_dir / "supplementary_snippets.jsonl",
        [snippet.model_dump(mode="json") for snippet in snippets],
    )
    _atomic_write_json(
        source_dir / "chronology.json",
        _legacy_chronology_bookmark(best_document, best_selection),
    )

    return {
        "selected_document_id": best_document.document_id,
        "selected_accession_number": best_document.accession_number,
        "confidence": best_selection.confidence,
        "confidence_factors": best_selection.confidence_factors,
        "block_count": len(blocks),
        "snippet_count": len(snippets),
        "evidence_count": len(all_evidence_items),
        "candidate_count": len(evaluations),
        "top_primary_candidate_id": best_candidate.document_id,
        "scanned_document_count": len(seen_document_ids),
    }


def _lookup_document(
    candidate: FilingCandidate,
    documents: dict[str, FrozenDocument],
) -> FrozenDocument | None:
    if candidate.accession_number and candidate.accession_number in documents:
        return documents[candidate.accession_number]
    return documents.get(candidate.document_id)


def _load_lines(
    project_root: Path,
    document: FrozenDocument,
    *,
    deal_slug: str,
    deals_dir: Path,
) -> list[str]:
    candidate_paths = [project_root / document.txt_path]
    accession_or_document = document.accession_number or document.document_id
    candidate_paths.append(deals_dir / deal_slug / "source" / "filings" / f"{accession_or_document}.txt")
    candidate_paths.append(deals_dir / deal_slug / "source" / "filings" / f"{document.document_id}.txt")
    for path in candidate_paths:
        if path.exists():
            return path.read_text(encoding="utf-8").splitlines()
    return []


def _candidate_sort_key(candidate: FilingCandidate) -> tuple[Any, ...]:
    ranking = candidate.ranking_features
    return (
        0 if ranking.get("seed_accession_match") else 1,
        ranking.get("form_preference", float("inf")),
        ranking.get("days_from_announcement", float("inf")),
        candidate.accession_number or candidate.document_id,
    )


def _selection_sort_key(
    selection: ChronologySelection,
    candidate: FilingCandidate,
) -> tuple[Any, ...]:
    confidence_factors = selection.confidence_factors or {}
    ambiguity_risk = confidence_factors.get("ambiguity_risk", "high")
    ambiguity_rank = {"low": 0, "medium": 1, "high": 2}.get(ambiguity_risk, 3)
    coverage_assessment = confidence_factors.get("coverage_assessment", "short_uncertain")
    coverage_rank = {
        "full": 0,
        "adequate": 1,
        "short_but_probably_complete": 2,
        "short_uncertain": 3,
    }.get(coverage_assessment, 4)
    return (
        0 if selection.selected_candidate is not None else 1,
        ambiguity_rank,
        CONFIDENCE_RANK[selection.confidence],
        coverage_rank,
        _candidate_sort_key(candidate),
    )


def _legacy_chronology_bookmark(
    document: FrozenDocument,
    selection: ChronologySelection,
) -> dict[str, Any]:
    candidate = selection.selected_candidate
    return {
        "accession_number": document.accession_number,
        "document_id": document.document_id,
        "heading": candidate.heading_text if candidate is not None else None,
        "start_line": candidate.start_line if candidate is not None else None,
        "end_line": candidate.end_line if candidate is not None else None,
        "confidence": selection.confidence,
        "txt_path": document.txt_path,
    }


def _dedupe_evidence_items(items: list[EvidenceItem]) -> list[EvidenceItem]:
    deduped: list[EvidenceItem] = []
    seen: set[tuple[str, str, int, int, str]] = set()
    for item in items:
        key = (
            item.document_id,
            item.evidence_type.value,
            item.start_line,
            item.end_line,
            " ".join(item.raw_text.lower().split()),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _materialize_source_filings(
    project_root: Path,
    source_dir: Path,
    documents: list[FrozenDocument],
) -> None:
    filings_dir = source_dir / "filings"
    filings_dir.mkdir(parents=True, exist_ok=True)
    for document in documents:
        aliases = {document.document_id}
        if document.accession_number:
            aliases.add(document.accession_number)
        for alias in aliases:
            _copy_if_present(project_root, document.txt_path, filings_dir / f"{alias}.txt")
            if document.html_path:
                _copy_if_present(project_root, document.html_path, filings_dir / f"{alias}.html")
            if document.md_path:
                _copy_if_present(project_root, document.md_path, filings_dir / f"{alias}.md")


def _copy_if_present(project_root: Path, relative_path: str, destination: Path) -> None:
    source = project_root / relative_path
    if not source.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.read_bytes() == source.read_bytes():
        return
    with tempfile.NamedTemporaryFile(mode="wb", dir=destination.parent, delete=False) as handle:
        handle.write(source.read_bytes())
        temp_path = Path(handle.name)
    temp_path.replace(destination)
    shutil.copystat(source, destination)


def _atomic_write_json(path: Path, payload: Any) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2))


def _atomic_write_jsonl(path: Path, payloads: list[dict[str, Any]]) -> None:
    text = "\n".join(json.dumps(payload) for payload in payloads)
    _atomic_write_text(path, text)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)
