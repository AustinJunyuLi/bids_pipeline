# CHANGELOG

## 2026-03-16 — Pipeline v3 implementation pass

### Added

- Full v3 design document at `docs/plans/2026-03-16-pipeline-design-v3.md`
- Enhanced preprocess evidence scan across all frozen filings
- `EvidenceItem` source model and `evidence_items.jsonl` artifact
- Cross-filing supplementary snippet derivation from evidence items
- Extraction orchestration modules:
  - `pipeline/extract/actors.py`
  - `pipeline/extract/events.py`
  - `pipeline/extract/merge.py`
  - `pipeline/extract/recovery.py`
  - `pipeline/extract/utils.py`
- Reconciliation / QA modules:
  - `pipeline/qa/rules.py`
  - `pipeline/qa/completeness.py`
  - `pipeline/qa/review.py`
- Enrichment modules:
  - `pipeline/enrich/classify.py`
  - `pipeline/enrich/cycles.py`
  - `pipeline/enrich/features.py`
- Export modules:
  - `pipeline/export/flatten.py`
  - `pipeline/export/alex_compat.py`
  - `pipeline/export/review_csv.py`
- Reference validation modules:
  - `pipeline/validate/reference.py`
  - `pipeline/validate/metrics.py`
- New tests for source evidence, extraction orchestration, QA, enrichment, export, and validation

### Changed

- `pipeline/preprocess/source.py`
  - now scans all documents, not just the selected primary
  - writes evidence items and materialized filing copies
  - filters supplementary snippets to non-primary cross-filing evidence
- `pipeline/source/locate.py`
  - confidence now separates ambiguity risk from coverage adequacy
- `pipeline/source/supplementary.py`
  - now derives snippets from deterministic evidence items
- `pipeline/llm/prompts.py`
  - user messages now include a cross-filing evidence appendix
- `pipeline/llm/schemas.py`
  - evidence refs now allow `block_id` or `evidence_id`
- `pipeline/llm/anthropic_backend.py`
  - import is now optional until a live client is actually needed
- `pipeline/raw/fetch.py`, `pipeline/source/fetch.py`, `pipeline/raw/stage.py`
  - `edgar` import is now optional until live networked fetch is actually needed
- `pipeline/orchestrator.py`
  - added batch entry points for extract, QA, enrich, export, and validation
- `pipeline/cli.py`
  - now executes all implemented stages and records stage/artifact/LLM usage state
- `pipeline/models/__init__.py`
  - exports new source evidence models

### Test status

- `pytest` passes from repo root with mocked LLM tests and no API key required.
