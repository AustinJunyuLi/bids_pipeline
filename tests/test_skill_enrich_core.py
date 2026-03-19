"""Tests for the deterministic enrich-core stage."""

from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.enrich_core import run_enrich_core
from skill_pipeline.paths import build_skill_paths


def _base_event(evt_id: str, event_type: str, **overrides: object) -> dict:
    """Minimal event template for fixtures."""
    evt = {
        "event_id": evt_id,
        "event_type": event_type,
        "date": {"raw_text": "2016-06", "normalized_hint": "2016-06"},
        "actor_ids": [],
        "summary": "",
        "evidence_refs": [{"block_id": "B001", "evidence_id": "E001", "anchor_text": "x"}],
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
    data_dir = tmp_path / "data"
    deals_source_dir = data_dir / "deals" / slug / "source"
    skill_root = data_dir / "skill" / slug
    extract_dir = skill_root / "extract"

    deals_source_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n"
        ),
        encoding="utf-8",
    )
    (deals_source_dir / "chronology_blocks.jsonl").write_text("{}\n", encoding="utf-8")
    (deals_source_dir / "evidence_items.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "raw" / slug).mkdir(parents=True, exist_ok=True)
    (tmp_path / "raw" / slug / "document_registry.json").write_text("{}", encoding="utf-8")

    actors_payload = {
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
                "evidence_refs": [{"block_id": "B001", "evidence_id": None, "anchor_text": "Party A"}],
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
            {
                "event_id": "evt_001",
                "event_type": "target_sale",
                "date": {"raw_text": "June 2016", "normalized_hint": "2016-06"},
                "actor_ids": ["party_a"],
                "summary": "Target initiated sale.",
                "evidence_refs": [{"block_id": "B001", "evidence_id": None, "anchor_text": "sale"}],
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
            },
            {
                "event_id": "evt_002",
                "event_type": "proposal",
                "date": {"raw_text": "July 5, 2016", "normalized_hint": "2016-07-05"},
                "actor_ids": ["party_a"],
                "summary": "Party A submitted a bid.",
                "evidence_refs": [{"block_id": "B001", "evidence_id": None, "anchor_text": "bid"}],
                "terms": {"per_share": 25.0, "range_low": None, "range_high": None, "enterprise_value": None, "consideration_type": "cash"},
                "formality_signals": residual_formality,
                "whole_company_scope": True,
                "drop_reason_text": None,
                "round_scope": None,
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": None,
                "notes": [],
            },
            {
                "event_id": "evt_003",
                "event_type": "executed",
                "date": {"raw_text": "July 13, 2016", "normalized_hint": "2016-07-13"},
                "actor_ids": ["party_a"],
                "summary": "Deal executed.",
                "evidence_refs": [{"block_id": "B001", "evidence_id": None, "anchor_text": "executed"}],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": True,
                "drop_reason_text": None,
                "round_scope": None,
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": "party_a",
                "boundary_note": None,
                "nda_signed": None,
                "notes": [],
            },
        ]
    else:
        # Extension round: final_round_ext_ann -> final_round_ext
        events = [
            {
                "event_id": "evt_001",
                "event_type": "target_sale",
                "date": {"raw_text": "June 2016", "normalized_hint": "2016-06"},
                "actor_ids": ["party_a"],
                "summary": "Target initiated sale.",
                "evidence_refs": [{"block_id": "B001", "evidence_id": None, "anchor_text": "sale"}],
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
            },
            {
                "event_id": "evt_002",
                "event_type": "nda",
                "date": {"raw_text": "June 15, 2016", "normalized_hint": "2016-06-15"},
                "actor_ids": ["party_a"],
                "summary": "Party A signed NDA.",
                "evidence_refs": [{"block_id": "B001", "evidence_id": None, "anchor_text": "NDA"}],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": True,
                "drop_reason_text": None,
                "round_scope": None,
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": True,
                "notes": [],
            },
            {
                "event_id": "evt_003",
                "event_type": "final_round_ext_ann",
                "date": {"raw_text": "July 1, 2016", "normalized_hint": "2016-07-01"},
                "actor_ids": [],
                "summary": "Target announced extension round.",
                "evidence_refs": [{"block_id": "B001", "evidence_id": None, "anchor_text": "extension"}],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": True,
                "drop_reason_text": None,
                "round_scope": "formal",
                "invited_actor_ids": ["party_a"],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": None,
                "notes": [],
            },
            {
                "event_id": "evt_004",
                "event_type": "final_round_ext",
                "date": {"raw_text": "July 5, 2016", "normalized_hint": "2016-07-05"},
                "actor_ids": [],
                "summary": "Extension round deadline.",
                "evidence_refs": [{"block_id": "B001", "evidence_id": None, "anchor_text": "deadline"}],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": True,
                "drop_reason_text": None,
                "round_scope": None,
                "invited_actor_ids": [],
                "deadline_date": {"raw_text": "July 5, 2016", "normalized_hint": "2016-07-05"},
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": None,
                "notes": [],
            },
            {
                "event_id": "evt_005",
                "event_type": "executed",
                "date": {"raw_text": "July 13, 2016", "normalized_hint": "2016-07-13"},
                "actor_ids": ["party_a"],
                "summary": "Deal executed.",
                "evidence_refs": [{"block_id": "B001", "evidence_id": None, "anchor_text": "executed"}],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": True,
                "drop_reason_text": None,
                "round_scope": None,
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": "party_a",
                "boundary_note": None,
                "nda_signed": None,
                "notes": [],
            },
        ]

    events_payload = {"events": events, "exclusions": [], "coverage_notes": []}

    (extract_dir / "actors_raw.json").write_text(json.dumps(actors_payload), encoding="utf-8")
    (extract_dir / "events_raw.json").write_text(json.dumps(events_payload), encoding="utf-8")


def test_enrich_core_preserves_extension_rounds(tmp_path: Path) -> None:
    _write_enrich_core_fixture(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    assert "rounds" in artifact
    assert len(artifact["rounds"]) >= 1
    assert artifact["rounds"][0]["round_scope"] == "extension"


def test_enrich_core_marks_residual_bid_uncertain_and_leaves_boundary_null(tmp_path: Path) -> None:
    _write_enrich_core_fixture(tmp_path, residual_only=True)
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
    """Proposal with after_final_round_deadline=True and no informal signals -> Formal via Rule 2.5."""
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
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    classification = artifact["bid_classifications"]["evt_003"]
    assert classification["label"] == "Formal"
    assert classification["rule_applied"] == 2.5


def test_rule_1_overrides_rule_2_5_when_non_binding(tmp_path: Path) -> None:
    """Proposal with both mentions_non_binding=True and after_final_round_deadline=True -> Informal via Rule 1."""
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
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    classification = artifact["bid_classifications"]["evt_003"]
    assert classification["label"] == "Informal"
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
    run_enrich_core("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    assert artifact["formal_boundary"]["cycle_1"]["event_id"] == "evt_003"
    assert "evt_003" in artifact["formal_boundary"]["cycle_1"]["basis"]


def test_invited_actor_ids_populated_from_count_assertions(tmp_path: Path) -> None:
    """count_assertion with final_round_invitees populates invited_actor_ids on round ann."""
    slug = "imprivata"
    data_dir = tmp_path / "data"
    deals_source_dir = data_dir / "deals" / slug / "source"
    extract_dir = data_dir / "skill" / slug / "extract"
    deals_source_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "seeds.csv").write_text(
        "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
        f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n",
        encoding="utf-8",
    )
    (deals_source_dir / "chronology_blocks.jsonl").write_text("{}\n", encoding="utf-8")
    (deals_source_dir / "evidence_items.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "raw" / slug).mkdir(parents=True, exist_ok=True)
    (tmp_path / "raw" / slug / "document_registry.json").write_text("{}", encoding="utf-8")

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
                "evidence_refs": [{"block_id": "B001", "evidence_id": None, "anchor_text": "x"}],
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
                "evidence_refs": [{"block_id": "B001", "evidence_id": None, "anchor_text": "x"}],
                "notes": [],
            },
        ],
        "count_assertions": [
            {
                "subject": "final_round_invitees",
                "count": 2,
                "evidence_refs": [
                    {
                        "block_id": "B078",
                        "evidence_id": None,
                        "anchor_text": "Sponsor B and Thoma Bravo had been invited to submit their final bids",
                    }
                ],
            }
        ],
        "unresolved_mentions": [],
    }

    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["bidder_a"]),
        _base_event("evt_003", "nda", actor_ids=["bidder_b"]),
        _base_event("evt_004", "nda", actor_ids=["bidder_c"]),
        _base_event("evt_005", "final_round_ann", invited_actor_ids=[]),
        _base_event("evt_006", "final_round"),
        _base_event("evt_007", "executed", executed_with_actor_id="bidder_c"),
    ]
    events_payload = {"events": events, "exclusions": [], "coverage_notes": []}

    (extract_dir / "actors_raw.json").write_text(json.dumps(actors_payload), encoding="utf-8")
    (extract_dir / "events_raw.json").write_text(json.dumps(events_payload), encoding="utf-8")

    run_enrich_core(slug, project_root=tmp_path)
    paths = build_skill_paths(slug, project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    assert len(artifact["rounds"]) >= 1
    formal_round = artifact["rounds"][0]
    assert set(formal_round["invited_actor_ids"]) == {"bidder_b", "bidder_c"}
    assert formal_round["is_selective"] is True


def test_invited_population_graceful_on_unmatched_names(tmp_path: Path) -> None:
    """Unmatched actor names in anchor text leave invited_actor_ids empty; no crash."""
    slug = "imprivata"
    data_dir = tmp_path / "data"
    deals_source_dir = data_dir / "deals" / slug / "source"
    extract_dir = data_dir / "skill" / slug / "extract"
    deals_source_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "seeds.csv").write_text(
        "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
        f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n",
        encoding="utf-8",
    )
    (deals_source_dir / "chronology_blocks.jsonl").write_text("{}\n", encoding="utf-8")
    (deals_source_dir / "evidence_items.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "raw" / slug).mkdir(parents=True, exist_ok=True)
    (tmp_path / "raw" / slug / "document_registry.json").write_text("{}", encoding="utf-8")

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
                "subject": "final_round_invitees",
                "count": 2,
                "evidence_refs": [
                    {
                        "block_id": "B078",
                        "evidence_id": None,
                        "anchor_text": "Unknown Corp and Mystery LLC were invited",
                    }
                ],
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
    events_payload = {"events": events, "exclusions": [], "coverage_notes": []}

    (extract_dir / "actors_raw.json").write_text(json.dumps(actors_payload), encoding="utf-8")
    (extract_dir / "events_raw.json").write_text(json.dumps(events_payload), encoding="utf-8")

    run_enrich_core(slug, project_root=tmp_path)
    paths = build_skill_paths(slug, project_root=tmp_path)
    artifact = json.loads(paths.deterministic_enrichment_path.read_text(encoding="utf-8"))

    assert len(artifact["rounds"]) >= 1
    formal_round = artifact["rounds"][0]
    assert formal_round["invited_actor_ids"] == []
    assert formal_round["is_selective"] is False
