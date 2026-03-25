# Workflow Contract

This document is the single canonical inventory of every active pipeline stage
from raw fetch through export, with stage classification, artifact contracts,
and gate boundaries.

**Last updated:** 2026-03-25

## Stage Order

The live pipeline follows this end-to-end sequence:

```text
1.  skill-pipeline raw-fetch --deal <slug>
2.  skill-pipeline preprocess-source --deal <slug>
3.  /extract-deal <slug>
4.  skill-pipeline canonicalize --deal <slug>
5.  skill-pipeline check --deal <slug>
6.  skill-pipeline verify --deal <slug>
7.  skill-pipeline coverage --deal <slug>
8.  /verify-extraction <slug>
9.  skill-pipeline enrich-core --deal <slug>
10. /enrich-deal <slug>
11. /export-csv <slug>
```

`/reconcile-alex <slug>` is optional and post-export only. It must not run
before `/export-csv` completes and must not modify generation artifacts.

## Deterministic vs LLM Mix

The pipeline is a deterministic/skill sandwich. Deterministic CLI stages own
artifact validity and fail-fast gating. LLM skill stages own extraction,
repair, interpretation, and export formatting.

**Count:** 7 deterministic stages, 4 LLM skill stages.

| Category | Count | Stages |
|----------|-------|--------|
| Deterministic CLI | 7 | `raw-fetch`, `preprocess-source`, `canonicalize`, `check`, `verify`, `coverage`, `enrich-core` |
| LLM skill | 3 | `/extract-deal`, `/enrich-deal`, `/export-csv` |
| Hybrid repair (LLM with deterministic pre-steps) | 1 | `/verify-extraction` |
| Post-export diagnostic (LLM, optional) | 1 | `/reconcile-alex` |

## Stage Table

| # | Stage | Entrypoint | Type | Required Inputs | Produced Artifacts | Fail-Fast Gate |
|---|-------|------------|------|-----------------|-------------------|----------------|
| 1 | raw-fetch | `skill-pipeline raw-fetch --deal <slug>` | Deterministic | `data/seeds.csv` entry for slug | `raw/<slug>/filings/*.txt`, `raw/<slug>/discovery.json`, `raw/<slug>/document_registry.json` | Fails if seed entry missing or filing unreachable |
| 2 | preprocess-source | `skill-pipeline preprocess-source --deal <slug>` | Deterministic | `raw/<slug>/filings/*.txt`, `raw/<slug>/document_registry.json` | `data/deals/<slug>/source/chronology_blocks.jsonl`, `data/deals/<slug>/source/evidence_items.jsonl`, `data/deals/<slug>/source/chronology_selection.json` | Fails on missing raw artifacts; invalidates partial outputs on error |
| 3 | extract-deal | `/extract-deal <slug>` | LLM skill | `data/deals/<slug>/source/chronology_blocks.jsonl`, `data/deals/<slug>/source/evidence_items.jsonl`, `raw/<slug>/document_registry.json` | `data/skill/<slug>/extract/actors_raw.json`, `data/skill/<slug>/extract/events_raw.json` | Fails closed on source ambiguity |
| 4 | canonicalize | `skill-pipeline canonicalize --deal <slug>` | Deterministic | `data/skill/<slug>/extract/actors_raw.json`, `data/skill/<slug>/extract/events_raw.json`, source artifacts | `data/skill/<slug>/extract/spans.json` (sidecar), `data/skill/<slug>/canonicalize/canonicalize_log.json`; overwrites actors/events in place to canonical schema | Fails if extract artifacts missing or malformed |
| 5 | check | `skill-pipeline check --deal <slug>` | Deterministic | Canonical `actors_raw.json`, `events_raw.json`, `spans.json` | `data/skill/<slug>/check/check_report.json` | Fails closed on structural blockers |
| 6 | verify | `skill-pipeline verify --deal <slug>` | Deterministic | Canonical extract artifacts, source artifacts, `spans.json` | `data/skill/<slug>/verify/verification_findings.json`, `data/skill/<slug>/verify/verification_log.json` | Fails on non-resolved references; EXACT and NORMALIZED pass, FUZZY does not |
| 7 | coverage | `skill-pipeline coverage --deal <slug>` | Deterministic | Canonical extract artifacts, source evidence items | `data/skill/<slug>/coverage/coverage_findings.json`, `data/skill/<slug>/coverage/coverage_summary.json` | Fails on uncovered high-confidence critical evidence |
| 8 | verify-extraction | `/verify-extraction <slug>` | Hybrid repair | Deterministic verify + coverage artifacts, canonical extract artifacts | Updated extraction files if repairs succeed | Runs LLM repair only when all error-level findings are repairable; fails closed on non-repairable errors or round-2 failures |
| 9 | enrich-core | `skill-pipeline enrich-core --deal <slug>` | Deterministic | Canonical extract artifacts, passing `check`, `verify`, and `coverage` artifacts | `data/skill/<slug>/enrich/deterministic_enrichment.json` | Refuses to write success artifact unless check, verify, and coverage all pass |
| 10 | enrich-deal | `/enrich-deal <slug>` | LLM skill | Canonical extract artifacts, `deterministic_enrichment.json` | `data/skill/<slug>/enrich/enrichment.json` | Fails closed; deterministic core must have run first |
| 11 | export-csv | `/export-csv <slug>` | LLM skill (formatting only) | Extract artifacts, enrichment artifacts | `data/skill/<slug>/export/deal_events.csv` | Fails closed on missing inputs |
| -- | reconcile-alex | `/reconcile-alex <slug>` | LLM skill (optional, post-export only) | `data/skill/<slug>/export/deal_events.csv`, benchmark spreadsheet | `data/skill/<slug>/reconcile/` outputs | Post-export only; must not modify generation artifacts |

## deal-agent: Two Surfaces, Two Jobs

The name "deal-agent" refers to two distinct entrypoints with different
responsibilities.

### `skill-pipeline deal-agent --deal <slug>` (CLI summary)

- **Type:** Deterministic preflight / summary only
- **Entrypoint:** `skill_pipeline/deal_agent.py` via `skill-pipeline` CLI
- **What it does:** Checks prerequisites, ensures output directories exist,
  summarizes the current state of all stage artifacts for the deal
- **What it does NOT do:** Run extraction, repair, enrichment, or export
- **When to use:** Before starting a workflow run to verify readiness, or after
  completion to inspect artifact status

### `/deal-agent <slug>` (skill orchestrator)

- **Type:** LLM skill orchestrator
- **Entrypoint:** `.claude/skills/deal-agent/SKILL.md`
- **What it does:** Runs the full end-to-end skill workflow:
  `/extract-deal` -> deterministic gates -> `/verify-extraction` ->
  deterministic enrichment -> `/enrich-deal` -> `/export-csv`
- **When to use:** For end-to-end deal processing after `raw-fetch` and
  `preprocess-source` have completed

These are not interchangeable. The CLI command summarizes; the skill command
orchestrates.

## Artifact Roots

| Root | Contents | Mutability |
|------|----------|------------|
| `raw/<slug>/` | Frozen filing text, discovery metadata, document registry | Immutable after raw-fetch |
| `data/deals/<slug>/source/` | Chronology blocks, evidence items, chronology selection | Written by preprocess-source |
| `data/skill/<slug>/extract/` | Raw or canonical actors/events, `spans.json` sidecar | Written by extract-deal, overwritten in place by canonicalize |
| `data/skill/<slug>/canonicalize/` | Canonicalize log | Written by canonicalize |
| `data/skill/<slug>/check/` | Check report | Written by check |
| `data/skill/<slug>/verify/` | Verification findings and log | Written by verify |
| `data/skill/<slug>/coverage/` | Coverage findings and summary | Written by coverage |
| `data/skill/<slug>/enrich/` | Deterministic enrichment and interpretive enrichment | Written by enrich-core and enrich-deal |
| `data/skill/<slug>/export/` | Review CSV | Written by export-csv |
| `data/skill/<slug>/reconcile/` | Benchmark comparison outputs | Written by reconcile-alex (post-export only) |

## Gate Boundaries

Three deterministic gates must pass before enrichment can proceed:

1. **check** -- structural blocker gate (`check_report.json` status == "pass")
2. **verify** -- referential integrity gate (`verification_log.json` status != "fail")
3. **coverage** -- source-cue audit gate (`coverage_summary.json` status != "fail")

`enrich-core` reads all three gate artifacts and refuses to write
`deterministic_enrichment.json` unless all three pass.

## Benchmark Boundary

Benchmark materials (`example/`, `diagnosis/`, benchmark workbooks,
`/reconcile-alex`) are forbidden before `/export-csv` completes. Generation
stages must use only filing-grounded inputs. `/reconcile-alex` is post-export
only and never rewrites generation artifacts.

## Source Constraints

- `raw-fetch` and `preprocess-source` are seed-only and single-primary-document
- Canonical extract artifacts require a valid `spans.json` sidecar
- Filing `.txt` files under `raw/` are immutable truth sources
- Filing text is the only factual source for generation
