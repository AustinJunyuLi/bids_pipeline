from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable

from skill_pipeline.pipeline_models.source import FilingCandidate, FrozenDocument

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


def _normalize_text_content(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n")


def write_immutable_text(path: Path, content: str) -> None:
    normalized_content = _normalize_text_content(content)
    if path.exists():
        existing = _normalize_text_content(path.read_text(encoding="utf-8"))
        if existing != normalized_content:
            raise FileExistsError(f"Immutable raw file already exists with different content: {path}")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        delete=False,
    ) as handle:
        handle.write(normalized_content)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def atomic_write_text(path: Path, content: str) -> None:
    normalized_content = _normalize_text_content(content)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        delete=False,
    ) as handle:
        handle.write(normalized_content)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, default=str))


def text_sha256(content: str) -> str:
    normalized_content = _normalize_text_content(content)
    return sha256(normalized_content.encode("utf-8")).hexdigest()


def _bytes_sha256(content: bytes) -> str:
    return sha256(content).hexdigest()


def fetch_filing_contents(
    accession_number: str,
    *,
    sec_url: str | None = None,
    get_filing_fn: Callable[[str], Any] | None = None,
    http_get_fn: Callable[[str], str] | None = None,
) -> tuple[str | None, str]:
    del http_get_fn  # No HTML fallback; raw .txt must come from filing text.
    filing = (get_filing_fn or _default_get_filing)(accession_number)
    html_text = None
    txt_text = None
    if filing is not None:
        html_text = filing.html()
        txt_text = filing.text()

    if txt_text and txt_text.strip():
        return html_text, _normalize_text_content(txt_text)

    if sec_url is not None:
        raise RuntimeError(
            f"Failed to fetch filing text for {accession_number} from {sec_url}"
        )
    raise RuntimeError(f"Failed to fetch filing text for {accession_number}")


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
    normalized_txt_text = _normalize_text_content(txt_text)
    txt_path = filings_dir / f"{stem}.txt"
    write_immutable_text(txt_path, normalized_txt_text)
    txt_bytes = txt_path.read_bytes()

    html_path = None
    if html_text is not None:
        normalized_html_text = _normalize_text_content(html_text)
        html_path = filings_dir / f"{stem}.html"
        write_immutable_text(html_path, normalized_html_text)
        html_bytes = html_path.read_bytes()
    else:
        normalized_html_text = None
        html_bytes = None

    md_path = None
    if md_text is not None:
        normalized_md_text = _normalize_text_content(md_text)
        md_path = filings_dir / f"{stem}.md"
        write_immutable_text(md_path, normalized_md_text)
    else:
        normalized_md_text = None

    project_root = raw_dir.parent
    return FrozenDocument(
        document_id=candidate.document_id,
        accession_number=candidate.accession_number,
        filing_type=candidate.filing_type,
        filing_date=candidate.filing_date,
        html_path=str(html_path.relative_to(project_root)) if html_path else None,
        txt_path=str(txt_path.relative_to(project_root)),
        md_path=str(md_path.relative_to(project_root)) if md_path else None,
        sha256_txt=_bytes_sha256(txt_bytes),
        sha256_html=_bytes_sha256(html_bytes) if html_bytes is not None else None,
        byte_count_txt=len(txt_bytes),
        fetched_at=datetime.now(UTC),
    )
