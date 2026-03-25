# Codebase Structure

**Analysis Date:** 2026-03-25

## Directory Layout

```text
bids_data/
|-- .planning/          # GSD project memory and brownfield codebase map
|-- .claude/            # Canonical skill instructions
|-- .codex/             # Derived Codex skill mirror
|-- .cursor/            # Derived Cursor skill mirror
|-- data/               # Seeds plus preprocessed and skill-stage artifacts
|-- docs/               # Design notes, setup docs, and plans
|-- quality_reports/    # Tracked report outputs
|-- raw/                # Immutable frozen filing text and discovery metadata
|-- scripts/            # Repo utilities such as skill-mirror sync
|-- skill_pipeline/     # Installed Python package and deterministic CLI stages
|-- tests/              # Pytest regression tests
|-- .gitattributes      # Line-ending policy
|-- .gitignore          # Local-state ignore rules
|-- AGENTS.md           # Minimal repo entry instruction
|-- CLAUDE.md           # Authoritative repository instructions
|-- pyproject.toml      # Package metadata and CLI entrypoint
`-- pytest.ini          # Pytest configuration
```

## Directory Purposes

**`skill_pipeline/`**
- Purpose: tracked Python implementation of the deterministic runtime
- Contains: stage modules, source helpers, raw-fetch helpers, Pydantic models
- Key files: `skill_pipeline/cli.py`, `skill_pipeline/raw/stage.py`, `skill_pipeline/preprocess/source.py`, `skill_pipeline/canonicalize.py`, `skill_pipeline/verify.py`, `skill_pipeline/coverage.py`, `skill_pipeline/enrich_core.py`
- Subdirectories: `raw/`, `preprocess/`, `source/`, `normalize/`, `pipeline_models/`

**`tests/`**
- Purpose: regression coverage for stage contracts and repo policy
- Contains: `test_skill_*.py` stage tests plus policy tests like `test_benchmark_separation_policy.py`
- Key files: `tests/test_skill_raw_stage.py`, `tests/test_skill_preprocess_source.py`, `tests/test_skill_pipeline.py`, `tests/test_skill_mirror_sync.py`
- Subdirectories: none in the tracked tree

**`data/`**
- Purpose: deal seeds and generated artifacts that remain part of the working dataset
- Contains: `data/seeds.csv`, `data/deals/<slug>/source/`, `data/skill/<slug>/...`
- Key files: `data/seeds.csv`
- Subdirectories: `deals/`, `skill/`

**`raw/`**
- Purpose: immutable frozen filing text and raw discovery metadata keyed by deal slug
- Contains: `raw/<slug>/filings/*.txt|*.html`, `discovery.json`, `document_registry.json`
- Key files: per-deal discovery and registry files
- Subdirectories: one directory per active deal slug

**`docs/`**
- Purpose: design notes, plans, and local environment setup
- Contains: `docs/design.md`, `docs/HOME_COMPUTER_SETUP.md`, dated design notes under `docs/plans/` and `docs/superpowers/`
- Key files: `docs/design.md`, `docs/HOME_COMPUTER_SETUP.md`
- Subdirectories: `plans/`, `superpowers/`

**`.claude/`, `.codex/`, `.cursor/`**
- Purpose: skill documentation for the hybrid agent workflow
- Contains: mirrored skill trees under `skills/`
- Key files: `.claude/skills/*/SKILL.md`, `.codex/skills/*/SKILL.md`, `.cursor/skills/*/SKILL.md`
- Subdirectories: `skills/`

**`.planning/`**
- Purpose: GSD project context, roadmap, and codebase map
- Contains: `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, and `.planning/codebase/*.md`
- Key files: `.planning/PROJECT.md`, `.planning/ROADMAP.md`
- Subdirectories: `codebase/`

## Key File Locations

**Entry Points:**
- `skill_pipeline/cli.py` - installed CLI entrypoint for deterministic stages
- `skill_pipeline/deal_agent.py` - preflight artifact summary command

**Configuration:**
- `pyproject.toml` - package metadata and the `skill-pipeline` script
- `pytest.ini` - pytest root settings
- `.gitattributes` - tracked line endings
- `.gitignore` - ignored local-only paths
- `CLAUDE.md` - repository operating contract

**Core Logic:**
- `skill_pipeline/raw/` - seed-only raw discovery and fetch
- `skill_pipeline/preprocess/source.py` - chronology and evidence materialization
- `skill_pipeline/canonicalize.py` - raw-to-canonical upgrade and provenance resolution
- `skill_pipeline/check.py`, `skill_pipeline/verify.py`, `skill_pipeline/coverage.py` - deterministic QA gates
- `skill_pipeline/enrich_core.py` - deterministic enrichment

**Testing:**
- `tests/` - all tracked tests
- `tests/test_benchmark_separation_policy.py` - benchmark-boundary policy enforcement

**Documentation:**
- `CLAUDE.md` - authoritative repo instructions
- `docs/design.md` - high-level pipeline index
- `.planning/` - GSD planning surface

## Naming Conventions

**Files:**
- `snake_case.py` for Python modules in `skill_pipeline/`
- `test_<scope>.py` for pytest modules in `tests/`
- `YYYY-MM-DD-*.md` for dated design notes in `docs/plans/` and `docs/superpowers/`

**Directories:**
- Deal artifacts use the slug as the directory name under `raw/`, `data/deals/`, and `data/skill/`
- Skill directories use kebab-case names such as `.claude/skills/extract-deal/`

**Special Patterns:**
- Skill instructions live in `SKILL.md` files
- Canonical extract sidecars use `spans.json`
- Deterministic stage outputs are grouped by stage directory under `data/skill/<slug>/`

## Where to Add New Code

**New deterministic stage behavior:**
- Implementation: `skill_pipeline/`
- Tests: `tests/test_skill_<stage>.py`
- Path/schema changes: `skill_pipeline/models.py`, `skill_pipeline/pipeline_models/`, or `skill_pipeline/paths.py`

**New repo policy or workflow documentation:**
- Repo contract: `CLAUDE.md`
- Planning/milestones: `.planning/`
- Detailed design notes: `docs/`

**New skill workflow logic:**
- Author in `.claude/skills/`
- Sync mirrors with `scripts/sync_skill_mirrors.py`

## Special Directories

**`raw/`**
- Purpose: immutable truth source for filing text
- Source: fetched from EDGAR and written once
- Committed: yes

**`data/`**
- Purpose: deal inputs and generated workflow artifacts
- Source: stage outputs and curated seeds
- Committed: yes

**`.planning/`**
- Purpose: GSD planning artifacts for this repo
- Source: manually maintained brownfield planning docs
- Committed: yes

**`.agents/`**
- Purpose: local scratch area for agent runtime state
- Source: local machine only
- Committed: no; ignored by `.gitignore`

---

*Structure analysis: 2026-03-25*
*Update when directory structure changes*
