# Phase 1 Research: Workflow Contract Surface

**Researched:** 2026-03-25
**Method:** 4 parallel codebase exploration agents (deterministic stages, LLM skills, artifact flow, tests/guards)

## Pipeline Architecture: Deterministic vs. LLM Mix

### End-to-End Flow

```
DETERMINISTIC: raw-fetch → preprocess-source
     ↓
LLM: /extract-deal (Claude structured output)
     ↓
DETERMINISTIC: canonicalize → check → verify → coverage
     ↓
LLM: /verify-extraction (2-round repair, only if repairable errors)
     ↓
DETERMINISTIC: enrich-core
     ↓
LLM: /enrich-deal (8-section interpretive enrichment)
     ↓
FORMATTING: /export-csv (no LLM — pure formatting rules)
     ↓
LLM (optional, post-export): /reconcile-alex (benchmark QA)
```

### Stage Classification

| # | Stage | Entry Point | Type | External Calls | Fail-Fast |
|---|-------|-------------|------|----------------|-----------|
| 1 | raw-fetch | `skill-pipeline raw-fetch` | Deterministic | HTTP (SEC EDGAR) | Missing credential, invalid URL, empty filing |
| 2 | preprocess-source | `skill-pipeline preprocess-source` | Deterministic | None | No chronology found, multiple candidates |
| 3 | extract-deal | `/extract-deal <slug>` | **LLM** (Claude) | Anthropic API | Structured JSON output, 2-pass extraction |
| 4 | canonicalize | `skill-pipeline canonicalize` | Deterministic | None | Unknown block/evidence ID, mismatched refs |
| 5 | check | `skill-pipeline check` | Deterministic | None | Missing proposal terms, empty anchor text |
| 6 | verify | `skill-pipeline verify` | Deterministic | None | FUZZY/UNRESOLVED quotes, broken actor refs |
| 7 | coverage | `skill-pipeline coverage` | Deterministic | None | Uncovered high-confidence critical evidence |
| 8 | verify-extraction | `/verify-extraction <slug>` | **Hybrid** (LLM repair) | Anthropic API | Non-repairable errors → fail closed |
| 9 | enrich-core | `skill-pipeline enrich-core` | Deterministic | None | Gate prereqs (check/verify/coverage must pass) |
| 10 | enrich-deal | `/enrich-deal <slug>` | **LLM** (Claude) | Anthropic API | 8 sections, all must complete |
| 11 | export-csv | `/export-csv <slug>` | Formatting only | None | Missing enrichment artifacts |
| 12 | deal-agent | `skill-pipeline deal-agent` | Deterministic | None | Missing required source inputs |
| 13 | reconcile-alex | `/reconcile-alex <slug>` | **LLM** (post-export) | Anthropic API | Diagnostic only, never gates pipeline |

### Count Summary

- **8 deterministic CLI stages** (zero LLM): raw-fetch, preprocess-source, canonicalize, check, verify, coverage, enrich-core, deal-agent
- **3 LLM skill stages**: extract-deal, enrich-deal, reconcile-alex
- **1 hybrid stage**: verify-extraction (deterministic findings → LLM repair loop)
- **1 formatting skill** (no LLM): export-csv

### Key Architectural Pattern

The pipeline sandwiches LLM extraction between deterministic gates:
1. **Deterministic prep** (raw-fetch, preprocess) produces source artifacts
2. **LLM extraction** (/extract-deal) reads source, writes raw actors/events
3. **Deterministic validation** (canonicalize, check, verify, coverage) validates LLM output against filing text
4. **LLM repair** (/verify-extraction) fixes repairable errors only
5. **Deterministic enrichment** (enrich-core) applies rule-based classifications
6. **LLM enrichment** (/enrich-deal) adds interpretive layer
7. **Deterministic export** (/export-csv) formats final CSV

## Artifact Dependency Chain

```
data/seeds.csv
  → raw/<slug>/filings/*.txt (immutable), discovery.json, document_registry.json
  → data/deals/<slug>/source/chronology_blocks.jsonl, evidence_items.jsonl
  → data/skill/<slug>/extract/actors_raw.json, events_raw.json [LLM writes]
  → data/skill/<slug>/extract/spans.json [canonicalize writes]
  → data/skill/<slug>/check/check_report.json
  → data/skill/<slug>/verify/verification_log.json
  → data/skill/<slug>/coverage/coverage_findings.json, coverage_summary.json
  → data/skill/<slug>/enrich/deterministic_enrichment.json
  → data/skill/<slug>/enrich/enrichment.json [LLM writes]
  → data/skill/<slug>/export/deal_events.csv
  → data/skill/<slug>/reconcile/reconciliation_report.json [optional, post-export]
```

## Handoff Boundaries

| From | To | Artifact | Missing Behavior |
|------|----|----------|-----------------|
| raw-fetch | preprocess-source | filings/*.txt, discovery.json, document_registry.json | FileNotFoundError |
| preprocess-source | /extract-deal | chronology_blocks.jsonl, evidence_items.jsonl | Skill fails |
| /extract-deal | canonicalize | actors_raw.json, events_raw.json | FileNotFoundError |
| canonicalize | check/verify/coverage | spans.json (required sidecar) | FileNotFoundError |
| check + verify + coverage | enrich-core | All three must status="pass" | ValueError |
| enrich-core | /enrich-deal | deterministic_enrichment.json | Skill fails |
| /enrich-deal | /export-csv | enrichment.json | Skill fails |
| /export-csv | /reconcile-alex | deal_events.csv (must exist) | Post-export gate |

## Test Coverage

| Test File | Stage | Tests | Lines |
|-----------|-------|-------|-------|
| test_skill_raw_stage.py | raw-fetch | 9 | 262 |
| test_skill_preprocess_source.py | preprocess-source | 8 | 331 |
| test_skill_canonicalize.py | canonicalize | 14 | 526 |
| test_skill_check.py | check | 6 | 202 |
| test_skill_verify.py | verify | 6 | 471 |
| test_skill_coverage.py | coverage | 6 | 416 |
| test_skill_enrich_core.py | enrich-core | 36 | 963 |
| test_skill_pipeline.py | integration | 4 | 361 |
| test_benchmark_separation_policy.py | policy boundary | 10 | 149 |
| test_skill_mirror_sync.py | skill sync | 4 | 77 |
| test_skill_provenance.py | span resolution | 3 | 240 |
| **Total** | | **106** | **3,998** |

## Policy Boundaries Enforced

| Boundary | Mechanism | Test Coverage |
|----------|-----------|--------------|
| Immutable raw filings | FileExistsError on rerun | Yes |
| Seed-only constraint | ValueError if supplementary candidates | Yes |
| Single primary document | ValueError if != 1 | Yes |
| NDA-gate drops | Drop without prior NDA removed | Yes |
| Quote strictness | EXACT/NORMALIZED only; FUZZY fails | Yes |
| Span registry required | Canonical artifacts need spans.json | Yes |
| Benchmark separation | Generation docs forbid example/, diagnosis/ | Yes |
| Skill mirror sync | .claude/ → .codex/, .cursor/ only | Yes |
| Line endings | LF only via .gitattributes | Yes |
| Gate prerequisites | check+verify+coverage must pass before enrich-core | Yes |

## LLM Configuration

```
ANTHROPIC_API_KEY      — required for Anthropic provider
OPENAI_API_KEY         — required for OpenAI provider
BIDS_LLM_PROVIDER      — default: anthropic (anthropic|openai)
BIDS_LLM_MODEL         — override model ID
```

Note: The Python code does NOT directly import `anthropic` or `openai`. LLM calls are handled entirely by Claude Code skills. The `anthropic>=0.49` dependency in pyproject.toml exists but is not used in the active deterministic stages.

## Gaps Relevant to Phase 1

1. **No single document maps the full stage inventory** — the flow is spread across CLAUDE.md, skill files, and code
2. **Deterministic vs. LLM boundary is implicit** — discoverable only by reading code, not from any contract doc
3. **Artifact path conventions exist in paths.py but aren't surfaced** to contributors as a reference
4. **.planning/ project memory is new** — success criteria and context need to be made durable

---
*Research completed: 2026-03-25 via 4 parallel exploration agents*
