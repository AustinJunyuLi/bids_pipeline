# Phase 13: Validation Stack - Research

**Date:** 2026-03-31
**Status:** Complete

## Findings

### 1. The architecture already commits to separate v2 validation modules

- `.planning/research/ARCHITECTURE.md` explicitly maps `check.py`,
  `coverage.py`, and `gates.py` to additive `*_v2.py` modules.
- That guidance matches the repo's existing additive v2 pattern from Phases 11
  and 12.
- Reusing v1 validation modules directly would force v2 identifiers into
  actor/event-specific report surfaces and blur the migration boundary.

### 2. Canonical v2 loading is ready for validation consumers

- `extract_artifacts_v2.py` already returns canonical observation artifacts plus
  `party_index`, `cohort_index`, `observation_index`, and `span_index`.
- Validation can therefore run entirely on `extract_v2/observations.json` and
  `extract_v2/spans.json` without touching raw quote-first payloads.
- That keeps validation downstream of canonicalization, which aligns with the
  roadmap dependency on Phase 12.

### 3. Coverage should stay source-grounded instead of graph-internal

- The existing `coverage.py` builds deterministic cues from
  `evidence_items.jsonl` and `chronology_blocks.jsonl`.
- Reusing that cue detector preserves the benchmark boundary and prevents v2
  coverage from becoming a second derivation engine.
- The main v2 work is therefore record generation and observation matching, not
  new source heuristics.

### 4. v2 report typing needs observation-aware identifiers

- The shared `CoverageCheckRecord` already models the right status vocabulary
  (`observed`, `derived`, `not_found`, `ambiguous`) but currently points at v1
  actors/events.
- `CheckFinding` and `GateFinding` are also actor/event-shaped.
- The least disruptive path is additive v2 fields or additive v2 report models,
  not mutation of the v1 runtime behavior.

## Recommended Plan Shape

### Plan 13-01
- Add `check_v2.py`
- Add typed v2 structural/gate report models or additive shared fields
- Add structural validation tests for evidence presence, ref integrity, and
  proposal subject requirements

### Plan 13-02
- Add `coverage_v2.py`
- Reuse source cue detection from `coverage.py`
- Emit structured coverage records for covered and uncovered cues
- Add synthetic coverage tests covering observed, ambiguous, and missing cases

### Plan 13-03
- Add `gates_v2.py`
- Add CLI wiring for `check-v2`, `coverage-v2`, `gates-v2`
- Add graph-gate tests and update repo memory for live v2 validation writers

## Risks

- If `check_v2` validates raw quote-first artifacts, later phases will have to
  duplicate evidence-presence logic across raw and canonical contracts.
- If v2 coverage only emits uncovered cues, the new structured status field
  vocabulary is wasted and the output becomes another sparse audit log.
- If v2 gate reports reuse actor/event IDs without observation-aware fields,
  downstream derivation and migration debugging will be much harder.
