from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from openpyxl import Workbook

from skill_pipeline import cli


def _write_reconcile_fixture(
    tmp_path: Path,
    *,
    slug: str = "imprivata",
    export_rows: list[dict[str, str]] | None = None,
    alex_rows: list[dict[str, object]] | None = None,
) -> None:
    data_dir = tmp_path / "data"
    skill_root = data_dir / "skill" / slug
    export_dir = skill_root / "export"
    extract_dir = skill_root / "extract"
    enrich_dir = skill_root / "enrich"
    source_dir = data_dir / "deals" / slug / "source"
    raw_dir = tmp_path / "raw" / slug
    filings_dir = raw_dir / "filings"
    example_dir = tmp_path / "example"

    export_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)
    enrich_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)
    filings_dir.mkdir(parents=True, exist_ok=True)
    example_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n"
        ),
        encoding="utf-8",
    )
    (extract_dir / "actors_raw.json").write_text(
        json.dumps(
            {
                "actors": [
                    {
                        "actor_id": "party_a",
                        "display_name": "Party A",
                        "canonical_name": "PARTY A",
                        "aliases": [],
                        "role": "bidder",
                        "advisor_kind": None,
                        "advised_actor_id": None,
                        "bidder_kind": "financial",
                        "listing_status": "private",
                        "geography": "domestic",
                        "is_grouped": False,
                        "group_size": None,
                        "group_label": None,
                        "evidence_refs": [
                            {
                                "block_id": "B001",
                                "evidence_id": None,
                                "anchor_text": "Party A",
                            }
                        ],
                        "notes": [],
                    }
                ],
                "count_assertions": [],
                "unresolved_mentions": [],
            }
        ),
        encoding="utf-8",
    )
    (extract_dir / "events_raw.json").write_text(
        json.dumps(
            {
                "events": [
                    {
                        "event_id": "evt_001",
                        "event_type": "proposal",
                        "date": {
                            "raw_text": "July 5, 2016",
                            "normalized_hint": "2016-07-05",
                        },
                        "actor_ids": ["party_a"],
                        "summary": "Party A submitted an indication of interest.",
                        "evidence_refs": [
                            {
                                "block_id": "B001",
                                "evidence_id": None,
                                "anchor_text": "submitted an indication of interest",
                            }
                        ],
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
                    }
                ],
                "exclusions": [],
                "coverage_notes": [],
            }
        ),
        encoding="utf-8",
    )
    (extract_dir / "spans.json").write_text(
        json.dumps(
            {
                "spans": [
                    {
                        "span_id": "span_0001",
                        "document_id": "DOC001",
                        "accession_number": "DOC001",
                        "filing_type": "DEFM14A",
                        "start_line": 1,
                        "end_line": 1,
                        "start_char": 1,
                        "end_char": 25,
                        "block_ids": ["B001"],
                        "evidence_ids": [],
                        "anchor_text": "submitted an indication of interest",
                        "quote_text": "Party A submitted an indication of interest at $25.00 per share.",
                        "quote_text_normalized": "party a submitted an indication of interest at $25.00 per share.",
                        "match_type": "exact",
                        "resolution_note": None,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (enrich_dir / "enrichment.json").write_text(
        json.dumps(
            {
                "dropout_classifications": {},
                "bid_classifications": {
                    "evt_001": {
                        "label": "Informal",
                        "rule_applied": 1,
                        "basis": "Observable informal signal.",
                    }
                },
                "rounds": [],
                "cycles": [],
                "formal_boundary": {},
                "initiation_judgment": {
                    "type": "bidder_driven",
                    "basis": "Party A approached the Company.",
                    "source_text": "Party A contacted the Company.",
                    "confidence": "high",
                },
                "advisory_verification": {},
                "count_reconciliation": [],
                "review_flags": [],
            }
        ),
        encoding="utf-8",
    )
    (source_dir / "chronology_blocks.jsonl").write_text(
        json.dumps(
            {
                "block_id": "B001",
                "document_id": "DOC001",
                "ordinal": 1,
                "start_line": 1,
                "end_line": 1,
                "raw_text": "Party A submitted an indication of interest at $25.00 per share.",
                "clean_text": "Party A submitted an indication of interest at $25.00 per share.",
                "is_heading": False,
                "page_break_before": False,
                "page_break_after": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (raw_dir / "document_registry.json").write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "document_id": "DOC001",
                        "txt_path": f"raw/{slug}/filings/DOC001.txt",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (filings_dir / "DOC001.txt").write_text(
        "Party A submitted an indication of interest at $25.00 per share.\n",
        encoding="utf-8",
    )

    if export_rows is None:
        export_rows = [
            {
                "bidderID": "1",
                "note": "NA",
                "bidder": "Party A",
                "type": "F",
                "bid_type": "Informal",
                "val": "25",
                "range": "NA",
                "date_r": "07/05/2016",
                "date_p": "07/05/2016",
                "cash": "1",
                "c1": "",
                "c2": "",
                "c3": "",
                "review_flags": "",
            }
        ]
    lines = [
        "TargetName,Events,Acquirer,DateAnnounced,URL",
        "IMPRIVATA INC,1,THOMA BRAVO LLC,07/13/2016,https://example.com",
        "",
        "bidderID,note,bidder,type,bid_type,val,range,date_r,date_p,cash,c1,c2,c3,review_flags",
    ]
    for row in export_rows:
        lines.append(
            ",".join(
                row[column]
                for column in [
                    "bidderID",
                    "note",
                    "bidder",
                    "type",
                    "bid_type",
                    "val",
                    "range",
                    "date_r",
                    "date_p",
                    "cash",
                    "c1",
                    "c2",
                    "c3",
                    "review_flags",
                ]
            )
        )
    (export_dir / "deal_events.csv").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    if alex_rows is None:
        alex_rows = [
            {
                "TargetName": "Imprivata, Inc.",
                "BidderID": 1,
                "BidderName": "Party A",
                "bid_note": "NA",
                "bid_date_rough": datetime(2016, 7, 5),
                "bid_value": 25.0,
                "bid_value_pershare": 25.0,
                "bid_value_lower": None,
                "bid_value_upper": None,
                "bid_type": "Informal",
                "bidder_type_note": "F",
                "all_cash": 1,
            }
        ]
    workbook = Workbook()
    ws = workbook.active
    ws.title = "deal_details"
    headers = list(alex_rows[0].keys())
    ws.append(headers)
    for row in alex_rows:
        ws.append([row.get(header) for header in headers])
    workbook.save(example_dir / "deal_details_Alex_2026.xlsx")


def test_skill_pipeline_cli_still_has_no_reconcile_subcommand() -> None:
    parser = cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["reconcile", "--deal", "imprivata"])


def test_standalone_reconcile_writes_report_for_exact_match(tmp_path: Path) -> None:
    from scripts.reconcile_alex import main

    _write_reconcile_fixture(tmp_path)

    result = main(["--deal", "imprivata", "--project-root", str(tmp_path)])

    report_path = (
        tmp_path
        / "data"
        / "skill"
        / "imprivata"
        / "reconcile"
        / "reconciliation_report.json"
    )
    alex_rows_path = (
        tmp_path / "data" / "skill" / "imprivata" / "reconcile" / "alex_rows.json"
    )
    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert result == 0
    assert alex_rows_path.exists()
    assert payload["matched_count"] == 1
    assert payload["pipeline_only_count"] == 0
    assert payload["alex_only_count"] == 0
    assert payload["summary"]["status"] == "pass"


def test_standalone_reconcile_normalizes_dropbelowm_against_alex_dropm(
    tmp_path: Path,
) -> None:
    from scripts.reconcile_alex import main

    _write_reconcile_fixture(
        tmp_path,
        export_rows=[
            {
                "bidderID": "2",
                "note": "DropBelowM",
                "bidder": "Party A",
                "type": "F",
                "bid_type": "NA",
                "val": "NA",
                "range": "NA",
                "date_r": "07/10/2016",
                "date_p": "07/10/2016",
                "cash": "NA",
                "c1": "",
                "c2": "",
                "c3": "",
                "review_flags": "",
            }
        ],
        alex_rows=[
            {
                "TargetName": "Imprivata, Inc.",
                "BidderID": 2,
                "BidderName": "Party A",
                "bid_note": "DropM",
                "bid_date_rough": datetime(2016, 7, 10),
                "bid_value": None,
                "bid_value_pershare": None,
                "bid_value_lower": None,
                "bid_value_upper": None,
                "bid_type": None,
                "bidder_type_note": "F",
                "all_cash": None,
            }
        ],
    )

    result = main(["--deal", "imprivata", "--project-root", str(tmp_path)])
    report_path = (
        tmp_path
        / "data"
        / "skill"
        / "imprivata"
        / "reconcile"
        / "reconciliation_report.json"
    )
    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert result == 0
    assert payload["matched_count"] == 1
    assert payload["field_mismatches"] == []


def test_standalone_reconcile_requires_post_export_artifacts(tmp_path: Path) -> None:
    from scripts.reconcile_alex import main

    _write_reconcile_fixture(tmp_path)
    export_path = (
        tmp_path / "data" / "skill" / "imprivata" / "export" / "deal_events.csv"
    )
    export_path.unlink()

    with pytest.raises(FileNotFoundError, match="deal_events.csv"):
        main(["--deal", "imprivata", "--project-root", str(tmp_path)])
