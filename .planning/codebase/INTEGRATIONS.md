# External Integrations

**Analysis Date:** 2026-03-26

## APIs & External Services

**SEC EDGAR:**
- The only live network integration implemented in the Python package is SEC EDGAR retrieval for raw filings in `skill_pipeline/raw/stage.py` and `skill_pipeline/raw/fetch.py`.
  - SDK/Client: `edgartools` from `pyproject.toml`, using `edgar.set_identity` in `skill_pipeline/raw/stage.py` and `edgar.get_by_accession_number` in `skill_pipeline/raw/fetch.py`.
  - Auth: `PIPELINE_SEC_IDENTITY`, `SEC_IDENTITY`, or `EDGAR_IDENTITY`, enforced in `skill_pipeline/raw/stage.py`.
  - Request scope: accession-based fetch only. `skill_pipeline/raw/discover.py` requires a standard `sec.gov` or `www.sec.gov` Archives URL from `data/seeds.csv`, and `skill_pipeline/raw/fetch.py` intentionally fails instead of falling back to page scraping.
- Downstream stages do not call EDGAR again. `skill_pipeline/preprocess/source.py` and later deterministic stages read frozen local filings from `raw/<slug>/`.

**LLM skill hosts / provider-backed stages:**
- The hybrid workflow includes six tracked agent skills in `.claude/skills/README.md`: `deal-agent`, `extract-deal`, `verify-extraction`, `enrich-deal`, `export-csv`, and `reconcile-alex`.
  - SDK/Client: not implemented inside `skill_pipeline/`; these stages are defined as skill contracts in `.claude/skills/*.md` and mirrored into `.codex/skills/` and `.cursor/skills/` by `scripts/sync_skill_mirrors.py`.
  - Auth: `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` are documented in `CLAUDE.md`.
  - Runtime selection: `BIDS_LLM_PROVIDER`, `BIDS_LLM_MODEL`, `BIDS_LLM_REASONING_EFFORT`, and `BIDS_LLM_STRUCTURED_MODE` are documented in `CLAUDE.md`.
- The Python package declares `anthropic>=0.49` in `pyproject.toml`, but no tracked `openai` dependency exists in `pyproject.toml` or `requirements.txt`. OpenAI support is therefore an external skill-runtime concern rather than a Python-package integration.

## Data Storage

**Databases:**
- Not detected in the active runtime. No database client or connection configuration is referenced in `skill_pipeline/cli.py`, `skill_pipeline/paths.py`, or `pyproject.toml`.
  - Connection: Not applicable.
  - Client: Not applicable.
- `.gitattributes` marks `*.sqlite` as binary, but no SQLite-backed runtime path is implemented in `skill_pipeline/`.

**File Storage:**
- Local filesystem only. `skill_pipeline/paths.py` hard-codes the working data layout.
  - `raw/<slug>/` stores immutable SEC filings plus `discovery.json` and `document_registry.json`.
  - `data/deals/<slug>/source/` stores chronology and evidence preprocessing outputs.
  - `data/skill/<slug>/` stores extract, check, verify, coverage, enrich, canonicalize, export, and reconcile artifacts.
- `skill_pipeline/raw/fetch.py` enforces immutable write semantics for raw filing text under `raw/<slug>/filings/*.txt`.
- `skill_pipeline/preprocess/source.py` materializes source-stage copies of the selected filing under `data/deals/<slug>/source/filings/`.

**Caching:**
- None detected in `skill_pipeline/`, `pyproject.toml`, or `docs/workflow-contract.md`.

**External file inputs:**
- `data/seeds.csv` is the required input registry for deal metadata and seed SEC URLs, referenced by `skill_pipeline/cli.py`, `skill_pipeline/paths.py`, and `skill_pipeline/seeds.py`.
- `example/deal_details_Alex_2026.xlsx` is a post-export benchmark input used only by `.claude/skills/reconcile-alex/SKILL.md` via `openpyxl`; `docs/workflow-contract.md` and `.claude/skills/reconcile-alex/SKILL.md` both keep it outside the generation-time path.

## Authentication & Identity

**Auth Provider:**
- No user authentication or identity provider integration is present in `skill_pipeline/cli.py` or `skill_pipeline/models.py`.
  - Implementation: service identities and API keys are configured through environment variables, not user sessions or OAuth flows.
- SEC access requires a caller identity string in `skill_pipeline/raw/stage.py`.
- LLM providers use API keys documented in `CLAUDE.md`; the repo does not include a tracked secret manager configuration.

## Monitoring & Observability

**Error Tracking:**
- None detected. There is no Sentry, Honeycomb, Datadog, or similar integration in `pyproject.toml`, `skill_pipeline/`, or `.github/`.

**Logs:**
- The pipeline uses artifact-based observability rather than hosted logging.
  - Structural checks write `data/skill/<slug>/check/check_report.json` from `skill_pipeline/check.py`.
  - Verification writes `data/skill/<slug>/verify/verification_log.json` and `data/skill/<slug>/verify/verification_findings.json` from `skill_pipeline/verify.py` and `skill_pipeline/paths.py`.
  - Coverage writes `data/skill/<slug>/coverage/coverage_findings.json` and `data/skill/<slug>/coverage/coverage_summary.json` from `skill_pipeline/coverage.py` and `skill_pipeline/paths.py`.
  - Enrichment writes `data/skill/<slug>/enrich/deterministic_enrichment.json` and `data/skill/<slug>/enrich/enrichment.json`.
  - Export writes `data/skill/<slug>/export/deal_events.csv`.

## CI/CD & Deployment

**Hosting:**
- Not applicable. No deployment target or hosting configuration is tracked beside the local CLI in `skill_pipeline/cli.py`.

**CI Pipeline:**
- Not detected. No `.github/workflows/` directory or other tracked CI configuration is present in the repository root.
- Consistency checks that do exist are local commands from `CLAUDE.md`, including `pytest -q` and `python scripts/sync_skill_mirrors.py --check`.

## Environment Configuration

**Required env vars:**
- `PIPELINE_SEC_IDENTITY` or `SEC_IDENTITY` or `EDGAR_IDENTITY` for `skill-pipeline raw-fetch` in `skill_pipeline/raw/stage.py`.
- `ANTHROPIC_API_KEY` for Anthropic-backed skill runs described in `CLAUDE.md`.
- `OPENAI_API_KEY` for OpenAI-backed skill runs described in `CLAUDE.md`.
- `BIDS_LLM_PROVIDER`, `BIDS_LLM_MODEL`, `BIDS_LLM_REASONING_EFFORT`, and `BIDS_LLM_STRUCTURED_MODE` for provider selection and structured-output behavior described in `CLAUDE.md`.

**Secrets location:**
- Environment variables at runtime.
- Optional local file path `.env.local` is ignored in `.gitignore`.
- No tracked `.env.example`, vault configuration, or repository-level secret bootstrap script is present.

## Webhooks & Callbacks

**Incoming:**
- None. There are no HTTP routes, webhook receivers, or callback handlers in `skill_pipeline/cli.py` or `skill_pipeline/`.

**Outgoing:**
- SEC EDGAR calls originate from `skill_pipeline/raw/stage.py` and `skill_pipeline/raw/fetch.py` through `edgartools`.
- Provider-backed LLM API calls are externalized to the skill hosts represented by `.claude/skills/`, `.codex/skills/`, and `.cursor/skills/`; no outgoing webhook client is implemented in `skill_pipeline/`.

---

*Integration audit: 2026-03-26*
