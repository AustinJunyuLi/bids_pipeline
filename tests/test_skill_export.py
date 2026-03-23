from __future__ import annotations

import csv
import json
from pathlib import Path

from skill_pipeline import cli


def _write_export_fixture(tmp_path: Path, *, slug: str = "imprivata") -> Path:
    data_dir = tmp_path / "data"
    skill_root = data_dir / "skill" / slug
    materialize_dir = skill_root / "materialize"
    enrich_dir = skill_root / "enrich"
    materialize_dir.mkdir(parents=True, exist_ok=True)
    enrich_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n"
        ),
        encoding="utf-8",
    )

    actors = {
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
                "evidence_span_ids": [],
                "notes": [],
            },
            {
                "actor_id": "party_b",
                "display_name": "Party B",
                "canonical_name": "PARTY B",
                "aliases": [],
                "role": "bidder",
                "advisor_kind": None,
                "advised_actor_id": None,
                "bidder_kind": "strategic",
                "listing_status": "public",
                "geography": "non_us",
                "is_grouped": False,
                "group_size": None,
                "group_label": None,
                "evidence_span_ids": [],
                "notes": [],
            },
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }
    events = {
        "events": [
            {
                "event_id": "evt_001",
                "event_type": "bidder_interest",
                "date": {
                    "raw_text": "July 1, 2016",
                    "normalized_start": "2016-07-01",
                    "normalized_end": "2016-07-01",
                    "sort_date": "2016-07-01",
                    "precision": "exact_day",
                    "anchor_event_id": None,
                    "anchor_span_id": None,
                    "resolution_note": None,
                    "is_inferred": False,
                },
                "actor_ids": ["party_a"],
                "summary": "Party A contacted the Company.",
                "evidence_span_ids": [],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": None,
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
                "event_type": "nda",
                "date": {
                    "raw_text": "July 3, 2016",
                    "normalized_start": "2016-07-03",
                    "normalized_end": "2016-07-03",
                    "sort_date": "2016-07-03",
                    "precision": "exact_day",
                    "anchor_event_id": None,
                    "anchor_span_id": None,
                    "resolution_note": None,
                    "is_inferred": False,
                },
                "actor_ids": ["party_a"],
                "summary": "Party A signed an NDA.",
                "evidence_span_ids": [],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": None,
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
                "event_id": "evt_003",
                "event_type": "proposal",
                "date": {
                    "raw_text": "July 5, 2016",
                    "normalized_start": "2016-07-05",
                    "normalized_end": "2016-07-05",
                    "sort_date": "2016-07-05",
                    "precision": "exact_day",
                    "anchor_event_id": None,
                    "anchor_span_id": None,
                    "resolution_note": None,
                    "is_inferred": False,
                },
                "actor_ids": ["party_a"],
                "summary": "Party A submitted a proposal.",
                "evidence_span_ids": [],
                "terms": {
                    "per_share": "25.00",
                    "range_low": None,
                    "range_high": None,
                    "enterprise_value": None,
                    "consideration_type": "cash",
                },
                "formality_signals": {
                    "contains_range": False,
                    "mentions_indication_of_interest": False,
                    "mentions_preliminary": False,
                    "mentions_non_binding": False,
                    "mentions_binding_offer": True,
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
            },
            {
                "event_id": "evt_004",
                "event_type": "final_round_ann",
                "date": {
                    "raw_text": "July 7, 2016",
                    "normalized_start": "2016-07-07",
                    "normalized_end": "2016-07-07",
                    "sort_date": "2016-07-07",
                    "precision": "exact_day",
                    "anchor_event_id": None,
                    "anchor_span_id": None,
                    "resolution_note": None,
                    "is_inferred": False,
                },
                "actor_ids": [],
                "summary": "Board announced the final round.",
                "evidence_span_ids": [],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": None,
                "drop_reason_text": None,
                "round_scope": "formal",
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": None,
                "notes": [],
            },
            {
                "event_id": "evt_005",
                "event_type": "drop",
                "date": {
                    "raw_text": "July 7, 2016",
                    "normalized_start": "2016-07-07",
                    "normalized_end": "2016-07-07",
                    "sort_date": "2016-07-07",
                    "precision": "exact_day",
                    "anchor_event_id": None,
                    "anchor_span_id": None,
                    "resolution_note": None,
                    "is_inferred": False,
                },
                "actor_ids": ["party_a"],
                "summary": "Party A dropped out.",
                "evidence_span_ids": [],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": None,
                "drop_reason_text": "Party A withdrew after the final round was announced.",
                "round_scope": None,
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": None,
                "notes": [],
            },
            {
                "event_id": "evt_006",
                "event_type": "final_round",
                "date": {
                    "raw_text": "July 7, 2016",
                    "normalized_start": "2016-07-07",
                    "normalized_end": "2016-07-07",
                    "sort_date": "2016-07-07",
                    "precision": "exact_day",
                    "anchor_event_id": None,
                    "anchor_span_id": None,
                    "resolution_note": None,
                    "is_inferred": False,
                },
                "actor_ids": [],
                "summary": "Final round bids due.",
                "evidence_span_ids": [],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": None,
                "drop_reason_text": None,
                "round_scope": "formal",
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": None,
                "notes": [],
            },
            {
                "event_id": "evt_007",
                "event_type": "proposal",
                "date": {
                    "raw_text": "July 9, 2016",
                    "normalized_start": "2016-07-09",
                    "normalized_end": "2016-07-09",
                    "sort_date": "2016-07-09",
                    "precision": "exact_day",
                    "anchor_event_id": None,
                    "anchor_span_id": None,
                    "resolution_note": None,
                    "is_inferred": False,
                },
                "actor_ids": ["party_b"],
                "summary": "Party B submitted an enterprise-value-only proposal.",
                "evidence_span_ids": [],
                "terms": {
                    "per_share": None,
                    "range_low": None,
                    "range_high": None,
                    "enterprise_value": "1500",
                    "consideration_type": "mixed",
                },
                "formality_signals": {
                    "contains_range": False,
                    "mentions_indication_of_interest": False,
                    "mentions_preliminary": False,
                    "mentions_non_binding": False,
                    "mentions_binding_offer": True,
                    "includes_draft_merger_agreement": False,
                    "includes_marked_up_agreement": False,
                    "requested_binding_offer_via_process_letter": False,
                    "after_final_round_announcement": True,
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
            },
        ],
        "exclusions": [],
        "coverage_notes": [],
    }
    enrichment = {
        "dropout_classifications": {
            "evt_005": {
                "label": "DropTarget",
                "basis": "Target excluded Party A.",
                "source_text": "Party A withdrew after the final round was announced.",
            }
        },
        "bid_classifications": {
            "evt_003": {
                "label": "Informal",
                "rule_applied": 1,
                "basis": "Indication of interest.",
            },
            "evt_007": {
                "label": "Uncertain",
                "rule_applied": None,
                "basis": "Enterprise value only.",
            },
        },
        "rounds": [],
        "cycles": [],
        "formal_boundary": {},
        "initiation_judgment": {
            "type": "bidder_driven",
            "basis": "Party A initiated contact.",
            "source_text": "Party A contacted the Company.",
            "confidence": "high",
        },
        "advisory_verification": {},
        "count_reconciliation": [],
        "review_flags": ["dropout_needs_review:evt_005"],
    }

    (materialize_dir / "actors.json").write_text(json.dumps(actors), encoding="utf-8")
    (materialize_dir / "events.json").write_text(json.dumps(events), encoding="utf-8")
    (materialize_dir / "spans.json").write_text(
        json.dumps({"spans": []}), encoding="utf-8"
    )
    (enrich_dir / "enrichment.json").write_text(
        json.dumps(enrichment), encoding="utf-8"
    )
    return skill_root


def _read_event_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))

    header = rows[3]
    event_rows = rows[4:]
    return [dict(zip(header, row, strict=False)) for row in event_rows]


def test_skill_cli_supports_export_subcommand() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["export", "--deal", "imprivata"])

    assert args.command == "export"
    assert args.deal == "imprivata"


def test_run_export_writes_header_and_first_type_only(tmp_path: Path) -> None:
    from skill_pipeline.stages.export import run_export

    skill_root = _write_export_fixture(tmp_path)

    result = run_export("imprivata", project_root=tmp_path)

    assert result == 0
    csv_path = skill_root / "export" / "deal_events.csv"
    rows = _read_event_rows(csv_path)
    nda_row = next(row for row in rows if row["note"] == "NDA")
    proposal_row = next(
        row for row in rows if row["bidder"] == "Party A" and row["note"] == "NA"
    )
    assert nda_row["type"] == "F"
    assert proposal_row["type"] == "NA"
    assert proposal_row["bid_type"] == "Informal"
    assert proposal_row["val"] == "25"
    assert proposal_row["range"] == "25-25"
    assert proposal_row["date_r"] == "07/05/2016"
    assert proposal_row["date_p"] == "07/05/2016"
    assert proposal_row["cash"] == "1"


def test_run_export_assigns_fractional_ids_and_same_date_sort(tmp_path: Path) -> None:
    from skill_pipeline.stages.export import run_export

    skill_root = _write_export_fixture(tmp_path)

    run_export("imprivata", project_root=tmp_path)

    rows = _read_event_rows(skill_root / "export" / "deal_events.csv")
    assert rows[0]["note"] == "Bidder Interest"
    assert rows[0]["bidderID"] == "0.5"

    july_7_rows = [row for row in rows if row["date_r"] == "07/07/2016"]
    assert [row["note"] for row in july_7_rows] == [
        "Final Round Ann",
        "DropTarget",
        "Final Round",
    ]


def test_run_export_uses_dropout_label_and_filters_review_flags(tmp_path: Path) -> None:
    from skill_pipeline.stages.export import run_export

    skill_root = _write_export_fixture(tmp_path)

    run_export("imprivata", project_root=tmp_path)

    rows = _read_event_rows(skill_root / "export" / "deal_events.csv")
    drop_row = next(row for row in rows if row["note"] == "DropTarget")
    nda_row = next(row for row in rows if row["note"] == "NDA")
    assert drop_row["review_flags"] == "dropout_needs_review:evt_005"
    assert nda_row["review_flags"] == ""


def test_run_export_flags_enterprise_value_only_and_uncertain_bid_type(
    tmp_path: Path,
) -> None:
    from skill_pipeline.stages.export import run_export

    skill_root = _write_export_fixture(tmp_path)

    run_export("imprivata", project_root=tmp_path)

    rows = _read_event_rows(skill_root / "export" / "deal_events.csv")
    row = next(row for row in rows if row["bidder"] == "Party B")
    assert row["type"] == "non-US public S"
    assert row["bid_type"] == "NA"
    assert row["val"] == "NA"
    assert row["c1"] == "Enterprise value only: 1500"
    assert (
        row["review_flags"]
        == "bid_classification_uncertain:evt_007|enterprise_value_only:evt_007"
    )
