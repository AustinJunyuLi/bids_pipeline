# Research Summary: v1.1 Reconciliation + Execution-Log Quality Fixes

**Domain:** Filing-grounded M&A extraction pipeline -- quality fixes and hardening
**Researched:** 2026-03-29
**Overall confidence:** HIGH

## Executive Summary

The v1.1 milestone addresses systematic bugs and gaps identified by two
independent audits: (1) a 9-deal cross-deal reconciliation comparing pipeline
output against a hand-coded benchmark, and (2) a 7-deal fresh rerun that
logged every runtime wall. These are not speculative improvements -- they are
fixes for documented, reproducible issues with clear root causes.

The reconciliation found that the pipeline wins filing arbitrations 45:16
against the benchmark but has one major systematic bug: the `bid_type`
enrichment rule priority causes final-round proposals to be misclassified as
Informal across 5+ deals. This is a mechanical rule-ordering fix in
`enrich_core.py`'s `_classify_proposal()` function -- Rule 1 (IOI language ->
Informal) fires before Rule 2.5 (after final round -> Formal). The M&A
convention is that process position overrides language signals. The pipeline also
has complementary coverage gaps versus the benchmark: it misses round milestone
events (which its schema already supports) and committee-driven field narrowing
(DropTarget dropout labels, already supported in the `DropoutClassification`
model). These gaps are extraction-side, not infrastructure-side.

The execution log identified runtime fragility in three clear areas:
(1) canonicalize crashes on duplicate quote_ids when actor and event extraction
passes use overlapping ID namespaces -- the fix is deterministic renumbering
before the merge;
(2) DuckDB file-lock contention when db-export runs immediately after db-load --
the fix is a 3-retry loop with exponential backoff in `open_pipeline_db()`;
(3) coverage false positives on contextual confidentiality-agreement mentions
that describe existing NDAs rather than new signings -- the fix is expanding
the exclusion phrase list in `_classify_cue_family()`.

All target features integrate cleanly with the existing architecture. No new
Python dependencies. No new modules. The event_type schema already supports
round milestones. The dropout classification model already supports DropTarget
labels. The proposal schema already supports verbal indications. The only
feature requiring schema extension is all_cash inference (one new nullable
DuckDB column in the enrichment table).

## Key Findings

**Stack:** No new dependencies. All changes are within existing `skill_pipeline/`
Python package and DuckDB schema.

**Architecture:** Changes span 7 Python files but are isolated to specific
functions within each. No new modules needed. See ARCHITECTURE.md for the
detailed 9-integration-point analysis and dependency graph.

**Critical pitfall:** The bid_type rule fix must land before any re-enrichment
run, or it perpetuates the misclassification across all 9 deals. The fix is
NOT "always promote to Formal" -- it is "final-round context overrides IOI
language." Early IOIs before any formal round should remain Informal.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Hardening fixes (parallel)** - DuckDB lock retry, quote_id collision prevention, coverage false-positive expansion
   - Addresses: Runtime walls from execution log (canonicalize crash, DuckDB lock, coverage FP)
   - Avoids: Blocking the critical path (these are independent of each other)
   - Rationale: Three independent single-function changes with clear test contracts. Can parallelize with everything else.

2. **bid_type rule priority fix** - Reorder `_classify_proposal()` rules in enrich_core.py
   - Addresses: Biggest accuracy bug per reconciliation (5+ deals affected, mac-gray, stec, prov-worcester, imprivata, penford)
   - Avoids: Re-enrichment before the fix lands
   - Rationale: Single-function change but highest impact. Must validate against all 9 deals before proceeding.

3. **Extraction skill-doc updates** - Round milestones, DropTarget, verbal indications, NDA exclusion guidance
   - Addresses: Coverage gaps identified by reconciliation (event types Alex captures that pipeline doesn't)
   - Avoids: Python infrastructure changes (infra already supports all of these)
   - Rationale: The bottleneck is extraction instructions, not code. Skill docs must reference the corrected bid_type behavior.

4. **Enrichment extensions** - all_cash contextual inference, deterministic DropTarget classification
   - Addresses: Remaining reconciliation gaps (conservative all_cash, committee-driven drops)
   - Avoids: Schema changes until base functionality is correct
   - Rationale: New inference logic builds on corrected enrichment rules. Requires careful boundary-case testing (CVR deals, mixed consideration).

5. **Deal-specific extraction fixes** - Zep NMC actor error, Medivation missing drops
   - Addresses: Per-deal extraction errors found in reconciliation
   - Avoids: Code changes (these are re-extraction, not pipeline code fixes)
   - Rationale: Requires re-running `/extract-deal` with corrected skill docs from Phase 3.

**Phase ordering rationale:**
- Hardening fixes (Phase 1) are independent and off the critical path.
- bid_type fix (Phase 2) is the single highest-impact change and blocks accurate re-enrichment.
- Skill-doc updates (Phase 3) depend on understanding the corrected bid_type behavior.
- Enrichment extensions (Phase 4) build on corrected enrichment infrastructure.
- Deal-specific fixes (Phase 5) require re-extraction, which should use the improved skill docs.

**Research flags for phases:**
- Phase 1 (hardening): Standard patterns, unlikely to need further research. Verify DuckDB IOException class hierarchy for retry.
- Phase 2 (bid_type): Clear root cause, well-understood fix. Needs careful regression testing against all 9 deals.
- Phase 3 (skill docs): May need deeper research on few-shot example design for round milestones and DropTarget events.
- Phase 4 (enrichment extensions): all_cash inference rules need validation against actual deal patterns to avoid false positives on mixed-consideration deals.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new dependencies; all changes in existing codebase |
| Features | HIGH | Each feature has a clear root cause from reconciliation or execution log |
| Architecture | HIGH | Integration points verified against actual source code in 7 modules |
| Pitfalls | HIGH | Pitfalls derived from actual runtime failures, not speculation |

## Gaps to Address

- **DuckDB IOException class hierarchy:** Verify the exact exception class and message format for lock errors in DuckDB 1.5.1. The retry strategy assumes `duckdb.IOException` with "lock" in the message.
- **all_cash inference false-positive rate:** The contextual inference rules (propagate cash from executed event) need validation against edge cases like mixed-consideration deals (prov-worcester cash+CVR).
- **Round milestone few-shot examples:** The extraction skill docs will need concrete examples from deals where the benchmark has round milestones and the pipeline doesn't.
- **DropTarget classification heuristic quality:** Deterministic rules for classifying committee-driven drops need testing against the 9-deal corpus to avoid over-classifying bidder-initiated withdrawals.
- **Coverage phrase expansion:** The initial exclusion patterns from zep, saks, and petsmart-inc may not cover all filing language variations for contextual CA mentions.

## Sources

- Cross-deal reconciliation analysis: `data/reconciliation_cross_deal_analysis.md`
- 7-deal execution log: `quality_reports/session_logs/2026-03-29_7-deal-rerun_master.md`
- Source code: `skill_pipeline/enrich_core.py` (lines 209-272), `skill_pipeline/canonicalize.py` (lines 88-142), `skill_pipeline/coverage.py` (lines 84-224), `skill_pipeline/db_schema.py` (lines 99-109), `skill_pipeline/models.py`, `skill_pipeline/check.py`, `skill_pipeline/gates.py`
- DuckDB concurrency documentation: https://duckdb.org/docs/stable/connect/concurrency
