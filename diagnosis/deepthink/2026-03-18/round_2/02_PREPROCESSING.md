# Preprocessing Pipeline

---

## pipeline/raw/__init__.py
```python
from pipeline.raw.discover import build_raw_discovery_manifest, collect_filing_candidates
from pipeline.raw.fetch import (
    atomic_write_json,
    fetch_filing_contents,
    freeze_raw_filing,
    text_sha256,
    write_immutable_text,
)
from pipeline.raw.stage import build_edgar_search_fn, fetch_raw_deal

__all__ = [
    "atomic_write_json",
    "build_edgar_search_fn",
    "build_raw_discovery_manifest",
    "collect_filing_candidates",
    "fetch_filing_contents",
    "fetch_raw_deal",
    "freeze_raw_filing",
    "text_sha256",
    "write_immutable_text",
]
```

---

## pipeline/raw/discover.py
```python
from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from pipeline.config import PRIMARY_FILING_TYPES, SUPPLEMENTARY_FILING_TYPES
from pipeline.models.raw import RawDiscoveryManifest
from pipeline.models.source import FilingCandidate, SeedDeal
from pipeline.source.discovery import FallbackLookupFn, SearchFn, search_candidates_with_fallback


def collect_filing_candidates(
    seed: SeedDeal,
    *,
    filing_types: Iterable[str],
    filing_family: str,
    search_fn: SearchFn,
    fallback_lookup_fn: FallbackLookupFn | None = None,
    top_k_per_form: int = 3,
) -> list[FilingCandidate]:
    candidates: list[FilingCandidate] = []
    for filing_type in filing_types:
        candidates.extend(
            search_candidates_with_fallback(
                seed,
                filing_type=filing_type,
                filing_family=filing_family,
                search_fn=search_fn,
                fallback_lookup_fn=fallback_lookup_fn,
                top_k=top_k_per_form,
            )
        )
    return _dedupe_candidates(candidates)


def build_raw_discovery_manifest(
    seed: SeedDeal,
    *,
    run_id: str,
    cik: str | None = None,
    primary_filing_types: Iterable[str] = PRIMARY_FILING_TYPES,
    supplementary_filing_types: Iterable[str] = SUPPLEMENTARY_FILING_TYPES,
    search_fn: SearchFn,
    fallback_lookup_fn: FallbackLookupFn | None = None,
    top_k_per_form: int = 3,
) -> RawDiscoveryManifest:
    primary_candidates = collect_filing_candidates(
        seed,
        filing_types=primary_filing_types,
        filing_family="primary",
        search_fn=search_fn,
        fallback_lookup_fn=fallback_lookup_fn,
        top_k_per_form=top_k_per_form,
    )
    supplementary_candidates = collect_filing_candidates(
        seed,
        filing_types=supplementary_filing_types,
        filing_family="supplementary",
        search_fn=search_fn,
        fallback_lookup_fn=fallback_lookup_fn,
        top_k_per_form=top_k_per_form,
    )
    return RawDiscoveryManifest(
        run_id=run_id,
        deal_slug=seed.deal_slug,
        seed=seed,
        cik=cik,
        primary_candidates=primary_candidates,
        supplementary_candidates=supplementary_candidates,
    )


def _dedupe_candidates(candidates: list[FilingCandidate]) -> list[FilingCandidate]:
    unique: dict[str, FilingCandidate] = {}
    for candidate in sorted(candidates, key=_candidate_sort_key):
        key = candidate.accession_number or candidate.document_id
        unique.setdefault(key, candidate)
    return list(unique.values())


def _candidate_sort_key(candidate: FilingCandidate) -> tuple[Any, ...]:
    ranking = candidate.ranking_features
    return (
        0 if ranking.get("seed_accession_match") else 1,
        ranking.get("form_preference", float("inf")),
        ranking.get("days_from_announcement", float("inf")),
        candidate.accession_number or candidate.document_id,
    )
```

---

## pipeline/raw/fetch.py
```python
from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable
from urllib.request import urlopen

from pipeline.models.source import FilingCandidate, FrozenDocument

try:  # pragma: no cover - optional dependency in tests.
    from edgar import get_by_accession_number as _edgar_get_by_accession_number
except ModuleNotFoundError:  # pragma: no cover
    _edgar_get_by_accession_number = None


def _default_get_filing(accession_number: str) -> Any:
    if _edgar_get_by_accession_number is None:
        raise ModuleNotFoundError(
            "edgar is required for live SEC fetches; pass get_filing_fn in tests or install edgartools."
        )
    return _edgar_get_by_accession_number(accession_number)


def write_immutable_text(path: Path, content: str) -> None:
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing != content:
            raise FileExistsError(f"Immutable raw file already exists with different content: {path}")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, default=str))


def text_sha256(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def fetch_filing_contents(
    accession_number: str,
    *,
    sec_url: str | None = None,
    get_filing_fn: Callable[[str], Any] | None = None,
    http_get_fn: Callable[[str], str] | None = None,
) -> tuple[str | None, str]:
    filing = (get_filing_fn or _default_get_filing)(accession_number)
    html_text = None
    txt_text = None
    if filing is not None:
        html_text = filing.html()
        txt_text = filing.text()

    if txt_text:
        return html_text, txt_text

    if sec_url is None:
        raise RuntimeError(f"Failed to fetch filing text for {accession_number}")

    http_get_fn = http_get_fn or _default_http_get
    html_text = http_get_fn(sec_url)
    return html_text, html_text


def freeze_raw_filing(
    candidate: FilingCandidate,
    *,
    deal_slug: str,
    raw_dir: Path,
    html_text: str | None,
    txt_text: str,
    md_text: str | None = None,
) -> FrozenDocument:
    filings_dir = raw_dir / deal_slug / "filings"
    stem = candidate.document_id
    txt_path = filings_dir / f"{stem}.txt"
    write_immutable_text(txt_path, txt_text)

    html_path = None
    if html_text is not None:
        html_path = filings_dir / f"{stem}.html"
        write_immutable_text(html_path, html_text)

    md_path = None
    if md_text is not None:
        md_path = filings_dir / f"{stem}.md"
        write_immutable_text(md_path, md_text)

    project_root = raw_dir.parent
    return FrozenDocument(
        document_id=candidate.document_id,
        accession_number=candidate.accession_number,
        filing_type=candidate.filing_type,
        filing_date=candidate.filing_date,
        html_path=str(html_path.relative_to(project_root)) if html_path else None,
        txt_path=str(txt_path.relative_to(project_root)),
        md_path=str(md_path.relative_to(project_root)) if md_path else None,
        sha256_txt=text_sha256(txt_text),
        sha256_html=text_sha256(html_text) if html_text is not None else None,
        byte_count_txt=len(txt_text.encode("utf-8")),
        fetched_at=datetime.now(UTC),
    )


def _default_http_get(url: str) -> str:
    with urlopen(url) as response:  # noqa: S310 - SEC fetch path only.
        return response.read().decode("utf-8", errors="replace")
```

---

## pipeline/raw/stage.py
```python
from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

from pipeline.config import PRIMARY_FILING_TYPES, RAW_DIR, SUPPLEMENTARY_FILING_TYPES
from pipeline.models.raw import RawDocumentRegistry
from pipeline.models.source import SeedDeal
from pipeline.raw.discover import build_raw_discovery_manifest
from pipeline.raw.fetch import atomic_write_json, fetch_filing_contents, freeze_raw_filing
from pipeline.source.ranking import extract_cik_from_url, search_terms_for_form

try:  # pragma: no cover - optional dependency in tests.
    from edgar import Company, find_company, get_by_accession_number, set_identity
except ModuleNotFoundError:  # pragma: no cover
    Company = None
    find_company = None
    get_by_accession_number = None
    set_identity = None


DEFAULT_IDENTITY = "Austin Li austin@example.com"


def fetch_raw_deal(
    seed: SeedDeal,
    *,
    run_id: str,
    raw_dir: Any = RAW_DIR,
    primary_filing_types: Iterable[str] = PRIMARY_FILING_TYPES,
    supplementary_filing_types: Iterable[str] = SUPPLEMENTARY_FILING_TYPES,
    search_fn: Any | None = None,
    fallback_lookup_fn: Any | None = None,
    fetch_contents_fn: Any = fetch_filing_contents,
    identity: str | None = None,
    search_limit: int = 25,
) -> dict[str, Any]:
    raw_dir = RAW_DIR if raw_dir is None else raw_dir
    if fallback_lookup_fn is None:
        fallback_lookup_fn = get_by_accession_number
    if search_fn is None:
        search_fn = build_edgar_search_fn(seed, identity=identity, search_limit=search_limit)

    discovery = build_raw_discovery_manifest(
        seed,
        run_id=run_id,
        cik=extract_cik_from_url(seed.primary_url_seed),
        primary_filing_types=primary_filing_types,
        supplementary_filing_types=supplementary_filing_types,
        search_fn=search_fn,
        fallback_lookup_fn=fallback_lookup_fn,
    )
    raw_deal_dir = raw_dir / seed.deal_slug
    raw_deal_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(raw_deal_dir / "discovery.json", discovery.model_dump(mode="json"))

    documents = []
    seen_keys: set[str] = set()
    for candidate in [*discovery.primary_candidates, *discovery.supplementary_candidates]:
        key = candidate.accession_number or candidate.document_id
        if key in seen_keys:
            continue
        seen_keys.add(key)
        accession = candidate.accession_number or candidate.document_id
        html_text, txt_text = fetch_contents_fn(accession, sec_url=candidate.sec_url)
        documents.append(
            freeze_raw_filing(
                candidate,
                deal_slug=seed.deal_slug,
                raw_dir=raw_dir,
                html_text=html_text,
                txt_text=txt_text,
            )
        )

    registry = RawDocumentRegistry(run_id=run_id, deal_slug=seed.deal_slug, documents=documents)
    atomic_write_json(raw_deal_dir / "document_registry.json", registry.model_dump(mode="json"))
    return {
        "deal_slug": seed.deal_slug,
        "cik": discovery.cik,
        "primary_candidate_count": len(discovery.primary_candidates),
        "supplementary_candidate_count": len(discovery.supplementary_candidates),
        "frozen_count": len(documents),
        "discovery_path": str((raw_deal_dir / "discovery.json").relative_to(raw_dir.parent)),
        "document_registry_path": str((raw_deal_dir / "document_registry.json").relative_to(raw_dir.parent)),
    }


def build_edgar_search_fn(
    seed: SeedDeal,
    *,
    identity: str | None = None,
    search_limit: int = 25,
) -> Any:
    company = _resolve_company(seed, identity=identity)

    def search_fn(filing_type: str) -> list[dict[str, Any]]:
        forms = list(search_terms_for_form(filing_type))
        filings = company.get_filings(
            form=forms if len(forms) > 1 else forms[0],
            amendments=True,
            trigger_full_load=False,
        )
        if filings.empty:
            return []
        return [
            {
                "accession_number": filing.accession_number,
                "filing_type": filing.form,
                "filing_date": filing.filing_date,
                "url": filing.url,
            }
            for filing in filings.head(search_limit)
        ]

    return search_fn


def _resolve_company(seed: SeedDeal, *, identity: str | None = None):
    if Company is None or find_company is None:
        raise ModuleNotFoundError(
            "edgar is required for live company resolution; pass search_fn in tests or install edgartools."
        )
    _set_identity(identity)
    cik = extract_cik_from_url(seed.primary_url_seed)
    if cik:
        return Company(cik)

    results = find_company(seed.target_name)
    if results.empty:
        raise ValueError(f"Unable to resolve company for seed target {seed.target_name!r}")
    return results[0]


def _set_identity(identity: str | None = None) -> None:
    if set_identity is None:
        raise ModuleNotFoundError(
            "edgar is required for live SEC access; pass search_fn in tests or install edgartools."
        )
    selected = identity
    if selected is None:
        for env_name in ("PIPELINE_SEC_IDENTITY", "SEC_IDENTITY", "EDGAR_IDENTITY"):
            selected = os.getenv(env_name)
            if selected:
                break
    set_identity(selected or DEFAULT_IDENTITY)
```

---

## pipeline/preprocess/source.py
```python
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR, RAW_DIR
from pipeline.models.raw import RawDiscoveryManifest, RawDocumentRegistry
from pipeline.models.source import ChronologySelection, EvidenceItem, FilingCandidate, FrozenDocument
from pipeline.source.blocks import build_chronology_blocks
from pipeline.source.evidence import scan_document_evidence
from pipeline.source.locate import select_chronology
from pipeline.source.supplementary import evidence_items_to_snippets


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
```

---

## pipeline/source/__init__.py
```python
from pipeline.source.blocks import build_chronology_blocks
from pipeline.source.discovery import load_filing_overrides, search_candidates_with_fallback
from pipeline.source.fetch import atomic_write_json, atomic_write_text, fetch_filing_contents, freeze_filing
from pipeline.source.locate import collect_chronology_candidates, locate_chronology, select_chronology
from pipeline.source.ranking import (
    canonical_form_name,
    extract_accession_from_url,
    extract_cik_from_url,
    parse_filing_date,
    rank_filing_candidates,
    search_terms_for_form,
)
from pipeline.source.supplementary import index_supplementary_snippets

_atomic_write_text = atomic_write_text
_atomic_write_json = atomic_write_json
_canonical_form_name = canonical_form_name
_search_terms_for_form = search_terms_for_form

__all__ = [
    "_atomic_write_json",
    "_atomic_write_text",
    "_canonical_form_name",
    "_search_terms_for_form",
    "atomic_write_json",
    "atomic_write_text",
    "build_chronology_blocks",
    "canonical_form_name",
    "collect_chronology_candidates",
    "extract_accession_from_url",
    "extract_cik_from_url",
    "fetch_filing_contents",
    "freeze_filing",
    "index_supplementary_snippets",
    "load_filing_overrides",
    "locate_chronology",
    "parse_filing_date",
    "rank_filing_candidates",
    "search_candidates_with_fallback",
    "search_terms_for_form",
    "select_chronology",
]
```

---

## pipeline/source/blocks.py
```python
from __future__ import annotations

from pipeline.models.source import ChronologyBlock, ChronologySelection
from pipeline.source.locate import looks_like_heading


def build_chronology_blocks(
    lines: list[str],
    *,
    selection: ChronologySelection,
) -> list[ChronologyBlock]:
    candidate = selection.selected_candidate
    if candidate is None:
        return []

    selected_lines = lines[candidate.start_line - 1 : candidate.end_line]
    blocks: list[ChronologyBlock] = []
    buffer: list[str] = []
    block_start: int | None = None
    ordinal = 1

    def flush(is_heading: bool = False) -> None:
        nonlocal buffer, block_start, ordinal
        if not buffer or block_start is None:
            return
        block_end = block_start + len(buffer) - 1
        raw_text = "\n".join(buffer)
        clean_text = " ".join(line.strip() for line in buffer if line.strip())
        blocks.append(
            ChronologyBlock(
                block_id=f"B{ordinal:03d}",
                document_id=candidate.document_id,
                ordinal=ordinal,
                start_line=block_start,
                end_line=block_end,
                raw_text=raw_text,
                clean_text=clean_text,
                is_heading=is_heading,
            )
        )
        ordinal += 1
        buffer = []
        block_start = None

    for offset, line in enumerate(selected_lines, start=candidate.start_line):
        stripped = line.strip()
        if not stripped:
            flush()
            continue

        line_is_heading = looks_like_heading(line)
        if line_is_heading and not buffer:
            buffer = [line]
            block_start = offset
            flush(is_heading=True)
            continue

        if block_start is None:
            block_start = offset
        buffer.append(line)

    flush()
    return blocks
```

---

## pipeline/source/discovery.py
```python
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from pipeline.models.source import FilingCandidate, SeedDeal
from pipeline.source.ranking import extract_accession_from_url, rank_filing_candidates


SearchFn = Callable[[str], list[Any]]
FallbackLookupFn = Callable[[str], Any | None]


def search_candidates_with_fallback(
    seed: SeedDeal,
    *,
    filing_type: str,
    filing_family: str,
    search_fn: SearchFn,
    fallback_lookup_fn: FallbackLookupFn | None = None,
    top_k: int = 3,
) -> list[FilingCandidate]:
    try:
        search_results = list(search_fn(filing_type))
    except Exception:
        search_results = []

    if not search_results and fallback_lookup_fn is not None:
        seed_accession = extract_accession_from_url(seed.primary_url_seed)
        if seed_accession:
            fallback_result = fallback_lookup_fn(seed_accession)
            if fallback_result is not None:
                search_results = [dict(_coerce_result(fallback_result), source_origin="seed_accession")]

    return rank_filing_candidates(
        seed,
        search_results,
        filing_family=filing_family,
        top_k=top_k,
    )


def load_filing_overrides(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}

    import yaml

    with path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError("filing_override.yaml must contain a mapping")
    return payload


def _coerce_result(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return dict(result)
    return {
        "accession_number": getattr(result, "accession_number", None),
        "filing_type": getattr(result, "filing_type", None) or getattr(result, "form", None),
        "filing_date": getattr(result, "filing_date", None),
        "url": getattr(result, "url", None),
    }
```

---

## pipeline/source/evidence.py
```python
from __future__ import annotations

import re
from dataclasses import dataclass

from pipeline.models.source import EvidenceItem, EvidenceType
from pipeline.source.locate import looks_like_heading


DATE_FRAGMENT_RE = re.compile(
    r"(?i)\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"(?:\s+\d{1,2},\s+\d{4}|\s+\d{4})?\b|\bq[1-4]\s+\d{4}\b|\b(?:early|mid|late)[-\s]+"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4}\b"
)
MONEY_RE = re.compile(
    r"(?i)\$\s?\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:to|-|–)\s*\$?\d+(?:,\d{3})*(?:\.\d+)?)?"
    r"(?:\s+per\s+share)?|\b\d+(?:\.\d+)?\s*(?:million|billion)\b"
)
ACTION_TERMS = {
    "met",
    "meeting",
    "contacted",
    "called",
    "submitted",
    "received",
    "proposed",
    "proposal",
    "offer",
    "offered",
    "signed",
    "executed",
    "entered into",
    "engaged",
    "retained",
    "authorized",
    "withdrew",
    "declined",
    "announced",
    "requested",
    "sent",
    "delivered",
    "discussed",
}
ACTOR_TERMS = {
    "advisor",
    "advisors",
    "law firm",
    "counsel",
    "investment bank",
    "financial advisor",
    "legal advisor",
    "special committee",
    "transaction committee",
    "shareholder",
    "stockholder",
    "activist",
    "consortium",
    "party ",
    "bidder ",
    "parent",
}
PROCESS_TERMS = {
    "confidentiality agreement",
    "standstill",
    "due diligence",
    "management presentation",
    "strategic alternatives",
    "process letter",
    "draft merger agreement",
    "marked-up",
    "markup of the agreement",
    "go-shop",
    "non-disclosure",
    "nda",
    "confidentiality and standstill",
}
OUTCOME_TERMS = {
    "closed",
    "closing",
    "effective time",
    "executed",
    "merger agreement",
    "lawsuit",
    "litigation",
    "stockholder approval",
    "shareholder approval",
    "vote",
    "termination fee",
    "terminated",
}
PRESS_RELEASE_TERMS = {"press release", "announced"}
ACTIVIST_TERMS = {"activist", "shareholder", "stockholder", "jana", "gamco", "gabelli"}


@dataclass(slots=True)
class Paragraph:
    start_line: int
    end_line: int
    text: str


def iter_paragraphs(lines: list[str]) -> list[Paragraph]:
    paragraphs: list[Paragraph] = []
    buffer: list[str] = []
    start_line: int | None = None

    def flush(end_line: int) -> None:
        nonlocal buffer, start_line
        if not buffer or start_line is None:
            buffer = []
            start_line = None
            return
        paragraphs.append(
            Paragraph(
                start_line=start_line,
                end_line=end_line,
                text="\n".join(buffer),
            )
        )
        buffer = []
        start_line = None

    for idx, line in enumerate(lines, start=1):
        if not line.strip():
            flush(idx - 1)
            continue
        if start_line is None:
            start_line = idx
        buffer.append(line)
    flush(len(lines))
    return paragraphs


def scan_document_evidence(
    lines: list[str],
    *,
    document_id: str,
    filing_type: str,
    accession_number: str | None = None,
) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    seen: set[tuple[str, int, int, str]] = set()
    ordinal = 1

    for paragraph in iter_paragraphs(lines):
        raw_text = paragraph.text.strip()
        if not raw_text:
            continue
        if looks_like_heading(raw_text) and len(raw_text.split()) <= 18:
            continue

        lowered = _normalize(raw_text)
        matches = _classify_paragraph(raw_text, lowered)
        for evidence_type, matched_terms in matches:
            key = (evidence_type.value, paragraph.start_line, paragraph.end_line, lowered)
            if key in seen:
                continue
            seen.add(key)
            evidence.append(
                EvidenceItem(
                    evidence_id=(
                        f"{accession_number}:E{ordinal:04d}"
                        if accession_number
                        else f"{document_id}:E{ordinal:04d}"
                    ),
                    document_id=document_id,
                    accession_number=accession_number,
                    filing_type=filing_type,
                    start_line=paragraph.start_line,
                    end_line=paragraph.end_line,
                    raw_text=raw_text,
                    evidence_type=evidence_type,
                    confidence=_score_confidence(evidence_type, matched_terms, raw_text),
                    matched_terms=matched_terms,
                    date_text=_first_match(DATE_FRAGMENT_RE, raw_text),
                    actor_hint=_extract_actor_hint(raw_text),
                    value_hint=_first_match(MONEY_RE, raw_text),
                    note=_build_note(evidence_type, matched_terms),
                )
            )
            ordinal += 1

    return evidence


def group_evidence_by_type(items: list[EvidenceItem]) -> dict[EvidenceType, list[EvidenceItem]]:
    grouped: dict[EvidenceType, list[EvidenceItem]] = {evidence_type: [] for evidence_type in EvidenceType}
    for item in items:
        grouped.setdefault(item.evidence_type, []).append(item)
    return grouped


def _classify_paragraph(raw_text: str, lowered: str) -> list[tuple[EvidenceType, list[str]]]:
    matches: list[tuple[EvidenceType, list[str]]] = []

    dated_terms = [term for term in ACTION_TERMS if term in lowered]
    if DATE_FRAGMENT_RE.search(raw_text) and dated_terms:
        matches.append((EvidenceType.DATED_ACTION, sorted(dated_terms)))

    money_terms = MONEY_RE.findall(raw_text)
    if money_terms:
        normalized_terms = sorted({term.strip() for term in money_terms})
        matches.append((EvidenceType.FINANCIAL_TERM, normalized_terms))

    actor_terms = [term for term in ACTOR_TERMS if term in lowered]
    if actor_terms or _extract_actor_hint(raw_text):
        matches.append((EvidenceType.ACTOR_IDENTIFICATION, sorted(set(actor_terms))))

    process_terms = [term for term in PROCESS_TERMS if term in lowered]
    if process_terms:
        matches.append((EvidenceType.PROCESS_SIGNAL, sorted(set(process_terms))))

    outcome_terms = [term for term in OUTCOME_TERMS if term in lowered]
    if outcome_terms:
        matches.append((EvidenceType.OUTCOME_FACT, sorted(set(outcome_terms))))

    return matches


def _score_confidence(
    evidence_type: EvidenceType,
    matched_terms: list[str],
    raw_text: str,
) -> str:
    score = len(matched_terms)
    if evidence_type == EvidenceType.DATED_ACTION and DATE_FRAGMENT_RE.search(raw_text):
        score += 2
    if evidence_type == EvidenceType.FINANCIAL_TERM and "per share" in raw_text.lower():
        score += 2
    if evidence_type == EvidenceType.OUTCOME_FACT and any(term in raw_text.lower() for term in {"closing", "executed", "termination fee"}):
        score += 2
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _first_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(0) if match else None


def _extract_actor_hint(text: str) -> str | None:
    patterns = [
        re.compile(r"\b(?:Party|Bidder)\s+[A-Z]\b"),
        re.compile(r"\b(?:Board|Special Committee|Transaction Committee)\b"),
        re.compile(r"\b[A-Z][A-Za-z&'.,-]+\s+(?:Partners|Sachs|Lynch|Morgan|Cooley|Gabelli|JANA|GAMCO|BMO)\b"),
    ]
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def _build_note(evidence_type: EvidenceType, matched_terms: list[str]) -> str | None:
    if not matched_terms:
        return None
    label = evidence_type.value.replace("_", " ")
    return f"detected {label}: {', '.join(matched_terms[:5])}"
```

---

## pipeline/source/fetch.py
```python
from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable
from urllib.request import urlopen

from pipeline.models.source import FilingCandidate, FrozenDocument

try:  # pragma: no cover - optional dependency in tests.
    from edgar import get_by_accession_number as _edgar_get_by_accession_number
except ModuleNotFoundError:  # pragma: no cover
    _edgar_get_by_accession_number = None


def _default_get_filing(accession_number: str) -> Any:
    if _edgar_get_by_accession_number is None:
        raise ModuleNotFoundError(
            "edgar is required for live SEC fetches; pass get_filing_fn in tests or install edgartools."
        )
    return _edgar_get_by_accession_number(accession_number)


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, default=str))


def text_sha256(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def fetch_filing_contents(
    accession_number: str,
    *,
    sec_url: str | None = None,
    get_filing_fn: Callable[[str], Any] | None = None,
    http_get_fn: Callable[[str], str] | None = None,
) -> tuple[str | None, str]:
    filing = (get_filing_fn or _default_get_filing)(accession_number)
    html_text = None
    txt_text = None
    if filing is not None:
        html_text = filing.html()
        txt_text = filing.text()

    if txt_text:
        return html_text, txt_text

    if sec_url is None:
        raise RuntimeError(f"Failed to fetch filing text for {accession_number}")

    http_get_fn = http_get_fn or _default_http_get
    html_text = http_get_fn(sec_url)
    return html_text, html_text


def freeze_filing(
    candidate: FilingCandidate,
    *,
    deal_dir: Path,
    html_text: str | None,
    txt_text: str,
    md_text: str | None = None,
) -> FrozenDocument:
    filings_dir = deal_dir / "source" / "filings"
    filings_dir.mkdir(parents=True, exist_ok=True)
    stem = candidate.document_id
    txt_path = filings_dir / f"{stem}.txt"
    atomic_write_text(txt_path, txt_text)

    html_path = None
    if html_text is not None:
        html_path = filings_dir / f"{stem}.html"
        atomic_write_text(html_path, html_text)

    md_path = None
    if md_text is not None:
        md_path = filings_dir / f"{stem}.md"
        atomic_write_text(md_path, md_text)

    return FrozenDocument(
        document_id=candidate.document_id,
        accession_number=candidate.accession_number,
        filing_type=candidate.filing_type,
        filing_date=candidate.filing_date,
        html_path=str(html_path.relative_to(deal_dir)) if html_path else None,
        txt_path=str(txt_path.relative_to(deal_dir)),
        md_path=str(md_path.relative_to(deal_dir)) if md_path else None,
        sha256_txt=text_sha256(txt_text),
        sha256_html=text_sha256(html_text) if html_text is not None else None,
        byte_count_txt=len(txt_text.encode("utf-8")),
        fetched_at=datetime.now(UTC),
    )


def _default_http_get(url: str) -> str:
    with urlopen(url) as response:  # noqa: S310 - SEC fetch path only.
        return response.read().decode("utf-8", errors="replace")
```

---

## pipeline/source/locate.py
```python
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pipeline.models.common import SCHEMA_VERSION
from pipeline.models.source import ChronologyCandidate, ChronologySelection


BACKGROUND_HEADING_RE = re.compile(
    r"^(?:background\s+of\s+(?:the\s+)?"
    r"(?:offer(?:\s+and\s+(?:the\s+)?)?merger|"
    r"merger(?:\s+and\s+(?:the\s+)?)?offer|"
    r"merger|offer|transaction|proposed\s+merger|"
    r"proposed\s+transaction|acquisition|tender\s+offer)"
    r"(?:\s*;\s*[^.]{1,120})?|"
    r"background\s+and\s+reasons\s+for\s+(?:the\s+)?merger)\.?\s*$",
    re.IGNORECASE,
)
STANDALONE_BACKGROUND_RE = re.compile(r"^background\.?\s*$", re.IGNORECASE)
DATE_RE = re.compile(
    r"(?i)\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\b|\b\d{4}\b"
)
PARTY_RE = re.compile(
    r"(?i)\b(?:party\s+[a-z]|\bboard\b|\bcompany\b|\bmerger\b|\boffer\b|"
    r"\bcommittee\b|\bcorp(?:oration)?\b|\binc\.?\b|llc|l\.p\.)"
)
END_HEADING_RE = re.compile(
    r"(?i)^(?:opinion\s+of|certain\s+(?:financial\s+)?projections|"
    r"reasons\s+for\s+the\s+(?:merger|offer)|recommendation\s+of|"
    r"interests\s+of|material\s+united\s+states\s+federal\s+income\s+tax|"
    r"regulatory\s+approvals|financing|the\s+(?:merger\s+agreement|offer)|"
    r"conditions\s+to)"
)
DOT_LEADER_RE = re.compile(r"\.{2,}\s*\d+\s*$")
CROSS_REFERENCE_RE = re.compile(
    r"(?i)\b(?:see|as\s+disclosed\s+under|as\s+described\s+in|incorporated\s+herein\s+by\s+reference)\b"
)
ROMAN_HEADING_PREFIX_RE = re.compile(r"^\(?[ivxlcdm]+\)?\s+", re.IGNORECASE)
HEADING_STYLE_RE = re.compile(r"^[A-Z0-9 ,.'()\-/&]+$")


@dataclass
class _ChronologyEvaluation:
    heading: str
    start_idx: int
    end_idx: int
    confidence: str
    selection_basis: str
    score: int
    is_standalone_background: bool


def locate_chronology(lines: list[str]) -> tuple[int, int, str] | None:
    selection = select_chronology(
        lines,
        document_id="document",
        accession_number=None,
        filing_type="UNKNOWN",
    )
    if selection.selected_candidate is None:
        return None
    candidate = selection.selected_candidate
    return candidate.start_line - 1, candidate.end_line - 1, candidate.heading_text


def select_chronology(
    lines: list[str],
    *,
    document_id: str,
    accession_number: str | None,
    filing_type: str,
    run_id: str = "local",
    deal_slug: str | None = None,
    markdown_lines: list[str] | None = None,
    section_headings: list[dict[str, Any]] | None = None,
) -> ChronologySelection:
    candidates = collect_chronology_candidates(
        lines,
        document_id=document_id,
        markdown_lines=markdown_lines,
        section_headings=section_headings,
    )
    if not candidates:
        return ChronologySelection(
            schema_version=SCHEMA_VERSION,
            artifact_type="chronology_selection",
            run_id=run_id,
            deal_slug=deal_slug,
            document_id=document_id,
            accession_number=accession_number,
            filing_type=filing_type,
            selected_candidate=None,
            confidence="none",
            adjudication_basis="No acceptable background-style chronology candidates were found.",
            alternative_candidates=[],
            review_required=True,
        )

    ordered = sorted(
        candidates,
        key=lambda candidate: (
            -candidate.score,
            1 if candidate.is_standalone_background else 0,
            -(candidate.end_line - candidate.start_line),
            candidate.start_line,
        ),
    )
    winner = ordered[0]
    runner_up = ordered[1] if len(ordered) > 1 else None
    confidence, confidence_factors = classify_chronology_confidence(winner, runner_up)
    basis = (
        f"Selected heading on line {winner.start_line} using normalized heading matching "
        f"and narrative scoring; considered {len(ordered)} viable background-like candidate(s)."
    )
    review_required = confidence in {"low", "none"} or confidence_factors["ambiguity_risk"] in {"medium", "high"}
    return ChronologySelection(
        schema_version=SCHEMA_VERSION,
        artifact_type="chronology_selection",
        run_id=run_id,
        deal_slug=deal_slug,
        document_id=document_id,
        accession_number=accession_number,
        filing_type=filing_type,
        selected_candidate=winner,
        confidence=confidence,
        adjudication_basis=basis,
        alternative_candidates=ordered[1:],
        review_required=review_required,
        confidence_factors=confidence_factors,
    )


def collect_chronology_candidates(
    lines: list[str],
    *,
    document_id: str,
    markdown_lines: list[str] | None = None,
    section_headings: list[dict[str, Any]] | None = None,
) -> list[ChronologyCandidate]:
    candidates = _collect_text_candidates(lines, document_id=document_id)

    for idx, line in enumerate(markdown_lines or [], start=1):
        stripped = line.strip().lstrip("#").strip()
        normalized = normalize_heading_candidate(stripped)
        if BACKGROUND_HEADING_RE.match(normalized):
            candidates.append(
                ChronologyCandidate(
                    document_id=document_id,
                    heading_text=stripped,
                    heading_normalized=normalized,
                    start_line=idx,
                    end_line=min(len(lines), idx + 50),
                    score=200,
                    source_methods=["markdown_heading"],
                    is_standalone_background=bool(STANDALONE_BACKGROUND_RE.match(normalized)),
                    diagnostics={"representation": "markdown"},
                )
            )

    for section in section_headings or []:
        title = str(section.get("title", "")).strip()
        normalized = normalize_heading_candidate(title)
        if not BACKGROUND_HEADING_RE.match(normalized):
            continue
        start_line = int(section.get("start_line", 1))
        end_line = int(section.get("end_line", start_line))
        candidates.append(
            ChronologyCandidate(
                document_id=document_id,
                heading_text=title,
                heading_normalized=normalized,
                start_line=start_line,
                end_line=end_line,
                score=250,
                source_methods=["sections_api"],
                is_standalone_background=bool(STANDALONE_BACKGROUND_RE.match(normalized)),
                diagnostics={"representation": "sections_api"},
            )
        )

    return _dedupe_candidates(candidates)


def classify_chronology_confidence(
    winner: ChronologyCandidate,
    runner_up: ChronologyCandidate | None,
) -> tuple[str, dict[str, Any]]:
    section_length = winner.end_line - winner.start_line + 1
    score_gap = winner.score - runner_up.score if runner_up is not None else winner.score
    ambiguity_risk = _ambiguity_risk(winner, runner_up, score_gap)
    coverage_assessment = _coverage_assessment(section_length, winner.score, score_gap)

    if ambiguity_risk == "high":
        confidence = "low"
    elif winner.score >= 700 and score_gap >= 100 and coverage_assessment in {"full", "adequate"}:
        confidence = "high"
    elif winner.score >= 450 and score_gap >= 80:
        confidence = "medium"
    else:
        confidence = "low"

    return confidence, {
        "section_length": section_length,
        "score_gap": score_gap,
        "ambiguity_risk": ambiguity_risk,
        "coverage_assessment": coverage_assessment,
    }




def _ambiguity_risk(
    winner: ChronologyCandidate,
    runner_up: ChronologyCandidate | None,
    score_gap: int,
) -> str:
    if runner_up is None:
        return "low"
    same_neighborhood = abs(winner.start_line - runner_up.start_line) <= 8
    if runner_up.score >= winner.score - 40 or (same_neighborhood and runner_up.score >= winner.score - 75):
        return "high"
    if runner_up.score >= winner.score - 120:
        return "medium"
    return "low"


def _coverage_assessment(section_length: int, winner_score: int, score_gap: int) -> str:
    if section_length >= 180:
        return "full"
    if section_length >= 100:
        return "adequate"
    if winner_score >= 600 and score_gap >= 150:
        return "short_but_probably_complete"
    return "short_uncertain"

def normalize_heading_candidate(line: str) -> str:
    stripped = line.strip().strip('"“”').strip()
    stripped = ROMAN_HEADING_PREFIX_RE.sub("", stripped)
    stripped = stripped.rstrip(".")
    stripped = re.sub(r"\s+", " ", stripped)
    return stripped.strip()


def normalize_heading_candidates_batch(lines: list[str]) -> list[str]:
    return [normalize_heading_candidate(line) for line in lines]


def _collect_text_candidates(lines: list[str], *, document_id: str) -> list[ChronologyCandidate]:
    candidates: list[ChronologyCandidate] = []
    normalized_headings = normalize_heading_candidates_batch(lines)
    heading_indexes: list[int] = []
    heading_forms: list[str] = []
    standalone_flags: list[bool] = []
    for idx, line in enumerate(lines):
        heading = line.strip()
        normalized_heading = normalized_headings[idx]
        if not heading:
            continue
        is_background_heading = bool(BACKGROUND_HEADING_RE.match(normalized_heading))
        is_standalone_background = bool(STANDALONE_BACKGROUND_RE.match(normalized_heading))
        if not is_background_heading and not is_standalone_background:
            continue
        if not looks_like_heading(heading):
            continue
        heading_indexes.append(idx)
        heading_forms.append(normalized_heading)
        standalone_flags.append(is_standalone_background)

    base_scores = score_heading_context_batch(
        lines,
        heading_indexes,
        normalized_headings=heading_forms,
        standalone_flags=standalone_flags,
    )
    for idx, normalized_heading, is_standalone_background, score in zip(
        heading_indexes,
        heading_forms,
        standalone_flags,
        base_scores,
        strict=True,
    ):
        if score <= 0:
            continue
        end_idx = find_section_end(lines, idx + 1)
        score += score_chronology_candidate(lines, idx, end_idx)
        candidates.append(
            ChronologyCandidate(
                document_id=document_id,
                heading_text=lines[idx].strip(),
                heading_normalized=normalized_heading,
                start_line=idx + 1,
                end_line=end_idx + 1,
                score=score,
                source_methods=["txt_heading", "txt_search"],
                is_standalone_background=is_standalone_background,
                diagnostics={
                    "line_count": end_idx - idx + 1,
                    "raw_start_idx": idx,
                    "raw_end_idx": end_idx,
                },
            )
        )
    return candidates


def score_heading_context(
    lines: list[str],
    start_idx: int,
    *,
    normalized_heading: str,
    is_standalone_background: bool,
) -> int:
    heading = lines[start_idx].strip()
    if DOT_LEADER_RE.search(heading):
        return -1

    total_lines = len(lines)
    lookahead = lines[start_idx + 1 : start_idx + 121]
    non_blank = [line.strip() for line in lookahead if line.strip()]
    min_non_blank = min(10, max(4, total_lines // 20))
    if len(non_blank) < min_non_blank:
        return -1

    date_hits = sum(1 for line in lookahead if DATE_RE.search(line))
    party_hits = sum(1 for line in lookahead if PARTY_RE.search(line))
    paragraph_breaks = sum(1 for line in lookahead if not line.strip())
    toc_like_followers = sum(
        1 for line in lookahead[:12] if DOT_LEADER_RE.search(line.strip()) or looks_like_heading(line)
    )
    section_end_idx = find_section_end(lines, start_idx + 1)
    section_length = max(0, section_end_idx - start_idx)
    min_section_length = min(60, max(6, total_lines // 15))

    if section_length < min_section_length:
        return -1
    if is_standalone_background and (date_hits < 2 or party_hits < 2):
        return -1
    if not is_standalone_background and date_hits == 0 and party_hits < 2:
        return -1
    if start_idx <= int(total_lines * 0.05) and toc_like_followers >= 4 and date_hits == 0:
        return -1

    score = min(section_length, 1600)
    score += date_hits * 40
    score += party_hits * 20
    score += paragraph_breaks * 5
    if not is_standalone_background:
        score += 100
    if start_idx <= int(total_lines * 0.10):
        score -= 150
    if CROSS_REFERENCE_RE.search(heading):
        score -= 300
    previous_line = lines[start_idx - 1] if start_idx > 0 else ""
    if CROSS_REFERENCE_RE.search(previous_line):
        score -= 250
    if normalized_heading.endswith(";"):
        score -= 200
    return score


def score_heading_context_batch(
    lines: list[str],
    start_indexes: list[int],
    *,
    normalized_headings: list[str],
    standalone_flags: list[bool],
) -> list[int]:
    return [
        score_heading_context(
            lines,
            start_idx,
            normalized_heading=normalized_heading,
            is_standalone_background=is_standalone_background,
        )
        for start_idx, normalized_heading, is_standalone_background in zip(
            start_indexes,
            normalized_headings,
            standalone_flags,
            strict=True,
        )
    ]


def find_section_end(lines: list[str], start_idx: int) -> int:
    for idx in range(start_idx + 1, len(lines)):
        candidate = lines[idx].strip()
        if not candidate:
            continue
        if END_HEADING_RE.search(candidate) and looks_like_heading(candidate):
            return idx - 1
    return len(lines) - 1


def looks_like_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    normalized = normalize_heading_candidate(stripped)
    if len(normalized) > 140 or stripped.endswith((",", ";")):
        return False
    if DATE_RE.search(normalized):
        return False
    words = normalized.split()
    if len(words) > 16:
        return False
    if HEADING_STYLE_RE.match(normalized):
        return True

    alpha_words = [re.sub(r"[^A-Za-z]+", "", word) for word in words]
    alpha_words = [word for word in alpha_words if word]
    if not alpha_words:
        return False

    title_like = 0
    for word in alpha_words:
        if word.lower() in {"of", "the", "and", "or", "for", "to"}:
            title_like += 1
        elif word[0].isupper():
            title_like += 1
    return title_like / len(alpha_words) >= 0.75


def score_chronology_candidate(lines: list[str], start_idx: int, end_idx: int) -> int:
    section = lines[start_idx : end_idx + 1]
    non_blank = [line.strip() for line in section if line.strip()]
    date_hits = sum(1 for line in non_blank if DATE_RE.search(line))
    paragraph_breaks = sum(1 for line in section if not line.strip())
    return len(non_blank) + date_hits * 15 + paragraph_breaks * 5


def _dedupe_candidates(candidates: list[ChronologyCandidate]) -> list[ChronologyCandidate]:
    deduped: list[ChronologyCandidate] = []
    for candidate in candidates:
        merged = False
        for index, existing in enumerate(deduped):
            same_heading = candidate.heading_normalized == existing.heading_normalized
            same_section = candidate.end_line == existing.end_line and abs(
                candidate.start_line - existing.start_line
            ) <= 3
            if not (same_heading and same_section):
                continue

            merged_methods = sorted(set(existing.source_methods + candidate.source_methods))
            winner = candidate if candidate.score > existing.score else existing
            deduped[index] = winner.model_copy(
                update={
                    "start_line": min(existing.start_line, candidate.start_line),
                    "source_methods": merged_methods,
                    "diagnostics": {
                        **existing.diagnostics,
                        **candidate.diagnostics,
                        "merged_duplicate_heading": True,
                    },
                }
            )
            merged = True
            break

        if not merged:
            deduped.append(candidate)
    return deduped
```

---

## pipeline/source/ranking.py
```python
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from pipeline.config import PRIMARY_PREFERENCE
from pipeline.models.source import FilingCandidate, SeedDeal


FORM_SEARCH_ALIASES: dict[str, tuple[str, ...]] = {
    "SC 14D-9": ("SC 14D-9", "SC 14D9"),
    "SC 13E-3": ("SC 13E-3", "SC 13E3"),
}
FORM_CANONICAL_NAMES: dict[str, str] = {
    "SC 14D9": "SC 14D-9",
    "SC14D9": "SC 14D-9",
    "SC 13E3": "SC 13E-3",
    "SC13E3": "SC 13E-3",
}
SUPPLEMENTARY_PREFERENCE = {
    "DEFA14A": 0,
    "8-K": 1,
    "SC 13D": 2,
}


def search_terms_for_form(filing_type: str) -> tuple[str, ...]:
    return FORM_SEARCH_ALIASES.get(filing_type, (filing_type,))


def canonical_form_name(filing_type: str) -> str:
    normalized = re.sub(r"\s+", " ", filing_type.strip().upper())
    return FORM_CANONICAL_NAMES.get(normalized, normalized)


def extract_accession_from_url(url: str | None) -> str | None:
    if not url:
        return None
    dashed = re.search(r"(\d{10}-\d{2}-\d{6})", url)
    if dashed:
        return dashed.group(1)

    compact = re.search(r"(\d{18})", url)
    if compact:
        value = compact.group(1)
        return f"{value[:10]}-{value[10:12]}-{value[12:]}"
    return None


def extract_cik_from_url(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"/data/(\d+)/", url)
    return match.group(1) if match else None


def parse_filing_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def filing_window_days(filing_family: str) -> int:
    if filing_family == "primary":
        return 365
    if filing_family == "supplementary":
        return 180
    raise ValueError(f"Unknown filing family: {filing_family}")


def rank_filing_candidates(
    seed: SeedDeal,
    search_results: list[Any],
    *,
    filing_family: str,
    top_k: int,
) -> list[FilingCandidate]:
    announcement_date = seed.date_announced_seed
    window_days = filing_window_days(filing_family)
    seed_accession = extract_accession_from_url(seed.primary_url_seed)

    candidates: list[FilingCandidate] = []
    for index, result in enumerate(search_results, start=1):
        accession_number = _result_value(result, "accession_number")
        filing_type = canonical_form_name(
            _result_value(result, "filing_type")
            or _result_value(result, "form")
            or ""
        )
        filing_date = parse_filing_date(_result_value(result, "filing_date"))
        sec_url = _result_value(result, "url") or _result_value(result, "sec_url")
        source_origin = _result_value(result, "source_origin") or "edgartools_search"

        days_from_announcement = None
        in_window = True
        if announcement_date and filing_date:
            days_from_announcement = abs((filing_date - announcement_date).days)
            in_window = days_from_announcement <= window_days

        seed_accession_match = accession_number == seed_accession
        if not in_window and not seed_accession_match:
            continue

        document_id = accession_number or f"{filing_type.lower()}-{index:03d}"
        form_preference = _form_preference(filing_type, filing_family)
        candidates.append(
            FilingCandidate(
                document_id=document_id,
                accession_number=accession_number,
                filing_type=filing_type,
                filing_date=filing_date,
                sec_url=sec_url,
                source_origin=source_origin,
                ranking_features={
                    "seed_accession_match": seed_accession_match,
                    "days_from_announcement": days_from_announcement,
                    "within_window": in_window,
                    "form_preference": form_preference,
                    "filing_family": filing_family,
                },
            )
        )

    candidates.sort(
        key=lambda candidate: (
            0 if candidate.ranking_features["seed_accession_match"] else 1,
            candidate.ranking_features["form_preference"],
            candidate.ranking_features["days_from_announcement"]
            if candidate.ranking_features["days_from_announcement"] is not None
            else float("inf"),
            candidate.accession_number or candidate.document_id,
        )
    )
    return candidates[:top_k]


def _form_preference(filing_type: str, filing_family: str) -> int:
    if filing_family == "primary":
        return PRIMARY_PREFERENCE.get(filing_type, len(PRIMARY_PREFERENCE))
    return SUPPLEMENTARY_PREFERENCE.get(filing_type, len(SUPPLEMENTARY_PREFERENCE))


def _result_value(result: Any, field_name: str) -> Any:
    if isinstance(result, dict):
        return result.get(field_name)
    return getattr(result, field_name, None)
```

---

## pipeline/source/supplementary.py
```python
from __future__ import annotations

from pipeline.models.source import EvidenceItem, EvidenceType, SupplementarySnippet
from pipeline.source.evidence import scan_document_evidence


PRESS_TERMS = {"press release", "announced", "announcement"}
ACTIVIST_TERMS = {"activist", "shareholder", "stockholder", "jana", "gamco", "gabelli"}
SALE_TERMS = {"strategic alternatives", "sale process", "review of alternatives", "review of strategic alternatives"}


def index_supplementary_snippets(
    lines: list[str],
    *,
    document_id: str,
    filing_type: str,
    accession_number: str | None = None,
) -> list[SupplementarySnippet]:
    evidence_items = scan_document_evidence(
        lines,
        document_id=document_id,
        filing_type=filing_type,
        accession_number=accession_number,
    )
    snippets: list[SupplementarySnippet] = []
    ordinal = 1
    for item in evidence_items:
        event_hint = _hint_for_item(item)
        if event_hint is None:
            continue
        snippets.append(
            SupplementarySnippet(
                snippet_id=f"S{ordinal:03d}",
                document_id=item.document_id,
                filing_type=item.filing_type,
                event_hint=event_hint,
                start_line=item.start_line,
                end_line=item.end_line,
                raw_text=item.raw_text,
                keyword_hits=item.matched_terms,
                confidence=item.confidence,
                evidence_id=item.evidence_id,
            )
        )
        ordinal += 1
    return snippets


def evidence_items_to_snippets(items: list[EvidenceItem]) -> list[SupplementarySnippet]:
    snippets: list[SupplementarySnippet] = []
    ordinal = 1
    for item in items:
        event_hint = _hint_for_item(item)
        if event_hint is None:
            continue
        snippets.append(
            SupplementarySnippet(
                snippet_id=f"S{ordinal:03d}",
                document_id=item.document_id,
                filing_type=item.filing_type,
                event_hint=event_hint,
                start_line=item.start_line,
                end_line=item.end_line,
                raw_text=item.raw_text,
                keyword_hits=item.matched_terms,
                confidence=item.confidence,
                evidence_id=item.evidence_id,
            )
        )
        ordinal += 1
    return snippets


def _hint_for_item(item: EvidenceItem) -> str | None:
    lowered = item.raw_text.lower()
    if any(term in lowered for term in ACTIVIST_TERMS):
        return "activist_sale"
    if any(term in lowered for term in PRESS_TERMS) and any(term in lowered for term in SALE_TERMS):
        return "sale_press_release"
    if any(term in lowered for term in PRESS_TERMS) or (
        item.evidence_type == EvidenceType.OUTCOME_FACT and "merger agreement" in lowered
    ):
        return "bid_press_release"
    if item.evidence_type == EvidenceType.PROCESS_SIGNAL and any(term in lowered for term in SALE_TERMS):
        return "sale_press_release"
    if item.evidence_type in {EvidenceType.OUTCOME_FACT, EvidenceType.PROCESS_SIGNAL}:
        return "other"
    return None
```
