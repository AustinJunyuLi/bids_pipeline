import json
import os
import re
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from edgar import Company, get_by_accession_number, search_filings as edgar_search_filings
from edgar import set_identity

from pipeline.config import PRIMARY_FILING_TYPES, PRIMARY_PREFERENCE, SUPPLEMENTARY_FILING_TYPES
from pipeline.schemas import ChronologyBookmark, FilingManifest, FilingRecord


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
SEC_IDENTITY = os.environ.get(
    "EDGAR_IDENTITY", "austinli@research.edu deal-extraction-tool/1.0"
)
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


class SourceError(RuntimeError):
    """Raised when Stage 1 cannot locate a usable primary filing."""


@dataclass
class _ChronologyEvaluation:
    heading: str
    start_idx: int
    end_idx: int
    confidence: str
    selection_basis: str
    score: int
    is_standalone_background: bool


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
    chronology = _evaluate_chronology_lines(lines)
    if chronology is None:
        raise SourceError("no chronology section found in primary filing")

    bookmark = ChronologyBookmark(
        accession_number=selected_filing.accession_number,
        heading=chronology.heading,
        start_line=chronology.start_idx + 1,
        end_line=chronology.end_idx + 1,
        confidence=chronology.confidence,
        selection_basis=chronology.selection_basis,
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
                filing_type=_canonical_form_name(str(filing.form)),
                accession_number=filing.accession_number,
                filing_date=filing.filing_date.isoformat() if filing.filing_date else None,
                url=_primary_document_url(filing),
                disposition="found",
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
    _atomic_write_text(html_path, html_text)
    _atomic_write_text(txt_path, txt_text)
    return html_path, txt_path


def locate_chronology(lines: list[str]) -> tuple[int, int, str] | None:
    """Find Background of the Merger section. Returns (start_line, end_line, heading)."""

    chronology = _evaluate_chronology_lines(lines)
    if chronology is None:
        return None
    return chronology.start_idx, chronology.end_idx, chronology.heading


def _evaluate_chronology_lines(lines: list[str]) -> _ChronologyEvaluation | None:
    candidates: list[tuple[int, int, int, str, bool]] = []
    for idx, line in enumerate(lines):
        heading = line.strip()
        normalized_heading = _normalize_heading_candidate(heading)
        if not heading:
            continue
        is_background_heading = bool(BACKGROUND_HEADING_RE.match(normalized_heading))
        is_standalone_background = bool(STANDALONE_BACKGROUND_RE.match(normalized_heading))
        if not is_background_heading and not is_standalone_background:
            continue
        if not _looks_like_heading(heading):
            continue
        score = _score_heading_context(
            lines,
            idx,
            normalized_heading=normalized_heading,
            is_standalone_background=is_standalone_background,
        )
        if score <= 0:
            continue
        end_idx = _find_section_end(lines, idx + 1)
        score += _score_chronology_candidate(lines, idx, end_idx)
        candidates.append((score, idx, end_idx, heading, is_standalone_background))

    if not candidates:
        return None

    score, start_idx, end_idx, heading, is_standalone_background = max(
        candidates,
        key=lambda item: (
            item[0],
            1 if not item[4] else 0,
            item[2] - item[1],
            -item[1],
        ),
    )
    confidence = _classify_chronology_confidence(
        score=score,
        start_idx=start_idx,
        end_idx=end_idx,
        is_standalone_background=is_standalone_background,
    )
    selection_basis = (
        f"Selected heading on line {start_idx + 1} using normalized standalone heading matching "
        f"and narrative scoring; considered {len(candidates)} viable background-like candidate(s)."
    )
    return _ChronologyEvaluation(
        heading=heading,
        start_idx=start_idx,
        end_idx=end_idx,
        confidence=confidence,
        selection_basis=selection_basis,
        score=score,
        is_standalone_background=is_standalone_background,
    )


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

    # Older/delisted issuers do not consistently resolve by name in edgartools,
    # so try the Company path first and then fall back to filing search.
    try:
        return str(Company(seed["target_name"]).cik)
    except Exception:
        pass

    results = edgar_search_filings(query=seed["target_name"], limit=5)
    if len(results):
        return str(results[0].cik)
    return None


def _lookup_filings(target_name: str, filing_type: str, cik: str | int | None) -> list[Any]:
    filings_by_accession: dict[str, Any] = {}
    for search_term in _search_terms_for_form(filing_type):
        if cik is not None:
            company = Company(int(cik))
            entity_filings = company.get_filings(form=search_term, amendments=False)
            filings = [entity_filings[i] for i in range(len(entity_filings))]
        else:
            results = edgar_search_filings(query=target_name, forms=[search_term], limit=20)
            filings = [get_by_accession_number(results[i].accession_number) for i in range(len(results))]
        for filing in filings:
            accession_number = getattr(filing, "accession_number", None)
            if accession_number and accession_number not in filings_by_accession:
                filings_by_accession[accession_number] = filing
    return list(filings_by_accession.values())


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


def _atomic_write_text(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def _search_terms_for_form(filing_type: str) -> tuple[str, ...]:
    return FORM_SEARCH_ALIASES.get(filing_type, (filing_type,))


def _canonical_form_name(filing_type: str) -> str:
    normalized = re.sub(r"\s+", " ", filing_type.strip().upper())
    return FORM_CANONICAL_NAMES.get(normalized, normalized)


def _classify_chronology_confidence(
    score: int,
    start_idx: int,
    end_idx: int,
    is_standalone_background: bool,
) -> str:
    section_length = end_idx - start_idx
    if not is_standalone_background and section_length >= 200 and score >= 700:
        return "high"
    if section_length >= 120 and score >= 250:
        return "medium"
    return "low"


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _normalize_heading_candidate(line: str) -> str:
    stripped = line.strip().strip('"“”').strip()
    stripped = ROMAN_HEADING_PREFIX_RE.sub("", stripped)
    stripped = re.sub(r"\s+", " ", stripped)
    return stripped.strip()


def _score_heading_context(
    lines: list[str],
    start_idx: int,
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
        1 for line in lookahead[:12] if DOT_LEADER_RE.search(line.strip()) or _looks_like_heading(line)
    )
    section_end_idx = _find_section_end(lines, start_idx + 1)
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


def _find_section_end(lines: list[str], start_idx: int) -> int:
    for idx in range(start_idx + 1, len(lines)):
        candidate = lines[idx].strip()
        if not candidate:
            continue
        if END_HEADING_RE.search(candidate) and _looks_like_heading(candidate):
            return idx - 1
    return len(lines) - 1


def _looks_like_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    normalized = _normalize_heading_candidate(stripped)
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


def _score_chronology_candidate(lines: list[str], start_idx: int, end_idx: int) -> int:
    section = lines[start_idx : end_idx + 1]
    non_blank = [line.strip() for line in section if line.strip()]
    date_hits = sum(1 for line in non_blank if DATE_RE.search(line))
    paragraph_breaks = sum(1 for line in section if not line.strip())
    return len(non_blank) + date_hits * 15 + paragraph_breaks * 5
