# Phase 12: Artifact Loading + Canonicalization - Research

**Date:** 2026-03-31
**Status:** Complete

## Findings

### 1. The live v1 loader is intentionally narrow

- `skill_pipeline/extract_artifacts.py` only understands v1 `actors_raw.json` /
  `events_raw.json`.
- Its mode detection is already specific to v1 quote-first vs canonical payloads.
- Extending that function into a v1/v2 three-way parser would couple unrelated
  contracts and fight the architecture guidance.

### 2. The canonical span resolver is already generic enough

- `skill_pipeline/canonicalize.py` exposes `_resolve_quotes_to_spans()` plus
  shared chronology/document loaders.
- Those helpers operate on `QuoteEntry` plus block/document metadata, not on v1
  event semantics.
- The v2 path can reuse them directly if quote-first v2 artifacts expose a
  top-level quote array.

### 3. Phase 11 created the canonical v2 model surface, not the raw one

- `skill_pipeline/models_v2.py` defines span-backed canonical records.
- There is currently no raw v2 quote-first model for `observations_raw.json`.
- Phase 12 therefore needs a quote-first v2 wrapper model family for the
  canonicalization input path.

### 4. The CLI registration surface is additive and low-risk

- `skill_pipeline/cli.py` registers existing runtime commands directly.
- Adding `canonicalize-v2` is a localized parser + dispatch change.
- Existing CLI regression checks live in `tests/test_skill_pipeline.py`, not in
  a separate CLI-specific test file.

## Recommended Plan Shape

### Plan 12-01
- Add `skill_pipeline/extract_artifacts_v2.py`
- Define quote-first v2 wrapper models and `LoadedObservationArtifacts`
- Add a version router that distinguishes `v1`, `v2`, `both`, and `none`
- Add dedicated loader tests

### Plan 12-02
- Add `run_canonicalize_v2`
- Reuse `_resolve_quotes_to_spans()` to upgrade quote-first v2 artifacts into
  `observations.json` + `spans_v2_path`
- Register `canonicalize-v2` in the CLI
- Add synthetic canonicalize-v2 fixture tests and a parser test

## Risks

- If raw v2 quote-first models are not introduced explicitly, canonicalize-v2
  will end up overloading canonical `evidence_span_ids` fields with quote IDs
  and blur the raw/canonical boundary immediately.
- If the version router silently auto-selects a contract when both v1 and v2
  artifacts exist, later migration phases will load the wrong surface without
  noticing.
- If canonicalize-v2 inherits v1 event heuristics, it will mutate observation
  semantics before the validation stack exists.
