You are entirely correct to separate System 1 (the production pipeline) from System 2 (the Deal-Agent skills). Evaluating the skills as an R&D sandbox clarifies the architectural boundaries. Furthermore, your correction regarding `pipeline/normalize/dates.py` is accurate—the pipeline indeed deterministically handles "early/mid/late" month approximations (lines 56–65), rendering my Round 1 critique on that specific point invalid. I also accept your pushback on fuzzy matching: retaining `QuoteMatchType.FUZZY` but deterministically flagging those rows with `review_required=True` is the correct econometric compromise between recall and precision.

Here is the exhaustive, independent assessment of your pipeline against Alex Gorbenko’s exact benchmark data and instructions, evaluated under the March 2026 applied econometric state of the art.

---

### Part 1: Pipeline Calibration vs. Alex's Requirements

I have mapped every requirement in Alex's instructions against the System 1 production codebase (files 02–06).

**(a) Start of Sale Process (Section 3.2)**
*   **Pipeline Status:** Extracts basic process markers (`TARGET_SALE`, `BIDDER_SALE`, `ACTIVIST_SALE`) accurately via `events.py`.
*   **The Gap:** Alex's instructions require a synthetic understanding of causality: *"Record both 'Target Sale' and 'Bidder Sale' in separate lines... if the target decided to sell itself, but a bidder approached it with a bid before."* Extracting isolated chronological events is insufficient for causal inference because SEC filings use legally stylized boilerplate (e.g., boards always claim they "regularly review alternatives" even if a hostile bidder forced their hand). 
*   **Optimal Approach: LLM Judgment (Auditable).** Causal sequencing is purely narrative. You must promote `initiation_judgment` from System 2 into System 1. Create a dedicated LLM call in Stage 5 (`enrich/features.py`) that reads the first 20% of the chronology blocks and outputs an `InitiationJudgment` object directly into the `DealEnrichment` schema, requiring a `justification_text` trace.

**(b) Investment Bank & Legal Counsel Retention (Section 3.3)**
*   **Pipeline Status:** Extracts `IB_RETENTION` events and `ActorRecord`s with `advisor_kind=legal`.
*   **The Gap:** Relational edges. Alex explicitly notes: *"legal counsel — we should probably use [these] in comments."* In the benchmark data, he maps specific firms to specific clients. Your pipeline extracts "Wachtell Lipton" but has no structural way in `ActorRecord` to link the firm to the Target versus the Bidder.
*   **Optimal Approach: LLM Extraction + Deterministic Verification.** Add `advised_actor_id: str | None` to the `ActorRecord` schema. The LLM extracts the linkage based on sentence syntax; Stage 4 QA verifies the anchor text confirming the representation.

**(c) Confidentiality Agreements (NDAs) (Section 3.4)**
*   **Pipeline Status:** Extracts `NDAEvent` for named parties and `CountAssertion` for aggregates.
*   **The Gap:** In Providence & Worcester, Alex clusters: `[1] NDA bidder=25 parties, including Parties A, B`. Your pipeline extracts a `CountAssertion` of 25, plus independent `NDAEvent` rows for Party A and Party B. 
*   **Optimal Approach: Fully Deterministic Export.** Do **not** alter the pipeline extraction. Your pipeline's normalized relational schema (1NF) is econometrically superior for downstream regressions. The gap is purely formatting. Update `pipeline/export/alex_compat.py` to deterministically aggregate concurrent `NDAEvent`s and `CountAssertion`s sharing the same date into Alex's requested string format.

**(d) Submitted Bids & Formal/Informal Classification (Section 3.5)**
*   **Pipeline Status:** Extracts `ProposalEvent`. `enrich/classify.py` uses a 4-tier deterministic priority cascade.
*   **The Gap 1 (Selectivity):** Alex states a bid is formal if the round invites *"only a SUBSET of bidders"*. Your Rule F2 (`after_final_round_announcement`) fires blindly for *any* post-announcement bid. Your `RoundEvent` schema lacks an `invited_actor_ids` array, making it impossible for Stage 5 to verify if the round was actually restricted.
*   **The Gap 2 (Conditionality):** Alex's comments heavily track firm financing vs. conditional bids. `ConsiderationType` tracks Cash/Stock, but you have no schema field for financing conditionality—a massive omitted variable in auction theory.
*   **The Gap 3 (Per-Share Math):** Alex requires `bid_value_pershare`. The LLM extracts `total_enterprise_value` but does no math.
*   **Optimal Approach:** 
    *   *Selectivity:* Add `invited_actor_ids: list[str]` to `RoundEvent` (LLM extracted). Update Rule F2 in Stage 5 to deterministically check `len(invited_actor_ids) < len(active_bidders)`.
    *   *Conditionality:* Add `is_subject_to_financing: bool | None` to `FormalitySignals` (LLM extracted).
    *   *Per-Share:* **Deterministic + External Data.** Stage 5 must pull `cshoc` (Shares Outstanding) from the COMPUSTAT API and deterministically divide the extracted EV. Never ask the LLM to do arithmetic.

**(e) Bidder Dropouts (Section 3.6)**
*   **Pipeline Status:** Catastrophically flawed implementation. In `prompts.py`, you force the LLM to extract `DROP_BELOW_M` and `DROP_BELOW_INF` natively.
*   **The Gap:** You are forcing the LLM to make quantitative relative judgments (comparing an offer to a moving market capitalization) using only narrative text. It is hallucinating these labels based on narrative "vibes."
*   **Optimal Approach: Deterministic + External Data.** Strip relative dropouts from the LLM taxonomy. The LLM must *only* extract `DROP` and `drop_reason_text`. In `enrich/features.py`, Stage 5 deterministically queries CRSP for the $T-30$ unaffected stock price to assign `DropBelowM`, and cross-references the bidder's previous `ProposalEvent` value in the pipeline memory to assign `DropBelowInf`.

**(f) Final Rounds, Execution, Termination (Sections 3.7 - 3.9)**
*   **Pipeline Status:** Handled via `RoundEvent`, `EXECUTED`, and `CycleBoundaryEvent`. `cycles.py` uses a 180-day gap rule for implicit restarts.
*   **Optimal Approach: Fully Deterministic.** Keep the 180-day inactivity rule for cycle boundaries. Overriding this with LLM "narrative interpretation" introduces unreplicable variance. 

---

### Part 2: Alex's Hand-Collected Data as Benchmark

File 08 reveals exactly how you must structure your validation framework. A simple `pandas.merge` will fail because Alex uses continuous narrative sequences (fractional IDs like 0.5, 13.5) and estimated "rough" dates.

**(a) Matching Criteria for Validation**
You must implement a **Bipartite Graph Matching** algorithm (e.g., the Hungarian algorithm) in `validate_stage.py`.
1.  **Temporal Alignment:** Match on Date, allowing a $\pm 3$ calendar day tolerance for Alex's "rough" dates.
2.  **Typological Alignment:** Map pipeline `EventType` enums to Alex's `bid_note` taxonomy.
3.  **Actor Equivalence:** Use Jaro-Winkler string similarity ($> 0.85$) to map pipeline `canonical_name` to Alex's `Bidder` field. Drop Alex's `bidderID` fractions entirely; sort both datasets by date and compare topological order.

**(b) Error Categories (Weighted by Econometric Severity)**
1.  **Fatal Omission (Weight 1.0):** Missed `ProposalEvent`. This destroys the auction demand curve calculation.
2.  **Fatal Commission (Weight 1.0):** Hallucinated `ProposalEvent`. (Your Stage 4 `SpanRegistry` effectively nullifies this risk).
3.  **Severe Measurement (Weight 0.8):** Wrong `value_per_share` (calculate via Mean Absolute Percentage Error [MAPE]). Misattributing Party A's bid to Party B.
4.  **Moderate Classification (Weight 0.3):** The LLM extracted the textual features correctly, but the deterministic rules in `classify.py` assigned "Formal" while Alex assigned "Informal." This is a methodological divergence, not an LLM extraction failure.

**(c) The Insufficiency of N=9 Deals**
Are 9 deals sufficient for publication in a top-3 finance journal? **No.** 
These 9 deals represent your *Calibration Set*. By iterating your prompts and rules against them, you have overfitted the pipeline to these specific narrative geometries. Under the framework established by Ludwig, Mullainathan, and Rambachan (2025, SSRN 5094968), because SEC filings from 2012-2021 are in the pre-training data of Claude and GPT, you suffer from "training leakage." 
*   **The Fix:** You must instruct Alex or an RA to code a sequestered **Holdout Set** of 30–50 random deals *after* the pipeline code is frozen. You run the pipeline on the holdout set once and report those out-of-sample F1 and MAPE metrics in the paper.

---

### Part 3: Optimal LLM/Deterministic Mix Summary

Here is the strict architectural boundary required for academic rigor:

| Requirement | Optimal Approach | Rationale |
| :--- | :--- | :--- |
| **Dates (Exact & Imprecise)** | **Fully Deterministic** | `dates.py` regex mapping is mathematically stable. LLMs hallucinate calendar math. |
| **Cycle Boundaries** | **Fully Deterministic** | The 180-day inactivity gap is standard empirical finance methodology. |
| **EV / Per-Share** | **Det. + External Data** | LLM extracts EV text; Python queries COMPUSTAT `cshoc` and divides. |
| **DropBelowM / Inf** | **Det. + External Data** | LLM extracts `DROP`; Python queries CRSP and internal event state to classify. |
| **Formal vs Informal** | **LLM Extract + Det. Cascade** | LLM extracts boolean signals (`includes_draft`). Stage 5 applies strict priority rules, decoupling NLP from economic definitions. |
| **Events, Actors, Quotes** | **LLM Extract + Det. Verify** | LLM semantic parsing is required, but `SpanRegistry` cryptographically ensures no hallucinated text enters the dataset. |
| **Initiation Judgment** | **LLM Judgment (Auditable)** | Requires causal narrative reading. Stage 5 triggers a targeted LLM call, saves reasoning trace to `DealEnrichment`. |

---

### Part 4: Skills as a Facilitating Tool (System 2)

System 2 is a highly effective diagnostic sandbox. Here is how it feeds back into System 1:

**(a) What to promote to System 1:**
*   **Initiation Judgment:** As established, move this to `DealEnrichment` via a dedicated Stage 5 LLM call.
*   **Structural Audit Checks:** The 5-point checklist (e.g., "Do all round announcements have deadlines?") is codifiable. Rewrite these as deterministic Python graph queries in `qa/completeness.py` to trigger automated `ReviewSeverity.WARNING` flags. 

**(b) What remains as Skill-only (System 2):**
*   **Count Reconciliation:** Asking an LLM to explain *why* the text says 25 NDAs but it only extracted 12 (e.g., `unnamed_aggregate`) is a hallucination trap. The LLM will invent a justification to satisfy the prompt. Keep this as a System 2 developer tool to help you identify prompt weaknesses, but never put the LLM's "explanation" into the final dataset.

**(c) The Feedback Loop to System 1:**
System 2's primary output (`qa/skill_audit.json`) should be formally ingested by `pipeline/export/alex_compat.py` purely to manipulate the human review queue. If the skill's Count Reconciliation returns `unresolved`, or the Structural Audit flags `lifecycle_consistency = False`, Stage 6 flips `review_required = 1` for that deal's rows in the CSV. The pipeline data is not altered, but the researcher's attention is targeted.

---

### Part 5: Publication-Ready Architecture (March 2026 SOTA)

To survive peer review, your infrastructure requires critical updates to address the latest API architectures and applied econometrics standards for LLM variance.

**(a) Critical API & Infrastructure Updates**
1.  **Claude 4.6 400 Errors:** As of February 2026, Anthropic disabled assistant prefilling. Your `backend.py` relying on `prompted_json` will return HTTP 400 errors in production. You **must** move to `provider_native` using `output_config.format` (native JSON Schema) and enable `thinking: {"type": "adaptive"}`.
2.  **GPT-5.4 Reasoning:** OpenAI’s GPT-5.4 uses `reasoning_effort` instead of traditional temperature scaling. Set `reasoning_effort: "high"` for Stage 3B (Events) to allow the model to build an internal Chain-of-Thought (CoT) prior to emitting the structured JSON.
3.  **Delete Chunking:** Claude 4.6, GPT-5.4, and Gemini 3.1 Pro process 1M tokens natively with near-perfect needle-in-a-haystack recall. Your `plan_event_chunks` in `token_budget.py` destroys coreference resolution (e.g., if a bidder signs an NDA in chunk 1 and drops out in chunk 4). **Delete the chunking logic.** Pass the entire chronology array in a single shot and utilize Anthropic Prompt Caching / OpenAI Context Caching.

**(b) Solving Reproducibility (The N-Run Protocol)**
OpenAI deprecated `seed` guarantees in late 2025. You cannot claim computational reproducibility on a single probabilistic run. You must adopt the framework established by **Wang & Wang (arXiv:2503.16974, 2025)**, which proved that aggregating 3 to 5 independent runs dramatically bounds LLM variance in complex finance tasks.
*   **Action:** Modify `pipeline/orchestrator.py`. Execute Stage 3B (`extract events`) **$N=3$ or $N=5$ times** concurrently at `temperature=0.2`.
*   **Action:** In `extract/merge.py`, write a consensus resolver. Only pass an event to Stage 4 if it was extracted in a majority of runs (aligned by the deterministic `SpanRegistry` exact quote match). Take the median of continuous variables (`value_per_share`) and the majority vote of boolean signals.

**(c) What the Methodology Section Must Say**
Draft your paper defensively. Position the LLM as an *indexer*, not an oracle:
> "We construct our dataset utilizing an ensemble of LLM agents (Claude Sonnet 4.6) operating over frozen SEC filing texts via native structured outputs. Recognizing that LLM inference exhibits irreducible distributional variance (Wang and Wang, 2025), we eschew single-shot extraction. Instead, we sample the extraction distribution five independent times per filing ($N=5$) and require a majority consensus for event inclusion. Crucially, the LLM functions strictly as a semantic indexer; every extracted event must supply a verbatim textual substring (`anchor_text`). A deterministic Python pipeline cryptographically verifies this substring against the hashed SEC filing text. Unverified events are discarded. Econometric classifications (such as formal vs. informal bids or market-relative dropouts) are executed exclusively by deterministic Python algorithms integrating external CRSP/COMPUSTAT data, isolating the LLM from subjective economic analysis (Ludwig et al., 2025)."

**(d) Preempting Referee Objections**
*   *Objection:* "How do we know the LLM didn't hallucinate a bid value?"
    *   *Defense:* "Our architecture fails closed. Any bid extracted by the LLM that cannot be exactly substring-matched to the immutable SEC text via our deterministic `SpanRegistry` is marked `UNRESOLVED` and structurally blocked from the dataset."
*   *Objection:* "Your classification of 'Formal' is subject to prompt-engineering bias."
    *   *Defense:* "The LLM does not classify bids. It only extracts boolean textual features (e.g., 'did the text mention a draft merger agreement?'). The classification mapping is a transparent, published Python cascade (`classify.py`) that can be audited and adjusted by future researchers without re-running the language models."
*   *Objection:* "I cannot replicate your LLM output because APIs change."
    *   *Defense:* "We provide a complete replication package containing the 'Frozen Inference Log'—a SQLite database containing the exact API payloads, adaptive thinking traces, and unparsed JSON responses. Researchers can perfectly replicate our final CSV dataset purely by running our deterministic Python transformation code over this archived log, entirely bypassing API non-determinism."
