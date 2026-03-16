# Event Taxonomy

Events are extracted from SEC filings using Alex Gorbenko's collection
instructions as the specification. Each event becomes one row in `events.jsonl`.

## Critical Rule

**Proposals are recorded as raw events.** The `bid_type` field (formal/informal)
is NOT assigned at extraction. It is assigned during structural enrichment
(Stage 4) after round structure is identified.

## Event Categories

### Process Initiation

| Type | When to Record | Fields |
|------|---------------|--------|
| `target_sale` | Board meeting where sale of target was agreed upon | date |
| `target_sale_public` | Public announcement of sale process | date |
| `bidder_sale` | A bidder's bid triggers a sale process | actor_id, date |
| `bidder_interest` | Bidder expresses interest (discussions, no bid) | actor_id, date |
| `activist_sale` | Activist pressures target to sell | actor_id, date |
| `sale_press_release` | Target announces strategic alternatives | date |
| `bid_press_release` | Bidder's bid becomes public | actor_id, date |

**Ordering:** Typically: Activist Sale -> Target Sale -> Target Sale Public ->
Sale Press Release. Or: Bidder Sale -> Bid Press Release.

**Filing signals:** "board determined to explore strategic alternatives",
"announced intention to explore a sale", "publicly announced a proposal",
"filed a Schedule 13D disclosing".

### Advisor Retention

| Type | When to Record | Fields |
|------|---------------|--------|
| `ib_retention` | Target retains investment bank / financial advisor | actor_id (bank name), date |

**Record ALL financial advisors, including pre-existing ones.** If the filing
describes an advisor as "already retained" or "retained for routine
preparedness," still record an `ib_retention` event. Use their first
appearance date in the filing. The model needs to know every advisor involved.

**Filing signals:** "retained J.P. Morgan as financial advisor", "engaged
Goldman Sachs to assist", "financial advisor to the Company", "with the
assistance of its outside financial advisors" (look for named advisors nearby).

Legal advisors are noted but don't need a date. Multiple financial advisors in
large deals -- record all.

### Confidentiality Agreements

| Type | When to Record | Fields |
|------|---------------|--------|
| `nda` | Bidder signs confidentiality/standstill agreement | actor_id, date |

**One row per signer.** If the filing says "the Company entered into
confidentiality agreements with 15 parties", create 15 NDA rows.

**Naming rules:**
- Winning bidder: use disclosed name
- Named losing bidders: use filing label ("Party A", "Bidder B")
- Unnamed bidders: use "Unnamed party N" (sequential)
- If later named, update the alias (not the stable ID)

**Cross-check:** Management often reports NDA progress to the board. Use these
summary counts to double-check the collected information.

### Proposals (Priced Bids)

| Type | When to Record | Fields |
|------|---------------|--------|
| `proposal` | Any priced bid to acquire the entire company | actor_id, date, value, value_lower, value_upper, value_unit, consideration_type, evidence_attributes |

**Whole-company bids only.** Only collect bids to acquire the entire company.
Bidders wanting a segment, division, or percentage stake are not recorded as proposal events.

**Value fields:**
- `value`: point estimate (midpoint if range, per_share if available)
- `value_lower` / `value_upper`: range bounds (for range bids)
- `value_unit`: `per_share` or `total`
- `consideration_type`: `cash`, `stock`, `mixed`, `cash_plus_cvr`

**evidence_attributes** (used later for formal/informal classification):
- `preceded_by_process_letter`: was a process letter sent before this bid?
- `accompanied_by_merger_agreement`: did bidder submit merger agreement draft?
- `post_final_round_announcement`: was a final round announced before this?
- `filing_language`: how the filing describes it ("indication of interest",
  "preliminary proposal", "final bid", etc.)

**Classification hints (for Stage 4, NOT extraction):**
- "Informal indication of interest" or range bids -> informal
- Post-final-round bids or bids with merger agreement draft -> formal

### Dropouts

| Type | When to Record | Fields |
|------|---------------|--------|
| `drop` | Bidder informs they are dropping out | actor_id, date |
| `drop_below_m` | Bidder says valuation is below market value | actor_id, date |
| `drop_below_inf` | Bidder says valuation is below their informal bid | actor_id, date |
| `drop_at_inf` | Bidder says valuation equals their informal bid | actor_id, date |
| `drop_target` | Target does not invite bidder to the final round | actor_id, date |

**Filing signals:** "informed the Company that it was withdrawing", "indicated
it would not be competitive", "the board determined to allow [N] bidders to
proceed" (implying others were dropped), "notified the eliminated parties".

Bidders sometimes re-enter the bidding -- still record the earlier dropout.

### Round Structure

| Type | When to Record | Fields |
|------|---------------|--------|
| `final_round_inf_ann` | Announcement of informal bid deadline | date |
| `final_round_inf` | Deadline for informal bids | date |
| `final_round_ann` | Announcement of formal/final round | date |
| `final_round` | Deadline for formal/final bids | date |
| `final_round_ext_ann` | Announcement of extended deadline | date |
| `final_round_ext` | Extended deadline for bids | date |

**Mandatory pairing rule:** Round events come in announcement + deadline
pairs. Every `*_ann` event MUST have a corresponding deadline event, and
vice versa. The announcement date is when bidders are notified; the deadline
date is when bids are due. They are always separate events even if the
filing describes them in one sentence. If the deadline date equals the
announcement date, still create both events.

**Filing signals:** "sent final round process letters", "requested bidders to
submit a final binding offer", "set the deadline for submission of final bids",
"asked the bidders to submit improved bids".

### Execution

| Type | When to Record | Fields |
|------|---------------|--------|
| `executed` | Merger agreement executed/signed | actor_id (winner), date |

**Filing signals:** "the parties executed the merger agreement", "entered into
the Merger Agreement".

### Process Lifecycle

| Type | When to Record | Fields |
|------|---------------|--------|
| `terminated` | Earlier sale process terminated | date |
| `restarted` | Sale process restarted after termination | actor_id (if bidder-initiated), date |

Record `terminated` if the deal was terminated by the target due to lack of
interest. Record `restarted` if the sale process was restarted later (may have
an entirely different set of bidders).

## Lifecycle Closure

After extraction, every actor must have a terminal status:

| Status | Meaning |
|--------|---------|
| `bid` | Submitted at least one priced proposal |
| `dropped` | Informed the company they were withdrawing |
| `dropped_by_target` | Not invited to continue |
| `winner` | Executed merger agreement |
| `stale` | From a terminated prior cycle |
| `advisor` | Financial/legal advisor, not bidder |
| `unresolved` | No terminal event found -- **hard flag**, `needs_review` |

If an NDA signer has no subsequent events (no bid, no dropout), their status
is `unresolved` and the deal is flagged `needs_review`.

**Lifecycle-event consistency rule:** Every non-advisor actor whose terminal
status is `dropped`, `dropped_by_target`, or `winner` MUST have a
corresponding event in `events.jsonl` (a `drop*` event, or `executed`).
If the filing has no explicit dropout statement but the actor clearly stopped
participating (e.g., bound by standstill, never bid in formal rounds), record
a `drop` event on the date their participation effectively ended (typically
the merger execution date) with a `raw_note` explaining the inference.
If the date is genuinely unknowable, flag `needs_review`.
