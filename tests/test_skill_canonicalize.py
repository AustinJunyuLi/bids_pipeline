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
        actors_payload = {"actors": [], "count_assertions": [], "unresolved_mentions": []}

    refs: list[dict] = []
    for actor in actors_payload.get("actors", []):
        refs.extend(actor.get("evidence_refs", []))
    for assertion in actors_payload.get("count_assertions", []):
        refs.extend(assertion.get("evidence_refs", []))
    for event in events:
        refs.extend(event.get("evidence_refs", []))

    block_texts: dict[str, list[str]] = {}
    evidence_items: list[dict] = []
    for ref in refs:
        block_id = ref.get("block_id")
        anchor_text = ref.get("anchor_text") or "placeholder source text"
        if block_id:
            block_texts.setdefault(block_id, []).append(anchor_text)
        if ref.get("evidence_id"):
            evidence_items.append(
                {
                    "evidence_id": ref["evidence_id"],
                    "document_id": "DOC001",
                    "accession_number": "DOC001",
                    "filing_type": "DEFM14A",
                    "start_line": 1,
                    "end_line": 1,
                    "raw_text": anchor_text,
                    "evidence_type": "dated_action",
                    "confidence": "high",
                    "matched_terms": [anchor_text],
                    "date_text": None,
                    "actor_hint": None,
                    "value_hint": None,
                    "note": None,
                }
            )

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


def _actor(
    actor_id: str,
    canonical_name: str,
    *,
    role: str = "bidder",
    bidder_kind: str | None = "financial",
    advised_actor_id: str | None = None,
    evidence_refs: list[dict] | None = None,
    aliases: list[str] | None = None,
    notes: list[str] | None = None,
) -> dict:
    return {
        "actor_id": actor_id,
        "display_name": canonical_name.title(),
        "canonical_name": canonical_name,
        "aliases": aliases or [],
        "role": role,
        "advisor_kind": None,
        "advised_actor_id": advised_actor_id,
        "bidder_kind": bidder_kind,
        "listing_status": "private",
        "geography": "domestic",
        "is_grouped": False,
        "group_size": None,
        "group_label": None,
        "evidence_refs": evidence_refs or [{"block_id": "B001", "evidence_id": None, "anchor_text": "x"}],
        "notes": notes or [],
    }


def test_dedup_actors_merges_duplicates(tmp_path: Path) -> None:
    actors_payload = {
        "actors": [
            _actor(
                "party_a_1",
                "PARTY A",
                evidence_refs=[
                    {"block_id": "B001", "evidence_id": None, "anchor_text": "Party A contacted the company"},
                    {"block_id": "B002", "evidence_id": None, "anchor_text": "Party A signed an NDA"},
                ],
            ),
            _actor(
                "party_a_2",
                "PARTY A",
                evidence_refs=[
                    {"block_id": "B003", "evidence_id": None, "anchor_text": "Party A submitted an indication"},
                ],
            ),
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }
    event = _evt(
        "evt_001",
        "proposal",
        actor_ids=["party_a_2"],
        block_id="B003",
        summary="Party A submitted an indication.",
    )
    event["invited_actor_ids"] = ["party_a_2"]
    event["executed_with_actor_id"] = "party_a_2"

    _write_canon_fixture(tmp_path, actors_payload=actors_payload, events=[event])
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    actors_result = json.loads(paths.actors_raw_path.read_text(encoding="utf-8"))
    events_result = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))
    log = json.loads(paths.canonicalize_log_path.read_text(encoding="utf-8"))

    assert [actor["actor_id"] for actor in actors_result["actors"]] == ["party_a_1"]
    assert log["actor_dedup_log"] == {"party_a_2": "party_a_1"}
    assert events_result["events"][0]["actor_ids"] == ["party_a_1"]
    assert events_result["events"][0]["invited_actor_ids"] == ["party_a_1"]
    assert events_result["events"][0]["executed_with_actor_id"] == "party_a_1"


def test_dedup_actors_different_role_not_merged(tmp_path: Path) -> None:
    actors_payload = {
        "actors": [
            _actor("party_a_bidder", "PARTY A", role="bidder", bidder_kind="financial"),
            _actor("party_a_advisor", "PARTY A", role="advisor", bidder_kind=None),
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }

    _write_canon_fixture(
        tmp_path,
        actors_payload=actors_payload,
        events=[_evt("evt_001", "executed", actor_ids=["party_a_bidder"])],
    )
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    actors_result = json.loads(paths.actors_raw_path.read_text(encoding="utf-8"))

    assert [actor["actor_id"] for actor in actors_result["actors"]] == [
        "party_a_bidder",
        "party_a_advisor",
    ]


def test_dedup_actors_evidence_merged(tmp_path: Path) -> None:
    actors_payload = {
        "actors": [
            _actor(
                "party_a_1",
                "PARTY A",
                evidence_refs=[
                    {"block_id": "B001", "evidence_id": None, "anchor_text": "Party A first mention"},
                    {"block_id": "B002", "evidence_id": None, "anchor_text": "Party A second mention"},
                ],
                aliases=["Sponsor A"],
                notes=["first note"],
            ),
            _actor(
                "party_a_2",
                "PARTY A",
                evidence_refs=[
                    {"block_id": "B002", "evidence_id": None, "anchor_text": "Party A second mention"},
                    {"block_id": "B003", "evidence_id": None, "anchor_text": "Party A third mention"},
                ],
                aliases=["Sponsor A", "Fund A"],
                notes=["second note"],
            ),
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }

    _write_canon_fixture(
        tmp_path,
        actors_payload=actors_payload,
        events=[_evt("evt_001", "nda", actor_ids=["party_a_1"])],
    )
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    actors_result = json.loads(paths.actors_raw_path.read_text(encoding="utf-8"))

    assert actors_result["actors"][0]["evidence_span_ids"] == [
        "span_0001",
        "span_0002",
        "span_0003",
    ]
    assert actors_result["actors"][0]["aliases"] == ["Sponsor A", "Fund A"]
    assert actors_result["actors"][0]["notes"] == ["first note", "second note"]


def test_dedup_actors_no_duplicates_passthrough(tmp_path: Path) -> None:
    actors_payload = {
        "actors": [_actor("party_a", "PARTY A")],
        "count_assertions": [],
        "unresolved_mentions": [],
    }

    _write_canon_fixture(
        tmp_path,
        actors_payload=actors_payload,
        events=[_evt("evt_001", "nda", actor_ids=["party_a"])],
    )
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    actors_result = json.loads(paths.actors_raw_path.read_text(encoding="utf-8"))
    events_result = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))
    log = json.loads(paths.canonicalize_log_path.read_text(encoding="utf-8"))

    assert [actor["actor_id"] for actor in actors_result["actors"]] == ["party_a"]
    assert events_result["events"][0]["actor_ids"] == ["party_a"]
    assert log["actor_dedup_log"] == {}


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


def test_nda_gate_removes_drop_when_nda_comes_later(tmp_path: Path) -> None:
    events = [
        _evt("evt_001", "drop", actor_ids=["bidder_a"], date="2016-06-03"),
        _evt("evt_002", "nda", actor_ids=["bidder_a"], date="2016-06-04"),
        _evt("evt_003", "executed", actor_ids=["bidder_a"], date="2016-07-13"),
    ]
    _write_canon_fixture(tmp_path, events=events)
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    result = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))

    assert len(result["events"]) == 2
    assert not any(e["event_id"] == "evt_001" for e in result["events"])


def test_recover_unnamed_party_from_count_gap(tmp_path: Path) -> None:
    actors_payload = {
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
                "evidence_refs": [{"block_id": "B001", "evidence_id": None, "anchor_text": "x"}],
                "notes": [],
            },
        ],
        "count_assertions": [
            {
                "subject": "nda_signed_financial_buyers",
                "count": 2,
                "evidence_refs": [{"block_id": "B030", "evidence_id": None, "anchor_text": "two financial sponsors"}],
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

    # Placeholder actor created
    assert len(actors_result["actors"]) == 2
    placeholder = [a for a in actors_result["actors"] if a["actor_id"].startswith("placeholder_")]
    assert len(placeholder) == 1
    assert placeholder[0]["bidder_kind"] == "financial"
    assert placeholder[0]["evidence_span_ids"] == ["span_0002"]

    placeholder_nda = next(
        e
        for e in events_result["events"]
        if e["event_type"] == "nda" and placeholder[0]["actor_id"] in e["actor_ids"]
    )
    assert placeholder_nda["evidence_span_ids"] == ["span_0002"]
    assert not any(
        e["event_type"] == "drop" and placeholder[0]["actor_id"] in e["actor_ids"]
        for e in events_result["events"]
    )
    assert len(log["recovery_log"]) == 1
    assert log["recovery_log"][0]["drop_event_skipped"] is True


def test_recover_unnamed_party_fail_closed_no_unresolved_mention(tmp_path: Path) -> None:
    actors_payload = {
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
                "evidence_refs": [{"block_id": "B001", "evidence_id": None, "anchor_text": "x"}],
                "notes": [],
            },
        ],
        "count_assertions": [
            {
                "subject": "nda_signed_financial_buyers",
                "count": 2,
                "evidence_refs": [{"block_id": "B030", "evidence_id": None, "anchor_text": "two financial sponsors"}],
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


def test_canonicalize_rejects_mismatched_block_and_evidence_refs(tmp_path: Path) -> None:
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
                "evidence_refs": [
                    {
                        "block_id": "B002",
                        "evidence_id": "DOC001:E0001",
                        "anchor_text": "anchor one",
                    }
                ],
                "notes": [],
            }
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }
    events_payload = {
        "events": [_evt("evt_001", "executed", actor_ids=["bidder_a"], date="2016-07-13")],
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
    _write_canon_fixture(tmp_path, events=events)
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    paths.spans_path.unlink()

    with pytest.raises(FileNotFoundError, match="spans"):
        load_extract_artifacts(paths)


def test_relative_dates_anchor_using_chronology_order_not_input_order(tmp_path: Path) -> None:
    absolute = _evt(
        "evt_001",
        "nda",
        actor_ids=["bidder_a"],
        block_id="B001",
        date="2016-07-01",
        summary="Bidder A signed an NDA.",
    )
    relative = _evt(
        "evt_002",
        "proposal",
        actor_ids=["bidder_a"],
        block_id="B002",
        date="two days later",
        summary="Bidder A submitted a proposal.",
    )

    _write_canon_fixture(tmp_path, events=[relative, absolute])
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    result = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))

    by_id = {event["event_id"]: event for event in result["events"]}
    assert by_id["evt_002"]["date"]["sort_date"] == "2016-07-03"
    assert by_id["evt_002"]["date"]["anchor_event_id"] == "evt_001"


def test_relative_date_without_chronology_anchor_fails(tmp_path: Path) -> None:
    _write_canon_fixture(
        tmp_path,
        events=[
            _evt(
                "evt_001",
                "proposal",
                actor_ids=["bidder_a"],
                block_id="B001",
                date="two days later",
                summary="Bidder A submitted a proposal.",
            )
        ],
    )

    with pytest.raises(ValueError, match="Relative date"):
        run_canonicalize("imprivata", project_root=tmp_path)


def test_nda_gate_uses_chronology_order_not_input_order(tmp_path: Path) -> None:
    nda = _evt(
        "evt_001",
        "nda",
        actor_ids=["bidder_a"],
        block_id="B001",
        date="2016-06-02",
        summary="Bidder A signed an NDA.",
    )
    drop = _evt(
        "evt_002",
        "drop",
        actor_ids=["bidder_a"],
        block_id="B002",
        date="2016-06-03",
        summary="Bidder A dropped out.",
    )
    executed = _evt(
        "evt_003",
        "executed",
        actor_ids=["bidder_a"],
        block_id="B003",
        date="2016-07-13",
        summary="Deal executed.",
    )

    _write_canon_fixture(tmp_path, events=[drop, nda, executed])
    run_canonicalize("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    result = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))

    assert any(event["event_id"] == "evt_002" for event in result["events"])
