# External Integrations

**Analysis Date:** 2026-03-25

## APIs and External Services

**SEC EDGAR:**
- SEC filing retrieval is the primary external dependency
  - Client: `edgartools` via `skill_pipeline/raw/fetch.py` and `skill_pipeline/raw/stage.py`
  - Auth: `PIPELINE_SEC_IDENTITY`, `SEC_IDENTITY`, or `EDGAR_IDENTITY`
  - Method: accession-based retrieval only; the tracked runtime intentionally does not fall back to page scraping

**LLM providers for skill-driven stages:**
- Anthropic / OpenAI are repo-level integrations for the hybrid workflow described in `CLAUDE.md`
  - Usage surface: `.claude/skills/`, `.codex/skills/`, `.cursor/skills/`, and manual skill execution outside the deterministic CLI
  - Auth: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `BIDS_LLM_PROVIDER`, `BIDS_LLM_MODEL`, `BIDS_LLM_REASONING_EFFORT`
  - Scope: agent-driven extraction, repair, enrichment, export, and reconciliation stages; not the deterministic CLI modules in `skill_pipeline/`

## Data Storage

**Repository-backed storage:**
- `raw/<slug>/` - immutable frozen filing text plus discovery metadata
- `data/deals/<slug>/source/` - preprocessed chronology and evidence artifacts
- `data/skill/<slug>/` - extract, QA, enrichment, and export outputs
- No tracked relational database, cache, or object store exists in this repo

**Files and documents:**
- `docs/` stores design notes and local setup documentation
- `quality_reports/` stores tracked report artifacts
- `example/` and `diagnosis/` are local benchmark/reference materials and are explicitly post-export only

## Authentication and Identity

**SEC identity requirement:**
- Live fetches require a configured EDGAR identity before `raw-fetch` can run
- The code fails fast when no identity is configured rather than attempting anonymous fallback

**Local secrets handling:**
- `.env.local` is the expected local secret file and is ignored by `.gitignore`
- No tracked `.env.example` is present in the repo root

## Monitoring and Observability

**Application monitoring:**
- None tracked
- The pipeline relies on machine-readable artifact outputs such as `check_report.json`, `verification_log.json`, and `coverage_summary.json` instead of a hosted observability stack

**Logging:**
- Minimal console output from the CLI
- Most diagnostics are persisted as JSON artifacts under `data/skill/<slug>/`

## CI/CD and Deployment

**Hosting / deployment:**
- None tracked
- The repository is designed for local execution, not for a hosted environment

**CI pipeline:**
- No tracked GitHub Actions or other CI configuration is present in the repository
- Verification currently depends on local pytest runs and repo policy tests

## Environment Configuration

**Development:**
- Editable install via `pip install -e .`
- Optional `.env.local` for local secrets
- GitHub is the authoritative sync point between Windows and Linux machines

**Production-like execution:**
- Active deal inputs are stored in `data/seeds.csv`
- The repository itself is the working data volume for raw and generated artifacts

## Webhooks and Callbacks

- None tracked
- No incoming HTTP routes, outgoing webhooks, or callback handlers exist in the current package surface

---

*Integration audit: 2026-03-25*
*Update when adding or removing external services*
