from __future__ import annotations

import json
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable
from urllib.request import urlopen

from edgar import get_by_accession_number

from pipeline.models.source import FilingCandidate, FrozenDocument


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as handle:
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
    get_filing_fn: Callable[[str], Any] = get_by_accession_number,
    http_get_fn: Callable[[str], str] | None = None,
) -> tuple[str | None, str]:
    filing = get_filing_fn(accession_number)
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
    txt_text = html_text
    return html_text, txt_text


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
        fetched_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )


def _default_http_get(url: str) -> str:
    with urlopen(url) as response:  # noqa: S310 - SEC fetch path only.
        return response.read().decode("utf-8", errors="replace")
