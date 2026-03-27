# Technology Stack

**Analysis Date:** 2026-03-27

## Languages

**Primary:**
- Python 3.11+ - All pipeline code, CLI, data processing, and testing

## Runtime

**Environment:**
- Python 3.11 or later (specified in `pyproject.toml`)

**Package Manager:**
- pip - Installs from `pyproject.toml` with setuptools
- Lockfile: Not present (uses version ranges)

## Frameworks

**Core:**
- Pydantic 2.0+ - Schema validation, data models, configuration (`skill_pipeline/models.py`, `skill_pipeline/pipeline_models/`)
  - Used for: `SkillModel`, `SeedEntry`, `RawSkillActorRecord`, `RawSkillEventRecord`, artifact schemas
  - Config: `ConfigDict(extra="forbid")` enforced across all models

**Testing:**
- pytest 8.0+ - Test runner and fixtures
  - Config: `pytest.ini` with `testpaths = tests`, `pythonpath = .`
  - Test discovery pattern: `test_*.py` files in `tests/` directory
  - Command: `pytest -q` for baseline runs

**Build/Dev:**
- setuptools 69+ - Package building and CLI entry point definition
- wheel - Python distribution packaging

## Key Dependencies

**Critical:**
- anthropic 0.49+ - Anthropic Claude API client for LLM-based extraction (optional at runtime; agents inject results via `/extract-deal` skill)
  - Environment variables: `ANTHROPIC_API_KEY`, `BIDS_LLM_PROVIDER`, `BIDS_LLM_MODEL`, `BIDS_LLM_REASONING_EFFORT`, `BIDS_LLM_STRUCTURED_MODE`
  - Used by: External skills (`/extract-deal`, `/verify-extraction`, `/enrich-deal`, `/export-csv`), not by `skill_pipeline` CLI directly

- edgartools 5.23+ - SEC EDGAR filing fetch and search
  - Entry points: `from edgar import get_by_accession_number`, `from edgar import set_identity`
  - Used by: `skill_pipeline/raw/fetch.py`, `skill_pipeline/raw/stage.py`, `skill_pipeline/source/fetch.py`
  - Environment variables: `PIPELINE_SEC_IDENTITY`, `SEC_IDENTITY`, `EDGAR_IDENTITY` (for EDGAR identity)
  - Known issue: v6 deprecation warnings in live fetch path; pinning/capping before breaking release is a follow-up risk

**Infrastructure:**
- openpyxl 3.1+ - Excel workbook reading/writing for diagnostic and benchmark reports
  - Used by: Post-export reconciliation and quality reporting (not core pipeline)

## Configuration

**Environment:**
SEC identity configuration (required for live EDGAR access):
- `PIPELINE_SEC_IDENTITY` (preferred)
- `SEC_IDENTITY` (fallback)
- `EDGAR_IDENTITY` (fallback)

LLM provider configuration (used by external skills, not CLI):
- `BIDS_LLM_PROVIDER` - default: `anthropic`, accepts: `anthropic|openai`
- `BIDS_LLM_MODEL` - override model ID
- `BIDS_LLM_REASONING_EFFORT` - provider-specific reasoning effort
- `BIDS_LLM_STRUCTURED_MODE` - prompted_json|provider_native|auto

API key configuration (used by external skills):
- `ANTHROPIC_API_KEY` - required for Anthropic provider
- `OPENAI_API_KEY` - required for OpenAI provider

Local-only paths (should be in `.gitignore`):
- `.venv/` - Virtual environment
- `.env*` - Local environment files (never committed)
- `.agents/` - Skill execution state
- `.claude/settings.json` - Local IDE settings

**Build:**
- `pyproject.toml` - Package metadata, dependencies, version, CLI entry point
  - Entrypoint: `skill-pipeline = skill_pipeline.cli:main`
  - Version: 0.1.0

## Platform Requirements

**Development:**
- Python 3.11+
- pip with setuptools 69+
- bash (Unix shell - Windows users run via WSL or Git Bash)
- No database or external service required for deterministic stages

**Production:**
- Python 3.11+ runtime
- EDGAR identity configured for live filing fetch (`raw-fetch` stage)
- API keys for LLM providers (if using agent-based extraction/enrichment)
- Local filesystem for artifact storage (`data/` and `raw/` directories)

---

*Stack analysis: 2026-03-27*
