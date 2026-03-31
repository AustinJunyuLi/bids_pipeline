from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline import cli
from skill_pipeline.canonicalize import run_canonicalize_v2
from skill_pipeline.compose_prompts import run_compose_prompts
from skill_pipeline.derive import run_derive
from skill_pipeline.gates_v2 import run_gates_v2
from skill_pipeline.check_v2 import run_check_v2
from skill_pipeline.coverage_v2 import run_coverage_v2
from skill_pipeline.migrate_extract_v1_to_v2 import run_migrate_extract_v1_to_v2
from skill_pipeline.paths import build_skill_paths
from scripts.validate_prompt_packets import validate_manifest
from tests._v2_validation_fixtures import write_v2_validation_reports
from tests.test_skill_db_load import _span, _write_canonical_fixture
from tests.test_skill_pipeline import _write_shared_inputs


def test_compose_prompts_v2_writes_prompt_v2_manifest_and_packets(tmp_path: Path) -> None:
    _write_shared_inputs(tmp_path)

    manifest = run_compose_prompts(
        "imprivata",
        project_root=tmp_path,
        contract="v2",
        mode="observations",
    )
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    assert paths.prompt_v2_manifest_path.exists()
    assert manifest.packets
    assert all(packet.packet_family == "observations_v2" for packet in manifest.packets)
    assert not paths.prompt_manifest_path.exists()
    assert validate_manifest(
        "imprivata",
        project_root=tmp_path,
        contract="v2",
        expect_sections=True,
    ) == []

    rendered_text = Path(manifest.packets[0].rendered_path).read_text(encoding="utf-8")
    assert "<actor_roster>" not in rendered_text
    assert "quotes, parties, cohorts, observations, exclusions, coverage" in rendered_text


def test_compose_prompts_v2_cli_parses_contract_and_mode() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(
        ["compose-prompts", "--deal", "stec", "--contract", "v2", "--mode", "observations"]
    )
    assert args.command == "compose-prompts"
    assert args.contract == "v2"
    assert args.mode == "observations"


def test_migrate_extract_v1_to_v2_cli_parses() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["migrate-extract-v1-to-v2", "--deal", "stec"])
    assert args.command == "migrate-extract-v1-to-v2"
    assert args.deal == "stec"


def _resolved_date(day: str) -> dict:
    return {
        "raw_text": day,
        "normalized_start": day,
        "normalized_end": day,
        "sort_date": day,
        "precision": "exact_day",
        "anchor_event_id": None,
        "anchor_span_id": None,
        "resolution_note": None,
        "is_inferred": False,
    }


def _phase16_fixture(tmp_path: Path) -> None:
    actors = [
        {
            "actor_id": "target_board_company",
            "display_name": "Company board",
            "canonical_name": "COMPANY BOARD",
            "aliases": [],
            "role": "target_board",
            "advisor_kind": None,
            "advised_actor_id": None,
            "bidder_kind": None,
            "listing_status": None,
            "geography": None,
            "is_grouped": False,
            "group_size": None,
            "group_label": None,
            "evidence_span_ids": ["span_actor_board"],
            "notes": [],
        },
        {
            "actor_id": "bidder_a",
            "display_name": "Bidder A",
            "canonical_name": "BIDDER A",
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
            "evidence_span_ids": ["span_actor_bidder_a"],
            "notes": [],
        },
        {
            "actor_id": "bidder_group_two",
            "display_name": "Two unnamed bidders",
            "canonical_name": "TWO UNNAMED BIDDERS",
            "aliases": [],
            "role": "bidder",
            "advisor_kind": None,
            "advised_actor_id": None,
            "bidder_kind": "financial",
            "listing_status": None,
            "geography": None,
            "is_grouped": True,
            "group_size": 2,
            "group_label": "two unnamed bidders",
            "evidence_span_ids": ["span_actor_group"],
            "notes": [],
        },
    ]
    events = [
        {
            "event_id": "evt_001",
            "event_type": "bidder_interest",
            "date": _resolved_date("2026-03-01"),
            "actor_ids": ["bidder_a"],
            "summary": "Bidder A expressed interest in a potential transaction.",
            "evidence_span_ids": ["span_evt_001"],
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
            "date": _resolved_date("2026-03-02"),
            "actor_ids": ["bidder_a"],
            "summary": "Bidder A entered into a confidentiality agreement.",
            "evidence_span_ids": ["span_evt_002"],
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
            "event_type": "final_round_ext_ann",
            "date": _resolved_date("2026-03-03"),
            "actor_ids": ["target_board_company"],
            "summary": "The Company requested a revised best and final offer from Bidder A by March 4, 2026.",
            "evidence_span_ids": ["span_evt_003"],
            "terms": None,
            "formality_signals": None,
            "whole_company_scope": None,
            "drop_reason_text": None,
            "round_scope": None,
            "invited_actor_ids": ["bidder_a"],
            "deadline_date": _resolved_date("2026-03-04"),
            "executed_with_actor_id": None,
            "boundary_note": None,
            "nda_signed": None,
            "notes": [],
        },
        {
            "event_id": "evt_004",
            "event_type": "final_round_ext",
            "date": _resolved_date("2026-03-04"),
            "actor_ids": [],
            "summary": "Revised best and final offers were due on March 4, 2026.",
            "evidence_span_ids": ["span_evt_004"],
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
            "event_id": "evt_005",
            "event_type": "proposal",
            "date": _resolved_date("2026-03-04"),
            "actor_ids": ["bidder_a"],
            "summary": "Bidder A submitted a written indication of interest at $21.50 per share.",
            "evidence_span_ids": ["span_evt_005"],
            "terms": {
                "per_share": 21.5,
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
        {
            "event_id": "evt_006",
            "event_type": "drop",
            "date": _resolved_date("2026-03-04"),
            "actor_ids": ["bidder_group_two"],
            "summary": "Two unnamed bidders were interested only in limited, select assets of the Company.",
            "evidence_span_ids": ["span_evt_006"],
            "terms": None,
            "formality_signals": None,
            "whole_company_scope": None,
            "drop_reason_text": "The bidders were interested only in limited, select assets.",
            "round_scope": None,
            "invited_actor_ids": [],
            "deadline_date": None,
            "executed_with_actor_id": None,
            "boundary_note": None,
            "nda_signed": None,
            "notes": [],
        },
        {
            "event_id": "evt_007",
            "event_type": "executed",
            "date": _resolved_date("2026-03-05"),
            "actor_ids": ["target_board_company"],
            "summary": "The merger agreement with Bidder A was executed.",
            "evidence_span_ids": ["span_evt_007"],
            "terms": None,
            "formality_signals": None,
            "whole_company_scope": None,
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
    spans = [
        _span("span_actor_board", "B001", 1, "Company board"),
        _span("span_actor_bidder_a", "B002", 2, "Bidder A"),
        _span("span_actor_group", "B003", 3, "Two unnamed bidders"),
        _span("span_evt_001", "B004", 4, "Bidder A expressed interest in a potential transaction."),
        _span("span_evt_002", "B005", 5, "Bidder A entered into a confidentiality agreement."),
        _span(
            "span_evt_003",
            "B006",
            6,
            "The Company requested a revised best and final offer from Bidder A by March 4, 2026.",
        ),
        _span("span_evt_004", "B007", 7, "Revised best and final offers were due on March 4, 2026."),
        _span(
            "span_evt_005",
            "B008",
            8,
            "Bidder A submitted a written indication of interest at $21.50 per share.",
        ),
        _span(
            "span_evt_006",
            "B009",
            9,
            "Two unnamed bidders were interested only in limited, select assets of the Company.",
        ),
        _span("span_evt_007", "B010", 10, "The merger agreement with Bidder A was executed."),
    ]
    _write_canonical_fixture(
        tmp_path,
        slug="imprivata",
        actors=actors,
        events=events,
        spans=spans,
    )


def test_migrate_extract_v1_to_v2_supports_bidder_interest_extension_and_group_drop(
    tmp_path: Path,
) -> None:
    _phase16_fixture(tmp_path)

    assert run_migrate_extract_v1_to_v2("imprivata", project_root=tmp_path) == 0
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    raw_payload = json.loads(paths.observations_raw_path.read_text(encoding="utf-8"))

    assert raw_payload["cohorts"][0]["cohort_id"] == "bidder_group_two"
    assert raw_payload["cohorts"][0]["unknown_member_count"] == 2
    assert any(
        observation["obs_type"] == "status" and observation["status_kind"] == "expressed_interest"
        for observation in raw_payload["observations"]
    )
    assert any(
        observation["obs_type"] == "solicitation"
        and observation["other_detail"] == "extension round"
        for observation in raw_payload["observations"]
    )

    assert run_canonicalize_v2("imprivata", project_root=tmp_path) == 0
    assert run_check_v2("imprivata", project_root=tmp_path) == 0
    assert run_gates_v2("imprivata", project_root=tmp_path) == 0
    write_v2_validation_reports(tmp_path, slug="imprivata")
    assert run_derive("imprivata", project_root=tmp_path) == 0

    derivations = json.loads(paths.derivations_path.read_text(encoding="utf-8"))
    analyst_types = [row["analyst_event_type"] for row in derivations["analyst_rows"]]
    extension_rows = [
        row for row in derivations["analyst_rows"] if row["analyst_event_type"] == "final_round_ext"
    ]
    drop_rows = [
        row
        for row in derivations["analyst_rows"]
        if row["analyst_event_type"] == "drop" and row["subject_ref"] == "bidder_group_two"
    ]

    assert "bidder_interest" in analyst_types
    assert "final_round_ext_ann" in analyst_types
    assert len(extension_rows) == 1
    assert drop_rows[0]["row_count"] == 2


def test_coverage_v2_handles_bidder_interest_cues_without_raising(tmp_path: Path) -> None:
    _phase16_fixture(tmp_path)

    run_migrate_extract_v1_to_v2("imprivata", project_root=tmp_path)
    run_canonicalize_v2("imprivata", project_root=tmp_path)

    exit_code = run_coverage_v2("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    assert exit_code in {0, 1}
    assert paths.coverage_v2_summary_path.exists()
