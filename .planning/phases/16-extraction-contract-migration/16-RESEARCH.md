# Phase 16: Extraction Contract + Migration - Research

## Main Conclusion

The fastest safe Phase 16 path is additive prompt work plus a deterministic
v1->v2 bridge. The 9-deal corpus already contains filing-grounded, canonical v1
artifacts with stable spans, so translating them into quote-first v2
observations is lower risk than attempting nine fresh manual extractions inside
the same turn.

## Key Findings

- The live prompt stack was still v1-only. A separate v2 contract needed its
  own packet family and output directory.
- Real-deal migration exposed three missing runtime semantics that synthetic
  tests had not covered:
  - literal `bidder_interest` rows were not compiled from `status`
    observations
  - extension solicitations did not classify into `final_round_ext_*`
  - `coverage-v2` failed on unsupported cue severities and multi-match NDA
    blocks
- The legacy adapter remains useful even when real-deal output is not
  byte-identical to v1. The deltas show where the observation graph is carrying
  extra literal structure: cohorts, selected-to-advance states, and recovered
  bidder-interest rows.

## Migration Outcome

- All 9 deals completed:
  `compose-prompts(v2) -> migrate-extract-v1-to-v2 -> canonicalize-v2 -> check-v2 -> coverage-v2 -> gates-v2 -> derive -> db-load-v2 -> db-export-v2`
- 5 of 9 deals now carry explicit cohorts in the canonical v2 graph
- 8 `selected_to_advance` observations and 31 `bidder_interest` analyst rows
  are now preserved across the corpus

## Boundary Reminder

Phase 16 completes the extraction-contract migration itself. Milestone audit,
archive, and cleanup are separate follow-up work.
