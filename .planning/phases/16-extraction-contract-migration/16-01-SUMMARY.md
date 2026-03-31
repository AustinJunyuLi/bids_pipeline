# Plan 16-01 Summary

## Outcome

Added the additive v2 prompt / skill surface.

## What Changed

- `compose-prompts` now accepts `--contract v2 --mode observations`
- v2 prompt packets write under `prompt_v2/`
- prompt metadata accepts a new `observations_v2` packet family
- packet validation now routes to `prompt_v2/` when `--contract v2` is used
- canonical v2 skill docs now exist in `.claude/skills/` and were synced to
  `.codex/skills/` and `.cursor/skills/`

## Verification

- `pytest -q tests/test_skill_prompt_models.py tests/test_skill_compose_prompts.py tests/test_skill_phase16_migration.py`
