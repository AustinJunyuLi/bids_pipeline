# Phase 14: Derivation Engine - Research

**Date:** 2026-03-31
**Status:** Complete

## Findings

### 1. The architecture wants a rule catalog, not a monolithic port of enrich-core

- `ARCHITECTURE.md` maps v1 helpers to explicit v2 rule families.
- `PITFALLS.md` explicitly warns that rule dependencies become opaque if derive
  is built as a single interleaved pass.
- The safest implementation is a new `derive.py` module with named rule
  functions and a fixed execution order.

### 2. The current v2 model surface still has two Phase 14 alignment gaps

- `models_v2.py` already supports the observation graph and Phase 13 coverage
  provenance, but the derived row surface is still more spreadsheet-shaped than
  graph-shaped.
- `AnalystRowRecord` still centers bidder/date/value export columns rather than
  `subject_ref`, `row_count`, date/terms, and phase linkage.
- Several literal observation fields that Phase 14 rules want are still thin or
  absent, which creates pressure to derive from `summary` text.
- Phase 14 should therefore allow an additive schema-alignment pass before the
  derive rules harden the wrong contract.

### 3. Phase derivation can collapse round announcement/deadline into one source observation

- v1 round pairing depends on two separate event types (`*_ann` and `*`).
- v2 solicitation observations already carry both the request date and
  `due_date`.
- That means one `SolicitationObservation` can produce a `ProcessPhaseRecord`
  plus two analyst rows during compilation, without reconstructing fake
  deadline observations.

### 4. Exit derivation needs explicit active-party state, but only at a lightweight level

- `EXIT-03` and `EXIT-04` need to know who is still active when a subset is
  selected or a winner emerges.
- The v2 observation graph does not yet carry a dedicated state machine table.
- Phase 14 can therefore derive transitions from phase participants, proposal
  subjects, and prior explicit exits, then layer judgments where the graph does
  not support a deterministic answer.

### 5. Cash-regime derivation is phase-local and should avoid v1's sparse override pattern

- `CASH-01` is explicit proposal-level evidence.
- `CASH-03` is a phase inference rule over typed proposals.
- `CASH-02` is schema-constrained because `AgreementObservation` does not carry
  a terms payload. A lightweight filing-grounded heuristic on merger-agreement
  summary text is the only available Phase 14 path unless the model changes.

## Recommended Plan Shape

### Plan 14-01
- Additive `models_v2.py` schema alignment for rule-relevant literal fields and
  graph-linked derived record contracts
- Add `derive.py`
- Implement validation gating and rule registry
- Implement phase derivation, cash regimes, and judgments

### Plan 14-02
- Implement lifecycle transitions and analyst-row compilation
- Keep analyst rows graph-linked and defer anonymous slot expansion to Phase 15
- Reuse bidder-type formatting semantics from `db_export.py` only where they do
  not force export policy into the core derivation artifact
- Add focused rule tests

### Plan 14-03
- Add CLI wiring, derive-log writing, parser coverage, and repo-memory updates
- Verify the full synthetic derivation bundle

## Risks

- If the derive stage tries to infer too much bidder state without judgments, it
  will silently recreate the v1 ambiguity problem on a different schema.
- If analyst-row compilation bakes benchmark/export formatting into the core row
  contract now, Phase 15 loses the clean boundary GPT Pro recommended.
- If anonymous slot expansion enters the core derivation artifact, it conflicts
  with the export-only benchmark-expanded surface already reserved in the
  roadmap and requirements.
- If Phase 14 blocks on a nonexistent v2 verify contract, the pipeline stalls
  despite a complete Phase 13 validation surface.
