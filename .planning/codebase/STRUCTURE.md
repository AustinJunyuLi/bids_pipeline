# Codebase Structure

**Analysis Date:** 2026-03-26

## Directory Layout

```text
bids_pipeline/
├── .claude/skills/              # Canonical skill instructions for the LLM-owned stages
├── .codex/skills/               # Mirrored skill tree for Codex
├── .cursor/skills/              # Mirrored skill tree for Cursor
├── .planning/                   # GSD project memory, phases, research, notes, and codebase docs
├── data/
│   ├── deals/                   # Deal-scoped source artifacts; current tree also contains non-active extract/qa directories
│   ├── runs/                    # Run-scoped data directory present in the repository
│   └── skill/                   # Active skill-stage artifacts keyed by deal slug
├── diagnosis/                   # Benchmark and external review material; post-export boundary applies
├── docs/                        # Design, setup, workflow contract, and benchmark collection docs
├── example/                     # Example and benchmark workbook material
├── quality_reports/             # Session and review report outputs
├── raw/                         # Frozen filing snapshots and raw discovery metadata keyed by deal slug
├── scripts/                     # Repository maintenance utilities
├── skill_pipeline/              # Installable Python package and deterministic stage implementation
├── tests/                       # Pytest suites for runtime behavior and repository policy
├── AGENTS.md                    # Minimal entry instruction that points to `CLAUDE.md`
├── CLAUDE.md                    # Authoritative repository contract
├── pyproject.toml               # Package metadata and `skill-pipeline` entrypoint
├── pytest.ini                   # Pytest configuration
└── requirements.txt             # Additional Python dependency surface present at repo root
```

## Directory Purposes

**`skill_pipeline/`:**
- Purpose: hold the active deterministic runtime.
- Contains: CLI dispatch, stage implementations, schema models, provenance helpers, normalization helpers, and path utilities.
- Key files: `skill_pipeline/cli.py`, `skill_pipeline/config.py`, `skill_pipeline/paths.py`, `skill_pipeline/models.py`, `skill_pipeline/extract_artifacts.py`, `skill_pipeline/deal_agent.py`.

**`skill_pipeline/raw/`:**
- Purpose: implement the active raw ingress path.
- Contains: seed-only discovery and immutable freeze logic.
- Key files: `skill_pipeline/raw/discover.py`, `skill_pipeline/raw/fetch.py`, `skill_pipeline/raw/stage.py`.

**`skill_pipeline/preprocess/`:**
- Purpose: build source artifacts from frozen filings.
- Contains: the top-level preprocess stage.
- Key files: `skill_pipeline/preprocess/source.py`.

**`skill_pipeline/source/`:**
- Purpose: hold source-selection and evidence helper modules.
- Contains: chronology localization, block building, evidence scanning, ranking helpers, and supplementary helper code.
- Key files: `skill_pipeline/source/locate.py`, `skill_pipeline/source/blocks.py`, `skill_pipeline/source/evidence.py`, `skill_pipeline/source/ranking.py`, `skill_pipeline/source/discovery.py`.

**`skill_pipeline/pipeline_models/`:**
- Purpose: define low-level pipeline artifact envelopes and source/raw schema families.
- Contains: shared enums and typed artifact models.
- Key files: `skill_pipeline/pipeline_models/common.py`, `skill_pipeline/pipeline_models/raw.py`, `skill_pipeline/pipeline_models/source.py`.

**`tests/`:**
- Purpose: verify deterministic stage behavior and repo-level policy boundaries.
- Contains: one-file-per-surface pytest modules such as `tests/test_skill_raw_stage.py`, `tests/test_skill_preprocess_source.py`, `tests/test_skill_canonicalize.py`, `tests/test_skill_check.py`, `tests/test_skill_verify.py`, `tests/test_skill_coverage.py`, `tests/test_skill_enrich_core.py`, `tests/test_skill_pipeline.py`, `tests/test_workflow_contract_surface.py`, `tests/test_benchmark_separation_policy.py`, `tests/test_skill_mirror_sync.py`.
- Key files: `tests/test_skill_pipeline.py`, `tests/test_workflow_contract_surface.py`, `tests/test_benchmark_separation_policy.py`.

**`raw/`:**
- Purpose: store deal-keyed frozen filing content and raw discovery metadata.
- Contains: one directory per slug such as `raw/imprivata/`, `raw/petsmart-inc/`, `raw/stec/`, each with `discovery.json`, `document_registry.json`, and a `filings/` directory of `.txt` and `.html` snapshots.
- Key files: `raw/<slug>/discovery.json`, `raw/<slug>/document_registry.json`, `raw/<slug>/filings/*.txt`.

**`data/deals/`:**
- Purpose: store deal-keyed source artifacts consumed by the LLM extraction stage.
- Contains: `data/deals/<slug>/source/chronology_selection.json`, `data/deals/<slug>/source/chronology_blocks.jsonl`, `data/deals/<slug>/source/evidence_items.jsonl`, `data/deals/<slug>/source/chronology.json`, and copied filings under `data/deals/<slug>/source/filings/` when present.
- Key files: `data/deals/<slug>/source/chronology_blocks.jsonl`, `data/deals/<slug>/source/evidence_items.jsonl`.

**`data/skill/`:**
- Purpose: store active extract, gate, enrichment, export, and reconciliation artifacts for the skill workflow.
- Contains: stage directories like `extract/`, `canonicalize/`, `check/`, `verify/`, `coverage/`, `enrich/`, `export/`, and `reconcile/` under each slug.
- Key files: `data/skill/<slug>/extract/actors_raw.json`, `data/skill/<slug>/extract/events_raw.json`, `data/skill/<slug>/extract/spans.json`, `data/skill/<slug>/check/check_report.json`, `data/skill/<slug>/verify/verification_log.json`, `data/skill/<slug>/coverage/coverage_summary.json`, `data/skill/<slug>/enrich/deterministic_enrichment.json`, `data/skill/<slug>/export/deal_events.csv`.

**`.claude/skills/`:**
- Purpose: hold the canonical LLM skill instructions.
- Contains: `SKILL.md` files for `deal-agent`, `extract-deal`, `verify-extraction`, `enrich-deal`, `export-csv`, and `reconcile-alex`.
- Key files: `.claude/skills/deal-agent/SKILL.md`, `.claude/skills/extract-deal/SKILL.md`, `.claude/skills/verify-extraction/SKILL.md`, `.claude/skills/enrich-deal/SKILL.md`, `.claude/skills/export-csv/SKILL.md`, `.claude/skills/reconcile-alex/SKILL.md`.

**`.codex/skills/` and `.cursor/skills/`:**
- Purpose: mirror the canonical skill tree for other agents.
- Contains: mirrored copies of the `.claude/skills/` structure.
- Key files: `.codex/skills/*/SKILL.md`, `.cursor/skills/*/SKILL.md`, `scripts/sync_skill_mirrors.py`.

**`.planning/`:**
- Purpose: store project-level planning memory and the codebase map.
- Contains: `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `.planning/codebase/*.md`, `.planning/notes/*.md`, `.planning/research/*.md`, and phase directories under `.planning/phases/`.
- Key files: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`.

**`docs/`:**
- Purpose: hold high-level design and operational reference documents.
- Contains: `docs/design.md`, `docs/workflow-contract.md`, `docs/HOME_COMPUTER_SETUP.md`, benchmark collection docs, and dated plan notes under `docs/plans/`.
- Key files: `docs/design.md`, `docs/workflow-contract.md`, `docs/HOME_COMPUTER_SETUP.md`, `docs/plans/2026-03-16-pipeline-design-v3.md`, `docs/plans/2026-03-16-prompt-engineering-spec.md`.

## Key File Locations

**Entry Points:**
- `pyproject.toml`: installs the `skill-pipeline` CLI via `skill_pipeline.cli:main`.
- `skill_pipeline/cli.py`: deterministic command router.
- `skill_pipeline/deal_agent.py`: preflight summary surface used by `skill-pipeline deal-agent`.
- `.claude/skills/deal-agent/SKILL.md`: orchestrated skill surface for end-to-end runs.

**Configuration:**
- `CLAUDE.md`: authoritative repository instructions and workflow constraints.
- `skill_pipeline/config.py`: repo-root and data-root constants plus filing-type preferences.
- `skill_pipeline/paths.py`: deal-path conventions for active artifacts.
- `pytest.ini`: pytest discovery configuration.
- `scripts/sync_skill_mirrors.py`: skill tree synchronization policy.

**Core Logic:**
- `skill_pipeline/raw/stage.py`: raw ingress orchestration.
- `skill_pipeline/preprocess/source.py`: chronology and evidence artifact generation.
- `skill_pipeline/canonicalize.py`: canonical upgrade and span creation.
- `skill_pipeline/check.py`: structural blocker gate.
- `skill_pipeline/verify.py`: strict provenance and referential-integrity gate.
- `skill_pipeline/coverage.py`: source-cue coverage audit.
- `skill_pipeline/enrich_core.py`: deterministic rounds, classifications, cycles, and formal boundary.

**Testing:**
- `tests/test_skill_raw_stage.py`: raw ingress expectations.
- `tests/test_skill_preprocess_source.py`: preprocess and source invalidation behavior.
- `tests/test_skill_canonicalize.py`: canonicalization, provenance, and recovery behavior.
- `tests/test_skill_pipeline.py`: deal-agent summary behavior.
- `tests/test_workflow_contract_surface.py`: workflow contract documentation guard.

## Naming Conventions

**Files:**
- Python modules use `snake_case.py` under `skill_pipeline/`, `skill_pipeline/raw/`, `skill_pipeline/preprocess/`, and `skill_pipeline/source/`.
- Test modules use `test_<surface>.py` under `tests/`.
- Skill instructions are always named `SKILL.md` inside a skill directory such as `.claude/skills/extract-deal/`.
- Planning files under `.planning/phases/` use numeric prefixes such as `01-01-PLAN.md`, `01-01-SUMMARY.md`, `01-CONTEXT.md`, `07-RESEARCH.md`.
- Dated notes use `YYYY-MM-DD-*.md` under `docs/plans/`, `.planning/notes/`, and `.planning/research/`.

**Directories:**
- Deal-specific directories use the slug under `raw/<slug>/`, `data/deals/<slug>/`, and `data/skill/<slug>/`.
- Stage output directories use the stage name under `data/skill/<slug>/`, for example `extract/`, `canonicalize/`, `check/`, `verify/`, `coverage/`, `enrich/`, `export/`, and `reconcile/`.
- Skill directories use kebab-case names under `.claude/skills/`, `.codex/skills/`, and `.cursor/skills/`.

## Where to Add New Code

**New deterministic CLI stage:**
- Primary code: add a top-level module under `skill_pipeline/` such as `skill_pipeline/<stage>.py`.
- Registration: wire the command into `skill_pipeline/cli.py`.
- Path conventions: add new stage directories and filenames in `skill_pipeline/paths.py` if the stage writes artifacts.
- Tests: add or extend `tests/test_skill_<stage>.py`.

**New raw ingress behavior:**
- Primary code: add to `skill_pipeline/raw/`.
- Shared parsing helpers: add to `skill_pipeline/source/ranking.py` only when the logic is shared with source discovery.
- Avoid: do not place active raw-fetch logic in `skill_pipeline/source/fetch.py`; `skill_pipeline/cli.py` dispatches raw ingress through `skill_pipeline/raw/stage.py` and `skill_pipeline/raw/fetch.py`.

**New source-preparation behavior:**
- Primary code: add stage orchestration to `skill_pipeline/preprocess/source.py`.
- Helper logic: add chronology logic to `skill_pipeline/source/locate.py`, block logic to `skill_pipeline/source/blocks.py`, and evidence heuristics to `skill_pipeline/source/evidence.py`.
- Validation: keep file-integrity checks in `skill_pipeline/source_validation.py`.

**New extract-artifact schema or gate logic:**
- Models: update `skill_pipeline/models.py` and, when needed, `skill_pipeline/pipeline_models/`.
- Loaders and adapters: update `skill_pipeline/extract_artifacts.py`.
- Provenance rules: update `skill_pipeline/provenance.py` and `skill_pipeline/normalize/` helpers.
- Tests: extend `tests/test_skill_canonicalize.py`, `tests/test_skill_check.py`, `tests/test_skill_verify.py`, or `tests/test_skill_coverage.py` as appropriate.

**New skill-stage behavior:**
- Canonical instruction source: add or edit `.claude/skills/<skill-name>/SKILL.md`.
- Mirrors: sync `.codex/skills/` and `.cursor/skills/` with `scripts/sync_skill_mirrors.py`.

**New generated artifacts:**
- Source-stage outputs: write under `data/deals/<slug>/source/`.
- Active skill-stage outputs: write under `data/skill/<slug>/<stage>/`.
- Avoid: do not place new active runtime outputs under `data/deals/<slug>/extract/` or `data/deals/<slug>/qa`; `skill_pipeline/paths.py` does not reference those directories.

**New planning or brownfield documentation:**
- Codebase map docs: place under `.planning/codebase/`.
- Phase work: place under `.planning/phases/<phase-name>/`.
- Research and notes: place under `.planning/research/` and `.planning/notes/`.

## Special Directories

**`data/deals/<slug>/extract`:**
- Purpose: extract artifacts are present in the current tree for several slugs.
- Generated: Yes.
- Committed: Yes.
- Placement rule: the active `skill_pipeline` path builder does not use this directory for current runtime writes.

**`data/deals/<slug>/qa`:**
- Purpose: QA artifacts are present in the current tree for several slugs.
- Generated: Yes.
- Committed: Yes.
- Placement rule: the active deterministic stages do not read or write this directory via `skill_pipeline/paths.py`.

**`data/skill/<slug>/extract/chunks`:**
- Purpose: hold per-chunk extraction artifacts produced by the chunked extract skill surface.
- Generated: Yes.
- Committed: Yes.
- Placement rule: keep chunk-level skill outputs under the active skill extract root rather than under `data/deals/`.

**`example/`:**
- Purpose: hold benchmark workbook material such as `example/deal_details.xlsx` and `example/deal_details_Alex_2026.xlsx`.
- Generated: No.
- Committed: Yes.
- Placement rule: treat as post-export benchmark input only.

**`diagnosis/deepthink/`:**
- Purpose: store external review rounds and prompts.
- Generated: Yes.
- Committed: Yes.
- Placement rule: keep benchmark or review material out of the filing-grounded generation path.

**`.planning/phases/`:**
- Purpose: store milestone phase context, plans, summaries, research, and verification files.
- Generated: Yes.
- Committed: Yes.
- Placement rule: phase-scoped planning artifacts belong here, not in `docs/`.

---

*Structure analysis: 2026-03-26*
