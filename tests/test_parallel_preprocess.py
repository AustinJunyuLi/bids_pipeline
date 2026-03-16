from concurrent.futures import ThreadPoolExecutor
from datetime import date

from pipeline.normalize.dates import parse_date_value, parse_date_values
from pipeline.normalize.quotes import normalize_for_matching, normalize_for_matching_batch
from pipeline.orchestrator import PipelineOrchestrator
from pipeline.source.locate import (
    collect_chronology_candidates,
    normalize_heading_candidate,
    normalize_heading_candidates_batch,
)


def test_batch_heading_normalization_matches_single_item_logic():
    headings = ["BACKGROUND OF THE MERGER.", "II. Background of the Offer", "  Background  "]

    assert normalize_heading_candidates_batch(headings) == [
        normalize_heading_candidate(heading) for heading in headings
    ]


def test_batch_quote_normalization_matches_single_item_logic():
    texts = ["Party A’s “offer”", "Party B — revised", " spaced   text "]

    assert normalize_for_matching_batch(texts) == [
        normalize_for_matching(text) for text in texts
    ]


def test_batch_date_parsing_matches_single_item_logic():
    raw_dates = ["March 9, 2016", "mid-February 2013", "Q3 2015"]

    batch = parse_date_values(raw_dates)

    assert batch == [parse_date_value(raw_date) for raw_date in raw_dates]
    assert batch[0].normalized_start == date(2016, 3, 9)


def test_batch_candidate_collection_preserves_original_heading_text():
    lines = [
        "BACKGROUND OF THE MERGER",
        "",
        "On March 9, 2016, the board met with Company advisors.",
        "On March 10, 2016, the company received an offer.",
        "",
        "On March 11, 2016, management met with Party A.",
        "On March 12, 2016, the board reviewed a revised proposal.",
        "",
        "On March 13, 2016, the company exchanged a draft merger agreement.",
        "",
        "SIGN HERE",
    ]

    candidates = collect_chronology_candidates(lines, document_id="doc-1")

    assert candidates[0].heading_text == "BACKGROUND OF THE MERGER"


def test_orchestrator_runs_preprocess_batch_with_parallel_executor(tmp_path):
    orchestrator = PipelineOrchestrator.from_db_path(tmp_path / "pipeline_state.sqlite")

    def fake_preprocess(
        deal_slug: str,
        *,
        run_id: str,
        raw_dir,
        deals_dir,
    ) -> dict[str, str]:
        return {"deal_slug": deal_slug, "run_id": run_id, "status": "ok"}

    results = orchestrator.run_preprocess_source_batch(
        run_id="run-1",
        deal_slugs=["imprivata", "zep", "imprivata"],
        workers=2,
        preprocess_fn=fake_preprocess,
        executor_cls=ThreadPoolExecutor,
    )

    assert results == {
        "imprivata": {"deal_slug": "imprivata", "run_id": "run-1", "status": "ok"},
        "zep": {"deal_slug": "zep", "run_id": "run-1", "status": "ok"},
    }
