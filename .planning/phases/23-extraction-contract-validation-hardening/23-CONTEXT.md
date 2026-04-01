# Phase 23: Extraction Contract + Validation Hardening - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning
**Mode:** Auto-generated from the GPT Pro round_1 diagnosis

<domain>
## Phase Boundary

Harden the remaining upstream contract edges so the Phase 20-22 derive/export
improvements have better literal inputs:

1. strengthen the v2 observation prompt instructions around recipient refs,
   chronology-safe proposal links, agreement families, bidder-scoped outcomes,
   and relative-date anchoring
2. align the active extract/verify skill docs with the stronger v2 contract
3. add v2 gate findings for missing named solicitation recipients,
   under-specified substantive outcomes, proxy-date leakage, and lossy
   agreement-family classification
4. pin the new prompt/gate behavior with focused tests

This phase should not change derived row schemas again or redesign the
deterministic runtime beyond the new gate findings.

</domain>

<decisions>
## Implementation Decisions

### Prompt Contract
- **D-01:** Keep the prompt changes field-specific and literal; do not turn the
  packet into a benchmark-shaped instruction set.
- **D-02:** Explicitly forbid forward `requested_by_observation_id` links and
  require `recipient_refs` when invitees are named or a reusable cohort is
  stated.

### Skill Docs
- **D-03:** Update the active mirrored skill docs in-place so extract and verify
  workflows reinforce the stronger v2 contract already implemented in code.

### Gate Surface
- **D-04:** Missing named solicitation recipients and missing bidder actors on
  substantive outcomes should surface as findings before derive.
- **D-05:** Non-exact proposal/outcome dates that still rely on proxy ordering
  should surface as warnings for analyst review.
- **D-06:** Agreements classified as `other` or `nda` despite exclusivity,
  standstill, clean-team, or amendment cues should raise a warning.

### the agent's Discretion
- The exact wording of prompt/skill doc examples, provided they stay filing
  literal and point at the real schema fields.
- Whether individual gate findings are blockers or warnings, as long as the
  under-specified cases are surfaced deterministically.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 23 goal and success criteria
- `.planning/REQUIREMENTS.md` — CONTRACT-01 and CONTRACT-02
- `diagnosis/gptpro/2026-04-01/round_1/v2_analytical_gap_inventory_3aa65f7.md`
- `skill_pipeline/compose_prompts.py`
- `skill_pipeline/prompt_assets/observations_v2_prefix.md`
- `skill_pipeline/prompt_assets/observations_v2_examples.md`
- `skill_pipeline/gates_v2.py`
- `.claude/skills/extract-deal-v2/SKILL.md`
- `.claude/skills/verify-extraction-v2/SKILL.md`
- `.codex/skills/extract-deal-v2/SKILL.md`
- `.codex/skills/verify-extraction-v2/SKILL.md`
- `.cursor/skills/extract-deal-v2/SKILL.md`
- `.cursor/skills/verify-extraction-v2/SKILL.md`
- `tests/test_skill_gates_v2.py`
- `tests/test_skill_compose_prompts.py`
- `tests/test_skill_phase16_migration.py`

</canonical_refs>

<specifics>
## Specific Ideas

- The prompt should call out `recipient_refs`, `requested_by_observation_id`,
  bidder-scoped outcomes, agreement families, and date anchoring by name.
- Gate tests should stay synthetic and local to v2 fixtures; no corpus reruns
  are needed for this hardening pass.

</specifics>

<deferred>
## Deferred Ideas

- additional corpus-scale smoke reruns outside the focused pytest suite
- further milestone planning around solicitation participant recovery beyond
  contract/gate hardening

</deferred>
