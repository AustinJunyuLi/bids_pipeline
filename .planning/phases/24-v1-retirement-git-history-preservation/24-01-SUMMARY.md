# Plan 24-01 Summary

## Outcome

Retired the legacy v1 working-tree surface and left the repository operating as
a clean v2-only runtime with explicit Git-history recovery.

## What Changed

- Removed legacy runtime modules, migration shims, skills, mirrored skill
  copies, tests, prompt assets, scripts, and `data/legacy/v1/` from the live
  working tree.
- Repointed the live v2 runtime onto neutral shared modules so `compose-prompts`,
  coverage, export ordering, canonicalization, and the CLI no longer depend on
  legacy-labeled runtime files.
- Rewrote the canonical repo docs and planning docs so they describe the live
  v2 workflow plus the Git-history recovery path instead of a live v1/v2 split.
- Reworked prompt-layer regression coverage to match the observations-v2 packet
  contract and removed the stale actor/event prompt asset surface.
- Preserved recovery through tag `v1-working-tree-2026-04-01`, pointing at the
  last pre-retirement commit `82a4966`.

## Verification

- `python scripts/sync_skill_mirrors.py --check`
- `pytest -q tests/test_skill_mirror_sync.py tests/test_runtime_contract_docs.py tests/test_benchmark_separation_policy.py tests/test_skill_pipeline.py tests/test_skill_extract_artifacts_v2.py tests/test_skill_db_export_v2.py tests/test_skill_compose_prompts.py tests/test_skill_prompt_models.py`
- `pytest -q tests/test_skill_canonicalize_v2.py tests/test_skill_check_v2.py tests/test_skill_coverage_v2.py tests/test_skill_gates_v2.py tests/test_skill_db_load_v2.py tests/test_skill_derive.py tests/test_skill_observation_models.py`

## Result

Phase 24 closes the last live v1 working-tree gap from the v2 cutover. The
repository can continue forward without the legacy runtime present, and the old
tree remains recoverable from GitHub-visible history rather than from live
checked-in artifacts.
