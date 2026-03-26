# Codebase Concerns

**Analysis Date:** 2026-03-26

## Tech Debt

**Dual extract surfaces are still live in the same repository:**
- Issue: the active contract writes and reads `data/skill/<slug>/...`, but the repository still carries populated historical `data/deals/<slug>/{extract,qa}/...` trees for `imprivata`, `mac-gray`, `medivation`, `penford`, `petsmart-inc`, `providence-worcester`, `saks`, and `zep`.
- Files: `skill_pipeline/extract_artifacts.py`, `skill_pipeline/check.py`, `skill_pipeline/verify.py`, `skill_pipeline/coverage.py`, `skill_pipeline/enrich_core.py`, `data/deals/imprivata/extract/`, `data/deals/imprivata/qa/`, `data/skill/stec/`
- Impact: every deterministic stage still has to support both legacy and canonical shapes, and contributors can easily inspect the wrong artifact root when deciding whether a deal is complete.
- Fix approach: finish the Phase 02 interface work, add an explicit path-policy regression check, and retire the historical `data/deals/<slug>/{extract,qa}` trees once they are no longer needed for comparison.

**Committed planning memory is internally inconsistent:**
- Issue: `.planning/ROADMAP.md` still shows Phase 1 as unchecked and `0/3` complete in the progress table, while `.planning/phases/01-workflow-contract-surface/01-01-PLAN.md` through `01-03-PLAN.md` exist and `.planning/STATE.md` records 7 completed plans and 2 completed phases.
- Files: `.planning/ROADMAP.md`, `.planning/STATE.md`, `.planning/phases/01-workflow-contract-surface/`
- Impact: GSD commands that trust committed planning artifacts can infer the wrong next step or misread milestone status.
- Fix approach: update `.planning/ROADMAP.md` and `.planning/STATE.md` in the same change whenever phase state changes, and keep the progress table derived from committed phase artifacts rather than manual edits.

## Known Bugs

**Warning-only QA findings are not reaching the exported review surface:**
- Symptoms: `data/skill/stec/coverage/coverage_summary.json` reports 19 warnings, `data/skill/stec/enrich/enrichment.json` has `review_flags: []`, and `data/skill/stec/export/deal_events.csv` leaves the `review_flags` column empty even though `.claude/skills/verify-extraction/SKILL.md` says warning-only findings should surface there.
- Files: `data/skill/stec/coverage/coverage_summary.json`, `data/skill/stec/enrich/enrichment.json`, `data/skill/stec/export/deal_events.csv`, `.claude/skills/verify-extraction/SKILL.md`, `.claude/skills/export-csv/SKILL.md`
- Trigger: a deal passes deterministic verification and coverage with warnings but no blocking errors.
- Workaround: review `check`, `verify`, and `coverage` artifacts directly; do not rely on `review_flags` in `enrichment.json` or the exported CSV as the only review surface.

**NDA-count semantics disagree across stages on `stec`:**
- Symptoms: `data/skill/stec/check/check_report.json` warns `Count assertion 'executed_ndas' expects 6, found 7.`, while `data/skill/stec/enrich/enrichment.json` says the filing count matches 6 extracted NDAs. `data/skill/stec/extract/events_raw.json` currently contains 7 `nda` events, including an NDA addendum (`evt_017`) and a clean-team agreement (`evt_035`).
- Files: `skill_pipeline/check.py`, `data/skill/stec/check/check_report.json`, `data/skill/stec/extract/events_raw.json`, `data/skill/stec/enrich/enrichment.json`
- Trigger: deals where later confidentiality-related agreements are encoded as `nda` events.
- Workaround: inspect the underlying `nda` events manually before trusting `count_assertion_gap` findings on NDA totals.

**Seed metadata contains mojibake for active and nearby deals:**
- Symptoms: `data/seeds.csv` stores strings such as `Dassault SystÃ¨mes S.E.` and `La Caisse de dÃ©pÃ´t et placement du QuÃ©bec`, and `python -m skill_pipeline.cli deal-agent --deal petsmart-inc` surfaces the garbled acquirer string directly in the summary.
- Files: `data/seeds.csv`
- Trigger: any summary or export that reads affected seed rows.
- Workaround: manually correct affected names in downstream review outputs until the seed file is repaired.

**The installed console entrypoint is not self-checked and is currently broken in this checkout:**
- Symptoms: `skill-pipeline --version` and `skill-pipeline deal-agent --deal stec` raise `ModuleNotFoundError: No module named 'skill_pipeline'`, while `python -m skill_pipeline.cli ...` works from the repository root.
- Files: `pyproject.toml`, `skill_pipeline/cli.py`, `docs/HOME_COMPUTER_SETUP.md`
- Trigger: stale or missing editable installation.
- Workaround: run `pip install -e .` before using the documented `skill-pipeline` command, or invoke `python -m skill_pipeline.cli ...` from the repository root.

## Security Considerations

**Benchmark-boundary enforcement is policy-level, not runtime-level:**
- Risk: benchmark and correction material such as `docs/CollectionInstructions_Alex_2026.qmd` can still be consulted before export if an operator or skill author ignores the documented boundary.
- Files: `docs/CollectionInstructions_Alex_2026.qmd`, `CLAUDE.md`, `docs/HOME_COMPUTER_SETUP.md`, `.claude/skills/deal-agent/SKILL.md`, `.claude/skills/extract-deal/SKILL.md`, `.claude/skills/verify-extraction/SKILL.md`, `.claude/skills/enrich-deal/SKILL.md`, `.claude/skills/export-csv/SKILL.md`, `tests/test_benchmark_separation_policy.py`
- Current mitigation: the boundary is documented in repository instructions and guarded by regression tests that check committed docs and skill contracts.
- Recommendations: add a machine-checked pre-export read whitelist or a contract test that fails if benchmark-facing paths appear in any pre-export skill reads.

## Performance Bottlenecks

**Chunked extraction is still serial by contract:**
- Problem: `.claude/skills/extract-deal/SKILL.md` requires chunk-by-chunk actor-roster carry-forward and says sequential processing is mandatory.
- Files: `.claude/skills/extract-deal/SKILL.md`, `.planning/phases/07-parallel-chunked-extraction/07-RESEARCH.md`
- Cause: actor IDs are minted incrementally from earlier chunks, so later chunks depend on earlier roster state.
- Improvement path: implement the researched Phase 7 split already documented in `.planning/phases/07-parallel-chunked-extraction/07-RESEARCH.md`: sequential actor discovery, then parallel event extraction with a fixed roster. The research doc already records `stec` as 235 blocks / 22 chunks and `mac-gray` as roughly 16 chunks on the current path.

**Preprocess and coverage stages rescan full local artifacts in memory:**
- Problem: source preprocessing, chronology selection, evidence scanning, and coverage all load full filing or full JSONL artifacts before evaluating the current deal.
- Files: `skill_pipeline/preprocess/source.py`, `skill_pipeline/source/locate.py`, `skill_pipeline/source/evidence.py`, `skill_pipeline/coverage.py`
- Cause: the pipeline prefers deterministic local-file processing and does not maintain incremental indexes or timing instrumentation.
- Improvement path: add stage timing first, then optimize the slowest whole-file scans rather than guessing at bottlenecks.

## Fragile Areas

**Legacy/canonical mode detection spans the full deterministic middle of the pipeline:**
- Files: `skill_pipeline/extract_artifacts.py`, `skill_pipeline/check.py`, `skill_pipeline/verify.py`, `skill_pipeline/coverage.py`, `skill_pipeline/enrich_core.py`, `skill_pipeline/deal_agent.py`
- Why fragile: runtime mode is inferred from payload shape (`evidence_span_ids` present or not). A partial rewrite or mixed artifact set can push later stages onto the wrong code path or fail late on missing sidecars.
- Safe modification: change models, loaders, and every mode-branching stage together; rerun `tests/test_skill_canonicalize.py`, `tests/test_skill_check.py`, `tests/test_skill_verify.py`, `tests/test_skill_coverage.py`, `tests/test_skill_enrich_core.py`, and `tests/test_skill_pipeline.py`.
- Test coverage: deterministic mode handling is well-covered, but the skill-generated side of the handoff is not executed under pytest.

**Warning propagation across skills is under-specified in code and already inconsistent in data:**
- Files: `.claude/skills/verify-extraction/SKILL.md`, `.claude/skills/enrich-deal/SKILL.md`, `.claude/skills/export-csv/SKILL.md`, `data/skill/stec/coverage/coverage_summary.json`, `data/skill/stec/enrich/enrichment.json`
- Why fragile: the contract says warning-only findings survive into `review_flags`, but the current full `stec` run demonstrates that warnings can disappear between deterministic QA and export.
- Safe modification: treat warning propagation as an explicit artifact contract and add a fixture that begins with warning-only `coverage` or `verify-extraction` output and ends at `deal_events.csv`.
- Test coverage: missing.

**Rule-heavy stage modules concentrate multiple concerns in single files:**
- Files: `skill_pipeline/canonicalize.py`, `skill_pipeline/verify.py`, `skill_pipeline/source/locate.py`, `skill_pipeline/enrich_core.py`
- Why fragile: provenance resolution, date normalization, actor deduplication, quote verification, round pairing, and cycle segmentation all live in large single modules.
- Safe modification: keep changes scoped to one rule family at a time and preserve or extend the stage-local regression file for that module before changing cross-stage behavior.
- Test coverage: good per-stage unit coverage, but cross-stage interactions still depend on manual end-to-end runs.

## Scaling Limits

**Current-contract deal coverage is still 1 full run + 1 partial run + 7 source-only deals:**
- Current capacity: `data/skill/stec/` contains current-contract artifacts through `export/`; `data/skill/petsmart-inc/` contains artifacts through `check/`; `imprivata`, `mac-gray`, `medivation`, `penford`, `providence-worcester`, `saks`, and `zep` currently stop at `raw/` plus `data/deals/<slug>/source/`.
- Limit: repo-wide QA, enrichment, and export work on the active `data/skill/<slug>/...` contract cannot be performed across all nine tracked deals from the checked-in state alone.
- Scaling path: complete current-contract runs for the remaining seven deals and add a parity check that makes the boundary between `data/deals/<slug>/{extract,qa}` and `data/skill/<slug>/...` explicit before historical outputs are removed.

## Dependencies at Risk

**`edgartools` v6 compatibility is an active watchpoint, not a hypothetical one:**
- Risk: the repository allows `edgartools>=5.23` with no upper bound, and the current `pytest -q` run emitted 3 `DeprecationWarning`s from `edgar._markdown`, `edgar.files.markdown`, and `edgar._filings`.
- Files: `pyproject.toml`, `requirements.txt`, `skill_pipeline/raw/fetch.py`, `skill_pipeline/raw/stage.py`
- Impact: ingress stages (`raw-fetch` and related discovery/fetch behavior) can break on a future v6 upgrade and block new deal ingestion.
- Migration plan: pin `<6`, add a compatibility smoke check for live fetch behavior, and migrate away from deprecated `edgar` surfaces before relaxing the cap.

## Missing Critical Features

**No CI pipeline is tracked in the repository:**
- Problem: `.github/workflows/` is not present, so regression checks for deterministic stages, mirror sync, benchmark policy, and packaging smoke depend on local discipline.
- Blocks: automatic detection of broken docs, stale skill mirrors, dependency regressions, and broken console entrypoints before merge.

**No installed end-to-end runner executes the full hybrid workflow from raw fetch through export:**
- Problem: `skill_pipeline/cli.py` exposes deterministic subcommands and a summary-only `deal-agent`, while the actual end-to-end path lives in `.claude/skills/deal-agent/SKILL.md`.
- Blocks: one-command reproducibility, scripted multi-deal reruns, and simple CI smoke tests for the full workflow.

## Test Coverage Gaps

**Skill-stage contracts are not executed under automated tests:**
- What's not tested: `.claude/skills/extract-deal/SKILL.md`, `.claude/skills/verify-extraction/SKILL.md`, `.claude/skills/enrich-deal/SKILL.md`, `.claude/skills/export-csv/SKILL.md`
- Files: `.claude/skills/extract-deal/SKILL.md`, `.claude/skills/verify-extraction/SKILL.md`, `.claude/skills/enrich-deal/SKILL.md`, `.claude/skills/export-csv/SKILL.md`, `tests/test_skill_pipeline.py`, `tests/test_workflow_contract_surface.py`, `tests/test_skill_mirror_sync.py`
- Risk: contract drift between skill instructions and deterministic stages is only discovered during manual deal runs.
- Priority: High

**Warning propagation into `review_flags` is not covered by a regression fixture:**
- What's not tested: warning-only `coverage` or `verify-extraction` outputs making it into `enrichment.json` and then into `export/deal_events.csv`
- Files: `.claude/skills/verify-extraction/SKILL.md`, `.claude/skills/enrich-deal/SKILL.md`, `.claude/skills/export-csv/SKILL.md`, `data/skill/stec/coverage/coverage_summary.json`, `data/skill/stec/enrich/enrichment.json`, `data/skill/stec/export/deal_events.csv`
- Risk: important human-review signals disappear without failing the pipeline.
- Priority: High

**NDA counting around addenda and clean-team agreements is not regression-tested end-to-end:**
- What's not tested: whether `skill_pipeline/check.py` and later enrichment agree on how count assertions such as `executed_ndas` should treat NDA addenda and clean-team agreements.
- Files: `skill_pipeline/check.py`, `tests/test_skill_check.py`, `data/skill/stec/extract/events_raw.json`, `data/skill/stec/enrich/enrichment.json`
- Risk: false-positive or false-negative `count_assertion_gap` warnings on live deals.
- Priority: High

**Installed console-script packaging is not smoke-tested:**
- What's not tested: the console entrypoint declared in `pyproject.toml` actually imports and runs from a contributor checkout.
- Files: `pyproject.toml`, `skill_pipeline/cli.py`
- Risk: documented `skill-pipeline` commands can fail until a contributor repairs the local install.
- Priority: Medium

---

*Concerns audit: 2026-03-26*
