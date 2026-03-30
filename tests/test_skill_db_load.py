from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import duckdb
import pytest

from skill_pipeline import cli, db_schema
from skill_pipeline.db_load import run_db_load
from skill_pipeline.db_schema import open_pipeline_db
from skill_pipeline.paths import build_skill_paths


def _write_canonical_fixture(
    tmp_path: Path,
    slug: str = "imprivata",
    *,
    actors: list[dict] | None = None,
    events: list[dict] | None = None,
    spans: list[dict] | None = None,
    deterministic_enrichment: dict | None = None,
    enrichment: dict | None = None,
) -> Path:
    paths = build_skill_paths(slug, project_root=tmp_path)
    paths.source_dir.mkdir(parents=True, exist_ok=True)
    paths.extract_dir.mkdir(parents=True, exist_ok=True)
    paths.enrich_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "raw" / slug / "filings").mkdir(parents=True, exist_ok=True)

    actors_payload = {
        "actors": actors or _default_actors(),
        "count_assertions": [],
        "unresolved_mentions": [],
    }
    events_payload = {
        "events": events or _default_events(),
        "exclusions": [],
        "coverage_notes": [],
    }
    spans_payload = {"spans": spans or _default_spans()}

    (paths.seeds_path.parent).mkdir(parents=True, exist_ok=True)
    paths.seeds_path.write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com/{slug},false\n"
        ),
        encoding="utf-8",
    )
    paths.chronology_blocks_path.write_text(
        "\n".join(json.dumps(block) for block in _chronology_blocks(spans_payload["spans"])) + "\n",
        encoding="utf-8",
    )
    paths.evidence_items_path.write_text("", encoding="utf-8")
    paths.document_registry_path.parent.mkdir(parents=True, exist_ok=True)
    paths.document_registry_path.write_text(
        json.dumps(
            {
                "artifact_type": "raw_document_registry",
                "documents": [
                    {
                        "document_id": "DOC001",
                        "accession_number": "DOC001",
                        "filing_type": "DEFM14A",
                        "txt_path": f"raw/{slug}/filings/DOC001.txt",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "raw" / slug / "filings" / "DOC001.txt").write_text(
        "\n".join(span["quote_text"] for span in spans_payload["spans"]) + "\n",
        encoding="utf-8",
    )
    paths.actors_raw_path.write_text(json.dumps(actors_payload), encoding="utf-8")
    paths.events_raw_path.write_text(json.dumps(events_payload), encoding="utf-8")
    paths.spans_path.write_text(json.dumps(spans_payload), encoding="utf-8")
    paths.deterministic_enrichment_path.write_text(
        json.dumps(deterministic_enrichment or _default_deterministic_enrichment()),
        encoding="utf-8",
    )
    paths.enrichment_path.write_text(
        json.dumps(enrichment if enrichment is not None else _minimal_enrichment()),
        encoding="utf-8",
    )
    return paths.database_path


def _write_quote_first_fixture(tmp_path: Path, slug: str = "imprivata") -> None:
    paths = build_skill_paths(slug, project_root=tmp_path)
    paths.source_dir.mkdir(parents=True, exist_ok=True)
    paths.extract_dir.mkdir(parents=True, exist_ok=True)
    paths.enrich_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "raw" / slug / "filings").mkdir(parents=True, exist_ok=True)
    paths.seeds_path.parent.mkdir(parents=True, exist_ok=True)

    paths.seeds_path.write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com/{slug},false\n"
        ),
        encoding="utf-8",
    )
    paths.chronology_blocks_path.write_text(
        json.dumps(
            {
                "block_id": "B001",
                "document_id": "DOC001",
                "ordinal": 1,
                "start_line": 1,
                "end_line": 1,
                "raw_text": "Party A signed a confidentiality agreement.",
                "clean_text": "Party A signed a confidentiality agreement.",
                "is_heading": False,
                "page_break_before": False,
                "page_break_after": False,
                "date_mentions": [],
                "entity_mentions": [],
                "evidence_density": 0,
                "temporal_phase": "other",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    paths.evidence_items_path.write_text("", encoding="utf-8")
    paths.document_registry_path.parent.mkdir(parents=True, exist_ok=True)
    paths.document_registry_path.write_text(
        json.dumps(
            {
                "artifact_type": "raw_document_registry",
                "documents": [
                    {
                        "document_id": "DOC001",
                        "accession_number": "DOC001",
                        "filing_type": "DEFM14A",
                        "txt_path": f"raw/{slug}/filings/DOC001.txt",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "raw" / slug / "filings" / "DOC001.txt").write_text(
        "Party A signed a confidentiality agreement.\n",
        encoding="utf-8",
    )
    paths.actors_raw_path.write_text(
        json.dumps(
            {
                "quotes": [
                    {"quote_id": "Q001", "block_id": "B001", "text": "Party A"}
                ],
                "actors": [
                    {
                        "actor_id": "bidder_a",
                        "display_name": "Party A",
                        "canonical_name": "PARTY A",
                        "aliases": [],
                        "role": "bidder",
                        "advisor_kind": None,
                        "advised_actor_id": None,
                        "bidder_kind": "strategic",
                        "listing_status": "public",
                        "geography": "domestic",
                        "is_grouped": False,
                        "group_size": None,
                        "group_label": None,
                        "quote_ids": ["Q001"],
                        "notes": [],
                    }
                ],
                "count_assertions": [],
                "unresolved_mentions": [],
            }
        ),
        encoding="utf-8",
    )
    paths.events_raw_path.write_text(
        json.dumps(
            {
                "quotes": [
                    {
                        "quote_id": "Q101",
                        "block_id": "B001",
                        "text": "signed a confidentiality agreement",
                    }
                ],
                "events": [
                    {
                        "event_id": "evt_001",
                        "event_type": "nda",
                        "date": {
                            "raw_text": "June 1, 2016",
                            "normalized_hint": "2016-06-01",
                        },
                        "actor_ids": ["bidder_a"],
                        "summary": "Party A signed a confidentiality agreement.",
                        "quote_ids": ["Q101"],
                        "terms": None,
                        "formality_signals": None,
                        "whole_company_scope": True,
                        "drop_reason_text": None,
                        "round_scope": None,
                        "invited_actor_ids": [],
                        "deadline_date": None,
                        "executed_with_actor_id": None,
                        "boundary_note": None,
                        "nda_signed": True,
                        "notes": [],
                    }
                ],
                "exclusions": [],
                "coverage_notes": [],
            }
        ),
        encoding="utf-8",
    )
    paths.spans_path.write_text(json.dumps({"spans": []}), encoding="utf-8")
    paths.deterministic_enrichment_path.write_text(
        json.dumps(_default_deterministic_enrichment()),
        encoding="utf-8",
    )
    paths.enrichment_path.write_text(
        json.dumps(_minimal_enrichment()),
        encoding="utf-8",
    )


def _default_actors() -> list[dict]:
    return [
        {
            "actor_id": "bidder_a",
            "display_name": "Party A",
            "canonical_name": "PARTY A",
            "aliases": ["Sponsor A"],
            "role": "bidder",
            "advisor_kind": None,
            "advised_actor_id": None,
            "bidder_kind": "strategic",
            "listing_status": "public",
            "geography": "domestic",
            "is_grouped": False,
            "group_size": None,
            "group_label": None,
            "evidence_span_ids": ["span_actor_bidder"],
            "notes": [],
        },
        {
            "actor_id": "advisor_bank",
            "display_name": "Morgan Stanley",
            "canonical_name": "MORGAN STANLEY",
            "aliases": [],
            "role": "advisor",
            "advisor_kind": "financial",
            "advised_actor_id": "target_board",
            "bidder_kind": None,
            "listing_status": None,
            "geography": None,
            "is_grouped": False,
            "group_size": None,
            "group_label": None,
            "evidence_span_ids": ["span_actor_advisor"],
            "notes": [],
        },
        {
            "actor_id": "target_board",
            "display_name": "Imprivata Board",
            "canonical_name": "IMPRIVATA BOARD",
            "aliases": ["Company"],
            "role": "target_board",
            "advisor_kind": None,
            "advised_actor_id": None,
            "bidder_kind": None,
            "listing_status": None,
            "geography": None,
            "is_grouped": False,
            "group_size": None,
            "group_label": None,
            "evidence_span_ids": ["span_actor_target"],
            "notes": [],
        },
    ]


def _default_events() -> list[dict]:
    return [
        {
            "event_id": "evt_001",
            "event_type": "nda",
            "date": _resolved_date("June 1, 2016", "2016-06-01", "exact_day"),
            "actor_ids": ["bidder_a"],
            "summary": "Party A signed a confidentiality agreement.",
            "evidence_span_ids": ["span_evt_nda"],
            "terms": None,
            "formality_signals": None,
            "whole_company_scope": True,
            "drop_reason_text": None,
            "round_scope": None,
            "invited_actor_ids": [],
            "deadline_date": None,
            "executed_with_actor_id": None,
            "boundary_note": None,
            "nda_signed": True,
            "notes": [],
        },
        {
            "event_id": "evt_002",
            "event_type": "proposal",
            "date": _resolved_date("June 10, 2016", "2016-06-10", "exact_day"),
            "actor_ids": ["bidder_a"],
            "summary": "Party A submitted a $25.00 per-share proposal.",
            "evidence_span_ids": ["span_evt_proposal"],
            "terms": {
                "per_share": 25.0,
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": "cash",
            },
            "formality_signals": None,
            "whole_company_scope": True,
            "drop_reason_text": None,
            "round_scope": None,
            "invited_actor_ids": [],
            "deadline_date": None,
            "executed_with_actor_id": None,
            "boundary_note": None,
            "nda_signed": None,
            "notes": [],
        },
        {
            "event_id": "evt_003",
            "event_type": "drop",
            "date": _resolved_date("June 20, 2016", "2016-06-20", "exact_day"),
            "actor_ids": ["bidder_a"],
            "summary": "Party A withdrew after declining to improve its proposal.",
            "evidence_span_ids": ["span_evt_drop"],
            "terms": None,
            "formality_signals": None,
            "whole_company_scope": True,
            "drop_reason_text": "Party A declined to improve its informal proposal.",
            "round_scope": None,
            "invited_actor_ids": [],
            "deadline_date": None,
            "executed_with_actor_id": None,
            "boundary_note": None,
            "nda_signed": None,
            "notes": [],
        },
        {
            "event_id": "evt_004",
            "event_type": "executed",
            "date": _resolved_date("July 13, 2016", "2016-07-13", "exact_day"),
            "actor_ids": ["bidder_a"],
            "summary": "The company executed a merger agreement with Party A.",
            "evidence_span_ids": ["span_evt_executed"],
            "terms": None,
            "formality_signals": None,
            "whole_company_scope": True,
            "drop_reason_text": None,
            "round_scope": None,
            "invited_actor_ids": [],
            "deadline_date": None,
            "executed_with_actor_id": "bidder_a",
            "boundary_note": None,
            "nda_signed": None,
            "notes": [],
        },
    ]


def _default_spans() -> list[dict]:
    return [
        _span("span_actor_bidder", "B001", 1, "Party A was a bidder."),
        _span("span_actor_advisor", "B002", 2, "Morgan Stanley advised the Company."),
        _span("span_actor_target", "B003", 3, "The Imprivata board evaluated strategic alternatives."),
        _span("span_evt_nda", "B010", 10, "Party A signed a confidentiality agreement."),
        _span("span_evt_proposal", "B011", 11, "Party A submitted a $25.00 per-share proposal."),
        _span("span_evt_drop", "B012", 12, "Party A declined to improve its proposal."),
        _span("span_evt_executed", "B013", 13, "The company executed a merger agreement with Party A."),
    ]


def _default_deterministic_enrichment() -> dict:
    return {
        "rounds": [],
        "bid_classifications": {
            "evt_002": {
                "label": "Formal",
                "rule_applied": 2.0,
                "basis": "Proposal included formal documentation.",
            }
        },
        "cycles": [
            {
                "cycle_id": "cycle_1",
                "start_event_id": "evt_001",
                "end_event_id": "evt_004",
                "boundary_basis": "Single cycle -- no termination events",
            }
        ],
        "formal_boundary": {
            "cycle_1": {
                "event_id": "evt_002",
                "basis": "First formal proposal in cycle_1.",
            }
        },
        "dropout_classifications": {},
        "all_cash_overrides": {},
    }


def _minimal_enrichment() -> dict:
    """Minimal enrichment.json with 5 required keys but no dropout data."""
    return {
        "dropout_classifications": {},
        "initiation_judgment": {
            "type": "target_driven",
            "basis": "The board initiated a sale review.",
            "source_text": "The board evaluated strategic alternatives.",
            "confidence": "high",
        },
        "advisory_verification": {},
        "count_reconciliation": [],
        "review_flags": [],
    }


def _default_interpretive_enrichment() -> dict:
    """Enrichment.json with interpretive dropout classifications."""
    base = _minimal_enrichment()
    base["dropout_classifications"] = {
        "evt_003": {
            "label": "DropAtInf",
            "basis": "Party A stayed at its earlier informal price.",
            "source_text": "Party A declined to improve its proposal.",
        }
    }
    return base


def _resolved_date(raw_text: str | None, sort_date: str | None, precision: str) -> dict:
    return {
        "raw_text": raw_text,
        "normalized_start": sort_date,
        "normalized_end": sort_date,
        "sort_date": sort_date,
        "precision": precision,
        "anchor_event_id": None,
        "anchor_span_id": None,
        "resolution_note": None,
        "is_inferred": False,
    }


def _span(span_id: str, block_id: str, start_line: int, quote_text: str) -> dict:
    return {
        "span_id": span_id,
        "document_id": "DOC001",
        "filing_type": "DEFM14A",
        "start_line": start_line,
        "end_line": start_line,
        "block_ids": [block_id],
        "evidence_ids": [],
        "anchor_text": quote_text,
        "quote_text": quote_text,
        "quote_text_normalized": quote_text.lower(),
        "match_type": "exact",
        "resolution_note": None,
    }


def _chronology_blocks(spans: list[dict]) -> list[dict]:
    blocks = []
    for ordinal, span in enumerate(spans, start=1):
        blocks.append(
            {
                "block_id": span["block_ids"][0],
                "document_id": span["document_id"],
                "ordinal": ordinal,
                "start_line": span["start_line"],
                "end_line": span["end_line"],
                "raw_text": span["quote_text"],
                "clean_text": span["quote_text"],
                "is_heading": False,
                "page_break_before": False,
                "page_break_after": False,
                "date_mentions": [],
                "entity_mentions": [],
                "evidence_density": 0,
                "temporal_phase": "other",
            }
        )
    return blocks


def test_build_skill_paths_exposes_database_path(tmp_path: Path) -> None:
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    assert paths.database_path == tmp_path / "data" / "pipeline.duckdb"


def test_open_pipeline_db_creates_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "data" / "pipeline.duckdb"

    con = open_pipeline_db(db_path)
    tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
    con.close()

    assert db_path.exists()
    assert tables == {"actors", "cycles", "enrichment", "events", "rounds", "spans"}


def test_open_pipeline_db_supports_read_only(tmp_path: Path) -> None:
    db_path = tmp_path / "data" / "pipeline.duckdb"
    open_pipeline_db(db_path).close()

    con = open_pipeline_db(db_path, read_only=True)
    assert con.execute("SELECT COUNT(*) FROM actors").fetchone()[0] == 0
    con.close()


def test_open_pipeline_db_retries_lock_contention_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    attempts: list[tuple[str, bool]] = []
    sleep_calls: list[float] = []
    db_path = tmp_path / "data" / "pipeline.duckdb"
    expected_con = object()

    def fake_connect(path: str, *, read_only: bool = False):
        attempts.append((path, read_only))
        if len(attempts) < 3:
            raise duckdb.IOException(
                'IO Error: Could not set lock on file "/tmp/pipeline.duckdb": Conflicting lock is held'
            )
        return expected_con

    monkeypatch.setattr(db_schema.duckdb, "connect", fake_connect)
    monkeypatch.setattr(db_schema.time, "sleep", sleep_calls.append)

    con = db_schema.open_pipeline_db(db_path, read_only=True)

    assert db_schema.LOCK_RETRY_ATTEMPTS == 3
    assert db_schema.LOCK_RETRY_BACKOFF_SECONDS == (0.25, 0.5, 1.0)
    assert con is expected_con
    assert attempts == [
        (str(db_path), True),
        (str(db_path), True),
        (str(db_path), True),
    ]
    assert sleep_calls == [0.25, 0.5]


def test_open_pipeline_db_raises_after_exhausting_lock_retries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    attempts: list[tuple[str, bool]] = []
    sleep_calls: list[float] = []
    db_path = tmp_path / "data" / "pipeline.duckdb"

    def fake_connect(path: str, *, read_only: bool = False):
        attempts.append((path, read_only))
        raise duckdb.IOException(
            'IO Error: Could not set lock on file "/tmp/pipeline.duckdb": Conflicting lock is held'
        )

    monkeypatch.setattr(db_schema.duckdb, "connect", fake_connect)
    monkeypatch.setattr(db_schema.time, "sleep", sleep_calls.append)

    with pytest.raises(duckdb.IOException, match="Could not set lock on file"):
        db_schema.open_pipeline_db(db_path, read_only=True)

    assert len(attempts) == 3
    assert sleep_calls == [0.25, 0.5]


def test_open_pipeline_db_does_not_retry_non_lock_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    attempts: list[tuple[str, bool]] = []
    sleep_calls: list[float] = []
    db_path = tmp_path / "data" / "pipeline.duckdb"

    def fake_connect(path: str, *, read_only: bool = False):
        attempts.append((path, read_only))
        raise duckdb.ConnectionException("Connection Error: invalid connection setup")

    monkeypatch.setattr(db_schema.duckdb, "connect", fake_connect)
    monkeypatch.setattr(db_schema.time, "sleep", sleep_calls.append)

    with pytest.raises(duckdb.ConnectionException, match="invalid connection setup"):
        db_schema.open_pipeline_db(db_path, read_only=True)

    assert attempts == [(str(db_path), True)]
    assert sleep_calls == []


def test_run_db_load_loads_canonical_artifacts(tmp_path: Path) -> None:
    db_path = _write_canonical_fixture(tmp_path)

    exit_code = run_db_load("imprivata", project_root=tmp_path)

    con = open_pipeline_db(db_path, read_only=True)
    actor_count = con.execute("SELECT COUNT(*) FROM actors").fetchone()[0]
    event_count = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    span_count = con.execute("SELECT COUNT(*) FROM spans").fetchone()[0]
    enrichment_count = con.execute("SELECT COUNT(*) FROM enrichment").fetchone()[0]
    cycle_count = con.execute("SELECT COUNT(*) FROM cycles").fetchone()[0]
    round_count = con.execute("SELECT COUNT(*) FROM rounds").fetchone()[0]
    con.close()

    assert exit_code == 0
    assert actor_count == 3
    assert event_count == 4
    assert span_count == 7
    assert enrichment_count == 1
    assert cycle_count == 1
    assert round_count == 0


def test_run_db_load_round_trips_actor_event_and_span_fields(tmp_path: Path) -> None:
    db_path = _write_canonical_fixture(tmp_path)
    run_db_load("imprivata", project_root=tmp_path)

    con = open_pipeline_db(db_path, read_only=True)
    actor_row = con.execute(
        """
        SELECT display_name, bidder_kind, listing_status, evidence_span_ids
        FROM actors
        WHERE deal_slug = ? AND actor_id = ?
        """,
        ["imprivata", "bidder_a"],
    ).fetchone()
    event_row = con.execute(
        """
        SELECT date_raw_text, date_sort, date_precision, terms_per_share, terms_consideration_type
        FROM events
        WHERE deal_slug = ? AND event_id = ?
        """,
        ["imprivata", "evt_002"],
    ).fetchone()
    span_row = con.execute(
        """
        SELECT document_id, block_ids, quote_text, match_type
        FROM spans
        WHERE deal_slug = ? AND span_id = ?
        """,
        ["imprivata", "span_evt_proposal"],
    ).fetchone()
    con.close()

    assert actor_row == ("Party A", "strategic", "public", ["span_actor_bidder"])
    assert event_row == ("June 10, 2016", date(2016, 6, 10), "exact_day", 25.0, "cash")
    assert span_row == (
        "DOC001",
        ["B011"],
        "Party A submitted a $25.00 per-share proposal.",
        "exact",
    )


def test_run_db_load_replaces_existing_rows_for_same_deal(tmp_path: Path) -> None:
    db_path = _write_canonical_fixture(tmp_path)
    run_db_load("imprivata", project_root=tmp_path)

    updated_actors = _default_actors()
    updated_actors[0]["display_name"] = "Party A Updated"
    _write_canonical_fixture(tmp_path, actors=updated_actors)
    run_db_load("imprivata", project_root=tmp_path)

    con = open_pipeline_db(db_path, read_only=True)
    actor_count = con.execute(
        "SELECT COUNT(*) FROM actors WHERE deal_slug = ?",
        ["imprivata"],
    ).fetchone()[0]
    display_name = con.execute(
        "SELECT display_name FROM actors WHERE deal_slug = ? AND actor_id = ?",
        ["imprivata", "bidder_a"],
    ).fetchone()[0]
    con.close()

    assert actor_count == 3
    assert display_name == "Party A Updated"


def test_run_db_load_keeps_multiple_deals_in_same_database(tmp_path: Path) -> None:
    db_path = _write_canonical_fixture(tmp_path, "deal-a")
    _write_canonical_fixture(tmp_path, "deal-b")

    run_db_load("deal-a", project_root=tmp_path)
    run_db_load("deal-b", project_root=tmp_path)

    con = open_pipeline_db(db_path, read_only=True)
    counts = con.execute(
        "SELECT deal_slug, COUNT(*) FROM events GROUP BY deal_slug ORDER BY deal_slug"
    ).fetchall()
    con.close()

    assert counts == [("deal-a", 4), ("deal-b", 4)]


def test_run_db_load_requires_canonical_extract_artifacts(tmp_path: Path) -> None:
    _write_canonical_fixture(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    paths.actors_raw_path.unlink()

    with pytest.raises(FileNotFoundError, match="actors_raw.json"):
        run_db_load("imprivata", project_root=tmp_path)


def test_run_db_load_rejects_quote_first_extracts(tmp_path: Path) -> None:
    _write_quote_first_fixture(tmp_path)

    with pytest.raises(ValueError, match="canonical extract artifacts"):
        run_db_load("imprivata", project_root=tmp_path)


def test_run_db_load_requires_deterministic_enrichment(tmp_path: Path) -> None:
    _write_canonical_fixture(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    paths.deterministic_enrichment_path.unlink()

    with pytest.raises(FileNotFoundError, match="deterministic_enrichment.json"):
        run_db_load("imprivata", project_root=tmp_path)


def test_run_db_load_requires_enrichment(tmp_path: Path) -> None:
    _write_canonical_fixture(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    paths.enrichment_path.unlink()

    with pytest.raises(FileNotFoundError, match="enrichment.json"):
        run_db_load("imprivata", project_root=tmp_path)


def test_run_db_load_rejects_malformed_interpretive_enrichment(tmp_path: Path) -> None:
    _write_canonical_fixture(
        tmp_path,
        enrichment={"dropout_classifications": {}},
    )

    with pytest.raises(ValueError, match="initiation_judgment"):
        run_db_load("imprivata", project_root=tmp_path)


def test_run_db_load_leaves_dropout_columns_null_with_minimal_enrichment(tmp_path: Path) -> None:
    db_path = _write_canonical_fixture(tmp_path)
    run_db_load("imprivata", project_root=tmp_path)

    con = open_pipeline_db(db_path, read_only=True)
    row = con.execute(
        """
        SELECT bid_label, dropout_label, dropout_basis
        FROM enrichment
        WHERE deal_slug = ? AND event_id = ?
        """,
        ["imprivata", "evt_002"],
    ).fetchone()
    con.close()

    assert row == ("Formal", None, None)


def test_run_db_load_overlays_dropout_classification_when_present(tmp_path: Path) -> None:
    db_path = _write_canonical_fixture(
        tmp_path,
        enrichment=_default_interpretive_enrichment(),
    )
    run_db_load("imprivata", project_root=tmp_path)

    con = open_pipeline_db(db_path, read_only=True)
    row = con.execute(
        """
        SELECT bid_label, dropout_label, dropout_basis
        FROM enrichment
        WHERE deal_slug = ? AND event_id = ?
        """,
        ["imprivata", "evt_003"],
    ).fetchone()
    con.close()

    assert row == (
        None,
        "DropAtInf",
        "Party A stayed at its earlier informal price.",
    )


def test_run_db_load_loads_deterministic_dropout_classifications(tmp_path: Path) -> None:
    enrichment_data = _default_deterministic_enrichment()
    enrichment_data["dropout_classifications"] = {
        "evt_003": {
            "label": "DropTarget",
            "basis": "Bidder active but not in invited_actor_ids for round.",
            "source_text": "Party A was no longer participating.",
        }
    }
    db_path = _write_canonical_fixture(
        tmp_path,
        deterministic_enrichment=enrichment_data,
    )

    run_db_load("imprivata", project_root=tmp_path)

    con = open_pipeline_db(db_path, read_only=True)
    row = con.execute(
        "SELECT dropout_label, dropout_basis FROM enrichment WHERE deal_slug = ? AND event_id = ?",
        ["imprivata", "evt_003"],
    ).fetchone()
    con.close()

    assert row[0] == "DropTarget"
    assert "invited_actor_ids" in row[1]


def test_run_db_load_deterministic_dropout_overlaid_by_interpretive(tmp_path: Path) -> None:
    enrichment_data = _default_deterministic_enrichment()
    enrichment_data["dropout_classifications"] = {
        "evt_003": {
            "label": "DropTarget",
            "basis": "Bidder active but not in invited_actor_ids for round.",
            "source_text": "Party A was no longer participating.",
        }
    }
    db_path = _write_canonical_fixture(
        tmp_path,
        deterministic_enrichment=enrichment_data,
        enrichment=_default_interpretive_enrichment(),
    )

    run_db_load("imprivata", project_root=tmp_path)

    con = open_pipeline_db(db_path, read_only=True)
    row = con.execute(
        "SELECT dropout_label, dropout_basis FROM enrichment WHERE deal_slug = ? AND event_id = ?",
        ["imprivata", "evt_003"],
    ).fetchone()
    con.close()

    assert row == (
        "DropAtInf",
        "Party A stayed at its earlier informal price.",
    )


def test_run_db_load_loads_all_cash_overrides(tmp_path: Path) -> None:
    enrichment_data = _default_deterministic_enrichment()
    enrichment_data["all_cash_overrides"] = {"evt_002": True}
    db_path = _write_canonical_fixture(
        tmp_path,
        deterministic_enrichment=enrichment_data,
    )

    run_db_load("imprivata", project_root=tmp_path)

    con = open_pipeline_db(db_path, read_only=True)
    row = con.execute(
        "SELECT all_cash_override FROM enrichment WHERE deal_slug = ? AND event_id = ?",
        ["imprivata", "evt_002"],
    ).fetchone()
    con.close()

    assert row[0] is True


def test_run_db_load_all_cash_override_null_when_not_in_overrides(tmp_path: Path) -> None:
    db_path = _write_canonical_fixture(tmp_path)

    run_db_load("imprivata", project_root=tmp_path)

    con = open_pipeline_db(db_path, read_only=True)
    row = con.execute(
        "SELECT all_cash_override FROM enrichment WHERE deal_slug = ? AND event_id = ?",
        ["imprivata", "evt_002"],
    ).fetchone()
    con.close()

    assert row[0] is None


def test_run_db_load_backward_compatible_without_new_enrichment_keys(tmp_path: Path) -> None:
    db_path = _write_canonical_fixture(tmp_path)

    run_db_load("imprivata", project_root=tmp_path)

    con = open_pipeline_db(db_path, read_only=True)
    rows = con.execute(
        "SELECT event_id, all_cash_override FROM enrichment WHERE deal_slug = ?",
        ["imprivata"],
    ).fetchall()
    con.close()

    assert len(rows) > 0
    assert all(row[1] is None for row in rows)


def test_db_load_cli_subcommand_dispatches(tmp_path: Path) -> None:
    db_path = _write_canonical_fixture(tmp_path)

    exit_code = cli.main(["db-load", "--deal", "imprivata", "--project-root", str(tmp_path)])

    con = open_pipeline_db(db_path, read_only=True)
    event_count = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    con.close()

    assert exit_code == 0
    assert event_count == 4
