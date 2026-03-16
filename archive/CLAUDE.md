# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

M&A deal-extraction pipeline that reads SEC EDGAR proxy filings (DEFM14A, PREM14A, etc.), extracts structured chronologies of auction events from "Background of the Merger" narratives, and outputs evidence-backed flat CSV rows for human review.

The local directory is `bids_data`; the intended GitHub repository name is `bids_pipeline`.

## Architecture

### Two Layers

1. **Reference skills** (`.claude/skills/`, also in `deal-extraction-skills/skills/`): 10 agent-driven extraction skills that define the artifact contracts, schemas, and domain logic. These are the canonical specification.
2. **Python pipeline** (`pipeline/`): A partial implementation that maps the skill workflow into deterministic Python stages. **There is no concrete `Provider` implementation yet** — stage 2 (LLM-backed extraction) cannot run end-to-end.

### Pipeline Stages

```
Seed CSV → Stage 1 (sourcing) → Stage 2 (extraction) → Stage 3 (enrichment)
         → Stage 3 audit → Stage 4 (assembly) → master_rows.csv
```

| Module | Stage | What It Does | LLM Required |
|--------|-------|-------------|--------------|
| `stage1_sourcing.py` | 1 | EDGAR search, filing download, HTML→text freeze, chronology bookmark | No |
| `providers.py` | 2 | Abstract interface for actor/event extraction, count reconciliation, deal metadata | Yes (abstract) |
| `stage3_enrichment.py` | 3 | Deterministic cycle segmentation, bid classification, formal boundary | No |
| `stage3_audit.py` | 3_audit | Quote verification, structural audit, census | No |
| `stage4_assembly.py` | 4 | 47-column review row assembly, master.csv rebuild | No |
| `orchestrator.py` | All | Resume logic, SHA-256 hashing, SQLite state tracking, cost accounting | - |
| `schemas.py` | All | Pydantic models for every artifact (~50 models) | - |

### Data Flow

Per-deal directory under `Data/deals/<slug>/`:
- `source/` — source_selection.json, corpus_manifest.json, chronology_bookmark.json, filings/*.txt
- `extraction/` — actors.jsonl, events.jsonl, event_actor_links.jsonl, deal.json, census.json, decisions.jsonl
- `enrichment/` — process_cycles.jsonl, judgments.jsonl
- `review/` — review_status.json, overrides.csv
- `master_rows.csv` — final 47-column output

Global: `Data/views/master.csv` concatenates all deals.

### Dependencies

Python 3.13+, Pydantic v2, requests, BeautifulSoup4. No packaging scaffold (no pyproject.toml, requirements.txt, or CLI entry point yet).

## Domain Rules

- **Filing text is the single source of truth.** Every fact must trace to `source_accession_number` + verbatim `source_text`.
- **Facts before judgments.** Proposals are raw events during extraction (stage 2). Classification as formal/informal happens in stage 3 enrichment, never during extraction.
- **Frozen text is immutable.** `.txt` files in `source/filings/` are never modified after creation.
- **Do not collapse range bids** into a single scalar unless the output contract explicitly requires it.
- **Do not use `docs/CollectionInstructions_Alex_2026.qmd`** as factual evidence for any deal — it defines taxonomy and methodology only.
- **Deterministic Python over prompt logic.** Policy rules (classification, cycle segmentation, audits) belong in Python, not hidden in LLM prompts.

## Known Gaps

- No concrete `Provider` implementation (stage 2 is abstract-only)
- No CLI entry point or packaging
- Supplementary filing handling is incomplete
- `actors_extended.jsonl` downstream integration is incomplete
