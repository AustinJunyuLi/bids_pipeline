# Seed-Only Pipeline Correction Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the clean `baseline-check-summary` branch use the seed URL as the only upstream filing source for raw fetch and source preprocess.

**Architecture:** Keep the provenance, date normalization, and coverage work, but replace the stale multi-filing upstream layer with the seed-only raw discovery/fetch/preprocess contract already developed on `skill-engine`. The correction is intentionally narrow: one filing in `raw/`, one filing in `data/deals/<slug>/source/`, and deterministic failures when legacy multi-filing manifests are present.

**Tech Stack:** Python 3.11, pytest, existing `skill_pipeline` CLI and Pydantic models.

---

### Task 1: Add Seed-Only Regression Tests

**Files:**
- Create: `tests/test_skill_raw_stage.py`
- Create: `tests/test_skill_preprocess_source.py`

- [ ] **Step 1: Write the failing raw-stage tests**

Add tests covering:
- seed URL discovery produces exactly one primary candidate and no supplementary candidates
- ambiguous or non-SEC seed URLs fail
- raw fetch freezes exactly one document
- live identity resolution requires `EDGAR_IDENTITY` or explicit `identity=...`

- [ ] **Step 2: Run raw-stage tests to verify they fail**

Run: `pytest -q tests/test_skill_raw_stage.py`
Expected: failures on the clean branch because it still supports multi-candidate discovery/fetch.

- [ ] **Step 3: Write the failing preprocess tests**

Add tests covering:
- preprocess scans only the one seed document
- stale `supplementary_snippets.jsonl` and stale extra filings are removed
- preprocess fails if discovery has supplementary candidates, multiple primary candidates, or multiple registry documents

- [ ] **Step 4: Run preprocess tests to verify they fail**

Run: `pytest -q tests/test_skill_preprocess_source.py`
Expected: failures on the clean branch because preprocess still scans all candidates and preserves supplementary artifacts.

### Task 2: Port Seed-Only Raw Discovery And Fetch

**Files:**
- Modify: `skill_pipeline/raw/discover.py`
- Modify: `skill_pipeline/raw/stage.py`
- Modify: `skill_pipeline/pipeline_models/raw.py`
- Modify: `skill_pipeline/raw/__init__.py`
- Test: `tests/test_skill_raw_stage.py`

- [ ] **Step 1: Port seed-only discovery**

Implement discovery directly from `seed.primary_url_seed`, extracting one unambiguous SEC accession and emitting:
- one `primary_candidates` entry
- empty `supplementary_candidates`
- `fetch_scope="seed_only"`

- [ ] **Step 2: Port seed-only fetch**

Make `fetch_raw_deal()`:
- require configured SEC identity for live fetches
- fetch exactly the one discovery candidate
- write a registry with exactly one document

- [ ] **Step 3: Adjust raw manifest model for the new contract**

Update `RawDiscoveryManifest.fetch_scope` so new writes are `seed_only` while remaining readable for legacy manifests if needed during transition.

- [ ] **Step 4: Run raw-stage tests to verify they pass**

Run: `pytest -q tests/test_skill_raw_stage.py`
Expected: pass.

### Task 3: Port Seed-Only Preprocess

**Files:**
- Modify: `skill_pipeline/preprocess/source.py`
- Test: `tests/test_skill_preprocess_source.py`

- [ ] **Step 1: Enforce one-document preprocess inputs**

Make preprocess fail fast unless:
- `len(primary_candidates) == 1`
- `supplementary_candidates == []`
- `len(registry.documents) == 1`

- [ ] **Step 2: Scan only the seed filing**

Build chronology and evidence from the single frozen document only. Remove the older multi-candidate ranking/evaluation loop and supplementary evidence scan.

- [ ] **Step 3: Clean stale supplementary artifacts**

Before materializing source files:
- delete stale `source/supplementary_snippets.jsonl`
- delete extra filing copies in `source/filings/` that are not the current single document

- [ ] **Step 4: Run preprocess tests to verify they pass**

Run: `pytest -q tests/test_skill_preprocess_source.py`
Expected: pass.

### Task 4: Trim Conflicting Surface And Update Repo Contract

**Files:**
- Modify: `CLAUDE.md`
- Modify: `skill_pipeline/raw/__init__.py` if exports are stale
- Optional modify: `skill_pipeline/source/__init__.py` only if stale supplementary exports now mislead users or tests
- Test: targeted existing skill-pipeline tests if impacted

- [ ] **Step 1: Update the repository manual**

Document that seed-only raw fetch and preprocess are authoritative for the skill pipeline, and that a rerun from raw is required if old multi-filing `raw/<slug>/discovery.json` artifacts still exist.

- [ ] **Step 2: Remove or leave clearly unused stale surface**

Do not broad-refactor. Only remove exports or references that directly conflict with the seed-only contract.

- [ ] **Step 3: Run impacted existing tests**

Run: `pytest -q tests/test_skill_pipeline.py tests/test_skill_canonicalize.py tests/test_skill_verify.py`
Expected: pass.

### Task 5: Full Verification And Branch Cleanup

**Files:**
- Modify: none necessarily

- [ ] **Step 1: Run the full test suite**

Run: `pytest -q --tb=short`
Expected: all tests pass.

- [ ] **Step 2: Inspect git state**

Run: `git status --short --branch`
Expected: only intended code/doc/test changes are present.

- [ ] **Step 3: Remove stale local branch/worktree after successful transplant**

Delete the obsolete `remove-supplementary` local worktree and branch once the clean branch fully contains the seed-only upstream contract.
