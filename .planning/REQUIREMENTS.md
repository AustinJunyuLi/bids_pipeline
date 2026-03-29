# Requirements: v1.1 Reconciliation + Execution-Log Quality Fixes

**Defined:** 2026-03-29
**Core Value:** Produce the most correct filing-grounded structured deal record
possible from raw text.

## v1.1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Deterministic Hardening

- [x] **HARD-02**: ~~Coverage stage does not raise false positives on contextual confidentiality-agreement mentions that describe existing NDAs rather than new signings~~ — already implemented in coverage.py with regression tests (7-deal rerun, saks/petsmart-inc)
- [x] **HARD-03**: ~~Check stage correctly counts grouped NDA-signing bidder cohorts via group_size assertions~~ — already implemented in check.py:48-51 with regression tests in test_skill_check.py (7-deal rerun, providence-worcester)
- [x] **HARD-06**: Shared extract loader rejects mixed actor/event schema modes (canonical actors + quote-first events or vice versa) with a dedicated error before any stage-specific processing or writes
- [x] **HARD-01**: Canonicalize handles duplicate quote_id collisions by deterministic cross-array renumbering before actor/event quote merge; same-array duplicates still fail-fast; all actor/event/count-assertion references rewritten consistently; idempotent on reruns
- [x] **HARD-04**: Gates and coverage stages tolerate rollover-side and non-sale-process confidentiality agreements without producing false findings (covers activist rollover, bidder-bidder teaming, and target-on-target diligence NDAs)
- [x] **HARD-05**: db-export retries on transient DuckDB file-lock contention after db-load with bounded exponential backoff; non-lock errors not retried; exhausted retries surface a hard failure

### Enrichment Improvements

- [ ] **ENRICH-01**: bid_type classification promotes final-round proposals to Formal when process position (after final round announcement) overrides IOI filing language
- [ ] **ENRICH-02**: Deterministic DropTarget classification for committee-driven field narrowing based on drop_reason_text signals in enrich-core
- [ ] **ENRICH-03**: Contextual all_cash inference from deal-level consideration patterns when explicit per-proposal mention is absent

### Extraction & Skill Docs

- [ ] **EXTRACT-01**: Extraction skill docs include round milestone event guidance (Final Round Inf Ann, Final Round Inf, deadlines) with filing-grounded examples
- [ ] **EXTRACT-02**: Extraction skill docs include verbal/oral price indication guidance with examples from stec and petsmart-inc patterns
- [ ] **EXTRACT-03**: Extraction skill docs include NDA exclusion guidance for rollover-side and non-target confidentiality agreements
- [ ] **EXTRACT-04**: Zep NMC actor error corrected -- remove NMC from evt_005 and evt_008 actor_ids
- [ ] **EXTRACT-05**: Medivation missing drops restored -- evt_013 and evt_017 present in events_raw.json with filing-grounded evidence

### Re-extraction & Validation

- [ ] **RERUN-01**: Affected deals re-extracted with updated skill docs and re-run through full deterministic pipeline (canonicalize through db-export)
- [ ] **RERUN-02**: 9-deal reconciliation re-run shows improved atomic match rate and reduced filing-contradicted pipeline claims vs baseline

## Future Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Coverage Expansion

- **COV-01**: Hybrid BM25 retrieval for targeted gap recovery when coverage finds missing evidence
- **COV-02**: Implicit DropTarget detection when active bidder absent from invited_actor_ids in subsequent rounds

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full re-extraction of all 9 deals | Only deals with known errors need re-extraction; clean deals should not be touched |
| Benchmark-driven generation | Benchmark materials remain post-export diagnostics only per hard invariant |
| Python LLM wrapper for extraction | Extraction remains local-agent orchestration per runtime split |
| UI or product surface | Backend pipeline focused |
| New deal onboarding | v1.1 is quality fixes on existing 9-deal corpus |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| HARD-01 | Phase 6 | Complete |
| HARD-02 | Phase 6 | Complete (7-deal rerun) |
| HARD-03 | Phase 6 | Complete (7-deal rerun) |
| HARD-04 | Phase 6 | Complete |
| HARD-05 | Phase 6 | Complete |
| HARD-06 | Phase 6 | Complete |
| ENRICH-01 | Phase 7 | Pending |
| ENRICH-02 | Phase 8 | Pending |
| ENRICH-03 | Phase 8 | Pending |
| EXTRACT-01 | Phase 8 | Pending |
| EXTRACT-02 | Phase 8 | Pending |
| EXTRACT-03 | Phase 8 | Pending |
| EXTRACT-04 | Phase 9 | Pending |
| EXTRACT-05 | Phase 9 | Pending |
| RERUN-01 | Phase 9 | Pending |
| RERUN-02 | Phase 9 | Pending |

**Coverage:**
- v1.1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0

---
*Requirements defined: 2026-03-29*
*Last updated: 2026-03-29 after Phase 06 verification and completion*
