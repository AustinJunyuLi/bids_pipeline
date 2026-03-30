---
phase: quick
plan: 260330-o5x
subsystem: enrichment, db-load, deal-agent
tags: [bugfix, contract, enrichment, validation]
dependency_graph:
  requires: []
  provides: [split-enrichment-contract-enforcement, mandatory-interpretive-gate]
  affects: [enrich-core, enrich-deal, deal-agent, db-load, reconcile-alex]
tech_stack:
  added: []
  patterns: [deterministic-baseline-plus-interpretive-overlay]
key_files:
  created: []
  modified:
    - skill_pipeline/models.py
    - skill_pipeline/deal_agent.py
    - skill_pipeline/db_load.py
    - tests/test_skill_pipeline.py
    - tests/test_skill_db_load.py
    - tests/test_skill_db_export.py
    - tests/test_skill_mirror_sync.py
    - CLAUDE.md
    - .claude/skills/reconcile-alex/SKILL.md
    - .codex/skills/reconcile-alex/SKILL.md
    - .cursor/skills/reconcile-alex/SKILL.md
decisions:
  - Keep deterministic ownership in `deterministic_enrichment.json`; do not reintroduce deterministic fields into `enrichment.json`
  - Validate both enrichment artifacts with typed models so malformed interpretive payloads fail closed
  - Let `deal-agent` report FAIL for malformed interpretive artifacts instead of crashing the summary path
  - Make official docs and mirrors describe the same split contract the runtime now enforces
metrics:
  duration: handoff session
  completed: 2026-03-30
---

# Quick Task 260330-o5x: Repair Mandatory Interpretive Enrich-Deal Contract Summary

Enforced the intended two-layer enrichment philosophy across runtime, tests, and official docs: deterministic enrichment stays authoritative in `deterministic_enrichment.json`, while `enrichment.json` is now consistently treated as the mandatory 5-key interpretive layer.

## Implementation Commit

- `1aaa572` `fix(260330-o5x): enforce split enrich-deal contract`

## What Changed

### Runtime contract repair

- Added a dedicated `DeterministicEnrichmentArtifact` model for rounds, bid classifications, cycles, formal boundary, sparse deterministic dropout labels, and all-cash overrides.
- Re-scoped `SkillEnrichmentArtifact` to the interpretive-only 5-key artifact so `enrichment.json` matches the live `/enrich-deal` skill contract.
- Updated `db-load` to validate both enrichment artifacts with the correct models before loading DuckDB.

### deal-agent alignment

- `deal-agent` now reads deterministic counts from `deterministic_enrichment.json`.
- Interpretive outputs such as `initiation_judgment` and `review_flags` come from `enrichment.json`.
- Malformed interpretive enrichment now marks the enrich stage as `FAIL` instead of crashing summary generation.

### Regression coverage and docs

- Updated fixtures to stop writing deterministic fields into `enrichment.json`.
- Added regressions proving malformed interpretive enrichment is rejected in `db-load` and reported as `FAIL` in `deal-agent`.
- Updated `CLAUDE.md` and reconcile-alex canonical/mirrored skill docs so the official process record matches the runtime contract.

## Verification

- Targeted contract suite passed: `129 passed`
- Command:

```bash
python3 -m pytest -q tests/test_skill_pipeline.py tests/test_skill_db_load.py tests/test_skill_db_export.py tests/test_skill_enrich_core.py tests/test_runtime_contract_docs.py tests/test_skill_mirror_sync.py tests/test_benchmark_separation_policy.py
```

## Deviations from Plan

None. The repair followed the agreed implementation shape and only required one additional fixture cleanup in `tests/test_skill_db_export.py` after the stricter deterministic model exposed stale test data.

## Self-Check: PASSED
