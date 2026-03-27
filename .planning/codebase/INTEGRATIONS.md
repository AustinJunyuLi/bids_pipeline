# External Integrations

**Analysis Date:** 2026-03-27

## APIs & External Services

**SEC EDGAR API:**
- SEC Electronic Data Gathering (filing database)
  - SDK/Client: `edgartools>=5.23`
  - Auth: Identity string (email/user-agent) via `PIPELINE_SEC_IDENTITY`,
    `SEC_IDENTITY`, or `EDGAR_IDENTITY`
  - Usage: `skill_pipeline/raw/fetch.py`, `skill_pipeline/raw/stage.py`,
    `skill_pipeline/source/fetch.py`
  - Entry points: `from edgar import get_by_accession_number`,
    `from edgar import set_identity`
  - Responsibility: Fetches DEFM14A, PREM14A, SC 14D-9, and other M&A filing
    text from SEC Archives
  - Lifecycle: `raw-fetch` queries by accession number; text files freeze
    immutably to `raw/<slug>/filings/`

**Local-Agent Execution Environment:**
- Extraction, repair, interpretive enrichment, and CSV export are executed by
  local agents following `.claude/skills/`
- No first-class OpenAI, Anthropic, or other provider integration was verified
  inside `skill_pipeline`
- Provider-specific credentials or SDK choices, if any, belong to the operator's
  local agent setup, not to the Python package contract

## Data Storage

**Databases:**
- None in the current runtime

**File Storage:**
- Local filesystem only
  - Input: `data/seeds.csv`
  - Raw filings: `raw/<slug>/filings/*.txt`
  - Discovery metadata: `raw/<slug>/discovery.json`,
    `raw/<slug>/document_registry.json`
  - Preprocessed source:
    `data/deals/<slug>/source/{chronology_selection,chronology}.json`,
    `chronology_blocks.jsonl`, `evidence_items.jsonl`, `filings/*`
  - Extract artifacts:
    `data/skill/<slug>/extract/{actors_raw,events_raw}.json`, `spans.json`
  - Deterministic outputs:
    `data/skill/<slug>/{check,verify,coverage,enrich,canonicalize}/*.json`
  - CSV export: `data/skill/<slug>/export/deal_events.csv`

**Caching:**
- No repo-level caching layer detected in the current runtime

## Authentication & Identity

**SEC EDGAR Identity:**
- Custom identity string (email/user-agent format)
  - Implementation: `skill_pipeline/raw/stage.py` calls `edgar.set_identity()`
  - Required env var: `PIPELINE_SEC_IDENTITY` (preferred), `SEC_IDENTITY`
    (fallback), or `EDGAR_IDENTITY` (fallback)
  - Enforced on: `raw-fetch`; raises `ValueError` if not provided

**Local-Agent Credentials:**
- No provider auth is handled by `skill_pipeline`
- If a chosen local-agent tool uses provider credentials, those credentials are
  external to the verified Python runtime contract

## Monitoring & Observability

**Error Tracking:**
- None detected; project uses exception-based fail-fast behavior

**Logs:**
- Standard Python logging via `logging`
- Deterministic stages emit JSON artifacts:
  - `data/skill/<slug>/check/check_report.json`
  - `data/skill/<slug>/verify/verification_log.json`,
    `verification_findings.json`
  - `data/skill/<slug>/coverage/coverage_findings.json`,
    `coverage_summary.json`
  - `data/skill/<slug>/canonicalize/canonicalize_log.json`

## CI/CD & Deployment

**Hosting:**
- None; designed for local execution or local-agent orchestrated runs

**CI Pipeline:**
- None detected
- Tests run via `pytest -q`
- Entry command: `skill-pipeline` CLI with subcommands:
  `source-discover`, `raw-fetch`, `preprocess-source`, `canonicalize`,
  `check`, `verify`, `coverage`, `enrich-core`, `deal-agent`

## Environment Configuration

**Repo-required env vars:**
- `PIPELINE_SEC_IDENTITY` (or `SEC_IDENTITY`, `EDGAR_IDENTITY`) for
  `raw-fetch`

**No additional repo-required LLM env vars were validated.**

If a local-agent tool uses provider credentials, treat those as operator-local
configuration rather than repo contract.

**Secrets location:**
- Environment variables only
- `.env*` files should remain local-only and ignored
- Never commit EDGAR identity values or any local-agent provider credentials

## Webhooks & Callbacks

**Incoming:**
- None; pipeline is pull-driven

**Outgoing:**
- None; pipeline outputs are files only

---

*Integration audit: 2026-03-27; hardened to match repo-truth runtime split*
