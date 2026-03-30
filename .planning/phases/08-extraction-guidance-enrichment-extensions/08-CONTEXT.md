# Phase 8: Extraction Guidance + Enrichment Extensions - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Update the extraction skill docs so the local-agent workflow reliably captures
round milestones, verbal/oral priced indications, and NDA exclusions, then
extend deterministic enrichment so Phase 8 adds filing-grounded `DropTarget`
classification and contextual `all_cash` support without mutating extract
artifacts.

This phase does not re-extract deals, repair Zep/Medivation artifacts, or run
the 9-deal validation sweep. Those remain Phase 9 work.

</domain>

<decisions>
## Implementation Decisions

### Skill-Doc Scope And Ownership
- **D-01:** Edit `.claude/skills/extract-deal/SKILL.md` as the canonical skill
  source, then sync `.codex/skills/` and `.cursor/skills/` from it with
  `scripts/sync_skill_mirrors.py`. Do not hand-edit the mirrors independently.
- **D-02:** Round milestone guidance stays inside the existing six round event
  types already supported by the schema:
  `final_round_inf_ann`, `final_round_inf`, `final_round_ann`, `final_round`,
  `final_round_ext_ann`, and `final_round_ext`. Phase 8 adds extraction
  guidance and examples, not new event types or new round fields.
- **D-03:** Verbal or oral whole-company bids with explicit economics are still
  `proposal` events. "Oral" or "verbal" affects the event summary, notes, and
  formality signals; it does not make the event ineligible for extraction.
- **D-04:** NDA exclusion remains a skill-doc behavior change, not a schema
  expansion. Rollover equity agreements, bidder-bidder teaming agreements, and
  non-target diligence agreements stay out of `nda` events unless the filing
  clearly ties them to target sale-process diligence. Phase 8 should not add
  `nda_subtype`.

### Deterministic Dropout Classification
- **D-05:** Reuse the existing `DropoutClassification` label vocabulary and the
  existing `dropout_classifications` key inside
  `deterministic_enrichment.json`. Do not create a second deterministic dropout
  artifact or a parallel label set.
- **D-06:** The deterministic layer should stay sparse and conservative: Phase
  8 emits `DropTarget` only when target-initiated exclusion is filing-grounded
  by round invitation context and/or explicit exclusion language in
  `drop_reason_text`. Other drop events can remain unlabeled in deterministic
  enrichment so downstream export still falls back to generic `Drop`.
- **D-07:** `DropTarget` directionality must match the existing
  `.claude/skills/enrich-deal/SKILL.md` rule: if the bidder first signals it
  will not improve, will not continue, or cannot proceed, that event is not
  `DropTarget` just because the target later confirms exclusion.

### Contextual All-Cash Inference
- **D-08:** Do not rewrite `terms.consideration_type` in extract artifacts or
  canonical events. Contextual `all_cash` is an enrichment/export concern and
  must travel through an explicit deterministic override path.
- **D-09:** Add an auditable deterministic `all_cash` override keyed by
  event_id, or an equivalent nullable enrichment-table column, so `db-load` and
  `db-export` can prefer the inferred value before falling back to
  `events.terms_consideration_type`.
- **D-10:** `all_cash` inference is cycle-local and fail-closed. Propagate
  `true` only when cash consideration is unambiguous from executed deal context
  or the same-cycle proposal set. Never infer through mixed/CVR structures
  (for example Providence & Worcester), and never override explicit mixed or
  non-cash terms.

### Validation And Rollout
- **D-11:** Phase 8 must ship deterministic regression tests together with the
  doc changes. Runtime tests should cover `DropTarget` and `all_cash`
  propagation using synthetic fixtures inspired by live cases; skill-level
  validation should cover mirror sync and the new extraction guidance text.
- **D-12:** Phase 8 stops at docs plus deterministic runtime/output wiring.
  Re-extraction, artifact repair, and reconciliation reruns remain Phase 9.

### the agent's Discretion
- Exact phrasing and example selection inside the skill docs, as long as the
  examples are filing-grounded and reinforce the decisions above
- Exact field name for the deterministic `all_cash` override, as long as it is
  explicit, auditable, and separate from extract literals
- Whether `DropTarget` detection starts from round invitation deltas,
  `drop_reason_text`, or both, as long as target directionality is preserved

</decisions>

<specifics>
## Specific Ideas

- `stec` already contains formal-round announcement/deadline pairs plus an
  extension pair (`evt_017` / `evt_018` / `evt_021` / `evt_022`). Use it as
  the primary round-milestone example in extraction guidance.
- `mac-gray` already contains oral priced proposal patterns
  (`evt_013`, `evt_020`), and `penford` has another oral priced proposal
  example (`evt_005`). Use those to clarify that oral bids with explicit price
  still count as `proposal`.
- `petsmart-inc` includes a note about an earlier oral indication before the
  final written bid; that is a useful boundary example for distinguishing oral
  proposal extraction from mere narrative recap.
- `saks`, `mac-gray`, `stec`, and `providence-worcester` are the strongest
  committee-narrowing / target-exclusion reference deals for `DropTarget`.
- `penford` and `petsmart-inc` are the positive examples for contextual
  `all_cash`; `providence-worcester` is the negative guardrail because the deal
  includes cash plus CVR and must not be inferred as all-cash.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope
- `.planning/ROADMAP.md` — Phase 8 goal, dependency on Phase 7, and success
  criteria for EXTRACT-01/02/03 and ENRICH-02/03
- `.planning/REQUIREMENTS.md` — Phase 8 requirement mapping and milestone
  boundaries
- `.planning/PROJECT.md` — correctness-first, filing-grounded, fail-fast repo
  constraints

### Prior Context
- `.planning/phases/06-deterministic-hardening/06-CONTEXT.md` — Phase 6
  decision to keep NDA exclusion schema-neutral and defer `nda_subtype`
- `.planning/phases/07-bid-type-rule-priority/07-CONTEXT.md` — Phase 7 bid
  classification context that Phase 8 skill docs must now describe accurately

### Skill Contracts
- `.claude/skills/extract-deal/SKILL.md` — canonical extraction workflow and
  event/formality schema guidance
- `.claude/skills/enrich-deal/SKILL.md` — existing dropout taxonomy and
  directionality rules to align deterministic `DropTarget` behavior with
  interpretive enrichment
- `scripts/sync_skill_mirrors.py` — required mirror-sync path after editing
  `.claude/skills/`
- `tests/test_skill_mirror_sync.py` — enforcement for `.claude` ->
  `.codex` / `.cursor` parity

### Runtime Surfaces
- `skill_pipeline/enrich_core.py` — current deterministic enrichment entry
  point; rounds and bid classifications already live here
- `skill_pipeline/models.py` — `DropoutClassification`,
  `SkillEnrichmentArtifact`, and event-model fields that Phase 8 must extend
  without breaking
- `skill_pipeline/db_load.py` — deterministic enrichment ingestion plus
  optional interpretive overlay behavior
- `skill_pipeline/db_export.py` — current `all_cash` export behavior and drop
  note fallback logic
- `skill_pipeline/db_schema.py` — current enrichment-table columns; likely
  touchpoint for deterministic `all_cash` override plumbing

### Prompt And Example Assets
- `skill_pipeline/prompt_assets/event_examples.md` — few-shot examples already
  shipped with extract prompts; Phase 8 should expand or align these with the
  new guidance
- `docs/plans/2026-03-16-prompt-engineering-spec.md` — prior event taxonomy
  and proposal/formality guidance for extraction

### Evidence Corpus
- `data/reconciliation_cross_deal_analysis.md` — Phase 8 rationale for round
  milestones, `DropTarget`, contextual `all_cash`, and verbal indications
- `docs/CollectionInstructions_Alex_2026.qmd` — benchmark-side framing for
  `DropTarget` and final-round milestone rows; diagnostic only, not generation
  authority

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.claude/skills/extract-deal/SKILL.md` already defines the event taxonomy,
  formality-signal fields, and exclusion model. Phase 8 extends that document
  rather than inventing a separate extraction spec.
- `.claude/skills/enrich-deal/SKILL.md` already defines the full dropout label
  vocabulary and `DropTarget` directionality. Phase 8 can reuse that contract
  for deterministic enrichment instead of introducing new terms.
- `skill_pipeline/enrich_core.py` already computes round pairing before bid
  classification, which gives Phase 8 a natural deterministic foundation for
  target-exclusion detection.
- `skill_pipeline/db_load.py` already reads deterministic enrichment first and
  then overlays optional interpretive dropout labels from `enrichment.json`,
  which supports adding sparse deterministic dropout rows without a second file.

### Established Patterns
- Canonical workflow docs live only under `.claude/skills/`; mirrors are
  derived artifacts.
- Deterministic runtime stages write auditable JSON artifacts and avoid
  mutating upstream extract artifacts.
- Export logic currently derives `all_cash` from
  `events.terms_consideration_type`, so contextual inference needs a new
  explicit downstream path rather than a silent overwrite.

### Integration Points
- `skill_pipeline/enrich_core.py` + `skill_pipeline/models.py` for new
  deterministic enrichment fields
- `skill_pipeline/db_schema.py`, `skill_pipeline/db_load.py`, and
  `skill_pipeline/db_export.py` for `all_cash` override plumbing
- `.claude/skills/extract-deal/SKILL.md`,
  `skill_pipeline/prompt_assets/event_examples.md`, and
  `docs/plans/2026-03-16-prompt-engineering-spec.md` for extraction guidance
  updates
- `tests/test_skill_enrich_core.py`, `tests/test_skill_db_load.py`,
  `tests/test_skill_db_export.py`, and `tests/test_skill_mirror_sync.py` for
  regression coverage

</code_context>

<deferred>
## Deferred Ideas

- `nda_subtype` schema support across raw/canonical models, gates, coverage,
  enrichment, DB load, and export — broader than this phase's doc-level NDA
  exclusion scope
- Full deterministic `DropBelowM`, `DropBelowInf`, and `DropAtInf`
  classification — interpretive enrichment already owns those richer labels
- Re-extracting affected deals and measuring reconciliation gains — Phase 9
- Additional bid-type refinements beyond the current deterministic rule set —
  outside this phase's extraction/doc + enrichment-extension scope

</deferred>

---

*Phase: 08-extraction-guidance-enrichment-extensions*
*Context gathered: 2026-03-30*
