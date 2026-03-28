"""Tests for semantic gates."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_pipeline.paths import build_skill_paths, ensure_output_directories


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
