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
