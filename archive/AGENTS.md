# Bids Pipeline Agent Guide

## Project Role

This repository is an M&A deal-extraction project built around SEC filing
chronologies.

- `deal-extraction-skills/` is the reference workflow and artifact contract.
- `pipeline/` is the current Python implementation attempt.
- `docs/CollectionInstructions_Alex_2026.qmd` is the methodological source for
  taxonomy and collection rules, not a factual source for any deal.

## Core Principles

- Treat the filing text as the only factual source of truth.
- Every extracted fact should remain traceable to
  `source_accession_number` plus verbatim `source_text`.
- Keep facts separate from judgments. Proposal events come first; bid
  classification, formal boundary, and initiation are later enrichment steps.
- Frozen filing `.txt` snapshots are immutable once created.
- Prefer deterministic Python policy logic over hidden prompt-only logic.

## Current Architecture

- `pipeline/stage1_sourcing.py`: deterministic sourcing, freezing, chronology
  localization
- `pipeline/providers.py`: abstract provider interface for actor extraction,
  event extraction, count reconciliation, and deal metadata
- `pipeline/stage3_enrichment.py`: deterministic cycle segmentation and
  proposal classification
- `pipeline/stage3_audit.py`: deterministic quote verification and structural
  audit
- `pipeline/stage4_assembly.py`: reviewer row assembly and global `master.csv`
  rebuild
- `pipeline/orchestrator.py`: resume logic, hashing, SQLite state, stage order

## Known Gaps

- There is no concrete `Provider` implementation in this repo.
- There is no CLI or packaging scaffold yet.
- Supplementary filing handling is not implemented to the same degree as the
  reference skill workflow.
- `actors_extended.jsonl` is part of the reference design, but downstream
  support is incomplete.

## Agent Working Rules

- When changing schemas or stage outputs, preserve compatibility with the
  reference artifacts unless the user explicitly wants a redesign.
- Do not collapse range bids into a single scalar unless the output contract
  explicitly requires it.
- Do not classify bids during extraction-stage logic.
- Do not use Alex's notes or spreadsheets as factual evidence for deal data.
- Prefer small, explicit validations at stage boundaries.
- If implementing missing functionality, favor making stage behavior explicit in
  Python rather than burying required behavior inside a provider prompt.

## Practical Notes

- The repo root may still be named `bids_data`; the intended GitHub repository
  name is `bids_pipeline`.
- Project-local Cursor skill wrappers live in `.cursor/skills/`; treat
  `deal-extraction-skills/skills/` as the canonical source and the wrappers as
  discovery shims only.
- Avoid destructive cleanup of raw or frozen source artifacts.
