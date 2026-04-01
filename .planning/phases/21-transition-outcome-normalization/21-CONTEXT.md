# Phase 21: Transition + Outcome Normalization - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning
**Mode:** Auto-generated from the GPT Pro round_1 diagnosis

<domain>
## Phase Boundary

Normalize the lifecycle rows that still lose analytical fidelity after Phase 20:

1. give `EXIT-03` and `EXIT-04` explicit transition dates instead of always
   inheriting the status/execution observation date
2. use earlier round evidence such as solicitation deadlines when that is the
   strongest deterministic elimination point
3. make literal executed/restarted/terminated rows choose bidder or
   bidder-cohort actors before target-side refs
4. allow clearly related exact-day observations to fill missing literal outcome
   dates when the relationship is explicit in the artifact graph
5. pin the new behavior with focused derive regression tests

This phase should not expand analyst event taxonomies, add new export columns,
or rewrite prompt/skill contracts beyond what the new derive logic requires.

</domain>

<decisions>
## Implementation Decisions

### Transition Dating
- **D-01:** Add an explicit transition date field to the derived transition
  record so transition rows are not forced to inherit the first source
  observation date.
- **D-02:** For `EXIT-03`, prefer the related solicitation due date when
  available, then adjust upward to the subject's last active evidence date if
  the due date would otherwise predate known activity.
- **D-03:** For `EXIT-04`, prefer the last known round exit date before falling
  back to the execution date.

### Outcome Normalization
- **D-04:** Literal outcome rows should use the same bidder-first actor
  selection logic as winner resolution in transition derivation.
- **D-05:** Only backfill a missing outcome date from a related observation when
  that related observation carries an exact-day date.

### the agent's Discretion
- Whether the transition-date helpers live close to `_derive_transitions` or
  near `_date_fields`, as long as the rule ordering stays readable.
- The smallest viable state to track prior round evidence without redesigning
  the entire phase engine.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 21 goal and success criteria
- `.planning/REQUIREMENTS.md` — TRANS-01 through TRANS-03
- `.planning/phases/20-proposal-linkage-bid-type-repair/20-VERIFICATION.md`
- `diagnosis/gptpro/2026-04-01/round_1/v2_analytical_gap_inventory_3aa65f7.md`
- `skill_pipeline/derive.py`
- `skill_pipeline/models_v2.py`
- `tests/test_skill_derive.py`
- `tests/_v2_validation_fixtures.py`

</canonical_refs>

<specifics>
## Specific Ideas

- Keep the new transition date field additive and provenance-bearing.
- Favor deadline-based exit dates only when they do not predate the subject's
  own last active evidence.
- Reuse the existing bidder-first winner logic for literal outcome rows rather
  than inventing a second actor-selection policy.

</specifics>

<deferred>
## Deferred Ideas

- solicitation recipient extraction contract changes
- agreement/process taxonomy expansion
- export precision and enterprise-value schema changes
- prompt/skill doc updates and new v2 gate warnings

</deferred>
