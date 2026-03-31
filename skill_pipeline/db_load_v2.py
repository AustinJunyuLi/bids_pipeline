from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.db_schema import open_pipeline_db
from skill_pipeline.extract_artifacts_v2 import load_observation_artifacts
from skill_pipeline.models_v2 import CoverageFindingsArtifactV2, DerivedArtifactV2, ObservationArtifactV2
from skill_pipeline.paths import build_skill_paths


def run_db_load_v2(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    paths = build_skill_paths(deal_slug, project_root=project_root)
    required_paths = [
        paths.observations_path,
        paths.spans_v2_path,
        paths.derivations_path,
        paths.coverage_v2_findings_path,
    ]
    for path in required_paths:
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    artifacts = load_observation_artifacts(paths, mode="canonical")
    if artifacts.observations is None:
        raise ValueError("db-load-v2 requires canonical v2 observation artifacts")
    if artifacts.derivations is None:
        raise ValueError("db-load-v2 requires derive artifacts")

    coverage = CoverageFindingsArtifactV2.model_validate(
        _read_json(paths.coverage_v2_findings_path)
    )

    con = open_pipeline_db(paths.database_path)
    in_transaction = False
    try:
        con.execute("BEGIN TRANSACTION")
        in_transaction = True
        _delete_v2_deal(con, deal_slug)
        _load_parties(con, deal_slug, artifacts.observations)
        _load_cohorts(con, deal_slug, artifacts.observations)
        _load_observations(con, deal_slug, artifacts.observations)
        _load_derivations(con, deal_slug, artifacts.derivations)
        _load_coverage_checks(con, deal_slug, coverage)
        con.execute("COMMIT")
        in_transaction = False
    except Exception:
        if in_transaction:
            con.execute("ROLLBACK")
        raise
    finally:
        con.close()
    return 0


def _delete_v2_deal(con, deal_slug: str) -> None:
    for table_name in (
        "v2_parties",
        "v2_cohorts",
        "v2_observations",
        "v2_derivations",
        "v2_coverage_checks",
    ):
        con.execute(f"DELETE FROM {table_name} WHERE deal_slug = ?", [deal_slug])


def _load_parties(con, deal_slug: str, artifact: ObservationArtifactV2) -> None:
    rows = [
        (
            deal_slug,
            party.party_id,
            party.display_name,
            party.canonical_name,
            party.aliases,
            party.role,
            party.bidder_kind,
            party.advisor_kind,
            party.advised_party_id,
            party.listing_status,
            party.geography,
            party.evidence_span_ids,
        )
        for party in artifact.parties
    ]
    if not rows:
        return
    con.executemany(
        """
        INSERT INTO v2_parties (
            deal_slug,
            party_id,
            display_name,
            canonical_name,
            aliases,
            role,
            bidder_kind,
            advisor_kind,
            advised_party_id,
            listing_status,
            geography,
            evidence_span_ids
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _load_cohorts(con, deal_slug: str, artifact: ObservationArtifactV2) -> None:
    rows = [
        (
            deal_slug,
            cohort.cohort_id,
            cohort.label,
            cohort.parent_cohort_id,
            cohort.exact_count,
            cohort.known_member_party_ids,
            cohort.unknown_member_count,
            cohort.membership_basis,
            cohort.created_by_observation_id,
            cohort.evidence_span_ids,
        )
        for cohort in artifact.cohorts
    ]
    if not rows:
        return
    con.executemany(
        """
        INSERT INTO v2_cohorts (
            deal_slug,
            cohort_id,
            label,
            parent_cohort_id,
            exact_count,
            known_member_party_ids,
            unknown_member_count,
            membership_basis,
            created_by_observation_id,
            evidence_span_ids
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _load_observations(con, deal_slug: str, artifact: ObservationArtifactV2) -> None:
    rows = []
    for observation in artifact.observations:
        payload = observation.model_dump(mode="json")
        type_fields = {
            key: value
            for key, value in payload.items()
            if key
            not in {
                "observation_id",
                "obs_type",
                "date",
                "subject_refs",
                "counterparty_refs",
                "summary",
                "evidence_span_ids",
            }
        }
        rows.append(
            (
                deal_slug,
                observation.observation_id,
                observation.obs_type,
                observation.date.raw_text if observation.date else None,
                observation.date.sort_date if observation.date else None,
                observation.date.precision.value if observation.date else None,
                observation.subject_refs,
                observation.counterparty_refs,
                observation.summary,
                observation.evidence_span_ids,
                json.dumps(type_fields, sort_keys=True),
            )
        )
    if not rows:
        return
    con.executemany(
        """
        INSERT INTO v2_observations (
            deal_slug,
            observation_id,
            obs_type,
            date_raw_text,
            date_sort,
            date_precision,
            subject_refs,
            counterparty_refs,
            summary,
            evidence_span_ids,
            type_fields
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _load_derivations(con, deal_slug: str, artifact: DerivedArtifactV2) -> None:
    rows = []
    for record_type, record_id, record in _iter_derivations(artifact):
        rows.append(
            (
                deal_slug,
                record_id,
                record_type,
                record.basis.rule_id,
                record.basis.confidence,
                record.basis.source_observation_ids,
                record.basis.source_span_ids,
                json.dumps(record.model_dump(mode="json"), sort_keys=True),
            )
        )
    if not rows:
        return
    con.executemany(
        """
        INSERT INTO v2_derivations (
            deal_slug,
            record_id,
            record_type,
            rule_id,
            confidence,
            source_observation_ids,
            source_span_ids,
            record_fields
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _iter_derivations(artifact: DerivedArtifactV2):
    for phase in artifact.phases:
        yield "phase", phase.phase_id, phase
    for transition in artifact.transitions:
        yield "transition", transition.transition_id, transition
    for cash_regime in artifact.cash_regimes:
        yield "cash_regime", cash_regime.cash_regime_id, cash_regime
    for judgment in artifact.judgments:
        yield "judgment", judgment.judgment_id, judgment
    for analyst_row in artifact.analyst_rows:
        yield "analyst_row", analyst_row.row_id, analyst_row


def _load_coverage_checks(
    con,
    deal_slug: str,
    artifact: CoverageFindingsArtifactV2,
) -> None:
    rows = [
        (
            deal_slug,
            finding.cue_family,
            finding.status,
            finding.supporting_observation_ids,
            finding.supporting_span_ids,
            finding.reason_code,
            finding.note,
        )
        for finding in artifact.findings
    ]
    if not rows:
        return
    con.executemany(
        """
        INSERT INTO v2_coverage_checks (
            deal_slug,
            cue_family,
            status,
            supporting_observation_ids,
            supporting_span_ids,
            reason_code,
            note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
