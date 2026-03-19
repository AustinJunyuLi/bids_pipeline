"""Tests for the deterministic canonicalize stage."""

from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.canonicalize import run_canonicalize
from skill_pipeline.paths import build_skill_paths


def _write_canon_fixture(
    tmp_path: Path,
    *,
    slug: str = "imprivata",
    actors_payload: dict | None = None,
    events: list[dict],
) -> None:
    data_dir = tmp_path / "data"
    deals_source_dir = data_dir / "deals" / slug / "source"
    extract_dir = data_dir / "skill" / slug / "extract"
    deals_source_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "seeds.csv").write_text(
        "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
        f"{slug},TARGET,ACQUIRER,2016-07-13,https://example.com,false\n",
        encoding="utf-8",
    )
    (deals_source_dir / "chronology_blocks.jsonl").write_text("{}\n", encoding="utf-8")
    (deals_source_dir / "evidence_items.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "raw" / slug).mkdir(parents=True, exist_ok=True)
    (tmp_path / "raw" / slug / "document_registry.json").write_text("{}", encoding="utf-8")

    if actors_payload is None:
        actors_payload = {"actors": [], "count_assertions": [], "unresolved_mentions": []}
    (extract_dir / "actors_raw.json").write_text(json.dumps(actors_payload), encoding="utf-8")
    (extract_dir / "events_raw.json").write_text(
        json.dumps({"events": events, "exclusions": [], "coverage_notes": []}),
        encoding="utf-8",
    )


def _evt(
    evt_id: str,
    event_type: str,
    *,
    date: str = "2016-07-08",
    actor_ids: list[str] | None = None,
    block_id: str = "B001",
    summary: str = "x",
) -> dict:
    return {
        "event_id": evt_id,
        "event_type": event_type,
        "date": {"raw_text": date, "normalized_hint": date},
        "actor_ids": actor_ids or [],
        "summary": summary,
        "evidence_refs": [{"block_id": block_id, "evidence_id": None, "anchor_text": "x"}],
        "terms": None,
        "formality_signals": None,
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


def test_dedup_collapses_same_type_date_actor_block(tmp_path: Path) -> None:
    events = [
        _evt("evt_001", "final_round_ann", block_id="B036", summary="short"),
        _evt("evt_002", "final_round_ann", block_id="B036", summary="longer description"),
        _evt("evt_003", "executed", actor_ids=["a"], date="2016-07-13"),
    ]
    _write_canon_fixture(tmp_path, events=events)
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    result = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))

    assert len(result["events"]) == 2
    surviving = [e for e in result["events"] if e["event_type"] == "final_round_ann"]
    assert len(surviving) == 1
    assert surviving[0]["summary"] == "longer description"


def test_dedup_preserves_different_actors(tmp_path: Path) -> None:
    events = [
        _evt("evt_001", "proposal", actor_ids=["bidder_a"], block_id="B064"),
        _evt("evt_002", "proposal", actor_ids=["bidder_b"], block_id="B064"),
    ]
    _write_canon_fixture(tmp_path, events=events)
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    result = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))

    assert len(result["events"]) == 2


def test_nda_gate_removes_drop_without_prior_nda(tmp_path: Path) -> None:
    events = [
        _evt("evt_001", "nda", actor_ids=["bidder_a"]),
        _evt("evt_002", "drop", actor_ids=["bidder_b"], date="2016-06-03"),
        _evt("evt_003", "executed", actor_ids=["bidder_a"], date="2016-07-13"),
    ]
    _write_canon_fixture(tmp_path, events=events)
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    result = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))

    assert len(result["events"]) == 2
    assert not any(e["event_id"] == "evt_002" for e in result["events"])


def test_nda_gate_preserves_drop_with_prior_nda(tmp_path: Path) -> None:
    events = [
        _evt("evt_001", "nda", actor_ids=["bidder_a"]),
        _evt("evt_002", "drop", actor_ids=["bidder_a"], date="2016-06-03"),
        _evt("evt_003", "executed", actor_ids=["bidder_a"], date="2016-07-13"),
    ]
    _write_canon_fixture(tmp_path, events=events)
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    result = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))

    assert len(result["events"]) == 3


def test_nda_gate_removes_drop_with_empty_actor_ids(tmp_path: Path) -> None:
    """Drops with empty actor_ids are unnamed parties without NDAs — remove them."""
    events = [
        _evt("evt_001", "nda", actor_ids=["bidder_a"]),
        _evt("evt_002", "drop", actor_ids=[], date="2016-06-03"),
        _evt("evt_003", "executed", actor_ids=["bidder_a"], date="2016-07-13"),
    ]
    _write_canon_fixture(tmp_path, events=events)
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    result = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))

    assert len(result["events"]) == 2
    assert not any(e["event_id"] == "evt_002" for e in result["events"])
