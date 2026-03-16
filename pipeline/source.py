import json
import os
import re
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any

from edgar import Company, get_by_accession_number, search_filings as edgar_search_filings
from edgar import set_identity

from pipeline.config import PRIMARY_FILING_TYPES, PRIMARY_PREFERENCE, SUPPLEMENTARY_FILING_TYPES
from pipeline.schemas import ChronologyBookmark, FilingManifest, FilingRecord


CHRONOLOGY_HEADING_RE = re.compile(
    r"\bbackground\s+of\s+(?:the\s+)?"
    r"(?:merger|offer|transaction|proposed\s+merger|proposed\s+transaction|acquisition|tender\s+offer)\b"
    r"|\bbackground\s+and\s+reasons\s+for\s+(?:the\s+)?merger\b",
    re.IGNORECASE,
)
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
SEC_IDENTITY = os.environ.get(
    "EDGAR_IDENTITY", "austinli@research.edu deal-extraction-tool/1.0"
)


class SourceError(RuntimeError):
    """Raised when Stage 1 cannot locate a usable primary filing."""


def run(seed: dict, deal_dir: Path) -> ChronologyBookmark:
    """Stage 1 entry point. Returns chronology bookmark or raises SourceError."""

    set_identity(SEC_IDENTITY)
    _ensure_stage_dirs(deal_dir)

    cik = _resolve_cik(seed)
    primary_records = search_filings(
        target_name=seed["target_name"],
        cik=cik,
        date_announced=seed.get("date_announced"),
        filing_types=PRIMARY_FILING_TYPES,
    )
    supplementary_records = search_filings(
        target_name=seed["target_name"],
        cik=cik,
        date_announced=seed.get("date_announced"),
        filing_types=SUPPLEMENTARY_FILING_TYPES,
    )
    selected_record, selected_filing = select_primary(
        primary_records=primary_records,
        seed_primary_url=seed.get("primary_url", ""),
    )
    html_path, txt_path = download_and_freeze(selected_record, deal_dir)
    selected_record.disposition = "selected"
    selected_record.html_path = str(html_path.relative_to(deal_dir))
    selected_record.txt_path = str(txt_path.relative_to(deal_dir))

    lines = txt_path.read_text(encoding="utf-8").splitlines()
    chronology = locate_chronology(lines)
    if chronology is None:
        raise SourceError("no chronology section found in primary filing")

    start_idx, end_idx, heading = chronology
    bookmark = ChronologyBookmark(
        accession_number=selected_filing.accession_number,
        heading=heading,
        start_line=start_idx + 1,
        end_line=end_idx + 1,
    )
    write_manifest(
        deal_dir,
        FilingManifest(
            deal_slug=seed["deal_slug"],
            cik=str(cik) if cik is not None else None,
            target_name=seed["target_name"],
            filings=primary_records + supplementary_records,
        ),
    )
    write_chronology_bookmark(deal_dir, bookmark)
    return bookmark


def search_filings(
    target_name: str,
    cik: str | int | None = None,
    date_announced: str | None = None,
    filing_types: tuple[str, ...] = PRIMARY_FILING_TYPES,
) -> list[FilingRecord]:
    """Search for the closest filing per requested type."""

    records: list[FilingRecord] = []
    for filing_type in filing_types:
        filings = _lookup_filings(
            target_name=target_name,
            filing_type=filing_type,
            cik=cik,
        )
        filing = _choose_best_filing(filings, date_announced=date_announced)
        if filing is None:
            records.append(FilingRecord(filing_type=filing_type, disposition="not_found"))
            continue
        records.append(
            FilingRecord(
                filing_type=filing.form,
                accession_number=filing.accession_number,
                filing_date=filing.filing_date.isoformat() if filing.filing_date else None,
                url=_primary_document_url(filing),
                disposition="searched_not_used",
            )
        )
    return records


def select_primary(
    primary_records: list[FilingRecord], seed_primary_url: str = ""
) -> tuple[FilingRecord, Any]:
    """Pick the best filing based on type preference and chronology presence."""

    seed_accession = _extract_accession_from_url(seed_primary_url)
    candidates: list[tuple[tuple[int, int, int], FilingRecord, Any]] = []
    for record in primary_records:
        if not record.accession_number:
            continue
        filing = get_by_accession_number(record.accession_number)
        lines = filing.text().splitlines()
        chronology = locate_chronology(lines)
        if chronology is None:
            continue
        start_idx, end_idx, _heading = chronology
        score = _score_chronology_candidate(lines, start_idx, end_idx)
        seed_bonus = 1 if record.accession_number == seed_accession else 0
        preference_bonus = -PRIMARY_PREFERENCE.get(record.filing_type, len(PRIMARY_PREFERENCE))
        candidates.append(((score, seed_bonus, preference_bonus), record, filing))

    if not candidates:
        raise SourceError("no usable filing found across primary filing types")

    _score, record, filing = max(candidates, key=lambda item: item[0])
    return record, filing


def download_and_freeze(filing_record: FilingRecord, deal_dir: Path) -> tuple[Path, Path]:
    """Download filing HTML, convert to text, save both. Return (html_path, txt_path)."""

    if not filing_record.accession_number:
        raise SourceError("selected filing is missing an accession number")

    filing = get_by_accession_number(filing_record.accession_number)
    html_text = filing.html()
    txt_text = filing.text()
    if not html_text or not txt_text:
        raise SourceError(f"failed to fetch filing text for {filing_record.accession_number}")

    filings_dir = deal_dir / "source" / "filings"
    html_path = filings_dir / f"{filing_record.accession_number}.html"
    txt_path = filings_dir / f"{filing_record.accession_number}.txt"
    html_path.write_text(html_text, encoding="utf-8")
    txt_path.write_text(txt_text, encoding="utf-8")
    return html_path, txt_path


def locate_chronology(lines: list[str]) -> tuple[int, int, str] | None:
    """Find Background of the Merger section. Returns (start_line, end_line, heading)."""

    candidates: list[tuple[int, int, int, str]] = []
    for idx, line in enumerate(lines):
        heading = line.strip()
        if not heading or not CHRONOLOGY_HEADING_RE.search(heading):
            continue
        score = _score_heading_context(lines, idx)
        if score <= 0:
            continue
        end_idx = _find_section_end(lines, idx + 1)
        score += _score_chronology_candidate(lines, idx, end_idx)
        candidates.append((score, idx, end_idx, heading))

    if not candidates:
        return None

    _score, start_idx, end_idx, heading = max(candidates, key=lambda item: (item[0], -item[1]))
    return start_idx, end_idx, heading


def write_manifest(deal_dir: Path, manifest: FilingManifest) -> None:
    """Write filing_manifest.json."""

    path = deal_dir / "source" / "filing_manifest.json"
    path.write_text(json.dumps(manifest.model_dump(), indent=2), encoding="utf-8")


def write_chronology_bookmark(deal_dir: Path, bookmark: ChronologyBookmark) -> None:
    """Write chronology.json."""

    path = deal_dir / "source" / "chronology.json"
    path.write_text(json.dumps(bookmark.model_dump(), indent=2), encoding="utf-8")


def _ensure_stage_dirs(deal_dir: Path) -> None:
    (deal_dir / "source" / "filings").mkdir(parents=True, exist_ok=True)
    (deal_dir / "extraction").mkdir(parents=True, exist_ok=True)
    (deal_dir / "enrichment").mkdir(parents=True, exist_ok=True)


def _resolve_cik(seed: dict) -> str | None:
    primary_url = seed.get("primary_url", "")
    cik = _extract_cik_from_url(primary_url)
    if cik:
        return cik

    results = edgar_search_filings(query=seed["target_name"], limit=5)
    if len(results):
        return str(results[0].cik)
    return None


def _lookup_filings(target_name: str, filing_type: str, cik: str | int | None) -> list[Any]:
    if cik is not None:
        company = Company(int(cik))
        entity_filings = company.get_filings(form=filing_type, amendments=False)
        return [entity_filings[i] for i in range(len(entity_filings))]

    results = edgar_search_filings(query=target_name, forms=[filing_type], limit=20)
    return [get_by_accession_number(results[i].accession_number) for i in range(len(results))]


def _choose_best_filing(filings: Iterable[Any], date_announced: str | None) -> Any | None:
    filings = list(filings)
    if not filings:
        return None

    announced = _parse_iso_date(date_announced)
    if announced is None:
        return filings[0]

    return min(
        filings,
        key=lambda filing: (
            abs((filing.filing_date - announced).days)
            if getattr(filing, "filing_date", None)
            else float("inf"),
            filing.filing_date if getattr(filing, "filing_date", None) else date.max,
        ),
    )


def _primary_document_url(filing: Any) -> str | None:
    primary_documents = getattr(filing, "primary_documents", [])
    if primary_documents:
        return getattr(primary_documents[0], "url", None)
    homepage = getattr(filing, "homepage", None)
    return getattr(homepage, "url", None)


def _extract_cik_from_url(url: str) -> str | None:
    match = re.search(r"/data/(\d+)/", url)
    return match.group(1) if match else None


def _extract_accession_from_url(url: str) -> str | None:
    match = re.search(r"(\d{10}-\d{2}-\d{6})", url)
    return match.group(1) if match else None


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _score_heading_context(lines: list[str], start_idx: int) -> int:
    heading = lines[start_idx].strip()
    if DOT_LEADER_RE.search(heading):
        return -1

    lookahead = lines[start_idx + 1 : start_idx + 41]
    non_blank = [line.strip() for line in lookahead if line.strip()]
    if len(non_blank) < 4:
        return -1

    date_hits = sum(1 for line in non_blank[:20] if DATE_RE.search(line))
    party_hits = sum(1 for line in non_blank[:20] if PARTY_RE.search(line))
    paragraph_breaks = sum(1 for line in lookahead[:20] if not line.strip())

    if date_hits == 0 or party_hits == 0:
        return -1
    if paragraph_breaks == 0 and len(non_blank) < 8:
        return -1

    return date_hits * 20 + party_hits * 10 + len(non_blank)


def _find_section_end(lines: list[str], start_idx: int) -> int:
    for idx in range(start_idx + 1, len(lines)):
        candidate = lines[idx].strip()
        if not candidate:
            continue
        if END_HEADING_RE.search(candidate) and _looks_like_heading(candidate):
            return idx - 1
    return len(lines) - 1


def _looks_like_heading(line: str) -> bool:
    if len(line) > 120 or line.endswith("."):
        return False
    alpha_only = re.sub(r"[^A-Za-z]+", "", line)
    return bool(alpha_only) and (line == line.upper() or line.istitle())


def _score_chronology_candidate(lines: list[str], start_idx: int, end_idx: int) -> int:
    section = lines[start_idx : end_idx + 1]
    non_blank = [line.strip() for line in section if line.strip()]
    date_hits = sum(1 for line in non_blank if DATE_RE.search(line))
    paragraph_breaks = sum(1 for line in section if not line.strip())
    return len(non_blank) + date_hits * 15 + paragraph_breaks * 5
