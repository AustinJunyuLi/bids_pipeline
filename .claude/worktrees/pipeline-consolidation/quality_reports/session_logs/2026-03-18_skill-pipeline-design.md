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
