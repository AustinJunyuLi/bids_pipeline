"""Tests for canonical provenance and date normalization."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from skill_pipeline.canonicalize import run_canonicalize
from skill_pipeline.normalize.dates import parse_resolved_date
from skill_pipeline.paths import build_skill_paths
from skill_pipeline.pipeline_models.common import DatePrecision, QuoteMatchType
from skill_pipeline.provenance import resolve_text_span


def test_parse_resolved_date_handles_exact_quarter_and_relative_forms() -> None:
    exact = parse_resolved_date("July 5, 2016")
    assert exact.normalized_start == date(2016, 7, 5)
    assert exact.normalized_end == date(2016, 7, 5)
    assert exact.sort_date == date(2016, 7, 5)
    assert exact.precision == DatePrecision.EXACT_DAY

    quarter = parse_resolved_date("Q3 2016")
    assert quarter.normalized_start == date(2016, 7, 1)
    assert quarter.normalized_end == date(2016, 9, 30)
    assert quarter.sort_date == date(2016, 7, 1)
    assert quarter.precision == DatePrecision.QUARTER

    relative = parse_resolved_date(
        "two days later",
        anchor_date=exact,
        anchor_event_id="evt_001",
    )
    assert relative.normalized_start == date(2016, 7, 7)
    assert relative.normalized_end == date(2016, 7, 7)
    assert relative.sort_date == date(2016, 7, 7)
    assert relative.precision == DatePrecision.RELATIVE
    assert relative.anchor_event_id == "evt_001"
    assert relative.is_inferred is True


def test_resolve_text_span_records_line_and_char_offsets() -> None:
    raw_lines = ["Party A submitted an indication of interest."]

    span = resolve_text_span(
        raw_lines,
        start_line=1,
        end_line=1,
        block_ids=["B001"],
        evidence_ids=["DOC001:E0001"],
        anchor_text="submitted an indication of interest",
        document_id="DOC001",
        accession_number="DOC001",
        filing_type="DEFM14A",
        span_id="span_0001",
    )

    assert span.match_type == QuoteMatchType.EXACT
    assert span.start_line == 1
    assert span.end_line == 1
    assert span.start_char == 8
    assert span.end_char == 43
    assert span.block_ids == ["B001"]
    assert span.evidence_ids == ["DOC001:E0001"]


def test_canonicalize_upgrades_legacy_extract_to_span_backed_schema(tmp_path: Path) -> None:
    slug = "imprivata"
    data_dir = tmp_path / "data"
    source_dir = data_dir / "deals" / slug / "source"
    extract_dir = data_dir / "skill" / slug / "extract"
    raw_dir = tmp_path / "raw" / slug
    filings_dir = raw_dir / "filings"

    source_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)
    filings_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n"
        ),
        encoding="utf-8",
    )

    line_text = "Party A submitted an indication of interest."
    chronology_blocks = [
        {
            "block_id": "B001",
            "document_id": "DOC001",
            "ordinal": 1,
            "start_line": 1,
            "end_line": 1,
            "raw_text": line_text,
            "clean_text": line_text,
            "is_heading": False,
            "page_break_before": False,
            "page_break_after": False,
            "date_mentions": [],
            "entity_mentions": [],
            "evidence_density": 0,
            "temporal_phase": "other",
        }
    ]
    (source_dir / "chronology_blocks.jsonl").write_text(
        "\n".join(json.dumps(block) for block in chronology_blocks) + "\n",
        encoding="utf-8",
    )
    evidence_items = [
        {
            "evidence_id": "DOC001:E0001",
            "document_id": "DOC001",
            "accession_number": "DOC001",
            "filing_type": "DEFM14A",
            "start_line": 1,
            "end_line": 1,
            "raw_text": line_text,
            "evidence_type": "dated_action",
            "confidence": "high",
            "matched_terms": ["submitted"],
            "date_text": "July 5, 2016",
            "actor_hint": "Party A",
            "value_hint": None,
            "note": None,
        }
    ]
    (source_dir / "evidence_items.jsonl").write_text(
        "\n".join(json.dumps(item) for item in evidence_items) + "\n",
        encoding="utf-8",
    )

    (raw_dir / "document_registry.json").write_text(
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
    (filings_dir / "DOC001.txt").write_text(line_text + "\n", encoding="utf-8")

    actors_payload = {
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
                    {"block_id": "B001", "evidence_id": None, "anchor_text": "Party A"}
                ],
                "notes": [],
            }
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }
    events_payload = {
        "events": [
            {
                "event_id": "evt_001",
                "event_type": "proposal",
                "date": {"raw_text": "July 5, 2016", "normalized_hint": "2016-07-05"},
                "actor_ids": ["party_a"],
                "summary": "Party A submitted an indication of interest.",
                "evidence_refs": [
                    {
                        "block_id": "B001",
                        "evidence_id": "DOC001:E0001",
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
                "formality_signals": {
                    "contains_range": False,
                    "mentions_indication_of_interest": True,
                    "mentions_preliminary": False,
                    "mentions_non_binding": False,
                    "mentions_binding_offer": False,
                    "includes_draft_merger_agreement": False,
                    "includes_marked_up_agreement": False,
                    "requested_binding_offer_via_process_letter": False,
                    "after_final_round_announcement": False,
                    "after_final_round_deadline": False,
                    "is_subject_to_financing": None,
                },
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
    (extract_dir / "actors_raw.json").write_text(json.dumps(actors_payload), encoding="utf-8")
    (extract_dir / "events_raw.json").write_text(json.dumps(events_payload), encoding="utf-8")

    run_canonicalize(slug, project_root=tmp_path)

    paths = build_skill_paths(slug, project_root=tmp_path)
    actors = json.loads(paths.actors_raw_path.read_text(encoding="utf-8"))
    events = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))
    spans = json.loads(paths.spans_path.read_text(encoding="utf-8"))

    assert actors["actors"][0]["evidence_span_ids"] == ["span_0001"]
    assert "evidence_refs" not in actors["actors"][0]
    assert events["events"][0]["evidence_span_ids"] == ["span_0002"]
    assert "evidence_refs" not in events["events"][0]
    assert events["events"][0]["date"]["normalized_start"] == "2016-07-05"
    assert events["events"][0]["date"]["normalized_end"] == "2016-07-05"
    assert events["events"][0]["date"]["sort_date"] == "2016-07-05"
    assert events["events"][0]["date"]["precision"] == "exact_day"
    assert spans["spans"][0]["start_char"] == 0
    assert spans["spans"][1]["start_char"] == 8
