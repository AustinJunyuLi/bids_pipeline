"""Tests for semantic gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_pipeline.cli import build_parser
from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.deal_agent import run_deal_agent
from skill_pipeline.enrich_core import run_enrich_core
from skill_pipeline.gates import run_gates
from skill_pipeline.models import GateReport, StageStatus
from skill_pipeline.paths import build_skill_paths, ensure_output_directories


def _make_block(
    block_id: str,
    ordinal: int,
    normalized: str | None,
    *,
    temporal_phase: str,
) -> dict:
    return {
        "block_id": block_id,
        "document_id": "DOC001",
        "ordinal": ordinal,
        "start_line": ordinal,
        "end_line": ordinal,
        "raw_text": f"Block {block_id}",
        "clean_text": f"Block {block_id}",
        "is_heading": False,
        "page_break_before": False,
        "page_break_after": False,
        "date_mentions": (
            [
                {
                    "raw_text": normalized,
                    "normalized": normalized,
                    "precision": "exact_day",
                }
            ]
            if normalized is not None
            else []
        ),
        "entity_mentions": [],
        "evidence_density": 1,
        "temporal_phase": temporal_phase,
    }


def _make_event(
    event_id: str,
    event_type: str,
    date_iso: str | None,
    *,
    actor_ids: list[str] | None = None,
    block_ids: list[str] | None = None,
    summary: str | None = None,
) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "date": date_iso,
        "actor_ids": actor_ids or [],
        "block_ids": block_ids or [],
        "summary": summary or f"{event_type} summary",
    }


def _default_blocks() -> list[dict]:
    return [
        _make_block("B001", 1, "2016-01-10", temporal_phase="initiation"),
        _make_block("B002", 2, "2016-02-15", temporal_phase="bidding"),
        _make_block("B003", 3, "2016-03-15", temporal_phase="bidding"),
        _make_block("B004", 4, "2016-04-20", temporal_phase="outcome"),
    ]


def _default_events() -> list[dict]:
    return [
        _make_event("evt_001", "nda", "2016-01-10", actor_ids=["party_a"], block_ids=["B001"]),
        _make_event(
            "evt_002",
            "final_round_ann",
            "2016-02-15",
            actor_ids=["party_a"],
            block_ids=["B002"],
        ),
        _make_event(
            "evt_003",
            "final_round",
            "2016-03-01",
            actor_ids=["party_a"],
            block_ids=["B003"],
        ),
        _make_event(
            "evt_004",
            "proposal",
            "2016-03-15",
            actor_ids=["party_a"],
            block_ids=["B003"],
        ),
        _make_event(
            "evt_005",
            "executed",
            "2016-04-20",
            actor_ids=["party_a"],
            block_ids=["B004"],
        ),
    ]


def _default_actors() -> list[dict]:
    return [
        {
            "actor_id": "party_a",
            "display_name": "Party A",
            "canonical_name": "PARTY A",
            "bidder_kind": "financial",
        }
    ]


def _quote_first_actor_payload(actors: list[dict], blocks: list[dict]) -> dict:
    actor_quotes: list[dict] = []
    actor_records: list[dict] = []
    default_block_id = blocks[0]["block_id"]
    for actor in actors:
        quote_id = f"quote_actor_{actor['actor_id']}"
        actor_quotes.append(
            {
                "quote_id": quote_id,
                "block_id": actor.get("quote_block_id", default_block_id),
                "text": actor["display_name"],
            }
        )
        actor_records.append(
            {
                "actor_id": actor["actor_id"],
                "display_name": actor["display_name"],
                "canonical_name": actor["canonical_name"],
                "aliases": [],
                "role": "bidder",
                "advisor_kind": None,
                "advised_actor_id": None,
                "bidder_kind": actor.get("bidder_kind"),
                "listing_status": "private",
                "geography": "domestic",
                "is_grouped": False,
                "group_size": None,
                "group_label": None,
                "quote_ids": [quote_id],
                "notes": [],
            }
        )
    return {
        "quotes": actor_quotes,
        "actors": actor_records,
        "count_assertions": [],
        "unresolved_mentions": [],
    }


def _quote_first_event_payload(events: list[dict]) -> dict:
    quotes: list[dict] = []
    event_records: list[dict] = []
    for event in events:
        quote_ids: list[str] = []
        for idx, block_id in enumerate(event["block_ids"], start=1):
            quote_id = f"quote_{event['event_id']}_{idx}"
            quote_ids.append(quote_id)
            quotes.append(
                {
                    "quote_id": quote_id,
                    "block_id": block_id,
                    "text": f"{event['event_type']} evidence {idx}",
                }
            )
        event_records.append(
            {
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "date": {
                    "raw_text": event["date"],
                    "normalized_hint": event["date"],
                },
                "actor_ids": event["actor_ids"],
                "summary": event["summary"],
                "quote_ids": quote_ids,
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": True,
                "drop_reason_text": None,
                "round_scope": None,
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": event["event_type"] == "nda",
                "notes": [],
            }
        )
    return {
        "quotes": quotes,
        "events": event_records,
        "exclusions": [],
        "coverage_notes": [],
    }


def _canonical_actor_payload(actors: list[dict], blocks: list[dict]) -> tuple[dict, list[dict]]:
    actor_records: list[dict] = []
    span_records: list[dict] = []
    default_block_id = blocks[0]["block_id"]
    for actor in actors:
        span_id = f"span_actor_{actor['actor_id']}"
        span_records.append(
            {
                "span_id": span_id,
                "document_id": "DOC001",
                "accession_number": "DOC001",
                "filing_type": "DEFM14A",
                "start_line": 1,
                "end_line": 1,
                "start_char": None,
                "end_char": None,
                "block_ids": [actor.get("quote_block_id", default_block_id)],
                "evidence_ids": [],
                "anchor_text": actor["display_name"],
                "quote_text": actor["display_name"],
                "quote_text_normalized": actor["display_name"].lower(),
                "match_type": "exact",
                "resolution_note": None,
            }
        )
        actor_records.append(
            {
                "actor_id": actor["actor_id"],
                "display_name": actor["display_name"],
                "canonical_name": actor["canonical_name"],
                "aliases": [],
                "role": "bidder",
                "advisor_kind": None,
                "advised_actor_id": None,
                "bidder_kind": actor.get("bidder_kind"),
                "listing_status": "private",
                "geography": "domestic",
                "is_grouped": False,
                "group_size": None,
                "group_label": None,
                "evidence_span_ids": [span_id],
                "notes": [],
            }
        )
    return (
        {
            "actors": actor_records,
            "count_assertions": [],
            "unresolved_mentions": [],
        },
        span_records,
    )


def _canonical_event_payload(events: list[dict]) -> tuple[dict, list[dict]]:
    event_records: list[dict] = []
    span_records: list[dict] = []
    for idx, event in enumerate(events, start=1):
        span_id = f"span_event_{idx}"
        span_records.append(
            {
                "span_id": span_id,
                "document_id": "DOC001",
                "accession_number": "DOC001",
                "filing_type": "DEFM14A",
                "start_line": idx,
                "end_line": idx,
                "start_char": None,
                "end_char": None,
                "block_ids": event["block_ids"],
                "evidence_ids": [],
                "anchor_text": event["summary"],
                "quote_text": event["summary"],
                "quote_text_normalized": event["summary"].lower(),
                "match_type": "exact",
                "resolution_note": None,
            }
        )
        event_records.append(
            {
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "date": {
                    "raw_text": event["date"],
                    "normalized_start": event["date"],
                    "normalized_end": event["date"],
                    "sort_date": event["date"],
                    "precision": "exact_day" if event["date"] else "unknown",
                    "anchor_event_id": None,
                    "anchor_span_id": None,
                    "resolution_note": None,
                    "is_inferred": False,
                },
                "actor_ids": event["actor_ids"],
                "summary": event["summary"],
                "evidence_span_ids": [span_id],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": True,
                "drop_reason_text": None,
                "round_scope": None,
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": event["event_type"] == "nda",
                "notes": [],
            }
        )
    return (
        {
            "events": event_records,
            "exclusions": [],
            "coverage_notes": [],
        },
        span_records,
    )


def _write_gates_fixture(
    tmp_path: Path,
    *,
    slug: str = "imprivata",
    blocks: list[dict] | None = None,
    actors: list[dict] | None = None,
    events: list[dict] | None = None,
    verification_findings: list[dict] | None = None,
    canonical: bool = False,
    create_empty_verification_file: bool = False,
) -> None:
    blocks = blocks or _default_blocks()
    actors = actors or _default_actors()
    events = events or _default_events()

    data_dir = tmp_path / "data"
    source_dir = data_dir / "deals" / slug / "source"
    skill_root = data_dir / "skill" / slug
    extract_dir = skill_root / "extract"
    verify_dir = skill_root / "verify"
    raw_dir = tmp_path / "raw" / slug

    source_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)
    verify_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},Example Target,Example Buyer,2016-01-01,https://example.com,false\n"
        ),
        encoding="utf-8",
    )
    (source_dir / "chronology_blocks.jsonl").write_text(
        "".join(json.dumps(block) + "\n" for block in blocks),
        encoding="utf-8",
    )
    (source_dir / "evidence_items.jsonl").write_text("{}\n", encoding="utf-8")
    (raw_dir / "document_registry.json").write_text("{}", encoding="utf-8")

    if canonical:
        actors_payload, actor_spans = _canonical_actor_payload(actors, blocks)
        events_payload, event_spans = _canonical_event_payload(events)
        (extract_dir / "actors_raw.json").write_text(
            json.dumps(actors_payload),
            encoding="utf-8",
        )
        (extract_dir / "events_raw.json").write_text(
            json.dumps(events_payload),
            encoding="utf-8",
        )
        (extract_dir / "spans.json").write_text(
            json.dumps({"spans": actor_spans + event_spans}),
            encoding="utf-8",
        )
    else:
        (extract_dir / "actors_raw.json").write_text(
            json.dumps(_quote_first_actor_payload(actors, blocks)),
            encoding="utf-8",
        )
        (extract_dir / "events_raw.json").write_text(
            json.dumps(_quote_first_event_payload(events)),
            encoding="utf-8",
        )

    if verification_findings is not None or create_empty_verification_file:
        (verify_dir / "verification_findings.json").write_text(
            json.dumps(verification_findings or []),
            encoding="utf-8",
        )


def _write_stage_gatekeepers(
    tmp_path: Path,
    *,
    slug: str = "imprivata",
    check_status: str = "pass",
    verify_status: str = "pass",
    coverage_status: str = "pass",
    gates_status: str = "pass",
    gate_warning_count: int = 0,
) -> None:
    skill_root = tmp_path / "data" / "skill" / slug
    check_dir = skill_root / "check"
    verify_dir = skill_root / "verify"
    coverage_dir = skill_root / "coverage"
    gates_dir = skill_root / "gates"
    check_dir.mkdir(parents=True, exist_ok=True)
    verify_dir.mkdir(parents=True, exist_ok=True)
    coverage_dir.mkdir(parents=True, exist_ok=True)
    gates_dir.mkdir(parents=True, exist_ok=True)

    (check_dir / "check_report.json").write_text(
        json.dumps(
            {
                "findings": [],
                "summary": {
                    "blocker_count": 1 if check_status == "fail" else 0,
                    "warning_count": 0,
                    "status": check_status,
                },
            }
        ),
        encoding="utf-8",
    )
    (verify_dir / "verification_log.json").write_text(
        json.dumps(
            {
                "round_1": {"findings": [], "fixes_applied": []},
                "round_2": {"findings": [], "status": verify_status},
                "summary": {
                    "total_checks": 0,
                    "round_1_errors": 1 if verify_status == "fail" else 0,
                    "round_1_warnings": 0,
                    "fixes_applied": 0,
                    "round_2_errors": 0,
                    "round_2_warnings": 0,
                    "status": verify_status,
                },
            }
        ),
        encoding="utf-8",
    )
    (coverage_dir / "coverage_summary.json").write_text(
        json.dumps(
            {
                "status": coverage_status,
                "finding_count": 1 if coverage_status == "fail" else 0,
                "error_count": 1 if coverage_status == "fail" else 0,
                "warning_count": 0,
                "counts_by_cue_family": {},
            }
        ),
        encoding="utf-8",
    )
    (gates_dir / "gates_report.json").write_text(
        json.dumps(
            {
                "findings": [],
                "attention_decay": None,
                "summary": {
                    "blocker_count": 1 if gates_status == "fail" else 0,
                    "warning_count": gate_warning_count,
                    "status": gates_status,
                },
            }
        ),
        encoding="utf-8",
    )


def test_gate_models_validate_and_forbid_extras() -> None:
    from skill_pipeline.models import (
        GateAttentionDecay,
        GateFinding,
        GateReport,
        GateReportSummary,
        GatesStageSummary,
    )

    finding = GateFinding(
        gate_id="temporal_consistency",
        rule_id="date_block_mismatch",
        severity="blocker",
        description="Event date contradicts its evidence blocks.",
    )
    assert finding.event_ids == []
    assert finding.actor_ids == []
    assert finding.block_ids == []

    report = GateReport(
        findings=[finding],
        attention_decay=GateAttentionDecay(
            quartile_counts=[0, 1, 0, 0],
            hot_spots=[{"block_ordinal_start": 10, "failure_count": 3}],
            decay_score=0.25,
            note="Attention concentrated late in the filing.",
        ),
        summary=GateReportSummary(blocker_count=1, warning_count=0, status="fail"),
    )
    assert report.summary.status == "fail"

    stage = GatesStageSummary(status="pass")
    assert stage.blocker_count == 0
    assert stage.warning_count == 0

    with pytest.raises(Exception):
        GateFinding(
            gate_id="temporal_consistency",
            rule_id="date_block_mismatch",
            severity="blocker",
            description="bad",
            unexpected=True,
        )


def test_build_skill_paths_includes_gates_dir(tmp_path: Path) -> None:
    paths = build_skill_paths("example", project_root=tmp_path)

    assert paths.gates_dir == tmp_path / "data" / "skill" / "example" / "gates"
    assert paths.gates_report_path == paths.gates_dir / "gates_report.json"

    ensure_output_directories(paths)

    assert paths.gates_dir.exists()


def test_gates_cli_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args(["gates", "--deal", "stec"])

    assert args.command == "gates"
    assert args.deal == "stec"


def test_temporal_consistency_blocker(tmp_path: Path) -> None:
    blocks = [
        _make_block("B001", 1, "2015-01-01", temporal_phase="initiation"),
        _make_block("B002", 2, "2015-02-01", temporal_phase="bidding"),
        _make_block("B003", 3, "2015-03-01", temporal_phase="outcome"),
    ]
    events = [
        _make_event(
            "evt_001",
            "proposal",
            "2020-01-01",
            actor_ids=["party_a"],
            block_ids=["B002"],
        )
    ]
    _write_gates_fixture(tmp_path, blocks=blocks, events=events)

    exit_code = run_gates("imprivata", project_root=tmp_path)
    report = json.loads(
        build_skill_paths("imprivata", project_root=tmp_path)
        .gates_report_path.read_text(encoding="utf-8")
    )

    assert exit_code == 1
    assert report["findings"][0]["gate_id"] == "temporal_consistency"
    assert report["findings"][0]["rule_id"] == "date_block_mismatch"
    assert report["findings"][0]["severity"] == "blocker"


def test_temporal_consistency_skip_sparse(tmp_path: Path) -> None:
    blocks = [
        _make_block("B001", 1, "2015-01-01", temporal_phase="initiation"),
        _make_block("B002", 2, "2015-02-01", temporal_phase="bidding"),
        _make_block("B003", 3, None, temporal_phase="outcome"),
    ]
    events = [
        _make_event(
            "evt_001",
            "proposal",
            "2020-01-01",
            actor_ids=["party_a"],
            block_ids=["B002"],
        )
    ]
    _write_gates_fixture(tmp_path, blocks=blocks, events=events)

    run_gates("imprivata", project_root=tmp_path)
    report = json.loads(
        build_skill_paths("imprivata", project_root=tmp_path)
        .gates_report_path.read_text(encoding="utf-8")
    )

    assert report["summary"]["blocker_count"] == 0
    assert [finding for finding in report["findings"] if finding["gate_id"] == "temporal_consistency"] == []


def test_temporal_consistency_pass(tmp_path: Path) -> None:
    _write_gates_fixture(tmp_path)

    run_gates("imprivata", project_root=tmp_path)
    report = json.loads(
        build_skill_paths("imprivata", project_root=tmp_path)
        .gates_report_path.read_text(encoding="utf-8")
    )

    assert [finding for finding in report["findings"] if finding["gate_id"] == "temporal_consistency"] == []


def test_proposal_after_executed(tmp_path: Path) -> None:
    events = [
        _make_event("evt_001", "nda", "2016-01-10", actor_ids=["party_a"], block_ids=["B001"]),
        _make_event(
            "evt_002",
            "executed",
            "2016-03-15",
            actor_ids=["party_a"],
            block_ids=["B003"],
        ),
        _make_event(
            "evt_003",
            "proposal",
            "2016-03-20",
            actor_ids=["party_a"],
            block_ids=["B004"],
        ),
    ]
    _write_gates_fixture(tmp_path, events=events)

    exit_code = run_gates("imprivata", project_root=tmp_path)
    report = json.loads(
        build_skill_paths("imprivata", project_root=tmp_path)
        .gates_report_path.read_text(encoding="utf-8")
    )

    assert exit_code == 1
    assert any(
        finding["rule_id"] == "proposal_after_executed"
        and finding["severity"] == "blocker"
        for finding in report["findings"]
    )


def test_nda_after_drop(tmp_path: Path) -> None:
    events = [
        _make_event("evt_001", "nda", "2016-01-10", actor_ids=["party_a"], block_ids=["B001"]),
        _make_event("evt_002", "drop", "2016-02-01", actor_ids=["party_a"], block_ids=["B002"]),
        _make_event("evt_003", "nda", "2016-03-01", actor_ids=["party_a"], block_ids=["B003"]),
        _make_event("evt_004", "proposal", "2016-03-10", actor_ids=["party_a"], block_ids=["B004"]),
    ]
    _write_gates_fixture(tmp_path, events=events)

    exit_code = run_gates("imprivata", project_root=tmp_path)
    report = json.loads(
        build_skill_paths("imprivata", project_root=tmp_path)
        .gates_report_path.read_text(encoding="utf-8")
    )

    assert exit_code == 1
    assert any(finding["rule_id"] == "nda_after_drop" for finding in report["findings"])


def test_announcement_before_deadline(tmp_path: Path) -> None:
    events = [
        _make_event("evt_001", "nda", "2016-01-10", actor_ids=["party_a"], block_ids=["B001"]),
        _make_event(
            "evt_002",
            "final_round",
            "2016-03-01",
            actor_ids=["party_a"],
            block_ids=["B003"],
        ),
        _make_event(
            "evt_003",
            "proposal",
            "2016-03-15",
            actor_ids=["party_a"],
            block_ids=["B003"],
        ),
    ]
    _write_gates_fixture(tmp_path, events=events)

    exit_code = run_gates("imprivata", project_root=tmp_path)
    report = json.loads(
        build_skill_paths("imprivata", project_root=tmp_path)
        .gates_report_path.read_text(encoding="utf-8")
    )

    assert exit_code == 1
    assert any(
        finding["rule_id"] == "announcement_before_deadline"
        for finding in report["findings"]
    )


def test_executed_last_in_cycle(tmp_path: Path) -> None:
    events = [
        _make_event("evt_001", "nda", "2016-01-10", actor_ids=["party_a"], block_ids=["B001"]),
        _make_event(
            "evt_002",
            "proposal",
            "2016-03-15",
            actor_ids=["party_a"],
            block_ids=["B003"],
        ),
        _make_event(
            "evt_003",
            "executed",
            "2016-04-20",
            actor_ids=["party_a"],
            block_ids=["B004"],
        ),
        _make_event(
            "evt_004",
            "terminated",
            "2016-04-25",
            actor_ids=["party_a"],
            block_ids=["B004"],
        ),
    ]
    _write_gates_fixture(tmp_path, events=events)

    exit_code = run_gates("imprivata", project_root=tmp_path)
    report = json.loads(
        build_skill_paths("imprivata", project_root=tmp_path)
        .gates_report_path.read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert any(
        finding["rule_id"] == "executed_last_in_cycle"
        and finding["severity"] == "warning"
        for finding in report["findings"]
    )


def test_cross_event_clean_pass(tmp_path: Path) -> None:
    _write_gates_fixture(tmp_path)

    exit_code = run_gates("imprivata", project_root=tmp_path)
    report = json.loads(
        build_skill_paths("imprivata", project_root=tmp_path)
        .gates_report_path.read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert [finding for finding in report["findings"] if finding["gate_id"] == "cross_event_logic"] == []


def test_undated_events_excluded(tmp_path: Path) -> None:
    events = [
        _make_event("evt_001", "nda", "2016-01-10", actor_ids=["party_a"], block_ids=["B001"]),
        _make_event(
            "evt_002",
            "executed",
            "2016-04-20",
            actor_ids=["party_a"],
            block_ids=["B004"],
        ),
        _make_event(
            "evt_003",
            "proposal",
            None,
            actor_ids=["party_a"],
            block_ids=["B003"],
        ),
    ]
    _write_gates_fixture(tmp_path, events=events)

    exit_code = run_gates("imprivata", project_root=tmp_path)
    report = json.loads(
        build_skill_paths("imprivata", project_root=tmp_path)
        .gates_report_path.read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert not any(
        finding["rule_id"] == "proposal_after_executed"
        for finding in report["findings"]
    )
    assert any(
        finding["rule_id"] == "undated_event_in_sequence"
        and finding["severity"] == "warning"
        for finding in report["findings"]
    )


def test_nda_signer_missing_downstream(tmp_path: Path) -> None:
    events = [
        _make_event("evt_001", "nda", "2016-01-10", actor_ids=["party_a"], block_ids=["B001"])
    ]
    _write_gates_fixture(tmp_path, events=events)

    exit_code = run_gates("imprivata", project_root=tmp_path)
    report = json.loads(
        build_skill_paths("imprivata", project_root=tmp_path)
        .gates_report_path.read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert any(
        finding["rule_id"] == "nda_signer_no_downstream"
        and finding["severity"] == "warning"
        for finding in report["findings"]
    )


def test_nda_signers_all_present(tmp_path: Path) -> None:
    _write_gates_fixture(tmp_path)

    run_gates("imprivata", project_root=tmp_path)
    report = json.loads(
        build_skill_paths("imprivata", project_root=tmp_path)
        .gates_report_path.read_text(encoding="utf-8")
    )

    assert [finding for finding in report["findings"] if finding["gate_id"] == "actor_lifecycle"] == []


def test_attention_decay_no_failures(tmp_path: Path) -> None:
    _write_gates_fixture(tmp_path, create_empty_verification_file=True)

    run_gates("imprivata", project_root=tmp_path)
    report = json.loads(
        build_skill_paths("imprivata", project_root=tmp_path)
        .gates_report_path.read_text(encoding="utf-8")
    )

    assert report["attention_decay"]["quartile_counts"] == [0, 0, 0, 0]
    assert report["attention_decay"]["decay_score"] == 1.0


def test_attention_decay_concentrated(tmp_path: Path) -> None:
    blocks = [
        _make_block(f"B{idx:03d}", idx, f"2016-01-{idx:02d}", temporal_phase="bidding")
        for idx in range(1, 13)
    ]
    verification_findings = [
        {
            "check_type": "quote_validation",
            "severity": "error",
            "description": "late filing failure",
            "block_ids": ["B010"],
        },
        {
            "check_type": "quote_validation",
            "severity": "error",
            "description": "late filing failure",
            "block_ids": ["B011"],
        },
        {
            "check_type": "quote_validation",
            "severity": "error",
            "description": "late filing failure",
            "block_ids": ["B012"],
        },
    ]
    _write_gates_fixture(
        tmp_path,
        blocks=blocks,
        verification_findings=verification_findings,
    )

    run_gates("imprivata", project_root=tmp_path)
    report = json.loads(
        build_skill_paths("imprivata", project_root=tmp_path)
        .gates_report_path.read_text(encoding="utf-8")
    )

    assert report["attention_decay"]["decay_score"] < 0.5
    assert report["attention_decay"]["hot_spots"] != []


def test_attention_decay_uniform(tmp_path: Path) -> None:
    blocks = [
        _make_block(f"B{idx:03d}", idx, f"2016-01-{idx:02d}", temporal_phase="bidding")
        for idx in range(1, 13)
    ]
    verification_findings = [
        {
            "check_type": "quote_validation",
            "severity": "error",
            "description": "spread failure",
            "block_ids": ["B001"],
        },
        {
            "check_type": "quote_validation",
            "severity": "error",
            "description": "spread failure",
            "block_ids": ["B004"],
        },
        {
            "check_type": "quote_validation",
            "severity": "error",
            "description": "spread failure",
            "block_ids": ["B007"],
        },
        {
            "check_type": "quote_validation",
            "severity": "error",
            "description": "spread failure",
            "block_ids": ["B010"],
        },
    ]
    _write_gates_fixture(
        tmp_path,
        blocks=blocks,
        verification_findings=verification_findings,
    )

    run_gates("imprivata", project_root=tmp_path)
    report = json.loads(
        build_skill_paths("imprivata", project_root=tmp_path)
        .gates_report_path.read_text(encoding="utf-8")
    )

    assert report["attention_decay"]["decay_score"] > 0.9


def test_attention_decay_reads_wrapped_findings_payload(tmp_path: Path) -> None:
    _write_gates_fixture(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    paths.verify_dir.mkdir(parents=True, exist_ok=True)
    paths.verification_findings_path.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "check_type": "quote_validation",
                        "severity": "error",
                        "description": "wrapped payload failure",
                        "block_ids": ["B001"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    run_gates("imprivata", project_root=tmp_path)
    report = json.loads(paths.gates_report_path.read_text(encoding="utf-8"))

    assert report["attention_decay"]["quartile_counts"][0] == 1


def test_run_gates_returns_zero_on_pass(tmp_path: Path) -> None:
    _write_gates_fixture(tmp_path)

    assert run_gates("imprivata", project_root=tmp_path) == 0


def test_run_gates_returns_one_on_blocker(tmp_path: Path) -> None:
    events = [
        _make_event(
            "evt_001",
            "proposal",
            "2020-01-01",
            actor_ids=["party_a"],
            block_ids=["B001"],
        )
    ]
    _write_gates_fixture(tmp_path, events=events)

    assert run_gates("imprivata", project_root=tmp_path) == 1


def test_run_gates_writes_report(tmp_path: Path) -> None:
    _write_gates_fixture(tmp_path, create_empty_verification_file=True)

    run_gates("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    assert paths.gates_report_path.exists()
    GateReport.model_validate(json.loads(paths.gates_report_path.read_text(encoding="utf-8")))


def test_enrich_core_requires_gates_pass(tmp_path: Path) -> None:
    _write_gates_fixture(tmp_path, canonical=True)
    _write_stage_gatekeepers(tmp_path, gates_status="fail")

    with pytest.raises(ValueError, match="gates pass"):
        run_enrich_core("imprivata", project_root=tmp_path)


def test_enrich_core_requires_gates_exist(tmp_path: Path) -> None:
    _write_gates_fixture(tmp_path, canonical=True)
    _write_stage_gatekeepers(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    paths.gates_report_path.unlink()

    with pytest.raises(FileNotFoundError, match="gates_report"):
        run_enrich_core("imprivata", project_root=tmp_path)


def test_deal_agent_gates_missing(tmp_path: Path) -> None:
    _write_gates_fixture(tmp_path)

    summary = run_deal_agent("imprivata", project_root=tmp_path)

    assert summary.gates.status == StageStatus.MISSING


def test_deal_agent_gates_pass(tmp_path: Path) -> None:
    _write_gates_fixture(tmp_path)
    _write_stage_gatekeepers(tmp_path, gate_warning_count=2)

    summary = run_deal_agent("imprivata", project_root=tmp_path)

    assert summary.gates.status == StageStatus.PASS
    assert summary.gates.blocker_count == 0
    assert summary.gates.warning_count == 2


def test_gates_canonical_mode(tmp_path: Path) -> None:
    _write_gates_fixture(tmp_path, canonical=True, create_empty_verification_file=True)

    exit_code = run_gates("imprivata", project_root=tmp_path)
    report = json.loads(
        build_skill_paths("imprivata", project_root=tmp_path)
        .gates_report_path.read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert report["summary"]["status"] == "pass"


_STEC_DATA = PROJECT_ROOT / "data" / "skill" / "stec" / "extract" / "actors_raw.json"


@pytest.mark.skipif(not _STEC_DATA.exists(), reason="stec data not available")
def test_stec_gates_pass() -> None:
    paths = build_skill_paths("stec", project_root=PROJECT_ROOT)
    original_report = (
        paths.gates_report_path.read_text(encoding="utf-8")
        if paths.gates_report_path.exists()
        else None
    )

    try:
        result = run_gates("stec", project_root=PROJECT_ROOT)
        report = json.loads(paths.gates_report_path.read_text(encoding="utf-8"))
        assert result == 0, f"stec should pass all semantic gates: {report['findings']}"
        assert report["summary"]["status"] == "pass"
    finally:
        if original_report is None:
            if paths.gates_report_path.exists():
                paths.gates_report_path.unlink()
            if paths.gates_dir.exists() and not any(paths.gates_dir.iterdir()):
                paths.gates_dir.rmdir()
        else:
            paths.gates_report_path.write_text(original_report, encoding="utf-8")
