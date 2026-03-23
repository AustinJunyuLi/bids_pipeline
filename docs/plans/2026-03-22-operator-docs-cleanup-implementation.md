# Operator Docs Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite the authoritative operator documentation around the consolidated `skill_pipeline`, remove redundant legacy instruction surfaces, and leave the worktree in a commit-ready state.

**Architecture:** Treat `CLAUDE.md` as the sole authoritative runbook for operators and agents. Keep historical design and diagnosis material as archive-only context, but remove redundant legacy skill-doc mirrors and any extra instruction layer that can drift from `CLAUDE.md`. Clean untracked runtime artifacts so the branch can be committed cleanly.

**Tech Stack:** Markdown docs, pytest regression tests, git, Python CLI runtime

---

### Task 1: Rewrite the authoritative operator docs

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/design.md`
- Modify: `docs/HOME_COMPUTER_SETUP.md` only if the new runbook requires consistency fixes

**Step 1: Write the failing doc regression expectation**

Use the existing benchmark-separation regression plus a manual checklist:
- `CLAUDE.md` must no longer describe the deleted hybrid skill workflow
- `CLAUDE.md` must describe `skill-pipeline run --deal <slug>` as the production runner
- `CLAUDE.md` must state that `python scripts/reconcile_alex.py --deal <slug>` is post-production only
- `docs/design.md` must no longer claim the v3 `pipeline/` design is current

**Step 2: Run the focused regression**

Run:
```bash
pytest tests/test_benchmark_separation_policy.py -q -s
```

**Step 3: Rewrite the docs**

- Replace the stale lower half of `CLAUDE.md` with:
  - current repository purpose
  - active directory map
  - backend configuration
  - seed-only source contract
  - exact production stage sequence
  - stage ownership and artifact layout
  - benchmark separation
  - troubleshooting / prerequisites
  - note that historical references to `pipeline/` or slash-skills are archival only
- Rewrite `docs/design.md` so the active design index points to the consolidation docs and marks older plans as historical
- Keep wording precise and operator-oriented

**Step 4: Re-run the focused regression**

Run:
```bash
pytest tests/test_benchmark_separation_policy.py -q -s
```

### Task 2: Remove redundant legacy instruction surfaces

**Files:**
- Delete: `docs/skills/README.md`
- Delete: `docs/skills/deal-agent.md`
- Delete: `docs/skills/extract-deal.md`
- Delete: `docs/skills/verify-extraction.md`
- Delete: `docs/skills/enrich-deal.md`
- Delete: `docs/skills/export-csv.md`
- Delete: `docs/skills/reconcile-alex.md`
- Modify: `tests/test_benchmark_separation_policy.py`

**Step 1: Update the failing regression**

Change the regression so it validates the benchmark boundary against active docs only:
- `CLAUDE.md`
- `docs/HOME_COMPUTER_SETUP.md`
- warning docs in `example/` and `diagnosis/`

Add an explicit assertion that `docs/skills/` legacy references are removed.

**Step 2: Run the test to verify the old assumption fails**

Run:
```bash
pytest tests/test_benchmark_separation_policy.py -q -s
```

**Step 3: Delete the redundant files**

Delete the `docs/skills/*.md` legacy copies after the test no longer depends on them.

**Step 4: Re-run the regression**

Run:
```bash
pytest tests/test_benchmark_separation_policy.py -q -s
```

### Task 3: Clean commit hygiene artifacts

**Files:**
- Delete untracked runtime artifacts only if they are local outputs and not intended source files:
  - `diagnosis/backend_load/*.json`
  - `raw/stec/**`
  - `data/deals/stec/source/**`

**Step 1: Verify they are generated runtime artifacts, not required source-controlled files**

Inspect with:
```bash
find diagnosis/backend_load -maxdepth 2 -type f | sort
find raw/stec -maxdepth 3 -type f | sort
find data/deals/stec -maxdepth 3 -type f | sort
```

**Step 2: Remove only the generated, untracked artifacts**

Use non-destructive file deletes through the normal editing flow so the final commit excludes local probes and partial validation artifacts.

**Step 3: Verify commit cleanliness**

Run:
```bash
git status --short
```

Confirm the remaining diff contains only intentional source changes.

### Task 4: Final verification and commit

**Files:**
- Commit all intended source changes in this worktree

**Step 1: Run the full test suite**

Run:
```bash
pytest tests -q -s
```

Expected: PASS, with only the existing `edgar` deprecation warnings.

**Step 2: Inspect git status**

Run:
```bash
git status --short
```

**Step 3: Create the commit**

Run:
```bash
git add -A
git commit -m "chore: rewrite operator docs and remove stale pipeline surfaces"
```
