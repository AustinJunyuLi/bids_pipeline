"""Tests for the deterministic enrich-core stage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_pipeline.canonicalize import run_canonicalize
from skill_pipeline.enrich_core import run_enrich_core
from skill_pipeline.paths import build_skill_paths


def _base_event(evt_id: str, event_type: str, **overrides: object) -> dict:
    """Minimal event template for fixtures."""
    quote_id = f"Q_{evt_id}"
    evt = {
        "event_id": evt_id,
        "event_type": event_type,
        "date": {"raw_text": "2016-06", "normalized_hint": "2016-06"},
        "actor_ids": [],
        "summary": "",
        "quote_ids": [quote_id],
        "_quote_source": {
            "quote_id": quote_id,
            "block_id": "B001",
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
    evt.update(overrides)
    return evt


def _event_payload(events: list[dict]) -> dict:
    quotes: list[dict[str, str]] = []
    materialized_events: list[dict] = []
    for event in events:
        event_payload = dict(event)
        quote_source = event_payload.pop("_quote_source", None)
        if quote_source is not None:
            quotes.append(quote_source)
        materialized_events.append(event_payload)
    return {"quotes": quotes, "events": materialized_events, "exclusions": [], "coverage_notes": []}


def _write_quote_first_extract_fixture(
    tmp_path: Path,
    *,
    slug: str,
    actors_payload: dict,
    events: list[dict],
    canonicalize: bool = True,
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
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n"
        ),
        encoding="utf-8",
    )

    events_payload = _event_payload(events)
    block_texts: dict[str, list[str]] = {}
    for quote in actors_payload.get("quotes", []) + events_payload.get("quotes", []):
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

    (deals_source_dir / "chronology_blocks.jsonl").write_text(
        "\n".join(json.dumps(block) for block in chronology_blocks) + "\n",
        encoding="utf-8",
    )
    (deals_source_dir / "evidence_items.jsonl").write_text("", encoding="utf-8")
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
    (extract_dir / "events_raw.json").write_text(json.dumps(events_payload), encoding="utf-8")

    if canonicalize:
        run_canonicalize(slug, project_root=tmp_path)


def _write_enrich_core_fixture(
    tmp_path: Path,
    *,
    slug: str = "imprivata",
    residual_only: bool = False,
    events_override: list[dict] | None = None,
) -> None:
    """Write minimal synthetic skill artifacts for enrich-core tests.

    Parameters:
        residual_only: True to create a proposal with no formality signals (residual case)
            and no rounds, so it becomes Uncertain and formal_boundary stays null.
        events_override: If provided, use these events instead of the default/residual sets.
    """
    actors_payload = {
        "quotes": [
            {
                "quote_id": "Q001",
                "block_id": "B001",
                "text": "Party A",
            }
        ],
        "actors": [
            {
                "actor_id": "party_a",
                "display_name": "Party A",
                "canonical_name": "PARTY A",
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

    # Residual proposal: no formality signals match rules 1-3
    residual_formality = {
        "contains_range": False,
        "mentions_indication_of_interest": False,
        "mentions_preliminary": False,
        "mentions_non_binding": False,
        "mentions_binding_offer": False,
        "includes_draft_merger_agreement": False,
        "includes_marked_up_agreement": False,
        "requested_binding_offer_via_process_letter": False,
        "after_final_round_announcement": False,
        "after_final_round_deadline": False,
        "is_subject_to_financing": None,
    }

    if events_override is not None:
        events = events_override
    elif residual_only:
        # Single cycle, one residual proposal, no rounds -> Uncertain, formal_boundary null
        events = [
            _base_event(
                "evt_001",
                "target_sale",
                date={"raw_text": "June 2016", "normalized_hint": "2016-06"},
                actor_ids=["party_a"],
                summary="Target initiated sale.",
                _quote_source={"quote_id": "Q_evt_001", "block_id": "B001", "text": "sale"},
            ),
            _base_event(
                "evt_002",
                "proposal",
                date={"raw_text": "July 5, 2016", "normalized_hint": "2016-07-05"},
                actor_ids=["party_a"],
                summary="Party A submitted a bid.",
                _quote_source={"quote_id": "Q_evt_002", "block_id": "B001", "text": "bid"},
                terms={
                    "per_share": 25.0,
                    "range_low": None,
                    "range_high": None,
                    "enterprise_value": None,
                    "consideration_type": "cash",
                },
                formality_signals=residual_formality,
            ),
            _base_event(
                "evt_003",
                "executed",
                date={"raw_text": "July 13, 2016", "normalized_hint": "2016-07-13"},
                actor_ids=["party_a"],
                summary="Deal executed.",
                _quote_source={"quote_id": "Q_evt_003", "block_id": "B001", "text": "executed"},
                executed_with_actor_id="party_a",
            ),
        ]
    else:
        # Extension round: final_round_ext_ann -> final_round_ext
        events = [
            _base_event(
                "evt_001",
                "target_sale",
                date={"raw_text": "June 2016", "normalized_hint": "2016-06"},
                actor_ids=["party_a"],
                summary="Target initiated sale.",
                _quote_source={"quote_id": "Q_evt_001", "block_id": "B001", "text": "sale"},
            ),
            _base_event(
                "evt_002",
                "nda",
                date={"raw_text": "June 15, 2016", "normalized_hint": "2016-06-15"},
                actor_ids=["party_a"],
                summary="Party A signed NDA.",
                _quote_source={"quote_id": "Q_evt_002", "block_id": "B001", "text": "NDA"},
                nda_signed=True,
            ),
            _base_event(
                "evt_003",
                "final_round_ext_ann",
                date={"raw_text": "July 1, 2016", "normalized_hint": "2016-07-01"},
                summary="Target announced extension round.",
                _quote_source={"quote_id": "Q_evt_003", "block_id": "B001", "text": "extension"},
                round_scope="formal",
                invited_actor_ids=["party_a"],
            ),
            _base_event(
                "evt_004",
                "final_round_ext",
                date={"raw_text": "July 5, 2016", "normalized_hint": "2016-07-05"},
                summary="Extension round deadline.",
                _quote_source={"quote_id": "Q_evt_004", "block_id": "B001", "text": "deadline"},
                deadline_date={"raw_text": "July 5, 2016", "normalized_hint": "2016-07-05"},
            ),
            _base_event(
                "evt_005",
                "executed",
                date={"raw_text": "July 13, 2016", "normalized_hint": "2016-07-13"},
                actor_ids=["party_a"],
                summary="Deal executed.",
                _quote_source={"quote_id": "Q_evt_005", "block_id": "B001", "text": "executed"},
                executed_with_actor_id="party_a",
            ),
        ]

    _write_quote_first_extract_fixture(
        tmp_path,
        slug=slug,
        actors_payload=actors_payload,
        events=events,
    )


def _write_gate_artifacts(
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

    blocker_count = 1 if check_status == "fail" else 0
    verify_errors = 1 if verify_status == "fail" else 0
    coverage_errors = 1 if coverage_status == "fail" else 0
    gates_blockers = 1 if gates_status == "fail" else 0

    (check_dir / "check_report.json").write_text(
        json.dumps(
            {
                "findings": [],
                "summary": {
                    "blocker_count": blocker_count,
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
                    "round_1_errors": verify_errors,
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
                "finding_count": coverage_errors,
                "error_count": coverage_errors,
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
                    "blocker_count": gates_blockers,
                    "warning_count": gate_warning_count,
                    "status": gates_status,
                },
            }
        ),
        encoding="utf-8",
    )


def test_enrich_core_preserves_extension_rounds(tmp_path: Path) -> None:
    _write_enrich_core_fixture(tmp_path)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    assert "rounds" in artifact
    assert len(artifact["rounds"]) >= 1
    assert artifact["rounds"][0]["round_scope"] == "extension"


def test_enrich_core_marks_residual_bid_uncertain_and_leaves_boundary_null(tmp_path: Path) -> None:
    _write_enrich_core_fixture(tmp_path, residual_only=True)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    assert artifact["bid_classifications"]["evt_002"]["label"] == "Uncertain"
    assert artifact["formal_boundary"]["cycle_1"]["event_id"] is None


def test_cycle_segmentation_terminated_no_restart_honest_boundary_basis(tmp_path: Path) -> None:
    """Single cycle with terminated but no restarted must not claim 'no termination events'."""
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event("evt_003", "terminated"),
        _base_event("evt_004", "executed", actor_ids=["party_a"], executed_with_actor_id="party_a"),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    cycles = artifact["cycles"]
    assert len(cycles) == 1
    assert cycles[0]["cycle_id"] == "cycle_1"
    assert cycles[0]["start_event_id"] == "evt_001"
    assert cycles[0]["end_event_id"] == "evt_004"
    assert cycles[0]["boundary_basis"] != "Single cycle -- no termination events"
    assert "terminat" in cycles[0]["boundary_basis"].lower()


def test_cycle_segmentation_terminated_intervening_restarted_no_orphans(tmp_path: Path) -> None:
    """Events between terminated and restarted must not be orphaned; boundary is at restarted."""
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "terminated"),
        _base_event("evt_003", "proposal"),  # intervening event
        _base_event("evt_004", "restarted"),
        _base_event("evt_005", "executed"),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    cycles = artifact["cycles"]
    assert len(cycles) == 2
    assert cycles[0]["cycle_id"] == "cycle_1"
    assert cycles[0]["start_event_id"] == "evt_001"
    assert cycles[0]["end_event_id"] == "evt_003"  # ends at event before restarted
    assert cycles[0]["boundary_basis"] == "Restarted event."
    assert cycles[1]["cycle_id"] == "cycle_2"
    assert cycles[1]["start_event_id"] == "evt_004"
    assert cycles[1]["end_event_id"] == "evt_005"
    assert cycles[1]["boundary_basis"] == "Final cycle."


def test_rule_2_5_classifies_after_final_round_deadline_as_formal(tmp_path: Path) -> None:
    """Proposal with after_final_round_deadline=True and no informal signals -> Formal via Rule 2."""
    formality_signals = {
        "contains_range": False,
        "mentions_indication_of_interest": False,
        "mentions_preliminary": False,
        "mentions_non_binding": False,
        "mentions_binding_offer": False,
        "includes_draft_merger_agreement": False,
        "includes_marked_up_agreement": False,
        "requested_binding_offer_via_process_letter": False,
        "after_final_round_announcement": False,
        "after_final_round_deadline": True,
        "is_subject_to_financing": None,
    }
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event("evt_003", "proposal", actor_ids=["party_a"], formality_signals=formality_signals),
        _base_event("evt_004", "executed", actor_ids=["party_a"], executed_with_actor_id="party_a"),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    classification = artifact["bid_classifications"]["evt_003"]
    assert classification["label"] == "Formal"
    assert classification["rule_applied"] == 2


def test_process_position_overrides_informal_signals(tmp_path: Path) -> None:
    """Proposal with mentions_non_binding=True AND after_final_round_deadline=True -> Formal via Rule 2 (process position overrides informal language, per D-01/D-04)."""
    formality_signals = {
        "contains_range": False,
        "mentions_indication_of_interest": False,
        "mentions_preliminary": False,
        "mentions_non_binding": True,
        "mentions_binding_offer": False,
        "includes_draft_merger_agreement": False,
        "includes_marked_up_agreement": False,
        "requested_binding_offer_via_process_letter": False,
        "after_final_round_announcement": False,
        "after_final_round_deadline": True,
        "is_subject_to_financing": None,
    }
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event("evt_003", "proposal", actor_ids=["party_a"], formality_signals=formality_signals),
        _base_event("evt_004", "executed", actor_ids=["party_a"], executed_with_actor_id="party_a"),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    classification = artifact["bid_classifications"]["evt_003"]
    assert classification["label"] == "Formal"
    assert classification["rule_applied"] == 2


def test_best_and_final_range_offer_after_final_round_is_formal(tmp_path: Path) -> None:
    """Range best-and-final offer after final round announcement stays Formal via Rule 2 (mac-gray pattern)."""
    formality_signals = {
        "contains_range": True,
        "mentions_indication_of_interest": True,
        "mentions_preliminary": False,
        "mentions_non_binding": False,
        "mentions_binding_offer": False,
        "includes_draft_merger_agreement": False,
        "includes_marked_up_agreement": False,
        "requested_binding_offer_via_process_letter": False,
        "after_final_round_announcement": True,
        "after_final_round_deadline": False,
        "is_subject_to_financing": None,
    }
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event(
            "evt_003",
            "proposal",
            actor_ids=["party_a"],
            summary="Party A reiterated that its prior $18.00 to $19.00 per share indication of interest was its best and final offer.",
            formality_signals=formality_signals,
        ),
        _base_event("evt_004", "executed", actor_ids=["party_a"], executed_with_actor_id="party_a"),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    classification = artifact["bid_classifications"]["evt_003"]
    assert classification["label"] == "Formal"
    assert classification["rule_applied"] == 2


def test_range_ioi_after_final_round_without_finality_stays_informal(tmp_path: Path) -> None:
    """Range IOI after final-round flags stays Informal when the event text lacks best-and-final language (stec evt_025 pattern)."""
    formality_signals = {
        "contains_range": True,
        "mentions_indication_of_interest": True,
        "mentions_preliminary": False,
        "mentions_non_binding": False,
        "mentions_binding_offer": False,
        "includes_draft_merger_agreement": False,
        "includes_marked_up_agreement": False,
        "requested_binding_offer_via_process_letter": False,
        "after_final_round_announcement": True,
        "after_final_round_deadline": True,
        "is_subject_to_financing": None,
    }
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event(
            "evt_003",
            "proposal",
            actor_ids=["party_a"],
            summary="WDC returned with a revised written $6.60 to $7.10 per share indication of interest.",
            formality_signals=formality_signals,
        ),
        _base_event("evt_004", "executed", actor_ids=["party_a"], executed_with_actor_id="party_a"),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    classification = artifact["bid_classifications"]["evt_003"]
    assert classification["label"] == "Informal"
    assert classification["rule_applied"] == 3


def test_range_process_letter_without_binding_docs_stays_informal(tmp_path: Path) -> None:
    """Range proposal requested via process letter stays Informal when it expressly lacks binding docs (saks evt_013 pattern)."""
    formality_signals = {
        "contains_range": True,
        "mentions_indication_of_interest": False,
        "mentions_preliminary": False,
        "mentions_non_binding": False,
        "mentions_binding_offer": False,
        "includes_draft_merger_agreement": False,
        "includes_marked_up_agreement": False,
        "requested_binding_offer_via_process_letter": True,
        "after_final_round_announcement": True,
        "after_final_round_deadline": False,
        "is_subject_to_financing": None,
    }
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event(
            "evt_003",
            "proposal",
            actor_ids=["party_a"],
            summary="Sponsor E and Sponsor G submitted a $14.50 to $15.50 per share joint proposal that required more diligence and did not include a draft merger agreement or financing support.",
            formality_signals=formality_signals,
        ),
        _base_event("evt_004", "executed", actor_ids=["party_a"], executed_with_actor_id="party_a"),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    classification = artifact["bid_classifications"]["evt_003"]
    assert classification["label"] == "Informal"
    assert classification["rule_applied"] == 3


def test_early_ioi_without_final_round_stays_informal(tmp_path: Path) -> None:
    """Early IOI without any final round -> Informal via Rule 3 (no over-promotion, per D-08)."""
    formality_signals = {
        "contains_range": False,
        "mentions_indication_of_interest": True,
        "mentions_preliminary": False,
        "mentions_non_binding": False,
        "mentions_binding_offer": False,
        "includes_draft_merger_agreement": False,
        "includes_marked_up_agreement": False,
        "requested_binding_offer_via_process_letter": False,
        "after_final_round_announcement": False,
        "after_final_round_deadline": False,
        "is_subject_to_financing": None,
    }
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event("evt_003", "proposal", actor_ids=["party_a"], formality_signals=formality_signals),
        _base_event("evt_004", "executed", actor_ids=["party_a"], executed_with_actor_id="party_a"),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    classification = artifact["bid_classifications"]["evt_003"]
    assert classification["label"] == "Informal"
    assert classification["rule_applied"] == 3


def test_explicit_formal_overrides_informal_signals(tmp_path: Path) -> None:
    """Proposal with marked-up agreement AND non-binding language -> Formal via Rule 1 (explicit formal beats informal, providence-worcester pattern per D-02/D-05)."""
    formality_signals = {
        "contains_range": False,
        "mentions_indication_of_interest": False,
        "mentions_preliminary": False,
        "mentions_non_binding": True,
        "mentions_binding_offer": False,
        "includes_draft_merger_agreement": False,
        "includes_marked_up_agreement": True,
        "requested_binding_offer_via_process_letter": False,
        "after_final_round_announcement": False,
        "after_final_round_deadline": False,
        "is_subject_to_financing": None,
    }
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event("evt_003", "proposal", actor_ids=["party_a"], formality_signals=formality_signals),
        _base_event("evt_004", "executed", actor_ids=["party_a"], executed_with_actor_id="party_a"),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    classification = artifact["bid_classifications"]["evt_003"]
    assert classification["label"] == "Formal"
    assert classification["rule_applied"] == 1


def test_formal_boundary_when_formal_proposal_in_cycle(tmp_path: Path) -> None:
    """First Formal proposal in a cycle sets formal_boundary for that cycle."""
    formal_signals = {
        "contains_range": False,
        "mentions_indication_of_interest": False,
        "mentions_preliminary": False,
        "mentions_non_binding": False,
        "mentions_binding_offer": False,
        "includes_draft_merger_agreement": True,
        "includes_marked_up_agreement": False,
        "requested_binding_offer_via_process_letter": False,
        "after_final_round_announcement": False,
        "after_final_round_deadline": False,
        "is_subject_to_financing": None,
    }
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event("evt_003", "proposal", actor_ids=["party_a"], formality_signals=formal_signals),
        _base_event("evt_004", "executed", actor_ids=["party_a"], executed_with_actor_id="party_a"),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    assert artifact["formal_boundary"]["cycle_1"]["event_id"] == "evt_003"
    assert "evt_003" in artifact["formal_boundary"]["cycle_1"]["basis"]


def test_round_pairing_does_not_cross_restart_boundary(tmp_path: Path) -> None:
    events = [
        _base_event("evt_001", "target_sale", _quote_source={"quote_id": "Q_evt_001", "block_id": "B001", "text": "sale"}),
        _base_event("evt_002", "nda", actor_ids=["party_a"], _quote_source={"quote_id": "Q_evt_002", "block_id": "B002", "text": "NDA"}),
        _base_event("evt_003", "final_round_ann", _quote_source={"quote_id": "Q_evt_003", "block_id": "B010", "text": "final round"}),
        _base_event("evt_004", "restarted", _quote_source={"quote_id": "Q_evt_004", "block_id": "B011", "text": "restarted"}),
        _base_event("evt_005", "final_round", _quote_source={"quote_id": "Q_evt_005", "block_id": "B012", "text": "deadline"}),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    rounds_by_ann = {round_record["announcement_event_id"]: round_record for round_record in artifact["rounds"]}
    assert rounds_by_ann["evt_003"]["deadline_event_id"] is None


def test_round_pairing_stops_at_next_same_family_announcement(tmp_path: Path) -> None:
    events = [
        _base_event("evt_001", "target_sale", _quote_source={"quote_id": "Q_evt_001", "block_id": "B001", "text": "sale"}),
        _base_event("evt_002", "nda", actor_ids=["party_a"], _quote_source={"quote_id": "Q_evt_002", "block_id": "B002", "text": "NDA"}),
        _base_event("evt_003", "final_round_ann", _quote_source={"quote_id": "Q_evt_003", "block_id": "B010", "text": "first announcement"}),
        _base_event("evt_004", "final_round_ann", _quote_source={"quote_id": "Q_evt_004", "block_id": "B020", "text": "second announcement"}),
        _base_event("evt_005", "final_round", _quote_source={"quote_id": "Q_evt_005", "block_id": "B030", "text": "deadline one"}),
        _base_event("evt_006", "final_round", _quote_source={"quote_id": "Q_evt_006", "block_id": "B040", "text": "deadline two"}),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    rounds_by_ann = {round_record["announcement_event_id"]: round_record for round_record in artifact["rounds"]}
    assert rounds_by_ann["evt_003"]["deadline_event_id"] is None
    assert rounds_by_ann["evt_004"]["deadline_event_id"] == "evt_005"


def test_active_bidders_use_cycle_local_state_and_restart_resets(tmp_path: Path) -> None:
    events = [
        _base_event("evt_001", "target_sale", _quote_source={"quote_id": "Q_evt_001", "block_id": "B001", "text": "sale"}),
        _base_event("evt_002", "nda", actor_ids=["party_a"], _quote_source={"quote_id": "Q_evt_002", "block_id": "B002", "text": "NDA"}),
        _base_event("evt_003", "drop", actor_ids=["party_a"], _quote_source={"quote_id": "Q_evt_003", "block_id": "B003", "text": "drop"}),
        _base_event("evt_004", "final_round_ann", _quote_source={"quote_id": "Q_evt_004", "block_id": "B010", "text": "round one"}),
        _base_event("evt_005", "nda", actor_ids=["party_a"], _quote_source={"quote_id": "Q_evt_005", "block_id": "B011", "text": "NDA again"}),
        _base_event("evt_006", "final_round_ann", _quote_source={"quote_id": "Q_evt_006", "block_id": "B012", "text": "round two"}),
        _base_event("evt_007", "restarted", _quote_source={"quote_id": "Q_evt_007", "block_id": "B020", "text": "restarted"}),
        _base_event("evt_008", "final_round_ann", _quote_source={"quote_id": "Q_evt_008", "block_id": "B021", "text": "round three"}),
        _base_event("evt_009", "final_round", _quote_source={"quote_id": "Q_evt_009", "block_id": "B022", "text": "deadline"}),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    rounds_by_ann = {round_record["announcement_event_id"]: round_record for round_record in artifact["rounds"]}
    assert rounds_by_ann["evt_004"]["active_bidders_at_time"] == 0
    assert rounds_by_ann["evt_006"]["active_bidders_at_time"] == 1
    assert rounds_by_ann["evt_008"]["active_bidders_at_time"] == 0


def test_invited_actor_ids_populated_from_count_assertions(tmp_path: Path) -> None:
    """count_assertion with final_round_invitees populates invited_actor_ids on round ann."""
    slug = "imprivata"
    actors_payload = {
        "quotes": [
            {"quote_id": "Q001", "block_id": "B001", "text": "x"},
            {"quote_id": "Q002", "block_id": "B001", "text": "x"},
            {"quote_id": "Q003", "block_id": "B001", "text": "x"},
            {
                "quote_id": "Q004",
                "block_id": "B078",
                "text": "Sponsor B and Thoma Bravo had been invited to submit their final bids",
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
            {
                "actor_id": "bidder_b",
                "display_name": "Sponsor B",
                "canonical_name": "SPONSOR B",
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
                "quote_ids": ["Q002"],
                "notes": [],
            },
            {
                "actor_id": "bidder_c",
                "display_name": "Thoma Bravo",
                "canonical_name": "THOMA BRAVO",
                "aliases": ["TB"],
                "role": "bidder",
                "advisor_kind": None,
                "advised_actor_id": None,
                "bidder_kind": "financial",
                "listing_status": "private",
                "geography": "domestic",
                "is_grouped": False,
                "group_size": None,
                "group_label": None,
                "quote_ids": ["Q003"],
                "notes": [],
            },
        ],
        "count_assertions": [
            {
                "subject": "final_round_invitees",
                "count": 2,
                "quote_ids": ["Q004"],
            }
        ],
        "unresolved_mentions": [],
    }

    events = [
        _base_event("evt_001", "target_sale", _quote_source={"quote_id": "Q_evt_001", "block_id": "B010", "text": "sale"}),
        _base_event("evt_002", "nda", actor_ids=["bidder_a"], _quote_source={"quote_id": "Q_evt_002", "block_id": "B020", "text": "nda a"}),
        _base_event("evt_003", "nda", actor_ids=["bidder_b"], _quote_source={"quote_id": "Q_evt_003", "block_id": "B030", "text": "nda b"}),
        _base_event("evt_004", "nda", actor_ids=["bidder_c"], _quote_source={"quote_id": "Q_evt_004", "block_id": "B040", "text": "nda c"}),
        _base_event("evt_005", "final_round_ann", invited_actor_ids=[], _quote_source={"quote_id": "Q_evt_005", "block_id": "B075", "text": "final round announcement"}),
        _base_event("evt_006", "final_round", _quote_source={"quote_id": "Q_evt_006", "block_id": "B080", "text": "final round deadline"}),
        _base_event("evt_007", "executed", executed_with_actor_id="bidder_c", _quote_source={"quote_id": "Q_evt_007", "block_id": "B090", "text": "executed"}),
    ]
    _write_quote_first_extract_fixture(
        tmp_path,
        slug=slug,
        actors_payload=actors_payload,
        events=events,
    )

    _write_gate_artifacts(tmp_path, slug=slug)
    run_enrich_core(slug, project_root=tmp_path)
    paths = build_skill_paths(slug, project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    assert len(artifact["rounds"]) >= 1
    formal_round = artifact["rounds"][0]
    assert set(formal_round["invited_actor_ids"]) == {"bidder_b", "bidder_c"}
    assert formal_round["is_selective"] is True


def test_invited_actor_ids_attach_to_nearest_round_announcement_in_cycle_by_evidence_position(
    tmp_path: Path,
) -> None:
    slug = "imprivata"
    actors_payload = {
        "quotes": [
            {"quote_id": "Q001", "block_id": "B001", "text": "x"},
            {"quote_id": "Q002", "block_id": "B001", "text": "x"},
            {"quote_id": "Q003", "block_id": "B001", "text": "x"},
            {
                "quote_id": "Q004",
                "block_id": "B018",
                "text": "Sponsor B and Thoma Bravo were invited to submit final bids",
            },
            {
                "quote_id": "Q005",
                "block_id": "B011",
                "text": "Unknown Corp and Mystery LLC were invited",
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
            {
                "actor_id": "bidder_b",
                "display_name": "Sponsor B",
                "canonical_name": "SPONSOR B",
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
                "quote_ids": ["Q002"],
                "notes": [],
            },
            {
                "actor_id": "bidder_c",
                "display_name": "Thoma Bravo",
                "canonical_name": "THOMA BRAVO",
                "aliases": ["TB"],
                "role": "bidder",
                "advisor_kind": None,
                "advised_actor_id": None,
                "bidder_kind": "financial",
                "listing_status": "private",
                "geography": "domestic",
                "is_grouped": False,
                "group_size": None,
                "group_label": None,
                "quote_ids": ["Q003"],
                "notes": [],
            },
        ],
        "count_assertions": [
            {
                "subject": "final_round_invitees",
                "count": 2,
                "quote_ids": ["Q004"],
            },
            {
                "subject": "final_round_invitees",
                "count": 2,
                "quote_ids": ["Q005"],
            },
        ],
        "unresolved_mentions": [],
    }

    events = [
        _base_event(
            "evt_001",
            "target_sale",
            _quote_source={"quote_id": "Q_evt_001", "block_id": "B001", "text": "sale"},
        ),
        _base_event(
            "evt_002",
            "nda",
            actor_ids=["bidder_a", "bidder_b", "bidder_c"],
            _quote_source={"quote_id": "Q_evt_002", "block_id": "B005", "text": "NDA"},
        ),
        _base_event(
            "evt_003",
            "final_round_ann",
            invited_actor_ids=[],
            _quote_source={"quote_id": "Q_evt_003", "block_id": "B010", "text": "announcement one"},
        ),
        _base_event(
            "evt_004",
            "final_round_ann",
            invited_actor_ids=[],
            _quote_source={"quote_id": "Q_evt_004", "block_id": "B020", "text": "announcement two"},
        ),
        _base_event(
            "evt_005",
            "final_round",
            _quote_source={"quote_id": "Q_evt_005", "block_id": "B030", "text": "deadline"},
        ),
    ]
    _write_quote_first_extract_fixture(
        tmp_path,
        slug=slug,
        actors_payload=actors_payload,
        events=events,
    )

    _write_gate_artifacts(tmp_path, slug=slug)
    run_enrich_core(slug, project_root=tmp_path)
    paths = build_skill_paths(slug, project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    rounds_by_ann = {round_record["announcement_event_id"]: round_record for round_record in artifact["rounds"]}
    assert rounds_by_ann["evt_003"]["invited_actor_ids"] == []
    assert set(rounds_by_ann["evt_004"]["invited_actor_ids"]) == {"bidder_b", "bidder_c"}
    assert rounds_by_ann["evt_004"]["is_selective"] is True


def test_invited_population_graceful_on_unmatched_names(tmp_path: Path) -> None:
    """Unmatched actor names in anchor text leave invited_actor_ids empty; no crash."""
    slug = "imprivata"
    actors_payload = {
        "quotes": [
            {"quote_id": "Q001", "block_id": "B001", "text": "x"},
            {
                "quote_id": "Q002",
                "block_id": "B078",
                "text": "Unknown Corp and Mystery LLC were invited",
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
                "subject": "final_round_invitees",
                "count": 2,
                "quote_ids": ["Q002"],
            }
        ],
        "unresolved_mentions": [],
    }

    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["bidder_a"]),
        _base_event("evt_003", "final_round_ann", invited_actor_ids=[]),
        _base_event("evt_004", "final_round"),
        _base_event("evt_005", "executed", executed_with_actor_id="bidder_a"),
    ]
    _write_quote_first_extract_fixture(
        tmp_path,
        slug=slug,
        actors_payload=actors_payload,
        events=events,
    )

    _write_gate_artifacts(tmp_path, slug=slug)
    run_enrich_core(slug, project_root=tmp_path)
    paths = build_skill_paths(slug, project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    assert len(artifact["rounds"]) >= 1
    formal_round = artifact["rounds"][0]
    assert formal_round["invited_actor_ids"] == []
    assert formal_round["is_selective"] is False


def test_enrich_core_requires_gate_artifacts(tmp_path: Path) -> None:
    _write_enrich_core_fixture(tmp_path)

    with pytest.raises(FileNotFoundError, match="check_report.json"):
        run_enrich_core("imprivata", project_root=tmp_path)


def test_enrich_core_rejects_failed_verify_gate(tmp_path: Path) -> None:
    _write_enrich_core_fixture(tmp_path)
    _write_gate_artifacts(tmp_path, verify_status="fail")

    with pytest.raises(ValueError, match="verify"):
        run_enrich_core("imprivata", project_root=tmp_path)


def test_enrich_core_invalidates_stale_output_when_gate_fails_on_rerun(tmp_path: Path) -> None:
    _write_enrich_core_fixture(tmp_path)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    _write_gate_artifacts(tmp_path, verify_status="fail")

    with pytest.raises(ValueError, match="verify"):
        run_enrich_core("imprivata", project_root=tmp_path)

    assert not paths.deterministic_enrichment_path.exists()


def _build_bidder_actors_payload(actor_ids: list[str]) -> dict:
    quotes = []
    actors = []
    for idx, actor_id in enumerate(actor_ids, start=1):
        label = actor_id.replace("_", " ").title()
        quote_id = f"QACT{idx:03d}"
        quotes.append({
            "quote_id": quote_id,
            "block_id": f"BA{idx:03d}",
            "text": label,
        })
        actors.append({
            "actor_id": actor_id,
            "display_name": label,
            "canonical_name": label.upper(),
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
            "quote_ids": [quote_id],
            "notes": [],
        })
    return {
        "quotes": quotes,
        "actors": actors,
        "count_assertions": [],
        "unresolved_mentions": [],
    }


def _write_multi_bidder_enrich_core_fixture(
    tmp_path: Path,
    *,
    events: list[dict],
    actor_ids: list[str],
    slug: str = "imprivata",
) -> None:
    _write_quote_first_extract_fixture(
        tmp_path,
        slug=slug,
        actors_payload=_build_bidder_actors_payload(actor_ids),
        events=events,
    )


def _read_deterministic_enrichment(tmp_path: Path, *, slug: str = "imprivata") -> dict:
    paths = build_skill_paths(slug, project_root=tmp_path)
    return json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))


def test_drop_target_classified_when_bidder_active_but_not_invited_to_round(tmp_path: Path) -> None:
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event("evt_003", "nda", actor_ids=["party_b"]),
        _base_event("evt_004", "final_round_ann", invited_actor_ids=["party_a"]),
        _base_event("evt_005", "final_round"),
        _base_event(
            "evt_006",
            "drop",
            actor_ids=["party_b"],
            drop_reason_text="Party B was no longer participating in the process",
        ),
        _base_event(
            "evt_007",
            "executed",
            actor_ids=["party_a"],
            executed_with_actor_id="party_a",
        ),
    ]
    _write_multi_bidder_enrich_core_fixture(
        tmp_path,
        events=events,
        actor_ids=["party_a", "party_b"],
    )
    _write_gate_artifacts(tmp_path)

    run_enrich_core("imprivata", project_root=tmp_path)
    artifact = _read_deterministic_enrichment(tmp_path)

    classification = artifact["dropout_classifications"]["evt_006"]
    assert classification["label"] == "DropTarget"
    assert "invited_actor_ids" in classification["basis"]


def test_drop_target_not_classified_when_bidder_signaled_withdrawal(tmp_path: Path) -> None:
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event("evt_003", "nda", actor_ids=["party_b"]),
        _base_event("evt_004", "final_round_ann", invited_actor_ids=["party_a"]),
        _base_event("evt_005", "final_round"),
        _base_event(
            "evt_006",
            "drop",
            actor_ids=["party_b"],
            drop_reason_text="Party B indicated it would not be in a position to improve its proposal",
        ),
    ]
    _write_multi_bidder_enrich_core_fixture(
        tmp_path,
        events=events,
        actor_ids=["party_a", "party_b"],
    )
    _write_gate_artifacts(tmp_path)

    run_enrich_core("imprivata", project_root=tmp_path)
    artifact = _read_deterministic_enrichment(tmp_path)

    assert artifact["dropout_classifications"] == {}


def test_drop_target_not_classified_when_drop_has_bidder_withdrawal_and_target_exclusion(
    tmp_path: Path,
) -> None:
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event("evt_003", "nda", actor_ids=["party_b"]),
        _base_event("evt_004", "final_round_ann", invited_actor_ids=["party_a"]),
        _base_event("evt_005", "final_round"),
        _base_event(
            "evt_006",
            "drop",
            actor_ids=["party_b"],
            drop_reason_text=(
                "Party B could not improve its offer and the Committee determined not to include "
                "Party B in the final round"
            ),
        ),
    ]
    _write_multi_bidder_enrich_core_fixture(
        tmp_path,
        events=events,
        actor_ids=["party_a", "party_b"],
    )
    _write_gate_artifacts(tmp_path)

    run_enrich_core("imprivata", project_root=tmp_path)
    artifact = _read_deterministic_enrichment(tmp_path)

    assert artifact["dropout_classifications"] == {}


def test_drop_target_not_classified_when_no_round_context(tmp_path: Path) -> None:
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event("evt_003", "nda", actor_ids=["party_b"]),
        _base_event(
            "evt_004",
            "drop",
            actor_ids=["party_b"],
            drop_reason_text="Party B was no longer participating in the process",
        ),
    ]
    _write_multi_bidder_enrich_core_fixture(
        tmp_path,
        events=events,
        actor_ids=["party_a", "party_b"],
    )
    _write_gate_artifacts(tmp_path)

    run_enrich_core("imprivata", project_root=tmp_path)
    artifact = _read_deterministic_enrichment(tmp_path)

    assert artifact["dropout_classifications"] == {}


def test_drop_target_sparse_output_only_contains_classified_events(tmp_path: Path) -> None:
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event("evt_003", "nda", actor_ids=["party_b"]),
        _base_event("evt_004", "nda", actor_ids=["party_c"]),
        _base_event("evt_005", "final_round_ann", invited_actor_ids=["party_a", "party_c"]),
        _base_event("evt_006", "final_round"),
        _base_event(
            "evt_007",
            "drop",
            actor_ids=["party_b"],
            drop_reason_text="Party B was no longer participating in the process",
        ),
        _base_event(
            "evt_008",
            "drop",
            actor_ids=["party_a"],
            drop_reason_text="Party A would not continue in the process",
        ),
        _base_event(
            "evt_009",
            "drop",
            actor_ids=["party_c"],
            drop_reason_text="Party C was unable to proceed with the transaction",
        ),
    ]
    _write_multi_bidder_enrich_core_fixture(
        tmp_path,
        events=events,
        actor_ids=["party_a", "party_b", "party_c"],
    )
    _write_gate_artifacts(tmp_path)

    run_enrich_core("imprivata", project_root=tmp_path)
    artifact = _read_deterministic_enrichment(tmp_path)

    assert set(artifact["dropout_classifications"]) == {"evt_007"}


def test_drop_target_empty_when_all_drops_bidder_initiated(tmp_path: Path) -> None:
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event("evt_003", "nda", actor_ids=["party_b"]),
        _base_event("evt_004", "final_round_ann", invited_actor_ids=["party_a"]),
        _base_event("evt_005", "final_round"),
        _base_event(
            "evt_006",
            "drop",
            actor_ids=["party_b"],
            drop_reason_text="Party B could not improve its proposal",
        ),
        _base_event(
            "evt_007",
            "drop",
            actor_ids=["party_a"],
            drop_reason_text="Party A would not continue in the process",
        ),
    ]
    _write_multi_bidder_enrich_core_fixture(
        tmp_path,
        events=events,
        actor_ids=["party_a", "party_b"],
    )
    _write_gate_artifacts(tmp_path)

    run_enrich_core("imprivata", project_root=tmp_path)
    artifact = _read_deterministic_enrichment(tmp_path)

    assert artifact["dropout_classifications"] == {}


def test_all_cash_inferred_when_executed_event_is_cash(tmp_path: Path) -> None:
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event(
            "evt_003",
            "proposal",
            actor_ids=["party_a"],
            terms={
                "per_share": 25.0,
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": "cash",
            },
        ),
        _base_event("evt_004", "proposal", actor_ids=["party_a"], terms=None),
        _base_event(
            "evt_005",
            "executed",
            actor_ids=["party_a"],
            executed_with_actor_id="party_a",
            terms={
                "per_share": 26.0,
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": "cash",
            },
        ),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)

    run_enrich_core("imprivata", project_root=tmp_path)
    artifact = _read_deterministic_enrichment(tmp_path)

    assert artifact["all_cash_overrides"] == {"evt_004": True}


def test_all_cash_inferred_when_all_typed_proposals_are_cash(tmp_path: Path) -> None:
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event(
            "evt_003",
            "proposal",
            actor_ids=["party_a"],
            terms={
                "per_share": 25.0,
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": "cash",
            },
        ),
        _base_event("evt_004", "proposal", actor_ids=["party_a"], terms=None),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)

    run_enrich_core("imprivata", project_root=tmp_path)
    artifact = _read_deterministic_enrichment(tmp_path)

    assert artifact["all_cash_overrides"] == {"evt_004": True}


def test_all_cash_not_inferred_when_any_proposal_is_mixed(tmp_path: Path) -> None:
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event(
            "evt_003",
            "proposal",
            actor_ids=["party_a"],
            terms={
                "per_share": 25.0,
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": "cash",
            },
        ),
        _base_event(
            "evt_004",
            "proposal",
            actor_ids=["party_a"],
            terms={
                "per_share": 26.0,
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": "mixed",
            },
        ),
        _base_event("evt_005", "proposal", actor_ids=["party_a"], terms=None),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)

    run_enrich_core("imprivata", project_root=tmp_path)
    artifact = _read_deterministic_enrichment(tmp_path)

    assert artifact["all_cash_overrides"] == {}


def test_all_cash_not_inferred_for_proposals_with_explicit_type(tmp_path: Path) -> None:
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event(
            "evt_003",
            "proposal",
            actor_ids=["party_a"],
            terms={
                "per_share": 25.0,
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": "cash",
            },
        ),
        _base_event("evt_004", "proposal", actor_ids=["party_a"], terms=None),
        _base_event(
            "evt_005",
            "executed",
            actor_ids=["party_a"],
            executed_with_actor_id="party_a",
            terms={
                "per_share": 26.0,
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": "cash",
            },
        ),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)

    run_enrich_core("imprivata", project_root=tmp_path)
    artifact = _read_deterministic_enrichment(tmp_path)

    assert "evt_003" not in artifact["all_cash_overrides"]
    assert artifact["all_cash_overrides"]["evt_004"] is True


def test_all_cash_cycle_local_not_crossing_restart(tmp_path: Path) -> None:
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event("evt_003", "proposal", actor_ids=["party_a"], terms=None),
        _base_event(
            "evt_004",
            "executed",
            actor_ids=["party_a"],
            executed_with_actor_id="party_a",
            terms={
                "per_share": 26.0,
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": "cash",
            },
        ),
        _base_event("evt_005", "restarted"),
        _base_event("evt_006", "proposal", actor_ids=["party_a"], terms=None),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)

    run_enrich_core("imprivata", project_root=tmp_path)
    artifact = _read_deterministic_enrichment(tmp_path)

    assert artifact["all_cash_overrides"] == {"evt_003": True}


def test_all_cash_falls_back_when_executed_event_lacks_type(tmp_path: Path) -> None:
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event(
            "evt_003",
            "proposal",
            actor_ids=["party_a"],
            terms={
                "per_share": 25.0,
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": "cash",
            },
        ),
        _base_event(
            "evt_004",
            "proposal",
            actor_ids=["party_b"],
            terms={
                "per_share": 26.0,
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": "cash",
            },
        ),
        _base_event("evt_005", "proposal", actor_ids=["party_a"], terms=None),
        _base_event(
            "evt_006",
            "executed",
            actor_ids=["party_a"],
            executed_with_actor_id="party_a",
            terms={
                "per_share": 27.0,
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": None,
            },
        ),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)

    run_enrich_core("imprivata", project_root=tmp_path)
    artifact = _read_deterministic_enrichment(tmp_path)

    assert artifact["all_cash_overrides"] == {"evt_005": True}


def test_all_cash_not_inferred_providence_worcester_guardrail(tmp_path: Path) -> None:
    events = [_base_event("evt_001", "target_sale"), _base_event("evt_002", "nda", actor_ids=["party_a"])]
    for idx in range(3, 13):
        terms = None
        if idx == 3:
            terms = {
                "per_share": 25.0,
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": "cash",
            }
        events.append(
            _base_event(
                f"evt_{idx:03d}",
                "proposal",
                actor_ids=["party_a"],
                terms=terms,
            )
        )
    events.append(
        _base_event(
            "evt_013",
            "executed",
            actor_ids=["party_a"],
            executed_with_actor_id="party_a",
            terms={
                "per_share": 26.0,
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": None,
            },
        )
    )
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)

    run_enrich_core("imprivata", project_root=tmp_path)
    artifact = _read_deterministic_enrichment(tmp_path)

    assert artifact["all_cash_overrides"] == {}
