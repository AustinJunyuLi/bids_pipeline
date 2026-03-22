---
name: deal-agent
description: Use when orchestrating the repo's end-to-end skill workflow for a deal after raw fetch and source preprocessing already ran.
---

# deal-agent

## Design Principles

1. The orchestrator stays thin. It checks gates and reports summaries.
2. It does not re-encode extraction, verification, enrichment, or export logic.
3. Each sub-skill is independently invocable.

## Overview

Thin orchestrator that runs four sub-skills against preprocessed source:
extract-deal, verify-extraction, enrich-deal, export-csv. Deterministic runtime
stages (canonicalize, check, verify, coverage, enrich-core) are available via
`skill-pipeline` CLI.

## Prerequisite

`pipeline raw fetch --deal <slug>` and `pipeline preprocess source --deal <slug>`
already ran.

## When To Use

Invoke as `/deal-agent <slug>` for end-to-end extraction through CSV export. Use
individual skills when re-running a specific stage.

## Benchmark Boundary

Benchmark materials are forbidden during generation. Do not consult benchmark
files, benchmark notes, `example/`, `diagnosis/`,
`data/skill/<slug>/reconcile/*`, or `/reconcile-alex` before `/export-csv`
completes.
Do not open or read the `reconcile-alex` skill file itself in `.claude/`,
`.codex/`, or `.cursor/` before `/export-csv` completes.

Use only filing-grounded inputs through export. Benchmark comparison is
post-export only and read-only.

## Skills

| # | Skill | Artifacts | Failure Mode |
|---|---|---|---|
| 0 | `extract-deal` | `extract/actors_raw.json`, `extract/events_raw.json` | Fail closed |
| 1 | `canonicalize` (deterministic) | `extract/spans.json`, `canonicalize/canonicalize_log.json` | Fail closed |
| 2 | `check` (deterministic) | `check/check_report.json` | Fail closed on blockers |
| 3 | `verify` + `coverage` (deterministic) | `verify/verification_findings.json`, `verify/verification_log.json`, `coverage/coverage_findings.json`, `coverage/coverage_summary.json` | Fail closed on error status |
| 4 | `verify-extraction` | updated extraction files + verify/coverage findings consumed | Fail closed (stop on round-2 errors) |
| 5 | `enrich-core` (deterministic) | `enrich/deterministic_enrichment.json` | Fail closed |
| 6 | `enrich-deal` | `enrich/enrichment.json` | Fail closed |
| 7 | `export-csv` | `export/deal_events.csv` | Fail closed |

## Procedure

```text
1. Read the seed entry for <slug>.

2. Verify prerequisites:
   - data/deals/<slug>/source/chronology_blocks.jsonl
   - data/deals/<slug>/source/evidence_items.jsonl
   - raw/<slug>/document_registry.json
   If missing: stop, tell user to run raw fetch + preprocess first.

3. Ensure output directories exist:
   - data/skill/<slug>/extract/
   - data/skill/<slug>/check/
   - data/skill/<slug>/verify/
   - data/skill/<slug>/coverage/
   - data/skill/<slug>/enrich/
   - data/skill/<slug>/export/

4. Run /extract-deal <slug>
   Gate: actors_raw.json and events_raw.json both exist and are non-empty.
   If gate fails: stop.

4a. Run `skill-pipeline canonicalize --deal <slug>`.
   - Outputs: `data/skill/<slug>/canonicalize/canonicalize_log.json`
     and `data/skill/<slug>/extract/spans.json`
   - Overwrites `actors_raw.json` and `events_raw.json` in place with the
     canonical schema (`evidence_span_ids`, normalized dates)
   - Deduplicates events, removes drops without NDAs, recovers unnamed parties

4b. Run deterministic check: `skill-pipeline check --deal <slug>`
   Gate: check_report.json exists and summary.status == "pass".
   If gate fails: stop.

5. Run deterministic verify: `skill-pipeline verify --deal <slug>`
   Gate: verification_log.json exists AND summary.status != "fail".
   Writes verification_findings.json and verification_log.json.

5a. Run deterministic coverage: `skill-pipeline coverage --deal <slug>`
   Gate: coverage_summary.json exists and summary.status != "fail".
   Writes coverage_findings.json and coverage_summary.json.

6. Run /verify-extraction <slug>
   Gate: verification and coverage artifacts exist. May invoke LLM repair when
   all error-level findings are repairable; otherwise fail closed.

7. Run `skill-pipeline enrich-core --deal <slug>`
   Gate: deterministic_enrichment.json exists.

8. Run /enrich-deal <slug>
   Gate: enrichment.json exists.

9. Run /export-csv <slug>
   Gate: deal_events.csv exists.

10. Report summary:
   - Actor count, event count, proposal count
   - Check: blocker count, warning count (if check_report exists)
   - Coverage: error count, warning count (if coverage_summary exists)
   - Verification: round 1 errors found, fixes applied, round 2 status
   - Enrichment: cycle count, formal/informal split, initiation judgment type
   - Review flags count
   - Output path: data/skill/<slug>/export/deal_events.csv
```

## Individual Invocation

Each skill is independently callable:

- `skill-pipeline canonicalize --deal <slug>` -- upgrade extraction into canonical span-backed artifacts
- `skill-pipeline check --deal <slug>` -- run deterministic structural check
- `skill-pipeline verify --deal <slug>` -- run deterministic verification
- `skill-pipeline coverage --deal <slug>` -- run deterministic source-coverage audit
- `skill-pipeline enrich-core --deal <slug>` -- run deterministic enrich core
- `/extract-deal <slug>` -- run extraction only
- `/verify-extraction <slug>` -- run verification only
- `/enrich-deal <slug>` -- run enrichment only
- `/export-csv <slug>` -- run export only

## Supersedes

This replaces the old 2-skill chain (extract-deal + audit-and-enrich). The old
audit-and-enrich skill is deprecated. Its responsibilities are now split between
verify-extraction (Skill 2) and enrich-deal (Skill 3).
