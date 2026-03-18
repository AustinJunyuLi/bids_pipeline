# Round 2 Assessment + Independent Agent Audits

## Part A: Gemini Round 2 Recommendations — Our Independent Assessment

We had Claude Opus independently evaluate every recommendation from your Round 2 review against the actual codebase. Here is our assessment, organized by your section numbering.

---

### 1a. Initiation Judgment → Promote to System 1

**Our verdict: AGREE.**

Promoting `InitiationJudgment` into `DealEnrichment` via a Stage 5 LLM call is the right move. The data is genuinely narrative-interpretive — boards always claim "we regularly explored strategic alternatives." No deterministic rule can untangle that. The implementation: add the field to `DealEnrichment`, make a single targeted LLM call in Stage 5 reading the first N chronology blocks, require `justification_text` for auditability. This is the only place in the pipeline where a Stage 5 LLM call is justified.

### 1b. Advisor-Client Linkage (`advised_actor_id`)

**Our verdict: AGREE. Real schema gap.**

Alex explicitly tracks which advisor serves which party. The pipeline has no structural way to express "Wachtell Lipton advises the Target board." Adding `advised_actor_id: str | None` to `ActorRecord` is the minimal correct fix. The LLM extracts it from sentence syntax ("Morgan Stanley, financial advisor to the Company"), QA verifies the anchor text.

### 1c. NDA Aggregation

**Our verdict: AGREE. Formatting-only gap.**

The pipeline's 1NF normalized schema is superior for econometrics. The gap is purely in `alex_compat.py` export formatting. No extraction or schema changes needed.

### 1d. Formal/Informal Classification

**Gap 1 (Selectivity / `invited_actor_ids`): AGREE.** Looking at `classify.py`, Rule F2 fires on `after_final_round_announcement` regardless of whether the round was restricted. Adding `invited_actor_ids: list[str]` to `RoundEvent` and making Rule F2 check `len(invited_actor_ids) < len(active_bidders)` is the right approach.

**Gap 2 (Financing conditionality): PARTIALLY AGREE.** Adding `is_subject_to_financing: bool | None` to `FormalitySignals` is reasonable, but Alex's instructions don't explicitly require this as a classification input. Alex tracks it in comments, not as a structured field. Add it to the schema as an LLM-extracted signal but keep it out of the classification cascade until confirmed.

**Gap 3 (Per-share math / COMPUSTAT): AGREE IN PRINCIPLE, defer.** The v2 design explicitly lists "Compustat linkage" as a non-goal for the first production version. Defer until after 9-deal validation.

### 1e. Dropout Classification

**Our verdict: DISAGREE with severity framing. Partially agree with recommendation.**

Gemini called this "catastrophically flawed." That's hyperbolic. The LLM extracts `DROP_BELOW_M`, `DROP_BELOW_INF`, etc. from narrative text — these are textual pattern matches, not "quantitative relative judgments comparing an offer to market cap." When Alex records "DropBelowM," he's reading the filing text saying "Party C indicated that its analysis suggested a value below the Company's current stock price."

**The correct hybrid:**
- Keep the full dropout taxonomy in LLM extraction (the model reads the same text Alex reads)
- `drop_reason_text: str` already exists on `DropEvent`
- In Stage 5, cross-reference against extracted `ProposalEvent` values to *validate* the LLM's subtype label
- Flag inconsistencies (e.g., LLM says `DROP_BELOW_INF` but no prior informal bid exists) as `review_required`
- Stripping subtypes from the LLM and relying purely on CRSP would be *less* accurate because the filing contains qualitative context no external data source has

### 1f. Final Rounds / Cycles

**Our verdict: AGREE. Keep deterministic.** The 180-day gap rule in `cycles.py` is methodologically sound.

---

### 2a. Bipartite Graph Matching for Validation

**Our verdict: OVERENGINEERED for N=9.** Hungarian algorithm for 9 deals is overkill. Simpler: sort both datasets by (deal, date, actor), inner join on date (±3 days) + event type + actor name similarity, manually inspect unmatched residuals. At N=9, manual inspection is required for understanding failure modes.

### 2b. Error Categories

**Our verdict: REASONABLE but premature.** Binary match/miss per row is sufficient to drive iteration right now. Weighted severity framework is for the paper's methodology section, not current development.

### 2c. N=9 and Holdout

**Our verdict: CORRECT AND IMPORTANT.** The strongest point in the entire review. 9 deals is a calibration set. Pipeline is tuned against them. For publication, need held-out validation of 30-50 deals coded independently. The pre-training leakage concern is real but mitigated by SpanRegistry (fabricated facts get caught). Residual risk: LLM may be better at *finding* substrings in filings seen during training. The holdout set addresses this.

---

### 5a. "Claude 4.6 400 Errors from prompted_json"

**Our verdict: FACTUALLY WRONG about the pipeline.**

Gemini claimed `prompted_json` uses "assistant prefilling" and will return HTTP 400. **This is incorrect.** Looking at `backend.py` lines 268-296: `prompted_json` mode calls `PromptPack.render_structured_system_prompt()` which injects the JSON schema into the *system prompt*, then calls `_agenerate_text()` — a normal text generation call. There is NO assistant prefilling anywhere.

Furthermore, the pipeline **already supports** `provider_native` mode. `anthropic_backend.py` lines 174-201 implement `_build_native_request_params` using `output_config.format` with `json_schema`. The `--structured-mode` CLI flag switches between modes. Gemini told us to build something we already have.

That said, defaulting to `provider_native` for Anthropic is worth testing — native JSON schema gives guaranteed structural conformance without the repair loop.

### 5b. GPT-5.4 `reasoning_effort: "high"`

**Our verdict: CONTRADICTS current guidance, worth A/B testing.**

`CLAUDE.md` says "Use `reasoning_effort=none` for extraction" because GPT-5.4 shares `max_completion_tokens` between hidden reasoning and visible output. Gemini recommends `reasoning_effort: "high"`. These are directly contradictory. The trade-off: higher reasoning produces better extraction quality but consumes output budget. This is an empirical question — run the same deal both ways and compare.

### 5c. "Delete Chunking"

**Our verdict: WRONG, for the wrong reason.**

The constraint isn't input tokens — it's output tokens. A complex deal with 40+ events can produce 8k-12k output tokens. Also, most deals aren't chunked: `classify_complexity()` only triggers chunking for COMPLEX (>15k tokens or >400 lines or >15 actors).

**CRITICAL BUG FOUND BY OUR AUDIT:** In `events.py` line 73, `complexity` is a `ComplexityClass` enum but is compared to the string `"simple"`. Since `ComplexityClass.SIMPLE != "simple"` is always `True` in Python, **chunking ALWAYS activates regardless of complexity**. Every deal gets chunked. This is a bug that must be fixed.

A reasonable compromise: raise chunking thresholds substantially (e.g., 30k tokens, 800 lines) so single-shot is the default for all but the largest filings. Don't delete the infrastructure.

### 5d. N-Run Protocol (Wang & Wang 2025)

**Our verdict: CONCEPTUALLY SOUND, PRACTICALLY PREMATURE.**

Running extraction N=3-5 times and majority voting is rigorous but:
1. Multiplies API cost 3-5x
2. The consensus merger is non-trivial (aligning events across runs)
3. SpanRegistry already provides strong error-correction

Implement **after** the 9-deal validation, not before. First prove single-shot works well.

### 5e. Frozen Inference Log

**Our verdict: GOOD IDEA, implement it.** The `llm_calls` SQLite table already stores usage metadata. Extending it to store actual request/response JSON is the right move for replication.

---

## Part B: Independent Agent Audits of Current Codebase

We deployed 4 independent agents to audit the complete codebase. Below are their key findings organized by severity.

### Critical Bugs

1. **Events chunking always activates (events.py line 73).** `complexity != "simple"` compares a `ComplexityClass` enum to a string, which is always `True`. Every deal gets chunked regardless of actual complexity. This destroys single-shot extraction for simple deals and introduces unnecessary merge complexity.

2. **Missing `import json` in backend.py.** `_system_to_text()` calls `json.dumps()` but `json` is not imported. Will crash with `NameError` if `system` is ever passed as `list[dict]`. Currently unexploded because all callers pass strings.

3. **`review_items` table lacks `run_id` column (state.py).** The `summarize_run` query counts ALL review items globally instead of per-run. The table schema has no `run_id` column, making per-run review reporting impossible.

4. **Review overrides severity comparison uses raw strings (qa/review.py).** `finding.severity == "blocker"` compares a `ReviewSeverity` enum to a string. If Pydantic enforces the enum type, this comparison will silently fail, undercounting blockers.

### Major Design Issues

5. **OpenAI provider-native schema is NOT ref-inlined (openai_backend.py).** `_ainvoke_provider_native` passes `model_json_schema()` raw to the API with `$ref` pointers intact. OpenAI strict mode rejects `$ref`. The `schema_profile` safety gate probably prevents this in practice, but the code path is broken if reached.

6. **No partial-failure handling in batch operations (orchestrator.py, cli.py).** If deal N fails in a batch, all prior successes are lost. No stage attempts are recorded for successfully processed deals.

7. **Module-level I/O at import time (prompts.py).** Importing `pipeline.llm.prompts` reads a markdown file from disk. If the spec file is missing, the entire `pipeline.llm` package fails to import.

8. **`peak_active_bidders` is misnamed (features.py).** The function never removes actors from the `active` set and counts ALL actors (not just bidders). It's really "cumulative unique actors seen," not "peak active bidders."

9. **`last_round_event` carries across cycles in classify.py.** The classifier doesn't receive cycle boundaries. A round event in cycle 1 can influence classification of a proposal in cycle 2.

10. **Export runs without gate enforcement (review_csv.py).** `run_export` writes all artifacts regardless of `passes_export_gate`. The gate is informational only.

### Schema Gaps

11. **`DealExtraction` serves dual roles** — both raw and canonical extraction. The `artifact_type == "canonical_extraction"` conditional validator is runtime-only; there's no type-level separation.

12. **No cross-entity referential integrity.** All ID references (`actor_ids`, `span_ids`, `start_event_id`, etc.) are bare strings. The model layer never validates that referenced IDs exist.

13. **Four untyped `dict[str, Any]` bags** across the model layer: `QAReport.completeness_metrics`, `ChronologyCandidate.diagnostics`, `ChronologySelection.confidence_factors`, `FilingCandidate.ranking_features`.

14. **`ReviewRow` uses `str` where enums exist** — `event_type`, `actor_role`, etc. are all `str` instead of their corresponding enums, meaning invalid values pass validation silently.

15. **Duplicated validators between LLM and internal layers** — `validate_group_metadata` and `validate_amounts` are copy-pasted across `Raw*` and internal models.

### Infrastructure Issues

16. **Triple-duplicated atomic write utilities** across `extract/utils.py`, `preprocess/source.py`, and `source/fetch.py`.

17. **Three copies of `_normalize_message_content`** across `openai_backend.py`, `local_agent_backend.py`, and `_build_messages`.

18. **Two copies of `_inline_refs`** in `json_utils.py` and `schemas.py`.

19. **No logging framework.** None of the 60+ files use Python's `logging` module. All diagnostic information is silently dropped or returned in dict payloads.

20. **`cache_control` placement in anthropic_backend.py** may be incorrect — the Anthropic SDK expects cache_control as a block-level annotation within content blocks, not as a top-level parameter. Needs verification.

21. **OpenAI token counting is entirely heuristic** (`len(text)/4`) — no tiktoken or API-based counting. Complexity classification can diverge between providers.

22. **`urlopen` without timeout in source/fetch.py.** A hung EDGAR server will block indefinitely.

23. **Bare `except Exception` in source/discovery.py** swallows all search failures silently, including network errors and auth failures.

---

## Part C: Our Prioritized Implementation Roadmap

Based on the combined Gemini review + our independent assessment:

**Phase 0 — Bug Fixes (immediate):**
1. Fix `events.py` enum-vs-string chunking bug
2. Add `import json` to `backend.py`
3. Add `run_id` to `review_items` table
4. Fix enum string comparisons in `qa/review.py`

**Phase 1 — Schema Augmentations (before next extraction run):**
1. `advised_actor_id: str | None` on `ActorRecord`
2. `invited_actor_ids: list[str]` on `RoundEvent`
3. `is_subject_to_financing: bool | None` on `FormalitySignals`
4. `InitiationJudgment` model + field on `DealEnrichment`

**Phase 2 — Pipeline Hardening (before 9-deal validation):**
1. Consolidate duplicated utilities (atomic writes, message normalization, ref inlining)
2. Add Python logging framework
3. Fix `peak_active_bidders` to track only bidder-role actors
4. Make classification cycle-aware (reset `last_round_event` at boundaries)
5. Enforce export gate
6. NDA aggregation formatting in `alex_compat.py`
7. Frozen inference log (extend `llm_calls` table with request/response JSON)

**Phase 3 — Validation & External Data (before corpus run):**
1. Build 9-deal comparison framework against Alex's benchmark data
2. Evaluate `provider_native` as default structured output mode
3. Evaluate chunking threshold adjustments
4. Add dropout subtype validation in Stage 5

**Phase 4 — Publication Robustness (before paper submission):**
1. Holdout set of 30-50 deals coded independently
2. Evaluate N-run protocol cost/benefit
3. COMPUSTAT integration for per-share math
4. CRSP integration for dropout validation
