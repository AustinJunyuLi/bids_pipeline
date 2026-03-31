from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.check_v2 import run_check_v2
from skill_pipeline.paths import build_skill_paths
from tests._v2_validation_fixtures import (
    canonical_observations_payload,
    clone_payload,
    spans_payload,
    write_v2_validation_fixture,
)


def _report(tmp_path: Path, slug: str = "stec") -> dict:
    paths = build_skill_paths(slug, project_root=tmp_path)
    return json.loads(paths.check_v2_report_path.read_text(encoding="utf-8"))


def test_check_v2_passes_on_valid_canonical_fixture(tmp_path: Path) -> None:
    write_v2_validation_fixture(tmp_path)

    exit_code = run_check_v2("stec", project_root=tmp_path)
    report = _report(tmp_path)

    assert exit_code == 0
    assert report["summary"]["status"] == "pass"
    assert report["findings"] == []


def test_check_v2_blocks_observation_without_evidence_span(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    proposal = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_proposal"
    )
    proposal["evidence_span_ids"] = []
    write_v2_validation_fixture(tmp_path, observations_payload=observations)

    exit_code = run_check_v2("stec", project_root=tmp_path)
    report = _report(tmp_path)

    assert exit_code == 1
    assert report["summary"]["status"] == "fail"
    assert report["findings"][0]["check_id"] == "observation_evidence_required"
    assert report["findings"][0]["observation_ids"] == ["obs_proposal"]


def test_check_v2_blocks_unresolved_party_or_cohort_refs(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    proposal = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_proposal"
    )
    proposal["subject_refs"] = ["party_missing"]
    write_v2_validation_fixture(tmp_path, observations_payload=observations)

    exit_code = run_check_v2("stec", project_root=tmp_path)
    report = _report(tmp_path)

    assert exit_code == 1
    assert report["summary"]["status"] == "fail"
    assert report["findings"][0]["check_id"] == "observation_entity_ref_missing"
    assert report["findings"][0]["observation_ids"] == ["obs_proposal"]


def test_check_v2_blocks_bidderless_proposal_subjects(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    proposal = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_proposal"
    )
    proposal["subject_refs"] = ["party_target"]
    write_v2_validation_fixture(tmp_path, observations_payload=observations)

    exit_code = run_check_v2("stec", project_root=tmp_path)
    report = _report(tmp_path)

    finding = next(
        finding
        for finding in report["findings"]
        if finding["check_id"] == "proposal_bidder_subject_required"
    )
    assert exit_code == 1
    assert finding["observation_ids"] == ["obs_proposal"]


def test_check_v2_blocks_agreement_superseding_non_agreement(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    agreement = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_nda"
    )
    agreement["supersedes_observation_id"] = "obs_proposal"
    write_v2_validation_fixture(tmp_path, observations_payload=observations)

    exit_code = run_check_v2("stec", project_root=tmp_path)
    report = _report(tmp_path)

    finding = next(
        finding
        for finding in report["findings"]
        if finding["check_id"] == "agreement_supersedes_non_agreement"
    )
    assert exit_code == 1
    assert finding["observation_ids"] == ["obs_nda", "obs_proposal"]


def test_check_v2_blocks_unknown_span_references(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    spans = clone_payload(spans_payload())
    spans["spans"] = [span for span in spans["spans"] if span["span_id"] != "span_proposal"]
    write_v2_validation_fixture(tmp_path, observations_payload=observations, spans=spans)

    exit_code = run_check_v2("stec", project_root=tmp_path)
    report = _report(tmp_path)

    finding = next(
        finding
        for finding in report["findings"]
        if finding["check_id"] == "observation_span_ref_missing"
    )
    assert exit_code == 1
    assert finding["observation_ids"] == ["obs_proposal"]
