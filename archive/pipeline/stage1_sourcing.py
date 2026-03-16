from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import time
from dataclasses import dataclass
from datetime import date
from html import unescape
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Comment

from pipeline.schemas import (
    ChronologyBookmark,
    CorpusManifestEntry,
    Decision,
    DocumentListEntry,
    DocumentSelection,
    FilingSearchRecord,
    SourceSelection,
    Stage1Result,
)


logger = logging.getLogger(__name__)


USER_AGENT = "austinli@research.edu deal-extraction-tool/1.0"
REQUEST_TIMEOUT_SECONDS = 60
SEC_RATE_LIMIT_SECONDS = 0.15

PRIMARY_FILING_SEARCHES: tuple[tuple[str, str], ...] = (
    ("DEFM14A", "DEFM14A"),
    ("PREM14A", "PREM14A"),
    ("SC 14D-9", "SC+14D-9"),
    ("SC 13E-3", "SC+13E-3"),
    ("S-4", "S-4"),
    ("SC TO-T", "SC+TO-T"),
)

SUPPLEMENTARY_FILING_SEARCHES: tuple[tuple[str, str], ...] = (
    ("SC 13D", "SC+13D"),
    ("DEFA14A", "DEFA14A"),
    ("8-K", "8-K"),
)

PRIMARY_PREFERENCE_RANK: dict[str, int] = {
    "DEFM14A": 0,
    "PREM14A": 1,
    "SC 14D-9": 2,
    "SC 13E-3": 3,
    "SC TO-T": 4,
    "S-4": 5,
}

BACKGROUND_HEADING_RE = re.compile(
    r"(?i)^(?:background\s+of\s+(?:the\s+)?(?:offer(?:\s+and\s+(?:the\s+)?)?merger|merger(?:\s+and\s+(?:the\s+)?)?offer|merger|offer|transaction|proposed\s+merger|proposed\s+transaction|acquisition|tender\s+offer)|background\s+and\s+reasons\s+for\s+the\s+merger)\s*$"
)

STANDALONE_BACKGROUND_RE = re.compile(r"(?i)^background\s*$")

END_HEADING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)^opinion\s+of\b"),
    re.compile(r"(?i)^certain\s+(?:financial\s+)?projections\b"),
    re.compile(r"(?i)^reasons\s+for\s+the\s+(?:merger|offer)\b"),
    re.compile(r"(?i)^recommendation\s+of\b"),
    re.compile(r"(?i)^interests\s+of\b"),
    re.compile(r"(?i)^material\s+united\s+states\s+federal\s+income\s+tax\b"),
    re.compile(r"(?i)^regulatory\s+approvals\b"),
    re.compile(r"(?i)^financing\b"),
    re.compile(r"(?i)^the\s+(?:merger\s+agreement|offer)\b"),
    re.compile(r"(?i)^conditions\s+to\b"),
)

DATE_RE = re.compile(
    r"(?i)\b(?:on\s+)?(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},\s+\d{4}\b"
)

PARTY_RE = re.compile(
    r"(?i)\b(?:party\s+[a-z]|bidder\s+[a-z]|the\s+company|company|board\s+of\s+directors|merger\s+sub|parent|purchaser|bidder|target|financial\s+sponsor)\b"
)

TOC_PAGE_RE = re.compile(r"(?:\.{2,}|\s)\d{1,4}\s*$")

HEADING_STYLE_RE = re.compile(r"^[A-Z0-9 ,.'()\-/&]+$")

BLOCK_TAGS: set[str] = {
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "dd",
    "div",
    "dl",
    "dt",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}


@dataclass(slots=True, frozen=True)
class _FilingCandidate:
    """Internal candidate filing inspected during anchor selection."""

    accession_number: str
    cik: str
    filing_type: str
    filing_date: str
    index_url: str
    document_url: str
    document_selection: DocumentSelection
    chronology_bookmark: ChronologyBookmark
    chronology_score: int
    seed_url_match: bool
    is_primary: bool


@dataclass(slots=True, frozen=True)
class _ChronologyEvaluation:
    """Internal chronology span evaluation result used during selection and localization."""

    heading_text: str
    start_line: int
    end_line: int
    confidence: str
    selection_basis: str
    score: int


def _ensure_session_headers(session: requests.Session) -> None:
    """Ensure the SEC-required headers are configured on the session."""

    session.headers["User-Agent"] = USER_AGENT
    session.headers["Accept-Encoding"] = "gzip, deflate"
    session.headers["Accept"] = "text/html,application/json;q=0.9,*/*;q=0.8"


def _sec_get(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, str] | None = None,
    allow_redirects: bool = True,
) -> requests.Response:
    """Send a rate-limited request to an SEC host and raise on HTTP failure."""

    _ensure_session_headers(session)
    parsed = urlparse(url)
    if parsed.netloc.endswith("sec.gov") or parsed.netloc.endswith("data.sec.gov"):
        time.sleep(SEC_RATE_LIMIT_SECONDS)
    response: requests.Response = session.get(
        url,
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
        allow_redirects=allow_redirects,
    )
    response.raise_for_status()
    return response


def _normalize_cik(value: str | int | None) -> str | None:
    """Normalize a CIK-like value to an unpadded digit string."""

    if value is None:
        return None
    digits: str = re.sub(r"\D", "", str(value))
    if not digits:
        return None
    return digits.lstrip("0") or "0"


def _normalize_form(value: str) -> str:
    """Normalize a filing form label for comparisons across SEC variants."""

    return re.sub(r"[^A-Z0-9]", "", value.upper())


def _parse_cik_from_url(url: str) -> str | None:
    """Parse a CIK value from a SEC archive URL when possible."""

    match = re.search(r"/data/(\d+)/", url)
    if match:
        return _normalize_cik(match.group(1))
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    cik_values: list[str] = query.get("CIK", [])
    if cik_values:
        return _normalize_cik(cik_values[0])
    return None


def _parse_accession_from_text(text: str) -> str | None:
    """Extract a dashed accession number from arbitrary SEC text."""

    match = re.search(r"(\d{10}-\d{2}-\d{6})", text)
    if match:
        return match.group(1)
    return None


def _parse_accession_from_url(url: str) -> str | None:
    """Extract a dashed accession number from a SEC URL when present."""

    parsed = urlparse(url)
    path: str = parsed.path
    accession_match = re.search(r"/(\d{10}-\d{2}-\d{6})-index\.htm(?:l)?$", path, flags=re.IGNORECASE)
    if accession_match:
        return accession_match.group(1)
    return _parse_accession_from_text(path)


def _candidate_index_urls(cik: str, accession_number: str) -> list[str]:
    """Return SEC filing index URL candidates for an accession number."""

    cik_int: int = int(cik)
    accession_no_dashes: str = accession_number.replace("-", "")
    base: str = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_no_dashes}/{accession_number}-index"
    return [f"{base}.html", f"{base}.htm"]


def _resolve_document_url(index_url: str, href: str) -> str:
    """Resolve a filing document href against an SEC index page URL."""

    base_url: str = index_url if index_url.endswith("/") else index_url.rsplit("/", 1)[0] + "/"
    accession_number: str | None = _parse_accession_from_url(index_url)
    if accession_number is not None and "-index." in index_url.lower():
        base_url = f"{base_url}{accession_number.replace('-', '')}/"
    return urljoin(base_url, href)


def _token_similarity(target_name: str, candidate_name: str) -> float:
    """Compute a simple token-overlap similarity score between two names."""

    target_tokens: set[str] = set(re.findall(r"[A-Za-z0-9]+", target_name.lower()))
    candidate_tokens: set[str] = set(re.findall(r"[A-Za-z0-9]+", candidate_name.lower()))
    if not target_tokens or not candidate_tokens:
        return 0.0
    intersection: int = len(target_tokens.intersection(candidate_tokens))
    union: int = len(target_tokens.union(candidate_tokens))
    return intersection / union if union else 0.0


def _collect_cik_name_pairs(payload: Any) -> list[tuple[str, str]]:
    """Recursively collect possible CIK and company-name pairs from a JSON payload."""

    pairs: list[tuple[str, str]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            possible_cik: str | None = None
            possible_name: str = ""
            for key, value in node.items():
                lower_key: str = key.lower()
                if "cik" in lower_key:
                    normalized = _normalize_cik(value)
                    if normalized is not None:
                        possible_cik = normalized
                if lower_key in {"entityname", "companyname", "displayname", "title", "name"} and isinstance(value, str):
                    if value.strip():
                        possible_name = value.strip()
            if possible_cik is not None:
                pairs.append((possible_cik, possible_name))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return pairs


def resolve_cik(target_name: str, session: requests.Session) -> str | None:
    """Resolve the SEC CIK for a target company.

    The function first tries the SEC full-text search endpoint and falls back to a company
    search page parse when JSON search results are unavailable or ambiguous.
    """

    logger.info("resolve_cik target_name=%s", target_name)
    today: str = date.today().isoformat()
    full_text_url: str = "https://efts.sec.gov/LATEST/search-index"
    params: dict[str, str] = {
        "q": f'"{target_name}"',
        "dateRange": "custom",
        "startdt": "1990-01-01",
        "enddt": today,
    }
    try:
        response: requests.Response = _sec_get(session, full_text_url, params=params)
        payload: Any = response.json()
        pairs: list[tuple[str, str]] = _collect_cik_name_pairs(payload)
        if pairs:
            ranked_pairs: list[tuple[float, str, str]] = sorted(
                [(_token_similarity(target_name, name), cik, name) for cik, name in pairs],
                key=lambda item: (item[0], len(item[2])),
                reverse=True,
            )
            best_similarity, best_cik, _best_name = ranked_pairs[0]
            if best_similarity > 0.0 or len({cik for _, cik, _ in ranked_pairs}) == 1:
                logger.info("resolve_cik full_text_success target_name=%s cik=%s similarity=%s", target_name, best_cik, best_similarity)
                return best_cik
    except Exception as exc:
        logger.warning("resolve_cik full_text_failed target_name=%s error=%s", target_name, exc)

    fallback_url: str = "https://www.sec.gov/cgi-bin/browse-edgar"
    fallback_params: dict[str, str] = {
        "company": target_name,
        "CIK": "",
        "type": "",
        "dateb": "",
        "owner": "include",
        "count": "40",
        "search_text": "",
        "action": "getcompany",
    }
    try:
        response = _sec_get(session, fallback_url, params=fallback_params)
        redirected_cik: str | None = _parse_cik_from_url(response.url)
        if redirected_cik is not None:
            logger.info("resolve_cik company_search_redirect target_name=%s cik=%s", target_name, redirected_cik)
            return redirected_cik
        html_text: str = response.text
        soup = BeautifulSoup(html_text, "html.parser")
        candidate_pairs: list[tuple[str, str]] = []
        for anchor in soup.find_all("a", href=True):
            href: str = anchor.get("href", "")
            if "CIK=" not in href:
                continue
            cik_value: str | None = _parse_cik_from_url(urljoin(response.url, href))
            if cik_value is None:
                continue
            candidate_pairs.append((cik_value, anchor.get_text(" ", strip=True)))
        if not candidate_pairs:
            for match in re.finditer(r"CIK\s*[:#]?\s*(\d{1,10})", html_text, flags=re.IGNORECASE):
                candidate_pairs.append((_normalize_cik(match.group(1)) or "", ""))
        candidate_pairs = [(cik_value, name) for cik_value, name in candidate_pairs if cik_value]
        if candidate_pairs:
            ranked_pairs = sorted(
                [(_token_similarity(target_name, name), cik_value, name) for cik_value, name in candidate_pairs],
                key=lambda item: (item[0], len(item[2])),
                reverse=True,
            )
            return ranked_pairs[0][1]
    except Exception as exc:
        logger.warning("resolve_cik company_search_failed target_name=%s error=%s", target_name, exc)
    return None


def _iter_submission_payloads(cik: str, session: requests.Session) -> Iterable[dict[str, Any]]:
    """Yield the SEC submissions JSON payload and any historical continuation files."""

    cik_padded: str = cik.zfill(10)
    main_url: str = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
    response: requests.Response = _sec_get(session, main_url)
    payload: dict[str, Any] = response.json()
    yield payload

    filing_files: list[dict[str, Any]] = payload.get("filings", {}).get("files", []) if isinstance(payload, dict) else []
    for file_entry in filing_files:
        if not isinstance(file_entry, dict):
            continue
        name: str = str(file_entry.get("name", "")).strip()
        if not name:
            continue
        url: str = f"https://data.sec.gov/submissions/{name}"
        continuation_response = _sec_get(session, url)
        continuation_payload: Any = continuation_response.json()
        if isinstance(continuation_payload, dict):
            yield continuation_payload


def _submission_rows_from_payload(payload: dict[str, Any], cik: str) -> list[dict[str, str]]:
    """Convert a submissions JSON payload into filing rows."""

    filing_rows: list[dict[str, str]] = []
    filings_section: Any = payload.get("filings", {}).get("recent") if isinstance(payload.get("filings"), dict) else payload
    if not isinstance(filings_section, dict):
        return filing_rows
    forms: list[str] = list(filings_section.get("form", []))
    accession_numbers: list[str] = list(filings_section.get("accessionNumber", []))
    filing_dates: list[str] = list(filings_section.get("filingDate", []))
    primary_documents: list[str] = list(filings_section.get("primaryDocument", []))
    count: int = min(len(forms), len(accession_numbers), len(filing_dates), len(primary_documents))
    for index in range(count):
        accession_number: str = accession_numbers[index]
        primary_document: str = primary_documents[index]
        accession_no_dashes: str = accession_number.replace("-", "")
        filing_rows.append(
            {
                "accession_number": accession_number,
                "filing_date": filing_dates[index],
                "filing_type": forms[index],
                "index_url": _candidate_index_urls(cik, accession_number)[0],
                "filing_url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_no_dashes}/{primary_document}",
                "primary_document": primary_document,
            }
        )
    return filing_rows


def _fallback_search_filings_by_type_html(cik: str, filing_type: str, session: requests.Session) -> list[dict[str, str]]:
    """Fallback HTML-based filing search when submissions JSON is unavailable."""

    browse_url: str = "https://www.sec.gov/cgi-bin/browse-edgar"
    params: dict[str, str] = {
        "action": "getcompany",
        "CIK": cik,
        "type": filing_type,
        "dateb": "",
        "owner": "include",
        "count": "10",
        "search_text": "",
    }
    response: requests.Response = _sec_get(session, browse_url, params=params)
    soup = BeautifulSoup(response.text, "html.parser")
    results: list[dict[str, str]] = []
    seen_accessions: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href: str = anchor.get("href", "")
        if "-index" not in href:
            continue
        absolute_url: str = urljoin(response.url, href)
        accession_number: str | None = _parse_accession_from_url(absolute_url)
        if accession_number is None or accession_number in seen_accessions:
            continue
        row_text: str = anchor.parent.get_text(" ", strip=True) if anchor.parent is not None else anchor.get_text(" ", strip=True)
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", row_text)
        filing_date: str = date_match.group(1) if date_match else "1900-01-01"
        results.append(
            {
                "accession_number": accession_number,
                "filing_date": filing_date,
                "filing_type": filing_type.replace("+", " "),
                "index_url": absolute_url,
                "filing_url": absolute_url,
                "primary_document": "",
            }
        )
        seen_accessions.add(accession_number)
    results.sort(key=lambda item: item["filing_date"], reverse=True)
    return results


def search_filings_by_type(cik: str, filing_type: str, session: requests.Session) -> list[dict]:
    """Search EDGAR for filings of a specific type for a given CIK.

    The implementation prefers the SEC submissions JSON feed and falls back to the HTML
    company-filings browse page when the JSON feed is unavailable.
    """

    normalized_target_form: str = _normalize_form(filing_type)
    deduped_results: dict[str, dict[str, str]] = {}
    try:
        for payload in _iter_submission_payloads(cik, session):
            for row in _submission_rows_from_payload(payload, cik):
                if _normalize_form(row["filing_type"]) != normalized_target_form:
                    continue
                deduped_results.setdefault(row["accession_number"], row)
        results: list[dict[str, str]] = sorted(
            deduped_results.values(),
            key=lambda item: item["filing_date"],
            reverse=True,
        )
        if results:
            return results
    except Exception as exc:
        logger.warning("search_filings_by_type submissions_failed cik=%s filing_type=%s error=%s", cik, filing_type, exc)
    return _fallback_search_filings_by_type_html(cik, filing_type, session)


def fetch_filing_html(url: str, session: requests.Session) -> bytes:
    """Fetch filing HTML bytes from SEC EDGAR with required rate limiting and headers."""

    response: requests.Response = _sec_get(session, url)
    return response.content


def _parse_size_text(size_text: str) -> int:
    """Parse a SEC size string into approximate bytes for ranking."""

    normalized: str = size_text.strip().upper().replace(",", "")
    if not normalized:
        return 0
    match = re.match(r"([0-9]+(?:\.[0-9]+)?)\s*(B|KB|MB|GB)?", normalized)
    if not match:
        return 0
    value: float = float(match.group(1))
    unit: str = match.group(2) or "B"
    multiplier: dict[str, int] = {"B": 1, "KB": 1024, "MB": 1024 * 1024, "GB": 1024 * 1024 * 1024}
    return int(value * multiplier.get(unit, 1))


def _choose_document_from_index(index_url: str, html_bytes: bytes, filing_type_hint: str | None) -> tuple[DocumentSelection, str]:
    """Choose the main HTML document from a filing index page and return its URL."""

    soup = BeautifulSoup(html_bytes, "html.parser")
    document_rows: list[tuple[str, str, str, str, str]] = []
    target_form: str = _normalize_form(filing_type_hint or "")
    for table in soup.find_all("table"):
        header_cells: list[str] = [cell.get_text(" ", strip=True).lower() for cell in table.find_all("th")]
        if "document" not in header_cells:
            continue
        document_index: int = header_cells.index("document")
        description_index: int | None = header_cells.index("description") if "description" in header_cells else None
        type_index: int | None = header_cells.index("type") if "type" in header_cells else None
        size_index: int | None = header_cells.index("size") if "size" in header_cells else None
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            if document_index >= len(cells):
                continue
            document_cell = cells[document_index]
            anchor = document_cell.find("a", href=True)
            if anchor is None:
                continue
            filename: str = anchor.get_text(" ", strip=True) or Path(anchor.get("href", "")).name
            href: str = _resolve_document_url(index_url, anchor.get("href", ""))
            description: str = cells[description_index].get_text(" ", strip=True) if description_index is not None and description_index < len(cells) else ""
            type_text: str = cells[type_index].get_text(" ", strip=True) if type_index is not None and type_index < len(cells) else ""
            size_text: str = cells[size_index].get_text(" ", strip=True) if size_index is not None and size_index < len(cells) else ""
            document_rows.append((filename, description, type_text, size_text, href))
        if document_rows:
            break

    if not document_rows:
        parsed = urlparse(index_url)
        filename = Path(parsed.path).name
        selection = DocumentSelection(
            index_url=index_url,
            documents_listed=[DocumentListEntry(filename=filename, description="Index page document", size="")],
            selected_document=filename,
            selection_rationale="No document table was found on the filing index page; falling back to the referenced URL itself.",
        )
        return selection, index_url

    def row_score(row: tuple[str, str, str, str, str]) -> tuple[int, int, str]:
        filename, description, type_text, size_text, _href = row
        score: int = 0
        normalized_filename: str = filename.lower()
        normalized_description: str = _normalize_form(description)
        normalized_type_text: str = _normalize_form(type_text)
        if normalized_filename.endswith(".htm") or normalized_filename.endswith(".html"):
            score += 1000
        if target_form and normalized_type_text == target_form:
            score += 800
        elif target_form and normalized_description == target_form:
            score += 750
        elif target_form and target_form in normalized_type_text:
            score += 700
        elif target_form and target_form in normalized_description:
            score += 650
        score += min(_parse_size_text(size_text) // 1024, 500)
        return score, _parse_size_text(size_text), filename

    selected_row: tuple[str, str, str, str, str] = max(document_rows, key=row_score)
    documents_listed: list[DocumentListEntry] = [
        DocumentListEntry(filename=filename, description=description, size=size_text)
        for filename, description, _type_text, size_text, _href in document_rows
    ]
    selected_filename, selected_description, selected_type_text, selected_size_text, selected_href = selected_row
    selected_file_ext: str = selected_filename.lower()
    if (selected_file_ext.endswith(".htm") or selected_file_ext.endswith(".html")) and (
        target_form and (_normalize_form(selected_type_text) == target_form or target_form in _normalize_form(selected_description))
    ):
        rationale = "Selected the largest .htm document whose type or description best matches the filing type."
    elif selected_file_ext.endswith(".htm") or selected_file_ext.endswith(".html"):
        rationale = "Selected the largest HTML document on the filing index page after no stronger filing-type match was available."
    else:
        rationale = "Selected the best-scoring document available on the filing index page because no HTML document met the filing-type criteria."
    selection = DocumentSelection(
        index_url=index_url,
        documents_listed=documents_listed,
        selected_document=selected_filename,
        selection_rationale=rationale,
    )
    return selection, selected_href


def html_to_text(html_bytes: bytes) -> str:
    """Convert filing HTML bytes into a normalized plain-text snapshot."""

    soup = BeautifulSoup(html_bytes, "html.parser")
    for removable in soup.find_all(["script", "style", "head", "noscript"]):
        removable.decompose()
    for comment in soup.find_all(string=lambda item: isinstance(item, Comment)):
        comment.extract()
    for element in soup.find_all(True):
        if element.name == "br":
            element.replace_with("\n")
            continue
        if element.name in {"td", "th"}:
            element.insert_after("\t")
            continue
        if element.name in BLOCK_TAGS:
            element.insert_after("\n")
    raw_text: str = soup.get_text()
    raw_text = unescape(raw_text)
    normalized_lines: list[str] = []
    previous_blank: bool = False
    for raw_line in raw_text.splitlines():
        line: str = raw_line.replace("\xa0", " ").replace("\u200b", "")
        line = re.sub(r"[ \t\f\v]+", " ", line).strip()
        if not line:
            if not previous_blank:
                normalized_lines.append("")
            previous_blank = True
            continue
        normalized_lines.append(line)
        previous_blank = False
    return "\n".join(normalized_lines).strip() + "\n"


def _looks_like_heading(line: str) -> bool:
    """Return whether a line resembles a section heading rather than body prose."""

    stripped: str = line.strip()
    if not stripped or len(stripped) > 140:
        return False
    if stripped.endswith((".", ",", ";")):
        return False
    if DATE_RE.search(stripped):
        return False
    words: list[str] = stripped.split()
    if len(words) > 14:
        return False
    if HEADING_STYLE_RE.match(stripped):
        return True
    title_ratio: float = sum(1 for word in words if word[:1].isupper()) / len(words)
    return title_ratio >= 0.75


def _find_section_end(lines: list[str], start_index: int) -> int:
    """Find the line index at which the chronology section ends."""

    for index in range(start_index + 1, len(lines)):
        stripped: str = lines[index].strip()
        if not stripped:
            continue
        if not _looks_like_heading(stripped):
            continue
        for pattern in END_HEADING_PATTERNS:
            if pattern.search(stripped):
                return index - 1 if index > start_index else start_index
    return len(lines) - 1


def _score_candidate(lines: list[str], heading_index: int, heading_text: str) -> tuple[bool, int, int, str]:
    """Score a chronology heading candidate and return acceptance metadata."""

    total_lines: int = len(lines)
    after_lines: list[str] = lines[heading_index + 1 : min(len(lines), heading_index + 121)]
    nonempty_after: list[str] = [line for line in after_lines if line.strip()]
    date_hits: int = sum(1 for line in after_lines if DATE_RE.search(line))
    party_hits: int = sum(1 for line in after_lines if PARTY_RE.search(line))
    blank_count: int = sum(1 for line in after_lines if not line.strip())
    toc_like_followers: int = sum(1 for line in after_lines[:12] if TOC_PAGE_RE.search(line) or _looks_like_heading(line))
    section_end_index: int = _find_section_end(lines, heading_index)
    section_length: int = max(0, section_end_index - heading_index)
    is_standalone_background: bool = bool(STANDALONE_BACKGROUND_RE.match(heading_text.strip()))

    score: int = 0
    score += min(section_length, 1600)
    score += date_hits * 40
    score += party_hits * 20
    score += blank_count * 5
    if not is_standalone_background:
        score += 200
    if heading_index <= int(total_lines * 0.10):
        score -= 150
    if TOC_PAGE_RE.search(heading_text):
        score -= 500
    if toc_like_followers >= 4 and date_hits == 0:
        score -= 400

    accept: bool = True
    reasons: list[str] = []
    if len(nonempty_after) < 10:
        accept = False
        reasons.append("fewer than 10 non-empty lines after heading")
    if section_length < 60:
        accept = False
        reasons.append("section span shorter than 60 lines")
    if is_standalone_background and (date_hits < 2 or party_hits < 2):
        accept = False
        reasons.append("standalone Background heading lacks enough narrative date and party signals")
    elif not is_standalone_background and (date_hits < 1 and party_hits < 2):
        accept = False
        reasons.append("insufficient date or party narrative signals after heading")
    if heading_index <= int(total_lines * 0.05) and toc_like_followers >= 4 and date_hits == 0:
        accept = False
        reasons.append("heading appears in the first five percent of the document with TOC-like followers")
    if re.search(r"(?i)\bsee\b|\bas described in\b", lines[heading_index - 1] if heading_index > 0 else ""):
        score -= 250
        reasons.append("preceded by a cross-reference line")
    reason_text: str = "; ".join(reasons) if reasons else "candidate has narrative structure"
    return accept, section_end_index, score, reason_text


def _evaluate_chronology_lines(lines: list[str], accession_number: str) -> _ChronologyEvaluation:
    """Evaluate and locate the chronology span inside normalized text lines."""

    candidates: list[tuple[int, str, bool, int, int, str]] = []
    for index, raw_line in enumerate(lines):
        line: str = raw_line.strip()
        if not line:
            continue
        canonical_match: bool = bool(BACKGROUND_HEADING_RE.match(line))
        standalone_match: bool = bool(STANDALONE_BACKGROUND_RE.match(line))
        if not canonical_match and not standalone_match:
            continue
        accept, end_index, score, reason = _score_candidate(lines, index, line)
        candidates.append((index, line, accept, end_index, score, reason))

    if not candidates:
        raise ValueError(f"No chronology heading candidate found in accession {accession_number}")

    accepted_candidates: list[tuple[int, str, bool, int, int, str]] = [candidate for candidate in candidates if candidate[2]]
    if accepted_candidates:
        best_candidate = max(
            accepted_candidates,
            key=lambda item: (
                item[4],
                1 if not STANDALONE_BACKGROUND_RE.match(item[1]) else 0,
                item[3] - item[0],
            ),
        )
        rejected_count: int = len(candidates) - len(accepted_candidates)
        confidence: str
        section_length: int = best_candidate[3] - best_candidate[0]
        if not STANDALONE_BACKGROUND_RE.match(best_candidate[1]) and section_length >= 200 and best_candidate[4] >= 450:
            confidence = "high"
        elif section_length >= 120 and best_candidate[4] >= 250:
            confidence = "medium"
        else:
            confidence = "low"
        selection_basis: str = (
            f"Selected heading on line {best_candidate[0] + 1} because it is followed by date-rich narrative prose; "
            f"rejected {rejected_count} other background-like candidate(s) as TOC or cross-reference hits."
        )
        return _ChronologyEvaluation(
            heading_text=best_candidate[1],
            start_line=best_candidate[0] + 1,
            end_line=best_candidate[3] + 1,
            confidence=confidence,
            selection_basis=selection_basis,
            score=best_candidate[4],
        )

    fallback_candidate = max(candidates, key=lambda item: (item[4], item[3] - item[0]))
    selection_basis = (
        f"No background candidate satisfied the full narrative acceptance rules; falling back to the strongest available candidate on line {fallback_candidate[0] + 1}."
    )
    return _ChronologyEvaluation(
        heading_text=fallback_candidate[1],
        start_line=fallback_candidate[0] + 1,
        end_line=fallback_candidate[3] + 1,
        confidence="low",
        selection_basis=selection_basis,
        score=fallback_candidate[4],
    )


def freeze_filing_text(accession_number: str, html_bytes: bytes, deal_dir: Path) -> tuple[Path, Path]:
    """Write the selected filing HTML and frozen text snapshot atomically to disk."""

    filings_dir: Path = deal_dir / "source" / "filings"
    filings_dir.mkdir(parents=True, exist_ok=True)
    html_path: Path = filings_dir / f"{accession_number}.html"
    txt_path: Path = filings_dir / f"{accession_number}.txt"
    txt_text: str = html_to_text(html_bytes)

    def atomic_write_bytes(path: Path, payload: bytes) -> None:
        file_descriptor: int
        tmp_path_str: str
        file_descriptor, tmp_path_str = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
        tmp_path = Path(tmp_path_str)
        try:
            with os.fdopen(file_descriptor, "wb") as handle:
                handle.write(payload)
            os.replace(tmp_path, path)
            path.chmod(0o444)
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def atomic_write_text(path: Path, payload: str) -> None:
        file_descriptor: int
        tmp_path_str: str
        file_descriptor, tmp_path_str = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
        tmp_path = Path(tmp_path_str)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as handle:
                handle.write(payload)
            os.replace(tmp_path, path)
            path.chmod(0o444)
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    atomic_write_bytes(html_path, html_bytes)
    atomic_write_text(txt_path, txt_text)
    return html_path, txt_path


def locate_chronology(txt_path: Path) -> ChronologyBookmark:
    """Locate the Background of the Merger/Offer/Transaction section in frozen text."""

    lines: list[str] = txt_path.read_text(encoding="utf-8").splitlines()
    accession_number: str = txt_path.stem
    evaluation: _ChronologyEvaluation = _evaluate_chronology_lines(lines, accession_number)
    return ChronologyBookmark(
        accession_number=accession_number,
        section_heading=evaluation.heading_text,
        start_line=evaluation.start_line,
        end_line=evaluation.end_line,
        confidence=evaluation.confidence,
        selection_basis=evaluation.selection_basis,
    )


def _write_json(path: Path, payload: object) -> None:
    """Write JSON atomically with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor: int
    tmp_path_str: str
    file_descriptor, tmp_path_str = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp_path: Path = Path(tmp_path_str)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _write_jsonl(path: Path, rows: Iterable[Decision]) -> None:
    """Write decision JSONL atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    serialized_lines: list[str] = [json.dumps(row.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) for row in rows]
    file_descriptor: int
    tmp_path_str: str
    file_descriptor, tmp_path_str = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp_path: Path = Path(tmp_path_str)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as handle:
            if serialized_lines:
                handle.write("\n".join(serialized_lines) + "\n")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _canonical_filing_label(value: str) -> str:
    """Return a display-friendly filing type label."""

    normalized: str = _normalize_form(value)
    for label, token in (*PRIMARY_FILING_SEARCHES, *SUPPLEMENTARY_FILING_SEARCHES):
        if _normalize_form(label) == normalized or _normalize_form(token) == normalized:
            return label
    return value.replace("+", " ")


def _fetch_index_and_choose_document(
    session: requests.Session,
    cik: str,
    accession_number: str,
    candidate_url: str,
    filing_type_hint: str | None,
) -> tuple[str, DocumentSelection, str]:
    """Fetch a filing index page and choose the best document from its table."""

    candidate_index_urls: list[str] = []
    if "-index." in candidate_url.lower():
        candidate_index_urls.append(candidate_url)
    elif accession_number:
        candidate_index_urls.extend(_candidate_index_urls(cik, accession_number))
    candidate_index_urls.append(candidate_url)

    seen_urls: set[str] = set()
    last_error: Exception | None = None
    for index_url in candidate_index_urls:
        if index_url in seen_urls:
            continue
        seen_urls.add(index_url)
        try:
            index_html_bytes: bytes = fetch_filing_html(index_url, session)
            selection, selected_document_url = _choose_document_from_index(index_url, index_html_bytes, filing_type_hint)
            return index_url, selection, selected_document_url
        except Exception as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    raise RuntimeError("Unable to fetch or parse filing index page")


def _inspect_filing_candidate(
    session: requests.Session,
    cik: str,
    accession_number: str,
    filing_type: str,
    filing_date: str,
    candidate_url: str,
    *,
    seed_url_match: bool,
) -> _FilingCandidate:
    """Inspect a candidate filing and score its chronology section."""

    index_url, document_selection, document_url = _fetch_index_and_choose_document(
        session,
        cik,
        accession_number,
        candidate_url,
        filing_type,
    )
    document_html: bytes = fetch_filing_html(document_url, session)
    text_snapshot: str = html_to_text(document_html)
    evaluation: _ChronologyEvaluation = _evaluate_chronology_lines(text_snapshot.splitlines(), accession_number)
    return _FilingCandidate(
        accession_number=accession_number,
        cik=cik,
        filing_type=_canonical_filing_label(filing_type),
        filing_date=filing_date,
        index_url=index_url,
        document_url=document_url,
        document_selection=document_selection,
        chronology_bookmark=ChronologyBookmark(
            accession_number=accession_number,
            section_heading=evaluation.heading_text,
            start_line=evaluation.start_line,
            end_line=evaluation.end_line,
            confidence=evaluation.confidence,
            selection_basis=evaluation.selection_basis,
        ),
        chronology_score=evaluation.score + (50 if seed_url_match else 0),
        seed_url_match=seed_url_match,
        is_primary=_canonical_filing_label(filing_type) in {label for label, _ in PRIMARY_FILING_SEARCHES},
    )


def select_anchor_filing(
    deal_slug: str,
    target_name: str,
    cik: str,
    filing_url: str | None,
    session: requests.Session,
) -> SourceSelection:
    """Search candidate filing types and select the anchor filing with the best chronology."""

    logger.info("select_anchor_filing deal_slug=%s cik=%s", deal_slug, cik)
    search_summaries: dict[str, list[dict[str, str]]] = {}
    search_errors: dict[str, str] = {}
    for label, token in (*PRIMARY_FILING_SEARCHES, *SUPPLEMENTARY_FILING_SEARCHES):
        try:
            results: list[dict[str, str]] = search_filings_by_type(cik, token, session)
            search_summaries[label] = results
        except Exception as exc:
            search_errors[label] = str(exc)
            search_summaries[label] = []

    candidates: list[_FilingCandidate] = []
    inspected_accessions: set[str] = set()

    if filing_url:
        parsed_cik: str | None = _parse_cik_from_url(filing_url) or cik
        accession_number: str | None = _parse_accession_from_url(filing_url)
        filing_type_hint: str | None = None
        filing_date_hint: str = "1900-01-01"
        if accession_number is not None:
            for label, rows in search_summaries.items():
                for row in rows:
                    if row.get("accession_number") == accession_number:
                        filing_type_hint = _canonical_filing_label(row.get("filing_type", label))
                        filing_date_hint = row.get("filing_date", filing_date_hint)
                        break
                if filing_type_hint is not None:
                    break
        if accession_number is not None:
            try:
                explicit_candidate = _inspect_filing_candidate(
                    session,
                    parsed_cik or cik,
                    accession_number,
                    filing_type_hint or "",
                    filing_date_hint,
                    filing_url,
                    seed_url_match=True,
                )
                candidates.append(explicit_candidate)
                inspected_accessions.add(explicit_candidate.accession_number)
            except Exception as exc:
                logger.warning("explicit filing_url inspection failed deal_slug=%s url=%s error=%s", deal_slug, filing_url, exc)

    for label, _token in (*PRIMARY_FILING_SEARCHES, *SUPPLEMENTARY_FILING_SEARCHES):
        rows = search_summaries.get(label, [])
        for row in rows[:3]:
            accession_number = row.get("accession_number", "")
            if not accession_number or accession_number in inspected_accessions:
                continue
            try:
                candidate = _inspect_filing_candidate(
                    session,
                    cik,
                    accession_number,
                    row.get("filing_type", label),
                    row.get("filing_date", "1900-01-01"),
                    row.get("index_url") or row.get("filing_url") or "",
                    seed_url_match=False,
                )
                candidates.append(candidate)
                inspected_accessions.add(accession_number)
            except Exception as exc:
                logger.warning(
                    "candidate inspection failed deal_slug=%s filing_type=%s accession=%s error=%s",
                    deal_slug,
                    label,
                    accession_number,
                    exc,
                )

    if not candidates:
        raise RuntimeError(f"No candidate filing could be inspected for deal {deal_slug}")

    def candidate_rank(candidate: _FilingCandidate) -> tuple[int, int, int, int, int]:
        preference_rank: int = PRIMARY_PREFERENCE_RANK.get(candidate.filing_type, 999)
        confidence_rank: int = {"high": 2, "medium": 1, "low": 0}.get(candidate.chronology_bookmark.confidence, 0)
        filing_date_rank: int = int(candidate.filing_date.replace("-", "")) if re.match(r"\d{4}-\d{2}-\d{2}", candidate.filing_date) else 0
        return (
            1 if candidate.is_primary else 0,
            candidate.chronology_score,
            confidence_rank,
            -preference_rank,
            filing_date_rank,
        )

    selected_candidate: _FilingCandidate = max(candidates, key=candidate_rank)
    logger.info(
        "select_anchor_filing selected deal_slug=%s accession=%s filing_type=%s score=%s",
        deal_slug,
        selected_candidate.accession_number,
        selected_candidate.filing_type,
        selected_candidate.chronology_score,
    )

    primary_searches: list[FilingSearchRecord] = []
    supplementary_searches: list[FilingSearchRecord] = []
    selected_label: str = selected_candidate.filing_type

    for label, _token in PRIMARY_FILING_SEARCHES:
        rows = search_summaries.get(label, [])
        if label == selected_label:
            disposition = "selected"
            selected_accession = selected_candidate.accession_number
            reason = None if rows else "Selected from the provided filing URL after search results were empty."
        elif label in search_errors:
            disposition = "uncertain"
            selected_accession = None
            reason = search_errors[label]
        elif rows:
            disposition = "searched_not_used"
            selected_accession = None
            reason = None
        else:
            disposition = "not_found"
            selected_accession = None
            reason = None
        primary_searches.append(
            FilingSearchRecord(
                filing_type=label,
                results_count=len(rows),
                disposition=disposition,
                selected_accession_number=selected_accession,
                reason=reason,
            )
        )

    for label, _token in SUPPLEMENTARY_FILING_SEARCHES:
        rows = search_summaries.get(label, [])
        if label == selected_label:
            disposition = "selected"
            selected_accession = selected_candidate.accession_number
            reason = None if rows else "Selected from the provided filing URL after search results were empty."
        elif label in search_errors:
            disposition = "uncertain"
            selected_accession = None
            reason = search_errors[label]
        elif rows:
            disposition = "searched_not_used"
            selected_accession = None
            reason = None
        else:
            disposition = "not_found"
            selected_accession = None
            reason = None
        supplementary_searches.append(
            FilingSearchRecord(
                filing_type=label,
                results_count=len(rows),
                disposition=disposition,
                selected_accession_number=selected_accession,
                reason=reason,
            )
        )

    return SourceSelection(
        deal_slug=deal_slug,
        cik=cik,
        target_name=target_name,
        primary_searches=primary_searches,
        supplementary_searches=supplementary_searches,
        document_selection=selected_candidate.document_selection,
    )


def _selected_accession_number(source_selection: SourceSelection) -> str:
    """Return the selected accession number from a source selection artifact."""

    for record in [*source_selection.primary_searches, *source_selection.supplementary_searches]:
        if record.disposition == "selected" and record.selected_accession_number:
            return record.selected_accession_number
    raise ValueError("Source selection does not contain a selected accession number")


def _selected_filing_type(source_selection: SourceSelection) -> str:
    """Return the selected filing type from a source selection artifact."""

    for record in [*source_selection.primary_searches, *source_selection.supplementary_searches]:
        if record.disposition == "selected":
            return record.filing_type
    raise ValueError("Source selection does not contain a selected filing type")


def _infer_selected_document_url(source_selection: SourceSelection) -> str:
    """Construct the selected filing document URL from source-selection metadata."""

    return _resolve_document_url(
        source_selection.document_selection.index_url,
        source_selection.document_selection.selected_document,
    )


def _find_filing_date_for_accession(source_selection: SourceSelection, search_results: dict[str, list[dict[str, str]]], accession_number: str) -> str:
    """Find the filing date for a selected accession from search results, if available."""

    for label, rows in search_results.items():
        del label
        for row in rows:
            if row.get("accession_number") == accession_number:
                return row.get("filing_date", "1900-01-01")
    return "1900-01-01"


def run_stage1(deal_slug: str, target_name: str, filing_url: str | None, deal_dir: Path) -> Stage1Result:
    """Run deterministic stage 1 sourcing, freezing, and chronology localization."""

    logger.info("run_stage1 starting deal_slug=%s target_name=%s", deal_slug, target_name)
    session = requests.Session()
    _ensure_session_headers(session)

    cik: str | None = resolve_cik(target_name, session)
    if cik is None and filing_url:
        cik = _parse_cik_from_url(filing_url)
    if cik is None:
        raise RuntimeError(f"Unable to resolve CIK for target {target_name}")

    search_results: dict[str, list[dict[str, str]]] = {}
    for label, token in (*PRIMARY_FILING_SEARCHES, *SUPPLEMENTARY_FILING_SEARCHES):
        try:
            search_results[label] = search_filings_by_type(cik, token, session)
        except Exception:
            search_results[label] = []

    source_selection: SourceSelection = select_anchor_filing(
        deal_slug=deal_slug,
        target_name=target_name,
        cik=cik,
        filing_url=filing_url,
        session=session,
    )
    accession_number: str = _selected_accession_number(source_selection)
    filing_type: str = _selected_filing_type(source_selection)
    document_url: str = _infer_selected_document_url(source_selection)
    html_bytes: bytes = fetch_filing_html(document_url, session)
    html_path, txt_path = freeze_filing_text(accession_number, html_bytes, deal_dir)
    chronology_bookmark: ChronologyBookmark = locate_chronology(txt_path)

    filing_date: str = _find_filing_date_for_accession(source_selection, search_results, accession_number)
    html_relative: str = str(html_path.relative_to(deal_dir))
    txt_relative: str = str(txt_path.relative_to(deal_dir))
    corpus_manifest: list[CorpusManifestEntry] = [
        CorpusManifestEntry(
            accession_number=accession_number,
            filing_type=filing_type,
            role="primary",
            url=document_url,
            html_filename=html_relative,
            txt_filename=txt_relative,
            filing_date=filing_date,
            fetch_status="success",
            fetch_error=None,
        )
    ]

    source_dir: Path = deal_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    _write_json(source_dir / "source_selection.json", source_selection.model_dump(mode="json"))
    _write_json(source_dir / "corpus_manifest.json", [entry.model_dump(mode="json") for entry in corpus_manifest])
    _write_json(source_dir / "chronology_bookmark.json", chronology_bookmark.model_dump(mode="json"))

    extraction_dir: Path = deal_dir / "extraction"
    extraction_dir.mkdir(parents=True, exist_ok=True)
    filing_selection_decision = Decision(
        skill="stage1_sourcing",
        decision_type="filing_selection",
        detail=(
            f"Selected accession {accession_number} ({filing_type}) as the anchor filing because it provided the strongest chronology section under deterministic scoring."
        ),
        artifact_affected="source/source_selection.json",
        target_id=accession_number,
        confidence="high" if chronology_bookmark.confidence == "high" else "medium",
    )
    _write_jsonl(extraction_dir / "decisions.jsonl", [filing_selection_decision])

    logger.info(
        "run_stage1 complete deal_slug=%s cik=%s accession=%s chronology_lines=%s-%s",
        deal_slug,
        cik,
        accession_number,
        chronology_bookmark.start_line,
        chronology_bookmark.end_line,
    )
    return Stage1Result(
        deal_slug=deal_slug,
        cik=cik,
        source_selection=source_selection,
        corpus_manifest=corpus_manifest,
        chronology_bookmark=chronology_bookmark,
        html_path=html_path,
        txt_path=txt_path,
        primary_accession_number=accession_number,
        filing_type=filing_type,
        filing_url=document_url,
    )
