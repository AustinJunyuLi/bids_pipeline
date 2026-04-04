# Requirements: v2.3 Structured Field Recovery

**Defined:** 2026-04-04
**Core Value:** Convert surface facts trapped in observation summaries into
structured fields through deterministic repair, prompt hardening, and semantic
completeness gates — raising field-level accuracy without weakening the
filing-grounded extraction contract.

## Milestone Basis

Grounded in:

- `diagnosis/gptpro/2026-04-04/round_1/response.md`

## v2.3 Requirements

### Repair Infrastructure

- [ ] **REPR-01**: Repair module (`skill_pipeline/repair/structured_fields_v2.py`) with fill-only semantics — populate missing/null fields, never overwrite populated values except harmless normalization (e.g., inverted range swap)
- [ ] **REPR-02**: Canonicalize integration wires repair into `canonicalize.py` in both quote-first and canonical modes, immediately before final Pydantic validation
- [ ] **REPR-03**: Dual-source parsing extracts cues from both observation `summary` and linked `evidence_span_ids` quote text, with confidence rules when sources agree, disagree, or only one yields a cue
- [ ] **REPR-04**: Subject-aware clause restriction limits extraction to clauses mentioning the proposal's `subject_ref` display name, canonical name, aliases, or cohort label — falls back to full text when no alias match exists

### Price Recovery

- [ ] **PRICE-01**: Single headline price extraction for `terms.per_share` using context-sensitive scoring — prefers "valued at", "best and final offer of", "offer of" phrases; penalizes component-level phrases ("stock price", "CVR", "strike price") and temporal qualifiers ("initially", "earlier")
- [ ] **PRICE-02**: Explicit range extraction for `terms.range_low` and `terms.range_high` — accepts only when clause contains share-level offer context, normalizes to Decimal, swaps if low > high, rejects component splits
- [ ] **PRICE-03**: Headline-vs-component disambiguation — mixed offers like "$21.50 including $19.00 cash and $2.50 CVR" populate `per_share=21.50` and `consideration_type=mixed` with null range fields; ranges mean only explicit intervals

### Consideration Type

- [ ] **CTYPE-01**: Deterministic `terms.consideration_type` recovery using explicit cues only — "all-cash"/"in cash" for cash, "stock-for-stock"/"exchange ratio" for stock, "cash and stock/CVR/equity" for mixed
- [ ] **CTYPE-02**: False-positive guards reject financing language ("equity commitment"), stock-price references ("trading price"), and out-of-scope mentions; decision window restricted to the selected price clause neighborhood

### Delivery Mode

- [ ] **DLVR-01**: Deterministic `delivery_mode` extraction with priority order: email > phone > oral > written > other — "emailed a written proposal" resolves to `email`, "orally indicated in a telephone call" resolves to `phone`
- [ ] **DLVR-02**: Clause-aligned detection restricts mode parsing to the same local context as the selected proposal action; conflicting modes without clear alignment leave the field null with a warning

### Bidder Classification

- [ ] **BKIND-01**: Filing-local `bidder_kind` classifier using evidence hierarchy: (1) direct descriptors near bidder name, (2) parenthetical list membership, (3) display-name heuristics, (4) small sponsor lexicon fallback
- [ ] **BKIND-02**: Conservative confidence rule — set `bidder_kind` only when one class has strong evidence and clearly dominates; otherwise keep `unknown`

### Secondary Booleans

- [ ] **BOOL-01**: `mentions_non_binding` set true on explicit "non-binding" cue
- [ ] **BOOL-02**: `includes_draft_merger_agreement` set true on "draft merger agreement", "form of merger agreement", or similar direct references
- [ ] **BOOL-03**: `includes_markup` set true on "markup", "marked-up", "marked draft", or "comments on the draft merger agreement" — not triggered by mere attachment of a draft

### Prompt And Schema Hardening

- [ ] **PRMT-01**: Structured field completeness block added to `observations_v2_prefix.md` making field population an obligation, not a hint
- [ ] **PRMT-02**: Bidder kind completeness block added to observations prompt requiring `bidder_kind` when filing gives a literal cue
- [ ] **PRMT-03**: Worked examples added to `observations_v2_examples.md` covering: range-to-range_low/high, mixed-offer headline total, delivery mode mapping, and parenthetical bidder kind classification
- [ ] **PRMT-04**: Schema guidance section added to `schema_ref.py` via `generate_schema_reference()` for `MoneyTerms.per_share`, `range_low`, `range_high`, `Proposal.delivery_mode`, and `PartyRecord.bidder_kind`

### Semantic Completeness Gates

- [ ] **GATE-01**: `gates_v2.py` adds blocker findings for proposals with surface price/range cues but missing `per_share` or `range_low/high` after repair
- [ ] **GATE-02**: `gates_v2.py` adds warning findings for missing `consideration_type`, `delivery_mode`, `bidder_kind`, and secondary booleans when surface cues exist — promotable to blockers after signal validation

### Test Coverage

- [ ] **TEST-01**: Parser unit tests covering single prices, ranges, mixed offers, later-vs-earlier prices, stock-price false positives, each delivery mode, non-binding, draft merger agreement, and markup
- [ ] **TEST-02**: Bidder kind classifier tests for direct descriptors, parenthetical list classification, display-name heuristics, and ambiguous cases that must remain `unknown`
- [ ] **TEST-03**: Canonicalize integration tests for canonical-mode repair, quote-first-mode repair, idempotence, and fill-only behavior
- [ ] **TEST-04**: Gate tests for missing cue-backed fields and prompt render tests asserting the new enforcement language is present

### Validation

- [ ] **VALID-01**: All 9 existing deals pass canonicalize → derive → export → gates through the repair layer without regression
- [ ] **VALID-02**: 3-deal re-extraction (mac-gray, petsmart-inc, imprivata) after prompt changes demonstrates measurable raw extraction improvement for structured fields

## Future Requirements

### Second LLM Pass

- **LLM-01**: Optional second LLM pass for bidder_kind and consideration_type when filing-local heuristics yield insufficient confidence — deferred unless coverage remains poor after v2.3

## Out of Scope

| Feature | Reason |
|---------|--------|
| Benchmark-driven generation logic | Violates the filing-grounded extraction contract |
| Making structured fields globally required in Pydantic models | Fields are conditionally required based on filing content; validators lack filing context |
| Overwriting populated values | Fill-only for v2.3 to prevent regression on correct extractions |
| Full 9-deal re-extraction | Cost too high; 3-deal sample sufficient to validate prompt improvement |
| Second LLM pass | Unnecessary for v2.3 unless bidder_kind coverage remains poor |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REPR-01 | — | Pending |
| REPR-02 | — | Pending |
| REPR-03 | — | Pending |
| REPR-04 | — | Pending |
| PRICE-01 | — | Pending |
| PRICE-02 | — | Pending |
| PRICE-03 | — | Pending |
| CTYPE-01 | — | Pending |
| CTYPE-02 | — | Pending |
| DLVR-01 | — | Pending |
| DLVR-02 | — | Pending |
| BKIND-01 | — | Pending |
| BKIND-02 | — | Pending |
| BOOL-01 | — | Pending |
| BOOL-02 | — | Pending |
| BOOL-03 | — | Pending |
| PRMT-01 | — | Pending |
| PRMT-02 | — | Pending |
| PRMT-03 | — | Pending |
| PRMT-04 | — | Pending |
| GATE-01 | — | Pending |
| GATE-02 | — | Pending |
| TEST-01 | — | Pending |
| TEST-02 | — | Pending |
| TEST-03 | — | Pending |
| TEST-04 | — | Pending |
| VALID-01 | — | Pending |
| VALID-02 | — | Pending |

**Coverage:**

- v2.3 requirements: 28 total
- Mapped to phases: 0
- Unmapped: 28 (awaiting roadmap)

---
*Requirements defined: 2026-04-04*
*Last updated: 2026-04-04 after initial definition*
