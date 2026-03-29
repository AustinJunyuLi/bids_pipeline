from __future__ import annotations

from pathlib import Path
import time

import duckdb


DEFAULT_DB_NAME = "pipeline.duckdb"
LOCK_RETRY_ATTEMPTS = 3
LOCK_RETRY_BACKOFF_SECONDS = (0.25, 0.5, 1.0)

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS actors (
    deal_slug TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    aliases TEXT[],
    role TEXT NOT NULL,
    advisor_kind TEXT,
    advised_actor_id TEXT,
    bidder_kind TEXT,
    listing_status TEXT,
    geography TEXT,
    is_grouped BOOLEAN NOT NULL,
    group_size INTEGER,
    group_label TEXT,
    evidence_span_ids TEXT[],
    PRIMARY KEY (deal_slug, actor_id)
);

CREATE TABLE IF NOT EXISTS events (
    deal_slug TEXT NOT NULL,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    date_raw_text TEXT,
    date_sort DATE,
    date_precision TEXT,
    actor_ids TEXT[],
    summary TEXT NOT NULL,
    evidence_span_ids TEXT[],
    terms_per_share DOUBLE,
    terms_range_low DOUBLE,
    terms_range_high DOUBLE,
    terms_consideration_type TEXT,
    whole_company_scope BOOLEAN,
    drop_reason_text TEXT,
    round_scope TEXT,
    invited_actor_ids TEXT[],
    executed_with_actor_id TEXT,
    nda_signed BOOLEAN,
    PRIMARY KEY (deal_slug, event_id)
);

CREATE TABLE IF NOT EXISTS spans (
    deal_slug TEXT NOT NULL,
    span_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    filing_type TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    block_ids TEXT[],
    quote_text TEXT NOT NULL,
    match_type TEXT NOT NULL,
    PRIMARY KEY (deal_slug, span_id)
);

CREATE TABLE IF NOT EXISTS enrichment (
    deal_slug TEXT NOT NULL,
    event_id TEXT NOT NULL,
    dropout_label TEXT,
    dropout_basis TEXT,
    bid_label TEXT,
    bid_rule_applied DOUBLE,
    bid_basis TEXT,
    PRIMARY KEY (deal_slug, event_id)
);

CREATE TABLE IF NOT EXISTS cycles (
    deal_slug TEXT NOT NULL,
    cycle_id TEXT NOT NULL,
    start_event_id TEXT NOT NULL,
    end_event_id TEXT NOT NULL,
    boundary_basis TEXT NOT NULL,
    PRIMARY KEY (deal_slug, cycle_id)
);

CREATE TABLE IF NOT EXISTS rounds (
    deal_slug TEXT NOT NULL,
    announcement_event_id TEXT NOT NULL,
    deadline_event_id TEXT,
    round_scope TEXT NOT NULL,
    invited_actor_ids TEXT[],
    active_bidders_at_time INTEGER NOT NULL,
    is_selective BOOLEAN NOT NULL,
    PRIMARY KEY (deal_slug, announcement_event_id)
);
"""


def open_pipeline_db(
    db_path: Path,
    *,
    read_only: bool = False,
) -> duckdb.DuckDBPyConnection:
    if not read_only:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    con: duckdb.DuckDBPyConnection | None = None
    for attempt_index in range(LOCK_RETRY_ATTEMPTS):
        try:
            con = duckdb.connect(str(db_path), read_only=read_only)
            break
        except Exception as exc:
            if not _is_lock_contention_error(exc):
                raise
            if attempt_index == LOCK_RETRY_ATTEMPTS - 1:
                raise
            time.sleep(LOCK_RETRY_BACKOFF_SECONDS[attempt_index])
    assert con is not None
    if not read_only:
        _ensure_schema(con)
    return con


def _is_lock_contention_error(exc: Exception) -> bool:
    return isinstance(exc, duckdb.IOException) and "Could not set lock on file" in str(exc)


def _ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(SCHEMA_DDL)
