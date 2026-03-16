# Meeting Notes: Architecture Review — GPT Pro + Deep Think Synthesis

**Date:** 2026-03-16
**Reviewers:** GPT Pro (OpenAI), Gemini Deep Think (Google) — user-corrected with web search
**Project:** M&A Deal Extraction Pipeline (Austin Li & Alex Gorbenko)

---

## Executive Summary

Both reviewers independently converge on the same core architecture: **deterministic Python spine + schema-first AI extraction + independent auditor + targeted repair loops.** They agree on almost everything that matters. The 9-skill decomposition should flatten to ~4 stages. Only 2-3 skills need AI. Cost is ~$10 for 100 deals. The biggest risk is silent semantic omission, not schema validation.

---

## Consensus (Both Agree)

### C1. AI Boundary — Nearly Identical Verdicts

| Skill | GPT Pro | Deep Think | Consensus |
|-------|---------|------------|-----------|
| 1. select-anchor-filing | **A** deterministic | **A** deterministic | **A** |
| 2. freeze-filing-text | **A** deterministic | **A** deterministic | **A** |
| 3. locate-chronology | **C** hybrid (regex first, AI fallback) | **C** hybrid | **C** |
| 4. build-party-register | **D** AI extract + deterministic validation | **D** AI extract + deterministic validation | **D** |
| 5. extract-events | **D** AI extract + deterministic validation | **D** AI extract + deterministic validation | **D** |
| 6. audit-and-reconcile | **D** hybrid (mostly deterministic) | **D** hybrid (mostly deterministic) | **D** |
| 7. segment-processes | **A** deterministic (small C fallback) | **A** deterministic | **A** |
| 8. classify-bids | **C** rules first, AI for edge cases | **C** rules first, AI for edge cases | **C** |
| 9. render-review-rows | **A** deterministic | **A** deterministic | **A** |

**Perfect agreement on all 9 skills.**

### C2. Call Structure — Both Say C (Extract → Validate → Repair)

Both reject chunking as obsolete. Both reject single monolithic call as naive. Both recommend:
1. Full-context extraction call
2. Deterministic validation pass
3. Targeted repair calls only for flagged gaps
4. Independent auditor call

### C3. Fresh Eyes — Both Say Separate Context, Consider Cross-Vendor

- GPT Pro: separate stateless session (D) + different system prompt (B) + cross-vendor on flagged deals
- Deep Think: cross-vendor by default (Sonnet for extraction, Gemini/o3 for audit)
- Both: **never let the auditor fix artifacts silently** — emit findings, let deterministic merge handle it

### C4. Batch Orchestration — Both Say Sequential Python + SQLite/State Machine

- Both reject Airflow/Prefect as overengineering
- Both recommend per-skill checkpointing with artifact hashes
- Both recommend Batch API for bulk processing at 50% discount

### C5. Error Handling — Both Say Layered Retry + Fail Open

- Schema retry → semantic repair retry → model escalation → fail open to review queue
- Both: **null > wrong** for unresolved fields
- Both: cap retries tightly (2-3 max)

### C6. Cost — Both Estimate ~$10 for 100 Deals

- Both recommend Sonnet 4.6 or GPT-5.4 as default extractor
- Both say prompt caching + batch API makes this cheap
- Both say do NOT fine-tune for first 100 deals

---

## Disagreements (Where They Diverge)

### D1. Cross-Vendor Audit: Default or Escalation-Only?

- **GPT Pro:** Cross-vendor audit only on flagged deals. Baseline is same-provider separate session.
- **Deep Think:** Cross-vendor by default (Sonnet extraction → Gemini audit). "Same model weights = shared blind spots."

**My assessment:** Deep Think's argument is stronger for a research dataset where silent errors are catastrophic. But it adds complexity and cost. **Recommendation: start with same-provider separate session, add cross-vendor after eval harness shows where same-provider auditor misses.**

### D2. In-Memory vs. Disk-Based State Passing

- **GPT Pro:** "Your file-based message bus is a brilliant prototyping hack but a fragile production anti-pattern." Recommends in-memory Pydantic `DealState` passed through functions, disk writes only as checkpoints.
- **Deep Think:** Does not object to disk-based state. Focuses on atomic writes and idempotency.

**My assessment:** GPT Pro is right that passing state via JSON files is fragile. But disk-based artifacts are the audit trail — they're a feature, not a bug. **Recommendation: in-memory Pydantic pipeline for the hot path, but checkpoint to disk after each stage for reproducibility and resume.**

### D3. HTML-to-Text Conversion

- **Both** flag the current python3 one-liner as insufficient for pre-2010 filings with nested HTML tables.
- **GPT Pro:** recommends `markitdown` or `unstructured`
- **Deep Think:** recommends `BeautifulSoup` with separator logic or `markdownify`

**My assessment:** Test both on a sample of pre-2010 filings. This is a real risk — if tables become soup, Skill 5 will hallucinate. **Action: evaluate `markitdown` vs. `beautifulsoup4` on 5 pre-2010 filings.**

### D4. Iterative Focused Calls vs. Single Full-Context Call

- **GPT Pro (first response, stale):** one large call per pass, abandon chunking entirely
- **GPT Pro (corrected):** iterative targeted calls against globally cached context
- **Deep Think:** extract → validate → targeted re-read/repair
- **Gemini (first response, stale):** 3 iterative passes (actors → events → completeness sweep)

**Consensus after correction:** All converge on iterative focused calls against a cached full context. The key insight: **cache the full text, but ask focused questions per call** to reduce attention dilution.

---

## Action Items

| # | Item | Source | Priority | Effort |
|---|------|--------|----------|--------|
| 1 | Define Pydantic schemas for all 23 event types + actors + deal.json | Both | **P0** | Medium |
| 2 | Build eval harness on 8 reference deals (event recall, actor recall, quote-verify rate, edit minutes) | Both | **P0** | Medium |
| 3 | Rewrite Skills 1, 2, 3, 7, 9 as pure Python with atomic writes | Both | **P0** | Medium |
| 4 | Evaluate HTML-to-text parsers on pre-2010 filings | Both | **P1** | Low |
| 5 | Implement Skill 4+5 with provider abstraction + prompt caching + structured output | Both | **P1** | High |
| 6 | Implement deterministic auditor (quote verify, structural checks, round pairs) | Both | **P1** | Medium |
| 7 | Add AI-based count reconciliation as separate stateless call | Both | **P1** | Low |
| 8 | Run 20-deal bake-off: Sonnet 4.6 vs GPT-5.4 vs Gemini 2.5 Pro | GPT Pro | **P1** | Medium |
| 9 | Add SQLite state machine for deal tracking (status, cost, errors, model_id, prompt_version) | Both | **P2** | Low |
| 10 | Implement Batch API integration for backlog processing | Both | **P2** | Medium |
| 11 | Add cross-vendor audit for flagged deals | Deep Think | **P2** | Medium |
| 12 | Pin model snapshot IDs + prompt versions in every deal artifact | GPT Pro | **P2** | Low |

---

## Validated (Both Confirm as Correct)

- The 23-event taxonomy is sound
- Typed reconciliation (7 categories, no free text) is the right design
- Append-only decisions.jsonl is a strength
- Provenance model (direct_quote + derived_from_rows) is correct
- "Facts before judgments" principle (no classification during extraction)
- Fresh-eyes auditor separation is architecturally critical
- Frozen .txt contract is essential for quote verification

## Risks Flagged

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Silent semantic omission** (valid JSON missing events) | Critical | Taxonomy completeness sweep + independent auditor + eval harness |
| **Hallucinated provenance** (paraphrased quotes) | Critical | Deterministic `str.find()` at Python boundary, not deferred to Skill 6 |
| **SEC IP ban** at machine speed | Major | `time.sleep(0.15)` + compliant User-Agent |
| **Entity resolution drift** across iterative calls | Major | Lock actor roster as Enum, inject into subsequent prompts |
| **Pre-2010 HTML table destruction** | Major | Upgrade text converter to layout-aware parser |
| **Model/provider churn** (Gemini 3 preview deprecation) | Major | Provider abstraction + pinned model IDs + artifact hashes |
| **Taxonomy gaps** (Go-Shop, SPAC, partial-asset) | Minor | Add `unclassified_event` fallback type |

---

## Open Questions for Austin + Alex

1. **Provider bake-off scope:** Should we run the 20-deal eval on all 3 providers, or start with Anthropic only?
2. **Cross-vendor audit:** Worth the complexity now, or defer until eval shows same-provider blind spots?
3. **Standalone package vs. in-repo:** Should the Python pipeline be a separate package or stay in hmc-screening?
4. **Pre-2010 filing coverage:** How many of the 9,336 seed deals are pre-2010? This determines urgency of HTML parser upgrade.
5. **Human review workflow:** Who reviews flagged deals — Austin, Alex, or an RA? This affects the review queue design.

---

_GPT Pro reply saved to: `diagnosis/gptpro/2026-03-16/round_1_reply.md`_
_Deep Think reply saved to: `diagnosis/deepthink/2026-03-16/round_1_reply.md`_
_Generated by Claude from both reviewers' feedback_
