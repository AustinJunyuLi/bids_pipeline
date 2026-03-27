# Phase 1 Research — Foundation + Annotation

**Researched:** 2026-03-27
**Scope:** Phase 1 only
**Confidence:** HIGH

## Executive Summary

Phase 1 is a deterministic source-artifact upgrade, not an extraction redesign.
The live implementation still writes bare `ChronologyBlock` records from
`skill_pipeline/preprocess/source.py` and validates them via
`skill_pipeline/pipeline_models/source.py`. The correct Phase 1 move is to add
required block metadata directly onto `ChronologyBlock`, compute that metadata
inside `preprocess-source`, refresh every fixture that serializes block JSONL,
and then regenerate all 9 deal source artifacts.

The live code already contains almost all primitives needed for the annotation
layer:

- `skill_pipeline/normalize/dates.py` for deterministic date parsing
- `skill_pipeline/source/evidence.py` for document cue families and
  `DATE_FRAGMENT_RE`
- `skill_pipeline/seeds.py` for target/acquirer seed names
- `skill_pipeline/preprocess/source.py` for the correct integration point
- `tests/test_skill_preprocess_source.py` for the current preprocess contract

The contract hardening side of the phase is narrower than the earlier research
packet implied. The repo-truth docs already describe the deterministic
`skill_pipeline` split fairly well. The remaining hardening is mostly manifest
and historical-doc hygiene:

- cap `edgartools` below v6 in live dependency manifests
- remove Python-side LLM SDK dependencies from runtime manifests if they are
  unused by `skill_pipeline/` and `tests/`
- clearly mark historical plan docs that still refer to the deleted `pipeline/`
  package or provider-wrapper runtime

## Recommended Implementation Shape

### 1. Extend `ChronologyBlock` In Place

Add required metadata fields directly to
`skill_pipeline/pipeline_models/source.py`:

- `date_mentions`
- `entity_mentions`
- `evidence_density`
- `temporal_phase`

Do not create a sibling artifact such as `annotated_blocks.jsonl`. The roadmap
and phase context both commit to `chronology_blocks.jsonl` as the single source
artifact for downstream prompt work.

Recommended model shape:

- `BlockDateMention`
  - `raw_text: str`
  - `normalized: str | None`
  - `precision: str`
- `BlockEntityMention`
  - `raw_text: str`
  - `canonical_name: str`
  - `entity_role: str`
- `ChronologyBlock`
  - `date_mentions: list[BlockDateMention]`
  - `entity_mentions: list[BlockEntityMention]`
  - `evidence_density: int`
  - `temporal_phase: Literal["initiation", "bidding", "outcome", "other"]`

These fields should be required. No defaults. No fallback loader for stale
blocks.

### 2. Put Annotation Logic in `skill_pipeline/source/annotate.py`

Keep the annotation helpers close to the other source-artifact builders.
`skill_pipeline/source/annotate.py` is the cleanest fit because it keeps the
logic deterministic and reusable without bloating `preprocess/source.py`.

Recommended helper surface:

- `extract_block_date_mentions(block: ChronologyBlock) -> list[BlockDateMention]`
- `extract_block_entity_mentions(block: ChronologyBlock, *, target_name: str, acquirer_name: str | None) -> list[BlockEntityMention]`
- `compute_evidence_density(block: ChronologyBlock, evidence_items: list[EvidenceItem]) -> int`
- `infer_temporal_phase(block: ChronologyBlock, evidence_items: list[EvidenceItem], *, total_blocks: int) -> str`
- `annotate_chronology_blocks(blocks: list[ChronologyBlock], evidence_items: list[EvidenceItem], *, target_name: str, acquirer_name: str | None) -> list[ChronologyBlock]`

Concrete rules from the phase context:

- Date mentions come from `DATE_FRAGMENT_RE` plus normalization through
  `parse_resolved_date`
- Entity mentions come from the deal seed names plus filing aliases:
  `Party [A-Z]`, `the Company`, `the Board`, `Special Committee`,
  `Transaction Committee`
- Evidence density is a simple integer overlap count on line ranges
- Temporal phase uses evidence-item families first, then ordinal fallback:
  early blocks prefer `initiation`, middle blocks prefer `bidding`, late blocks
  prefer `outcome`

### 3. Integrate Inside `preprocess-source`

The right integration point in `skill_pipeline/preprocess/source.py` is after
`scan_document_evidence()` and `_dedupe_evidence_items(...)`, but before writing
`chronology_blocks.jsonl`.

`preprocess_source_deal()` does not currently load the seed row, so it must do
that itself via:

- `project_root = raw_dir.parent`
- `seeds_path = project_root / "data" / "seeds.csv"`
- `load_seed_entry(deal_slug, seeds_path=seeds_path)`

That keeps the CLI surface unchanged and preserves the existing one-command
preprocess contract.

### 4. Expect Broad Fixture Churn

Making metadata required on `ChronologyBlock` will break any test that writes
`chronology_blocks.jsonl` using `{}` or the old bare schema. The current impact
surface is larger than `test_skill_preprocess_source.py`; it also includes:

- `tests/test_skill_canonicalize.py`
- `tests/test_skill_verify.py`
- `tests/test_skill_coverage.py`
- `tests/test_skill_enrich_core.py`
- `tests/test_skill_pipeline.py`
- `tests/test_skill_provenance.py`

Plan for one dedicated test-refresh pass rather than patching these piecemeal
during implementation.

### 5. Keep Dependency Hygiene Narrow

The deterministic runtime manifests still include `anthropic>=0.49` in both
`pyproject.toml` and `requirements.txt`, even though the live repo contract says
Python-side LLM wrappers are out of scope. Phase 1 should not invent new
provider dependencies; it should tighten the live deterministic path.

Recommended Phase 1 dependency actions:

- Change `edgartools>=5.23` to `edgartools>=5.23,<6.0`
- Remove `anthropic>=0.49` from runtime dependency manifests if
  `skill_pipeline/` and `tests/` have no live imports
- Leave `openpyxl>=3.1` alone unless a live workflow audit proves it is safe to
  remove

## Risks To Watch

### Event-Order-Dependent Tests

Some downstream tests only need schema-valid chronology blocks and do not care
about annotation semantics. Refresh those fixtures minimally so they keep
testing their intended behavior rather than becoming annotation tests by
accident.

### Historical Docs Reintroducing Stale Runtime Assumptions

The two 2026-03-16 plan docs still refer to the deleted `pipeline/` package and
provider-wrapper surfaces. Do not rewrite them line-by-line. Add explicit
historical warnings so they remain useful background without being mistaken for
live implementation truth.

### Generated Artifact Regeneration

Re-running `preprocess-source` for all 9 deals will rewrite generated source
artifacts. That is intentional for this phase, but the run must fail fast on
the first broken deal and should not touch `raw/<slug>/filings/*.txt`.

## Validation Architecture

### Automated Checks

- Quick annotation pass:
  `python -m pytest -q tests/test_skill_source_annotations.py tests/test_skill_preprocess_source.py`
- Broader schema-compatibility pass:
  `python -m pytest -q tests/test_skill_canonicalize.py tests/test_skill_verify.py tests/test_skill_coverage.py tests/test_skill_enrich_core.py tests/test_skill_pipeline.py tests/test_skill_provenance.py`
- Runtime-contract docs pass:
  `python -m pytest -q tests/test_runtime_contract_docs.py tests/test_benchmark_separation_policy.py`
- Full suite:
  `python -m pytest -q`

### Corpus Validation

Add a dedicated validation helper under `scripts/` that:

- loads each regenerated `chronology_blocks.jsonl` through
  `ChronologyBlock.model_validate_json`
- asserts the four new metadata keys exist on every block
- performs a focused `stec` spot-check for at least one block with:
  non-empty `date_mentions`, non-empty `entity_mentions`,
  `evidence_density > 0`, and a valid `temporal_phase`

### Manual Spot Check

The roadmap explicitly requires a `stec` spot-check. Keep that human-visible:

- inspect one early, one middle, and one late `stec` block
- verify the phase hint is plausible against the narrative
- verify evidence density is not trivially zero everywhere
- verify seed-based entities actually match filing language

## Files To Read First During Execution

- `skill_pipeline/pipeline_models/source.py`
- `skill_pipeline/preprocess/source.py`
- `skill_pipeline/source/blocks.py`
- `skill_pipeline/source/evidence.py`
- `skill_pipeline/normalize/dates.py`
- `skill_pipeline/seeds.py`
- `data/seeds.csv`
- `tests/test_skill_preprocess_source.py`
- `tests/test_skill_canonicalize.py`
- `tests/test_skill_verify.py`
- `tests/test_skill_coverage.py`
- `tests/test_skill_enrich_core.py`
- `tests/test_skill_pipeline.py`
- `tests/test_skill_provenance.py`
- `.planning/phases/01-foundation-annotation/01-CONTEXT.md`

---
*Phase 1 research created from the live codebase and existing project research packet*
