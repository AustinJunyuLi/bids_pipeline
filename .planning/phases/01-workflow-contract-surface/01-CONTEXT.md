# Phase 1: Workflow Contract Surface -- Context

**Created:** 2026-03-25
**Phase:** 01-workflow-contract-surface
**Derived from:** 01-RESEARCH.md, docs/workflow-contract.md, CLAUDE.md

## Phase Boundary

Phase 1 is a contract-publication phase. It does not change runtime behavior, add stages, or redesign orchestration. Its deliverables are committed documentation and planning artifacts that make the existing hybrid brownfield workflow explicit and resumable.

## Accepted Workflow Baseline

The live pipeline is a deterministic/skill sandwich with 11 active stages plus one optional post-export diagnostic. The accepted stage order is:

```text
1.  skill-pipeline raw-fetch --deal <slug>         (deterministic)
2.  skill-pipeline preprocess-source --deal <slug>  (deterministic)
3.  /extract-deal <slug>                            (LLM skill)
4.  skill-pipeline canonicalize --deal <slug>       (deterministic)
5.  skill-pipeline check --deal <slug>              (deterministic)
6.  skill-pipeline verify --deal <slug>             (deterministic)
7.  skill-pipeline coverage --deal <slug>           (deterministic)
8.  /verify-extraction <slug>                       (hybrid repair)
9.  skill-pipeline enrich-core --deal <slug>        (deterministic)
10. /enrich-deal <slug>                             (LLM skill)
11. /export-csv <slug>                              (LLM skill)
--  /reconcile-alex <slug>                          (optional, post-export)
```

### deterministic vs LLM Split

| Category | Count | Stages |
|----------|-------|--------|
| Deterministic CLI | 7 | raw-fetch, preprocess-source, canonicalize, check, verify, coverage, enrich-core |
| LLM skill | 3 | /extract-deal, /enrich-deal, /export-csv |
| Hybrid repair (LLM + deterministic pre-steps) | 1 | /verify-extraction |
| Post-export diagnostic (LLM, optional) | 1 | /reconcile-alex |

Deterministic stages own artifact validity and fail-fast gating. LLM skill stages own extraction, interpretation, export formatting, and benchmark comparison.

### deal-agent Disambiguation

The name "deal-agent" refers to two distinct entrypoints:

- **`skill-pipeline deal-agent --deal <slug>`** (CLI summary): Deterministic preflight that checks prerequisites, ensures output directories exist, and summarizes stage artifact status. It does not run extraction, repair, enrichment, or export.
- **`/deal-agent <slug>`** (skill orchestrator): Runs the full end-to-end skill workflow from `/extract-deal` through deterministic gates through `/verify-extraction` through deterministic enrichment through `/enrich-deal` through `/export-csv`.

These are not interchangeable. The CLI command summarizes; the skill command orchestrates.

## Brownfield Drifts Tracked in Phase 1

### 1. `supplementary_snippets.jsonl` contract mismatch

- **Observed:** `preprocess-source` actively deletes stale `supplementary_snippets.jsonl` copies and does not regenerate the file.
- **Drift:** Some skill docs (historically including `enrich-deal`) listed `supplementary_snippets.jsonl` as a required read input.
- **Resolution in Phase 1:** Plan 01-02 removed the stale reference from the enrich-deal SKILL.md Reads table. The file is not part of the live source contract. Future phases should not assume it exists.

### 2. Legacy `data/deals/<slug>/{extract,qa}` artifacts

- **Observed:** The checked-in dataset contains `data/deals/<slug>/extract/` and `data/deals/<slug>/qa/` outputs for several active deals.
- **Drift:** Current code and skill docs target `data/skill/<slug>/...` as the active extract, check, verify, coverage, enrich, and export root. The `data/deals/<slug>/{extract,qa}` paths are legacy from an earlier pipeline layout.
- **Resolution in Phase 1:** These artifacts are treated as historical/non-authoritative. They should not be referenced by new docs or plans as the current contract surface.

### 3. Historical docs that look plausible but are not authoritative

- **Observed:** `docs/plans/2026-03-16-pipeline-design-v3.md` and `quality_reports/session_logs/2026-03-18_skill-pipeline-design.md` contain detailed workflow descriptions that predate the current runtime.
- **Drift:** Those documents describe earlier transition states (all-filings preprocess, "Alex-compatible" export framing) that no longer match the seed-only, filing-grounded contract.
- **Resolution in Phase 1:** Plan 01-01 published `docs/workflow-contract.md` as the single canonical stage inventory. Historical docs are background context, not live contracts.

## Key Decisions from Phase 1

| Decision | Source |
|----------|--------|
| Workflow contract doc is the single detailed inventory; design.md stays a concise index | Plan 01-01 |
| Stage count: 7 deterministic, 3 LLM skill, 1 hybrid repair, 1 optional post-export diagnostic | Plan 01-01 |
| deal-agent disambiguation added to CLAUDE.md as a dedicated section | Plan 01-02 |
| Stale supplementary_snippets.jsonl removed from enrich-deal Reads entirely | Plan 01-02 |
| /export-csv classified as LLM skill (formatting only) | Plan 01-01 |

## Authoritative Sources

| Surface | Authority | Use |
|---------|-----------|-----|
| `CLAUDE.md` | HIGH | Primary repo contract, invariants, benchmark boundary |
| `docs/workflow-contract.md` | HIGH | Single canonical stage inventory with classification and artifact roots |
| `skill_pipeline/cli.py` + `paths.py` + `models.py` | HIGH | Deterministic stage entrypoints, path contract, schema contract |
| `.claude/skills/*/SKILL.md` | HIGH for intent | Skill-stage reads, writes, procedure |
| `tests/test_workflow_contract_surface.py` | HIGH | 9 regression assertions protecting the contract surface |
| `.planning/{PROJECT,REQUIREMENTS,ROADMAP,STATE}.md` | HIGH | Shared project memory and phase continuity |
| `docs/plans/*`, `quality_reports/session_logs/*` | LOW | Historical context only, not live contract |

## What Later Phases Inherit

1. The stage order and classification are locked by `docs/workflow-contract.md` and protected by regression tests.
2. The deal-agent disambiguation is documented in both `CLAUDE.md` and the workflow contract.
3. The `supplementary_snippets.jsonl` drift is resolved (removed from skill docs) and documented here.
4. Legacy `data/deals/<slug>/{extract,qa}` paths are labeled as historical and should not appear in new contract references.
5. `.planning/` provides enough shared context that future phases start from committed memory rather than rediscovering the deterministic-versus-skill split.

---
*Phase: 01-workflow-contract-surface*
*Created: 2026-03-25*
