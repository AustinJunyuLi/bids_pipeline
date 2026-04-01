---
phase: 20-proposal-linkage-bid-type-repair
verified: 2026-04-01T12:05:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 20: Proposal Linkage + Bid-Type Repair Verification Report

**Phase Goal:** Repair proposal-to-phase association and bid-type derivation so
proposal rows reflect filing-supported chronology and formality signals.

**Verified:** 2026-04-01T12:05:00Z
**Status:** passed
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | proposal derivation no longer trusts malformed or forward `requested_by_observation_id` links | VERIFIED | `skill_pipeline/derive.py` now validates proposal links through `_trusted_requested_phase_for_proposal` and falls back to the latest same-day-or-earlier solicitation when the explicit link is invalid. |
| 2 | proposal `bid_type` uses bounded proposal-local formality cues before falling back to phase inheritance | VERIFIED | `skill_pipeline/derive.py` now evaluates markup, merger-agreement, definitive/final, and non-binding/IOI cues through `_proposal_bid_type`. |
| 3 | `gates-v2` blocks non-solicitation and forward proposal-request links | VERIFIED | `skill_pipeline/gates_v2.py` now emits `proposal_request_not_solicitation` and `proposal_request_points_forward` blocker findings. |
| 4 | the chronology and precedence rules are pinned by direct regression tests | VERIFIED | `tests/test_skill_derive.py` and `tests/test_skill_gates_v2.py` cover fallback to prior solicitations, local bid-type cues without a valid phase link, and both new gate blockers. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skill_pipeline/derive.py` | Safe proposal association and bid-type inference | VERIFIED | Proposal links are validated before use and proposal rows now classify `bid_type` from bounded local cues plus valid phase context. |
| `skill_pipeline/gates_v2.py` | Proposal-link blocker findings | VERIFIED | Adds explicit blockers for wrong-type and forward proposal links. |
| `tests/test_skill_derive.py` | Derive regression coverage | VERIFIED | Covers future-link fallback and proposal-local formality inference without valid phase context. |
| `tests/test_skill_gates_v2.py` | Gate regression coverage | VERIFIED | Covers the new proposal-link gate failures directly. |

### Behavioral Spot-Checks

| Behavior | Command / Check | Result | Status |
|----------|-----------------|--------|--------|
| Focused proposal slice | `pytest -q tests/test_skill_derive.py tests/test_skill_gates_v2.py -k 'proposal or link or bid_type or formality or future or solicitation'` | `8 passed, 8 deselected` | PASS |
| Full derive + gate suite | `pytest -q tests/test_skill_derive.py tests/test_skill_gates_v2.py` | `16 passed` | PASS |
| Broader v2 regression bundle | `pytest -q tests/test_skill_observation_models.py tests/test_skill_extract_artifacts_v2.py tests/test_skill_canonicalize_v2.py tests/test_skill_check_v2.py tests/test_skill_coverage_v2.py tests/test_skill_gates_v2.py tests/test_skill_derive.py tests/test_skill_pipeline.py` | `77 passed` | PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| LINK-01 | Ignore future-linked proposal requests and fall back to same-day-or-earlier solicitations | SATISFIED | `derive.py` validates requested solicitation timing before using the link. |
| LINK-02 | Use proposal-local cues for `bid_type` classification | SATISFIED | `_proposal_bid_type` now prioritizes markup/merger-agreement and non-binding/IOI signals before phase fallback. |
| LINK-03 | Block forward or wrong-type proposal links in v2 gates | SATISFIED | `gates_v2.py` now emits explicit blocker findings for both malformed link classes. |

### Human Verification Required

None for this synthetic validation slice.

### Gaps Summary

No phase-blocking gaps remain inside the Phase 20 scope. Later phases still own
transition dating, outcome normalization, and export/taxonomy work.

---

_Verified: 2026-04-01T12:05:00Z_
_Verifier: Codex_
