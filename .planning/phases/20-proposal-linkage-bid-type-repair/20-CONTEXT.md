# Phase 20: Proposal Linkage + Bid-Type Repair - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning
**Mode:** Auto-generated from the GPT Pro round_1 diagnosis

<domain>
## Phase Boundary

Repair the highest-value proposal fidelity gaps without widening scope into the
later export/taxonomy phases:

1. make proposal-to-solicitation association chronology-safe
2. stop trusting future-linked or non-solicitation `requested_by_observation_id`
   values during derive
3. classify proposal `bid_type` from proposal-local formality cues plus valid
   phase context
4. harden v2 semantic gates so invalid proposal links fail before derive
5. add focused regression coverage for these rules

This phase should not redesign EXIT-03/EXIT-04, expand analyst taxonomy, change
CSV schemas, or tighten prompt/skill contracts beyond what is necessary for the
proposal-link gate path.

</domain>

<decisions>
## Implementation Decisions

### Proposal Association
- **D-01:** Use a dedicated helper in `derive.py` for proposals that only trusts
  `requested_by_observation_id` when it points to a solicitation on or before
  the proposal date.
- **D-02:** When the explicit link is invalid, fall back to the latest valid
  same-day-or-earlier solicitation instead of leaving the proposal unphased if
  a deterministic fallback exists.

### Bid-Type Inference
- **D-03:** Proposal-local formality signals outrank raw phase inheritance.
- **D-04:** Strong formal signals are `includes_draft_merger_agreement`,
  `includes_markup`, and summary phrases such as `definitive proposal`, `final
  proposal`, and `best and final`.
- **D-05:** Explicit non-binding or IOI language should keep a proposal
  `Informal` unless a stronger hard-formal signal is present.

### Validation Scope
- **D-06:** `gates_v2.py` should block proposal links that point forward in time
  or to non-solicitation observations.
- **D-07:** Existing fixtures should stay small and synthetic; use targeted
  tests rather than corpus reruns in this phase.

### the agent's Discretion
- Whether chronology checks live entirely in `gates_v2.py` or share helper
  functions with `derive.py`, as long as derive remains safe when malformed
  links slip through older artifacts.
- The exact precedence order for mixed signals, provided it is deterministic,
  documented in tests, and conservative about explicit non-binding language.

</decisions>

<canonical_refs>
## Canonical References

### Milestone Scope
- `.planning/ROADMAP.md` — Phase 20 goal and success criteria
- `.planning/REQUIREMENTS.md` — LINK-01 through LINK-03
- `.planning/STATE.md` — v2.2 milestone context and benchmark-boundary rule

### GPT Pro Diagnosis
- `diagnosis/gptpro/2026-04-01/round_1/v2_analytical_gap_inventory_3aa65f7.md`
- `diagnosis/gptpro/2026-04-01/round_1/reponse.md`

### Runtime Surfaces
- `skill_pipeline/derive.py`
- `skill_pipeline/gates_v2.py`
- `skill_pipeline/models_v2.py`
- `tests/test_skill_derive.py`
- `tests/test_skill_gates_v2.py`
- `tests/_v2_validation_fixtures.py`

</canonical_refs>

<specifics>
## Specific Ideas

- Keep the proposal-phase fallback same-day-or-earlier; do not let a later
  solicitation define an earlier proposal.
- Reuse the existing `mentions_non_binding`,
  `includes_draft_merger_agreement`, and `includes_markup` fields before adding
  new schema.
- Treat summary parsing as a bounded fallback for phrases that GPT Pro showed in
  real disagreements (`definitive proposal`, `final proposal`, `best and
  final`, `indication of interest`, `preliminary`, `non-binding`).

</specifics>

<deferred>
## Deferred Ideas

- solicitation recipient extraction contract changes
- transition/drop-date redesign
- outcome actor/date normalization
- agreement/process taxonomy expansion
- export precision and enterprise-value schema changes

</deferred>
