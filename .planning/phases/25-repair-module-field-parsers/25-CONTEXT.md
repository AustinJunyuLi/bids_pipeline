# Phase 25: Repair Module + Field Parsers - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

A standalone deterministic repair module that extracts structured fields from
observation summaries and linked evidence spans. Covers price extraction
(`per_share`, `range_low/high`), consideration type, delivery mode, bidder kind
classification, and secondary booleans (`mentions_non_binding`,
`includes_draft_merger_agreement`, `includes_markup`). Includes comprehensive
unit tests for all parser and classifier paths.

Does NOT wire into `canonicalize.py` (Phase 26), add gates (Phase 27), or
modify prompts (Phase 28).

</domain>

<decisions>
## Implementation Decisions

### Module placement
- **D-01:** New module at `skill_pipeline/repair/structured_fields_v2.py` — separate from canonicalize.py to keep it lean and each parser independently testable
- **D-02:** Single entry point: `repair_structured_fields(observations_dict, spans)` — canonicalize.py calls one function; the repair module coordinates all sub-repairs internally
- **D-03:** Existing repairs (`_repair_forward_requested_by`, `_repair_outcome_bidder_refs`) stay in canonicalize.py — don't touch working code, new module handles only GPT Pro review scope

### Parser confidence rules
- **D-04:** Fill-only semantics — populate null/missing fields, never overwrite populated values except harmless normalization (inverted range swap)
- **D-05:** Summary-only cues are sufficient to fill — summary is already filing-grounded LLM output from the same extraction; emit info-level log
- **D-06:** When summary and span text disagree (e.g., different prices), do NOT fill — emit a structured warning instead so gates or human review can resolve
- **D-07:** Structured repair log — return a list of RepairAction objects alongside the mutated dict, enabling downstream metrics, gate input, and audit trail (not just Python logging)

### Bidder kind strategy
- **D-08:** Parse-and-propagate parenthetical lists — regex-parse parenthetical body (e.g., "three financial sponsors (Sponsor A, Sponsor B and Thoma Bravo)"), match named parties by alias, assign the list's kind to all matched parties
- **D-09:** Moderate sponsor lexicon (20-30 names) as last-resort fallback — subordinate to all filing-local evidence; never overrides contradictory filing text
- **D-10:** Conservative confidence rule — set `bidder_kind` only when one class has strong dominant evidence; ambiguous cases stay `unknown`

### Test fixture scope
- **D-11:** Synthetic text snippets for all parser unit tests — hand-crafted sentences isolating each pattern, no filing dependency
- **D-12:** Single test file with `@pytest.mark.parametrize` — `tests/test_skill_structured_field_repairs_v2.py` covers all parser and classifier paths

### Claude's Discretion
- Internal module structure (how parsers are organized within the repair package)
- Exact regex patterns (GPT Pro review provides starting patterns, Claude may refine)
- RepairAction model design (fields, severity levels)
- Specific PE firm names in the sponsor lexicon
- Subject-aware clause restriction implementation details
- Handling of edge cases not explicitly covered above

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design anchor
- `diagnosis/gptpro/2026-04-04/round_1/response.md` — Complete design specification including regex patterns, decision logic, confidence rules, implementation order, and field-by-field guidance

### Existing repair pattern
- `skill_pipeline/canonicalize.py` lines 162-254 — Two existing repair functions (`_repair_forward_requested_by`, `_repair_outcome_bidder_refs`) that define the dict-mutation pattern the new module must follow
- `skill_pipeline/canonicalize.py` lines 286-292 — Integration point where repairs run before final Pydantic validation

### Data models
- `skill_pipeline/models_v2.py` — Canonical observation models: `PartyRecord` (has `bidder_kind`), `ProposalObservationV2` (has `terms: MoneyTerms`, `delivery_mode`), `MoneyTerms` (has `per_share`, `range_low`, `range_high`, `consideration_type`)
- `skill_pipeline/extract_artifacts_v2.py` — `LoadedObservationArtifacts` with `observation_index`, `party_index`, `span_index` for lookup

### Normalization baseline
- `skill_pipeline/normalize/extraction.py` — Existing field normalization (`per_share` string→Decimal cleanup) that runs BEFORE repair; repair must not duplicate this work

### Test patterns
- `tests/test_skill_canonicalize_v2.py` — Fixture builder pattern (`_raw_observations_payload`, `_canonical_observations_payload`)
- `tests/test_skill_gates_v2.py` — Gate test pattern using `clone_payload()` and `write_v2_validation_fixture()`
- `tests/_v2_validation_fixtures.py` — Shared canonical payload builders

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `LoadedObservationArtifacts.span_index` — dict[span_id, SpanRecord] for span text lookup
- `LoadedObservationArtifacts.party_index` — dict[party_id, PartyRecord] for bidder alias resolution
- `normalize/extraction.py::clean_per_share()` — already handles `"$21.50"` → `Decimal("21.50")` format normalization
- `_v2_validation_fixtures.py` — canonical payload builders for test fixtures

### Established Patterns
- Repairs mutate dicts in-place and return the mutated dict
- Repairs log at INFO level with observation_id context
- Gate findings use `GateFindingV2` model with gate_id, rule_id, severity, observation_ids
- Tests use pytest `tmp_path`, `clone_payload()`, and `write_v2_validation_fixture()`

### Integration Points
- New module called from `canonicalize.py` after quote→span upgrade, before Pydantic validation (Phase 26 wires this)
- RepairAction log consumed by gates (Phase 27) for cue-backed completeness checks
- Parser patterns inform prompt hardening (Phase 28)

</code_context>

<specifics>
## Specific Ideas

- GPT Pro review provides detailed regex starting patterns for MONEY, PRICE_HEADLINE_RE, PRICE_RANGE_RE, PRICE_COMPONENT_GUARD_RE, EXPLICIT_CASH_RE, EXPLICIT_STOCK_RE, EXPLICIT_MIXED_RE, and delivery mode maps — use these as the implementation baseline
- Subject-aware clause restriction is the key safeguard preventing wrong-bidder price backfill in bundled summaries
- Decision order for consideration_type: mixed first, then cash, then stock — apply within narrow window around selected price clause
- Delivery mode priority: email > phone > oral > written > other — "emailed a written proposal" → email

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 25-repair-module-field-parsers*
*Context gathered: 2026-04-04*
