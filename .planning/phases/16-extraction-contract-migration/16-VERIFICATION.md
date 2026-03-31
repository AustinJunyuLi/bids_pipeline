# Phase 16: Extraction Contract + Migration Verification Report

## Runtime Verification

### Regression Suite

Passed:

`pytest -q tests/test_skill_db_load.py tests/test_skill_db_export.py tests/test_skill_observation_models.py tests/test_skill_extract_artifacts_v2.py tests/test_skill_canonicalize_v2.py tests/test_skill_check_v2.py tests/test_skill_coverage_v2.py tests/test_skill_gates_v2.py tests/test_skill_derive.py tests/test_skill_db_load_v2.py tests/test_skill_db_export_v2.py tests/test_skill_pipeline.py tests/test_skill_prompt_models.py tests/test_skill_compose_prompts.py tests/test_skill_phase16_migration.py`

Result: `186 passed`

### Real-Deal Rerun

Each deal completed:

`compose-prompts --contract v2 --mode observations`
`-> migrate-extract-v1-to-v2`
`-> canonicalize-v2`
`-> check-v2`
`-> coverage-v2`
`-> gates-v2`
`-> derive`
`-> db-load-v2`
`-> db-export-v2`

Result: all 9 deals completed without blockers.

## Benchmark Comparison

The legacy-adapter output is not byte-identical to the v1 CSV on real deals.
That is expected after Phase 16, because the v2 graph now preserves literal
structure that the flat v1 contract either flattened or omitted:

- literal `bidder_interest` rows are preserved from `status` observations
- explicit `selected_to_advance` states survive round migration
- unnamed bidder groups are represented as cohorts instead of collapsed text
- exact-day `date_public` is preserved where the v1 export left it `NA`
- advisor-retention rows now prefer the advisor subject rather than
  board-plus-advisor concatenation

### Corpus-Level Graph Wins

- 9 deals migrated end-to-end
- 5 deals now carry explicit cohorts
- 8 total cohorts across the corpus
- 8 `selected_to_advance` observations across the corpus
- 31 `bidder_interest` analyst rows compiled from literal status observations
- 6 `synthetic_anonymous` analyst rows remain export-only / benchmark-only

### Per-Deal Summary

| Deal | v1 rows | v2 legacy rows | Delta | Parties | Cohorts | Observations | Selected-to-Advance | Bidder-Interest Rows | Synthetic Anonymous |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| imprivata | 28 | 29 | +1 | 17 | 0 | 29 | 1 | 3 | 0 |
| mac-gray | 26 | 34 | +8 | 13 | 0 | 27 | 1 | 1 | 0 |
| medivation | 39 | 46 | +7 | 13 | 0 | 40 | 2 | 6 | 0 |
| penford | 24 | 26 | +2 | 14 | 1 | 25 | 0 | 6 | 0 |
| petsmart-inc | 20 | 22 | +2 | 9 | 2 | 20 | 1 | 1 | 4 |
| providence-worcester | 23 | 29 | +6 | 12 | 0 | 23 | 0 | 2 | 0 |
| saks | 22 | 30 | +8 | 11 | 2 | 23 | 1 | 5 | 0 |
| stec | 33 | 36 | +3 | 20 | 1 | 34 | 2 | 4 | 0 |
| zep | 18 | 19 | +1 | 6 | 2 | 19 | 0 | 3 | 2 |

## STEC Reference Deal

STEC completed the full Phase 16 flow first and validated the runtime-hardening
changes:

- literal bidder-interest rows survive derivation
- round extensions compile to `final_round_ext_ann` / `final_round_ext`
- NDA-heavy coverage blocks no longer fail on multi-match literal observations
- the v2 export surface and legacy adapter both complete successfully

## Conclusion

Phase 16 is complete. The repository now has:

- a live v2 prompt-composition contract
- canonical v2 extraction / verification skill docs
- a deterministic corpus migration path into `extract_v2/`
- validated v2 outputs for all 9 benchmark deals
