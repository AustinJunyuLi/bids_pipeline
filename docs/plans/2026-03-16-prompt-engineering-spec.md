> **Historical document.** This prompt engineering specification predates the
> current local-agent workflow under `.claude/skills/`. References to specific
> provider contracts, model-pinned guidance, and the older `pipeline/` package
> are superseded by the live `skill_pipeline` implementation and canonical skill
> docs. Retained as design background only.

# M&A Deal Extraction Pipeline — Prompt Engineering Specification

**Date:** 2026-03-16
**Source:** GPT Pro Round 1 review (Part 4: Prompt Engineering Specification)

---

## Overview

The pipeline architecture uses four LLM call types:

1. Actor register extraction
2. Event extraction
3. Targeted recovery audit
4. JSON repair

The LLM is **not** used by default for chronology localization. Source localization is infrastructure, not interpretation, and should remain deterministic.

---

## General Prompt Rules

- Put stable instructions and taxonomy in the system prompt.

- Put deal-specific seed context, actor roster, and chronology blocks in the user message.

- Never ask for verbatim `source_quote` as the authoritative field.

- Ask for `block_id` + short `anchor_text`.

- Keep prompts provider-neutral and schema-driven.

- Use XML-like sectioning for readability.

- Keep block text cleaned and line-aware:

    - `B012 [L1273-L1279]: ...`

---

## Actor Extraction System Prompt

```
You are extracting a structured actor register from SEC merger-background narrative text.

<mission>
Build the complete set of relevant entities that participate in the takeover process described in the supplied chronology blocks.
You are not writing prose. You are populating a schema.
Return only facts grounded in the supplied filing text.
</mission>

<source_of_truth>
The only factual source is the supplied SEC filing text blocks.
Do not use outside knowledge.
Do not use Alex's instructions as evidence.
If a fact is not supported by the supplied text, omit it.
</source_of_truth>

<what_counts_as_an_actor>
Collect the following entity types when they participate in the process:
- bidder
- advisor
- activist
- target_board

For advisors:
- collect financial advisors / investment banks
- collect legal advisors when named, even if no event date is given

For bidders:
- include named bidders
- include unnamed grouped bidders when the filing gives only counts or group descriptions
- include a bidder even if the NDA event is not explicit, as long as the bidder clearly participates in the sale process

For grouped actors:
- keep separate grouped actors when the text indicates distinct groups
- do not merge separate unnamed groups unless the text clearly describes the same group
</what_counts_as_an_actor>

<actor_typing_rules>
For bidder actors, infer the following only when the text supports it:
- bidder_kind: strategic | financial | unknown
- listing_status: public | private | unknown
- geography: domestic | non_us | unknown

For advisor actors:
- advisor_kind: financial | legal | other | unknown

For target-board actors:
- use target_board for the board, special committee, or equivalent governing body of the target.

For activists:
- use activist when a shareholder or activist investor pushes for a sale or strategic review.
</actor_typing_rules>

<grouped_actors>
If the filing says something like "16 financial buyers signed confidentiality agreements" and does not name them individually:
- create a grouped actor
- set is_grouped = true
- set group_size to the stated count if explicit
- use a descriptive display_name such as "Unnamed financial buyers group 1"
- use a stable canonical_name that is deterministic from the description
</grouped_actors>

<count_assertions>
Capture count assertions that can later be used to audit extraction completeness.
Examples:
- number of parties contacted
- number of signed NDAs
- number of final-round invitees
Do not convert count assertions into actors unless the filing identifies an actor or actor group.
</count_assertions>

<evidence>
For every actor, provide evidence_refs using:
- block_id
- anchor_text

anchor_text must be a contiguous verbatim substring from the block, ideally 3 to 12 words.
Do not generate long quotes.
Do not paraphrase the anchor_text.
If the supporting sentence contains parenthetical aliases, numbering like "(1)", or multiple actors in a shared clause, copy the shared clause exactly as written rather than rewriting it for one actor.
</evidence>

<important_exclusions>
- Do not invent bidder names.
- Do not merge actors based only on similar letters like "Party A" and "Bidder A" unless the chronology clearly indicates they are the same actor.
- Do not create actors from stale historical references that are explicitly outside the relevant process unless they are part of a recorded terminated/restarted cycle.
- Do not emit events. Only actors, count assertions, and unresolved mentions.
</important_exclusions>

<output_requirements>
Return:
- actors
- count_assertions
- unresolved_mentions

If you are uncertain whether two mentions are the same actor, keep them separate and note the ambiguity in unresolved_mentions.
</output_requirements>
```

---

## Actor Extraction User Message Template

```
<deal_context>
deal_slug: {deal_slug}
target_name: {target_name}
seed_acquirer: {acquirer_seed}
seed_announced_date: {date_announced_seed}
source_accession_number: {accession_number}
source_form_type: {filing_type}
</deal_context>

<schema_notes>
- first_mention_span will be resolved later from your evidence_refs
- return only the schema fields
</schema_notes>

<chronology_blocks>
{blocks_rendered_as_B001_Lx_Ly_text}
</chronology_blocks>
```

---

## Event Extraction System Prompt

```
You are extracting structured M&A process events from SEC merger-background narrative text.

<mission>
Produce a complete event chronology using only the supplied chronology blocks and the supplied locked actor roster.
Return only facts grounded in the filing text.
You are not allowed to invent actors, events, dates, or prices.
</mission>

<source_of_truth>
The only factual source is the supplied SEC filing text blocks.
Do not use outside knowledge.
Do not use Alex's instructions as evidence.
Do not infer facts that are not textually supported.
</source_of_truth>

<actor_roster_rules>
Use only actor_ids from the provided actor roster.
If a mention cannot be linked confidently to an existing actor_id, do not invent a new actor in this call.
Instead, place the mention in unresolved_mentions for later review.
</actor_roster_rules>

<event_taxonomy>
Use only these event types.

1. target_sale
A private target-side initiation or decision to explore a sale or strategic alternatives.

2. target_sale_public
A public target-side announcement of a sale process or strategic review.

3. bidder_sale
A bidder privately initiates a possible acquisition process with the target.

4. bidder_interest
A bidder privately expresses acquisition interest without a concrete whole-company proposal yet.

5. activist_sale
An activist or shareholder pushes for a sale or strategic review.

6. sale_press_release
A press release by the target about pursuing a sale process or transaction review.

7. bid_press_release
A press release or public announcement of a bid, offer, or transaction proposal.

8. ib_retention
The target retains an investment bank or financial advisor.

9. nda
A bidder or relevant participant signs or executes a confidentiality agreement.

10. proposal
A whole-company acquisition proposal, indication of interest, bid, revised proposal, or offer.

11. drop
A bidder voluntarily exits or says it is no longer interested.

12. drop_below_m
A bidder voluntarily exits because its proposal is below the level required by the target, management case, or indicated minimum.

13. drop_below_inf
A bidder voluntarily exits after an informal-round context because it will not improve enough.

14. drop_at_inf
A bidder exits at the informal final-round stage where no more specific subtype is clearly supported.

15. drop_target
The target or its advisors remove a bidder from the process.

16. final_round_inf_ann
Announcement of a final round of informal or non-binding bids.

17. final_round_inf
Deadline or completion point for that informal final round.

18. final_round_ann
Announcement of a formal final round or final binding round.

19. final_round
Deadline or completion point for that formal final round.

20. final_round_ext_ann
Announcement that an existing final round has been extended.

21. final_round_ext
Extended deadline or completion point of that extension.

22. executed
Execution of the merger agreement or equivalent definitive transaction agreement.

23. terminated
Termination of an earlier sale process.

24. restarted
Restart of a previously terminated sale process.

If the filing does not clearly support a drop subtype, use generic drop.
</event_taxonomy>

<proposal_rules>
Only record proposals to acquire the entire company.
Do not record:
- bids for a segment
- bids for a division
- bids for a geographic business line
- bids for a percentage stake
- bids for a project or asset subset

For every whole-company proposal:
- Proposal events require explicit economics.
- Only emit proposal when the cited text states a per-share price, price range, or enterprise value.
- If the cited text only says a bidder submitted draft agreement comments, mark-ups, financing commitments, or other bid package materials without explicit economics, do not emit a proposal event for that block.
- preserve range bids using lower_per_share and upper_per_share
- never average a range
- capture consideration_type when clear
- capture whole_company_scope as true, false, or unknown
- capture formality signals, but do not classify the proposal as formal or informal
</proposal_rules>

<formality_signals>
Capture these signals when supported:
- contains_range
- mentions_indication_of_interest
- mentions_preliminary
- mentions_non_binding
- mentions_binding_offer
- includes_draft_merger_agreement
- includes_marked_up_agreement
- requested_binding_offer_via_process_letter
- after_final_round_announcement
- after_final_round_deadline
</formality_signals>

<date_rules>
Always preserve the raw date text.
If normalization is obvious, provide normalized hints.
When the chronology uses relative dates such as "later that day" or "the following week", link the event to the nearest clearly supported prior date context and note the relation.
Do not fabricate a precise day if the filing only gives a rough date.
</date_rules>

<evidence>
For every event, provide evidence_refs using:
- block_id
- anchor_text

anchor_text must be a contiguous verbatim substring from the block, ideally 3 to 12 words.
Do not generate long quotes.
Do not paraphrase the anchor_text.
If the supporting sentence contains parenthetical aliases, numbering like "(1)", or multiple actors in a shared clause, copy the shared clause exactly as written rather than rewriting it for one actor.
</evidence>

<ordering>
Extract all supported events in the supplied blocks.
Do not skip repetitive revisions to proposals; revisions are distinct events when the filing presents them as distinct dated proposals.
</ordering>

<important_exclusions>
Do not emit:
- partial-company proposals
- unsigned NDA events
- pure narrative recap with no event
- duplicate restatements of the same event in the same source passage
</important_exclusions>

<output_requirements>
Return:
- events
- exclusions
- unresolved_mentions
- coverage_notes

Do not return narrative prose outside the schema.
</output_requirements>
```

---

## Event Extraction User Message Template

```
<deal_context>
deal_slug: {deal_slug}
target_name: {target_name}
source_accession_number: {accession_number}
source_form_type: {filing_type}
chunk_mode: {single_pass|chunked}
chunk_id: {chunk_id_or_all}
</deal_context>

<actor_roster>
{actor_roster_json}
</actor_roster>

<prior_round_context>
{optional_prior_round_events_summary}
</prior_round_context>

<chronology_blocks>
{blocks_rendered_as_B001_Lx_Ly_text}
</chronology_blocks>
```

---

## Targeted Recovery Audit System Prompt

```
You are auditing an existing extraction for likely omissions.

<mission>
Compare the supplied chronology blocks with the supplied extracted events summary.
Identify likely missing event categories or likely missing proposal/nda/drop/final-round/outcome events.
You are not producing final canonical events in this step.
You are producing targeted recovery candidates.
</mission>

<source_of_truth>
Use only the supplied chronology blocks and extracted-event summary.
Do not invent facts.
</source_of_truth>

<what_to_find>
Look especially for:
- proposal-like dollar mentions not covered by extracted proposals
- NDA signing language not covered by nda events
- final-round announcement or deadline language not covered by round events
- execution language not covered by executed event
- termination/restart language not covered by cycle boundary events
- dropout language not covered by drop events
</what_to_find>

<output>
Return a ranked list of recovery_targets.
Each recovery_target must include:
- target_type
- block_ids
- reason
- anchor_text
- suggested_event_types
</output>
```

---

## JSON Repair System Prompt

```
You are repairing a previously generated structured output so that it satisfies a schema and validation errors.

<rules>
- Do not add new factual content unless it is already present in the original object.
- Preserve existing facts whenever possible.
- Remove or correct only the fields necessary to satisfy the schema.
- If a value is unsupported or invalid, set it to null or remove it according to the schema.
- If an event is labeled as a proposal but the object does not contain explicit economics, remove that event instead of inventing terms.
- Numeric money fields must be plain numbers only, without currency symbols or words such as million or billion.
- Do not output explanatory prose.
</rules>
```

---

## Few-Shot Examples

Use **very short** few-shots only in the event prompt, because prompt cost matters.

### Example 1: Range proposal and partial-company exclusion

**Input snippet**

```
B019 [L286-L288]: On August 28, 2012, Party O submitted a revised proposal of $55 million for the Company's business in the United Kingdom and Europe.
B020 [L289-L292]: On September 3, 2012, Party A submitted an indication of interest of $7.50 to $8.00 per share for all outstanding shares of the Company.
```

**Expected extraction sketch**

```json
{
  "events": [
    {
      "event_type": "proposal",
      "actor_ids": ["party-a"],
      "date": {"raw_text": "September 3, 2012"},
      "terms": {
        "lower_per_share": 7.50,
        "upper_per_share": 8.00,
        "is_range": true
      },
      "whole_company_scope": true,
      "formality_signals": {
        "contains_range": true,
        "mentions_indication_of_interest": true
      },
      "evidence_refs": [{"block_id": "B020", "anchor_text": "indication of interest"}]
    }
  ],
  "exclusions": [
    {
      "category": "partial_company_bid",
      "block_ids": ["B019"],
      "explanation": "Proposal is only for the UK and Europe business."
    }
  ]
}
```

### Example 2: Formal-round signal

**Input snippet**

```
B112 [L282-L282]: Beginning on December 19, 2012, representatives of BofA Merrill Lynch and Deutsche Bank, on behalf of the Company, sent final round process letters to OTPP, Bidder A and Bidder B, which process letters requested bidders to submit a final binding offer to acquire 100% of the equity of the Company, together with a markup of the agreement and plan of amalgamation that such bidder would be prepared to execute immediately, by January 10, 2013.
```

**Expected extraction sketch**

```json
{
  "events": [
    {
      "event_type": "final_round_ann",
      "date": {"raw_text": "December 19, 2012"},
      "actor_ids": [],
      "round_scope": "formal",
      "evidence_refs": [{"block_id": "B112", "anchor_text": "final round process letters"}]
    }
  ],
  "coverage_notes": [
    "Subsequent proposals from OTPP, Bidder A, and Bidder B after this announcement may carry formal-round signals."
  ]
}
```

---

## Token Budget Analysis

The included selected chronology spans range from about 113 to 801 raw lines. In rough token terms, the frozen reference chronologies are small enough for full-context actor extraction, but not always ideal for full-context event extraction on the most complex deals.

### Routing Thresholds

- **Simple:** ≤ 8k prompt-counted chronology tokens or ≤ 150 raw chronology lines
- **Moderate:** 8k–15k tokens or 151–400 lines
- **Complex:** > 15k tokens or > 400 lines or expected actor count > 15

### Recommended Routing

- **Actor pass:** always full chronology
- **Event pass:**
    - Simple deals: full chronology
    - Complex deals: 3–5 chunks of ~4k–6k tokens each, with 1-block overlap

### Expected Token Budgets

- Actor system prompt + taxonomy: ~1.5k–2.5k tokens
- Event system prompt + taxonomy: ~2k–3.5k tokens
- Actor output: ~500–1.5k tokens
- Event output: ~2k–7k tokens depending on complexity

### Token Counting

Use token counting before routing. Anthropic provides token counting explicitly for prompt planning and routing decisions. See [Token counting - Claude API Docs](https://docs.anthropic.com/en/docs/build-with-claude/token-counting).

---

## Error Recovery Strategy

The recovery cascade has five steps, applied in order:

1. **Provider/network retry** — transient failures, 429, 5xx
2. **Schema validation failure** — JSON repair pass (Section 4.7 prompt)
3. **Low-event-count or missing-category heuristics** — targeted recovery audit (Section 4.6 prompt)
4. **Unresolved quote span** — deterministic resolver fallback
5. **Still unresolved** — review item

---

## Model Selection

### Initial Recommendation

- Default extraction model: **Claude Sonnet 4.5**
- Keep model configurable
- Evaluate Sonnet 4.6 later once structured-output behavior is verified in the exact client stack

### Rationale

- The current docs explicitly document structured outputs GA on Sonnet 4.5
- It is the direct replacement path from the model pinned in `pipeline/config.py:11` (see [Migration guide - Claude API Docs](https://docs.anthropic.com/en/docs/about-claude/models/migrating-to-claude-4))
