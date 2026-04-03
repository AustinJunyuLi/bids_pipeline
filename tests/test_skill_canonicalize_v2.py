"""Tests for the additive v2 canonicalize stage."""

from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline import cli
from skill_pipeline.canonicalize import run_canonicalize_v2
from skill_pipeline.paths import build_skill_paths


def _resolved_date_payload(day: str = "2026-03-31") -> dict:
    return {
        "raw_text": day,
        "normalized_start": day,
        "normalized_end": day,
        "sort_date": day,
        "precision": "exact_day",
        "anchor_event_id": None,
        "anchor_span_id": None,
        "resolution_note": None,
        "is_inferred": False,
    }


def _raw_observations_payload() -> dict:
    return {
        "quotes": [
            {"quote_id": "Q001", "block_id": "B001", "text": "Bidder A"},
            {"quote_id": "Q002", "block_id": "B002", "text": "Three finalists advanced"},
            {"quote_id": "Q101", "block_id": "B003", "text": "Bidder A submitted a proposal"},
        ],
        "parties": [
            {
                "party_id": "party_bidder_a",
                "display_name": "Bidder A",
                "canonical_name": "BIDDER A",
                "aliases": [],
                "role": "bidder",
                "bidder_kind": "financial",
                "advisor_kind": None,
                "advised_party_id": None,
                "listing_status": "private",
                "geography": "domestic",
                "quote_ids": ["Q001"],
            }
        ],
        "cohorts": [
            {
                "cohort_id": "cohort_finalists",
                "label": "Finalists",
                "parent_cohort_id": None,
                "exact_count": 3,
                "known_member_party_ids": ["party_bidder_a"],
                "unknown_member_count": 2,
                "membership_basis": "advanced to the final round",
                "created_by_observation_id": "obs_status",
                "quote_ids": ["Q002"],
            }
        ],
        "observations": [
            {
                "observation_id": "obs_proposal",
                "obs_type": "proposal",
                "date": _resolved_date_payload(),
                "subject_refs": ["party_bidder_a"],
                "counterparty_refs": ["cohort_finalists"],
                "summary": "Bidder A submitted a proposal.",
                "quote_ids": ["Q101"],
                "requested_by_observation_id": None,
                "revises_observation_id": None,
                "delivery_mode": "written",
                "terms": {
                    "per_share": "21.50",
                    "range_low": None,
                    "range_high": None,
                    "enterprise_value": None,
                    "consideration_type": "cash",
                },
                "mentions_non_binding": True,
                "includes_draft_merger_agreement": False,
                "includes_markup": False,
            }
        ],
        "exclusions": [],
        "coverage": [],
    }


def _canonical_observations_payload() -> dict:
    return {
        "parties": [
            {
                "party_id": "party_bidder_a",
                "display_name": "Bidder A",
                "canonical_name": "BIDDER A",
                "aliases": [],
                "role": "bidder",
                "bidder_kind": "financial",
                "advisor_kind": None,
                "advised_party_id": None,
                "listing_status": "private",
                "geography": "domestic",
                "evidence_span_ids": ["span_0001"],
            }
        ],
        "cohorts": [
            {
                "cohort_id": "cohort_finalists",
                "label": "Finalists",
                "parent_cohort_id": None,
                "exact_count": 3,
                "known_member_party_ids": ["party_bidder_a"],
                "unknown_member_count": 2,
                "membership_basis": "advanced to the final round",
                "created_by_observation_id": "obs_status",
                "evidence_span_ids": ["span_0002"],
            }
        ],
        "observations": [
            {
                "observation_id": "obs_proposal",
                "obs_type": "proposal",
                "date": _resolved_date_payload(),
                "subject_refs": ["party_bidder_a"],
                "counterparty_refs": ["cohort_finalists"],
                "summary": "Bidder A submitted a proposal.",
                "evidence_span_ids": ["span_0003"],
                "requested_by_observation_id": None,
                "revises_observation_id": None,
                "delivery_mode": "written",
                "terms": {
                    "per_share": "21.50",
                    "range_low": None,
                    "range_high": None,
                    "enterprise_value": None,
                    "consideration_type": "cash",
                },
                "mentions_non_binding": True,
                "includes_draft_merger_agreement": False,
                "includes_markup": False,
            }
        ],
        "exclusions": [],
        "coverage": [],
    }


def _spans_payload() -> dict:
    return {
        "spans": [
            {
                "span_id": "span_0001",
                "document_id": "DOC001",
                "accession_number": "DOC001",
                "filing_type": "DEFM14A",
                "start_line": 1,
                "end_line": 1,
                "start_char": None,
                "end_char": None,
                "block_ids": ["B001"],
                "evidence_ids": [],
                "anchor_text": "Bidder A",
                "quote_text": "Bidder A",
                "quote_text_normalized": "bidder a",
                "match_type": "exact",
                "resolution_note": None,
            },
            {
                "span_id": "span_0002",
                "document_id": "DOC001",
                "accession_number": "DOC001",
                "filing_type": "DEFM14A",
                "start_line": 2,
                "end_line": 2,
                "start_char": None,
                "end_char": None,
                "block_ids": ["B002"],
                "evidence_ids": [],
                "anchor_text": "Three finalists advanced",
                "quote_text": "Three finalists advanced",
                "quote_text_normalized": "three finalists advanced",
                "match_type": "exact",
                "resolution_note": None,
            },
            {
                "span_id": "span_0003",
                "document_id": "DOC001",
                "accession_number": "DOC001",
                "filing_type": "DEFM14A",
                "start_line": 3,
                "end_line": 3,
                "start_char": None,
                "end_char": None,
                "block_ids": ["B003"],
                "evidence_ids": [],
                "anchor_text": "Bidder A submitted a proposal",
                "quote_text": "Bidder A submitted a proposal",
                "quote_text_normalized": "bidder a submitted a proposal",
                "match_type": "exact",
                "resolution_note": None,
            },
        ]
    }


def _write_v2_raw_fixture(tmp_path: Path, *, slug: str = "imprivata") -> None:
    data_dir = tmp_path / "data"
    deals_source_dir = data_dir / "deals" / slug / "source"
    extract_v2_dir = data_dir / "skill" / slug / "extract_v2"
    raw_dir = tmp_path / "raw" / slug
    filings_dir = raw_dir / "filings"
    deals_source_dir.mkdir(parents=True, exist_ok=True)
    extract_v2_dir.mkdir(parents=True, exist_ok=True)
    filings_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "seeds.csv").write_text(
        "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
        f"{slug},TARGET,ACQUIRER,2016-07-13,https://example.com,false\n",
        encoding="utf-8",
    )
    (deals_source_dir / "chronology_blocks.jsonl").write_text(
        "\n".join(
            json.dumps(block)
            for block in [
                {
                    "block_id": "B001",
                    "document_id": "DOC001",
                    "ordinal": 1,
                    "start_line": 1,
                    "end_line": 1,
                    "raw_text": "Bidder A",
                    "clean_text": "Bidder A",
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
                    "raw_text": "Three finalists advanced",
                    "clean_text": "Three finalists advanced",
                    "is_heading": False,
                    "page_break_before": False,
                    "page_break_after": False,
                    "date_mentions": [],
                    "entity_mentions": [],
                    "evidence_density": 0,
                    "temporal_phase": "other",
                },
                {
                    "block_id": "B003",
                    "document_id": "DOC001",
                    "ordinal": 3,
                    "start_line": 3,
                    "end_line": 3,
                    "raw_text": "Bidder A submitted a proposal",
                    "clean_text": "Bidder A submitted a proposal",
                    "is_heading": False,
                    "page_break_before": False,
                    "page_break_after": False,
                    "date_mentions": [],
                    "entity_mentions": [],
                    "evidence_density": 0,
                    "temporal_phase": "other",
                },
            ]
        )
        + "\n",
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
    (filings_dir / "DOC001.txt").write_text(
        "Bidder A\nThree finalists advanced\nBidder A submitted a proposal\n",
        encoding="utf-8",
    )
    (extract_v2_dir / "observations_raw.json").write_text(
        json.dumps(_raw_observations_payload()),
        encoding="utf-8",
    )


def _write_v2_canonical_fixture(tmp_path: Path, *, slug: str = "imprivata") -> None:
    paths = build_skill_paths(slug, project_root=tmp_path)
    paths.extract_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.observations_path.write_text(
        json.dumps(_canonical_observations_payload()),
        encoding="utf-8",
    )
    paths.spans_v2_path.write_text(json.dumps(_spans_payload()), encoding="utf-8")


def test_canonicalize_v2_upgrades_quote_first_observations_to_span_backed_schema(
    tmp_path: Path,
) -> None:
    _write_v2_raw_fixture(tmp_path)

    run_canonicalize_v2("imprivata", project_root=tmp_path)

    paths = build_skill_paths("imprivata", project_root=tmp_path)
    observations = json.loads(paths.observations_path.read_text(encoding="utf-8"))
    spans = json.loads(paths.spans_v2_path.read_text(encoding="utf-8"))

    assert observations["parties"][0]["evidence_span_ids"] == ["span_0001"]
    assert observations["cohorts"][0]["evidence_span_ids"] == ["span_0002"]
    assert observations["observations"][0]["evidence_span_ids"] == ["span_0003"]
    assert [span["span_id"] for span in spans["spans"]] == [
        "span_0001",
        "span_0002",
        "span_0003",
    ]
    assert paths.observations_raw_path.exists()


def test_canonicalize_v2_is_idempotent_on_existing_canonical_extract(tmp_path: Path) -> None:
    _write_v2_canonical_fixture(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    before_spans = json.loads(paths.spans_v2_path.read_text(encoding="utf-8"))

    run_canonicalize_v2("imprivata", project_root=tmp_path)
    run_canonicalize_v2("imprivata", project_root=tmp_path)

    observations = json.loads(paths.observations_path.read_text(encoding="utf-8"))
    assert observations["parties"][0]["party_id"] == "party_bidder_a"
    assert observations["parties"][0]["evidence_span_ids"] == ["span_0001"]
    assert observations["cohorts"][0]["cohort_id"] == "cohort_finalists"
    assert observations["cohorts"][0]["evidence_span_ids"] == ["span_0002"]
    assert observations["observations"][0]["observation_id"] == "obs_proposal"
    assert observations["observations"][0]["evidence_span_ids"] == ["span_0003"]
    assert json.loads(paths.spans_v2_path.read_text(encoding="utf-8")) == before_spans


def test_canonicalize_v2_cli_runs_on_quote_first_fixture(tmp_path: Path) -> None:
    _write_v2_raw_fixture(tmp_path)

    exit_code = cli.main(
        [
            "canonicalize-v2",
            "--deal",
            "imprivata",
            "--project-root",
            str(tmp_path),
        ]
    )

    paths = build_skill_paths("imprivata", project_root=tmp_path)
    observations = json.loads(paths.observations_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert observations["observations"][0]["observation_id"] == "obs_proposal"


# ---------------------------------------------------------------------------
# Repair: forward requested_by_observation_id
# ---------------------------------------------------------------------------


def _raw_payload_with_forward_ref(*, forward: bool) -> dict:
    """Build a raw payload where a proposal links to a solicitation.

    If *forward* is True the solicitation date is after the proposal date
    (temporal inversion).  If False the solicitation precedes the proposal.
    """
    base = _raw_observations_payload()
    solicitation_date = "2026-04-15" if forward else "2026-03-15"
    base["quotes"].append(
        {"quote_id": "Q201", "block_id": "B001", "text": "Bidder A"},
    )
    base["observations"] = [
        {
            "observation_id": "obs_solicitation",
            "obs_type": "solicitation",
            "date": _resolved_date_payload(solicitation_date),
            "subject_refs": [],
            "counterparty_refs": [],
            "summary": "The board requested final bids.",
            "quote_ids": ["Q201"],
            "requested_submission": "best_and_final",
            "binding_level": "binding",
            "due_date": None,
            "recipient_refs": [],
            "attachments": [],
        },
        {
            "observation_id": "obs_proposal",
            "obs_type": "proposal",
            "date": _resolved_date_payload("2026-03-31"),
            "subject_refs": ["party_bidder_a"],
            "counterparty_refs": [],
            "summary": "Bidder A submitted a proposal.",
            "quote_ids": ["Q101"],
            "requested_by_observation_id": "obs_solicitation",
            "revises_observation_id": None,
            "delivery_mode": "written",
            "terms": None,
            "mentions_non_binding": None,
            "includes_draft_merger_agreement": False,
            "includes_markup": False,
        },
    ]
    return base


def test_canonicalize_v2_nullifies_forward_requested_by(tmp_path: Path) -> None:
    _write_v2_raw_fixture(tmp_path)
    extract_dir = tmp_path / "data" / "skill" / "imprivata" / "extract_v2"
    extract_dir.mkdir(parents=True, exist_ok=True)
    (extract_dir / "observations_raw.json").write_text(
        json.dumps(_raw_payload_with_forward_ref(forward=True)),
        encoding="utf-8",
    )

    run_canonicalize_v2("imprivata", project_root=tmp_path)

    paths = build_skill_paths("imprivata", project_root=tmp_path)
    observations = json.loads(paths.observations_path.read_text(encoding="utf-8"))
    proposal = next(
        o for o in observations["observations"] if o["obs_type"] == "proposal"
    )
    assert proposal["requested_by_observation_id"] is None


def test_canonicalize_v2_preserves_valid_requested_by(tmp_path: Path) -> None:
    _write_v2_raw_fixture(tmp_path)
    extract_dir = tmp_path / "data" / "skill" / "imprivata" / "extract_v2"
    extract_dir.mkdir(parents=True, exist_ok=True)
    (extract_dir / "observations_raw.json").write_text(
        json.dumps(_raw_payload_with_forward_ref(forward=False)),
        encoding="utf-8",
    )

    run_canonicalize_v2("imprivata", project_root=tmp_path)

    paths = build_skill_paths("imprivata", project_root=tmp_path)
    observations = json.loads(paths.observations_path.read_text(encoding="utf-8"))
    proposal = next(
        o for o in observations["observations"] if o["obs_type"] == "proposal"
    )
    assert proposal["requested_by_observation_id"] == "obs_solicitation"


# ---------------------------------------------------------------------------
# Repair: outcome bidder refs
# ---------------------------------------------------------------------------


def _raw_payload_with_outcome(*, bidder_in_refs: bool, bidder_in_summary: bool) -> dict:
    """Build a raw payload with an executed outcome.

    *bidder_in_refs*: whether the bidder party_id is already in subject_refs.
    *bidder_in_summary*: whether the summary text names the bidder.
    """
    base = _raw_observations_payload()
    summary = (
        "Bidder A and the target executed the merger agreement."
        if bidder_in_summary
        else "The merger agreement was executed."
    )
    base["observations"] = [
        {
            "observation_id": "obs_outcome",
            "obs_type": "outcome",
            "date": _resolved_date_payload(),
            "subject_refs": ["party_bidder_a"] if bidder_in_refs else [],
            "counterparty_refs": [],
            "summary": summary,
            "quote_ids": ["Q101"],
            "outcome_kind": "executed",
            "related_observation_id": None,
        },
    ]
    return base


def test_canonicalize_v2_repairs_outcome_bidder_refs_from_summary(
    tmp_path: Path,
) -> None:
    _write_v2_raw_fixture(tmp_path)
    extract_dir = tmp_path / "data" / "skill" / "imprivata" / "extract_v2"
    extract_dir.mkdir(parents=True, exist_ok=True)
    (extract_dir / "observations_raw.json").write_text(
        json.dumps(_raw_payload_with_outcome(bidder_in_refs=False, bidder_in_summary=True)),
        encoding="utf-8",
    )

    run_canonicalize_v2("imprivata", project_root=tmp_path)

    paths = build_skill_paths("imprivata", project_root=tmp_path)
    observations = json.loads(paths.observations_path.read_text(encoding="utf-8"))
    outcome = next(
        o for o in observations["observations"] if o["obs_type"] == "outcome"
    )
    assert "party_bidder_a" in outcome["subject_refs"]


def test_canonicalize_v2_preserves_existing_outcome_bidder_refs(
    tmp_path: Path,
) -> None:
    _write_v2_raw_fixture(tmp_path)
    extract_dir = tmp_path / "data" / "skill" / "imprivata" / "extract_v2"
    extract_dir.mkdir(parents=True, exist_ok=True)
    (extract_dir / "observations_raw.json").write_text(
        json.dumps(_raw_payload_with_outcome(bidder_in_refs=True, bidder_in_summary=True)),
        encoding="utf-8",
    )

    run_canonicalize_v2("imprivata", project_root=tmp_path)

    paths = build_skill_paths("imprivata", project_root=tmp_path)
    observations = json.loads(paths.observations_path.read_text(encoding="utf-8"))
    outcome = next(
        o for o in observations["observations"] if o["obs_type"] == "outcome"
    )
    assert outcome["subject_refs"].count("party_bidder_a") == 1


def test_canonicalize_v2_no_false_positive_bidder_injection(
    tmp_path: Path,
) -> None:
    _write_v2_raw_fixture(tmp_path)
    extract_dir = tmp_path / "data" / "skill" / "imprivata" / "extract_v2"
    extract_dir.mkdir(parents=True, exist_ok=True)
    (extract_dir / "observations_raw.json").write_text(
        json.dumps(_raw_payload_with_outcome(bidder_in_refs=False, bidder_in_summary=False)),
        encoding="utf-8",
    )

    run_canonicalize_v2("imprivata", project_root=tmp_path)

    paths = build_skill_paths("imprivata", project_root=tmp_path)
    observations = json.loads(paths.observations_path.read_text(encoding="utf-8"))
    outcome = next(
        o for o in observations["observations"] if o["obs_type"] == "outcome"
    )
    assert outcome["subject_refs"] == []
