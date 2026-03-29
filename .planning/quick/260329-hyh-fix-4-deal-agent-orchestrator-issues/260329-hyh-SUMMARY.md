---
phase: quick
plan: 260329-hyh
subsystem: verify, deal-agent
tags: [bugfix, workflow, skill-docs]
dependency_graph:
  requires: []
  provides: [canonical-quote-findings-fix, deal-agent-procedure-fix]
  affects: [verify, deal-agent, enrich-deal, compose-prompts]
tech_stack:
  added: []
  patterns: [tdd-red-green]
key_files:
  created: []
  modified:
    - skill_pipeline/verify.py
    - tests/test_skill_verify.py
    - .claude/skills/deal-agent/SKILL.md
    - .codex/skills/deal-agent/SKILL.md
    - .cursor/skills/deal-agent/SKILL.md
decisions:
  - Canonical quote_verification findings were silently dropped; fix appends them to findings list
  - compose-prompts split into explicit --mode actors and --mode events steps
  - db-load/db-export re-run after enrich-deal to pick up enrichment overlay
  - Re-validation note after verify-extraction for stale gate artifacts
metrics:
  duration: 2m31s
  completed: 2026-03-29
---

# Quick Task 260329-hyh: Fix 4 Deal-Agent Orchestrator Issues Summary

Fixed canonical verify quote findings silently dropped and three deal-agent SKILL.md workflow gaps (compose-prompts event packets never generated, stale db after enrich-deal, stale gates after verify-extraction repairs).

## Task Results

### Task 1: Fix verify.py canonical quote findings bug (TDD)

**Bug:** `_collect_verification_findings` in `skill_pipeline/verify.py` (lines 506-510) computed `quote_findings` and `quote_checks` in the canonical branch but never appended them to the `findings` list or added `quote_checks` to `total_checks`. Canonical quote_verification findings were silently dropped.

**Fix:** Added two lines after the canonical branch call:
```python
findings.extend(quote_findings)
total_checks += quote_checks
```

**Regression test:** `test_verify_canonical_quote_findings_collected` creates a clean fixture, runs canonicalize, corrupts one span's `anchor_text`, runs verify, and asserts `exit_code == 1` with at least one `quote_verification` finding. The test fails on the unfixed code (exit_code 0) and passes on the fixed code.

**Commits:**
- `9f86576` test(260329-hyh): add failing test for canonical quote findings bug (RED)
- `1aaa7dc` fix(260329-hyh): append canonical quote findings in verify (GREEN)

### Task 2: Fix deal-agent SKILL.md procedure (3 workflow gaps)

**Fix 1 (HIGH):** Split compose-prompts into two explicit steps:
- Step 3a: `--mode actors` (before extract-deal)
- Step 4a: `--mode events` (after extract-deal produces actors_raw.json)

Previously `--mode all` only generated actor packets because `compose_events = mode == "events"`. Event packets were never generated.

**Fix 2 (MEDIUM):** Added steps 8a/8b to re-run db-load and db-export after enrich-deal writes enrichment.json with dropout_classifications. Previously DuckDB and CSV were stale after interpretive enrichment.

**Fix 3 (LOW-MEDIUM):** Added re-validation note after step 6 (verify-extraction) warning that if structural changes were made, steps 4c through 5b (check, verify, coverage, gates) must be re-run before enrich-core.

Updated Skills table to reflect compose-prompts actor/event split (0a, 0b, 0c). Synced mirrors via `sync_skill_mirrors.py`.

**Commit:** `605ee5d` docs(260329-hyh): fix deal-agent SKILL.md procedure (3 workflow gaps)

## Verification

- Full verify test suite: 9/9 passed
- Full test suite: 266/266 passed
- SKILL.md procedure numbering: sequential and consistent (1-9 with sub-steps)
- Skill mirrors: in sync

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED
