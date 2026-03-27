---
phase: 01-foundation-annotation
plan: 03
subsystem: validation
status: complete
tags: [validation, source-artifacts, stec, prod-fixes]

requires:
  - phase: 01
    provides: annotated ChronologyBlock schema and preprocess integration
  - phase: 02
    provides: runtime-contract hardening
provides:
  - local validator for annotated chronology block artifacts
  - regenerated annotated `stec` source artifacts
  - rerun deterministic `stec` downstream chain after prod logic fixes
  - validated annotated source artifacts for all 9 active deals after corpus restoration
affects: [01-foundation-annotation, canonicalize, check, verify, enrich-core, validation]

key-files:
  created:
    - scripts/validate_annotated_blocks.py
  modified:
    - data/deals/stec/source/chronology_blocks.jsonl
    - data/deals/stec/source/evidence_items.jsonl
    - data/deals/stec/source/chronology_selection.json
    - data/deals/stec/source/chronology.json
    - data/skill/stec/canonicalize/canonicalize_log.json
    - data/skill/stec/check/check_report.json
    - data/skill/stec/verify/verification_findings.json
    - data/skill/stec/verify/verification_log.json
    - data/skill/stec/coverage/coverage_findings.json
    - data/skill/stec/coverage/coverage_summary.json
    - data/skill/stec/enrich/deterministic_enrichment.json

completed: 2026-03-27
---

# Phase 01 Plan 03: Local Validation Summary

## Outcome

Plan 03 is complete:

- added `scripts/validate_annotated_blocks.py`
- regenerated annotated source artifacts for `stec`
- reran the deterministic downstream chain for `stec`
- confirmed the full repository test suite still passes after the prod logic fixes
- validated annotated source artifacts for all 9 active deals in the active corpus:
  `imprivata`, `mac-gray`, `medivation`, `penford`, `petsmart-inc`,
  `providence-worcester`, `saks`, `stec`, `zep`

## Commands Run

- `python -m skill_pipeline.cli preprocess-source --deal stec --project-root /home/austinli/Projects/bids_pipeline`
- `python scripts/validate_annotated_blocks.py --deals stec --spot-check stec`
- `python scripts/validate_annotated_blocks.py --spot-check stec`
- `python -m skill_pipeline.cli canonicalize --deal stec --project-root /home/austinli/Projects/bids_pipeline`
- `python -m skill_pipeline.cli check --deal stec --project-root /home/austinli/Projects/bids_pipeline`
- `python -m skill_pipeline.cli verify --deal stec --project-root /home/austinli/Projects/bids_pipeline`
- `python -m skill_pipeline.cli coverage --deal stec --project-root /home/austinli/Projects/bids_pipeline`
- `python -m skill_pipeline.cli enrich-core --deal stec --project-root /home/austinli/Projects/bids_pipeline`
- `python scripts/validate_annotated_blocks.py --deals imprivata mac-gray medivation penford petsmart-inc providence-worcester saks stec zep`
- `python -m pytest -q`

## Results

- `scripts/validate_annotated_blocks.py` passes on the default locally discovered corpus and on explicit `--deals stec --spot-check stec`
- `scripts/validate_annotated_blocks.py --deals imprivata mac-gray medivation penford petsmart-inc providence-worcester saks stec zep` passes
- `preprocess-source` regenerated `stec` with `235` chronology blocks and `997` evidence items
- the full deterministic `stec` chain completed successfully after the code fixes
- `python -m pytest -q` passed with `121 passed, 3 warnings`

## Spot Check Notes

- Early block `B002` (`ordinal=2`) is plausibly labeled `bidding`, carries `evidence_density=2`, and includes a `party_alias` entity mention for `the company` in the strategic-alternatives narrative.
- Middle block `B079` (`ordinal=79`) is plausibly labeled `bidding`, carries `evidence_density=2`, and captures both `June 10, 2013` and a `the board` entity mention in the late negotiation sequence.
- Late block `B158` (`ordinal=158`) is plausibly labeled `bidding`, carries `evidence_density=2`, and captures `June 23, 2013` in the board/fairness-opinion discussion near signing.

## Additional Notes

- While executing the local rerun, `canonicalize` was found to be non-idempotent on already canonical extract artifacts. That was fixed so reruns now succeed against the current on-disk state.
- The prod logic fixes for fail-closed evidence grounding, order-aware drop gating, cycle-local round logic, and invitee attachment were bundled into this execution pass and covered by new regressions before the `stec` rerun.

## Corpus Note

- Medivation originally failed because the seed pointed at the wrong SEC accession. The working seed now targets `0001193125-16-696911`, and source validation passes on the restored 9-deal corpus.
- Seed-quality hardening remains open as a scoped follow-up in `.planning/todos/pending/2026-03-27-investigate-seed-quality-guard-for-medivation-style-bad-accession.md`.
