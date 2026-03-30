---
phase: 08-extraction-guidance-enrichment-extensions
plan: 01
subsystem: skill-docs
tags: [extract-deal, skill-mirrors, extraction-guidance]
requires:
  - phase: 07-bid-type-rule-priority
    provides: corrected deterministic enrichment vocabulary and stable phase-08 planning context
provides:
  - canonical extract-deal guidance for round milestones, verbal/oral proposals, and NDA exclusions
  - synced `.codex` and `.cursor` skill mirrors
  - regression assertions that the new guidance remains present in the canonical skill doc
affects: [extract-deal, skill-mirrors, phase-09 re-extraction]
tech-stack:
  added: []
  patterns:
    - canonical skill doc edits in `.claude/skills/` with mirror sync via `scripts/sync_skill_mirrors.py`
key-files:
  created:
    - .planning/phases/08-extraction-guidance-enrichment-extensions/08-01-SUMMARY.md
  modified:
    - .claude/skills/extract-deal/SKILL.md
    - .codex/skills/extract-deal/SKILL.md
    - .cursor/skills/extract-deal/SKILL.md
    - tests/test_skill_mirror_sync.py
key-decisions:
  - "Round milestone guidance stays inside the existing six round event types; no schema expansion."
  - "Verbal/oral bids with explicit economics remain `proposal` events; only the guidance changed."
  - "NDA exclusions remain documentation-only logic; rollover, teaming, and non-target diligence agreements stay out of `nda` extraction."
patterns-established:
  - "Phase-08 extraction guidance changes must land in `.claude/skills/` first and then sync to mirrors."
requirements-completed: [EXTRACT-01, EXTRACT-02, EXTRACT-03]
duration: session
completed: 2026-03-30
---

# Phase 08 Plan 01: Extraction Guidance Summary

**Added the missing extraction guidance for round milestones, verbal/oral price indications, and NDA exclusions, then synced the skill mirrors and locked the content with regression tests.**

## Performance

- **Completed:** 2026-03-30
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added a new `Round Milestone Events` section to the canonical extract skill with paired announcement/deadline rules, `invited_actor_ids` handling, and filing-grounded stec examples.
- Added a `Verbal/Oral Price Indications` section clarifying that priced verbal bids are still `proposal` events, with mac-gray and penford examples.
- Added an `NDA Exclusion Guidance` section to keep rollover-side, bidder-bidder teaming, and non-target diligence agreements out of `nda` extraction unless the filing ties them to target diligence access.
- Synced `.codex/skills/extract-deal/SKILL.md` and `.cursor/skills/extract-deal/SKILL.md` from the canonical `.claude` source.
- Added three content-verification tests to `tests/test_skill_mirror_sync.py` so future edits cannot silently remove the new guidance.

## Verification

- `python scripts/sync_skill_mirrors.py`
- `.\.venv\Scripts\python.exe -m pytest tests/test_skill_mirror_sync.py -q`

Result: `8 passed`.

## Issues Encountered

- The repo virtualenv was missing declared package dependencies at execution start. Installed the project into `.venv` before running runtime-backed tests later in the phase; the mirror-sync tests themselves were unaffected.

## Self-Check: PASSED

- Verified the canonical skill doc contains all three new guidance headings.
- Verified `.codex` and `.cursor` mirrors match the canonical file byte-for-byte.
- Verified the mirror-sync test suite passes with the new content assertions.

---
*Phase: 08-extraction-guidance-enrichment-extensions*
*Completed: 2026-03-30*
