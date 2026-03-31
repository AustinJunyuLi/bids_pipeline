from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.coverage_v2 import run_coverage_v2
from skill_pipeline.paths import build_skill_paths
from tests._v2_validation_fixtures import (
    canonical_observations_payload,
    clone_payload,
    write_v2_validation_fixture,
)


def _load_outputs(tmp_path: Path, slug: str = "stec") -> tuple[dict, dict]:
    paths = build_skill_paths(slug, project_root=tmp_path)
    findings = json.loads(paths.coverage_v2_findings_path.read_text(encoding="utf-8"))
    summary = json.loads(paths.coverage_v2_summary_path.read_text(encoding="utf-8"))
    return findings, summary


def test_coverage_v2_records_observed_matches_for_literal_cues(tmp_path: Path) -> None:
    write_v2_validation_fixture(tmp_path)

    exit_code = run_coverage_v2("stec", project_root=tmp_path)
    findings, summary = _load_outputs(tmp_path)

    proposal = next(
        finding
        for finding in findings["findings"]
        if finding["cue_family"] == "proposal"
    )
    assert exit_code == 0
    assert summary["status"] == "pass"
    assert summary["finding_count"] == 0
    assert summary["error_count"] == 0
    assert summary["warning_count"] == 0
    assert proposal["status"] == "observed"
    assert proposal["severity"] == "info"
    assert proposal["reason_code"] == "matched_observation"
    assert proposal["supporting_observation_ids"] == ["obs_proposal"]


def test_coverage_v2_treats_multiple_matching_nda_observations_as_covered(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    observations["observations"].append(
        {
            "observation_id": "obs_nda_duplicate",
            "obs_type": "agreement",
            "date": observations["observations"][2]["date"],
            "subject_refs": ["party_bidder_a"],
            "counterparty_refs": ["party_target"],
            "summary": "Bidder A also signed a duplicate confidentiality agreement record.",
            "evidence_span_ids": ["span_nda"],
            "agreement_kind": "nda",
            "signed": True,
            "grants_diligence_access": True,
            "includes_standstill": False,
            "consideration_type": None,
            "supersedes_observation_id": None,
            "other_detail": None,
        }
    )
    write_v2_validation_fixture(tmp_path, observations_payload=observations)

    exit_code = run_coverage_v2("stec", project_root=tmp_path)
    findings, summary = _load_outputs(tmp_path)

    nda = next(
        finding
        for finding in findings["findings"]
        if finding["cue_family"] == "nda"
    )
    assert exit_code == 0
    assert summary["status"] == "pass"
    assert summary["finding_count"] == 0
    assert summary["error_count"] == 0
    assert summary["warning_count"] == 0
    assert nda["status"] == "observed"
    assert nda["severity"] == "info"
    assert nda["reason_code"] == "matched_multiple_observations"
    assert nda["supporting_observation_ids"] == ["obs_nda", "obs_nda_duplicate"]


def test_coverage_v2_fails_when_high_confidence_proposal_cue_is_uncovered(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    observations["observations"] = [
        observation
        for observation in observations["observations"]
        if observation["observation_id"] != "obs_proposal"
    ]
    write_v2_validation_fixture(tmp_path, observations_payload=observations)

    exit_code = run_coverage_v2("stec", project_root=tmp_path)
    findings, summary = _load_outputs(tmp_path)

    proposal = next(
        finding
        for finding in findings["findings"]
        if finding["cue_family"] == "proposal"
    )
    assert exit_code == 1
    assert summary["status"] == "fail"
    assert proposal["status"] == "not_found"
    assert proposal["reason_code"] == "uncovered_proposal_cue"
    assert proposal["supporting_observation_ids"] == []


def test_coverage_v2_marks_multiple_matching_proposals_as_ambiguous(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    observations["observations"].append(
        {
            "observation_id": "obs_proposal_alt",
            "obs_type": "proposal",
            "date": observations["observations"][3]["date"],
            "subject_refs": ["party_bidder_a"],
            "counterparty_refs": ["party_target"],
            "summary": "Bidder A also submitted a companion indication of interest.",
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
        }
    )
    write_v2_validation_fixture(tmp_path, observations_payload=observations)

    exit_code = run_coverage_v2("stec", project_root=tmp_path)
    findings, summary = _load_outputs(tmp_path)

    proposal = next(
        finding
        for finding in findings["findings"]
        if finding["cue_family"] == "proposal"
    )
    assert exit_code == 1
    assert summary["status"] == "fail"
    assert proposal["status"] == "ambiguous"
    assert proposal["reason_code"] == "multiple_matching_candidates"
    assert proposal["supporting_observation_ids"] == ["obs_proposal", "obs_proposal_alt"]
