"""Structured coverage audit for canonical v2 observation artifacts."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.coverage_cues import (
    CRITICAL_CUE_FAMILIES,
    CoverageCue,
    build_coverage_cues,
    load_chronology_blocks,
    load_evidence_items,
    severity_for_cue,
)
from skill_pipeline.extract_artifacts_v2 import (
    LoadedObservationArtifacts,
    load_observation_artifacts,
)
from skill_pipeline.models import CoverageSummary
from skill_pipeline.models_v2 import (
    AgreementObservation,
    CoverageCheckRecordV2,
    CoverageFindingsArtifactV2,
    ProcessObservation,
    ProposalObservation,
    StatusObservation,
)
from skill_pipeline.paths import build_skill_paths, ensure_output_directories

DROP_STATUS_KINDS = frozenset(
    {
        "withdrew",
        "not_interested",
        "cannot_improve",
        "cannot_proceed",
        "limited_assets_only",
        "excluded",
    }
)
PROCESS_CUE_KINDS = frozenset({"sale_launch", "public_announcement", "press_release"})


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")


def _span_ids_overlap(
    cue: CoverageCue,
    span_ids: list[str],
    span_index,
) -> bool:
    cue_block_ids = set(cue.block_ids)
    cue_evidence_ids = set(cue.evidence_ids)
    for span_id in span_ids:
        span = span_index.get(span_id)
        if span is None:
            continue
        if cue_evidence_ids and span.evidence_ids and cue_evidence_ids.intersection(span.evidence_ids):
            return True
        if cue_block_ids.intersection(span.block_ids):
            return True
    return False


def _actor_hint_matches_party(hint: str, display_name: str) -> bool:
    """Check whether an actor hint token-overlaps with a party display_name."""
    hint_tokens = set(re.sub(r"[^a-z0-9 ]", " ", hint.lower()).split())
    name_tokens = set(re.sub(r"[^a-z0-9 ]", " ", display_name.lower()).split())
    # Remove trivially common tokens
    noise = {"the", "a", "an", "of", "and", "or", "inc", "corp", "llc", "lp"}
    # Single-letter suffixes are meaningful identities in proxy labels
    # such as "Party A" and "Bidder B", so only strip longer noise tokens.
    hint_tokens = {token for token in hint_tokens if not (len(token) > 1 and token in noise)}
    name_tokens = {token for token in name_tokens if not (len(token) > 1 and token in noise)}
    if not hint_tokens:
        return False
    hint_identity_tokens = {token for token in hint_tokens if len(token) == 1}
    name_identity_tokens = {token for token in name_tokens if len(token) == 1}
    if hint_identity_tokens and name_identity_tokens:
        return bool(hint_identity_tokens & name_identity_tokens)
    return bool(hint_tokens & name_tokens)


def _observation_actor_matches_cue(
    observation,
    cue: CoverageCue,
    artifacts: LoadedObservationArtifacts,
) -> bool:
    """Check if observation's subject party matches any of the cue's actor hints."""
    if not cue.actor_hints:
        return True  # No actor constraint — any match is fine

    observations = artifacts.observations
    if observations is None:
        return True

    party_index = {p.party_id: p for p in observations.parties}

    # Check observation subject_refs against actor hints
    subject_refs = getattr(observation, "subject_refs", []) or []
    for ref in subject_refs:
        party = party_index.get(ref)
        if party is None:
            continue
        for hint in cue.actor_hints:
            if _actor_hint_matches_party(hint, party.display_name):
                return True

    return False


def _matching_candidates(
    cue: CoverageCue,
    artifacts: LoadedObservationArtifacts,
) -> tuple[list[str], list[str], list[str], list[str]]:
    observation_ids: list[str] = []
    party_ids: list[str] = []
    cohort_ids: list[str] = []
    span_ids: set[str] = set()

    observations = artifacts.observations
    if observations is None:
        return observation_ids, party_ids, cohort_ids, []

    # First pass: collect all type+span matches
    type_span_matches: list[tuple[object, str]] = []
    for observation in observations.observations:
        if not _observation_matches_cue_family(observation, cue.cue_family):
            continue
        if _span_ids_overlap(cue, observation.evidence_span_ids, artifacts.span_index):
            type_span_matches.append((observation, observation.observation_id))

    # Actor check is a tie-breaker: only filter when multiple type+span matches
    # exist AND the cue has actor hints. This prevents false negatives from
    # proxy name mismatches (e.g., "Sponsor A" vs extracted "Thoma Bravo").
    if len(type_span_matches) > 1 and cue.actor_hints:
        actor_matches = [
            (obs, oid) for obs, oid in type_span_matches
            if _observation_actor_matches_cue(obs, cue, artifacts)
        ]
        # Use actor-filtered matches if any survived; otherwise keep all
        if actor_matches:
            type_span_matches = actor_matches

    for observation, oid in type_span_matches:
        observation_ids.append(oid)
        span_ids.update(observation.evidence_span_ids)

    if cue.cue_family == "advisor":
        for party in observations.parties:
            if party.role != "advisor":
                continue
            if _span_ids_overlap(cue, party.evidence_span_ids, artifacts.span_index):
                party_ids.append(party.party_id)
                span_ids.update(party.evidence_span_ids)

    return (
        sorted(set(observation_ids)),
        sorted(set(party_ids)),
        sorted(set(cohort_ids)),
        sorted(span_ids),
    )


def _observation_matches_cue_family(observation, cue_family: str) -> bool:
    if cue_family == "proposal":
        return isinstance(observation, ProposalObservation)
    if cue_family == "nda":
        return isinstance(observation, AgreementObservation) and observation.agreement_kind == "nda"
    if cue_family == "withdrawal_or_drop":
        return isinstance(observation, StatusObservation) and observation.status_kind in DROP_STATUS_KINDS
    if cue_family == "bidder_interest":
        return isinstance(observation, StatusObservation) and observation.status_kind == "expressed_interest"
    if cue_family == "process_initiation":
        return isinstance(observation, ProcessObservation) and (
            observation.process_kind in PROCESS_CUE_KINDS
            or observation.process_kind == "advisor_retention"
        )
    if cue_family == "advisor":
        return isinstance(observation, ProcessObservation) and observation.process_kind == "advisor_retention"
    return False


def _build_record(
    cue: CoverageCue,
    artifacts: LoadedObservationArtifacts,
) -> CoverageCheckRecordV2:
    issue_severity = severity_for_cue(cue)
    if issue_severity is None:
        raise ValueError(f"Unsupported cue severity for v2 coverage cue {cue.cue_family!r}")

    observation_ids, party_ids, cohort_ids, span_ids = _matching_candidates(cue, artifacts)
    total_matches = len(observation_ids) + len(party_ids) + len(cohort_ids)

    if total_matches == 0:
        status = "not_found"
        repairability = "repairable"
        description = (
            f"{cue.confidence.capitalize()}-confidence {cue.cue_family} cue was not covered "
            "by canonical v2 artifacts."
        )
        reason_code = f"uncovered_{cue.cue_family}_cue"
    elif total_matches == 1:
        status = "observed"
        repairability = None
        description = (
            f"{cue.confidence.capitalize()}-confidence {cue.cue_family} cue is covered by "
            "canonical v2 artifacts."
        )
        if observation_ids:
            reason_code = "matched_observation"
        elif party_ids:
            reason_code = "matched_party"
        else:
            reason_code = "matched_cohort"
    elif cue.cue_family == "nda" and observation_ids and not party_ids and not cohort_ids:
        status = "observed"
        repairability = None
        description = (
            f"{cue.confidence.capitalize()}-confidence {cue.cue_family} cue is covered by "
            "multiple canonical v2 observations."
        )
        reason_code = "matched_multiple_observations"
    else:
        status = "ambiguous"
        repairability = "repairable"
        description = (
            f"{cue.confidence.capitalize()}-confidence {cue.cue_family} cue matched multiple "
            "canonical v2 candidates."
        )
        reason_code = "multiple_matching_candidates"

    severity = "info" if status in {"observed", "derived"} else issue_severity

    return CoverageCheckRecordV2(
        cue_family=cue.cue_family,
        status=status,
        severity=severity,
        repairability=repairability,
        description=description,
        reason_code=reason_code,
        block_ids=cue.block_ids,
        evidence_ids=cue.evidence_ids,
        matched_terms=cue.matched_terms,
        confidence=cue.confidence,
        suggested_event_types=cue.suggested_event_types,
        supporting_span_ids=span_ids,
        supporting_observation_ids=observation_ids,
        supporting_party_ids=party_ids,
        supporting_cohort_ids=cohort_ids,
    )


def _bidder_inventory_findings(
    cues: list[CoverageCue],
    artifacts: LoadedObservationArtifacts,
) -> list[CoverageCheckRecordV2]:
    """Check that every actor mentioned in critical cues has a corresponding extracted party.

    This is the "Bidder 3 was missed entirely" detector: if a proposal or NDA cue
    mentions Party C but no extracted party with role=bidder matches, emit an error.
    """
    if artifacts.observations is None:
        return []

    bidder_names = {
        p.display_name
        for p in artifacts.observations.parties
        if p.role == "bidder"
    }

    # Only consider actor hints that look like bidder identifiers, not firm names
    # "Party A", "Bidder 2", "Company C", "Sponsor B" are bidder patterns
    # "Goldman Sachs", "Merrill Lynch", "J.P. Morgan" are typically advisors
    _BIDDER_PATTERN = re.compile(r"^(?:Party|Bidder|Company|Sponsor)\s+[A-Z0-9]$")

    # Collect actor hints from critical cues only
    actor_to_evidence: dict[str, list[str]] = {}
    actor_to_blocks: dict[str, list[str]] = {}
    for cue in cues:
        if cue.cue_family not in CRITICAL_CUE_FAMILIES:
            continue
        if cue.confidence != "high":
            continue
        if not cue.actor_hints:
            continue
        for hint in cue.actor_hints:
            # Only flag structured bidder identifiers, not firm names or committees
            if not _BIDDER_PATTERN.match(hint):
                continue
            actor_to_evidence.setdefault(hint, []).extend(cue.evidence_ids)
            actor_to_blocks.setdefault(hint, []).extend(cue.block_ids)

    findings: list[CoverageCheckRecordV2] = []
    for actor_hint, evidence_ids in sorted(actor_to_evidence.items()):
        # Check if any extracted bidder matches this actor hint
        matched = any(
            _actor_hint_matches_party(actor_hint, name)
            for name in bidder_names
        )
        if not matched:
            findings.append(
                CoverageCheckRecordV2(
                    cue_family="bidder_inventory",
                    status="not_found",
                    severity="error",
                    repairability="repairable",
                    description=(
                        f"Actor '{actor_hint}' appears in high-confidence critical cues "
                        f"(proposal/NDA/drop) but no extracted party with role=bidder matches."
                    ),
                    reason_code="missing_bidder_party",
                    block_ids=sorted(set(actor_to_blocks.get(actor_hint, []))),
                    evidence_ids=sorted(set(evidence_ids)),
                    matched_terms=[actor_hint],
                    confidence="high",
                    suggested_event_types=["proposal", "nda"],
                )
            )
    return findings


def _actor_roster_findings(
    blocks: list,
    artifacts: LoadedObservationArtifacts,
) -> list[CoverageCheckRecordV2]:
    """Check that named party aliases in chronology blocks have corresponding extracted parties.

    Scans BlockEntityMention where entity_type == 'party_alias' and checks against
    extracted parties. Only flags aliases appearing 2+ times (filters incidental mentions).
    """
    if artifacts.observations is None:
        return []

    # Count party alias mentions across all blocks
    alias_counts: Counter[str] = Counter()
    alias_blocks: dict[str, list[str]] = {}
    for block in blocks:
        for mention in getattr(block, "entity_mentions", []):
            if mention.entity_type == "party_alias":
                raw = mention.raw_text.strip()
                alias_counts[raw] += 1
                alias_blocks.setdefault(raw, []).append(block.block_id)

    party_names = {p.display_name for p in artifacts.observations.parties}

    findings: list[CoverageCheckRecordV2] = []
    for alias, count in sorted(alias_counts.items()):
        if count < 2:
            continue
        # Skip non-bidder aliases
        if re.match(r"(?i)(?:the company|the board|special committee|transaction committee)", alias):
            continue
        matched = any(_actor_hint_matches_party(alias, name) for name in party_names)
        if not matched:
            findings.append(
                CoverageCheckRecordV2(
                    cue_family="actor_roster",
                    status="not_found",
                    severity="warning",
                    repairability="repairable",
                    description=(
                        f"Party alias '{alias}' appears {count} times in chronology blocks "
                        f"but no extracted party matches."
                    ),
                    reason_code="missing_roster_party",
                    block_ids=sorted(set(alias_blocks.get(alias, []))),
                    evidence_ids=[],
                    matched_terms=[alias],
                    confidence="medium",
                    suggested_event_types=[],
                )
            )
    return findings


_COUNT_WORD_MAP = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
}


def _parse_count(hint: str) -> int | None:
    """Parse a count hint like 'five parties' or '9 bidders' into an integer."""
    match = re.match(r"(\d+|[a-z]+)\s+", hint.lower())
    if not match:
        return None
    word = match.group(1)
    if word.isdigit():
        return int(word)
    return _COUNT_WORD_MAP.get(word)


def _count_assertion_findings(
    cues: list[CoverageCue],
    artifacts: LoadedObservationArtifacts,
) -> list[CoverageCheckRecordV2]:
    """Check that count assertions in cues match cohort exact_counts."""
    if artifacts.observations is None:
        return []

    cohort_counts = {
        c.exact_count
        for c in artifacts.observations.cohorts
    }

    findings: list[CoverageCheckRecordV2] = []
    seen_counts: set[int] = set()
    for cue in cues:
        if not cue.count_hint:
            continue
        count = _parse_count(cue.count_hint)
        if count is None or count in seen_counts:
            continue
        seen_counts.add(count)
        if count not in cohort_counts:
            findings.append(
                CoverageCheckRecordV2(
                    cue_family="count_assertion",
                    status="not_found",
                    severity="warning",
                    repairability="repairable",
                    description=(
                        f"Filing asserts '{cue.count_hint}' but no cohort with "
                        f"exact_count={count} was extracted."
                    ),
                    reason_code="missing_count_cohort",
                    block_ids=cue.block_ids,
                    evidence_ids=cue.evidence_ids,
                    matched_terms=[cue.count_hint],
                    confidence=cue.confidence,
                    suggested_event_types=[],
                )
            )
    return findings


def _build_summary(records: list[CoverageCheckRecordV2]) -> CoverageSummary:
    issue_records = [record for record in records if record.severity != "info"]
    counter = Counter(record.cue_family for record in issue_records)
    error_count = sum(1 for record in issue_records if record.severity == "error")
    warning_count = sum(1 for record in issue_records if record.severity == "warning")
    return CoverageSummary(
        status="fail" if error_count > 0 else "pass",
        finding_count=len(issue_records),
        error_count=error_count,
        warning_count=warning_count,
        counts_by_cue_family=dict(counter),
    )


def run_coverage_v2(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Run deterministic source coverage against canonical v2 observation artifacts."""
    paths = build_skill_paths(deal_slug, project_root=project_root)
    artifacts = load_observation_artifacts(paths, mode="canonical")
    blocks = load_chronology_blocks(paths.chronology_blocks_path)
    evidence_items = load_evidence_items(paths.evidence_items_path)
    cues = build_coverage_cues(evidence_items, blocks)
    records = [
        _build_record(cue, artifacts)
        for cue in cues
        if severity_for_cue(cue) is not None
    ]

    # Layer 1: Bidder inventory — error-level if actor in critical cue has no party
    records.extend(_bidder_inventory_findings(cues, artifacts))

    # Layer 2: Actor roster — warning-level if party alias in blocks has no party
    records.extend(_actor_roster_findings(blocks, artifacts))

    # Layer 2: Count assertions — warning-level if count hint has no matching cohort
    records.extend(_count_assertion_findings(cues, artifacts))

    summary = _build_summary(records)

    ensure_output_directories(paths)
    _write_json(paths.coverage_v2_findings_path, CoverageFindingsArtifactV2(findings=records))
    _write_json(paths.coverage_v2_summary_path, summary)
    return 1 if summary.status == "fail" else 0
