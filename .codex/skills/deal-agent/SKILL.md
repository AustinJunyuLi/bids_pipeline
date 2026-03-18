# deal-agent

## Design Principles

1. The orchestrator stays thin. It checks gates and reports summaries.
2. It does not re-encode extraction, verification, enrichment, or export logic.
3. Each sub-skill is independently invocable.

## Overview

Thin orchestrator that runs exactly four sub-skills against preprocessed source:
extract-deal, verify-extraction, enrich-deal, export-csv.

## Prerequisite

`pipeline raw fetch --deal <slug>` and `pipeline preprocess source --deal <slug>`
already ran.

## When To Use

Invoke as `/deal-agent <slug>` for end-to-end extraction through CSV export. Use
individual skills when re-running a specific stage.

## Skills

| # | Skill | Artifacts | Failure Mode |
|---|---|---|---|
| 1 | `extract-deal` | `extract/actors_raw.json`, `extract/events_raw.json` | Fail closed |
| 2 | `verify-extraction` | `verify/verification_log.json` (+ updated extraction files) | Fail closed (stop on round-2 errors) |
| 3 | `enrich-deal` | `enrich/enrichment.json` | Fail closed |
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
   - data/skill/<slug>/verify/
   - data/skill/<slug>/enrich/
   - data/skill/<slug>/export/

4. Run /extract-deal <slug>
   Gate: actors_raw.json and events_raw.json both exist and are non-empty.
   If gate fails: stop.

5. Run /verify-extraction <slug>
   Gate: verification_log.json exists AND summary.status != "fail"
   (i.e., no unresolved round-2 errors).
   If fail: stop and show log.

6. Run /enrich-deal <slug>
   Gate: enrichment.json exists.

7. Run /export-csv <slug>
   Gate: deal_events.csv exists.

8. Report summary:
   - Actor count, event count, proposal count
   - Verification: round 1 errors found, fixes applied, round 2 status
   - Enrichment: cycle count, formal/informal split, initiation judgment type
   - Review flags count
   - Output path: data/skill/<slug>/export/deal_events.csv
```

## Individual Invocation

Each skill is independently callable:

- `/extract-deal <slug>` -- run extraction only
- `/verify-extraction <slug>` -- run verification only
- `/enrich-deal <slug>` -- run enrichment only
- `/export-csv <slug>` -- run export only

## Supersedes

This replaces the old 2-skill chain (extract-deal + audit-and-enrich). The old
audit-and-enrich skill is deprecated. Its responsibilities are now split between
verify-extraction (Skill 2) and enrich-deal (Skill 3).
