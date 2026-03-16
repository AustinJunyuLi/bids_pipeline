import json
from pathlib import Path

from pipeline.config import RAW_DIR
from pipeline.orchestrator import PipelineOrchestrator


REFERENCE_DEALS = [
    "imprivata",
    "medivation",
    "zep",
    "petsmart-inc",
    "penford",
    "mac-gray",
    "saks",
    "providence-worcester",
    "stec",
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []
    return [json.loads(line) for line in text.splitlines()]


def _stable_selection(payload: dict) -> dict:
    normalized = dict(payload)
    normalized.pop("run_id", None)
    normalized.pop("created_at", None)
    return normalized


def test_reference_raw_archives_rebuild_offline_deterministically(monkeypatch, tmp_path: Path):
    missing = [
        slug
        for slug in REFERENCE_DEALS
        if not (RAW_DIR / slug / "discovery.json").exists()
        or not (RAW_DIR / slug / "document_registry.json").exists()
    ]
    assert not missing, f"Missing raw archives for: {', '.join(missing)}"

    def _no_network(*_args, **_kwargs):
        raise AssertionError("offline preprocess should not make network calls")

    monkeypatch.setattr("urllib.request.urlopen", _no_network)

    orchestrator = PipelineOrchestrator.from_db_path(tmp_path / "pipeline_state.sqlite")
    serial_dir = tmp_path / "serial" / "deals"
    parallel_dir = tmp_path / "parallel" / "deals"

    serial_results = orchestrator.run_preprocess_source_batch(
        run_id="offline-serial",
        deal_slugs=REFERENCE_DEALS,
        workers=1,
        raw_dir=RAW_DIR,
        deals_dir=serial_dir,
    )
    parallel_results = orchestrator.run_preprocess_source_batch(
        run_id="offline-parallel",
        deal_slugs=REFERENCE_DEALS,
        workers=2,
        raw_dir=RAW_DIR,
        deals_dir=parallel_dir,
    )

    assert serial_results.keys() == parallel_results.keys()

    for slug in REFERENCE_DEALS:
        serial_source = serial_dir / slug / "source"
        parallel_source = parallel_dir / slug / "source"
        serial_selection = _load_json(serial_source / "chronology_selection.json")
        parallel_selection = _load_json(parallel_source / "chronology_selection.json")
        serial_blocks = _load_jsonl(serial_source / "chronology_blocks.jsonl")
        parallel_blocks = _load_jsonl(parallel_source / "chronology_blocks.jsonl")
        serial_snippets = _load_jsonl(serial_source / "supplementary_snippets.jsonl")
        parallel_snippets = _load_jsonl(parallel_source / "supplementary_snippets.jsonl")

        assert _stable_selection(serial_selection) == _stable_selection(parallel_selection), slug
        assert serial_blocks == parallel_blocks, slug
        assert serial_snippets == parallel_snippets, slug
        assert serial_selection["selected_candidate"] is not None, slug
        assert serial_selection["confidence"] in {"high", "medium", "low"}, slug
        assert len(serial_blocks) >= 1, slug
