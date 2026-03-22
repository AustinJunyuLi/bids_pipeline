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

## Session: 2026-03-21 — Codebase Scan + STEC Reconciliation

### Work Done

1. **Full codebase scan** — deployed 5 parallel agents covering pipeline/, skill_pipeline/, tests/, data/, config/docs, and git history. Produced complete module maps and coverage analysis.

2. **Deep skill_pipeline scan** — deployed 6 parallel agents for line-by-line analysis of all 34 Python modules:
   - canonicalize.py: schema upgrade, dedup, NDA-gate, unnamed recovery
   - verify.py + coverage.py: quote verification, cue families, matching logic
   - check.py + enrich_core.py: structural gates, bid classification rules
   - models.py + normalize/ + provenance.py: schemas, date parsing, quote matching
   - raw/ + preprocess/ + source/: seed-only fetch, chronology location, evidence scanning
   - cli.py + deal_agent.py + all 10 test files: CLI dispatch, test coverage gaps

3. **STEC reconcile-alex** — ran `/reconcile-alex stec` end-to-end:
   - Extracted 28 Alex rows from benchmark xlsx
   - Matched 22 atomic events across families
   - Status: `attention` (match rate ~85%)
   - Key disagreements: bid_type on WDC's May 28 and Jun 14 proposals (pipeline=Informal, Alex=Formal — inconclusive, mixed filing signals)
   - Alex-only: 2 DropTarget for partial-company exclusions (Company E, F), 2 informal round interpretations
   - All pipeline orphans filing-grounded
   - Report: `data/skill/stec/reconcile/reconciliation_report.json`

### Issues Found (from deep scan)

| # | Issue | Severity |
|---|-------|----------|
| 1 | NDA gate ignores temporal order | Medium |
| 2 | Unresolved spans allowed in canonicalize output | Medium |
| 3 | Empty anchor_text silently skipped in verify | Medium |
| 4 | spans.json optional for canonical mode — defaults to empty | Medium |
| 5 | Zero export test coverage | High |
| 6 | First-match-wins cue classification in coverage | Low |
| 7 | Dedup tiebreaker arbitrary on identical summaries | Low |

### Current State

- Branch: `baseline-check-summary` (8 commits ahead of main)
- 19 modified tracked files (skills, CLAUDE.md, coverage.py, tests)
- All 9 raw bundles untracked (seed-only, ready for preprocess)
- Only `stec` fully compiled through export + reconcile
- 8 deals need `skill-pipeline preprocess-source` before extraction
