# External Integrations

**Analysis Date:** 2026-03-27

## APIs & External Services

**SEC EDGAR API:**
- SEC Electronic Data Gathering (filing database)
  - SDK/Client: `edgartools>=5.23`
  - Auth: Identity string (email/user-agent) via `PIPELINE_SEC_IDENTITY`, `SEC_IDENTITY`, or `EDGAR_IDENTITY` env var
  - Usage: `skill_pipeline/raw/fetch.py`, `skill_pipeline/raw/stage.py`, `skill_pipeline/source/fetch.py`
  - Entry points: `from edgar import get_by_accession_number`, `from edgar import set_identity`
  - Responsibility: Fetches DEFM14A, PREM14A, SC 14D-9, and other M&A filing text from SEC Archives
  - Lifecycle: `raw-fetch` stage queries by accession number; text files frozen immutably to `raw/<slug>/filings/`

**LLM Providers (External Skills Only):**
- Anthropic Claude API
  - SDK/Client: `anthropic>=0.49`
  - Auth: `ANTHROPIC_API_KEY` env var
  - Usage: **Not used by `skill_pipeline` CLI directly**. Used by agent-based `/extract-deal`, `/verify-extraction`, `/enrich-deal` skills
  - Config: `BIDS_LLM_PROVIDER=anthropic` (default), `BIDS_LLM_MODEL`, `BIDS_LLM_REASONING_EFFORT`, `BIDS_LLM_STRUCTURED_MODE`

- OpenAI API (gpt-4, gpt-5.4)
  - SDK/Client: OpenAI Python client (not in direct dependencies, used by agent skills)
  - Auth: `OPENAI_API_KEY` env var
  - Usage: Alternative LLM provider when `BIDS_LLM_PROVIDER=openai`
  - Config: Same `BIDS_LLM_*` env vars route to OpenAI client

## Data Storage

**Databases:**
- None - Project uses local filesystem only

**File Storage:**
- Local filesystem only
  - Input: `data/seeds.csv` (deal metadata and primary filing URLs)
  - Raw filings: `raw/<slug>/filings/*.txt` (immutable frozen filing text)
  - Discovery metadata: `raw/<slug>/discovery.json`, `raw/<slug>/document_registry.json`
  - Preprocessed source: `data/deals/<slug>/source/{chronology_blocks,evidence_items}.jsonl`
  - Extract artifacts: `data/skill/<slug>/extract/{actors_raw,events_raw}.json`, `spans.json`
  - Deterministic outputs: `data/skill/<slug>/{check,verify,coverage,enrich,export}/*.json`
  - CSV export: `data/skill/<slug>/export/deal_events.csv`

**Caching:**
- None detected

## Authentication & Identity

**SEC EDGAR Identity:**
- Custom identity string (email/user-agent format)
  - Implementation: `skill_pipeline/raw/stage.py` calls `edgar.set_identity()` at runtime
  - Required env var: `PIPELINE_SEC_IDENTITY` (preferred), `SEC_IDENTITY` (fallback), or `EDGAR_IDENTITY` (fallback)
  - Enforced on: `raw-fetch` stage; raises `ValueError` if not provided

**LLM Provider Auth:**
- No auth handled by `skill_pipeline` CLI (external skills manage credentials)
- Keys passed via environment variables only (never hardcoded)

## Monitoring & Observability

**Error Tracking:**
- None detected - Project uses exception-based fail-fast pattern
- Errors logged to stderr and propagated to caller

**Logs:**
- Standard Python logging via `logging` module (not configured in CLI, caller controls output)
- Deterministic gates (`check`, `verify`, `coverage`) produce JSON finding logs:
  - `data/skill/<slug>/check/check_report.json`
  - `data/skill/<slug>/verify/verification_log.json`, `verification_findings.json`
  - `data/skill/<slug>/coverage/coverage_findings.json`, `coverage_summary.json`
  - `data/skill/<slug>/canonicalize/canonicalize_log.json`

## CI/CD & Deployment

**Hosting:**
- None - Designed for local execution or agent-orchestrated runs

**CI Pipeline:**
- None detected - Project includes `pytest.ini` for local test runs
- Tests run via `pytest -q` (quiet mode with summary)
- Entry command: `skill-pipeline` CLI with subcommands (raw-fetch, preprocess-source, canonicalize, check, verify, coverage, enrich-core, deal-agent)

## Environment Configuration

**Required env vars:**
- `PIPELINE_SEC_IDENTITY` (or `SEC_IDENTITY`, `EDGAR_IDENTITY`) - EDGAR API identity for `raw-fetch`
- `ANTHROPIC_API_KEY` - If using Anthropic LLM in agent skills
- `OPENAI_API_KEY` - If using OpenAI LLM in agent skills

**Optional env vars:**
- `BIDS_LLM_PROVIDER` - LLM provider (default: `anthropic`)
- `BIDS_LLM_MODEL` - Override model ID
- `BIDS_LLM_REASONING_EFFORT` - Extended thinking budget
- `BIDS_LLM_STRUCTURED_MODE` - JSON output mode

**Secrets location:**
- Environment variables only (no `.env` file is processed by CLI)
- `.env*` files should be local-only and listed in `.gitignore`
- Never commit `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `PIPELINE_SEC_IDENTITY` values

## Webhooks & Callbacks

**Incoming:**
- None - Pipeline is pull-driven (fetches filings from SEC on demand)

**Outgoing:**
- None - Pipeline outputs are files only (JSON, JSONL, CSV)

---

*Integration audit: 2026-03-27*
