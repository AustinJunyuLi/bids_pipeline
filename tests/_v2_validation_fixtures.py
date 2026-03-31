from __future__ import annotations

import copy
import json
from pathlib import Path

from skill_pipeline.paths import build_skill_paths


def resolved_date_payload(day: str) -> dict:
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


def canonical_observations_payload() -> dict:
    return {
        "parties": [
            {
                "party_id": "party_target",
                "display_name": "Company",
                "canonical_name": "COMPANY",
                "aliases": [],
                "role": "other",
                "bidder_kind": None,
                "advisor_kind": None,
                "advised_party_id": None,
                "listing_status": "public",
                "geography": "domestic",
                "evidence_span_ids": ["span_target"],
            },
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
                "evidence_span_ids": ["span_bidder"],
            },
            {
                "party_id": "party_advisor",
                "display_name": "Advisor Bank",
                "canonical_name": "ADVISOR BANK",
                "aliases": [],
                "role": "advisor",
                "bidder_kind": None,
                "advisor_kind": "financial",
                "advised_party_id": "party_target",
                "listing_status": None,
                "geography": None,
                "evidence_span_ids": ["span_advisor"],
            },
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
                "created_by_observation_id": "obs_solicit",
                "evidence_span_ids": ["span_cohort"],
            }
        ],
        "observations": [
            {
                "observation_id": "obs_process",
                "obs_type": "process",
                "date": resolved_date_payload("2026-03-01"),
                "subject_refs": ["party_target"],
                "counterparty_refs": [],
                "summary": "The Company began exploring a potential sale.",
                "evidence_span_ids": ["span_process"],
                "process_kind": "sale_launch",
                "process_scope": "target",
                "other_detail": None,
            },
            {
                "observation_id": "obs_solicit",
                "obs_type": "solicitation",
                "date": resolved_date_payload("2026-03-02"),
                "subject_refs": ["party_advisor"],
                "counterparty_refs": ["party_target"],
                "summary": "Advisor Bank requested indications of interest.",
                "evidence_span_ids": ["span_solicit"],
                "requested_submission": "ioi",
                "binding_level": "non_binding",
                "due_date": resolved_date_payload("2026-03-10"),
                "recipient_refs": ["cohort_finalists"],
                "attachments": [],
                "other_detail": None,
            },
            {
                "observation_id": "obs_nda",
                "obs_type": "agreement",
                "date": resolved_date_payload("2026-03-03"),
                "subject_refs": ["party_bidder_a"],
                "counterparty_refs": ["party_target"],
                "summary": "Bidder A entered into a confidentiality agreement.",
                "evidence_span_ids": ["span_nda"],
                "agreement_kind": "nda",
                "signed": True,
                "grants_diligence_access": True,
                "includes_standstill": False,
                "consideration_type": None,
                "supersedes_observation_id": None,
                "other_detail": None,
            },
            {
                "observation_id": "obs_proposal",
                "obs_type": "proposal",
                "date": resolved_date_payload("2026-03-08"),
                "subject_refs": ["party_bidder_a"],
                "counterparty_refs": ["party_target"],
                "summary": "Bidder A submitted a written indication of interest.",
                "evidence_span_ids": ["span_proposal"],
                "requested_by_observation_id": "obs_solicit",
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
                "other_detail": None,
            },
            {
                "observation_id": "obs_status",
                "obs_type": "status",
                "date": resolved_date_payload("2026-03-09"),
                "subject_refs": ["party_bidder_a"],
                "counterparty_refs": ["party_target"],
                "summary": "Bidder A was selected to advance.",
                "evidence_span_ids": ["span_status"],
                "status_kind": "selected_to_advance",
                "related_observation_id": "obs_proposal",
                "other_detail": None,
            },
        ],
        "exclusions": [],
        "coverage": [],
    }


def spans_payload() -> dict:
    return {
        "spans": [
            _span("span_target", "B000", [], "Company"),
            _span("span_bidder", "B000", [], "Bidder A"),
            _span("span_advisor", "B000", [], "Advisor Bank"),
            _span("span_cohort", "B004", [], "three finalists"),
            _span("span_process", "B001", ["DOC001:E0001"], "exploring a potential sale"),
            _span("span_solicit", "B004", [], "requested indications of interest"),
            _span("span_nda", "B002", ["DOC001:E0002"], "confidentiality agreement"),
            _span("span_proposal", "B003", ["DOC001:E0003"], "written indication of interest"),
            _span("span_status", "B005", [], "selected to advance"),
        ]
    }


def chronology_blocks_payload() -> list[dict]:
    return [
        _block("B000", 0, "Company, Bidder A, and Advisor Bank were identified."),
        _block("B001", 1, "The Company began exploring a potential sale."),
        _block("B002", 2, "Bidder A entered into a confidentiality agreement."),
        _block("B003", 3, "Bidder A submitted a written indication of interest."),
        _block("B004", 4, "Advisor Bank requested indications of interest from three finalists."),
        _block("B005", 5, "Bidder A was selected to advance."),
    ]


def evidence_items_payload() -> list[dict]:
    return [
        {
            "evidence_id": "DOC001:E0001",
            "document_id": "DOC001",
            "accession_number": "DOC001",
            "filing_type": "DEFM14A",
            "start_line": 1,
            "end_line": 1,
            "raw_text": "The Company began exploring a potential sale.",
            "evidence_type": "process_signal",
            "confidence": "high",
            "matched_terms": ["exploring a potential sale"],
            "date_text": "March 1, 2026",
            "actor_hint": "Company",
            "value_hint": None,
            "note": None,
        },
        {
            "evidence_id": "DOC001:E0002",
            "document_id": "DOC001",
            "accession_number": "DOC001",
            "filing_type": "DEFM14A",
            "start_line": 2,
            "end_line": 2,
            "raw_text": "Bidder A entered into a confidentiality agreement.",
            "evidence_type": "dated_action",
            "confidence": "high",
            "matched_terms": ["entered into", "confidentiality agreement"],
            "date_text": "March 3, 2026",
            "actor_hint": "Bidder A",
            "value_hint": None,
            "note": None,
        },
        {
            "evidence_id": "DOC001:E0003",
            "document_id": "DOC001",
            "accession_number": "DOC001",
            "filing_type": "DEFM14A",
            "start_line": 3,
            "end_line": 3,
            "raw_text": "Bidder A submitted a written indication of interest.",
            "evidence_type": "dated_action",
            "confidence": "high",
            "matched_terms": ["submitted", "written indication of interest"],
            "date_text": "March 8, 2026",
            "actor_hint": "Bidder A",
            "value_hint": None,
            "note": None,
        },
    ]


def write_v2_validation_fixture(
    tmp_path: Path,
    *,
    slug: str = "stec",
    observations_payload: dict | None = None,
    spans: dict | None = None,
    chronology_blocks: list[dict] | None = None,
    evidence_items: list[dict] | None = None,
) -> None:
    data_dir = tmp_path / "data"
    source_dir = data_dir / "deals" / slug / "source"
    source_dir.mkdir(parents=True, exist_ok=True)

    paths = build_skill_paths(slug, project_root=tmp_path)
    paths.extract_v2_dir.mkdir(parents=True, exist_ok=True)

    if observations_payload is None:
        observations_payload = canonical_observations_payload()
    if spans is None:
        spans = spans_payload()
    if chronology_blocks is None:
        chronology_blocks = chronology_blocks_payload()
    if evidence_items is None:
        evidence_items = evidence_items_payload()

    (data_dir / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},STEC INC,HGST,2013-06-01,https://example.com,false\n"
        ),
        encoding="utf-8",
    )
    (source_dir / "chronology_blocks.jsonl").write_text(
        "\n".join(json.dumps(block) for block in chronology_blocks) + "\n",
        encoding="utf-8",
    )
    (source_dir / "evidence_items.jsonl").write_text(
        "\n".join(json.dumps(item) for item in evidence_items) + "\n",
        encoding="utf-8",
    )
    paths.observations_path.write_text(json.dumps(observations_payload), encoding="utf-8")
    paths.spans_v2_path.write_text(json.dumps(spans), encoding="utf-8")


def write_v2_validation_reports(
    tmp_path: Path,
    *,
    slug: str = "stec",
    check_status: str = "pass",
    coverage_status: str = "pass",
    gates_status: str = "pass",
    coverage_findings: list[dict] | None = None,
) -> None:
    paths = build_skill_paths(slug, project_root=tmp_path)
    paths.check_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.coverage_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.gates_v2_dir.mkdir(parents=True, exist_ok=True)
    if coverage_findings is None:
        coverage_findings = []

    paths.check_v2_report_path.write_text(
        json.dumps(
            {
                "findings": [],
                "summary": {
                    "blocker_count": 0 if check_status == "pass" else 1,
                    "warning_count": 0,
                    "status": check_status,
                },
            }
        ),
        encoding="utf-8",
    )
    paths.coverage_v2_summary_path.write_text(
        json.dumps(
            {
                "status": coverage_status,
                "finding_count": len(coverage_findings) if coverage_status == "pass" else 1,
                "error_count": 0 if coverage_status == "pass" else 1,
                "warning_count": 0,
                "counts_by_cue_family": {},
            }
        ),
        encoding="utf-8",
    )
    paths.coverage_v2_findings_path.write_text(
        json.dumps({"findings": coverage_findings}),
        encoding="utf-8",
    )
    paths.gates_v2_report_path.write_text(
        json.dumps(
            {
                "findings": [],
                "summary": {
                    "blocker_count": 0 if gates_status == "pass" else 1,
                    "warning_count": 0,
                    "status": gates_status,
                },
            }
        ),
        encoding="utf-8",
    )


def clone_payload(payload):
    return copy.deepcopy(payload)


def _block(block_id: str, ordinal: int, raw_text: str) -> dict:
    return {
        "block_id": block_id,
        "document_id": "DOC001",
        "ordinal": ordinal,
        "start_line": max(1, ordinal),
        "end_line": max(1, ordinal),
        "raw_text": raw_text,
        "clean_text": raw_text,
        "is_heading": False,
        "page_break_before": False,
        "page_break_after": False,
        "date_mentions": [],
        "entity_mentions": [],
        "evidence_density": 0,
        "temporal_phase": "other",
    }


def _span(span_id: str, block_id: str, evidence_ids: list[str], anchor_text: str) -> dict:
    return {
        "span_id": span_id,
        "document_id": "DOC001",
        "accession_number": "DOC001",
        "filing_type": "DEFM14A",
        "start_line": 1,
        "end_line": 1,
        "start_char": None,
        "end_char": None,
        "block_ids": [block_id],
        "evidence_ids": evidence_ids,
        "anchor_text": anchor_text,
        "quote_text": anchor_text,
        "quote_text_normalized": anchor_text.lower(),
        "match_type": "exact",
        "resolution_note": None,
    }
