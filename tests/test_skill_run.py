from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from skill_pipeline import cli


def test_skill_cli_supports_run_subcommand() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["run", "--deal", "imprivata"])

    assert args.command == "run"
    assert args.deal == "imprivata"


def test_cli_main_dispatches_run_subcommand(tmp_path: Path) -> None:
    with patch("skill_pipeline.cli.run_deal", return_value=0) as mock_run:
        result = cli.main(
            ["run", "--deal", "imprivata", "--project-root", str(tmp_path)]
        )

    assert result == 0
    mock_run.assert_called_once_with("imprivata", project_root=tmp_path)


def test_run_deal_runs_all_pipeline_stages_and_leaves_reconcile_standalone(
    tmp_path: Path,
) -> None:
    from skill_pipeline.stages.run import run_deal

    calls: list[tuple[str, str, Path]] = []

    def _record(stage_name: str):
        def _inner(deal_slug: str, *, project_root: Path) -> int:
            calls.append((stage_name, deal_slug, project_root))
            return 0

        return _inner

    with (
        patch(
            "skill_pipeline.stages.extract.run_extract",
            side_effect=_record("extract"),
        ),
        patch(
            "skill_pipeline.stages.materialize.run_materialize",
            side_effect=_record("materialize"),
        ),
        patch(
            "skill_pipeline.stages.qa.check.run_check",
            side_effect=_record("check"),
        ),
        patch(
            "skill_pipeline.stages.qa.verify.run_verify", side_effect=_record("verify")
        ),
        patch(
            "skill_pipeline.stages.qa.coverage.run_coverage",
            side_effect=_record("coverage"),
        ),
        patch(
            "skill_pipeline.stages.qa.omission_audit.run_omission_audit",
            side_effect=_record("omission-audit"),
        ),
        patch(
            "skill_pipeline.stages.qa.repair.run_repair", side_effect=_record("repair")
        ),
        patch(
            "skill_pipeline.stages.enrich.core.run_enrich_core",
            side_effect=_record("enrich-core"),
        ),
        patch(
            "skill_pipeline.stages.enrich.interpret.run_enrich_interpret",
            side_effect=_record("enrich-interpret"),
        ),
        patch("skill_pipeline.stages.export.run_export", side_effect=_record("export")),
    ):
        result = run_deal("imprivata", project_root=tmp_path)

    assert result == 0
    assert calls == [
        ("extract", "imprivata", tmp_path),
        ("materialize", "imprivata", tmp_path),
        ("check", "imprivata", tmp_path),
        ("verify", "imprivata", tmp_path),
        ("coverage", "imprivata", tmp_path),
        ("omission-audit", "imprivata", tmp_path),
        ("repair", "imprivata", tmp_path),
        ("enrich-core", "imprivata", tmp_path),
        ("enrich-interpret", "imprivata", tmp_path),
        ("export", "imprivata", tmp_path),
    ]


def test_run_deal_returns_1_when_repair_raises(tmp_path: Path) -> None:
    from skill_pipeline.stages.run import run_deal

    with (
        patch("skill_pipeline.stages.extract.run_extract", return_value=0),
        patch("skill_pipeline.stages.materialize.run_materialize", return_value=0),
        patch("skill_pipeline.stages.qa.check.run_check", return_value=0),
        patch("skill_pipeline.stages.qa.verify.run_verify", return_value=0),
        patch("skill_pipeline.stages.qa.coverage.run_coverage", return_value=0),
        patch("skill_pipeline.stages.qa.omission_audit.run_omission_audit", return_value=0),
        patch(
            "skill_pipeline.stages.qa.repair.run_repair",
            side_effect=RuntimeError("non-repairable"),
        ),
        patch("skill_pipeline.stages.enrich.core.run_enrich_core") as mock_enrich,
        patch("skill_pipeline.stages.enrich.interpret.run_enrich_interpret") as mock_interpret,
        patch("skill_pipeline.stages.export.run_export") as mock_export,
    ):
        result = run_deal("imprivata", project_root=tmp_path)

    assert result == 1
    mock_enrich.assert_not_called()
    mock_interpret.assert_not_called()
    mock_export.assert_not_called()


def test_run_deal_runs_all_qa_stages_even_when_check_fails(
    tmp_path: Path,
) -> None:
    from skill_pipeline.stages.run import run_deal

    calls: list[str] = []

    def _record(name: str, retval: int = 0):
        def _inner(*args, **kwargs):
            calls.append(name)
            return retval
        return _inner

    with (
        patch("skill_pipeline.stages.extract.run_extract", side_effect=_record("extract")),
        patch("skill_pipeline.stages.materialize.run_materialize", side_effect=_record("materialize")),
        patch("skill_pipeline.stages.qa.check.run_check", side_effect=_record("check", 1)),
        patch("skill_pipeline.stages.qa.verify.run_verify", side_effect=_record("verify")),
        patch("skill_pipeline.stages.qa.coverage.run_coverage", side_effect=_record("coverage")),
        patch("skill_pipeline.stages.qa.omission_audit.run_omission_audit", side_effect=_record("omission-audit")),
        patch("skill_pipeline.stages.qa.repair.run_repair", side_effect=_record("repair")),
        patch("skill_pipeline.stages.enrich.core.run_enrich_core", side_effect=_record("enrich-core")),
        patch("skill_pipeline.stages.enrich.interpret.run_enrich_interpret", side_effect=_record("enrich-interpret")),
        patch("skill_pipeline.stages.export.run_export", side_effect=_record("export")),
    ):
        result = run_deal("imprivata", project_root=tmp_path)

    assert result == 0
    # ALL QA stages run regardless of individual results — repair gets the full picture
    assert "check" in calls
    assert "verify" in calls
    assert "coverage" in calls
    assert "omission-audit" in calls
    assert "repair" in calls


def test_run_deal_prints_stage_status(tmp_path: Path, capsys) -> None:
    from skill_pipeline.stages.run import run_deal

    with (
        patch("skill_pipeline.stages.extract.run_extract", return_value=0),
        patch("skill_pipeline.stages.materialize.run_materialize", return_value=0),
        patch("skill_pipeline.stages.qa.check.run_check", return_value=0),
        patch("skill_pipeline.stages.qa.verify.run_verify", return_value=0),
        patch("skill_pipeline.stages.qa.coverage.run_coverage", return_value=0),
        patch("skill_pipeline.stages.qa.omission_audit.run_omission_audit", return_value=0),
        patch("skill_pipeline.stages.qa.repair.run_repair", return_value=0),
        patch("skill_pipeline.stages.enrich.core.run_enrich_core", return_value=0),
        patch("skill_pipeline.stages.enrich.interpret.run_enrich_interpret", return_value=0),
        patch("skill_pipeline.stages.export.run_export", return_value=0),
    ):
        run_deal("imprivata", project_root=tmp_path)

    output = capsys.readouterr().out
    assert "PASS" in output
    assert "Pipeline complete" in output
