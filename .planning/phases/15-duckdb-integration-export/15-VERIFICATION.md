---
phase: 15-duckdb-integration-export
verified: 2026-03-31T11:33:16Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 15: DuckDB Integration + Export Verification Report

**Phase Goal:** v2 observations and derived records load into DuckDB via
additive schema and export through a triple CSV surface plus a legacy adapter
that maps v2 analyst rows back to the v1 CSV shape for benchmark regression.

**Verified:** 2026-03-31T11:33:16Z  
**Status:** passed  
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `db-load-v2` writes canonical observations, derivations, and structured coverage into additive `v2_*` tables | VERIFIED | `skill_pipeline/db_schema.py` now defines `v2_parties`, `v2_cohorts`, `v2_observations`, `v2_derivations`, and `v2_coverage_checks`, and `skill_pipeline/db_load_v2.py` loads those tables with a delete-and-reload transaction per deal. |
| 2 | `db-export-v2` writes the triple export surface from DuckDB | VERIFIED | `skill_pipeline/db_export_v2.py` queries the additive DuckDB tables and writes `literal_observations.csv`, `analyst_rows.csv`, and `benchmark_rows_expanded.csv` under `data/skill/<slug>/export_v2/`. |
| 3 | Anonymous slot expansion remains export-only | VERIFIED | `db_export_v2.py` expands `synthetic_anonymous` rows only when writing `benchmark_rows_expanded.csv`; `analyst_rows.csv` preserves the original graph-linked `subject_ref` plus `row_count`. |
| 4 | The legacy adapter reproduces the existing v1 CSV formatting contract without replacing `db-export` | VERIFIED | `skill_pipeline/legacy_adapter.py` routes v2 analyst rows back through the v1 `_build_event_rows()` formatter, and `tests/test_skill_db_export_v2.py` compares the serialized adapter output byte-for-byte against a synthetic v1 `deal_events.csv`. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skill_pipeline/db_schema.py` | Additive v2 DuckDB tables | VERIFIED | Keeps v1 schema intact and adds the required `v2_*` tables. |
| `skill_pipeline/db_load_v2.py` | Live v2 DuckDB loader | VERIFIED | Loads observations, derivations, and coverage checks into DuckDB atomically. |
| `skill_pipeline/db_export_v2.py` | Triple v2 export runtime | VERIFIED | Writes all three export_v2 CSV surfaces. |
| `skill_pipeline/legacy_adapter.py` | Byte-stable v1 CSV mapper | VERIFIED | Reuses v1 export formatting helpers for compatibility. |
| `skill_pipeline/cli.py` | Live CLI for `db-load-v2` and `db-export-v2` | VERIFIED | Exposes both subcommands. |
| `tests/test_skill_db_load_v2.py` | Loader regression coverage | VERIFIED | Covers load success, reload replacement, and CLI execution. |
| `tests/test_skill_db_export_v2.py` | Export and legacy-adapter regression coverage | VERIFIED | Covers triple export, benchmark expansion, byte-stable legacy CSV rendering, and CLI execution. |
| `tests/test_skill_db_load.py` | Updated additive schema smoke test | VERIFIED | Confirms the shared DuckDB schema now includes the additive v2 tables. |
| `CLAUDE.md` | Repo memory update for live v2 DB/export writers | VERIFIED | Documents `db-load-v2` and `db-export-v2` as live runtime stages and output writers. |

### Behavioral Spot-Checks

| Behavior | Command / Check | Result | Status |
|----------|-----------------|--------|--------|
| Focused Phase 15 slice | `pytest -q tests/test_skill_db_load_v2.py tests/test_skill_db_export_v2.py tests/test_skill_pipeline.py -k 'db_load_v2 or db_export_v2 or legacy_adapter or db-load-v2 or db-export-v2'` | `9 passed, 27 deselected` | PASS |
| Broad v1/v2 regression bundle | `pytest -q tests/test_skill_db_load.py tests/test_skill_db_export.py tests/test_skill_observation_models.py tests/test_skill_extract_artifacts_v2.py tests/test_skill_canonicalize_v2.py tests/test_skill_check_v2.py tests/test_skill_coverage_v2.py tests/test_skill_gates_v2.py tests/test_skill_derive.py tests/test_skill_db_load_v2.py tests/test_skill_db_export_v2.py tests/test_skill_pipeline.py` | `117 passed` | PASS |
| Syntax sanity | `python -m py_compile skill_pipeline/db_schema.py skill_pipeline/db_load.py skill_pipeline/db_export.py skill_pipeline/derive.py skill_pipeline/db_load_v2.py skill_pipeline/db_export_v2.py skill_pipeline/legacy_adapter.py tests/_v2_validation_fixtures.py tests/test_skill_db_load.py tests/test_skill_db_export.py tests/test_skill_derive.py tests/test_skill_db_load_v2.py tests/test_skill_db_export_v2.py tests/test_skill_pipeline.py` | `success` | PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| EXPORT-01 | Additive `v2_*` DuckDB tables | SATISFIED | `db_schema.py` and `db_load_v2.py` create and populate the required tables. |
| EXPORT-02 | Triple export surface with benchmark-only anonymous expansion | SATISFIED | `db_export_v2.py` writes the three CSVs and expands anonymous rows only in the benchmark surface. |
| EXPORT-03 | Legacy adapter mapping to v1 CSV shape | SATISFIED | `legacy_adapter.py` plus the byte-stable regression test prove the v1 CSV contract can be reproduced from v2 analyst rows. |

### Human Verification Required

None for Phase 15 synthetic validation. Real benchmark comparison on migrated
deals remains Phase 16 work.

### Gaps Summary

No phase-blocking gaps remain.

Residual note: Phase 16 still needs to exercise the new v2 DuckDB/export
surface on STEC and the remaining 8 migrated deals before the milestone is
complete.

---

_Verified: 2026-03-31T11:33:16Z_  
_Verifier: Codex_
