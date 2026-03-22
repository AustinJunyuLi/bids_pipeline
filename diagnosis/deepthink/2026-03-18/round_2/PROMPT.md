# Codebase Review Request — bids-data-pipeline (Round 2)

**Commit:** 942b6e7 (2026-03-18)
**Files uploaded:** 9 consolidated files covering ~107 source files
**Prior round:** Round 1 (2026-03-17) — see file 08 for feedback + our assessment

## How to Read the Uploaded Files

| File | Contents |
|------|----------|
| 00_PROJECT_OVERVIEW.md | CLAUDE.md, AGENTS.md, git history, seeds.csv, config |
| 01_MODELS_AND_SCHEMAS.md | All Pydantic models + LLM output schemas |
| 02_PREPROCESSING.md | Raw EDGAR fetch, preprocess source, evidence scanning |
| 03_LLM_INFRASTRUCTURE.md | LLM backend protocol, providers, prompts, token budgeting |
| 04_EXTRACTION.md | CLI, actor/event extraction, chunk merging, recovery audit |
| 05_QA_ENRICH_EXPORT.md | QA span resolution, enrichment classification, CSV export |
| 06_TESTS.md | Key test files in full, rest summarized |
| 07_SKILLS_AND_ALEX.md | **READ THIS CAREFULLY** — skills vs pipeline separation, Alex's full collection instructions |
| 08_ROUND1_AND_BENCHMARK.md | Round 1 feedback + our assessment + **Alex's complete hand-collected data for all 9 benchmark deals** |

**CRITICAL INSTRUCTIONS ON INTELLECTUAL HONESTY:**

I am a serious academic researcher. I need your **honest, independent judgment** — not agreement, not flattery, not validation.

1. **Do NOT open with compliments.** Go straight to substance.
2. **Do NOT agree with my analysis just because I presented it.** If my assessment of your Round 1 findings is wrong, push back.
3. **Challenge my assumptions.** If I ruled out an approach prematurely, say so.
4. **Distinguish your confidence levels.** "I am confident that X" vs "I suspect Y" vs "Z is speculative."
5. **Prioritize correctness over my feelings.**

**CRITICAL INSTRUCTIONS ON VERBOSITY AND DETAIL:**

1. **Do NOT abbreviate.** Show all reasoning.
2. **Be specific.** Cite file paths and line numbers.
3. **Your response should be VERY LONG.** A short response means you abbreviated.
4. **Verify your own reasoning.** Stress-test your recommendations against edge cases.

## CRITICAL FRAMING: Two Separate Systems

**You MUST keep these clearly separated in your analysis.**

### System 1: The Deterministic Pipeline (production code)

This is `pipeline/` — Python code that runs via CLI commands. It produces
the FINAL dataset for the academic paper. Files 00-06 contain this code.

```
Stage 1: raw fetch           DETERMINISTIC  (EDGAR API)
Stage 2: preprocess source   DETERMINISTIC  (regex evidence scanning)
Stage 3A: extract actors     LLM            (structured output → JSON)
Stage 3B: extract events     LLM            (structured output → JSON)
Stage 4: QA / span resolve   DETERMINISTIC  (substring matching, dedup)
Stage 5: enrich              DETERMINISTIC  (7 priority rules, cycles)
Stage 6: export              DETERMINISTIC  (CSV denormalization)
```

### System 2: The Deal-Agent Skills (facilitating tool)

These are Claude Code subagent PROMPT INSTRUCTIONS (not code). File 07
contains them. They serve three purposes:

1. **Quick preliminary extraction** before the pipeline's LLM config is tuned
2. **Testing hypotheses** about what LLMs can extract, informing pipeline design
3. **Complementary quality checks** the deterministic pipeline cannot do
   (count reconciliation reasoning, structural audit, initiation judgment)

Skills write pipeline-compatible output. But skill output is a DRAFT —
the pipeline is the authority for the final published dataset.

**Do NOT critique the skills as if they were the production pipeline.
Do NOT recommend deleting the skills. Assess them as a development and
exploration tool.**

## Your Task (Round 2)

### Part 1: Pipeline vs Alex's Requirements — Critical Calibration

Read Alex Gorbenko's full collection instructions in file 07 (section
"Alex Gorbenko's Collection Instructions"). Then read the actual pipeline
code (files 02-06).

For EVERY requirement Alex specifies, determine:

(a) **Does the pipeline handle this?** If yes, cite the specific file/function.
(b) **If not, WHAT exactly is missing?** Be precise — schema gap? Logic gap?
    External data needed?
(c) **Can it be made deterministic?** Or does it inherently require LLM
    judgment? What is the optimal approach?

Cover at minimum:
- Start of sale process (Section 3.2 in Alex's instructions)
- Investment bank retention (Section 3.3)
- Confidentiality agreements / NDAs (Section 3.4)
- Submitted bids with formal/informal classification (Section 3.5)
- Bidder dropouts with all 5 types (Section 3.6)
- Final round announcements and deadlines (Section 3.7)
- Executing the merger agreement (Section 3.8)
- Termination and restart (Section 3.9)
- All fields: bidder_type_note, bid_value_pershare, bid_value_lower/upper, all_cash, cshoc, comments

### Part 2: Alex's Hand-Collected Data as Benchmark

File 08 contains the COMPLETE event-level data from Alex's hand-corrected
Excel (`deal_details_Alex_2026.xlsx`) for all 9 benchmark deals. This is
the ground truth we must match.

**What the benchmark data shows (read file 08 carefully):**
- 35 columns per row including TargetName, Acquirer, BidderID, BidderName,
  bidder_type_note, bid_value_pershare, bid_value_lower/upper, bid_type
  (Formal/Informal), bid_date_rough, bid_date_precise, bid_note, all_cash,
  cshoc, and 3 comment fields
- BidderID uses non-integer sequencing (e.g., 0.3, 0.5, 0.7, 1, 2...)
  where fractional numbers are Alex's insertions between Chicago RA events
- Each deal has 15-50+ events covering: initiation, IB retention, NDAs,
  proposals, dropouts, round announcements, execution
- Comments contain rich qualitative annotations about legal counsel,
  sale process rationale, and bidder behavior
- "NA" values indicate fields that are intentionally blank per Alex's
  instructions (not missing data)

For a validation framework:
(a) Compare the pipeline's extracted events against these exact rows.
    What matching criteria should we use? (date proximity? event type?
    actor name fuzzy match?)
(b) What error categories matter most? (missed events vs extra events vs
    wrong field values?)
(c) How many hand-validated deals do we need for a credible validation in
    a JFE/RFS/JF paper? Alex has 9 — is that sufficient?
(d) Look at the SPECIFIC patterns in the data — e.g., Providence &
    Worcester has "[1] NDA bidder=25 parties, including Parties A, B |
    type=11S, 14F". How should the pipeline handle grouped NDA entries
    where 25 parties signed but only 2 are named?

### Part 3: Optimal LLM/Deterministic Mix

For EACH of Alex's requirements from Part 1, recommend the optimal approach:

| Approach | When to use |
|----------|-------------|
| Fully deterministic (regex/rules) | When filing text is structured enough |
| Deterministic + external data | When COMPUSTAT/CRSP/SDC fills the gap |
| LLM extraction + deterministic verification | When reading comprehension is needed but facts can be verified |
| LLM judgment (auditable) | When subjective judgment is genuinely required |

Be specific about which of Alex's requirements fall into which category.
Do not assume "LLM needed" without demonstrating why a deterministic
approach fails.

### Part 4: Skills as Facilitating Tool

Given that the skills exist as a development aid:
(a) What skill-generated outputs should eventually be promoted into the
    pipeline as new deterministic stages?
(b) What should remain as skill-only LLM judgment (complementary QA)?
(c) How should skill output feed back into pipeline development? (e.g.,
    skill finds that initiation judgment matters → we add
    `initiation_type` to `DealEnrichment` and implement a deterministic
    heuristic + human review flag)

### Part 5: Publication-Ready Architecture

For a JFE/RFS/JF paper:
(a) What must the methodology section say about LLM usage?
(b) How do we handle the fact that LLM outputs are not perfectly reproducible?
(c) What validation statistics should we report?
(d) What are the referee objections and how do we preempt them?

## HARD CONSTRAINT: Search for Current State of the Art

**Before answering, you MUST actively search the web for the latest developments as of March 2026.** Do not rely solely on your training data.

Specifically, search for and incorporate:

1. **Current frontier models:**
   - Claude Opus 4.6 and Sonnet 4.6 (Feb 2026) — 1M context, native JSON schema via `output_config.format`, extended thinking
   - GPT-5.4 — `reasoning_effort` (none/low/medium/high/xhigh), structured outputs
   - Gemini 3.1 Pro (Feb 19, 2026) — 1M context, 64K output, 77.1% ARC-AGI-2, Pydantic-native structured output, `thinking_level` parameter, improved finance domain
   - Search for anything newer

2. **Recent papers on LLM-assisted data collection (2025-2026):**
   - arxiv:2503.16974 — Wang & Wang on LLM consistency in finance tasks (3-5 run aggregation)
   - arxiv:2412.02065 — LLMs for costly dataset access (SEC filing extraction)
   - SSRN 5094968 — Ludwig, Mullainathan, Rambachan econometric framework
   - Search for others

3. **Reproducibility infrastructure:**
   - OpenAI `seed` parameter deprecated Oct 2025; determinism not guaranteed
   - Anthropic auto-caching (Feb 2026); temperature=0 + caching
   - Search for new deterministic guarantees from any provider

4. **Search for anything else relevant** — especially papers that extract event-level structured data from legal/financial documents.

Your recommendations must reflect actual March 2026 capabilities. When citing papers, verify they exist via search.

---
_Internal: snapshot_sha=942b6e7, round=2, date=2026-03-18, prior_round=diagnosis/deepthink/2026-03-17/round_1_
