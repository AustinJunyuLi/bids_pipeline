---
date: 2026-04-02
description: Debug 7 failing gates-v2 deals from sequential rerun
status: in-progress
---

## Goal

Resolve 37 gates-v2 blockers across 7 deals (imprivata, mac-gray, medivation, petsmart-inc, saks, stec, zep) that fail during the sequential 9-deal rerun. penford and providence-worcester pass end-to-end.

## Key Context

- Rerun log: `runtime_logs/deal-agent-rerun-all-9-20260402T000103Z.log`
- Active debug session: `.planning/debug/multi-deal-gates-v2-blockers.md`
- All 7 deals fail at `gates-v2` stage after passing fetch/preprocess/compose/canonicalize/check/coverage

## Root Causes Identified

1. **Forward `requested_by_observation_id` (35/37 blockers)**: Proposals link to a solicitation that occurs AFTER them in time. Extraction tagged proposals with the eventual final-bid solicitation rather than the actual earlier request.

2. **Missing bidder actor on substantive outcomes (2/37 blockers)**: petsmart-inc obs_evt_021 (executed) and zep obs_evt_016 (restarted) lack bidder references in structured fields despite naming them in summary text.

## Decision

User chose the most fundamental fix: rebuild all three layers (prompt, canonicalization, re-extraction).

## Progress

### Layer 1: Prompt Improvements (DONE)
- `observations_v2_prefix.md`: Added CRITICAL — TEMPORAL ORDER and CRITICAL — OUTCOME ACTOR blocks
- `observations_v2_examples.md`: Added concrete JSON examples (correct + incorrect) for both failure classes
- `compose_prompts.py`: Added delimited constraint blocks in task_instructions

### Layer 2: Canonicalization Enforcement (DONE)
- `canonicalize.py`: Added `_repair_forward_requested_by()` and `_repair_outcome_bidder_refs()`
- Both repairs wired into `run_canonicalize_v2()` for both quote-first and canonical paths
- 5 new tests in `test_skill_canonicalize_v2.py` — all pass
- Full suite: 219 passed

### Layer 3: Re-extraction and Pipeline Rerun (IN PROGRESS)
- Prompts recomposed for all 7 deals
- All 7 deals re-extracted via parallel agents (single-pass: imprivata, petsmart-inc, saks, zep; multi-window: mac-gray 3w, medivation 2w, stec 4w)
- All 7 deals pass gates-v2 with **0 blockers** (was 37)
- 4 deals (medivation, petsmart-inc, saks, zep) completed full pipeline through db-export
- 3 deals (imprivata, mac-gray, stec) had repairable coverage gaps — repair agents running
  - imprivata: missing NDA → FIXED, coverage now passes
  - mac-gray: missing process_initiation → repair in progress
  - stec: missing process_initiation x2 + withdrawal → repair in progress
- Regression check: penford and providence-worcester still pass (0 blockers)

### Reconciliation Against Alex's Spreadsheet (DONE)
- Created `scripts/reconcile_alex.py` for mechanical matching (family-level, multi-pass)
- All 9 deals reconciled: alex_rows.json + reconciliation_report.json written
- 63 total disagreements, 55 arbitrated by 9 parallel agents
- Verdicts: 15 pipeline-correct, 8 alex-correct, 33 both-defensible, 6 inconclusive
- Key pattern: pipeline preserves ranges well; Alex collapses to point values; both valid conventions
- Outputs: `data/skill/<slug>/reconcile/reconciliation_report.json` (with verdicts array)

### Systematic Missing Event Prevention (DONE)
- Diagnosed: many reconciler "misses" were name-matching failures, not pipeline misses
- GPT-5.4 review identified 6 critical gaps in initial plan; plan revised
- Implemented Layers 0-3:
  - **Layer 0**: Multi-actor hints + count hints in `evidence.py` (`_extract_actor_hints()`, `_extract_count_hint()`)
  - **Layer 1**: Actor-level coverage in `coverage_v2.py` (bidder_inventory error-level, actor tie-breaking)
  - **Layer 2**: Actor roster (party alias cross-check) + count assertions (cohort count verification)
  - **Layer 3**: Extended `verify-extraction-v2/SKILL.md` with actor completeness checklist
- All 9 deals pass coverage-v2 with no false-positive blockers
- 3 legitimate count_assertion warnings detected (imprivata, petsmart-inc, saks)
- 219 tests pass, no regressions

---

## 2026-04-04: Clean 9-Deal Production Rerun + Hardening Plan

### Full E2E Rerun (DONE)
- Verified local `two-pass` branch matches `origin/two-pass` at `8522edd`
- Cleaned all v2 output surfaces for 9 deals (prompt_v2/ extract_v2/ check_v2/ coverage_v2/ gates_v2/ derive/ export_v2/ + data/deals/*/source/)
- EDGAR identity: Austin Li junyu.li.24@ucl.ac.uk
- Stages 1-3 (raw-fetch, preprocess, compose-prompts): 9/9 pass
- Stage 4 (extract-deal-v2): 9 parallel agents, all completed
  - Single-window: imprivata, penford, petsmart-inc, providence-worcester, saks, zep
  - Multi-window: mac-gray (3w), medivation (2w), stec (4w)
- Schema normalization required mid-run (12 mismatch categories — see below)
- Stages 5-9 (canonicalize, check, coverage, gates): 9/9 pass after fixes
  - 5 coverage gaps repaired (imprivata, mac-gray, medivation, petsmart-inc, stec)
- Stages 10-12 (derive, db-load, db-export): 9/9 pass
- Final: 398 observations, 119 parties, 215 analyst rows across 9 deals

### Schema Mismatches Discovered (12 categories)
1. `observation_type` → should be `obs_type`
2. `date: "2016-03-09"` string → should be `ResolvedDate` dict
3. `precision: "day"` → enum is `exact_day`
4. `name` → should be `display_name` (PartyRecord)
5. `description` → should be `label` (CohortRecord)
6. `known_members` → should be `known_member_party_ids` (CohortRecord)
7. `coverage: {dict}` → should be `coverage: []` (list)
8. `exclusions[].item/reason` → should be `category/explanation`
9. `terms.price_per_share` → should be `per_share`
10. `terms.per_share: "$16"` → should be numeric
11. Missing `subject_refs` on proposals (18 in medivation, 2 in saks)
12. Empty `created_by_observation_id` on cohorts (7 in providence-worcester)

Root cause: prompt gives semantic guidance but no structural JSON schema; no pre-validation normalizer exists.

### Hardening Plan (IN PROGRESS)
- Plan written: `/home/austinli/.claude/plans/functional-dancing-minsky.md`
- Two layers:
  - **Layer B (normalizer)**: `skill_pipeline/normalize/extraction.py` — deterministic pre-validation normalizer for the 10 fixable mismatches, called before `model_validate()` in `extract_artifacts_v2.py`
  - **Layer A (prompt schema)**: `skill_pipeline/prompts/schema_ref.py` — compact JSON schema reference generated from Pydantic models, injected into rendered prompts
- Codex dispatched (GPT 5.4 xhigh) to implement both phases
