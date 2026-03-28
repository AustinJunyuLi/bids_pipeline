# Session Log: Skill-Only Quick Workflow Design & Implementation

**Date:** 2026-03-18
**Status:** IMPLEMENTED — auditing path consistency

## Goal

Design and implement a skill-only quick workflow that replaces the deterministic
pipeline (stages 3-6) with agent-driven skills, producing an Alex-compatible CSV.
Hard separation between canonical pipeline (`data/deals/`) and skill workflow
(`data/skill/`).

## What Was Built

4-skill chain orchestrated by deal-agent:

```
/deal-agent <slug>
  |-- /extract-deal       (filing -> actors + events JSON)
  |-- /verify-extraction   (fact-check -> fix -> re-check -> log)
  |-- /enrich-deal         (classify, segment, judge -> enrichment JSON)
  |-- /export-csv          (format -> Alex-compatible CSV)
```

Plus `skill_pipeline/` Python package with its own models, paths, seeds, CLI.

## Architecture Separation

- Canonical pipeline: `pipeline/` code, `data/deals/<slug>/` artifacts
- Skill workflow: `skill_pipeline/` code + skill files, `data/skill/<slug>/` artifacts
- Shared read-only: `data/deals/<slug>/source/`, `raw/<slug>/`, `data/seeds.csv`
- CLAUDE.md is authoritative. AGENTS.md redirects to CLAUDE.md.

## Files Created/Modified

| File | Action |
|------|--------|
| `skill_pipeline/` (7 files) | Created: models, paths, seeds, config, deal_agent, cli, __init__ |
| `tests/test_skill_pipeline.py` | Created |
| `.claude/skills/{5 skills}/SKILL.md` | Updated with `data/skill/` paths |
| `.cursor/skills/{5 skills}/SKILL.md` | Synced with claude |
| `.codex/skills/{5 skills}/SKILL.md` | STALE — needs re-sync |
| `CLAUDE.md` | Rewritten with dual-architecture docs |
| `AGENTS.md` | Reduced to 2-line redirect |
| `pyproject.toml` | Added skill-pipeline CLI entrypoint |

## Current Issue

Codex skill mirrors are stale (still have old `data/deals/` write paths).
Spec and plan docs also use old paths but CLAUDE.md warns about this.

## Key Decisions

1. Hard path separation: `data/deals/` (pipeline) vs `data/skill/` (skills)
2. Separate Python package: `skill_pipeline/` with own models
3. Separate CLI: `skill-pipeline deal-agent --deal <slug>`
4. CLAUDE.md as single source of truth
5. Agent-driven enrichment for 8 nuanced tasks pipeline can't do
6. 4 skills, no audit theater
7. Two-phase dropout classification
8. Free-text comments + machine-readable review_flags

---

## 2026-03-28: Phase 3 Planning Session

**Goal:** Plan Phase 3 (Quote-Before-Extract) — force LLM to cite verbatim filing passages before emitting structured events.

### What happened
- Ran `/gsd:discuss-phase 03` (prior session) → `03-CONTEXT.md` with 9 locked decisions (D-01 through D-09)
- Ran `/gsd:plan-phase 03`:
  - Research: gsd-phase-researcher analyzed all 10+ files needing modification, confirmed core functions (`resolve_text_span`, `find_anchor_in_segment`) are reusable, biggest risk is test fixture rewrites
  - Validation: Created `03-VALIDATION.md` with 9-task verification map tied to PROMPT-05 sub-behaviors
  - Planning: gsd-planner produced 4 plans in 2 waves:
    - Wave 1: 03-01 (schema foundation — QuoteEntry model, extract loader, test fixtures)
    - Wave 2: 03-02 (canonicalize rewrite), 03-03 (verify+check rewrite), 03-04 (prompt instructions + SKILL.md)
  - Verification: gsd-plan-checker passed all 10 dimensions, 1 warning (skill mirror sync deferred)

### Commits
- `6700dbd` docs(03): research phase domain
- `53fbe7c` docs(phase-03): add validation strategy
- `5c5e67c` docs(03): create phase 3 quote-before-extract plans

### Next
- `/gsd:execute-phase 03` to implement all 4 plans
- After code changes: re-extract stec and medivation through quote-first protocol
- Run `python scripts/sync_skill_mirrors.py` after SKILL.md update (checker warning)

---

## 2026-03-28: Phase 05 Planning + Milestone Completion

### Phase 05 Planning
- Ran `/gsd:plan-phase 05` for Integration + Calibration
- Research: DuckDB 1.4.4 verified, corpus complexity analysis (6 simple / 3 complex at 150-block threshold)
- Plans: 3 plans in 2 waves (01: DuckDB+db-load+db-export, 02: complexity routing+few-shot, 03: orchestration+docs)
- Plan checker: passed all 10 dimensions

### Second Brain Review (Claude + GPT 5.4)
- GPT independently reviewed Phase 05 discretionary decisions (D-04 through D-09)
- 6 issues found: enrichment schema bug, SINGLE_PASS_BUDGET sentinel, 9-deal batch gap, fabricated examples, CSV scope mismatch, stec validation incomplete
- All 6 addressed in plan revisions; committed `4bb6e05`

### Phase 05 Execution (prior session)
- All 3 plans executed, verified 10/10 truths, 265 tests passing

### Milestone Audit
- Initial audit: 18/20 satisfied, 2 partial (INFRA-04, INFRA-06)
- CRITICAL gap: deal-agent SKILL.md missing `gates` and `compose-prompts` steps
- Adversarial audit by GPT 5.4 caught DB-02 and PROMPT-06 misclassification
- All gaps fixed: added compose-prompts (step 3a) and gates (step 5b) to SKILL.md, synced mirrors, checked INFRA-04, updated PROMPT-06 text
- Revised audit: 20/20, status passed

### Milestone v1.0 Completed
- Archived to `.planning/milestones/v1.0-*`
- ROADMAP.md collapsed, REQUIREMENTS.md deleted
- PROJECT.md evolved: 8 Active -> Validated, Key Decisions updated
- Tag `v1.0` created and pushed to remote
- Stats: 5 phases, 16 plans, 8,967 LOC pipeline, 9,074 LOC tests, 265 passing
