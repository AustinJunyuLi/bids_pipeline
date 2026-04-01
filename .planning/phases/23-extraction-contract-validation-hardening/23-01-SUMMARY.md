# Plan 23-01 Summary

## Outcome

Strengthened the live v2 extraction contract and added gate findings for the
remaining malformed upstream cases that GPT Pro highlighted.

## What Changed

- Updated `skill_pipeline/compose_prompts.py` and the observation prompt assets
  so the rendered v2 packet now explicitly requires:
  - `recipient_refs` when invitees or reusable cohorts are named
  - chronology-safe `requested_by_observation_id` links
  - literal proposal formality cues
  - distinct agreement families
  - bidder-scoped outcomes
  - anchored but non-exact relative dates
- Updated the mirrored extract/verify skill docs under:
  - `.claude/skills/`
  - `.codex/skills/`
  - `.cursor/skills/`
- Extended `skill_pipeline/gates_v2.py` with findings for:
  - missing named solicitation recipients
  - under-specified substantive outcomes
  - proxy-date export warnings
  - lossy agreement-kind classification
- Added focused regression coverage in:
  - `tests/test_skill_gates_v2.py`
  - `tests/test_skill_phase16_migration.py`

## Verification

- `pytest -q tests/test_skill_gates_v2.py tests/test_skill_phase16_migration.py -k 'recipient or outcome or proxy or agreement or prompt'`
- `pytest -q tests/test_skill_gates_v2.py tests/test_skill_phase16_migration.py tests/test_skill_derive.py tests/test_skill_db_export_v2.py tests/test_skill_pipeline.py`
- `pytest -q tests/test_skill_observation_models.py tests/test_skill_extract_artifacts_v2.py tests/test_skill_canonicalize_v2.py tests/test_skill_check_v2.py tests/test_skill_coverage_v2.py tests/test_skill_gates_v2.py tests/test_skill_derive.py tests/test_skill_db_export_v2.py tests/test_skill_pipeline.py tests/test_skill_phase16_migration.py`

## Result

Phase 23 closes the remaining contract gap between the literal extraction layer
and the now-hardened derive/export runtime, so malformed upstream artifacts are
more likely to fail loudly before they distort later stages.
