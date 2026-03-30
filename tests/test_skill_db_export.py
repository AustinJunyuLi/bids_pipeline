from __future__ import annotations

import csv
from multiprocessing import get_context
from pathlib import Path
import threading

import duckdb
import pytest

from skill_pipeline import cli
from skill_pipeline.db_export import run_db_export
from skill_pipeline.db_load import run_db_load
from skill_pipeline import db_schema
from skill_pipeline.db_schema import open_pipeline_db
from skill_pipeline.paths import build_skill_paths
from tests.test_skill_db_load import (
    _default_actors,
    _default_deterministic_enrichment,
    _default_events,
    _resolved_date,
    _span,
    _write_canonical_fixture,
)


def _load_fixture(
    tmp_path: Path,
    slug: str = "imprivata",
    *,
    actors: list[dict] | None = None,
    events: list[dict] | None = None,
    spans: list[dict] | None = None,
    deterministic_enrichment: dict | None = None,
    enrichment: dict | None = None,
) -> Path:
    _write_canonical_fixture(
        tmp_path,
        slug,
        actors=actors,
        events=events,
        spans=spans,
        deterministic_enrichment=deterministic_enrichment,
        enrichment=enrichment,
    )
    run_db_load(slug, project_root=tmp_path)
    return build_skill_paths(slug, project_root=tmp_path).deal_events_path


def _read_rows(path: Path) -> list[list[str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def _events_with_untyped_cash_proposal() -> list[dict]:
    events = _default_events()
    proposal = dict(events[1])
    proposal_terms = dict(proposal["terms"])
    proposal_terms["consideration_type"] = None
    proposal["terms"] = proposal_terms
    events[1] = proposal
    return events


def _hold_duckdb_write_lock(db_path: str, ready, release) -> None:
    con = duckdb.connect(db_path)
    con.execute("CREATE TABLE IF NOT EXISTS export_lock_probe(x INTEGER)")
    con.execute("INSERT INTO export_lock_probe VALUES (1)")
    ready.set()
    release.wait(timeout=5)
    con.close()


def test_run_db_export_writes_deal_events_csv(tmp_path: Path) -> None:
    output_path = _load_fixture(tmp_path)

    exit_code = run_db_export("imprivata", project_root=tmp_path)

    assert exit_code == 0
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_run_db_export_writes_deal_header_block_first(tmp_path: Path) -> None:
    output_path = _load_fixture(tmp_path)
    run_db_export("imprivata", project_root=tmp_path)

    rows = _read_rows(output_path)

    assert rows[0] == ["TargetName", "Events", "Acquirer", "DateAnnounced", "URL"]
    assert rows[1] == [
        "IMPRIVATA INC",
        "4",
        "THOMA BRAVO LLC",
        "2016-07-13 00:00:00",
        "https://example.com/imprivata",
    ]


def test_run_db_export_writes_fourteen_column_event_rows(tmp_path: Path) -> None:
    output_path = _load_fixture(tmp_path)
    run_db_export("imprivata", project_root=tmp_path)

    rows = _read_rows(output_path)

    assert len(rows) == 6
    assert all(len(row) == 14 for row in rows[2:])


def test_run_db_export_assigns_fractional_and_integer_bidder_ids(tmp_path: Path) -> None:
    actors = _default_actors()
    spans = [
        _span("span_evt_001", "B001", 1, "The board initiated a sale process."),
        _span("span_evt_002", "B002", 2, "Party A expressed interest."),
        _span("span_evt_003", "B003", 3, "Party A signed a confidentiality agreement."),
        _span("span_evt_004", "B004", 4, "Party A submitted a proposal."),
        _span("span_evt_005", "B005", 5, "The company executed a merger agreement with Party A."),
    ]
    events = [
        {
            "event_id": "evt_001",
            "event_type": "target_sale",
            "date": _resolved_date("May 1, 2016", "2016-05-01", "exact_day"),
            "actor_ids": [],
            "summary": "The board initiated a sale process.",
            "evidence_span_ids": ["span_evt_001"],
            "terms": None,
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
            "event_id": "evt_002",
            "event_type": "bidder_interest",
            "date": _resolved_date("May 2, 2016", "2016-05-02", "exact_day"),
            "actor_ids": ["bidder_a"],
            "summary": "Party A expressed interest.",
            "evidence_span_ids": ["span_evt_002"],
            "terms": None,
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
            "event_type": "nda",
            "date": _resolved_date("May 3, 2016", "2016-05-03", "exact_day"),
            "actor_ids": ["bidder_a"],
            "summary": "Party A signed a confidentiality agreement.",
            "evidence_span_ids": ["span_evt_003"],
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
            "event_id": "evt_004",
            "event_type": "proposal",
            "date": _resolved_date("May 4, 2016", "2016-05-04", "exact_day"),
            "actor_ids": ["bidder_a"],
            "summary": "Party A submitted a proposal.",
            "evidence_span_ids": ["span_evt_004"],
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
            "event_id": "evt_005",
            "event_type": "executed",
            "date": _resolved_date("May 5, 2016", "2016-05-05", "exact_day"),
            "actor_ids": ["bidder_a"],
            "summary": "The company executed a merger agreement with Party A.",
            "evidence_span_ids": ["span_evt_005"],
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
    deterministic_enrichment = {
        "rounds": [],
        "bid_classifications": {
            "evt_004": {
                "label": "Formal",
                "rule_applied": 2.0,
                "basis": "Formal proposal",
            }
        },
        "cycles": [
            {
                "cycle_id": "cycle_1",
                "start_event_id": "evt_001",
                "end_event_id": "evt_005",
                "boundary_basis": "Single cycle -- no termination events",
            }
        ],
        "formal_boundary": {
            "cycle_1": {"event_id": "evt_004", "basis": "First formal proposal"}
        },
        "dropout_classifications": {},
        "all_cash_overrides": {},
    }
    output_path = _load_fixture(
        tmp_path,
        actors=actors,
        events=events,
        spans=spans,
        deterministic_enrichment=deterministic_enrichment,
    )

    run_db_export("imprivata", project_root=tmp_path)

    rows = _read_rows(output_path)
    bidder_ids = [row[0] for row in rows[2:]]

    assert bidder_ids == ["0.3", "0.7", "1", "2", "3"]


def test_run_db_export_formats_exact_imprecise_and_unknown_dates(tmp_path: Path) -> None:
    actors = _default_actors()
    spans = [
        _span("span_evt_001", "B001", 1, "Party A signed a confidentiality agreement."),
        _span("span_evt_002", "B002", 2, "Party A submitted a proposal in mid June."),
        _span("span_evt_003", "B003", 3, "Party A later withdrew."),
    ]
    events = [
        {
            "event_id": "evt_001",
            "event_type": "nda",
            "date": _resolved_date("June 1, 2016", "2016-06-01", "exact_day"),
            "actor_ids": ["bidder_a"],
            "summary": "Party A signed a confidentiality agreement.",
            "evidence_span_ids": ["span_evt_001"],
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
            "date": _resolved_date("mid June 2016", "2016-06-15", "month_mid"),
            "actor_ids": ["bidder_a"],
            "summary": "Party A submitted a proposal in mid June.",
            "evidence_span_ids": ["span_evt_002"],
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
            "date": _resolved_date(None, None, "unknown"),
            "actor_ids": ["bidder_a"],
            "summary": "Party A later withdrew.",
            "evidence_span_ids": ["span_evt_003"],
            "terms": None,
            "formality_signals": None,
            "whole_company_scope": True,
            "drop_reason_text": "Party A later withdrew.",
            "round_scope": None,
            "invited_actor_ids": [],
            "deadline_date": None,
            "executed_with_actor_id": None,
            "boundary_note": None,
            "nda_signed": None,
            "notes": [],
        },
    ]
    deterministic_enrichment = {
        "rounds": [],
        "bid_classifications": {
            "evt_002": {
                "label": "Formal",
                "rule_applied": 2.0,
                "basis": "Formal proposal",
            }
        },
        "cycles": [
            {
                "cycle_id": "cycle_1",
                "start_event_id": "evt_001",
                "end_event_id": "evt_003",
                "boundary_basis": "Single cycle -- no termination events",
            }
        ],
        "formal_boundary": {
            "cycle_1": {"event_id": "evt_002", "basis": "First formal proposal"}
        },
        "dropout_classifications": {},
        "all_cash_overrides": {},
    }
    output_path = _load_fixture(
        tmp_path,
        actors=actors,
        events=events,
        spans=spans,
        deterministic_enrichment=deterministic_enrichment,
    )

    run_db_export("imprivata", project_root=tmp_path)

    rows = _read_rows(output_path)

    assert rows[2][7:9] == ["2016-06-01 00:00:00", "2016-06-01 00:00:00"]
    assert rows[3][7:9] == ["2016-06-15 00:00:00", "NA"]
    assert rows[4][7:9] == ["NA", "NA"]


def test_run_db_export_renders_null_values_as_na(tmp_path: Path) -> None:
    output_path = _load_fixture(tmp_path)
    run_db_export("imprivata", project_root=tmp_path)

    rows = _read_rows(output_path)
    proposal_row = rows[3]
    executed_row = rows[5]

    assert proposal_row[1] == "NA"
    assert proposal_row[3] == "NA"
    assert executed_row[4] == "NA"
    assert executed_row[5] == "NA"
    assert executed_row[13] == "NA"


def test_run_db_export_retries_transient_duckdb_lock_contention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = _load_fixture(tmp_path)
    db_path = build_skill_paths("imprivata", project_root=tmp_path).database_path
    multiprocessing_context = get_context("spawn")
    ready = multiprocessing_context.Event()
    release = multiprocessing_context.Event()
    lock_holder = multiprocessing_context.Process(
        target=_hold_duckdb_write_lock,
        args=(str(db_path), ready, release),
    )

    monkeypatch.setattr(db_schema, "LOCK_RETRY_BACKOFF_SECONDS", (0.05, 0.1, 0.2))
    lock_holder.start()
    assert ready.wait(timeout=5)

    release_timer = threading.Timer(0.08, release.set)
    release_timer.start()
    try:
        exit_code = run_db_export("imprivata", project_root=tmp_path)
    finally:
        release.set()
        release_timer.cancel()
        lock_holder.join(timeout=5)
        if lock_holder.is_alive():
            lock_holder.terminate()
            lock_holder.join(timeout=5)

    rows = _read_rows(output_path)

    assert lock_holder.exitcode == 0
    assert exit_code == 0
    assert rows[0][0] == "TargetName"


def test_run_db_export_requires_existing_database(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="pipeline.duckdb"):
        run_db_export("imprivata", project_root=tmp_path)


def test_run_db_export_requires_events_for_deal(tmp_path: Path) -> None:
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    open_pipeline_db(paths.database_path).close()

    with pytest.raises(ValueError, match="No events found for deal 'imprivata'"):
        run_db_export("imprivata", project_root=tmp_path)


def test_all_cash_override_produces_1_in_export(tmp_path: Path) -> None:
    deterministic_enrichment = _default_deterministic_enrichment()
    deterministic_enrichment["all_cash_overrides"] = {"evt_002": True}
    output_path = _load_fixture(
        tmp_path,
        events=_events_with_untyped_cash_proposal(),
        deterministic_enrichment=deterministic_enrichment,
    )

    run_db_export("imprivata", project_root=tmp_path)
    rows = _read_rows(output_path)

    proposal_rows = [row for row in rows[2:] if row[4] == "Formal"]
    assert len(proposal_rows) == 1
    assert proposal_rows[0][9] == "1"


def test_all_cash_fallback_to_explicit_terms_when_no_override(tmp_path: Path) -> None:
    output_path = _load_fixture(tmp_path)

    run_db_export("imprivata", project_root=tmp_path)
    rows = _read_rows(output_path)

    proposal_rows = [row for row in rows[2:] if row[4] == "Formal"]
    assert len(proposal_rows) == 1
    assert proposal_rows[0][9] == "1"


def test_all_cash_na_when_no_override_and_no_explicit_terms(tmp_path: Path) -> None:
    output_path = _load_fixture(
        tmp_path,
        events=_events_with_untyped_cash_proposal(),
    )

    run_db_export("imprivata", project_root=tmp_path)
    rows = _read_rows(output_path)

    proposal_rows = [row for row in rows[2:] if row[4] == "Formal"]
    assert len(proposal_rows) == 1
    assert proposal_rows[0][9] == "NA"


def test_drop_target_label_in_note_column(tmp_path: Path) -> None:
    deterministic_enrichment = _default_deterministic_enrichment()
    deterministic_enrichment["dropout_classifications"] = {
        "evt_003": {
            "label": "DropTarget",
            "basis": "Bidder not invited to round.",
            "source_text": "no longer participating",
        }
    }
    output_path = _load_fixture(
        tmp_path,
        deterministic_enrichment=deterministic_enrichment,
    )

    run_db_export("imprivata", project_root=tmp_path)
    rows = _read_rows(output_path)

    drop_rows = [row for row in rows[2:] if row[1] == "DropTarget"]
    assert len(drop_rows) == 1


def test_drop_without_enrichment_shows_generic_drop(tmp_path: Path) -> None:
    output_path = _load_fixture(tmp_path)

    run_db_export("imprivata", project_root=tmp_path)
    rows = _read_rows(output_path)

    drop_rows = [row for row in rows[2:] if row[1] == "Drop"]
    assert len(drop_rows) == 1


def test_db_export_cli_subcommand_dispatches(tmp_path: Path) -> None:
    output_path = _load_fixture(tmp_path)

    exit_code = cli.main(["db-export", "--deal", "imprivata", "--project-root", str(tmp_path)])

    rows = _read_rows(output_path)
    assert exit_code == 0
    assert rows[0][0] == "TargetName"
