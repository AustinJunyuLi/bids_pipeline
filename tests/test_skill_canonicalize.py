"""Tests for the deterministic canonicalize stage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_pipeline.canonicalize import run_canonicalize
from skill_pipeline.extract_artifacts import load_extract_artifacts
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
    raw_dir = tmp_path / "raw" / slug
    filings_dir = raw_dir / "filings"
    deals_source_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)
    filings_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "seeds.csv").write_text(
        "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
        f"{slug},TARGET,ACQUIRER,2016-07-13,https://example.com,false\n",
        encoding="utf-8",
    )

    if actors_payload is None:
        actors_payload = {
            "quotes": [],
            "actors": [],
            "count_assertions": [],
            "unresolved_mentions": [],
        }

    event_quotes: list[dict[str, str]] = []
    for event in events:
        quote_source = event.pop("_quote_source", None)
        if quote_source is None:
            continue
        event_quotes.append(
            {
                "quote_id": quote_source["quote_id"],
                "block_id": quote_source["block_id"],
                "text": quote_source["text"],
            }
        )

    block_texts: dict[str, list[str]] = {}
    evidence_items: list[dict] = []
    for quote in actors_payload.get("quotes", []) + event_quotes:
        block_id = quote.get("block_id")
        anchor_text = quote.get("text") or "placeholder source text"
        if block_id:
            block_texts.setdefault(block_id, []).append(anchor_text)

    if not block_texts:
        block_texts["B001"] = ["placeholder source text"]

    chronology_blocks: list[dict] = []
    filing_lines: list[str] = []
    for ordinal, block_id in enumerate(sorted(block_texts), start=1):
        line_text = " ".join(dict.fromkeys(block_texts[block_id]))
        if not line_text.strip():
            line_text = f"{block_id} placeholder source text"
        chronology_blocks.append(
            {
                "block_id": block_id,
                "document_id": "DOC001",
                "ordinal": ordinal,
                "start_line": ordinal,
                "end_line": ordinal,
                "raw_text": line_text,
                "clean_text": line_text,
                "is_heading": False,
                "page_break_before": False,
                "page_break_after": False,
                "date_mentions": [],
                "entity_mentions": [],
                "evidence_density": 0,
                "temporal_phase": "other",
            }
        )
        filing_lines.append(line_text)

    evidence_jsonl = "\n".join(json.dumps(item) for item in evidence_items)
    if evidence_jsonl:
        evidence_jsonl += "\n"
    (deals_source_dir / "chronology_blocks.jsonl").write_text(
        "\n".join(json.dumps(block) for block in chronology_blocks) + "\n",
        encoding="utf-8",
    )
    (deals_source_dir / "evidence_items.jsonl").write_text(evidence_jsonl, encoding="utf-8")
    (raw_dir / "document_registry.json").write_text(
        json.dumps(
            {
                "artifact_type": "raw_document_registry",
                "documents": [
                    {
                        "document_id": "DOC001",
                        "accession_number": "DOC001",
                        "filing_type": "DEFM14A",
                        "txt_path": f"raw/{slug}/filings/DOC001.txt",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (filings_dir / "DOC001.txt").write_text("\n".join(filing_lines) + "\n", encoding="utf-8")

    (extract_dir / "actors_raw.json").write_text(json.dumps(actors_payload), encoding="utf-8")
    (extract_dir / "events_raw.json").write_text(
        json.dumps(
            {
                "quotes": event_quotes,
                "events": events,
                "exclusions": [],
                "coverage_notes": [],
            }
        ),
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
        "quote_ids": [f"Q_{evt_id}"],
        "_quote_source": {
            "quote_id": f"Q_{evt_id}",
            "block_id": block_id,
            "text": "x",
        },
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


def test_nda_gate_removes_drop_before_later_nda(tmp_path: Path) -> None:
    events = [
        _evt("evt_001", "drop", actor_ids=["bidder_b"], date="2016-06-03"),
        _evt("evt_002", "nda", actor_ids=["bidder_b"]),
        _evt("evt_003", "executed", actor_ids=["bidder_a"], date="2016-07-13"),
    ]
    _write_canon_fixture(tmp_path, events=events)
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    result = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))

    assert len(result["events"]) == 2
    assert not any(e["event_id"] == "evt_001" for e in result["events"])


def test_nda_gate_resets_on_restarted(tmp_path: Path) -> None:
    events = [
        _evt("evt_001", "nda", actor_ids=["bidder_a"], date="2016-06-01"),
        _evt("evt_002", "restarted", actor_ids=["bidder_a"], date="2016-06-02"),
        _evt("evt_003", "drop", actor_ids=["bidder_a"], date="2016-06-03"),
        _evt("evt_004", "nda", actor_ids=["bidder_a"], date="2016-06-04"),
        _evt("evt_005", "drop", actor_ids=["bidder_a"], date="2016-06-05"),
        _evt("evt_006", "executed", actor_ids=["bidder_a"], date="2016-07-13"),
    ]
    _write_canon_fixture(tmp_path, events=events)
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    result = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))

    assert len(result["events"]) == 5
    assert not any(e["event_id"] == "evt_003" for e in result["events"])
    assert any(e["event_id"] == "evt_005" for e in result["events"])


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


def test_recover_unnamed_party_from_count_gap(tmp_path: Path) -> None:
    actors_payload = {
        "quotes": [
            {"quote_id": "Q001", "block_id": "B001", "text": "x"},
            {
                "quote_id": "Q002",
                "block_id": "B030",
                "text": "two financial sponsors",
            },
        ],
        "actors": [
            {
                "actor_id": "bidder_a",
                "display_name": "Sponsor A",
                "canonical_name": "SPONSOR A",
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
                "quote_ids": ["Q001"],
                "notes": [],
            },
        ],
        "count_assertions": [
            {
                "subject": "nda_signed_financial_buyers",
                "count": 2,
                "quote_ids": ["Q002"],
            },
        ],
        "unresolved_mentions": [
            "One financial sponsor executed a confidentiality agreement but declined interest shortly thereafter."
        ],
    }
    events = [
        _evt("evt_001", "nda", actor_ids=["bidder_a"]),
        _evt("evt_002", "executed", actor_ids=["bidder_a"], date="2016-07-13"),
    ]
    _write_canon_fixture(tmp_path, actors_payload=actors_payload, events=events)
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    actors_result = json.loads(paths.actors_raw_path.read_text(encoding="utf-8"))
    events_result = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))
    log = json.loads(paths.canonicalize_log_path.read_text(encoding="utf-8"))

    assert len(actors_result["actors"]) == 1
    assert not any(a["actor_id"].startswith("placeholder_") for a in actors_result["actors"])
    assert len(events_result["events"]) == 2
    assert not any(e["event_id"].startswith("placeholder_") for e in events_result["events"])
    assert len(log["recovery_log"]) == 1
    gap_entry = log["recovery_log"][0]
    assert gap_entry["status"] == "blocked_unresolved_gap"
    assert gap_entry["gap"] == 1
    assert gap_entry["candidate_mentions"] == [
        "One financial sponsor executed a confidentiality agreement but declined interest shortly thereafter."
    ]


def test_recover_unnamed_party_uses_highest_count_assertion(tmp_path: Path) -> None:
    actors_payload = {
        "quotes": [
            {"quote_id": "Q001", "block_id": "B001", "text": "x"},
            {
                "quote_id": "Q002",
                "block_id": "B029",
                "text": "one financial sponsor",
            },
            {
                "quote_id": "Q003",
                "block_id": "B030",
                "text": "three financial sponsors",
            },
        ],
        "actors": [
            {
                "actor_id": "bidder_a",
                "display_name": "Sponsor A",
                "canonical_name": "SPONSOR A",
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
                "quote_ids": ["Q001"],
                "notes": [],
            },
        ],
        "count_assertions": [
            {
                "subject": "nda_signed_financial_buyers",
                "count": 1,
                "quote_ids": ["Q002"],
            },
            {
                "subject": "nda_signed_financial_buyers",
                "count": 3,
                "quote_ids": ["Q003"],
            },
        ],
        "unresolved_mentions": [
            "One financial sponsor executed a confidentiality agreement but declined interest shortly thereafter."
        ],
    }
    events = [
        _evt("evt_001", "nda", actor_ids=["bidder_a"]),
        _evt("evt_002", "executed", actor_ids=["bidder_a"], date="2016-07-13"),
    ]
    _write_canon_fixture(tmp_path, actors_payload=actors_payload, events=events)
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    log = json.loads(paths.canonicalize_log_path.read_text(encoding="utf-8"))

    assert len(log["recovery_log"]) == 1
    gap_entry = log["recovery_log"][0]
    assert gap_entry["status"] == "blocked_unresolved_gap"
    assert gap_entry["asserted_count"] == 3
    assert gap_entry["gap"] == 2


def test_recover_unnamed_party_fail_closed_no_unresolved_mention(tmp_path: Path) -> None:
    actors_payload = {
        "quotes": [
            {"quote_id": "Q001", "block_id": "B001", "text": "x"},
            {
                "quote_id": "Q002",
                "block_id": "B030",
                "text": "two financial sponsors",
            },
        ],
        "actors": [
            {
                "actor_id": "bidder_a",
                "display_name": "Sponsor A",
                "canonical_name": "SPONSOR A",
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
                "quote_ids": ["Q001"],
                "notes": [],
            },
        ],
        "count_assertions": [
            {
                "subject": "nda_signed_financial_buyers",
                "count": 2,
                "quote_ids": ["Q002"],
            },
        ],
        "unresolved_mentions": [],  # No matching mention -> fail closed
    }
    events = [
        _evt("evt_001", "nda", actor_ids=["bidder_a"]),
        _evt("evt_002", "executed", actor_ids=["bidder_a"], date="2016-07-13"),
    ]
    _write_canon_fixture(tmp_path, actors_payload=actors_payload, events=events)
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    actors_result = json.loads(paths.actors_raw_path.read_text(encoding="utf-8"))
    assert len(actors_result["actors"]) == 1  # No placeholder


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


def test_canonicalize_rejects_unknown_quote_block_id(tmp_path: Path) -> None:
    slug = "imprivata"
    data_dir = tmp_path / "data"
    deals_source_dir = data_dir / "deals" / slug / "source"
    extract_dir = data_dir / "skill" / slug / "extract"
    raw_dir = tmp_path / "raw" / slug
    filings_dir = raw_dir / "filings"
    deals_source_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)
    filings_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "seeds.csv").write_text(
        "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
        f"{slug},TARGET,ACQUIRER,2016-07-13,https://example.com,false\n",
        encoding="utf-8",
    )
    chronology_blocks = [
        {
            "block_id": "B001",
            "document_id": "DOC001",
            "ordinal": 1,
            "start_line": 1,
            "end_line": 1,
            "raw_text": "anchor one",
            "clean_text": "anchor one",
            "is_heading": False,
            "page_break_before": False,
            "page_break_after": False,
            "date_mentions": [],
            "entity_mentions": [],
            "evidence_density": 0,
            "temporal_phase": "other",
        },
        {
            "block_id": "B002",
            "document_id": "DOC001",
            "ordinal": 2,
            "start_line": 2,
            "end_line": 2,
            "raw_text": "anchor two",
            "clean_text": "anchor two",
            "is_heading": False,
            "page_break_before": False,
            "page_break_after": False,
            "date_mentions": [],
            "entity_mentions": [],
            "evidence_density": 0,
            "temporal_phase": "other",
        },
    ]
    evidence_items = [
        {
            "evidence_id": "DOC001:E0001",
            "document_id": "DOC001",
            "accession_number": "DOC001",
            "filing_type": "DEFM14A",
            "start_line": 1,
            "end_line": 1,
            "raw_text": "anchor one",
            "evidence_type": "dated_action",
            "confidence": "high",
            "matched_terms": ["anchor one"],
            "date_text": None,
            "actor_hint": None,
            "value_hint": None,
            "note": None,
        }
    ]
    actors_payload = {
        "quotes": [
            {
                "quote_id": "Q001",
                "block_id": "B999",
                "text": "anchor one",
            }
        ],
        "actors": [
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
                "quote_ids": ["Q001"],
                "notes": [],
            }
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }
    events_payload = {
        "quotes": [
            {
                "quote_id": "Q101",
                "block_id": "B001",
                "text": "x",
            }
        ],
        "events": [
            {
                "event_id": "evt_001",
                "event_type": "executed",
                "date": {"raw_text": "2016-07-13", "normalized_hint": "2016-07-13"},
                "actor_ids": ["bidder_a"],
                "summary": "x",
                "quote_ids": ["Q101"],
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
        ],
        "exclusions": [],
        "coverage_notes": [],
    }

    (deals_source_dir / "chronology_blocks.jsonl").write_text(
        "\n".join(json.dumps(block) for block in chronology_blocks) + "\n",
        encoding="utf-8",
    )
    (deals_source_dir / "evidence_items.jsonl").write_text(
        "\n".join(json.dumps(item) for item in evidence_items) + "\n",
        encoding="utf-8",
    )
    (raw_dir / "document_registry.json").write_text(
        json.dumps(
            {
                "artifact_type": "raw_document_registry",
                "documents": [
                    {
                        "document_id": "DOC001",
                        "accession_number": "DOC001",
                        "filing_type": "DEFM14A",
                        "txt_path": f"raw/{slug}/filings/DOC001.txt",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (filings_dir / "DOC001.txt").write_text("anchor one\nanchor two\n", encoding="utf-8")
    (extract_dir / "actors_raw.json").write_text(json.dumps(actors_payload), encoding="utf-8")
    (extract_dir / "events_raw.json").write_text(json.dumps(events_payload), encoding="utf-8")

    with pytest.raises(ValueError, match="block_id"):
        run_canonicalize(slug, project_root=tmp_path)


def test_canonicalize_rejects_duplicate_quote_ids(tmp_path: Path) -> None:
    actors_payload = {
        "quotes": [
            {"quote_id": "Q001", "block_id": "B001", "text": "Bidder A"},
            {"quote_id": "Q001", "block_id": "B002", "text": "Bidder B"},
        ],
        "actors": [
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
                "quote_ids": ["Q001"],
                "notes": [],
            }
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }
    events = [_evt("evt_001", "executed", actor_ids=["bidder_a"], date="2016-07-13")]
    _write_canon_fixture(tmp_path, actors_payload=actors_payload, events=events)

    with pytest.raises(ValueError, match="Duplicate quote_id"):
        run_canonicalize("imprivata", project_root=tmp_path)


def test_canonicalize_cross_array_quote_ids_are_renumbered_and_logged(tmp_path: Path) -> None:
    actors_payload = {
        "quotes": [
            {"quote_id": "Q001", "block_id": "B001", "text": "Bidder A signed an NDA"},
        ],
        "actors": [
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
                "quote_ids": ["Q001"],
                "notes": [],
            },
        ],
        "count_assertions": [
            {
                "subject": "nda_signed_financial_buyers",
                "count": 1,
                "quote_ids": ["Q001"],
            },
        ],
        "unresolved_mentions": [],
    }
    event = _evt("evt_001", "nda", actor_ids=["bidder_a"], block_id="B002", summary="Bidder A signed an NDA")
    event["quote_ids"] = ["Q001"]
    event["_quote_source"] = {
        "quote_id": "Q001",
        "block_id": "B002",
        "text": "Bidder A signed an NDA",
    }
    events = [
        event,
        _evt("evt_002", "executed", actor_ids=["bidder_a"], date="2016-07-13", block_id="B003"),
    ]
    _write_canon_fixture(tmp_path, actors_payload=actors_payload, events=events)

    run_canonicalize("imprivata", project_root=tmp_path)

    paths = build_skill_paths("imprivata", project_root=tmp_path)
    actors_result = json.loads(paths.actors_raw_path.read_text(encoding="utf-8"))
    events_result = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))
    log = json.loads(paths.canonicalize_log_path.read_text(encoding="utf-8"))

    actor_span_ids = actors_result["actors"][0]["evidence_span_ids"]
    assertion_span_ids = actors_result["count_assertions"][0]["evidence_span_ids"]
    nda_event = next(event for event in events_result["events"] if event["event_id"] == "evt_001")

    assert actor_span_ids == ["span_0001"]
    assert assertion_span_ids == ["span_0001"]
    assert nda_event["evidence_span_ids"] == ["span_0002"]
    assert log["quote_id_renumber_log"]["actor_quotes"] == {"Q001": "qa_001"}
    assert log["quote_id_renumber_log"]["event_quotes"]["Q001"] == "qe_001"
    assert all(event["evidence_span_ids"] for event in events_result["events"])


def test_canonicalize_logs_orphaned_quotes(tmp_path: Path) -> None:
    actors_payload = {
        "quotes": [
            {"quote_id": "Q001", "block_id": "B001", "text": "Bidder A"},
            {"quote_id": "Q999", "block_id": "B002", "text": "Unused quote"},
        ],
        "actors": [
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
                "quote_ids": ["Q001"],
                "notes": [],
            }
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }
    events = [_evt("evt_001", "executed", actor_ids=["bidder_a"], date="2016-07-13")]
    _write_canon_fixture(tmp_path, actors_payload=actors_payload, events=events)
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    log = json.loads(paths.canonicalize_log_path.read_text(encoding="utf-8"))

    assert log["orphaned_quotes"] == ["qa_002"]
    assert log["quote_id_renumber_log"]["actor_quotes"]["Q999"] == "qa_002"


def test_dedup_preserves_events_with_conflicting_structured_fields(tmp_path: Path) -> None:
    first = _evt("evt_001", "proposal", actor_ids=["bidder_a"], block_id="B064", summary="first")
    second = _evt("evt_002", "proposal", actor_ids=["bidder_a"], block_id="B064", summary="second")
    first["terms"] = {
        "per_share": 25.0,
        "range_low": None,
        "range_high": None,
        "enterprise_value": None,
        "consideration_type": "cash",
    }
    second["terms"] = {
        "per_share": 27.0,
        "range_low": None,
        "range_high": None,
        "enterprise_value": None,
        "consideration_type": "cash",
    }
    events = [
        first,
        second,
        _evt("evt_003", "executed", actor_ids=["bidder_a"], date="2016-07-13"),
    ]

    _write_canon_fixture(tmp_path, events=events)
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    result = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))

    proposal_events = [event for event in result["events"] if event["event_type"] == "proposal"]
    assert len(proposal_events) == 2


def test_load_extract_artifacts_requires_spans_for_canonical_payloads(tmp_path: Path) -> None:
    events = [
        _evt("evt_001", "proposal", actor_ids=["bidder_a"], block_id="B064"),
        _evt("evt_002", "executed", actor_ids=["bidder_a"], date="2016-07-13"),
    ]
    actors_payload = {
        "quotes": [
            {
                "quote_id": "Q001",
                "block_id": "B064",
                "text": "Bidder A",
            }
        ],
        "actors": [
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
                "quote_ids": ["Q001"],
                "notes": [],
            },
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }
    _write_canon_fixture(tmp_path, actors_payload=actors_payload, events=events)
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    paths.spans_path.unlink()

    with pytest.raises(FileNotFoundError, match="spans"):
        load_extract_artifacts(paths)


def test_canonicalize_is_idempotent_on_existing_canonical_extract(tmp_path: Path) -> None:
    events = [
        _evt("evt_001", "drop", actor_ids=["bidder_a"], block_id="B064"),
        _evt("evt_002", "nda", actor_ids=["bidder_a"], block_id="B065"),
        _evt("evt_003", "executed", actor_ids=["bidder_a"], date="2016-07-13", block_id="B066"),
    ]
    actors_payload = {
        "quotes": [
            {
                "quote_id": "Q001",
                "block_id": "B064",
                "text": "Bidder A",
            }
        ],
        "actors": [
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
                "quote_ids": ["Q001"],
                "notes": [],
            },
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }
    _write_canon_fixture(tmp_path, actors_payload=actors_payload, events=events)

    run_canonicalize("imprivata", project_root=tmp_path)
    run_canonicalize("imprivata", project_root=tmp_path)

    paths = build_skill_paths("imprivata", project_root=tmp_path)
    result = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))
    log = json.loads(paths.canonicalize_log_path.read_text(encoding="utf-8"))
    assert [event["event_id"] for event in result["events"]] == ["evt_002", "evt_003"]
    assert log["quote_id_renumber_log"] == {
        "actor_quotes": {},
        "event_quotes": {},
    }
