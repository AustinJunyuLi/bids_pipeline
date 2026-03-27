# Technology Stack

**Analysis Date:** 2026-03-27

## Languages

**Primary:**
- Python 3.11+ for runtime code, CLI, data processing, and tests

## Runtime

**Environment:**
- Python 3.11 or later (`pyproject.toml`)

**Package Manager:**
- pip installs the project from `pyproject.toml` with setuptools
- No lockfile is present

## Frameworks

**Core:**
- Pydantic 2.0+ for schema validation and data models
  - Used by: `skill_pipeline/models.py`,
    `skill_pipeline/pipeline_models/`
  - Pattern: strict model validation with `extra="forbid"`

**Testing:**
- pytest 8.0+ for regression tests
  - Config: `pytest.ini`
  - Discovery: `tests/test_*.py`
  - Command: `python -m pytest -q`

**Build/Dev:**
- setuptools 69+ for packaging and CLI entrypoint
- wheel for distribution packaging

## Key Dependencies

**Verified deterministic runtime dependencies:**
- `pydantic>=2.0`
  - Used by the schema and artifact model layer
- `edgartools>=5.23,<6.0`
  - Used by live SEC discovery and raw fetch
  - Runtime env vars: `PIPELINE_SEC_IDENTITY`, `SEC_IDENTITY`,
    `EDGAR_IDENTITY`
  - Capped below 6.0 to guard against breaking API changes
- `pytest>=8.0`
  - Used by the local test suite

**Other dependencies currently present in `pyproject.toml`:**
- `openpyxl>=3.1`
  - Used for workbook-facing or benchmark-adjacent tasks outside the core
    deterministic path

## Configuration

**Repo-verified environment variables:**
- `PIPELINE_SEC_IDENTITY` (preferred)
- `SEC_IDENTITY` (fallback)
- `EDGAR_IDENTITY` (fallback)

**No repo-verified provider-specific LLM env var contract exists.**

Provider-specific local-agent settings, if any, are external to the verified
Python package contract and should not be documented as core runtime facts.

**Local-only paths:**
- `.venv/`
- `.env*`
- `.agents/`
- `.claude/settings.json`

**Build metadata:**
- `pyproject.toml`
  - Entrypoint: `skill-pipeline = skill_pipeline.cli:main`
  - Version: `0.1.0`

## Platform Requirements

**Development:**
- Python 3.11+
- pip with setuptools 69+
- PowerShell or another shell capable of invoking the CLI and pytest
- No database or external service required for deterministic stages

**Production / real runs:**
- Python 3.11+ runtime
- EDGAR identity configured for live filing fetch
- Local filesystem for artifact storage under `raw/` and `data/`
- A local-agent execution environment if running non-deterministic extraction,
  repair, or export stages

---

*Stack analysis: 2026-03-27; hardened to match the current codebase contract*
