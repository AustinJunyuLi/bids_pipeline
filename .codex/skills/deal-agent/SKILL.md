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
stages (check, verify, enrich-core) are available via `skill-pipeline` CLI.

## Prerequisite

`pipeline raw fetch --deal <slug>` and `pipeline preprocess source --deal <slug>`
already ran.

## When To Use

Invoke as `/deal-agent <slug>` for end-to-end extraction through CSV export. Use
individual skills when re-running a specific stage.

## Skills

| # | Skill | Artifacts | Failure Mode |
|---|---|---|---|
| 0 | `check` (deterministic) | `check/check_report.json` | Fail closed on blockers |
| 1 | `extract-deal` | `extract/actors_raw.json`, `extract/events_raw.json` | Fail closed |
| 2 | `verify-extraction` | `verify/verification_findings.json`, `verify/verification_log.json` (+ updated extraction files) | Fail closed (stop on round-2 errors) |
| 3 | `enrich-deal` | `enrich/deterministic_enrichment.json`, `enrich/enrichment.json` | Fail closed |
| 4 | `export-csv` | `export/deal_events.csv` | Fail closed |

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
   - data/skill/<slug>/enrich/
   - data/skill/<slug>/export/

4. Run /extract-deal <slug>
   Gate: actors_raw.json and events_raw.json both exist and are non-empty.
   If gate fails: stop.

4a. Run `skill-pipeline canonicalize --deal <slug>`.
   - Output: `data/skill/<slug>/canonicalize/canonicalize_log.json`
   - Overwrites `actors_raw.json` and `events_raw.json` in place
   - Deduplicates events, removes drops without NDAs, recovers unnamed parties

4b. Run deterministic check: `skill-pipeline check --deal <slug>`
   Gate: check_report.json exists and summary.status == "pass".
   If gate fails: stop.

5. Run deterministic verify: `skill-pipeline verify --deal <slug>`
   Gate: verification_log.json exists AND summary.status != "fail".
   Writes verification_findings.json and verification_log.json.

6. Run /verify-extraction <slug>
   Gate: same as step 5. May invoke LLM repair when all error-level
   findings are repairable; otherwise fail closed.

7. Run /enrich-deal <slug>
   Gate: enrichment.json exists. Deterministic core (rounds, bid
   classification, cycles, formal_boundary) is in
   deterministic_enrichment.json from `skill-pipeline enrich-core --deal <slug>`.

8. Run /export-csv <slug>
   Gate: deal_events.csv exists.

9. Report summary:
   - Actor count, event count, proposal count
   - Check: blocker count, warning count (if check_report exists)
   - Verification: round 1 errors found, fixes applied, round 2 status
   - Enrichment: cycle count, formal/informal split, initiation judgment type
   - Review flags count
   - Output path: data/skill/<slug>/export/deal_events.csv
```

## Individual Invocation

Each skill is independently callable:

- `skill-pipeline check --deal <slug>` -- run deterministic structural check
- `skill-pipeline verify --deal <slug>` -- run deterministic verification
- `skill-pipeline enrich-core --deal <slug>` -- run deterministic enrich core
- `/extract-deal <slug>` -- run extraction only
- `/verify-extraction <slug>` -- run verification only
- `/enrich-deal <slug>` -- run enrichment only
- `/export-csv <slug>` -- run export only

## Supersedes

This replaces the old 2-skill chain (extract-deal + audit-and-enrich). The old
audit-and-enrich skill is deprecated. Its responsibilities are now split between
verify-extraction (Skill 2) and enrich-deal (Skill 3).
