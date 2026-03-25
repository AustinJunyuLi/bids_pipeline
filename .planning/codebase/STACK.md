# Technology Stack

**Analysis Date:** 2026-03-25

## Languages

**Primary:**
- Python 3.11+ - all tracked runtime code in `skill_pipeline/` and the main test suite in `tests/`

**Secondary:**
- Markdown - repository instructions and design notes in `CLAUDE.md`, `docs/`, and `.claude/skills/`
- JSON/JSONL/CSV - pipeline artifacts and seed inputs under `data/` and `raw/`
- TOML/INI - project metadata and test configuration in `pyproject.toml` and `pytest.ini`

## Runtime

**Environment:**
- Local Python CLI runtime - invoked through the `skill-pipeline` console script defined in `pyproject.toml`
- No web server, database server, or background worker is tracked in this repository
- The runtime is file-based and operates against repository paths such as `raw/`, `data/deals/`, and `data/skill/`

**Package Manager:**
- `pip` / editable installs - the repo expects `pip install -e .`
- Build backend: `setuptools.build_meta` from `pyproject.toml`
- Lockfile: none tracked

## Frameworks

**Core:**
- Standard library `argparse` - command routing in `skill_pipeline/cli.py`
- Pydantic 2 - artifact schemas and validation in `skill_pipeline/models.py` and `skill_pipeline/pipeline_models/`
- `edgartools` - live SEC filing access in `skill_pipeline/raw/fetch.py` and `skill_pipeline/raw/stage.py`

**Testing:**
- `pytest` - all tracked tests under `tests/`
- `pytest` fixtures such as `tmp_path` and `monkeypatch` are the dominant testing style

**Build/Dev:**
- `setuptools` - packaging and editable installs from `pyproject.toml`
- No formatter or linter configuration is tracked in the repository

## Key Dependencies

**Critical:**
- `pydantic>=2.0` - validates raw, canonical, verification, coverage, and enrichment artifacts
- `edgartools>=5.23` - fetches approved SEC filings by accession number
- `pytest>=8.0` - regression tests for stage contracts and repo policy checks

**Supporting:**
- `anthropic>=0.49` - declared for adjacent skill-driven LLM workflows referenced in `CLAUDE.md`
- `openpyxl>=3.1` - declared for workbook-adjacent tasks and benchmark-era utilities, not the deterministic CLI core

## Configuration

**Environment:**
- LLM provider variables are documented in `CLAUDE.md`: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `BIDS_LLM_PROVIDER`, `BIDS_LLM_MODEL`, and related overrides
- Live SEC access uses `PIPELINE_SEC_IDENTITY`, then `SEC_IDENTITY`, then `EDGAR_IDENTITY`
- Local-only secrets live in `.env.local`, which is gitignored by `.gitignore`

**Build and Repo Policy:**
- `pyproject.toml` - package metadata and console entrypoint
- `pytest.ini` - pytest root and default options
- `.gitattributes` - tracked text files use `LF`
- `.gitignore` - ignores local environments, caches, editor state, and `.agents/`

## Platform Requirements

**Development:**
- Windows and Linux are both active development environments for this repo
- Python 3.11+ is required
- GitHub is the synchronization point between machines

**Production / Execution Target:**
- This is a local research pipeline, not a deployed service
- Artifacts are written into the repository working tree under `raw/` and `data/`

---

*Stack analysis: 2026-03-25*
*Update after major dependency or runtime changes*
