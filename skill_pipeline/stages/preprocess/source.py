from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from skill_pipeline.core.config import DEALS_DIR, RAW_DIR
from skill_pipeline.schemas.raw import RawDiscoveryManifest, RawDocumentRegistry
from skill_pipeline.schemas.source import (
    ChronologySelection,
    EvidenceItem,
    FilingCandidate,
    FrozenDocument,
)
from skill_pipeline.source.blocks import build_chronology_blocks
from skill_pipeline.source.evidence import scan_document_evidence
from skill_pipeline.source.locate import select_chronology


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
        document.accession_number or document.document_id: document
        for document in registry.documents
    }
    documents.update(
        {document.document_id: document for document in registry.documents}
    )

    if len(discovery.primary_candidates) != 1:
        raise ValueError("Expected exactly one primary candidate in discovery.json")
    if discovery.supplementary_candidates:
        raise ValueError(
            "supplementary_candidates must be empty under seed-only preprocess"
        )
    if len(registry.documents) != 1:
        raise ValueError(
            "document_registry.json must contain exactly one document under seed-only preprocess"
        )

    candidate = discovery.primary_candidates[0]
    document = _lookup_document(candidate, documents)
    if document is None:
        raise ValueError("discovery candidate is missing from document_registry.json")

    lines = _load_lines(project_root, document)
    if not lines:
        raise FileNotFoundError(
            f"No local raw primary filings available for {deal_slug}"
        )

    selection = select_chronology(
        lines,
        document_id=document.document_id,
        accession_number=document.accession_number,
        filing_type=document.filing_type,
        run_id=run_id,
        deal_slug=deal_slug,
    )
    blocks = build_chronology_blocks(lines, selection=selection)
    evidence_items = _dedupe_evidence_items(
        scan_document_evidence(
            lines,
            document_id=document.document_id,
            accession_number=document.accession_number,
            filing_type=document.filing_type,
        )
    )

    source_dir = deals_dir / deal_slug / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    _remove_stale_source_artifacts(source_dir, registry.documents)
    _materialize_source_filings(project_root, source_dir, registry.documents)
    _atomic_write_json(
        source_dir / "chronology_selection.json", selection.model_dump(mode="json")
    )
    _atomic_write_jsonl(
        source_dir / "chronology_blocks.jsonl",
        [block.model_dump(mode="json") for block in blocks],
    )
    _atomic_write_jsonl(
        source_dir / "evidence_items.jsonl",
        [item.model_dump(mode="json") for item in evidence_items],
    )
    _atomic_write_json(
        source_dir / "chronology.json",
        _legacy_chronology_bookmark(document, selection),
    )

    return {
        "selected_document_id": document.document_id,
        "selected_accession_number": document.accession_number,
        "confidence": selection.confidence,
        "confidence_factors": selection.confidence_factors,
        "block_count": len(blocks),
        "evidence_count": len(evidence_items),
        "candidate_count": 1,
        "top_primary_candidate_id": candidate.document_id,
        "scanned_document_count": 1,
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
) -> list[str]:
    path = project_root / document.txt_path
    if path.exists():
        return path.read_text(encoding="utf-8").splitlines()
    return []


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


def _remove_stale_source_artifacts(
    source_dir: Path,
    documents: list[FrozenDocument],
) -> None:
    stale_snippets_path = source_dir / "supplementary_snippets.jsonl"
    if stale_snippets_path.exists():
        stale_snippets_path.unlink()

    filings_dir = source_dir / "filings"
    if not filings_dir.exists():
        return

    expected_names: set[str] = set()
    for document in documents:
        aliases = {document.document_id}
        if document.accession_number:
            aliases.add(document.accession_number)
        for alias in aliases:
            expected_names.add(f"{alias}.txt")
            if document.html_path:
                expected_names.add(f"{alias}.html")
            if document.md_path:
                expected_names.add(f"{alias}.md")

    for path in filings_dir.iterdir():
        if path.is_file() and path.name not in expected_names:
            path.unlink()


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
            _copy_if_present(
                project_root, document.txt_path, filings_dir / f"{alias}.txt"
            )
            if document.html_path:
                _copy_if_present(
                    project_root, document.html_path, filings_dir / f"{alias}.html"
                )
            if document.md_path:
                _copy_if_present(
                    project_root, document.md_path, filings_dir / f"{alias}.md"
                )


def _copy_if_present(project_root: Path, relative_path: str, destination: Path) -> None:
    source = project_root / relative_path
    if not source.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.read_bytes() == source.read_bytes():
        return
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=destination.parent, delete=False
    ) as handle:
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
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)
