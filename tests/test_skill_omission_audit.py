from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from skill_pipeline import cli
from skill_pipeline.schemas.runtime import CoverageFindingsArtifact


def _write_omission_audit_fixture(tmp_path: Path, *, slug: str = "imprivata") -> None:
    data_dir = tmp_path / "data"
    source_dir = data_dir / "deals" / slug / "source"
    materialize_dir = data_dir / "skill" / slug / "materialize"
    coverage_dir = data_dir / "skill" / slug / "coverage"

    source_dir.mkdir(parents=True, exist_ok=True)
    materialize_dir.mkdir(parents=True, exist_ok=True)
    coverage_dir.mkdir(parents=True, exist_ok=True)

    chronology_blocks = [
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
        },
        {
            "block_id": "B002",
            "document_id": "DOC001",
            "ordinal": 2,
            "start_line": 2,
            "end_line": 2,
            "raw_text": "On July 10, 2016, bidders were invited to submit final bids by July 15, 2016.",
            "clean_text": "On July 10, 2016, bidders were invited to submit final bids by July 15, 2016.",
            "is_heading": False,
            "page_break_before": False,
            "page_break_after": False,
        },
    ]
    (source_dir / "chronology_blocks.jsonl").write_text(
        "\n".join(json.dumps(block) for block in chronology_blocks) + "\n",
        encoding="utf-8",
    )

    (materialize_dir / "actors.json").write_text(
        json.dumps({"actors": [], "count_assertions": [], "unresolved_mentions": []}),
        encoding="utf-8",
    )
    (materialize_dir / "events.json").write_text(
        json.dumps(
            {
                "events": [
                    {
                        "event_id": "evt_001",
                        "event_type": "nda",
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
                        "summary": "Party A signed a confidentiality agreement.",
                        "evidence_span_ids": ["span_0001"],
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
    (materialize_dir / "spans.json").write_text(
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
                        "end_char": 20,
                        "block_ids": ["B001"],
                        "evidence_ids": [],
                        "anchor_text": "signed a confidentiality agreement",
                        "quote_text": "Party A signed a confidentiality agreement.",
                        "quote_text_normalized": "party a signed a confidentiality agreement.",
                        "match_type": "exact",
                        "resolution_note": None,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (coverage_dir / "coverage_findings.json").write_text(
        json.dumps({"findings": []}),
        encoding="utf-8",
    )


def _omission_output() -> CoverageFindingsArtifact:
    return CoverageFindingsArtifact.model_validate(
        {
            "findings": [
                {
                    "cue_family": "round_event",
                    "severity": "error",
                    "repairability": "repairable",
                    "description": "Explicit final-round invitation appears uncovered.",
                    "block_ids": ["B002"],
                    "evidence_ids": [],
                    "matched_terms": ["final bids"],
                    "confidence": "high",
                    "suggested_event_types": ["final_round_ann", "final_round"],
                }
            ]
        }
    )


def test_skill_cli_supports_omission_audit_subcommand() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["omission-audit", "--deal", "imprivata"])

    assert args.command == "omission-audit"
    assert args.deal == "imprivata"


def test_run_omission_audit_writes_findings_and_prompts_with_uncovered_blocks(
    tmp_path: Path,
) -> None:
    from skill_pipeline.stages.qa.omission_audit import run_omission_audit

    _write_omission_audit_fixture(tmp_path)

    with patch(
        "skill_pipeline.stages.qa.omission_audit.invoke_structured",
        return_value=_omission_output(),
    ) as mock_invoke:
        result = run_omission_audit("imprivata", project_root=tmp_path)

    assert result == 1
    omission_path = (
        tmp_path
        / "data"
        / "skill"
        / "imprivata"
        / "coverage"
        / "omission_findings.json"
    )
    payload = json.loads(omission_path.read_text(encoding="utf-8"))
    assert payload["findings"][0]["cue_family"] == "round_event"
    assert payload["findings"][0]["suggested_event_types"] == [
        "final_round_ann",
        "final_round",
    ]

    user_message = mock_invoke.call_args.kwargs["user_message"]
    assert "B002" in user_message
    assert "final bids by July 15, 2016" in user_message
    assert "B001" not in user_message


def test_run_omission_audit_writes_empty_findings_when_no_uncovered_blocks(
    tmp_path: Path,
) -> None:
    from skill_pipeline.stages.qa.omission_audit import run_omission_audit

    _write_omission_audit_fixture(tmp_path)
    source_dir = tmp_path / "data" / "deals" / "imprivata" / "source"
    materialize_dir = tmp_path / "data" / "skill" / "imprivata" / "materialize"

    (source_dir / "chronology_blocks.jsonl").write_text(
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
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (materialize_dir / "spans.json").write_text(
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
                        "end_char": 20,
                        "block_ids": ["B001"],
                        "evidence_ids": [],
                        "anchor_text": "signed a confidentiality agreement",
                        "quote_text": "Party A signed a confidentiality agreement.",
                        "quote_text_normalized": "party a signed a confidentiality agreement.",
                        "match_type": "exact",
                        "resolution_note": None,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with patch(
        "skill_pipeline.stages.qa.omission_audit.invoke_structured"
    ) as mock_invoke:
        result = run_omission_audit("imprivata", project_root=tmp_path)

    assert result == 0
    mock_invoke.assert_not_called()
    omission_path = (
        tmp_path
        / "data"
        / "skill"
        / "imprivata"
        / "coverage"
        / "omission_findings.json"
    )
    payload = json.loads(omission_path.read_text(encoding="utf-8"))
    assert payload == {"findings": []}
