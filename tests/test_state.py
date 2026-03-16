from concurrent.futures import ThreadPoolExecutor

from pipeline.orchestrator import stage_names_from
from pipeline.state import PipelineStateStore


def test_state_store_can_start_run_and_summarize(tmp_path):
    db_path = tmp_path / "runs" / "pipeline_state.sqlite"
    store = PipelineStateStore(db_path)

    store.start_run(
        run_id="run-1",
        code_version="abc123",
        config_hash="cfg-1",
        mode="strict",
    )
    store.record_stage_attempt(
        run_id="run-1",
        deal_slug="imprivata",
        stage_name="source_discover",
        status="success",
        duration_ms=250,
    )
    store.record_artifact(
        run_id="run-1",
        deal_slug="imprivata",
        artifact_type="filing_discovery_report",
        path="data/deals/imprivata/source/discovery.json",
        sha256="deadbeef",
        schema_version="2.0.0",
    )
    store.record_review_item(
        review_id="review-1",
        deal_slug="imprivata",
        stage_name="source_locate",
        severity="warning",
        code="low_confidence",
        message="Chronology section is short.",
        artifact_path="data/deals/imprivata/source/chronology_selection.json",
    )

    summary = store.summarize_run("run-1")

    assert summary["run"]["mode"] == "strict"
    assert summary["counts"]["stage_attempts"] == 1
    assert summary["counts"]["artifacts"] == 1
    assert summary["counts"]["review_items"] == 1


def test_state_store_resume_semantics_return_existing_run(tmp_path):
    db_path = tmp_path / "pipeline_state.sqlite"
    store = PipelineStateStore(db_path)

    first = store.start_run(
        run_id="run-1",
        code_version="abc123",
        config_hash="cfg-1",
        mode="strict",
    )
    resumed = store.start_run(
        run_id="run-1",
        code_version="abc123",
        config_hash="cfg-1",
        mode="strict",
        resume=True,
    )

    assert resumed["started_at"] == first["started_at"]
    assert store.list_runs() == ["run-1"]


def test_record_stage_attempt_increments_attempt_number_on_rerun(tmp_path):
    db_path = tmp_path / "pipeline_state.sqlite"
    store = PipelineStateStore(db_path)
    store.start_run(
        run_id="run-1",
        code_version="abc123",
        config_hash="cfg-1",
        mode="strict",
    )

    first = store.record_stage_attempt(
        run_id="run-1",
        deal_slug="imprivata",
        stage_name="source_discover",
        status="success",
    )
    second = store.record_stage_attempt(
        run_id="run-1",
        deal_slug="imprivata",
        stage_name="source_discover",
        status="queued",
    )

    assert first["attempt_no"] == 1
    assert second["attempt_no"] == 2


def test_stage_names_from_supports_rerun_from_stage():
    assert stage_names_from("preprocess_source") == [
        "preprocess_source",
        "extract_actors",
        "extract_events",
        "qa",
        "enrich",
        "export",
        "validate_references",
    ]


def test_stage_names_include_decoupled_raw_stages():
    assert stage_names_from("raw_discover")[:3] == [
        "raw_discover",
        "raw_freeze",
        "preprocess_source",
    ]


def test_state_store_supports_simple_concurrent_writes(tmp_path):
    db_path = tmp_path / "pipeline_state.sqlite"
    store = PipelineStateStore(db_path)
    store.start_run(
        run_id="run-1",
        code_version="abc123",
        config_hash="cfg-1",
        mode="exploratory",
    )

    def write_attempt(i: int) -> None:
        store.record_stage_attempt(
            run_id="run-1",
            deal_slug=f"deal-{i}",
            stage_name="source_discover",
            status="success",
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(write_attempt, range(8)))

    summary = store.summarize_run("run-1")
    assert summary["counts"]["stage_attempts"] == 8
