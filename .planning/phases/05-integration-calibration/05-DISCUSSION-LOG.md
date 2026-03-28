# Phase 5: Integration + Calibration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 05-integration-calibration
**Areas discussed:** DuckDB schema + loading, Orchestration contract, Complexity routing, Few-shot expansion

---

## DuckDB Schema + Loading

### Q1: Database scope

| Option | Description | Selected |
|--------|-------------|----------|
| Single multi-deal database | One .duckdb file with all deals. Enables cross-deal queries. Simpler export. | ✓ |
| One database per deal | Isolated per-deal files under data/skill/<slug>/. No cross-deal contamination risk. | |
| You decide | Claude picks based on requirements and existing patterns. | |

**User's choice:** Single multi-deal database
**Notes:** None

### Q2: Loading point

| Option | Description | Selected |
|--------|-------------|----------|
| After enrich-core as a new 'db-load' stage | New CLI command: skill-pipeline db-load --deal <slug>. Runs after all gates pass. | ✓ |
| Inside enrich-core as a final step | Enrich-core already has all the data. DuckDB write becomes its last operation. | |
| After export-csv as final stage | DB loading happens last, after all local-agent work. | |
| You decide | Claude picks the cleanest integration point. | |

**User's choice:** After enrich-core as a new 'db-load' stage
**Notes:** None

### Q3: CSV export migration

| Option | Description | Selected |
|--------|-------------|----------|
| New Python db-export stage | skill-pipeline db-export --deal <slug> generates CSV from DuckDB queries. Replaces /export-csv. | ✓ |
| Keep /export-csv skill, read from DuckDB | Local-agent skill reads from DuckDB instead of JSON. | |
| Both: Python for standard CSV, skill for custom | Python handles standard export, skill for interpretive needs. | |
| You decide | Claude picks based on existing export-csv skill complexity. | |

**User's choice:** New Python db-export stage
**Notes:** None

---

## Orchestration Contract

### Q1: Orchestration form

| Option | Description | Selected |
|--------|-------------|----------|
| Enhanced deal-agent with run plan | Expand deal-agent to emit machine-readable run plan. | |
| New run-pipeline CLI command | Single entry point executing all deterministic stages then handoff. | |
| Documented workflow only | No new Python code. Updated docs and skill. | |
| You decide | Claude picks approach satisfying DB-02 with local-agent constraint. | ✓ |

**User's choice:** You decide
**Notes:** None

### Q2: Batch scope

| Option | Description | Selected |
|--------|-------------|----------|
| Per-deal only | One deal at a time. Batch = sequential per-deal invocations. | |
| Batch mode with per-deal fallback | --all processes all 9 deals. Still per-deal internally. | |
| You decide | Claude picks what fits exit criteria. | ✓ |

**User's choice:** You decide, but for test we will need to be able to make sure one deal works, then batch works
**Notes:** Testing strategy: per-deal first, then batch.

---

## Complexity Routing

### Q1: Automatic vs override

| Option | Description | Selected |
|--------|-------------|----------|
| Automatic with override flag | Auto-detect with --force-chunked/--force-single-pass flags. | |
| Fully automatic, no override | Thresholds are single source of truth. | |
| You decide | Claude picks based on codebase pattern. | ✓ |

**User's choice:** You decide
**Notes:** None

### Q2: Thresholds

| Option | Description | Selected |
|--------|-------------|----------|
| Roadmap thresholds are final | Use <=150 blocks AND <=8 actors as fixed boundary. | |
| Calibrate from corpus first | Run all 9 deals, measure, then set thresholds. | |
| You decide | Claude picks based on actual deal data. | ✓ |

**User's choice:** You decide
**Notes:** None

---

## Few-Shot Expansion

### Q1: Example source

| Option | Description | Selected |
|--------|-------------|----------|
| Extract from completed deals | Use verified extraction artifacts from stec and others. | |
| Hand-craft from filing text | Manually write examples covering 5 target patterns. | |
| You decide | Claude picks approach for highest-quality examples. | ✓ |

**User's choice:** You decide
**Notes:** None

### Q2: Example format

| Option | Description | Selected |
|--------|-------------|----------|
| Expand existing prompt_assets/ files | Add to event_examples.md directly. Matches current pattern. | |
| Structured example registry | JSON/JSONL registry with metadata. Compose-prompts selects by complexity. | |
| You decide | Claude picks format compatible with existing engine. | ✓ |

**User's choice:** You decide
**Notes:** None

---

## Claude's Discretion

- Orchestration form (enhanced deal-agent, new CLI, documented workflow, or combination)
- Batch mode design (per-deal + --all flag, or separate commands)
- Complexity routing: automatic vs override, exact thresholds
- Few-shot example source and format
- DuckDB table schema and normalization level
- Chunk-budget overhead resolution

## Deferred Ideas

None — discussion stayed within phase scope
