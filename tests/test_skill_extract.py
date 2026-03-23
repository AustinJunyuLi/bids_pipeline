from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from skill_pipeline import cli
from skill_pipeline.schemas.runtime import (
    RawSkillActorsArtifact,
    RawSkillEventsArtifact,
)


def _write_extract_fixture(tmp_path: Path, *, slug: str = "imprivata") -> None:
    data_dir = tmp_path / "data"
    source_dir = data_dir / "deals" / slug / "source"
    source_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n"
        ),
        encoding="utf-8",
    )
    (source_dir / "chronology_blocks.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "block_id": "B001",
                        "document_id": "DOC001",
                        "ordinal": 1,
                        "start_line": 1,
                        "end_line": 1,
                        "raw_text": "On July 1, 2016, Party A contacted the Company.",
                        "clean_text": "On July 1, 2016, Party A contacted the Company.",
                        "is_heading": False,
                    }
                ),
                json.dumps(
                    {
                        "block_id": "B002",
                        "document_id": "DOC001",
                        "ordinal": 2,
                        "start_line": 2,
                        "end_line": 2,
                        "raw_text": "On July 5, 2016, Party A submitted an indication of interest.",
                        "clean_text": "On July 5, 2016, Party A submitted an indication of interest.",
                        "is_heading": False,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (source_dir / "evidence_items.jsonl").write_text(
        json.dumps(
            {
                "evidence_id": "DOC001:E0001",
                "document_id": "DOC001",
                "accession_number": "DOC001",
                "filing_type": "DEFM14A",
                "start_line": 2,
                "end_line": 2,
                "raw_text": "Party A submitted an indication of interest.",
                "evidence_type": "dated_action",
                "confidence": "high",
                "matched_terms": ["submitted"],
                "date_text": "July 5, 2016",
                "actor_hint": "Party A",
                "value_hint": None,
                "note": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _actors_output() -> RawSkillActorsArtifact:
    return RawSkillActorsArtifact.model_validate(
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
                            "anchor_text": "Party A contacted the Company",
                        }
                    ],
                    "notes": [],
                }
            ],
            "count_assertions": [],
            "unresolved_mentions": [],
        }
    )


def _events_output() -> RawSkillEventsArtifact:
    return RawSkillEventsArtifact.model_validate(
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
                            "block_id": "B002",
                            "evidence_id": "DOC001:E0001",
                            "anchor_text": "submitted an indication of interest",
                        }
                    ],
                    "terms": {
                        "per_share": "25.00",
                        "range_low": None,
                        "range_high": None,
                        "enterprise_value": None,
                        "consideration_type": "cash",
                    },
                    "formality_signals": {
                        "contains_range": False,
                        "mentions_indication_of_interest": True,
                        "mentions_preliminary": False,
                        "mentions_non_binding": True,
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
            "coverage_notes": [
                "proposal: extracted (evt_001)",
                "nda: NOT FOUND -- no signed confidentiality agreement in the chronology",
            ],
        }
    )


def test_skill_cli_supports_extract_subcommand() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["extract", "--deal", "imprivata"])

    assert args.command == "extract"
    assert args.deal == "imprivata"


def test_run_extract_writes_raw_artifacts(tmp_path: Path) -> None:
    from skill_pipeline.stages.extract import run_extract

    _write_extract_fixture(tmp_path)

    with patch(
        "skill_pipeline.stages.extract.invoke_structured",
        side_effect=[_actors_output(), _events_output()],
    ):
        result = run_extract("imprivata", project_root=tmp_path)

    assert result == 0
    extract_dir = tmp_path / "data" / "skill" / "imprivata" / "extract"
    assert (extract_dir / "actors_raw.json").exists()
    assert (extract_dir / "events_raw.json").exists()


def test_run_extract_event_prompt_includes_actor_roster(tmp_path: Path) -> None:
    from skill_pipeline.stages.extract import run_extract

    _write_extract_fixture(tmp_path)

    with patch(
        "skill_pipeline.stages.extract.invoke_structured",
        side_effect=[_actors_output(), _events_output()],
    ) as mock_invoke:
        run_extract("imprivata", project_root=tmp_path)

    event_call = mock_invoke.call_args_list[1].kwargs
    assert "party_a" in event_call["user_message"]
    assert "Party A" in event_call["user_message"]


def test_run_extract_preserves_coverage_notes_from_events_output(
    tmp_path: Path,
) -> None:
    from skill_pipeline.stages.extract import run_extract

    _write_extract_fixture(tmp_path)

    with patch(
        "skill_pipeline.stages.extract.invoke_structured",
        side_effect=[_actors_output(), _events_output()],
    ):
        run_extract("imprivata", project_root=tmp_path)

    events_path = (
        tmp_path / "data" / "skill" / "imprivata" / "extract" / "events_raw.json"
    )
    payload = json.loads(events_path.read_text(encoding="utf-8"))
    assert payload["coverage_notes"] == [
        "proposal: extracted (evt_001)",
        "nda: NOT FOUND -- no signed confidentiality agreement in the chronology",
    ]


def test_run_extract_moves_partial_company_bids_to_exclusions(tmp_path: Path) -> None:
    from skill_pipeline.stages.extract import run_extract

    _write_extract_fixture(tmp_path)
    partial_output = RawSkillEventsArtifact.model_validate(
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
                    "summary": "Party A only wanted one division.",
                    "evidence_refs": [
                        {
                            "block_id": "B002",
                            "evidence_id": None,
                            "anchor_text": "only wanted one division",
                        }
                    ],
                    "terms": {
                        "per_share": "25.00",
                        "range_low": None,
                        "range_high": None,
                        "enterprise_value": None,
                        "consideration_type": "cash",
                    },
                    "formality_signals": {
                        "contains_range": False,
                        "mentions_indication_of_interest": True,
                        "mentions_preliminary": False,
                        "mentions_non_binding": True,
                        "mentions_binding_offer": False,
                        "includes_draft_merger_agreement": False,
                        "includes_marked_up_agreement": False,
                        "requested_binding_offer_via_process_letter": False,
                        "after_final_round_announcement": False,
                        "after_final_round_deadline": False,
                        "is_subject_to_financing": None,
                    },
                    "whole_company_scope": False,
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
    )

    with patch(
        "skill_pipeline.stages.extract.invoke_structured",
        side_effect=[_actors_output(), partial_output],
    ):
        run_extract("imprivata", project_root=tmp_path)

    events_path = (
        tmp_path / "data" / "skill" / "imprivata" / "extract" / "events_raw.json"
    )
    payload = json.loads(events_path.read_text(encoding="utf-8"))
    assert payload["events"] == []
    assert payload["exclusions"][0]["category"] == "partial_company_bid"


def test_run_extract_moves_unsigned_nda_to_exclusions(tmp_path: Path) -> None:
    from skill_pipeline.stages.extract import run_extract

    _write_extract_fixture(tmp_path)
    unsigned_nda_output = RawSkillEventsArtifact.model_validate(
        {
            "events": [
                {
                    "event_id": "evt_001",
                    "event_type": "nda",
                    "date": {
                        "raw_text": "July 5, 2016",
                        "normalized_hint": "2016-07-05",
                    },
                    "actor_ids": ["party_a"],
                    "summary": "The Company sent an NDA but it was never signed.",
                    "evidence_refs": [
                        {
                            "block_id": "B002",
                            "evidence_id": None,
                            "anchor_text": "never signed",
                        }
                    ],
                    "terms": None,
                    "formality_signals": None,
                    "whole_company_scope": None,
                    "drop_reason_text": None,
                    "round_scope": None,
                    "invited_actor_ids": [],
                    "deadline_date": None,
                    "executed_with_actor_id": None,
                    "boundary_note": None,
                    "nda_signed": False,
                    "notes": [],
                }
            ],
            "exclusions": [],
            "coverage_notes": [],
        }
    )

    with patch(
        "skill_pipeline.stages.extract.invoke_structured",
        side_effect=[_actors_output(), unsigned_nda_output],
    ):
        run_extract("imprivata", project_root=tmp_path)

    events_path = (
        tmp_path / "data" / "skill" / "imprivata" / "extract" / "events_raw.json"
    )
    payload = json.loads(events_path.read_text(encoding="utf-8"))
    assert payload["events"] == []
    assert payload["exclusions"][0]["category"] == "unsigned_nda"


def test_run_extract_raises_on_empty_events(tmp_path: Path) -> None:
    from skill_pipeline.stages.extract import run_extract

    _write_extract_fixture(tmp_path)

    empty_events = RawSkillEventsArtifact.model_validate(
        {"events": [], "exclusions": [], "coverage_notes": []}
    )

    with (
        patch(
            "skill_pipeline.stages.extract.invoke_structured",
            side_effect=[_actors_output(), empty_events],
        ),
        pytest.raises(ValueError, match="zero events"),
    ):
        run_extract("imprivata", project_root=tmp_path)
