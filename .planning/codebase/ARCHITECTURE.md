# Architecture

**Analysis Date:** 2026-03-25

## Pattern Overview

**Overall:** Monolithic local CLI pipeline with hybrid agent-assisted stages

**Key Characteristics:**
- One installed package, `skill_pipeline/`, with a single console entrypoint in `skill_pipeline/cli.py`
- File-based artifact flow instead of service-to-service communication
- Deterministic Python stages wrapped around LLM-driven skill stages documented in `.claude/skills/`
- Fail-fast behavior on missing inputs, schema mismatches, and boundary violations

## Layers

**Contract and schema layer:**
- Purpose: define artifact shapes, path conventions, and shared constants
- Contains: `skill_pipeline/models.py`, `skill_pipeline/pipeline_models/`, `skill_pipeline/config.py`, `skill_pipeline/paths.py`
- Depends on: Pydantic and `pathlib`
- Used by: every deterministic stage

**Ingress layer:**
- Purpose: turn a deal seed into frozen raw filing artifacts
- Contains: `skill_pipeline/cli.py`, `skill_pipeline/seeds.py`, `skill_pipeline/raw/discover.py`, `skill_pipeline/raw/fetch.py`, `skill_pipeline/raw/stage.py`
- Depends on: the contract layer plus `edgartools`
- Used by: operators running `skill-pipeline raw-fetch` or `skill-pipeline source-discover`

**Source preparation layer:**
- Purpose: localize the chronology section and derive evidence items from the frozen filing
- Contains: `skill_pipeline/preprocess/source.py`, `skill_pipeline/source/locate.py`, `skill_pipeline/source/blocks.py`, `skill_pipeline/source/evidence.py`
- Depends on: raw artifacts plus source models
- Used by: `skill-pipeline preprocess-source`

**Deterministic transform and QA layer:**
- Purpose: canonicalize extract artifacts and enforce structural, referential, quote, and coverage constraints
- Contains: `skill_pipeline/canonicalize.py`, `skill_pipeline/check.py`, `skill_pipeline/verify.py`, `skill_pipeline/coverage.py`, `skill_pipeline/provenance.py`, `skill_pipeline/normalize/`
- Depends on: source artifacts and extract artifacts
- Used by: operators after `/extract-deal` has written extract files

**Deterministic enrichment layer:**
- Purpose: derive rounds, bid classifications, cycles, and formal boundary from validated extract artifacts
- Contains: `skill_pipeline/enrich_core.py` and `skill_pipeline/extract_artifacts.py`
- Depends on: passing check, verify, and coverage outputs
- Used by: `skill-pipeline enrich-core`

**Agent orchestration and policy layer:**
- Purpose: document the non-CLI stages and the repo operating contract
- Contains: `CLAUDE.md`, `AGENTS.md`, `.claude/skills/`, `.codex/skills/`, `.cursor/skills/`, `scripts/sync_skill_mirrors.py`
- Depends on: repository conventions rather than Python imports
- Used by: humans and agents running `/extract-deal`, `/verify-extraction`, `/enrich-deal`, `/export-csv`, and `/reconcile-alex`

## Data Flow

**Hybrid deal workflow:**

1. Operator selects a deal from `data/seeds.csv`
2. `skill-pipeline raw-fetch --deal <slug>` freezes one approved SEC filing into `raw/<slug>/`
3. `skill-pipeline preprocess-source --deal <slug>` writes chronology and evidence artifacts into `data/deals/<slug>/source/`
4. `/extract-deal <slug>` writes raw extract artifacts into `data/skill/<slug>/extract/`
5. `skill-pipeline canonicalize/check/verify/coverage` upgrades and audits those artifacts
6. `/verify-extraction <slug>` may repair deterministic findings when the findings are repairable
7. `skill-pipeline enrich-core --deal <slug>` writes deterministic enrichment outputs
8. `/enrich-deal <slug>` and `/export-csv <slug>` add later interpretive and export layers
9. `/reconcile-alex <slug>` is optional post-export QA only

**State management:**
- The system is file-based; no database-backed application state exists
- Raw inputs, intermediate artifacts, and downstream outputs live in explicit repository directories
- Reruns rely on the presence and correctness of those files rather than in-memory state

## Key Abstractions

**Artifact models:**
- Purpose: enforce schema correctness at every stage boundary
- Examples: `RawDiscoveryManifest`, `FrozenDocument`, `ChronologySelection`, `SkillActorsArtifact`, `SkillVerificationLog`
- Pattern: Pydantic models validated at read and write boundaries

**Path set:**
- Purpose: centralize all deal-specific file locations
- Examples: `build_skill_paths()` and `SkillPathSet` in `skill_pipeline/paths.py` and `skill_pipeline/models.py`
- Pattern: derive paths once, reuse across stages

**Span-backed provenance:**
- Purpose: connect canonical extract evidence back to exact filing text spans
- Examples: `resolve_text_span()` in `skill_pipeline/provenance.py` and `spans.json`
- Pattern: canonical sidecar registry plus deterministic validation

## Entry Points

**CLI entrypoint:**
- Location: `skill_pipeline/cli.py`
- Triggers: `skill-pipeline <command>`
- Responsibilities: parse subcommands, load seeds, dispatch to stage functions, print JSON or return an exit code

**Preflight summary entrypoint:**
- Location: `skill_pipeline/deal_agent.py`
- Triggers: `skill-pipeline deal-agent --deal <slug>`
- Responsibilities: summarize artifact state; it is not the end-to-end runner

**Skill entrypoints:**
- Location: `.claude/skills/*/SKILL.md`
- Triggers: explicit skill invocation by a human or agent
- Responsibilities: run LLM-assisted extraction, repair, enrichment, export, and reconciliation work around the deterministic CLI

## Error Handling

**Strategy:** raise precise exceptions and invalidate partial outputs when a stage cannot produce trustworthy artifacts

**Patterns:**
- Missing required inputs raise `FileNotFoundError` early
- Invalid invariants raise `ValueError` or `RuntimeError`
- `preprocess_source_deal()` and `run_enrich_core()` remove or invalidate partial outputs on failure
- No silent fallback exists for missing source files, missing spans, or benchmark-boundary violations

## Cross-Cutting Concerns

**Validation:**
- Pydantic models validate both inputs and outputs across stages

**Provenance:**
- Canonicalization and verification resolve evidence back to filing text and reject unresolved or fuzzy provenance

**Repo policy:**
- `CLAUDE.md` defines benchmark separation, canonical skill-tree ownership, and cross-platform line-ending rules

**Cross-platform hygiene:**
- `.gitattributes` enforces `LF` text files
- `.claude/skills` is canonical, while `.codex/skills` and `.cursor/skills` are derived mirrors

---

*Architecture analysis: 2026-03-25*
*Update when major patterns change*
