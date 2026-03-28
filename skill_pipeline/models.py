from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skill_pipeline.pipeline_models.common import DatePrecision, QuoteMatchType


class SkillModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StageStatus(StrEnum):
    MISSING = "missing"
    PASS = "pass"
    FAIL = "fail"


class SkillPathSet(SkillModel):
    project_root: Path
    data_dir: Path
    database_path: Path
    deals_root: Path
    skill_data_root: Path
    raw_root: Path
    seeds_path: Path
    deal_slug: str
    source_dir: Path
    chronology_blocks_path: Path
    evidence_items_path: Path
    document_registry_path: Path
    skill_root: Path
    extract_dir: Path
    check_dir: Path
    verify_dir: Path
    coverage_dir: Path
    enrich_dir: Path
    export_dir: Path
    actors_raw_path: Path
    events_raw_path: Path
    spans_path: Path
    check_report_path: Path
    verification_log_path: Path
    verification_findings_path: Path
    coverage_findings_path: Path
    coverage_summary_path: Path
    gates_dir: Path
    gates_report_path: Path
    enrichment_path: Path
    deterministic_enrichment_path: Path
    deal_events_path: Path
    canonicalize_dir: Path
    canonicalize_log_path: Path
    prompt_dir: Path
    prompt_packets_dir: Path
    prompt_manifest_path: Path


class SeedEntry(SkillModel):
    deal_slug: str
    target_name: str
    acquirer: str | None = None
    date_announced: str | None = None
    primary_url: str | None = None
    is_reference: bool


class QuoteEntry(SkillModel):
    quote_id: str
    block_id: str
    text: str


class RawCountAssertion(SkillModel):
    subject: str
    count: int
    quote_ids: list[str] = Field(default_factory=list)


class RawSkillActorRecord(SkillModel):
    actor_id: str
    display_name: str
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    role: Literal["bidder", "advisor", "activist", "target_board"]
    advisor_kind: Literal["financial", "legal", "other"] | None = None
    advised_actor_id: str | None = None
    bidder_kind: Literal["strategic", "financial"] | None = None
    listing_status: Literal["public", "private"] | None = None
    geography: Literal["domestic", "non_us"] | None = None
    is_grouped: bool
    group_size: int | None = None
    group_label: str | None = None
    quote_ids: list[str]
    notes: list[str] = Field(default_factory=list)


class RawSkillActorsArtifact(SkillModel):
    quotes: list[QuoteEntry]
    actors: list[RawSkillActorRecord]
    count_assertions: list[RawCountAssertion] = Field(default_factory=list)
    unresolved_mentions: list[str] = Field(default_factory=list)


class DateHint(SkillModel):
    raw_text: str | None = None
    normalized_hint: str | None = None


class ResolvedDate(SkillModel):
    raw_text: str | None = None
    normalized_start: date | None = None
    normalized_end: date | None = None
    sort_date: date | None = None
    precision: DatePrecision = DatePrecision.UNKNOWN
    anchor_event_id: str | None = None
    anchor_span_id: str | None = None
    resolution_note: str | None = None
    is_inferred: bool = False


class SpanRecord(SkillModel):
    span_id: str
    document_id: str
    accession_number: str | None = None
    filing_type: str
    start_line: int
    end_line: int
    start_char: int | None = None
    end_char: int | None = None
    block_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    anchor_text: str | None = None
    quote_text: str
    quote_text_normalized: str
    match_type: QuoteMatchType
    resolution_note: str | None = None


class SpanRegistryArtifact(SkillModel):
    spans: list[SpanRecord] = Field(default_factory=list)


class MoneyTerms(SkillModel):
    per_share: Decimal | None = None
    range_low: Decimal | None = None
    range_high: Decimal | None = None
    enterprise_value: Decimal | None = None
    consideration_type: Literal["cash", "stock", "mixed", "other"] | None = None


class FormalitySignals(SkillModel):
    contains_range: bool
    mentions_indication_of_interest: bool
    mentions_preliminary: bool
    mentions_non_binding: bool
    mentions_binding_offer: bool
    includes_draft_merger_agreement: bool
    includes_marked_up_agreement: bool
    requested_binding_offer_via_process_letter: bool
    after_final_round_announcement: bool
    after_final_round_deadline: bool
    is_subject_to_financing: bool | None = None


class RawSkillEventRecord(SkillModel):
    event_id: str
    event_type: Literal[
        "target_sale",
        "target_sale_public",
        "bidder_sale",
        "bidder_interest",
        "activist_sale",
        "sale_press_release",
        "bid_press_release",
        "ib_retention",
        "nda",
        "proposal",
        "drop",
        "final_round_inf_ann",
        "final_round_inf",
        "final_round_ann",
        "final_round",
        "final_round_ext_ann",
        "final_round_ext",
        "executed",
        "terminated",
        "restarted",
    ]
    date: DateHint
    actor_ids: list[str] = Field(default_factory=list)
    summary: str
    quote_ids: list[str]
    terms: MoneyTerms | None = None
    formality_signals: FormalitySignals | None = None
    whole_company_scope: bool | None = None
    drop_reason_text: str | None = None
    round_scope: Literal["formal", "informal"] | None = None
    invited_actor_ids: list[str] = Field(default_factory=list)
    deadline_date: DateHint | None = None
    executed_with_actor_id: str | None = None
    boundary_note: str | None = None
    nda_signed: bool | None = None
    notes: list[str] = Field(default_factory=list)


class CountAssertion(SkillModel):
    subject: str
    count: int
    evidence_span_ids: list[str] = Field(default_factory=list)


class SkillActorRecord(SkillModel):
    actor_id: str
    display_name: str
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    role: Literal["bidder", "advisor", "activist", "target_board"]
    advisor_kind: Literal["financial", "legal", "other"] | None = None
    advised_actor_id: str | None = None
    bidder_kind: Literal["strategic", "financial"] | None = None
    listing_status: Literal["public", "private"] | None = None
    geography: Literal["domestic", "non_us"] | None = None
    is_grouped: bool
    group_size: int | None = None
    group_label: str | None = None
    evidence_span_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class SkillActorsArtifact(SkillModel):
    actors: list[SkillActorRecord]
    count_assertions: list[CountAssertion] = Field(default_factory=list)
    unresolved_mentions: list[str] = Field(default_factory=list)


class SkillEventRecord(SkillModel):
    event_id: str
    event_type: Literal[
        "target_sale",
        "target_sale_public",
        "bidder_sale",
        "bidder_interest",
        "activist_sale",
        "sale_press_release",
        "bid_press_release",
        "ib_retention",
        "nda",
        "proposal",
        "drop",
        "final_round_inf_ann",
        "final_round_inf",
        "final_round_ann",
        "final_round",
        "final_round_ext_ann",
        "final_round_ext",
        "executed",
        "terminated",
        "restarted",
    ]
    date: ResolvedDate
    actor_ids: list[str] = Field(default_factory=list)
    summary: str
    evidence_span_ids: list[str] = Field(default_factory=list)
    terms: MoneyTerms | None = None
    formality_signals: FormalitySignals | None = None
    whole_company_scope: bool | None = None
    drop_reason_text: str | None = None
    round_scope: Literal["formal", "informal"] | None = None
    invited_actor_ids: list[str] = Field(default_factory=list)
    deadline_date: ResolvedDate | None = None
    executed_with_actor_id: str | None = None
    boundary_note: str | None = None
    nda_signed: bool | None = None
    notes: list[str] = Field(default_factory=list)


class SkillExclusionRecord(SkillModel):
    category: Literal[
        "partial_company_bid",
        "unsigned_nda",
        "stale_process_reference",
        "duplicate_mention",
        "non_event_context",
        "other",
    ]
    block_ids: list[str] = Field(default_factory=list)
    explanation: str


class RawSkillEventsArtifact(SkillModel):
    quotes: list[QuoteEntry]
    events: list[RawSkillEventRecord]
    exclusions: list[SkillExclusionRecord] = Field(default_factory=list)
    coverage_notes: list[str] = Field(default_factory=list)


class SkillEventsArtifact(SkillModel):
    events: list[SkillEventRecord]
    exclusions: list[SkillExclusionRecord] = Field(default_factory=list)
    coverage_notes: list[str] = Field(default_factory=list)


class VerificationFinding(SkillModel):
    check_type: str
    severity: Literal["error", "warning"]
    repairability: Literal["repairable", "non_repairable"] | None = None
    description: str
    actor_ids: list[str] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    actor_id: str | None = None
    event_id: str | None = None
    anchor_text: str | None = None
    span_ids: list[str] = Field(default_factory=list)
    block_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class VerificationFix(SkillModel):
    finding_index: int
    action: str
    old_value: Any | None = None
    new_value: Any | None = None


class VerificationRound(SkillModel):
    findings: list[VerificationFinding] = Field(default_factory=list)
    fixes_applied: list[VerificationFix] = Field(default_factory=list)


class VerificationRoundTwo(SkillModel):
    findings: list[VerificationFinding] = Field(default_factory=list)
    status: Literal["pass", "fail"]


class VerificationLogSummary(SkillModel):
    total_checks: int
    round_1_errors: int
    round_1_warnings: int
    fixes_applied: int
    round_2_errors: int
    round_2_warnings: int
    status: Literal["pass", "fail"]


class SkillVerificationLog(SkillModel):
    round_1: VerificationRound
    round_2: VerificationRoundTwo
    summary: VerificationLogSummary

    @model_validator(mode="after")
    def validate_round_two_status(self) -> "SkillVerificationLog":
        if self.round_2.status != self.summary.status:
            raise ValueError("round_2.status must match summary.status")
        return self


class DropoutClassification(SkillModel):
    label: Literal["Drop", "DropBelowM", "DropBelowInf", "DropAtInf", "DropTarget"]
    basis: str
    source_text: str


class BidClassification(SkillModel):
    label: Literal["Formal", "Informal", "Uncertain"]
    rule_applied: float | None = None
    basis: str


class RoundRecord(SkillModel):
    announcement_event_id: str
    deadline_event_id: str | None = None
    round_scope: Literal["formal", "informal", "extension"]
    invited_actor_ids: list[str] = Field(default_factory=list)
    active_bidders_at_time: int
    is_selective: bool


class CycleRecord(SkillModel):
    cycle_id: str
    start_event_id: str
    end_event_id: str
    boundary_basis: str


class FormalBoundaryRecord(SkillModel):
    event_id: str | None = None
    basis: str


class InitiationJudgment(SkillModel):
    type: Literal["target_driven", "bidder_driven", "activist_driven", "mixed"]
    basis: str
    source_text: str
    confidence: Literal["high", "medium", "low"]


class AdvisoryVerificationRecord(SkillModel):
    advised_actor_id: str | None = None
    verified: bool
    source_text: str


class CountReconciliationRecord(SkillModel):
    assertion: str
    extracted_count: int
    classification: Literal[
        "advisor_exclusion",
        "stale_process",
        "unnamed_aggregate",
        "filing_approximation",
        "consortium_counted_once",
        "partial_bidder_excluded",
        "unresolved",
    ] | None = None
    note: str


class SkillEnrichmentArtifact(SkillModel):
    dropout_classifications: dict[str, DropoutClassification]
    bid_classifications: dict[str, BidClassification]
    rounds: list[RoundRecord]
    cycles: list[CycleRecord]
    formal_boundary: dict[str, FormalBoundaryRecord]
    initiation_judgment: InitiationJudgment
    advisory_verification: dict[str, AdvisoryVerificationRecord]
    count_reconciliation: list[CountReconciliationRecord]
    review_flags: list[str]


class CheckFinding(SkillModel):
    check_id: str
    severity: Literal["blocker", "warning"]
    description: str
    actor_ids: list[str] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)


class CheckReportSummary(SkillModel):
    blocker_count: int
    warning_count: int
    status: Literal["pass", "fail"]


class SkillCheckReport(SkillModel):
    findings: list[CheckFinding] = Field(default_factory=list)
    summary: CheckReportSummary


class CoverageFinding(SkillModel):
    cue_family: str
    severity: Literal["error", "warning"]
    repairability: Literal["repairable", "non_repairable"] | None = None
    description: str
    block_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]
    suggested_event_types: list[str] = Field(default_factory=list)


class CoverageFindingsArtifact(SkillModel):
    findings: list[CoverageFinding] = Field(default_factory=list)


class CoverageSummary(SkillModel):
    status: Literal["pass", "fail"]
    finding_count: int
    error_count: int
    warning_count: int
    counts_by_cue_family: dict[str, int] = Field(default_factory=dict)


class GateFinding(SkillModel):
    gate_id: str
    rule_id: str
    severity: Literal["blocker", "warning"]
    description: str
    event_ids: list[str] = Field(default_factory=list)
    actor_ids: list[str] = Field(default_factory=list)
    block_ids: list[str] = Field(default_factory=list)


class GateAttentionDecay(SkillModel):
    quartile_counts: list[int]
    hot_spots: list[dict] = Field(default_factory=list)
    decay_score: float
    note: str | None = None


class GateReportSummary(SkillModel):
    blocker_count: int
    warning_count: int
    status: Literal["pass", "fail"]


class GateReport(SkillModel):
    findings: list[GateFinding] = Field(default_factory=list)
    attention_decay: GateAttentionDecay | None = None
    summary: GateReportSummary


class ExtractStageSummary(SkillModel):
    status: StageStatus
    actor_count: int = 0
    event_count: int = 0
    proposal_count: int = 0


class CheckStageSummary(SkillModel):
    status: StageStatus
    blocker_count: int = 0
    warning_count: int = 0


class CoverageStageSummary(SkillModel):
    status: StageStatus
    error_count: int = 0
    warning_count: int = 0


class VerifyStageSummary(SkillModel):
    status: StageStatus
    round_1_errors: int = 0
    fixes_applied: int = 0
    round_2_status: Literal["pass", "fail"] | None = None


class EnrichStageSummary(SkillModel):
    status: StageStatus
    cycle_count: int = 0
    formal_bid_count: int = 0
    informal_bid_count: int = 0
    initiation_judgment_type: str | None = None
    review_flags_count: int = 0


class GatesStageSummary(SkillModel):
    status: StageStatus
    blocker_count: int = 0
    warning_count: int = 0


class DbLoadStageSummary(SkillModel):
    status: StageStatus
    actor_rows: int = 0
    event_rows: int = 0
    span_rows: int = 0


class DbExportStageSummary(SkillModel):
    status: StageStatus
    event_rows: int = 0
    output_path: Path


class ExportStageSummary(SkillModel):
    status: StageStatus
    output_path: Path


class PromptStageSummary(SkillModel):
    status: StageStatus
    packet_count: int = 0
    actor_packet_count: int = 0
    event_packet_count: int = 0


class DealAgentSummary(SkillModel):
    deal_slug: str
    seed: SeedEntry
    paths: SkillPathSet
    prompt: PromptStageSummary
    extract: ExtractStageSummary
    check: CheckStageSummary
    coverage: CoverageStageSummary
    gates: GatesStageSummary
    verify: VerifyStageSummary
    enrich: EnrichStageSummary
    db_load: DbLoadStageSummary
    db_export: DbExportStageSummary
    export: ExportStageSummary
