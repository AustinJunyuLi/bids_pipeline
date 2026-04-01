---
phase: 23-extraction-contract-validation-hardening
verified: 2026-04-01T13:10:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 23: Extraction Contract + Validation Hardening Verification Report

**Phase Goal:** Update extraction instructions, skill docs, and v2 gates so the
repaired derivation logic gets better inputs and failures surface before
export.

**Verified:** 2026-04-01T13:10:00Z
**Status:** passed
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | the rendered v2 observation prompt now names the stricter contract rules explicitly | VERIFIED | `compose_prompts.py`, `observations_v2_prefix.md`, and `observations_v2_examples.md` now call out `recipient_refs`, chronology-safe `requested_by_observation_id`, bidder-scoped outcomes, agreement-family distinctions, and anchored relative dates. |
| 2 | the active extract/verify skill docs reinforce the same stronger contract | VERIFIED | The mirrored extract/verify skill docs under `.claude/`, `.codex/`, and `.cursor/` now mirror the strengthened v2 contract language. |
| 3 | `gates-v2` surfaces the remaining malformed upstream cases before derive | VERIFIED | `gates_v2.py` now emits findings for missing named recipients, under-specified substantive outcomes, proxy-date export warnings, and lossy agreement-kind classification. |
| 4 | focused prompt/gate tests pin the new contract | VERIFIED | `tests/test_skill_gates_v2.py` and `tests/test_skill_phase16_migration.py` cover the new gate findings and rendered prompt strings directly. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skill_pipeline/compose_prompts.py` | Stronger observation task instructions | VERIFIED | The task instructions now explicitly mention the strengthened v2 contract fields. |
| `skill_pipeline/prompt_assets/observations_v2_prefix.md` | Top-level prompt reminders | VERIFIED | Prefix now calls out recipient refs, chronology-safe proposal links, agreement families, bidder-scoped outcomes, and non-exact date precision. |
| `skill_pipeline/prompt_assets/observations_v2_examples.md` | Field-specific reminders/examples | VERIFIED | Examples now mention formality cues, recipient refs, agreement-family distinctions, and outcome actor/date expectations. |
| `skill_pipeline/gates_v2.py` | Contract-hardening findings | VERIFIED | New findings surface the malformed cases GPT Pro highlighted as upstream contract failures. |
| `.claude/skills/extract-deal-v2/SKILL.md` and mirrors | Active extraction contract docs | VERIFIED | Extract docs now reinforce recipient refs, chronology-safe proposal links, agreement families, and bidder-scoped outcomes. |
| `.claude/skills/verify-extraction-v2/SKILL.md` and mirrors | Active verification contract docs | VERIFIED | Verify docs now reinforce chronology-safe links, named recipients, bidder-scoped outcomes, and non-exact date preservation. |
| `tests/test_skill_gates_v2.py` | Gate regression coverage | VERIFIED | Covers all newly added gate categories. |
| `tests/test_skill_phase16_migration.py` | Prompt rendering coverage | VERIFIED | Confirms the rendered observation packet exposes the stronger contract text. |

### Behavioral Spot-Checks

| Behavior | Command / Check | Result | Status |
|----------|-----------------|--------|--------|
| Focused hardening slice | `pytest -q tests/test_skill_gates_v2.py tests/test_skill_phase16_migration.py -k 'recipient or outcome or proxy or agreement or prompt'` | `6 passed, 9 deselected` | PASS |
| Prompt/gate/derive/export subset | `pytest -q tests/test_skill_gates_v2.py tests/test_skill_phase16_migration.py tests/test_skill_derive.py tests/test_skill_db_export_v2.py tests/test_skill_pipeline.py` | `63 passed` | PASS |
| Broader v2 regression bundle | `pytest -q tests/test_skill_observation_models.py tests/test_skill_extract_artifacts_v2.py tests/test_skill_canonicalize_v2.py tests/test_skill_check_v2.py tests/test_skill_coverage_v2.py tests/test_skill_gates_v2.py tests/test_skill_derive.py tests/test_skill_db_export_v2.py tests/test_skill_pipeline.py tests/test_skill_phase16_migration.py` | `95 passed` | PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| CONTRACT-01 | Strengthen the v2 prompt and skill docs around recipient refs, chronology-safe links, bidder-scoped outcomes, and agreement families | SATISFIED | Prompt assets and mirrored skill docs now carry those rules explicitly. |
| CONTRACT-02 | Emit gate findings for missing named recipients, under-specified substantive outcomes, proxy-date leakage, and lossy agreement-family classification | SATISFIED | `gates_v2.py` now emits those findings and the test suite covers each category. |

### Human Verification Required

None for this contract-hardening slice.

### Gaps Summary

No phase-blocking gaps remain inside the Phase 23 scope. The v2.2 milestone is
now fully executed and verified at the focused regression-test level.

---

_Verified: 2026-04-01T13:10:00Z_
_Verifier: Codex_
