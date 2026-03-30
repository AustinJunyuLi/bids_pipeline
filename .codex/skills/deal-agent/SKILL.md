---
name: deal-agent
description: Use when orchestrating the repo's end-to-end skill workflow for a deal, from SEC filing fetch through DuckDB export.
---

# deal-agent

## Design Principles

1. The orchestrator stays thin. It checks gates and reports summaries.
2. It does not re-encode extraction, verification, enrichment, or export logic.
3. Each sub-skill is independently invocable.
4. Re-runs are idempotent. Old artifacts are cleaned before fresh writes.

## Overview

End-to-end orchestrator that fetches a SEC filing, preprocesses it into
chronology blocks, runs LLM extraction with composed prompt packets, validates
through deterministic gates, enriches, and exports to DuckDB-backed CSV.
Deterministic runtime stages are available via `skill-pipeline` CLI. Three
stages require LLM calls: extract-deal, verify-extraction, and enrich-deal.

## Prerequisite

Requires `data/seeds.csv` with a row for `<slug>` and a valid SEC identity
environment variable (`PIPELINE_SEC_IDENTITY`, `SEC_IDENTITY`, or
`EDGAR_IDENTITY`).

## When To Use

Invoke as `/deal-agent <slug>` for end-to-end pipeline from filing fetch through
DuckDB export, plus optional interpretive enrichment and post-export
reconciliation. Use individual skills when re-running a specific stage.

Re-running `/deal-agent <slug>` on a previously processed deal cleans all
downstream artifacts and rebuilds from scratch.

## Benchmark Boundary

Benchmark materials are forbidden during generation. Do not consult benchmark
files, benchmark notes, `example/`, `diagnosis/`,
`data/skill/<slug>/reconcile/*`, or `/reconcile-alex` before
`skill-pipeline db-export --deal <slug>` completes.

Use only filing-grounded inputs through export. Benchmark comparison is
post-export only and read-only.

## Skills

| # | Skill | Artifacts | Failure Mode |
|---|---|---|---|
| 0 | `raw-fetch` (deterministic) | `raw/<slug>/document_registry.json`, `raw/<slug>/filings/*.txt` | Fail closed |
| 0a | `preprocess-source` (deterministic) | `source/chronology_blocks.jsonl`, `source/evidence_items.jsonl` | Fail closed |
| 1 | `compose-prompts --mode actors` (deterministic) | `prompt/manifest.json`, actor `prompt/packets/*/rendered.md` | Fail closed |
| 1a | `extract-deal` (LLM) | `extract/actors_raw.json`, `extract/events_raw.json` | Fail closed |
| 1b | `compose-prompts --mode events` (deterministic) | `prompt/manifest.json` updated, event `prompt/packets/*/rendered.md` | Fail closed; requires `actors_raw.json` |
| 2 | `canonicalize` (deterministic) | `extract/spans.json`, `canonicalize/canonicalize_log.json` | Fail closed |
| 2a | `check` (deterministic) | `check/check_report.json` | Fail closed on blockers |
| 3 | `verify` + `coverage` (deterministic) | `verify/*.json`, `coverage/*.json` | Fail closed on error status |
| 3a | `gates` (deterministic) | `gates/gates_report.json` | Fail closed on blocker findings |
| 4 | `verify-extraction` (LLM) | updated extraction files | Fail closed (stop on round-2 errors) |
| 5 | `enrich-core` (deterministic) | `enrich/deterministic_enrichment.json` | Fail closed |
| 6 | `enrich-deal` (LLM, mandatory) | `enrich/enrichment.json` | Fail closed |
| 6a | `db-load` (deterministic) | DuckDB `data/pipeline.duckdb` updated | Fail closed |
| 6b | `db-export` (deterministic) | `export/deal_events.csv` | Fail closed |

## Procedure

```text
0. Clean artifacts for fresh run.
   Delete data/skill/<slug>/ entirely (extract, check, verify, coverage,
   gates, enrich, export, canonicalize, prompt — all downstream artifacts).
   Delete data/deals/<slug>/source/ (preprocess outputs).
   Leave raw/<slug>/ intact — filing text is immutable from EDGAR.
   If raw/<slug>/ does not exist, it will be created by raw-fetch.

1. Read the seed entry for <slug>.
   Gate: seeds.csv contains a row for this slug.

1a. Set SEC identity.
    Run: export EDGAR_IDENTITY="Austin Li junyu.li.24@ucl.ac.uk"
    Gate: EDGAR_IDENTITY is set in the shell environment before raw-fetch.

2. Run `skill-pipeline raw-fetch --deal <slug>`
   Gate: raw/<slug>/document_registry.json exists.
   Note: If raw filings already exist with identical content, raw-fetch
   succeeds silently (immutable-write contract). Discovery and registry
   metadata are always refreshed.

2a. Run `skill-pipeline preprocess-source --deal <slug>`
    Gate: data/deals/<slug>/source/chronology_blocks.jsonl exists.

3. Ensure output directories exist:
   - data/skill/<slug>/extract/
   - data/skill/<slug>/check/
   - data/skill/<slug>/verify/
   - data/skill/<slug>/coverage/
   - data/skill/<slug>/gates/
   - data/skill/<slug>/enrich/
   - data/skill/<slug>/export/
   - data/skill/<slug>/canonicalize/
   - data/skill/<slug>/prompt/

4. Run `skill-pipeline compose-prompts --deal <slug> --mode actors`
   Gate: prompt/manifest.json exists, actor_packet_count > 0.
   Generates actor prompt packets consumed by extract-deal.

4a. Run /extract-deal <slug>
    Gate: actors_raw.json and events_raw.json both exist and are non-empty.
    If gate fails: stop.

4b. Run `skill-pipeline compose-prompts --deal <slug> --mode events`
    Gate: prompt/manifest.json updated, event_packet_count > 0.
    Requires actors_raw.json from step 4a.

5. Run `skill-pipeline canonicalize --deal <slug>`
   - Outputs: canonicalize/canonicalize_log.json and extract/spans.json
   - Overwrites actors_raw.json and events_raw.json in place with the
     canonical schema (evidence_span_ids, normalized dates)
   - Deduplicates events, removes drops without NDAs, recovers unnamed parties

5a. Run deterministic check: `skill-pipeline check --deal <slug>`
    Gate: check_report.json exists and summary.status == "pass".
    If gate fails: stop.

6. Run deterministic verify: `skill-pipeline verify --deal <slug>`
   Gate: verification_log.json exists AND summary.status != "fail".

6a. Run deterministic coverage: `skill-pipeline coverage --deal <slug>`
    Gate: coverage_summary.json exists and summary.status != "fail".

6b. Run deterministic gates: `skill-pipeline gates --deal <slug>`
    Gate: gates_report.json exists and has no blocker-severity findings.
    Required by enrich-core.

7. Run /verify-extraction <slug>
   Gate: verification and coverage artifacts exist. May invoke LLM repair when
   all error-level findings are repairable; otherwise fail closed.

   Note: If verify-extraction made structural changes (added/removed events,
   changed dates, modified actor references), re-run steps 5a through 6b
   (check, verify, coverage, gates) before proceeding to enrich-core.
   Enrich-core uses gate artifacts that may be stale after structural repairs.

8. Run `skill-pipeline enrich-core --deal <slug>`
   Gate: deterministic_enrichment.json exists.

9. Run /enrich-deal <slug>
   Gate: enrichment.json exists and contains 5 required keys
   (dropout_classifications, initiation_judgment, advisory_verification,
   count_reconciliation, review_flags). This is a mandatory step.

9a. Run `skill-pipeline db-load --deal <slug>`
    Gate: data/pipeline.duckdb exists and contains rows for this deal.
    Note: Requires both deterministic_enrichment.json and enrichment.json.
    Loads deterministic enrichment baseline and overlays interpretive
    dropout_classifications from enrichment.json.

9b. Run `skill-pipeline db-export --deal <slug>`
    Gate: deal_events.csv exists and is non-empty.

10. Report summary:
    - Actor count, event count, proposal count
    - Check: blocker count, warning count
    - Coverage: error count, warning count
    - Verification: round 1 errors found, fixes applied, round 2 status
    - Enrichment: cycle count, formal/informal split, initiation judgment type
    - DB load: actor row count, event row count, span row count
    - DB export: event row count, output path
    - Review flags count
    - Output path: data/skill/<slug>/export/deal_events.csv
```

## Individual Invocation

Each skill is independently callable:

- `skill-pipeline raw-fetch --deal <slug>` -- fetch and freeze SEC filing
- `skill-pipeline preprocess-source --deal <slug>` -- build source artifacts from frozen filings
- `skill-pipeline compose-prompts --deal <slug>` -- build prompt packets for extraction
- `skill-pipeline canonicalize --deal <slug>` -- upgrade extraction into canonical span-backed artifacts
- `skill-pipeline check --deal <slug>` -- run deterministic structural check
- `skill-pipeline verify --deal <slug>` -- run deterministic verification
- `skill-pipeline coverage --deal <slug>` -- run deterministic source-coverage audit
- `skill-pipeline gates --deal <slug>` -- run semantic validation gates (temporal, cross-event, lifecycle, attention)
- `skill-pipeline enrich-core --deal <slug>` -- run deterministic enrich core
- `skill-pipeline db-load --deal <slug>` -- load canonical extracts + enrichment into DuckDB
- `skill-pipeline db-export --deal <slug>` -- generate CSV export from DuckDB
- `/extract-deal <slug>` -- run extraction only
- `/verify-extraction <slug>` -- run verification only
- `/enrich-deal <slug>` -- run enrichment only
