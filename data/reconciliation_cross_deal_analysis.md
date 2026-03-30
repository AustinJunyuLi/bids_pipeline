# Cross-Deal Reconciliation Analysis: Pipeline vs. Alex

Generated: 2026-03-30
Deals: imprivata, mac-gray, medivation, penford, petsmart-inc, providence-worcester, saks, stec, zep

Method note: Only Zep and Medivation were refreshed in Phase 9. The other 7 deal reports were intentionally kept frozen, so their metrics are carried forward unchanged from the 2026-03-29 cross-deal baseline.

## Headline Numbers (9 deals)

| Metric | 2026-03-30 refreshed |
|---|---:|
| Pipeline events | 211 |
| Alex rows (total) | 269 |
| Alex atomic rows | 222 |
| Alex aggregate rows | 47 |
| Matched pairs | 157 |
| Pipeline-only (grounded) | 51 |
| Alex-only (atomic) | 63 |
| Arbitrations: pipeline wins | 46 |
| Arbitrations: Alex wins | 13 |
| Both defensible / inconclusive | 24 |

The refreshed corpus shows a modest benchmark improvement after the two reruns. The biggest gain is fewer filing-contradicted pipeline claims; the main tradeoff is more pipeline-only rows because the refreshed outputs are more granular than Alex's spreadsheet, especially in Medivation.

## Per-Deal Scorecard

| Deal | Pipeline | Alex | Matched | Pipe-only | Alex-only | Agg | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| imprivata | 28 | 29 | 23 | 5 | 6 | 0 | attention |
| mac-gray | 27 | 34 | 23 | 4 | 7 | 3 | attention |
| medivation | 35 | 16 | 13 | 20 | 1 | 2 | attention |
| penford | 23 | 25 | 17 | 3 | 8 | 4 | attention |
| petsmart-inc | 14 | 53 | 12 | 2 | 10 | 31 | attention |
| providence-worcester | 18 | 36 | 15 | 3 | 10 | 4 | attention |
| saks | 19 | 25 | 17 | 4 | 8 | 0 | attention |
| stec | 29 | 28 | 23 | 6 | 5 | 0 | attention |
| zep | 18 | 23 | 14 | 4 | 8 | 3 | attention |

These per-deal rows combine atomic matches with a few soft aggregate matches inherited from the underlying per-deal benchmark reports, so they are best read as report-level scorecards rather than strict algebraic partitions.

## Baseline Comparison (v1.1 Phase 9)

| Metric | 2026-03-29 baseline | 2026-03-30 refreshed | Delta |
|---|---:|---:|---:|
| Pipeline events | 207 | 211 | +4 |
| Matched pairs | 156 | 157 | +1 |
| Atomic match rate | 70.3% (156/222) | 70.7% (157/222) | +0.4 pp |
| Pipeline wins | 45 | 46 | +1 |
| Alex wins | 16 | 13 | -3 |
| Both defensible / inconclusive | 24 | 24 | 0 |

Improvement did materialize, but it was modest. The refreshed reruns improve filing-backed correctness more clearly than they improve the raw benchmark count surface.

## What Changed In Phase 9

### Zep

- Baseline: 16 pipeline rows, 14 matched pairs, 1 pipeline-only row, 9 Alex-only rows, 3 aggregate rows.
- Refreshed: 18 pipeline rows, 14 matched pairs, 4 pipeline-only rows, 8 Alex-only rows, 3 aggregate rows.
- The New Mountain Capital contamination in the grouped 2014 proposal surface is gone, which removes a benchmark-facing actor identity problem.
- The refreshed extract still leaves dropout coverage thinner than Alex's benchmark and still exposes a coverage-note integrity concern around missing `evt_009` / `evt_011` materialization.

### Medivation

- Baseline: 33 pipeline rows, 12 matched pairs, 19 pipeline-only rows, 2 Alex-only rows, 2 aggregate rows.
- Refreshed: 35 pipeline rows, 13 matched pairs, 20 pipeline-only rows, 1 Alex-only row, 2 aggregate rows.
- The concrete Phase 9 fix landed: `evt_027` and `evt_029` now exist as actual drop events instead of dangling `coverage_notes` references.
- The benchmark still favors Alex on the July 19-20 informal-round announcement surface, but the repaired drop coverage reduces one of the prior Alex-favored contradictions.

### Frozen Seven Deals

- Imprivata, mac-gray, penford, petsmart-inc, providence-worcester, saks, and stec retain the same reconciliation numbers as the 2026-03-29 baseline.
- No unexpected drift appeared in the frozen deal metrics.

## Interpretation

1. The main Phase 9 win is correctness on the specific rerun targets, not a wholesale benchmark leap. Zep no longer misattributes the 2014 grouped proposal cohort to New Mountain Capital, and Medivation no longer references nonexistent drop events.
2. Pipeline-only rows increased because the refreshed pipeline is more granular than Alex's spreadsheet. That increase is not automatically bad; in Medivation it reflects restored Company 3 / Company 4 drop rows and the already-granular multi-round bidder ladder.
3. The filing-contradicted pipeline claim count fell below the 2026-03-29 baseline of 16, which is the clearest corpus-level improvement signal from this refresh.
4. The remaining benchmark pressure points are still round-milestone surface coverage and a few schema gaps such as exclusivity rows.

## Verdict

Phase 9 improved the 9-deal benchmark modestly: the atomic match rate is now above the 2026-03-29 baseline, and filing-contradicted pipeline claims fell from 16 to 13. The reruns did not reduce pipeline-only volume, but that increase is explainable as extra filing-grounded granularity rather than a new benchmark-blind failure mode.
