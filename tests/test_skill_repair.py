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
from skill_pipeline.core.paths import build_skill_paths


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
                            "anchor_text": "Party A",
                        }
                    ],
                    "notes": [],
                }
            ],
            "count_assertions": [],
            "unresolved_mentions": [],
        }
    )


def _events_output(summary: str = "Original summary") -> RawSkillEventsArtifact:
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
                    "summary": summary,
                    "evidence_refs": [
                        {
                            "block_id": "B001",
                            "evidence_id": None,
                            "anchor_text": "submitted a proposal",
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
    )


def _write_repair_fixture(tmp_path: Path, *, slug: str = "imprivata") -> None:
    data_dir = tmp_path / "data"
    extract_dir = data_dir / "skill" / slug / "extract"
    verify_dir = data_dir / "skill" / slug / "verify"
    coverage_dir = data_dir / "skill" / slug / "coverage"
    source_dir = data_dir / "deals" / slug / "source"

    extract_dir.mkdir(parents=True, exist_ok=True)
    verify_dir.mkdir(parents=True, exist_ok=True)
    coverage_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)

    (extract_dir / "actors_raw.json").write_text(
        _actors_output().model_dump_json(indent=2),
        encoding="utf-8",
    )
    (extract_dir / "events_raw.json").write_text(
        _events_output().model_dump_json(indent=2),
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
                "raw_text": "Party A submitted a proposal.",
                "clean_text": "Party A submitted a proposal.",
                "is_heading": False,
                "page_break_before": False,
                "page_break_after": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _write_findings(
    paths,
    *,
    verification_findings: list[dict] | None = None,
    coverage_findings: list[dict] | None = None,
    omission_findings: list[dict] | None = None,
) -> None:
    (paths.verify_dir).mkdir(parents=True, exist_ok=True)
    (paths.coverage_dir).mkdir(parents=True, exist_ok=True)
    paths.verification_findings_path.write_text(
        json.dumps({"findings": verification_findings or []}),
        encoding="utf-8",
    )
    paths.coverage_findings_path.write_text(
        json.dumps({"findings": coverage_findings or []}),
        encoding="utf-8",
    )
    paths.omission_findings_path.write_text(
        json.dumps({"findings": omission_findings or []}),
        encoding="utf-8",
    )


def test_skill_cli_supports_repair_subcommand() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["repair", "--deal", "imprivata"])

    assert args.command == "repair"
    assert args.deal == "imprivata"


def test_repair_fails_closed_on_non_repairable(tmp_path: Path) -> None:
    from skill_pipeline.stages.qa.repair import run_repair

    _write_repair_fixture(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    _write_findings(
        paths,
        verification_findings=[
            {
                "check_type": "quote_verification",
                "severity": "error",
                "repairability": "non_repairable",
                "description": "Span references missing source.",
            }
        ],
    )

    with patch("skill_pipeline.stages.qa.repair.invoke_structured") as mock_invoke:
        with pytest.raises(RuntimeError, match="non-repairable"):
            run_repair("imprivata", project_root=tmp_path)

    mock_invoke.assert_not_called()


def test_repair_patches_raw_artifacts(tmp_path: Path) -> None:
    from skill_pipeline.stages.qa.repair import RepairPatchArtifact, run_repair

    _write_repair_fixture(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    _write_findings(
        paths,
        verification_findings=[
            {
                "check_type": "structural_integrity",
                "severity": "error",
                "repairability": "repairable",
                "description": "Proposal summary needs correction.",
                "event_ids": ["evt_001"],
            }
        ],
    )

    patch_output = RepairPatchArtifact(
        actors_raw=None,
        events_raw=_events_output(summary="Patched summary"),
        repair_notes=["Updated proposal summary."],
    )

    def _clear_findings(*args, **kwargs) -> int:
        _write_findings(paths)
        return 0

    with (
        patch(
            "skill_pipeline.stages.qa.repair.invoke_structured",
            return_value=patch_output,
        ),
        patch(
            "skill_pipeline.stages.qa.repair.run_materialize",
            return_value=0,
        ),
        patch(
            "skill_pipeline.stages.qa.repair.run_check",
            return_value=0,
        ),
        patch(
            "skill_pipeline.stages.qa.repair.run_verify",
            return_value=0,
        ),
        patch(
            "skill_pipeline.stages.qa.repair.run_coverage",
            side_effect=_clear_findings,
        ),
    ):
        result = run_repair("imprivata", project_root=tmp_path)

    assert result == 0
    payload = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))
    assert payload["events"][0]["summary"] == "Patched summary"


def test_repair_reruns_deterministic_stages(tmp_path: Path) -> None:
    from skill_pipeline.stages.qa.repair import RepairPatchArtifact, run_repair

    _write_repair_fixture(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    _write_findings(
        paths,
        verification_findings=[
            {
                "check_type": "structural_integrity",
                "severity": "error",
                "repairability": "repairable",
                "description": "Proposal summary needs correction.",
                "event_ids": ["evt_001"],
            }
        ],
    )

    patch_output = RepairPatchArtifact(
        actors_raw=None,
        events_raw=_events_output(summary="Patched summary"),
        repair_notes=["Updated proposal summary."],
    )

    def _clear_findings(*args, **kwargs) -> int:
        _write_findings(paths)
        return 0

    with (
        patch(
            "skill_pipeline.stages.qa.repair.invoke_structured",
            return_value=patch_output,
        ),
        patch(
            "skill_pipeline.stages.qa.repair.run_materialize",
            return_value=0,
        ) as mock_materialize,
        patch(
            "skill_pipeline.stages.qa.repair.run_check",
            return_value=0,
        ) as mock_check,
        patch(
            "skill_pipeline.stages.qa.repair.run_verify",
            return_value=0,
        ) as mock_verify,
        patch(
            "skill_pipeline.stages.qa.repair.run_coverage",
            side_effect=_clear_findings,
        ) as mock_coverage,
    ):
        result = run_repair("imprivata", project_root=tmp_path)

    assert result == 0
    mock_materialize.assert_called_once_with("imprivata", project_root=tmp_path)
    mock_check.assert_called_once_with("imprivata", project_root=tmp_path)
    mock_verify.assert_called_once_with("imprivata", project_root=tmp_path)
    mock_coverage.assert_called_once_with("imprivata", project_root=tmp_path)


def test_repair_stops_after_two_rounds(tmp_path: Path) -> None:
    from skill_pipeline.stages.qa.repair import RepairPatchArtifact, run_repair

    _write_repair_fixture(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    _write_findings(
        paths,
        verification_findings=[
            {
                "check_type": "structural_integrity",
                "severity": "error",
                "repairability": "repairable",
                "description": "Proposal summary needs correction.",
                "event_ids": ["evt_001"],
            }
        ],
    )

    patch_output = RepairPatchArtifact(
        actors_raw=None,
        events_raw=_events_output(summary="Still wrong"),
        repair_notes=["Attempted update."],
    )

    with (
        patch(
            "skill_pipeline.stages.qa.repair.invoke_structured",
            return_value=patch_output,
        ) as mock_invoke,
        patch(
            "skill_pipeline.stages.qa.repair.run_materialize",
            return_value=0,
        ),
        patch(
            "skill_pipeline.stages.qa.repair.run_check",
            return_value=0,
        ),
        patch(
            "skill_pipeline.stages.qa.repair.run_verify",
            return_value=0,
        ),
        patch(
            "skill_pipeline.stages.qa.repair.run_coverage",
            return_value=0,
        ),
    ):
        with pytest.raises(RuntimeError, match="after 2 rounds"):
            run_repair("imprivata", project_root=tmp_path)

    assert mock_invoke.call_count == 2


def test_repair_sends_rendered_blocks_not_raw_jsonl(tmp_path: Path) -> None:
    from skill_pipeline.stages.qa.repair import RepairPatchArtifact, run_repair

    _write_repair_fixture(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    _write_findings(
        paths,
        verification_findings=[
            {
                "check_type": "structural_integrity",
                "severity": "error",
                "repairability": "repairable",
                "description": "Needs correction.",
                "event_ids": ["evt_001"],
            }
        ],
    )

    patch_output = RepairPatchArtifact(
        actors_raw=None,
        events_raw=_events_output(summary="Fixed"),
        repair_notes=["Fixed."],
    )

    def _clear_findings(*args, **kwargs) -> int:
        _write_findings(paths)
        return 0

    captured_user_message: dict[str, str] = {}

    def _capture_invoke(*, system_prompt, user_message, output_model):
        captured_user_message["text"] = user_message
        return patch_output

    with (
        patch(
            "skill_pipeline.stages.qa.repair.invoke_structured",
            side_effect=_capture_invoke,
        ),
        patch("skill_pipeline.stages.qa.repair.run_materialize", side_effect=_clear_findings),
        patch("skill_pipeline.stages.qa.repair.run_check", return_value=0),
        patch("skill_pipeline.stages.qa.repair.run_verify", return_value=0),
        patch("skill_pipeline.stages.qa.repair.run_coverage", return_value=0),
    ):
        run_repair("imprivata", project_root=tmp_path)

    user_msg = captured_user_message["text"]
    # Extract the filing_context section specifically
    fc_start = user_msg.index("<filing_context>") + len("<filing_context>")
    fc_end = user_msg.index("</filing_context>")
    filing_context = user_msg[fc_start:fc_end]
    # Should contain rendered block format, not raw JSONL
    assert "B001 [L1-L1]:" in filing_context
    # Filing context should NOT contain raw JSON keys
    assert '"block_id"' not in filing_context
    assert '"document_id"' not in filing_context


def test_repair_raises_when_patch_drops_records(tmp_path: Path) -> None:
    from skill_pipeline.stages.qa.repair import RepairPatchArtifact, run_repair

    _write_repair_fixture(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    _write_findings(
        paths,
        verification_findings=[
            {
                "check_type": "structural_integrity",
                "severity": "error",
                "repairability": "repairable",
                "description": "Needs fix.",
                "event_ids": ["evt_001"],
            }
        ],
    )

    # Patch returns ZERO events — a silent drop
    dropped_events = RawSkillEventsArtifact.model_validate(
        {"events": [], "exclusions": [], "coverage_notes": []}
    )
    patch_output = RepairPatchArtifact(
        actors_raw=None,
        events_raw=dropped_events,
        repair_notes=["Dropped everything."],
    )

    with (
        patch(
            "skill_pipeline.stages.qa.repair.invoke_structured",
            return_value=patch_output,
        ),
        patch("skill_pipeline.stages.qa.repair.run_materialize", return_value=0),
        patch("skill_pipeline.stages.qa.repair.run_check", return_value=0),
        patch("skill_pipeline.stages.qa.repair.run_verify", return_value=0),
        patch("skill_pipeline.stages.qa.repair.run_coverage", return_value=0),
    ):
        with pytest.raises(ValueError, match="dropped"):
            run_repair("imprivata", project_root=tmp_path)


def test_repair_passes_when_no_errors(tmp_path: Path) -> None:
    from skill_pipeline.stages.qa.repair import run_repair

    _write_repair_fixture(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    _write_findings(
        paths,
        verification_findings=[
            {
                "check_type": "structural_integrity",
                "severity": "warning",
                "repairability": "repairable",
                "description": "Minor warning only.",
                "event_ids": ["evt_001"],
            }
        ],
    )

    with (
        patch("skill_pipeline.stages.qa.repair.invoke_structured") as mock_invoke,
        patch("skill_pipeline.stages.qa.repair.run_materialize") as mock_materialize,
    ):
        result = run_repair("imprivata", project_root=tmp_path)

    assert result == 0
    mock_invoke.assert_not_called()
    mock_materialize.assert_not_called()
