"""Legacy compatibility models used by the pre-refactor source module."""

from pydantic import BaseModel


class ChronologyBookmark(BaseModel):
    accession_number: str
    heading: str
    start_line: int
    end_line: int
    confidence: str | None = None
    selection_basis: str | None = None


class FilingRecord(BaseModel):
    filing_type: str
    accession_number: str | None = None
    filing_date: str | None = None
    url: str | None = None
    disposition: str
    html_path: str | None = None
    txt_path: str | None = None


class FilingManifest(BaseModel):
    deal_slug: str
    cik: str | None = None
    target_name: str
    filings: list[FilingRecord]


class DealStatus(BaseModel):
    status: str
    last_stage: str | None = None
    cost_usd: float = 0.0
    events_extracted: int = 0
    actors_extracted: int = 0
    error: str | None = None
    timestamp: str | None = None
