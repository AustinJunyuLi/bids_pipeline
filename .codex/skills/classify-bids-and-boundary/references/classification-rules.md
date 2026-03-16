# Classification Rules and Judgment Schemas

Formal/informal classification rules, boundary determination, initiation
judgment, and the full judgments.jsonl schema.

## Formal/Informal Classification Rules

Apply in **priority order**. The first matching rule wins. Each proposal
event in events.jsonl receives exactly one `bid_classification` judgment.

### Rule 1: Post-Final-Round Announcement (formal)

**Trigger:** The proposal date falls after the announcement of a
formal round (`final_round_ann` or `final_round_ext_ann` event date).

**Classification:** `formal`
**Rule name:** `post_final_round_announcement`

**Filing signal language:**
- "submit best and final offers"
- "final round proposals"
- "binding proposals"
- "definitive proposals"
- The proposal occurs chronologically after a round announcement event.

**Example:** The board sends process letters on October 1 requesting
final bids by October 15. Party A submits a bid on October 12. This
bid is classified as formal because it follows the final round
announcement.

### Rule 2: Merger Agreement Draft (formal)

**Trigger:** The event's `evidence_attributes.accompanied_by_merger_agreement`
is `true`.

**Classification:** `formal`
**Rule name:** `merger_agreement_draft`

**Filing signal language:**
- "submitted a draft merger agreement"
- "accompanied by a markup of the merger agreement"
- "included a revised draft of the definitive agreement"

**Example:** Party B submits a $42/share offer accompanied by a draft
merger agreement on November 3. Classified as formal regardless of
round timing.

### Rule 3: Indication of Interest or Range Bid (informal)

**Trigger:** Either:
- The event's `evidence_attributes.filing_language` contains
  "indication of interest" (case-insensitive), OR
- The event has both `value_lower` and `value_upper` populated (a
  range bid rather than a point bid).

**Classification:** `informal`
**Rule name:** `indication_or_range`

**Filing signal language:**
- "indication of interest"
- "preliminary indication"
- "non-binding indication"
- "range of $38 to $42 per share"
- "indicated interest at a price of approximately..."

**Example:** Party C submits a "preliminary indication of interest at
$38-$42 per share" on September 15. Classified as informal due to
both the "indication of interest" language and the range format.

### Rule 4: Default (informal)

**Trigger:** No other rule matches.

**Classification:** `informal`
**Rule name:** `default_informal`

**Rationale:** The model's prior is that proposals are informal unless
there is affirmative evidence of formality. This prevents over-
classification of ambiguous proposals.

**Example:** Party D "expressed interest at $40 per share" in a letter
to the board, with no process letter context and no merger agreement.
Classified as informal by default.

### Priority Conflicts

When signals conflict (e.g., a post-final-round "indication of
interest"), the higher-priority rule wins:

- Rule 1 beats Rule 3: A post-final-round submission labeled
  "indication" is still classified as `formal` because Rule 1 has
  higher priority. Set `confidence: "medium"`.
- Rule 2 beats Rule 3: A range bid with a merger agreement draft is
  `formal`. Rule 2 takes priority.

Log all priority conflicts to `decisions.jsonl`.

---

## Boundary Determination

The formal boundary is the event (or narrow event range) where
informal bidding transitions to formal bidding.

### Procedure

1. **Identify the last informal proposal** and the **first formal
   proposal** (by date).
2. **The boundary event** is typically the round announcement
   (`final_round_ann` or equivalent) that triggers formal
   submissions. If no explicit round announcement exists, use the
   date of the first formal proposal.
3. **Record confidence:**
   - `high`: Clear round announcement with process letter.
   - `medium`: Boundary identifiable but transition is gradual.
   - `low`: No clear demarcation; best interpretation only.
4. **Record alternative interpretation** if another boundary event
   is plausible.

### Edge Cases

- **No formal proposals:** Some deals end with only informal bids
  (e.g., the deal terminates). Record `formal_boundary` as `null`
  with a note.
- **Single proposal:** If only one proposal exists and it is the
  executed bid, classify it based on the rules. The boundary may be
  the proposal itself.
- **Transition zone:** If the filing describes a gradual shift over
  multiple events, record the boundary as the most defensible single
  event and describe the zone in `alternative_basis`.

---

## Initiation Judgment

Determine who initiated the deal process.

### Types

| Value | Definition | Typical Filing Signal |
|-------|-----------|---------------------|
| `target_driven` | Board authorized sale exploration | "the board determined to explore strategic alternatives" |
| `bidder_driven` | Unsolicited offer triggered process | "Party A approached the Company with an unsolicited proposal" |
| `activist_driven` | Activist pressure drove the decision | "following the public campaign by [activist], the board formed a special committee" |
| `mixed` | Multiple initiating forces contributed | Both board authorization and external pressure present |

### Recording

Record basis (the specific factual reason), source_text (verbatim
quote), confidence, and alternative interpretation. Most deals have
a clear initiator, but some have multiple contributing forces.

---

## judgments.jsonl Full Schema

One JSON line per judgment. The file contains three judgment types:
`bid_classification`, `initiation`, and `formal_boundary`.

### Judgment Type: bid_classification

One per proposal event.

```json
{
  "judgment_type": "bid_classification",
  "scope": "event",
  "scope_id": "pet_e15",
  "value": "formal",
  "classification_rule": "post_final_round_announcement",
  "confidence": "high"
}
```

```json
{
  "judgment_type": "bid_classification",
  "scope": "event",
  "scope_id": "pet_e08",
  "value": "informal",
  "classification_rule": "indication_or_range",
  "confidence": "high"
}
```

```json
{
  "judgment_type": "bid_classification",
  "scope": "event",
  "scope_id": "pet_e22",
  "value": "formal",
  "classification_rule": "merger_agreement_draft",
  "confidence": "high"
}
```

```json
{
  "judgment_type": "bid_classification",
  "scope": "event",
  "scope_id": "pet_e11",
  "value": "informal",
  "classification_rule": "default_informal",
  "confidence": "medium"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| judgment_type | string | yes | `"bid_classification"` |
| scope | string | yes | `"event"` |
| scope_id | string | yes | event_id of the proposal |
| value | string | yes | `"formal"` or `"informal"` |
| classification_rule | string | yes | Rule name that determined classification |
| confidence | string | yes | `high` / `medium` / `low` |

### Judgment Type: initiation

One per deal.

```json
{
  "judgment_type": "initiation",
  "scope": "deal",
  "scope_id": "petsmart-inc",
  "value": "target_driven",
  "basis": "Board authorized sale exploration on August 13, 2014.",
  "source_text": "the board determined to explore strategic alternatives for the Company",
  "confidence": "high",
  "alternative_value": "mixed",
  "alternative_basis": "Activist pressure from Jana Partners preceded board decision by 3 months."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| judgment_type | string | yes | `"initiation"` |
| scope | string | yes | `"deal"` |
| scope_id | string | yes | deal_slug |
| value | string | yes | `target_driven` / `bidder_driven` / `activist_driven` / `mixed` |
| basis | string | yes | Factual reason for the judgment |
| source_text | string | yes | Verbatim quote supporting the judgment |
| confidence | string | yes | `high` / `medium` / `low` |
| alternative_value | string | no | Next-best interpretation |
| alternative_basis | string | no | Reason for the alternative |

### Judgment Type: formal_boundary

One per deal.

```json
{
  "judgment_type": "formal_boundary",
  "scope": "deal",
  "scope_id": "petsmart-inc",
  "value": "pet_e30",
  "basis": "Final round announcement on November 1 requested binding proposals.",
  "source_text": "the board directed the remaining bidders to submit best and final offers by November 15",
  "confidence": "high",
  "alternative_value": "pet_e28",
  "alternative_basis": "Process letter sent October 28 could also mark the transition."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| judgment_type | string | yes | `"formal_boundary"` |
| scope | string | yes | `"deal"` |
| scope_id | string | yes | deal_slug |
| value | string | yes | event_id of boundary event (or `null` if no formal proposals) |
| basis | string | yes | Factual reason for boundary placement |
| source_text | string | yes | Verbatim quote supporting the boundary |
| confidence | string | yes | `high` / `medium` / `low` |
| alternative_value | string | no | Alternative boundary event_id |
| alternative_basis | string | no | Reason for the alternative |

---

## Judgment Types (v1)

The current schema supports three judgment types:
- `bid_classification` -- formal/informal per proposal
- `initiation` -- who started the deal process
- `formal_boundary` -- where informal bidding transitions to formal

Future versions may add additional types (e.g., `deal_rationale`,
`consideration_structure`). The schema is extensible by adding new
`judgment_type` values with their own field requirements.
