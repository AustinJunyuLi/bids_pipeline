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

## Session: 2026-03-25 — STEC Reconciliation Against Alex

### What happened

Ran `/reconcile-alex stec` after full pipeline completion through `/export-csv`.
Extracted 28 Alex rows, matched against 34 pipeline export rows.

### Results

- **Match rate:** 25/28 (89%) atomic rows matched by family + date + actor
- **Status:** ATTENTION
- **All 9 pipeline orphans:** filing-grounded (process milestones, Company A interest, WDC temp drop)
- **3 Alex orphans:** 2 categorization differences (informal round), 1 genuine miss (Company H drop May 23)

### Key findings

1. **5 Alex date_p errors** — Company B, Company D, IB retention all had 2013-04-04 (copy-paste); executed had 2013-06-14 (proposal date not execution); final round deadline had 2013-05-16 (announcement date not deadline). Pipeline correct on all.
2. **13 bidder_type fields missing from export CSV** — pipeline actors_raw.json has the correct `bidder_kind: strategic` but the export formatter drops the type column for non-NDA rows. Export regression to fix.
3. **3 val fields** — Alex records lower bound of range bids as point value; pipeline leaves val null for ranges. Convention difference.
4. **Company H drop (May 23)** — filing line 1501: "Company H was not able to increase its indicated value range." Pipeline omits this. Genuine miss.
5. **Informal round categorization** — Alex has "Final Round Inf Ann" (Apr 23) and "Final Round Inf" (May 3). Pipeline treats these as individual IOIs. Filing says "process letters requesting non-binding indications of interest by May 3" which is structurally a round. Alex's categorization is defensible.

### Actionable items

- Fix export CSV to propagate bidder_type from actors_raw
- Add Company H May 23 drop to extraction
- Decide val convention for range bids (lower bound vs null)
