# Domain Pitfalls

**Domain:** SEC filing M&A deal extraction pipeline redesign (context management, prompt engineering, multi-pass verification)
**Researched:** 2026-03-27

## Critical Pitfalls

Mistakes that cause rewrites, silent data corruption, or structural regressions. Each of these has been observed or is strongly indicated by this project's existing codebase, diagnosis rounds, and current extraction research.

---

### Pitfall 1: Hallucinated Anchor Text Survives Verification

**What goes wrong:** The LLM generates plausible-sounding quotes that are paraphrases or composites of filing language rather than verbatim substrings. The current verify gate catches these (EXACT/NORMALIZED pass, FUZZY does not), but the repair loop re-reads the filing and may produce a *different* hallucinated quote that also fails. Two rounds of hallucinated quotes = hard failure with no extraction for that event.

**Why it happens:** LLMs are trained on prediction, not retrieval. When generating anchor_text fields, the model reconstructs from semantic memory rather than copying character-for-character from the input context. This is worse in the middle of long documents due to attention decay (the "lost in the middle" effect measured at 30%+ accuracy drops across 18 frontier models in 2025 studies).

**Consequences:** Verify gate fails repeatedly. Events with hallucinated anchors are lost entirely, creating coverage gaps the coverage gate may or may not catch (depends on whether the evidence item pattern matches). The repair loop wastes two LLM calls achieving nothing.

**Prevention:**
1. **Quote-before-extract protocol.** Restructure the extraction prompt so the LLM must first output verbatim quotes from the filing inside `<quotes>` tags, *then* build structured events referencing those quotes by index. Anthropic's own hallucination reduction guide explicitly recommends this for documents over 20k tokens. This forces the model into retrieval mode before extraction mode.
2. **Structured output with anchor_text as a constrained field.** When using provider_native structured outputs, the schema guarantees format but not accuracy. The quote-before-extract step provides the accuracy layer.
3. **Post-extraction anchor validation before writing artifacts.** Run a fast substring check on every anchor_text against the referenced block's raw text *inside the extraction call* (as a self-check instruction) rather than deferring entirely to the verify gate.

**Warning signs:** Verification findings dominated by `quote_verification` errors rather than `referential_integrity` or `structural_integrity` errors. High round-1 error counts in verification_log.json that do not decrease in round 2.

**Detection:** Monitor the ratio of UNRESOLVED anchors to total anchors across deals. If >10% of anchors fail EXACT/NORMALIZED on first extraction pass, the prompt architecture is the problem, not individual quotes.

**Phase:** Address in Phase 1 (prompt architecture redesign). This is the single highest-ROI change according to both Anthropic's documentation and this project's diagnosis history.

---

### Pitfall 2: Repair Loop Degenerative Correction

**What goes wrong:** The LLM repair loop (verify-extraction skill, round 1 fixes) introduces new errors while fixing old ones. Fixing an unresolved quote may change the event's date, actor_ids, or summary. Fixing a missing actor may create a referential integrity violation in events that referenced the old actor_id. Round 2 then finds *different* errors than round 1 found, and the 2-round cap means the extraction fails.

**Why it happens:** Self-correction research (2025) establishes that LLMs exhibit "self-bias" -- they favor their initial responses even when flawed. The repair loop feeds error traces back into the model, creating a fundamentally different conditional probability distribution (P(Y|X, Error) vs P(Y|X)). The repaired output is not an improved version of the original; it is a different generation conditioned on failure signals. Additionally, the repair context includes both the original extraction AND the error report, consuming tokens that could be used for better reasoning.

**Consequences:** Extraction success rates plateau below 100% even on deals the pipeline should handle. Each repair cycle costs a full LLM call with diminishing returns. The diagnosis round 3 response explicitly identifies this as "econometric poison" because repaired outputs are drawn from a contaminated distribution.

**Prevention:**
1. **Invest in first-pass quality over repair sophistication.** The quote-before-extract protocol, prompt ordering (data first, instructions last), and evidence-guided attention steering should reduce the repair loop's workload to genuinely minor fixes (typos in anchor text, off-by-one block_id references).
2. **Limit repair scope.** The repair loop should only fix what the deterministic gates flag. It must NOT re-extract events, change event types, add new actors, or modify dates unless the finding specifically requires it. Constrain fixes to: (a) anchor text substring correction, (b) block_id/evidence_id retargeting, (c) adding missing actors/events that coverage found.
3. **Track repair delta.** After round 1 fixes, diff the artifact to ensure only the flagged items changed. If the diff touches more than the flagged findings, reject the repair and fail closed.
4. **Cap at 2 rounds, as current design does.** Research confirms 2-3 cycles maximum before degenerative effects dominate.

**Warning signs:** Round 2 error count is comparable to or higher than round 1. Repair diffs touch artifacts not mentioned in findings. Repair introduces new event_ids or removes existing ones.

**Detection:** Compare round_1_errors vs round_2_errors in verification_log.json. If round_2_errors > round_1_errors * 0.5 across multiple deals, the repair loop is net-harmful.

**Phase:** Address in Phase 2 (verification/repair redesign), after Phase 1 prompt improvements reduce the repair loop's workload.

---

### Pitfall 3: Over-Chunking Simple Deals

**What goes wrong:** A complexity-based routing system defaults to multi-chunk extraction on deals that fit comfortably in a single context window. The chunking introduces overlap regions, deduplication complexity, actor roster synchronization between chunks, and cross-chunk event merging -- all of which are sources of new errors that would not exist in single-pass extraction.

**Why it happens:** Developers build the chunking infrastructure for complex deals (long filings with 200+ chronology blocks) and then apply it uniformly because "it works for complex deals." But chunking a 15,000-token chronology into 3 chunks of 7,000 tokens with 2-block overlap creates artificial boundaries that split related events across chunks, forcing deduplication logic that can merge semantically distinct events or miss the connection between an NDA event and its corresponding proposal.

**Consequences:** Actor confusion across chunks (the same party gets different actor_ids in different chunks). Event duplication (the same proposal extracted twice from overlapping blocks). Event splitting (a multi-day negotiation that spans a chunk boundary becomes two events instead of one). Coverage gaps from events in overlap regions that both chunks assume the other will handle.

**Prevention:**
1. **Complexity-based routing with a high chunking threshold.** Only chunk when the chronology exceeds the context window minus prompt overhead. For a 200k-token context window, this threshold should be set at ~150k tokens of chronology content (accounting for system prompt, actor roster, instructions, and output budget). Most deals in this corpus (9 deals) will fit in a single pass.
2. **Measure before chunking.** Count chronology block tokens before deciding. The preprocessing stage already produces chronology_blocks.jsonl with known block sizes. Sum them. If total < threshold, single-pass.
3. **Never chunk actors separately from events.** Actor extraction must see the full chronology to build a complete roster. Event extraction can be chunked, but only with the full actor roster passed as context to every chunk.

**Warning signs:** Chunking being applied to deals with <100 chronology blocks. Deduplication removing >5% of extracted events. Actor count differing between chunks.

**Detection:** Log the routing decision (single-pass vs chunked) and the token count that triggered it. If any of the 9 active deals routes to chunked extraction, verify it actually needed chunking by checking the chronology token count.

**Phase:** Address in Phase 1 (prompt architecture). The routing decision should be implemented alongside the prompt restructuring, not as a separate phase.

---

### Pitfall 4: Evidence Items Become an Extraction Crutch

**What goes wrong:** The evidence items (pre-tagged anchors from preprocessing with dates, actors, values, process signals) are promoted from a passive appendix to active attention-steering checklist. The LLM starts extracting events *only* for evidence items it sees in the checklist, ignoring chronology text that doesn't have a matching evidence item. Evidence items were designed to catch things the LLM might miss, not to define the exhaustive set of extractable events.

**Why it happens:** When evidence items are placed prominently in the prompt (e.g., as an "extraction checklist"), the LLM treats them as a closed-world specification. Anything not on the checklist is implicitly "not required." This is especially dangerous because evidence items are generated by regex-based pattern matching in the preprocessing stage, which has known recall gaps (e.g., unusual NDA phrasing, non-standard process initiation language).

**Consequences:** Systematically missing events that don't match the preprocessing regex patterns. False confidence from coverage passing (coverage checks against evidence items, not against the full chronology text). The pipeline appears to work perfectly but has a structural blind spot determined by preprocessing quality, not filing content.

**Prevention:**
1. **Evidence items guide re-reads, not primary extraction.** The extract-deal skill's principle #4 already states this: "Evidence items are anchors, not constraints. Use them to guide rereads, not to replace reading the chronology." This principle must be preserved in the redesigned prompt. Evidence items belong in the Pass 2 gap re-read, not in the Pass 1 forward scan.
2. **Primary extraction operates on chronology blocks alone.** Pass 1 reads chronology_blocks.jsonl sequentially and extracts everything it finds. Evidence items are not shown during Pass 1.
3. **Pass 2 uses evidence items as a coverage checklist.** After Pass 1, the evidence items are presented as "did you miss any of these?" This is additive, not constraining.
4. **Coverage gate audits against evidence items AND chronology text.** The current coverage gate only checks evidence item cues. Consider adding a lightweight chronology-text scan for high-signal patterns not in the evidence item set.

**Warning signs:** Extracted event count closely matches evidence item count. Events cluster around evidence item locations but leave gaps between them. New deals with unusual language consistently have lower extraction completeness.

**Detection:** Compare the set of block_ids referenced in extracted events against the full set of block_ids in chronology_blocks.jsonl. If >30% of blocks have no event referencing them, the extraction is skipping content.

**Phase:** Address in Phase 1 (prompt architecture). The separation between Pass 1 (chronology-driven) and Pass 2 (evidence-guided) must be explicit in the prompt design.

---

### Pitfall 5: Thinking Token Explosion on Structured Extraction

**What goes wrong:** Extended thinking (or adaptive thinking) generates enormous thinking token volumes on structured extraction tasks, consuming the token budget without proportional quality improvement. A 150-page filing with 40+ actors and 100+ events can trigger 50,000-100,000+ thinking tokens as the model deliberates over every classification decision, date normalization, and formality signal.

**Why it happens:** The extraction schema has 20 event types, 11 formality signal booleans per proposal, 6 actor classification dimensions, and requires evidence_refs for every item. Thinking-enabled models explore each decision branch. The current workflow uses reasoning-enabled extraction, and the diagnosis round 3 explicitly warns against disabling reasoning entirely because it cripples coreference resolution. But the opposite extreme -- maximum reasoning on every field -- creates cost and latency problems without quality gains on mechanical fields like `nda_signed: true`.

**Consequences:** 10x+ token cost per extraction call. Latency increases from seconds to minutes per chunk. Risk of hitting output token limits, truncating the actual extraction output. In the worst case, the thinking fills the budget and the structured output is incomplete.

**Prevention:**
1. **Use adaptive thinking with effort="high" rather than manual budget_tokens.** Anthropic's 2026 documentation recommends adaptive thinking over manual budget control. The model self-calibrates thinking depth per decision.
2. **Set max_tokens high enough for output.** With adaptive thinking, max_tokens serves as the hard limit on thinking + response combined. Set to at least 64,000 tokens for extraction calls. The thinking budget is implicitly controlled by the effort parameter, not by max_tokens starvation.
3. **Separate mechanical from interpretive extraction.** Mechanical fields (nda_signed, date parsing, actor_id lookups) do not benefit from deep reasoning. Interpretive fields (formality_signals, drop_reason_text, event_type classification) do. Consider whether the schema can be structured to front-load mechanical fields.
4. **Monitor thinking token usage per deal.** Track the ratio of thinking tokens to output tokens. If thinking > 3x output, the effort level is likely too high for the task.

**Warning signs:** Extraction calls taking >5 minutes. Token usage reports showing >80% thinking tokens. Output truncation in extraction responses.

**Detection:** Log thinking_tokens and output_tokens from every LLM call. Plot the ratio across deals. If the ratio is consistently >3:1, reduce effort or restructure the prompt to reduce decision complexity.

**Phase:** Address in Phase 1 (prompt architecture) for prompt structure changes. Address in Phase 3 (automation/orchestration) for effort parameter tuning and monitoring.

---

## Moderate Pitfalls

Mistakes that cause rework, quality degradation, or wasted effort but are recoverable without architectural rewrites.

---

### Pitfall 6: Few-Shot Example Overfitting

**What goes wrong:** Adding 4-5 few-shot examples (as the PROJECT.md active requirements specify) causes the LLM to mimic the examples' specific patterns rather than generalizing. A few-shot example showing Party A/Party B aliases causes the model to expect Party A/Party B in every filing. An example with 3 NDA events causes the model to extract exactly 3 NDA events even when the filing has 15.

**Why it happens:** Research from September 2025 ("The Few-shot Dilemma: Over-prompting Large Language Models") demonstrates that excessive domain-specific examples paradoxically degrade performance. The degradation appeared especially in multi-class classification (which maps directly to this pipeline's 20-type event taxonomy). Performance peaked at 5-20 examples before declining, with the optimal count being model-dependent.

**Prevention:**
1. **Use 3-5 examples maximum.** The Anthropic prompt engineering guide recommends 3-5 examples for best results.
2. **Ensure diversity across examples.** Each example should demonstrate a different pattern: one with NDA groups, one with ambiguous drops, one with cycle boundaries, one with simple 2-party deals, one with complex multi-bidder processes. Do not show multiple examples of the same pattern.
3. **Use XML `<example>` tags.** Wrap examples so the model distinguishes them from instructions. This is standard Anthropic guidance.
4. **Test with and without examples.** Before committing to few-shot, compare single-deal extraction quality with 0 examples vs 3 vs 5. If 0-shot quality is comparable, the examples may be unnecessary overhead.
5. **Avoid examples from the active deal set.** If stec is the baseline deal, do not use stec patterns as few-shot examples. This creates overfitting to the validation set.

**Warning signs:** Extracted events consistently match the count or pattern of few-shot examples. New deals produce outputs that look structurally identical to examples despite different filing content.

**Detection:** Remove few-shot examples and re-run extraction on one deal. If the output quality is the same or better, the examples were not helping.

**Phase:** Address in Phase 1 (prompt architecture). Example selection should be finalized during prompt design.

---

### Pitfall 7: Prompt Ordering Regression

**What goes wrong:** The prompt is restructured to put data first and instructions last (the highest-ROI zero-cost change per Anthropic docs), but during iterative development, new instructions or context get prepended to the prompt, pushing data back into the middle. Over time, the prompt order regresses to instructions-first, data-middle, query-last, recreating the attention decay problem the restructuring was meant to solve.

**Why it happens:** Developers naturally add new instructions at the top of the prompt because it feels like the most important position. Each small addition erodes the data-first ordering. Without a structural enforcement mechanism (e.g., prompt template with fixed sections), the ordering drifts.

**Prevention:**
1. **Template-based prompt construction.** Define the prompt as a template with fixed sections: `[system prompt] -> [actor roster] -> [chronology data] -> [evidence items] -> [few-shot examples] -> [extraction instructions] -> [output schema] -> [query]`. New content goes into the appropriate section, not at the top.
2. **Prompt structure tests.** Add a test that validates the prompt structure: data sections must appear before instruction sections. This catches regressions during development.
3. **Document the ordering rationale.** The prompt template should include comments explaining *why* data comes first (30% quality improvement per Anthropic testing), so future developers don't "optimize" by moving instructions up.

**Warning signs:** Extraction quality degrades on deals that previously worked. Middle-of-document events are missed more often than beginning/end events. Token usage hasn't changed but output quality has.

**Detection:** Diff the prompt template against the canonical ordering after each change. Flag any PR that moves data sections below instruction sections.

**Phase:** Address in Phase 1 (prompt architecture). The template structure is part of the initial prompt redesign and should have a regression test from day one.

---

### Pitfall 8: Chunk Overlap Deduplication Errors

**What goes wrong:** When extraction is chunked, the 2-block overlap region causes the same event to be extracted in both adjacent chunks. The deduplication logic merges them, but the merge heuristic is too aggressive (merging by event_type + actor_ids + date) or too conservative (merging only exact duplicates). Aggressive merging collapses genuinely distinct events (two different proposals on the same date by the same bidder). Conservative merging leaves duplicates that inflate event counts and confuse enrichment.

**Why it happens:** Event identity in M&A deals is nuanced. Two proposals by the same bidder on the same date may be distinct (one for the whole company, one for a division). Two NDA events on the same date for different parties are distinct. But two extractions of "Party A submitted an indication of interest on May 15" from overlapping blocks are the same event. The deduplication heuristic cannot capture these distinctions without domain-specific logic.

**Prevention:**
1. **Prefer single-pass extraction to avoid the problem entirely.** Most deals in this corpus fit in a single context window (see Pitfall 3).
2. **When chunking is necessary, deduplicate on evidence, not on semantics.** Two events referencing the same block_id + similar anchor_text are likely duplicates. Two events with the same type/date/actor but different block_ids are likely distinct.
3. **Flag potential duplicates for human review rather than auto-merging.** Include a `potential_duplicates` field in the extraction output listing pairs of events with high overlap scores.
4. **The canonicalization stage already has dedup logic.** Ensure it uses `evidence_span_ids` overlap as the primary signal, not just event_type + date. The existing code (canonicalize.py:240-298) is flagged as fragile in CONCERNS.md for exactly this reason.

**Warning signs:** Event counts vary by +/-5% between single-pass and chunked extraction on the same deal. Enrichment stage produces different round pairings depending on whether duplicates were merged.

**Detection:** Run both single-pass and chunked extraction on a test deal. Diff the outputs. Any discrepancy is a deduplication bug.

**Phase:** Address in Phase 2 (verification/coverage redesign) if chunking is implemented. If single-pass is sufficient for all 9 deals, this pitfall is deferred indefinitely.

---

### Pitfall 9: Actor Confusion Across Chunks

**What goes wrong:** In chunked extraction, the same entity gets different actor_ids in different chunks because the actor roster is built incrementally. Chunk 1 creates `bidder_party_a` for an entity referred to as "Party A". Chunk 2, seeing the entity's real name (revealed later in the filing), creates `bidder_acme_corp`. Both refer to the same party but have different IDs. Events from chunk 1 reference `bidder_party_a` while events from chunk 2 reference `bidder_acme_corp`. Merge fails or creates a referential integrity violation.

**Why it happens:** SEC filings often introduce parties as pseudonyms (Party A, Party B) and reveal their identities later in the chronology. In single-pass extraction, the LLM can resolve these aliases because it sees the full text. In chunked extraction, early chunks only see the pseudonym and late chunks only see the real name.

**Prevention:**
1. **Extract actors in a single pass over the full chronology before chunking events.** This is already the design in the existing extract-deal skill (Step 1a: Actor Extraction). The full actor roster, including aliases, must be established before any event extraction chunk begins.
2. **Pass the complete actor roster to every event extraction chunk.** Each chunk receives the roster as fixed context, not as something to extend. Open-world actor minting during event extraction should add to a shared append-only roster, with chunk-local IDs reconciled against the master roster after all chunks complete.
3. **Alias resolution in the actor roster.** The actor record includes an `aliases` field. Ensure Party A/Party B mappings are resolved during actor extraction, not deferred to canonicalization. This is a first-class extraction responsibility.

**Warning signs:** Actors with overlapping aliases but different actor_ids. Events referencing actor_ids that do not exist in the roster. Canonicalization log showing high merge counts.

**Detection:** After extraction, check for actors with overlapping alias sets or canonical_name matches. Any overlap is a resolution failure.

**Phase:** Address in Phase 1 (prompt architecture) as part of the actors-first extraction design.

---

### Pitfall 10: Prompt Caching Invalidation from Dynamic Content

**What goes wrong:** Prompt caching is implemented to reuse the system prompt + actor roster across chunk calls, but dynamic content (changing instructions, updated evidence items, or modified few-shot examples) invalidates the cache on every call, negating the cost and latency benefits.

**Why it happens:** Anthropic's prompt caching requires the cached prefix to be identical across calls. Any change to any content block before the cache breakpoint invalidates the entire cache. If the system prompt includes per-deal metadata, per-chunk instructions, or dynamically generated content, the cache is never reused.

**Prevention:**
1. **Separate static from dynamic content.** The system prompt (extraction instructions, event taxonomy, schema, few-shot examples) is static across all chunks of a deal. The actor roster is static across event extraction chunks. The chronology data is the only per-chunk variable. Structure the prompt as: `[static system prompt] -> [cache breakpoint] -> [static actor roster] -> [cache breakpoint] -> [per-chunk chronology + query]`.
2. **Do not embed deal-specific metadata in the cached prefix.** Deal slug, filing date, and other metadata belong after the cache breakpoints, not before.
3. **Verify cache hits in logs.** Anthropic reports cache hits in the API response (`cache_creation_input_tokens` vs `cache_read_input_tokens`). Log these. If cache_read is consistently 0, the caching is broken.

**Warning signs:** Token costs not decreasing across chunks of the same deal. Latency not decreasing on second and subsequent chunks. Cache write tokens charged on every call.

**Detection:** Log cache hit/miss rates from API responses. Expected pattern: first chunk = cache miss (write), subsequent chunks = cache hit (read). If all chunks are misses, inspect what changed in the prefix.

**Phase:** Address in Phase 3 (automation/orchestration) when implementing the chunked extraction infrastructure.

---

### Pitfall 11: Coverage Gate False Negatives from Regex Gaps

**What goes wrong:** The coverage gate passes because all evidence items are covered, but critical events are missing because the evidence items were never generated. The preprocessing regex patterns (in `coverage.py:_classify_cue_family`) do not match unusual phrasings, so no cue is created, so no coverage gap is flagged, so the extraction appears complete when it is not.

**Why it happens:** The coverage gate's cue detection is based on hardcoded string matching (e.g., "entered into a non-disclosure agreement", "submitted an indication of interest"). SEC filings use varied language: "signed a mutual confidentiality agreement", "delivered a non-binding expression of interest", "advised Party A that it was no longer pursuing the transaction". If these phrasings are not in the pattern set, no cue is generated, and the coverage gate has nothing to check.

**Prevention:**
1. **Treat coverage as a floor, not a ceiling.** The coverage gate catches what it can, but a passing coverage result does not mean extraction is complete. Document this limitation explicitly.
2. **Expand the pattern set incrementally.** After each deal extraction, review the chronology for events that were present in the filing but not flagged by evidence items. Add new patterns for any gaps found. This is a continuous improvement process, not a one-time design.
3. **Consider a lightweight LLM-assisted coverage check.** After extraction, ask the LLM "what important events in this chronology did you NOT extract, and why?" This is cheaper than full re-extraction and can surface gaps the regex misses.
4. **The block coverage metric (Pitfall 4 detection) serves as a complementary check.** If >30% of chronology blocks have no event, that is a signal regardless of evidence item coverage.

**Warning signs:** Coverage gate passes with 0 findings on a complex deal (unlikely in practice). Evidence item count is low relative to chronology block count. New deals consistently have lower extraction completeness despite passing coverage.

**Detection:** Track the evidence_items-to-chronology_blocks ratio per deal. If it is <0.5, the preprocessing regex is not capturing enough signal.

**Phase:** Address incrementally across all phases. The regex pattern set should grow as new deals expose gaps. An LLM-assisted coverage check could be added in Phase 2.

---

## Minor Pitfalls

Mistakes that cause friction, confusion, or suboptimal results but are easily correctable.

---

### Pitfall 12: Pydantic extra="forbid" Rejects LLM Innovation

**What goes wrong:** The Pydantic models use `ConfigDict(extra="forbid")`, which rejects any JSON key not in the schema. When the LLM adds a useful field (e.g., `confidence_score`, `alternative_date`, `cross_reference_event_id`) that the schema does not define, the entire artifact validation fails. The fix is to either add the field to the schema or strip it in post-processing, but the immediate failure blocks the pipeline.

**Prevention:** Use `extra="forbid"` on canonical artifacts (post-canonicalization) but consider `extra="ignore"` on raw artifacts (actors_raw.json, events_raw.json) during the extraction phase. Log ignored fields for schema evolution decisions. This is already flagged in CONCERNS.md as a dependency risk.

**Phase:** Address in Phase 1 (schema updates) alongside prompt architecture changes.

---

### Pitfall 13: Structured Output Schema Too Complex for Provider

**What goes wrong:** Anthropic's structured outputs support up to 100 object properties with 5 levels of nesting. The extraction schema (20 event types, discriminated unions, nested terms/formality_signals) may exceed these limits or produce edge cases where the constrained decoding fails. The result is either a malformed response or a 400 error.

**Prevention:** Validate the schema against provider limits before deployment. Keep the top-level structure flat: actors array + events array + metadata. Use discriminated unions only if the provider supports them natively. Test with the actual provider API, not just local Pydantic validation.

**Phase:** Address in Phase 1 (schema/prompt design). Validate against both Anthropic and OpenAI structured output limits.

---

### Pitfall 14: N-Run Consensus Without Infrastructure

**What goes wrong:** The diagnosis round 3 argues for N-run consensus infrastructure (running extraction multiple times and aggregating). This is architecturally sound for out-of-sample reliability but premature for a 9-deal corpus with no completed single-shot baseline across all deals. Building N-run infrastructure before proving single-shot creates engineering complexity that delays the more fundamental prompt quality improvements.

**Prevention:** Build the extraction orchestrator with `--n-runs=1` default and a clean interface for N-run support (results directory per run, aggregation hook). Do not implement the aggregation logic until single-shot extraction achieves acceptable quality on all 9 deals. The plumbing should exist; the logic should not.

**Phase:** Phase 3 (automation/orchestration). The interface should be designed in Phase 1 but the implementation deferred.

---

### Pitfall 15: Benchmark Contamination During Development

**What goes wrong:** Developers consult benchmark spreadsheets, reconciliation outputs, or example/ directory files while debugging extraction quality. This creates a feedback loop where the prompt is tuned to reproduce benchmark answers rather than to extract from filing text. The pipeline appears to work on the 9 calibration deals but fails on new filings because it was optimized for known answers, not for the extraction task.

**Why it happens:** The temptation is strong when an extraction misses an event that the benchmark shows. It is faster to add the event manually or tune the prompt to find it than to investigate why the filing-grounded extraction missed it. The CLAUDE.md benchmark separation rule exists specifically to prevent this, but it requires discipline.

**Prevention:**
1. **Enforce the benchmark boundary strictly.** No benchmark materials until after export-csv completes. This is already a project invariant.
2. **Automated enforcement.** Add a CI check or pre-commit hook that prevents imports from `example/`, `diagnosis/`, or reconciliation artifacts in extraction/verification/coverage code.
3. **Use filing text, not benchmark answers, to debug extraction gaps.** When an event is missing, read the filing text to understand *why* the prompt missed it, then fix the prompt to handle that pattern generally.

**Warning signs:** Prompt changes that reference specific benchmark event IDs or actor names. Test cases that assert exact benchmark values rather than structural properties.

**Detection:** Code review discipline. Any PR that mentions benchmark data in extraction-stage code should be rejected.

**Phase:** Continuous discipline across all phases. Enforcement tooling in Phase 3.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Prompt architecture (Phase 1) | Hallucinated anchor text (P1), over-chunking (P3), evidence crutch (P4), thinking explosion (P5), few-shot overfitting (P6), prompt ordering regression (P7) | Quote-before-extract protocol, complexity-based routing, evidence items in Pass 2 only, adaptive thinking with effort control, diverse examples, template-based prompt construction |
| Verification/coverage redesign (Phase 2) | Repair loop degenerative correction (P2), deduplication errors (P8), coverage false negatives (P11) | Constrain repair scope, evidence-based dedup, incremental regex expansion |
| Automation/orchestration (Phase 3) | Prompt caching invalidation (P10), N-run premature complexity (P14), benchmark contamination (P15) | Static/dynamic content separation, --n-runs=1 default, automated benchmark boundary enforcement |
| Schema/model updates (Phase 1) | Pydantic rejection of LLM innovation (P12), schema exceeds provider limits (P13) | extra="ignore" on raw artifacts, validate against provider constraints |
| Cross-chunk extraction (Phase 1-2) | Actor confusion (P9), chunk overlap dedup (P8), over-chunking (P3) | Actors-first single-pass, full roster context per chunk, prefer single-pass when possible |

---

## Sources

- [Anthropic: Reduce hallucinations](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations) - Quote-before-extract, direct quote grounding, verify-with-citations patterns
- [Anthropic: Extended thinking tips / Prompt engineering best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/extended-thinking-tips) - Data-first ordering (30% improvement), few-shot guidance (3-5 examples), adaptive thinking migration, overthinking control
- [Anthropic: Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) - Cache breakpoint requirements, static/dynamic separation, cache isolation changes (Feb 2026)
- [Anthropic: Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - Schema conformance guarantees, limitations (format not accuracy), 100-property/5-nesting limits
- [Anthropic: Adaptive thinking](https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking) - Effort parameter, budget_tokens deprecation, max_tokens as hard limit
- [Self-correction in LLM calls: a review](https://theelderscripts.com/self-correction-in-llm-calls-a-review/) - Self-bias, feedback quality bottleneck, 2-3 cycle maximum, hybrid validation recommendation
- [The Few-shot Dilemma: Over-prompting LLMs](https://arxiv.org/abs/2509.13196) - Performance degradation with excessive examples, optimal 5-20 range, multi-class sensitivity
- [Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172) - 30%+ accuracy drops at middle positions, U-shaped attention pattern
- [Lessons from Running an LLM Document Processing Pipeline in Production](https://medium.com/alan/lessons-from-running-an-llm-document-processing-pipeline-in-production-33d87f99cdb1) - Production extraction pipeline pitfalls
- [LLMQuoter: Enhancing RAG via Quote Extraction](https://arxiv.org/html/2501.05554v1) - Quote-first-then-answer strategy, 20-point accuracy gains
- [Why Do Multi-Agent LLM Systems Fail?](https://openreview.net/pdf?id=fAjbYBmonr) - Degenerative self-correction, error propagation, bias amplification
- [Google LangExtract](https://github.com/google/langextract) - Source grounding patterns, schema-guided extraction
- Project diagnosis round 3 response (`diagnosis/deepthink/2026-03-18/round_3/response.md`) - Repair loop contamination, reasoning effort tradeoffs, N-run protocol arguments
- Project CONCERNS.md (`.planning/codebase/CONCERNS.md`) - Pydantic extra="forbid", canonicalization dedup fragility, provenance edge cases

---

*Pitfalls research: 2026-03-27*
