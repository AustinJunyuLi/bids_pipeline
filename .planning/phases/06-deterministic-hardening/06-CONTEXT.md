# Phase 6: Deterministic Hardening - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 4 documented runtime bugs from the 7-deal rerun so deterministic pipeline stages handle all edge cases without crashing or producing false findings. HARD-02 (coverage contextual CA phrases) and HARD-03 (check grouped NDA bidder counts) are already satisfied from fixes applied during the rerun.

Open requirements: HARD-06 (mixed-schema guard), HARD-01 (quote_id collision renumbering), HARD-04 (rollover CA tolerance), HARD-05 (DuckDB lock retry).

</domain>

<decisions>
## Implementation Decisions

### Mixed-Schema Guard (HARD-06)
- **D-01:** The mixed-schema check lives in the shared extract loader (`extract_artifacts.py`), not in individual consuming stages. `load_extract_artifacts()` explicitly checks `actors_canonical != events_canonical` and raises a dedicated `MixedSchemaError` before any downstream stage processes the artifacts. One fix protects check, verify, coverage, gates, and canonicalize.
- **D-02:** The current loader routes to canonical if EITHER artifact has span_ids. The fix adds an explicit mismatch check before that routing decision.

### Quote_id Renumbering (HARD-01)
- **D-03:** Canonicalize always renumbers event-side quote_ids above the actor-side max — defensive, not collision-triggered. Deterministic, no collision possible, idempotent on reruns.
- **D-04:** Same-array duplicate quote_ids still fail-fast (existing behavior preserved).
- **D-05:** The renumber mapping is logged in the existing `canonicalize_log.json` artifact. No new files.
- **D-06:** All actor/event/count-assertion references to renumbered quote_ids must be rewritten consistently. Partial renumbering (IDs changed but references not updated) is a hard error.

### Rollover CA Tolerance (HARD-04)
- **D-07:** Phase 6 ships text-pattern exclusion as the immediate fix. Coverage phrase lists and gates logic are expanded to recognize rollover/teaming/diligence CA language patterns from filing text. This stops false positives on existing artifacts without extraction changes.
- **D-08:** Phase 8 will add `nda_subtype` to the extraction schema (sale_process, rollover, teaming, diligence) for precise long-term classification. Phase 9 re-extracts with subtypes. Progressive improvement.
- **D-09:** Both gates (`_gate_actor_lifecycle`) and coverage (`_classify_cue_family`) get the text-pattern fix. Gates-only is insufficient — coverage also produces false positives on rollover CAs.

### DuckDB Lock Retry (HARD-05)
- **D-10:** Retry logic lives in `open_pipeline_db()` in `db_schema.py` — any caller gets automatic retry on transient lock. Single implementation point.
- **D-11:** Bounded retry: 3 attempts, exponential backoff (0.1s, 0.5s, 2s). Only lock-specific DuckDB exceptions are retried. Non-lock errors propagate immediately. Hard failure after exhaustion with a clear error message.

### Claude's Discretion
- Exact text patterns for rollover/teaming/diligence CA recognition (research filing language across the 9-deal corpus)
- `MixedSchemaError` class placement (in `extract_artifacts.py` or a shared exceptions module)
- Exact DuckDB exception class to catch for lock errors (requires version-specific research — lockfile pins DuckDB 1.5.1)
- Whether to add a `--force` flag to canonicalize that skips the mixed-schema check (probably not, but Claude can decide)
- Internal organization of the renumbering logic within canonicalize.py

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope
- `.planning/ROADMAP.md` — Phase 6 goal, success criteria, execution order (HARD-06 -> HARD-01 -> HARD-04 -> HARD-05)
- `.planning/REQUIREMENTS.md` — HARD-01, HARD-04, HARD-05, HARD-06 (open); HARD-02, HARD-03 (already satisfied)
- `.planning/PROJECT.md` — project constraints (correctness priority, fail-fast, filing-text-only truth)

### Evidence Sources
- `data/reconciliation_cross_deal_analysis.md` — Cross-deal reconciliation findings, systematic difference #4 (event type coverage gaps), #6 (actor identity)
- `quality_reports/session_logs/2026-03-29_7-deal-rerun_master.md` — Runtime walls, per-deal fix logs, exact error descriptions

### Target Source Files
- `skill_pipeline/extract_artifacts.py` — Shared loader: `load_extract_artifacts()`, `_payload_has_span_ids()`. HARD-06 fix location.
- `skill_pipeline/canonicalize.py` — `_resolve_quotes_to_spans()` duplicate check at line 102. HARD-01 fix location.
- `skill_pipeline/coverage.py` — `_classify_cue_family()` phrase lists starting at line 84. HARD-04 coverage-side fix location.
- `skill_pipeline/gates.py` — `_gate_actor_lifecycle()` at line 405, `_gate_cross_event_logic()` NDA-after-drop rule at line 331. HARD-04 gates-side fix location.
- `skill_pipeline/db_schema.py` — `open_pipeline_db()` at line 99. HARD-05 fix location.

### Models and Artifacts
- `skill_pipeline/models.py` — `QuoteEntry`, `RawSkillActorsArtifact`, `RawSkillEventsArtifact`, `SkillActorsArtifact`, `SkillEventsArtifact`
- `skill_pipeline/paths.py` — `SkillPathSet` with `canonicalize_log_path`

### Prior Phase Context
- `.planning/phases/04-enhanced-gates/04-CONTEXT.md` — Gate architecture, severity policy, cross-event rules (D-04 through D-07)
- `.planning/phases/05-integration-calibration/05-CONTEXT.md` — DuckDB schema, db-load/db-export design (D-01 through D-03)

### Existing Tests
- `tests/test_skill_check.py` — HARD-03 regression tests already present (grouped NDA bidder counts)
- `tests/test_skill_coverage.py` — HARD-02 regression tests already present (contextual CA exclusion)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_classify_cue_family()` in `coverage.py` — existing phrase-list pattern for NDA/CA classification. HARD-04 extends this with rollover/teaming patterns.
- `_payload_has_span_ids()` in `extract_artifacts.py` — already detects canonical vs quote-first per artifact. HARD-06 uses this to detect mismatches.
- `canonicalize_log.json` artifact — already written by canonicalize. HARD-01 appends renumber mapping here.
- `CheckFinding` / `GateFinding` severity model — existing tiered severity. HARD-04 gates fix follows the same pattern.

### Established Patterns
- Fail-fast on invalid state: `raise ValueError(...)`, `raise FileNotFoundError(...)`
- Stage modules have one `run_<stage>()` public function
- Pydantic `model_validate()` for JSON parsing, `model_dump(mode="json")` for output
- Private helpers prefixed with `_`

### Integration Points
- `extract_artifacts.py:44` — the `if actors_canonical or events_canonical:` branch is where HARD-06 inserts the mismatch check
- `canonicalize.py:102` — the `seen_ids` duplicate check is where HARD-01 inserts the renumbering step (before the check, not after)
- `coverage.py:112-118` — `references_prior_executed_nda` phrase list is where HARD-04 adds rollover/teaming patterns
- `gates.py:410-411` — `nda_signer_ids` accumulation is where HARD-04 could filter out non-sale-process NDA events
- `db_schema.py:106` — `duckdb.connect()` call is where HARD-05 wraps with retry

</code_context>

<specifics>
## Specific Ideas

- The Second Brain evaluation (Claude + GPT-5.4) confirmed HARD-02 and HARD-03 are already satisfied and recommended reducing Phase 6 from 6 to 4 open items.
- GPT found that petsmart-inc `coverage_findings.json:238` still contains a rollover-CA false positive — use this as a concrete test case for HARD-04.
- The execution log for zep documents the exact mixed-schema failure: "events_raw.json reverted to quote-first while actors_raw.json remained canonical; likely overlapping worker write after canonicalize." Use as regression test case.
- The execution log for penford documents the exact quote_id collision: "canonicalize hit duplicate quote_id collisions; fixed by renumbering event-side quote ids above the actor-side max." Use as regression test case.
- DuckDB version mismatch: lockfile pins 1.5.1 but local runtime may differ. Research the exact exception class before implementing HARD-05.

</specifics>

<deferred>
## Deferred Ideas

- `nda_subtype` extraction schema field (sale_process, rollover, teaming, diligence) — Phase 8 scope (extraction guidance)
- Per-deal artifact locking or atomic writes to prevent concurrent write corruption — orchestration concern, not deterministic stage hardening
- Comprehensive rollover/teaming CA pattern coverage beyond the 9-deal corpus — future corpus expansion

</deferred>

---

*Phase: 06-deterministic-hardening*
*Context gathered: 2026-03-29*
