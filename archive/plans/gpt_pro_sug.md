I would not salvage the monolithic skill as the production extractor. Parts of it can survive as bounded helpers, but the core design is wrong. The real problem is not just prompt length. It is that one model is being asked to do source discovery, section selection, entity resolution, process-state inference, legal/economic classification, chronology ordering, and final row writing without a stable intermediate representation. That guarantees drift.

The taxonomy gap is also larger than the three missing labels you named. Alex’s instructions already make sale-process initiation, investment-bank retention, final-round announcements and deadlines, execution, termination/restart, dropout subtypes, and press-release events first-class chronology objects, and they preserve bid ranges rather than collapsing them. A bid-centric extractor will keep failing even with a better prompt. 

My design would be code-first, evidence-first, and policy-driven.

## 1. Pipeline stages

| Stage                              | Input → Output                                                           | Who does it                                 | Instruction size                      | Gate condition                                                                                         |
| ---------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| 0. Deal registry                   | `deal_seed.csv` → `deal_manifest.json`                                   | Script                                      | none                                  | Target, acquirer, announcement date, and known URLs resolve to one deal record                         |
| 1. Filing discovery                | deal manifest → `filing_candidates.json` and `preferred_filing_set.json` | Script                                      | none                                  | Preferred filing set chosen by deterministic scoring; runner-ups retained if close                     |
| 2. Filing fetch + canonicalization | filing set → `canonical_doc.jsonl`                                       | Script                                      | none                                  | Raw HTML/text preserved; every paragraph gets stable IDs, DOM path, offsets, accession, URL            |
| 3. Chronology section localization | canonical doc → `chronology_spans.json`                                  | Script first, fallback agent only if needed | ~250–400 words                        | “Background of the Merger/Offer/Transaction” span found, or flagged                                    |
| 4. Temporal scaffolding            | chronology spans → `dated_blocks.jsonl`                                  | Script                                      | none                                  | All explicit dates normalized to intervals with precision flags; unresolved date mentions flagged      |
| 5. Entity + alias registry         | chronology text → `entities.json`                                        | Agent + script                              | ~400–600 words                        | Every bidder, IB, activist, target, acquirer, advisor, and anonymous placeholder has stable ID/aliases |
| 6. Process segmentation            | entities + chronology → `processes.json`                                 | Agent + script                              | ~400–600 words                        | Every event belongs to active process, stale prior process, restarted process, or `unknown`            |
| 7. Atomic fact extraction          | entities + processes + dated blocks → `facts.jsonl`                      | Agent                                       | ~700–900 words plus schema card       | Every fact has source span, raw quote, entity refs, process ID, date interval, and typed attributes    |
| 8. Deterministic policy engine     | facts → `ledger_canonical.parquet`                                       | Script                                      | none                                  | No free-text business logic remains; every row has `rule_id` and provenance                            |
| 9. Model-view projection           | canonical ledger → `ledger_model.csv`                                    | Script                                      | none                                  | Expansion, ordering, bidderID rendering, and derived fields happen deterministically                   |
| 10. Ambiguity arbitration          | flagged facts/rows → `adjudications.jsonl`                               | Small agent or human                        | ~200–300 words with finite choice set | Every unresolved case is either explicitly resolved or held out                                        |
| 11. Validation + diffing           | ledger + gold set → `validation_report.html` / mismatch workbook         | Script                                      | none                                  | Benchmarks, invariants, and audit checks pass                                                          |
| 12. Batch QA + release             | accepted batch → final export bundle                                     | Human + script                              | 1-page rubric                         | Sample audit and drift checks pass before next tranche                                                 |

A few implementation details matter:

* The internal primary key should be `event_uuid`, not `bidderID`.
* `bidderID` should be rendered only at export time from a deterministic sort key. Alex’s non-integer bidderIDs are a presentation artifact for inserted events, not a good internal key. 
* The most important artifact is not the CSV. It is `facts.jsonl`: the evidence ledger.

## 2. Where agents add value, and where scripts should replace them

Agents should only do bounded semantic work:

* identify the relevant chronology span when headers are nonstandard;
* resolve aliases and party roles from messy legal prose;
* segment the narrative into process episodes;
* extract atomic facts with citations;
* adjudicate genuinely ambiguous cases from a finite menu.

Scripts should own everything mechanical:

* EDGAR search, candidate ranking, downloading, and retry logic;
* HTML-to-canonical-text conversion;
* date parsing and interval normalization;
* currency/per-share normalization;
* policy mapping from extracted features to event codes;
* grouped-event expansion rules;
* de-duplication;
* chronology sorting;
* bidderID rendering;
* CSV assembly;
* validation and benchmark diffing.

The design rule is simple: **agents extract evidence and bounded attributes; scripts decide final row structure**.

For example, an agent can extract this proposal fact:

```json
{
  "fact_type": "proposal",
  "entity_id": "bidder_b",
  "process_id": "p2",
  "whole_company": true,
  "price_lower": 7.5,
  "price_upper": 8.0,
  "explicit_indication_of_interest": true,
  "explicit_binding": false,
  "markup_merger_agreement": false,
  "final_round_state": "informal",
  "source_span": "..."
}
```

The script, not the agent, maps that to `Informal Bid`, preserves the range, and decides whether it belongs in the model view.

Things that should **never** be delegated to an LLM:

* midpoint vs lower-bound choice for ranges;
* whether to expand one aggregate statement into 5 separate rows;
* date formatting;
* bidderID numbering;
* final CSV order;
* duplicate suppression.

## 3. Consistency enforcement

The way to make Deal 1 and Deal 390 come out the same is to move consistency out of prose and into code.

### Freeze the ontology in code

Use a versioned ontology file, not a growing instruction memo. The ontology should include at least these families:

* sale initiation / process start;
* access / NDA;
* intermediary events (`IB`, `IB Terminated`, legal-advisor auxiliary facts if needed);
* proposals;
* screening / final-round state changes;
* dropout subtypes;
* exclusivity;
* execution;
* termination / restart;
* press releases.

Alex’s spec already points in this direction. 

### Use two outputs, not one

You are trying to force one artifact to serve two jobs:

1. a faithful chronology of what the filing says;
2. a model-ready bidder/event table.

That is part of the current mess.

I would keep:

* a **canonical evidence ledger** that can contain aggregate events, interval dates, unresolved-but-cited facts, and provenance;
* a **model view** derived from that ledger using deterministic expansion and filtering rules.

That separation solves your row-count problem. “Correct row count” is not well-defined until the expansion policy is frozen.

### Preserve raw uncertainty

For any date or value that is not exact, store raw and normalized forms separately:

* `date_raw`
* `date_lower`
* `date_upper`
* `date_precision`

and

* `value_raw`
* `value_lower`
* `value_upper`
* `value_unit`
* `value_basis` (`per_share`, `enterprise_value`, `unknown`)

Do **not** collapse ranges during extraction. Alex’s schema explicitly keeps lower/upper fields for interval bids. 

### Require provenance on every fact and row

Every fact should carry:

* accession number;
* filing URL;
* section name;
* paragraph ID / DOM path;
* character offsets;
* short supporting quote;
* extractor version;
* policy version.

Every row in the canonical ledger should point back to one or more facts. No provenance, no row.

### Add a verifier pass

Run a second, smaller verifier on each extracted fact:

* `supported`
* `contradicted`
* `underspecified`

Only `supported` facts pass into the policy engine. This is how you prevent agent-instance variance from leaking into the final dataset.

### Freeze prompts and policies by batch

No prompt or policy edits mid-batch. Process deals in tranches, review drift, then version-bump.

## 4. The hard semantic problems

### A. Formal vs. informal classification

This should not be a free-form LLM label. It should be a deterministic classification over extracted features.

Have the agent extract these features for each proposal:

* whole-company yes/no;
* range yes/no;
* explicit “indication of interest” / nonbinding language;
* explicit “binding” / “final” language;
* bidder invited to final round yes/no;
* final-round state (`none`, `informal_final_round`, `formal_final_round`);
* draft or marked-up merger agreement submitted yes/no;
* exclusivity in effect yes/no.

Then classify:

1. **Formal** if any of:

   * marked-up or draft merger agreement submitted;
   * bidder is in a formal final round;
   * proposal is explicitly binding/final.

2. **Informal** if any of:

   * range bid;
   * explicit IOI / nonbinding language;
   * proposal occurs in an explicitly informal round.

3. **Escalate** if bilateral late-stage negotiation has no markup, no explicit binding language, and no clear round-state trigger.

That handles “informal-deadline bids” cleanly: a deadline alone does not make a bid formal. A formal state trigger does.

### B. When an expression of interest becomes a bid

Use a three-part test.

Record a regular bid only if all three are true:

1. it concerns the **entire company**;
2. it contains **economic consideration** that can be tied to the whole company;
3. it is communicated as a **proposal**, not just generic interest.

If it fails (1), exclude it from the primary bid ledger. Alex’s instructions explicitly say not to record bids for only part of the company. 

If it fails (2) or (3), map it to an initiation/interest event instead:

* `Bidder Interest`
* `Bidder Sale`
* `Target Sale`
* `Activist Sale`

depending on who moved the process. Alex’s start-of-sale instructions already separate these from normal bid rows. 

That is how I would handle your `$2.6B unsolicited letter with no NDA` problem. It should not become a “Formal Bid” by default. If it triggered the process, it is a sale-initiation event first; it becomes a regular bid row only if later evidence supports that treatment.

### C. Earlier terminated processes and old NDAs

You need explicit `process_id`s.

Rule set:

* A prior process gets its own `process_id`.
* NDAs from a stale process do **not** count toward auction classification for the active process unless the filing clearly says the NDA remained operative into the restarted process.
* If the company later restarts, record `Terminated` and `Restarted` as separate process-state events.
* If a bidder from the stale process reappears, do not assume carryover NDA coverage unless the filing says so; otherwise require a fresh NDA or mark `nda_status=unclear`.

Alex’s instructions explicitly say to ignore stale-process NDAs for the auction criterion while still recording termination/restart history. 

### D. Grouped bidders described only in aggregate

This is where your current row-count divergence comes from.

Alex’s instructions already allow aggregate recording: if multiple bidders made offers in a range and there is no bidder-specific information, record the group-level range. 

So the canonical rule should be:

* keep an **aggregate event** in the canonical ledger when the evidence is aggregate;
* expand to bidder-level rows **only** if group membership is exactly known and your expansion rule is fixed in code.

My recommendation:

* canonical ledger: allow `group_id`, `group_size`, `member_ids` (optional);
* model view: expand only when `member_ids` is complete and no bidder-specific conflicting facts exist.

Do not let an LLM decide ad hoc whether “six bidders” becomes six rows today and three rows tomorrow.

### E. Dropout, exclusion, and re-entry

Treat dropout as a persistent historical fact.

If a bidder drops and later re-enters:

* keep the original dropout row;
* create the later re-entry implicitly through a new NDA/proposal event or explicitly through a `reengaged` fact if the prose supports it.

Alex’s instructions are explicit that earlier dropout should still be recorded even when bidders re-enter. 

### F. Range bids and date normalization

Range bids:

* canonical ledger stores lower and upper bounds exactly as extracted;
* the model view can derive midpoint, lower bound, or interval treatment later.

Dates:

* use intervals, not fake precision;
* ordering should use `(process_rank, date_lower, date_upper, paragraph_order, within_paragraph_order)`.

That removes the current midpoint/lower-bound drift and fake-date drift.

## 5. Validation and benchmarking

I would benchmark in three layers.

### Layer 1: infrastructure tests

Before semantics, test:

* filing discovery;
* canonicalization;
* chronology span selection;
* provenance survival.

Acceptance:

* 100% correct preferred filing set on the 9 gold deals;
* 100% chronology span recall for all gold evidence paragraphs;
* 100% rows/facts traceable to source spans.

### Layer 2: semantic extraction tests

Benchmark against Alex’s 9 corrected deals using a mismatch workbook with categories:

* missing fact;
* extra fact;
* wrong entity;
* wrong process;
* wrong event code;
* wrong formality;
* wrong value bounds;
* wrong date interval;
* provenance missing.

Acceptance before wider batching:

* **exact match** on all gold bid rows for:

  * event code,
  * formal/informal,
  * lower/upper value bounds,
  * date interval ordering;
* exact or signed-off agreement on row counts by event family per deal;
* ≥95% precision/recall on non-bid lifecycle events (`NDA`, `IB`, `Drop*`, final-round events, `Executed`, `Terminated`, `Restarted`, sale-initiation events);
* 100% provenance coverage.

### Layer 3: out-of-sample release gate

The 9 deals are necessary, but they are not enough. Alex explicitly says those 9 were chosen from the middle because earlier deals were collected poorly. 

So before the remaining 381, I would create a **shadow validation set** of roughly 10–15 additional manually corrected deals drawn from the early, messy part of the database.

Only after that would I batch the remainder, in tranches of maybe 20–30 deals, with:

* random audit sample each tranche;
* all low-confidence or unresolved deals reviewed;
* no prompt/policy changes mid-tranche;
* drift dashboard by event family.

The key benchmark is not just overall F1. It is whether every remaining disagreement can be classified as one of:

1. extraction failure;
2. policy ambiguity;
3. gold-set error.

Until mismatches fall into those buckets cleanly, you are not ready to scale.

## 6. Similar work and what to borrow

I did not find an open-source project that already extracts takeover-auction chronologies from proxy backgrounds end-to-end. The closest useful work falls into six buckets.

**Legal contract extraction benchmarks.** CUAD is an expert-labeled legal benchmark with 13,000+ annotations across 510 commercial contracts and 41 review categories. The lesson is not “use CUAD directly”; it is that expert-labeled legal extraction improves only when the target schema is explicit and benchmarked. Your 9 corrected deals are the start of that, but they are too small to function as the whole supervision and validation strategy. ([arXiv][1])

**Human/AI document knowledge bases.** OpenContracts is built around curated, version-controlled document knowledge, with structured extraction APIs, document/corpus agents, and responses that carry sources and metadata. The architectural lesson is strong: keep the document knowledge base and extraction artifacts explicit, versioned, and reviewable. ([GitHub][2])

**Legal preprocessing toolkits.** Blackstone is a spaCy-based pipeline for long-form unstructured legal text, and LexNLP provides legal-aware segmentation, clause/document classifiers, and extraction for dates, amounts, conditions, and other legal facts. These are useful for preprocessing and candidate feature extraction, not for solving your event ledger by themselves. ([GitHub][3])

**Document-level event extraction.** Recent document-level event extraction work such as DEED, and broader IE frameworks like DyGIE++, are closer to your true task than generic QA because they focus on event mention extraction, coreference, and cross-event dependencies at the document level. The limitation is data hunger: these approaches become compelling if you eventually build a much larger labeled set, but not with only 9 gold deals. ([ACL Anthology][4])

**Temporal timeline extraction.** Narrative timeline work and TempEval-style temporal reasoning are useful because your hardest errors are often temporal, not lexical. The lesson is to model event ordering and date uncertainty explicitly rather than hoping the model’s prose summary gets chronology right. ([ACL Anthology][5])

**Declarative LLM document ETL and EDGAR infrastructure.** DocETL is relevant because it treats long-document processing as a rewriteable, evaluable pipeline rather than a single prompt, and reports sizable accuracy gains over strong baselines on complex document tasks. For filing access, the SEC’s official APIs provide unauthenticated JSON submissions history, and EDGAR-CRAWLER shows the value of converting raw filings into structured JSON before NLP, though its section parser is aimed at 10-K/10-Q/8-K rather than proxy/tender-offer forms. ([arXiv][6])

## 7. What I think you’re getting wrong

A few things.

### You are slightly understating the architecture failure

The issue is not only “too many responsibilities in one prompt.” The prompt is being used as an implicit ontology, a business-rule engine, and an audit trail. Those must be explicit system components.

### The primitive should be the fact, not the row

Your current design seems row-first. That is the core mistake. The row is a projection. The primitive is an evidence-backed atomic fact inside a process episode.

### You probably need two datasets, not one

A faithful chronology ledger and a model-ready bidder panel are not the same object. Trying to make them the same is what creates inconsistent expansion rules.

### The taxonomy problem is broader than you described

The missing-event issue is not just `IB Terminated`, `Target Interest`, and `Exclusivity`. Alex’s own instructions already imply a much wider process-state ontology. The system should be organized around process-state changes, not around bids.

### The 9-deal gold set is not a sufficient release gate

It is a calibration set. It is not a representative validation set, because Alex says earlier deals are worse. You need an out-of-sample manual shadow set before full batching. 

### You may be overcomplicating the “agentic” part

Once the right filing and the right section are isolated, this is not really a broad RAG problem. It is a controlled long-document extraction problem with linear chronology. Most of the machinery should be deterministic.

### You are missing an ontology steward

Someone has to own policy changes, mismatch adjudication, and version freezes. Without that, every new edge case becomes prompt prose again.

My bottom line is this: build a small number of narrow agents around a rigid evidence schema, and push every repeatable rule into code. The thing that should grow from deal 1 to deal 390 is the policy table and the regression suite, not the extractor prompt.

[1]: https://arxiv.org/abs/2103.06268 "https://arxiv.org/abs/2103.06268"
[2]: https://github.com/Open-Source-Legal/OpenContracts "https://github.com/Open-Source-Legal/OpenContracts"
[3]: https://github.com/ICLRandD/Blackstone "https://github.com/ICLRandD/Blackstone"
[4]: https://aclanthology.org/2021.nuse-1.4.pdf?utm_source=chatgpt.com "Document-level Event Extraction with Efficient End-to- ..."
[5]: https://aclanthology.org/P12-1010/ "https://aclanthology.org/P12-1010/"
[6]: https://arxiv.org/abs/2410.12189 "https://arxiv.org/abs/2410.12189"

