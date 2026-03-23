# Alex Alignment Pipeline Fixes Implementation Plan

> Historical note: this plan predates the final Python-only `skill_pipeline/` runtime. References below to hybrid skills, `canonicalize`, or mirrored skill directories are archival; the live production contract is in `CLAUDE.md`.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Align the hybrid skill pipeline with Alex's benchmark logic for start-of-sale markers and preserve extraction audit data through canonicalization.

**Architecture:** Add deterministic recovery for missing `bidder_sale` process markers in canonicalization, add a verification guard so pre-`target_sale` bids cannot silently omit `bidder_sale`, and preserve `coverage_notes`/`exclusions` when canonicalizing. Keep the ambiguous late-stage formality policy separate unless a deterministic rule is explicitly chosen.

**Tech Stack:** Python, pytest, repo skill docs (`.claude`, `.codex`, `.cursor`)

---

### Task 1: Lock the regressions into tests

**Files:**
- Modify: `tests/test_skill_canonicalize.py`
- Modify: `tests/test_skill_verify.py`

**Step 1: Write the failing tests**

- Add a canonicalize test that preserves `coverage_notes` and `exclusions`.
- Add a canonicalize test that inserts a synthetic `bidder_sale` before a later `target_sale` when a whole-company proposal exists first.
- Add a canonicalize test that does not insert `bidder_sale` when the proposal occurs after `target_sale`.
- Add a verify test that emits an error when a pre-`target_sale` proposal exists without a matching `bidder_sale`.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_skill_canonicalize.py tests/test_skill_verify.py -q`

Expected: new tests fail before implementation.

### Task 2: Implement deterministic pipeline fixes

**Files:**
- Modify: `skill_pipeline/canonicalize.py`
- Modify: `skill_pipeline/verify.py`

**Step 1: Preserve extract audit data**

- Keep `events_artifact.exclusions` and `events_artifact.coverage_notes` when writing canonicalized events back to disk.

**Step 2: Recover missing bidder-sale markers**

- In `canonicalize.py`, synthesize a `bidder_sale` event when:
  - a whole-company `proposal` appears before the first `target_sale`, and
  - no earlier `bidder_sale` exists for that bidder.
- Insert the synthetic event before the proposal in event order.
- Record recovery details in the canonicalize log.

**Step 3: Add verification guardrail**

- In `verify.py`, add a structural-integrity rule that raises an error when a proposal precedes the first `target_sale` but no matching `bidder_sale` marker exists for that bidder.

### Task 3: Update skill instructions to match the deterministic guardrails

**Files:**
- Modify: `.claude/skills/extract-deal/SKILL.md`
- Modify: `.codex/skills/extract-deal/SKILL.md`
- Modify: `.cursor/skills/extract-deal/SKILL.md`
- Modify: `.claude/skills/export-csv/SKILL.md`
- Modify: `.codex/skills/export-csv/SKILL.md`
- Modify: `.cursor/skills/export-csv/SKILL.md`

**Step 1: Clarify bidder-sale semantics**

- Define `bidder_sale` as the separate process-marker row used when a bidder's actual bid triggers the sale process.
- Clarify that `bidder_sale` can coexist with the priced `proposal` row and with a later `target_sale`.

**Step 2: Clarify exporter handling**

- Make clear that exported `Bidder Sale` is distinct from the proposal row and must not be collapsed into the bid row.

### Task 4: Verify the implementation

**Files:**
- No new files.

**Step 1: Run focused tests**

Run: `pytest tests/test_skill_canonicalize.py tests/test_skill_verify.py -q`

Expected: pass.

**Step 2: Run broader regression coverage**

Run: `pytest tests/test_skill_check.py tests/test_skill_canonicalize.py tests/test_skill_verify.py tests/test_skill_enrich_core.py tests/test_skill_pipeline.py -q`

Expected: pass.

### Task 5: Summarize residual risks

**Files:**
- No new files.

**Step 1: Document what remains intentionally unresolved**

- Call out that the Imprivata July 9 `$19.25` classification remains a separate policy question unless deterministic enrichment is explicitly changed.
- Call out that post-signing press-release semantics remain doc-ambiguous and should be handled in a separate change.
