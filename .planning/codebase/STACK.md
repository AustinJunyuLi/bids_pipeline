# Technology Stack

**Analysis Date:** 2026-03-26

## Languages

**Primary:**
- Python `>=3.11` is the only application language declared in `pyproject.toml`, and the installed package surface is the `skill_pipeline/` package exposed by `skill-pipeline = "skill_pipeline.cli:main"` in `pyproject.toml`.

**Secondary:**
- Markdown documents the workflow and agent surfaces in `CLAUDE.md`, `docs/design.md`, `docs/workflow-contract.md`, and `.claude/skills/*.md`.
- JSON, JSONL, and CSV are first-class artifact formats in `skill_pipeline/paths.py`, with concrete outputs such as `raw/<slug>/discovery.json`, `data/deals/<slug>/source/chronology_blocks.jsonl`, and `data/skill/<slug>/export/deal_events.csv`.
- TOML and INI configure packaging and tests in `pyproject.toml` and `pytest.ini`.
- Plain SEC filing text is frozen under `raw/<slug>/filings/*.txt` by `skill_pipeline/raw/fetch.py`.

## Runtime

**Environment:**
- The active runtime is a local filesystem-backed CLI, not a service process. Command routing lives in `skill_pipeline/cli.py`.
- The repo pins only a minimum interpreter version, `requires-python = ">=3.11"`, in `pyproject.toml`; no `.python-version` is tracked at repo root.
- The pipeline version constant is `SKILL_PIPELINE_VERSION = "0.1.0"` in `skill_pipeline/config.py`.
- Deterministic stages run inside the Python package via `skill-pipeline` subcommands in `skill_pipeline/cli.py`; LLM stages are defined separately in `.claude/skills/README.md` and `.claude/skills/*.md`, then mirrored to `.codex/skills/` and `.cursor/skills/` by `scripts/sync_skill_mirrors.py`.

**Package Manager:**
- Editable installation via `pip install -e .` is the documented setup path in `CLAUDE.md`.
- Packaging uses `setuptools.build_meta` with build requirements `setuptools>=69` and `wheel` in `pyproject.toml`.
- Runtime dependency declarations are duplicated in `pyproject.toml` and `requirements.txt`.
- Lockfile: not tracked. No `poetry.lock`, `uv.lock`, or `Pipfile.lock` was found beside `pyproject.toml`.

## Frameworks

**Core:**
- `argparse` drives the CLI surface in `skill_pipeline/cli.py`.
- `pydantic>=2.0` defines and validates raw, canonical, verification, coverage, and enrichment schemas in `skill_pipeline/models.py` and `skill_pipeline/pipeline_models/*.py`.
- `edgartools>=5.23` provides SEC identity and accession-based filing retrieval in `skill_pipeline/raw/stage.py` and `skill_pipeline/raw/fetch.py`.
- The repo’s LLM workflow layer is skill-driven rather than implemented as Python commands: the active skill inventory is documented in `.claude/skills/README.md`, with stage contracts in `.claude/skills/deal-agent/SKILL.md`, `.claude/skills/extract-deal/SKILL.md`, `.claude/skills/verify-extraction/SKILL.md`, `.claude/skills/enrich-deal/SKILL.md`, `.claude/skills/export-csv/SKILL.md`, and `.claude/skills/reconcile-alex/SKILL.md`.

**Testing:**
- `pytest>=8.0` is the only tracked test runner in `pyproject.toml`.
- Test discovery is configured in `pytest.ini`, and the suite lives under `tests/`.

**Build/Dev:**
- `setuptools` is the only tracked packaging tool in `pyproject.toml`.
- Skill mirror maintenance is implemented by `scripts/sync_skill_mirrors.py`.
- No formatter or linter config files are tracked alongside `pyproject.toml` and `pytest.ini`.

## Key Dependencies

**Critical:**
- `pydantic>=2.0` in `pyproject.toml` underpins strict artifact schemas in `skill_pipeline/models.py` and `skill_pipeline/pipeline_models/source.py`.
- `edgartools>=5.23` in `pyproject.toml` is required for live SEC access in `skill_pipeline/raw/stage.py` and `skill_pipeline/raw/fetch.py`.
- `pytest>=8.0` in `pyproject.toml` backs regression coverage in `tests/test_skill_raw_stage.py`, `tests/test_skill_preprocess_source.py`, `tests/test_skill_verify.py`, and related stage tests.

**Infrastructure:**
- `anthropic>=0.49` is declared in `pyproject.toml`, matching the Anthropic provider surface documented in `CLAUDE.md`; no in-repo Anthropic client calls are present under `skill_pipeline/`.
- `openpyxl>=3.1` is declared in `pyproject.toml` and is referenced in the post-export benchmark workflow in `.claude/skills/reconcile-alex/SKILL.md` to read `example/deal_details_Alex_2026.xlsx`.
- An `openai` Python dependency is not tracked in `pyproject.toml` or `requirements.txt`; OpenAI appears only as an operational provider option in `CLAUDE.md`.

## Configuration

**Environment:**
- Live SEC access requires an identity string. `skill_pipeline/raw/stage.py` checks `PIPELINE_SEC_IDENTITY`, then `SEC_IDENTITY`, then `EDGAR_IDENTITY`, and raises if none is set.
- Repo-level LLM configuration is documented in `CLAUDE.md`: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `BIDS_LLM_PROVIDER`, `BIDS_LLM_MODEL`, `BIDS_LLM_REASONING_EFFORT`, and `BIDS_LLM_STRUCTURED_MODE`.
- Local secret material is expected through environment variables or the ignored `.env.local` path listed in `.gitignore`; no tracked secret template file is present.

**Build:**
- `pyproject.toml` is the authoritative package manifest.
- `requirements.txt` duplicates the runtime dependency list.
- `pytest.ini` configures the test root and default `pytest` options.
- `.gitattributes` enforces `LF` for tracked text files and marks `*.sqlite` as binary.
- `docs/workflow-contract.md` is the canonical stage inventory for the hybrid deterministic/skill runtime described in `CLAUDE.md`.

## Platform Requirements

**Development:**
- Python `>=3.11` is required by `pyproject.toml`.
- Network access to SEC EDGAR is required for `skill-pipeline raw-fetch` in `skill_pipeline/cli.py` and `skill_pipeline/raw/stage.py`.
- Write access to the working tree is required because artifact locations are hard-coded in `skill_pipeline/paths.py` under `raw/`, `data/deals/`, and `data/skill/`.

**Production:**
- No deployed production target is tracked in the repo. There is no `Dockerfile`, `.github/workflows/`, or server entrypoint beside `skill_pipeline/cli.py`.
- The execution target is the local repository filesystem, with outputs persisted under `raw/<slug>/`, `data/deals/<slug>/`, and `data/skill/<slug>/`.

---

*Stack analysis: 2026-03-26*
