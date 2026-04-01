---
phase: 24-v1-retirement-git-history-preservation
verified: 2026-04-01T21:08:48Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 24: V1 Retirement + Git-History Preservation Verification Report

**Phase Goal:** Retire the legacy v1 runtime, skill surface, and archived
working-tree artifacts from the live repository while keeping the prior
implementation recoverable through Git history, milestone archives, and tags.

**Verified:** 2026-04-01T21:08:48Z
**Status:** passed
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | the working tree now exposes only the live v2 workflow and skill surface | VERIFIED | `skill_pipeline/cli.py`, `.claude/skills/`, mirrored skill trees, and repo docs now reference only the live v2 flow; legacy skills and v1-only CLI/runtime surfaces are removed. |
| 2 | the live v2 runtime no longer depends on legacy v1 modules | VERIFIED | `compose_prompts.py`, `canonicalize.py`, `extract_artifacts_v2.py`, `coverage_v2.py`, `db_export_v2.py`, `paths.py`, and related neutral helper modules now support v2 directly without importing the retired legacy runtime files. |
| 3 | v1 recoverability is explicit and GitHub-visible instead of living in the working tree | VERIFIED | Recovery is pinned to tag `v1-working-tree-2026-04-01` at commit `82a4966`, and `CLAUDE.md` plus planning docs now direct recovery through Git history and milestone archives. |
| 4 | tests and contract docs now match the v2-only working tree | VERIFIED | The prompt/render regression suite, runtime contract docs, benchmark-boundary tests, mirror-sync tests, and broader v2 runtime bundles all pass against the retired-v1 working tree. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skill_pipeline/cli.py` | v2-only public CLI surface | VERIFIED | Exposes only live v2 commands and observations-mode compose-prompts. |
| `skill_pipeline/compose_prompts.py` | v2-only prompt composition contract | VERIFIED | Accepts only `mode=\"observations\"` and `contract=\"v2\"`. |
| `skill_pipeline/paths.py` | v2-only path contract | VERIFIED | Uses only live v2 directories and manifest paths. |
| `CLAUDE.md` | authoritative v2-only repo contract with recovery guidance | VERIFIED | Documents the live v2 runtime plus the Git-tag recovery path for retired v1. |
| `.planning/PROJECT.md` and `.planning/MILESTONES.md` | project state matches retirement | VERIFIED | Planning docs now describe the clean v2 surface and the recovery tag instead of `data/legacy/v1/`. |
| `tests/test_skill_mirror_sync.py` | mirror expectations without legacy skills | VERIFIED | Asserts only the live v2 skill set remains mirrored. |
| `tests/test_runtime_contract_docs.py` | doc contract coverage for retirement | VERIFIED | Validates the live workflow docs and prompt packet contract against the retired-v1 tree. |
| `tests/test_skill_compose_prompts.py` | observations-v2 prompt coverage | VERIFIED | Covers the live observations-v2 renderer and compose-prompts behavior without actor/event legacy assumptions. |

### Behavioral Spot-Checks

| Behavior | Command / Check | Result | Status |
|----------|-----------------|--------|--------|
| Skill mirror sync | `python scripts/sync_skill_mirrors.py --check` | `Skill mirrors are in sync.` | PASS |
| Focused retirement regression bundle | `pytest -q tests/test_skill_mirror_sync.py tests/test_runtime_contract_docs.py tests/test_benchmark_separation_policy.py tests/test_skill_pipeline.py tests/test_skill_extract_artifacts_v2.py tests/test_skill_db_export_v2.py tests/test_skill_compose_prompts.py tests/test_skill_prompt_models.py` | `115 passed in 0.66s` | PASS |
| Broader live-v2 runtime bundle | `pytest -q tests/test_skill_canonicalize_v2.py tests/test_skill_check_v2.py tests/test_skill_coverage_v2.py tests/test_skill_gates_v2.py tests/test_skill_db_load_v2.py tests/test_skill_derive.py tests/test_skill_observation_models.py` | `52 passed in 0.55s` | PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| RETIRE-01 | Expose only the live v2 workflow in the working tree | SATISFIED | Legacy runtime modules, canonical legacy skills, mirrored legacy skills, and the v1 archive tree were removed; docs and CLI now point only to v2. |
| RETIRE-02 | Remove live v2 dependencies on legacy runtime modules | SATISFIED | Shared live logic was extracted into neutral helpers and the active v2 runtime imports no longer depend on retired modules. |
| RETIRE-03 | Remove `data/legacy/v1/` and other v1-only working-tree artifacts after pinning recovery | SATISFIED | Recovery is pinned to tag `v1-working-tree-2026-04-01` at commit `82a4966`, after which `data/legacy/v1/` and related v1-only artifacts were removed from the tree. |
| RETIRE-04 | Rewrite regression tests and contract docs for a v2-only repo | SATISFIED | Prompt, mirror, doc-contract, benchmark-boundary, extract, load/export, and broader v2 runtime tests all pass against the cleaned tree. |

### Human Verification Required

None for the Phase 24 scope.

### Gaps Summary

No phase-blocking gaps remain. v2.2 now closes with the live repository
operating as a v2-only surface and the retired v1 implementation preserved in
Git history rather than in the working tree.

---

_Verified: 2026-04-01T21:08:48Z_
_Verifier: Codex_
