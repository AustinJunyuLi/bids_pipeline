---
phase: 06-deterministic-hardening
verified: 2026-03-29T22:22:49Z
status: passed
score: 4/4 must-haves verified
---

# Phase 6: Deterministic Hardening Verification Report

**Phase Goal:** Pipeline deterministic stages handle all documented edge cases from the 7-deal rerun without crashing, producing false findings, or accepting corrupt inputs
**Verified:** 2026-03-29T22:22:49Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Loading extract artifacts where actors are canonical but events are quote-first, or vice versa, raises a dedicated `MixedSchemaError` before stage-specific processing | ✓ VERIFIED | `load_extract_artifacts()` computes actor/event mode and raises `MixedSchemaError` before canonical-sidecar validation or parsing in `skill_pipeline/extract_artifacts.py:39-60`. The shared loader is used by `canonicalize`, `check`, `verify`, `coverage`, `gates`, `db-load`, `enrich-core`, and `deal-agent`. Behavioral proof: `python -m pytest -q tests/test_skill_extract_artifacts.py -k "mixed_schema or spans"` → `3 passed in 0.13s`. |
| 2 | `skill-pipeline canonicalize` handles overlapping actor/event `quote_id` namespaces by deterministic cross-array renumbering, rewrites references consistently, remains idempotent on reruns, and still fail-fast rejects same-array duplicates | ✓ VERIFIED | `skill_pipeline/canonicalize.py:145-215` validates same-array uniqueness, remaps actor quotes to `qa_###`, event quotes to `qe_###`, and rewrites actor, count-assertion, and event references before merge; `run_canonicalize()` applies that remap before `_resolve_quotes_to_spans()` in `skill_pipeline/canonicalize.py:475-527`. Regression proof: `python -m pytest -q tests/test_skill_canonicalize.py -k "duplicate_quote_ids or cross_array or idempotent"` → `3 passed, 13 deselected in 0.13s`. |
| 3 | `skill-pipeline coverage` and `skill-pipeline gates` do not raise false NDA findings for rollover-side, bidder-bidder teaming, and target-on-target diligence confidentiality agreements, while preserving real sale-process bidder-target NDAs | ✓ VERIFIED | `skill_pipeline/coverage.py:25-35,100-141,209-222` excludes normalized rollover, teaming, and non-sale diligence markers from NDA cues. `skill_pipeline/gates.py:13,209-226,355-357,442-445` reuses the same exclusion helper before `nda_after_drop` and `nda_signer_no_downstream`. Behavioral proof: `python -m pytest -q tests/test_skill_coverage.py tests/test_skill_gates.py -k "rollover or diligence or teaming or nda_after_drop or nda_signer_no_downstream or bidder_target_confidentiality"` → `11 passed, 35 deselected in 0.14s`. |
| 4 | `skill-pipeline db-export` immediately after `db-load` succeeds through bounded lock-specific retry in the shared DuckDB opener; non-lock errors are not retried; exhausted retries still fail hard | ✓ VERIFIED | `skill_pipeline/db_schema.py:10-12,102-127` defines a three-attempt bounded retry with exponential backoff and lock-specific matching on `duckdb.IOException`. `skill_pipeline/db_export.py:73-80` inherits it via `open_pipeline_db(db_path, read_only=True)`, and `skill_pipeline/db_load.py:14-32` uses the same helper for writes. Behavioral proof: `python -m pytest -q tests/test_skill_db_load.py tests/test_skill_db_export.py -k "retry or lock or non_lock"` → `5 passed, 21 deselected in 0.72s`. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `skill_pipeline/extract_artifacts.py` | Shared extract loader and dedicated mixed-schema failure | ✓ VERIFIED | `MixedSchemaError` defined at `:35-36`; mixed-mode guard runs at `:48-53`; canonical branch remains behind that guard at `:55-67`. |
| `skill_pipeline/canonicalize.py` | Quote-first to canonical upgrade with collision-safe renumbering and audit log | ✓ VERIFIED | Quote-ID validation/remap helpers at `:145-215`; renumbering is applied before quote merge at `:475-491`; log includes `quote_id_renumber_log` at `:521-527`. |
| `skill_pipeline/coverage.py` | NDA cue classification with Phase 06 non-sale exclusions | ✓ VERIFIED | `NON_SALE_NDA_MARKERS` at `:25-35`; `_has_non_sale_nda_marker()` at `:100-102`; NDA classification guarded at `:209-222`. |
| `skill_pipeline/gates.py` | Gate-side NDA qualification that suppresses non-sale NDA events | ✓ VERIFIED | Reuses coverage helper at `:13`; `_qualifies_as_sale_process_nda()` at `:209-226`; gate rules consume it at `:355-357` and `:442-445`. |
| `skill_pipeline/db_schema.py` | Shared DuckDB retry policy | ✓ VERIFIED | Retry constants at `:10-11`; retry loop in `open_pipeline_db()` at `:102-123`; lock predicate at `:126-127`. |
| `tests/test_skill_extract_artifacts.py` | Mixed-schema and spans-sidecar regressions | ✓ VERIFIED | 183 lines; directly asserts both mixed-mode failure directions and canonical spans-sidecar failure at `:144-183`. |
| `tests/test_skill_canonicalize.py` | Canonicalize regressions for duplicate handling, remapping, orphan logging, and idempotence | ✓ VERIFIED | 870 lines; duplicate rejection at `:608-640`; cross-array remap/logging at `:643-706`; idempotence at `:822-870`. |
| `tests/test_skill_coverage.py` | Coverage regressions for excluded vs genuine confidentiality cues | ✓ VERIFIED | 807 lines; prior-executed exclusion at `:397-431`; diligence/rollover/teaming exclusions at `:434-575`; bidder-target negative control at `:578-614`. |
| `tests/test_skill_gates.py` | Gate regressions for excluded vs genuine NDA lifecycle behavior | ✓ VERIFIED | 1239 lines; `nda_after_drop` control at `:653-771`; rollover exclusion at `:672-720`; lifecycle exclusion/control at `:919-993`. |
| `tests/test_skill_db_load.py` | Helper-level retry/non-retry boundary coverage | ✓ VERIFIED | 787 lines; eventual retry success at `:526-557`; retry exhaustion at `:559-580`; non-lock fail-fast at `:583-602`. |
| `tests/test_skill_db_export.py` | Export-level lock-handoff integration coverage | ✓ VERIFIED | 429 lines; real transient lock test at `:372-406` proves `run_db_export()` succeeds after a short-lived writer releases the DB. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `skill_pipeline/extract_artifacts.py` | `skill_pipeline/canonicalize.py` | `load_extract_artifacts(paths)` | WIRED | `skill_pipeline/canonicalize.py:475` loads through the shared guard before any canonicalization logic. |
| `skill_pipeline/extract_artifacts.py` | `skill_pipeline/coverage.py` | `load_extract_artifacts(paths)` | WIRED | `skill_pipeline/coverage.py:407` routes coverage through the same loader contract. |
| `skill_pipeline/extract_artifacts.py` | `skill_pipeline/gates.py` | `load_extract_artifacts(paths)` | WIRED | `skill_pipeline/gates.py:576` routes gates through the same loader contract. |
| `skill_pipeline/coverage.py` | `skill_pipeline/gates.py` | `_has_non_sale_nda_marker` + `_normalize_coverage_text` | WIRED | `skill_pipeline/gates.py:13` imports the coverage helper and `_qualifies_as_sale_process_nda()` applies it at `:209-226`. |
| `skill_pipeline/db_schema.py` | `skill_pipeline/db_load.py` | `open_pipeline_db(paths.database_path)` | WIRED | `skill_pipeline/db_load.py:32` uses the shared opener for write transactions. |
| `skill_pipeline/db_schema.py` | `skill_pipeline/db_export.py` | `open_pipeline_db(db_path, read_only=True)` | WIRED | `skill_pipeline/db_export.py:79` uses the shared opener for read-only export, so retry logic is inherited rather than duplicated. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `skill_pipeline/extract_artifacts.py` | `actors_canonical`, `events_canonical` | `actors_raw.json` and `events_raw.json` read from disk in `load_extract_artifacts()` | Yes | ✓ FLOWING |
| `skill_pipeline/canonicalize.py` | `all_quotes`, `quote_to_span`, `quote_id_renumber_log` | Renumbered `raw_actors.quotes` + `raw_events.quotes` from the shared loader | Yes | ✓ FLOWING |
| `skill_pipeline/coverage.py` | `cues`, `findings` | `evidence_items.jsonl`, `chronology_blocks.jsonl`, and loaded extract artifacts | Yes | ✓ FLOWING |
| `skill_pipeline/gates.py` | NDA qualification and gate findings | Loaded extract artifacts plus chronology block text | Yes | ✓ FLOWING |
| `skill_pipeline/db_export.py` | `con`, `event_rows` | Shared `open_pipeline_db()` connection and queried DuckDB tables | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Mixed-schema loader guard | `python -m pytest -q tests/test_skill_extract_artifacts.py -k "mixed_schema or spans"` | `3 passed in 0.13s` | ✓ PASS |
| Canonicalize duplicate/remap/idempotence behavior | `python -m pytest -q tests/test_skill_canonicalize.py -k "duplicate_quote_ids or cross_array or idempotent"` | `3 passed, 13 deselected in 0.13s` | ✓ PASS |
| Coverage + gates NDA tolerance | `python -m pytest -q tests/test_skill_coverage.py tests/test_skill_gates.py -k "rollover or diligence or teaming or nda_after_drop or nda_signer_no_downstream or bidder_target_confidentiality"` | `11 passed, 35 deselected in 0.14s` | ✓ PASS |
| DuckDB lock retry behavior | `python -m pytest -q tests/test_skill_db_load.py tests/test_skill_db_export.py -k "retry or lock or non_lock"` | `5 passed, 21 deselected in 0.72s` | ✓ PASS |
| Phase-wide regression slice | `python -m pytest -q tests/test_skill_extract_artifacts.py tests/test_skill_canonicalize.py tests/test_skill_coverage.py tests/test_skill_gates.py tests/test_skill_db_load.py tests/test_skill_db_export.py` | `91 passed in 1.37s` | ✓ PASS |
| Full repo regression (repo context supplied by user) | `python -m pytest -q` | `288 passed` on 2026-03-29 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `HARD-06` | `06-01` | Shared extract loader rejects mixed actor/event schema modes with a dedicated error before stage-specific processing | ✓ SATISFIED | `skill_pipeline/extract_artifacts.py:39-60`; `tests/test_skill_extract_artifacts.py:144-183`; targeted regression passed. |
| `HARD-01` | `06-01` | Canonicalize deterministically renumbers cross-array quote collisions, rewrites references consistently, remains idempotent, and still fail-fast rejects same-array duplicates | ✓ SATISFIED | `skill_pipeline/canonicalize.py:145-215,475-527`; `tests/test_skill_canonicalize.py:608-706,822-870`; targeted regression passed. |
| `HARD-04` | `06-02` | Coverage and gates tolerate rollover-side and non-sale-process confidentiality agreements without false NDA findings | ✓ SATISFIED | `skill_pipeline/coverage.py:25-35,100-141,209-222`; `skill_pipeline/gates.py:13,209-226,355-357,442-445`; `tests/test_skill_coverage.py:434-614`; `tests/test_skill_gates.py:672-720,919-993`; targeted regression passed. |
| `HARD-05` | `06-03` | db-export retries transient DuckDB lock contention with bounded exponential backoff, without retrying non-lock failures | ✓ SATISFIED | `skill_pipeline/db_schema.py:10-12,102-127`; `skill_pipeline/db_export.py:79`; `tests/test_skill_db_load.py:526-602`; `tests/test_skill_db_export.py:372-406`; targeted regression passed. |

`REQUIREMENTS.md` still shows `HARD-06`, `HARD-01`, and `HARD-04` unchecked at `.planning/REQUIREMENTS.md:15-17`. That is planning-tracker drift, not an implementation gap; verification is based on live code and passing regressions.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| Runtime phase files | - | TODO/FIXME/placeholder scan | ℹ️ Info | No blocker or warning anti-patterns found in `skill_pipeline/extract_artifacts.py`, `canonicalize.py`, `coverage.py`, `gates.py`, or `db_schema.py`. |
| `tests/test_skill_canonicalize.py` | `61, 66, 73` | `placeholder source text` | ℹ️ Info | Fixture-only placeholder text used to synthesize filing blocks in tests; not a runtime stub or hollow implementation. |

### Human Verification Required

None. All Phase 06 success criteria are deterministic CLI/runtime behaviors that were fully verified by code inspection and regression tests.

### Gaps Summary

No functional implementation gaps found. Phase 06 achieved its goal.

The only notable drift is documentation state: `.planning/REQUIREMENTS.md` still lists `HARD-06`, `HARD-01`, and `HARD-04` as unchecked even though the corresponding runtime code and regressions are present and passing.

---

_Verified: 2026-03-29T22:22:49Z_
_Verifier: Codex (gsd-verifier)_
