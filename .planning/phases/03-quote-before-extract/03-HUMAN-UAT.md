---
status: passed
phase: 03-quote-before-extract
source: [03-VERIFICATION.md]
started: 2026-03-28T10:32:38Z
updated: 2026-03-28T11:13:00Z
---

## Current Test

Both live/manual extraction checks completed and passed, with non-blocking caveats recorded below.

## Tests

### 1. stec live extraction quality
expected: Raw extraction artifacts begin with a `quotes` array, downstream deterministic gates pass, and quote grounding is at least as strong as the pre-phase baseline.
result: PASSED — quote-first provenance was proven indirectly through prompt artifacts and `canonicalize_log.json` orphaned `Q###` IDs, `canonicalize/check/verify` all passed, and a manual grounding spot-check matched the filing text. Non-blocking caveats: some NDA dates remain `precision: "unknown"` and one sampled support span was `fuzzy`.

### 2. medivation stress-case extraction quality
expected: The quote-first protocol preserves actor and event recall on the complex deal while improving evidence grounding quality.
result: PASSED — prompt artifacts are fresh, `canonicalize_log.json` shows orphaned `Q###` IDs proving quote-first input, `check` and `verify` passed cleanly, and the sampled proposal/final-round sequence looked grounded. Non-blocking caveats: two NDA assignments remain explicitly identity-uncertain and several stored spans are `fuzzy`, but neither blocked the deterministic gates.

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

None. Both manual checks passed with only non-blocking quality caveats.
