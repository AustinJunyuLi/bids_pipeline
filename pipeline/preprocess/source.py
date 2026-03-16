from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR, RAW_DIR
from pipeline.models.raw import RawDiscoveryManifest, RawDocumentRegistry
from pipeline.models.source import ChronologySelection, FilingCandidate, FrozenDocument
from pipeline.source.blocks import build_chronology_blocks
from pipeline.source.locate import select_chronology
from pipeline.source.supplementary import index_supplementary_snippets


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

    primary_candidates = sorted(discovery.primary_candidates, key=_candidate_sort_key)
    evaluations: list[tuple[FilingCandidate, FrozenDocument, ChronologySelection, list[str]]] = []
    for candidate in primary_candidates:
        document = _lookup_document(candidate, documents)
        if document is None:
            continue
        lines = _load_lines(project_root, document)
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
    snippets = []
    for candidate in sorted(discovery.supplementary_candidates, key=_candidate_sort_key):
        document = _lookup_document(candidate, documents)
        if document is None:
            continue
        lines = _load_lines(project_root, document)
        snippets.extend(
            index_supplementary_snippets(
                lines,
                document_id=document.document_id,
                filing_type=document.filing_type,
            )
        )

    source_dir = deals_dir / deal_slug / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    _materialize_source_filings(project_root, source_dir, registry.documents)
    _write_json(source_dir / "chronology_selection.json", best_selection.model_dump(mode="json"))
    _write_jsonl(source_dir / "chronology_blocks.jsonl", [block.model_dump(mode="json") for block in blocks])
    _write_jsonl(
        source_dir / "supplementary_snippets.jsonl",
        [snippet.model_dump(mode="json") for snippet in snippets],
    )
    _write_json(
        source_dir / "chronology.json",
        _legacy_chronology_bookmark(best_document, best_selection),
    )

    return {
        "selected_document_id": best_document.document_id,
        "selected_accession_number": best_document.accession_number,
        "confidence": best_selection.confidence,
        "block_count": len(blocks),
        "snippet_count": len(snippets),
        "candidate_count": len(evaluations),
        "top_primary_candidate_id": best_candidate.document_id,
    }


def _lookup_document(
    candidate: FilingCandidate,
    documents: dict[str, FrozenDocument],
) -> FrozenDocument | None:
    if candidate.accession_number and candidate.accession_number in documents:
        return documents[candidate.accession_number]
    return documents.get(candidate.document_id)


def _load_lines(project_root: Path, document: FrozenDocument) -> list[str]:
    txt_path = project_root / document.txt_path
    return txt_path.read_text(encoding="utf-8").splitlines()


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
    return (
        0 if selection.selected_candidate is not None else 1,
        CONFIDENCE_RANK[selection.confidence],
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


def _materialize_source_filings(
    project_root: Path,
    source_dir: Path,
    documents: list[FrozenDocument],
) -> None:
    filings_dir = source_dir / "filings"
    filings_dir.mkdir(parents=True, exist_ok=True)
    for document in documents:
        _copy_if_present(project_root, document.txt_path, filings_dir / f"{document.document_id}.txt")
        if document.html_path:
            _copy_if_present(project_root, document.html_path, filings_dir / f"{document.document_id}.html")
        if document.md_path:
            _copy_if_present(project_root, document.md_path, filings_dir / f"{document.document_id}.md")


def _copy_if_present(project_root: Path, relative_path: str, destination: Path) -> None:
    source = project_root / relative_path
    if not source.exists():
        return
    shutil.copy2(source, destination)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, payloads: list[dict[str, Any]]) -> None:
    text = "\n".join(json.dumps(payload) for payload in payloads)
    path.write_text(text, encoding="utf-8")
