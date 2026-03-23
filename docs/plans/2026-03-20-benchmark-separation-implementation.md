# Benchmark Separation Implementation Plan

> Historical note: this plan predates the final cleanup of mirrored skill directories. Active benchmark-boundary enforcement now lives in `CLAUDE.md`, the Python runtime, and the test suite; references below to old skill mirrors are archival.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enforce a hard separation between filing-grounded generation and post-export benchmark reconciliation in the live repo instructions.

**Architecture:** Update the authoritative repo instructions and active skill mirrors so benchmark materials are forbidden before `/export-csv`, then add a regression test that asserts the active docs preserve that boundary. Keep the runtime code unchanged except for wording-level cleanup where needed.

**Tech Stack:** Markdown skill docs, `pytest`

---

### Task 1: Write the policy regression test

**Files:**
- Create: `tests/test_benchmark_separation_policy.py`

**Step 1: Write the failing test**

- Assert that the active generation instruction files do not mention direct
  benchmark inputs such as `example/deal_details_Alex_2026.xlsx` or
  `CollectionInstructions_Alex_2026.qmd`.
- Assert that the active `reconcile-alex` skill requires post-export usage and
  does not permit the old extraction-plus-enrichment fallback.

**Step 2: Run the test to verify it fails**

Run: `pytest -q tests/test_benchmark_separation_policy.py`

Expected: fail against the current repo state.

### Task 2: Patch the authoritative repo instructions

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add benchmark-separation policy**

- Add a short section that explicitly lists allowed and forbidden pre-export
  inputs.
- State that benchmark materials are only for post-export `/reconcile-alex`
  usage.

**Step 2: Remove ambiguous generation wording**

- Reword `/export-csv` from “Alex-compatible” framing to a fixed repo review CSV
  contract.

### Task 3: Patch the active generation skill mirrors

**Files:**
- Modify: `.claude/skills/deal-agent/SKILL.md`
- Modify: `.codex/skills/deal-agent/SKILL.md`
- Modify: `.cursor/skills/deal-agent/SKILL.md`
- Modify: `.claude/skills/extract-deal/SKILL.md`
- Modify: `.codex/skills/extract-deal/SKILL.md`
- Modify: `.cursor/skills/extract-deal/SKILL.md`
- Modify: `.claude/skills/verify-extraction/SKILL.md`
- Modify: `.codex/skills/verify-extraction/SKILL.md`
- Modify: `.cursor/skills/verify-extraction/SKILL.md`
- Modify: `.claude/skills/enrich-deal/SKILL.md`
- Modify: `.codex/skills/enrich-deal/SKILL.md`
- Modify: `.cursor/skills/enrich-deal/SKILL.md`
- Modify: `.claude/skills/export-csv/SKILL.md`
- Modify: `.codex/skills/export-csv/SKILL.md`
- Modify: `.cursor/skills/export-csv/SKILL.md`

**Step 1: Add a benchmark-separation rule**

- State that these skills must not read Alex benchmark materials before export
  completes.

**Step 2: Reword export framing**

- Treat export as a fixed review-CSV contract, not a benchmark lookup step.

### Task 4: Patch the reconcile-only skill mirrors

**Files:**
- Modify: `.claude/skills/reconcile-alex/SKILL.md`
- Modify: `.codex/skills/reconcile-alex/SKILL.md`
- Modify: `.cursor/skills/reconcile-alex/SKILL.md`

**Step 1: Make reconciliation strictly post-export**

- Remove the extraction-plus-enrichment fallback path.
- Require `data/skill/<slug>/export/deal_events.csv` as a prerequisite.
- State explicitly that benchmark materials are forbidden during generation and
  only belong in this post-export skill.

### Task 5: Verify the boundary

**Files:**
- No new files

**Step 1: Run the focused policy test**

Run: `pytest -q tests/test_benchmark_separation_policy.py`

Expected: pass.

**Step 2: Run the full test suite**

Run: `pytest -q`

Expected: pass.
