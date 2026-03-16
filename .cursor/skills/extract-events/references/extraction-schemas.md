# Extraction Schemas

Schemas for all artifacts produced by the extract-events skill.

## events.jsonl

One JSON line per event. No actor_id on event rows -- actors are linked
via `event_actor_links.jsonl`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | string | yes | Unique within deal (e.g., `pet_e01`) |
| `event_type` | string | yes | From event taxonomy (23 types) |
| `date` | string | yes | YYYY-MM-DD (always populated) |
| `date_precision` | string | no | `exact` / `approximate` / `month_only` |
| `value` | float | no | Bid value -- proposals only (midpoint for ranges) |
| `value_lower` | float | no | Range lower bound |
| `value_upper` | float | no | Range upper bound |
| `value_unit` | string | no | `per_share` / `total` |
| `consideration_type` | string | no | `cash` / `stock` / `mixed` / `cash_plus_cvr` |
| `evidence_attributes` | object | no | Proposals only (see below) |
| `source_accession_number` | string | yes | Filing accession number |
| `source_line_start` | int | yes | Line number in .txt |
| `source_line_end` | int | yes | Line number in .txt |
| `source_text` | string | yes | Verbatim quote from filing |
| `raw_note` | string | no | Additional context or inference explanation |

### evidence_attributes (proposals only)

| Field | Type | Description |
|-------|------|-------------|
| `preceded_by_process_letter` | boolean | Was a process letter sent before this bid? |
| `accompanied_by_merger_agreement` | boolean | Did bidder submit merger agreement draft? |
| `post_final_round_announcement` | boolean | Was a final round announced before this? |
| `filing_language` | string | How the filing describes it ("indication of interest", "preliminary proposal", "final bid", etc.) |

### Event types (all 23)

`target_sale`, `target_sale_public`, `bidder_sale`, `bidder_interest`,
`activist_sale`, `sale_press_release`, `bid_press_release`,
`ib_retention`, `nda`, `proposal`, `drop`, `drop_below_m`,
`drop_below_inf`, `drop_at_inf`, `drop_target`, `final_round_inf_ann`,
`final_round_inf`, `final_round_ann`, `final_round`,
`final_round_ext_ann`, `final_round_ext`, `executed`, `terminated`,
`restarted`.

### Example

```json
{"event_id": "pet_e15", "event_type": "proposal", "date": "2014-11-12", "date_precision": "exact", "value": 83.0, "value_lower": 82.0, "value_upper": 84.0, "value_unit": "per_share", "consideration_type": "cash", "evidence_attributes": {"preceded_by_process_letter": true, "accompanied_by_merger_agreement": false, "post_final_round_announcement": false, "filing_language": "preliminary indication of interest"}, "source_accession_number": "0001571049-15-000695", "source_line_start": 1450, "source_line_end": 1455, "source_text": "On November 12, 2014, Party A submitted an indication of interest to acquire the Company at a price of $82.00 to $84.00 per share in cash.", "raw_note": null}
```

```json
{"event_id": "pet_e01", "event_type": "target_sale", "date": "2014-08-13", "date_precision": "exact", "value": null, "value_lower": null, "value_upper": null, "value_unit": null, "consideration_type": null, "evidence_attributes": null, "source_accession_number": "0001571049-15-000695", "source_line_start": 1260, "source_line_end": 1263, "source_text": "On August 13, 2014, the board of directors of the Company met and determined to explore strategic alternatives, including a possible sale of the Company.", "raw_note": null}
```

## event_actor_links.jsonl

One JSON line per event-actor relationship. Links events to actors with
a participation role.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | string | yes | References events.jsonl |
| `actor_id` | string | yes | References actors.jsonl |
| `participation_role` | string | yes | `bidder` / `advisor` / `counterparty` / `decision_maker` / `initiator` |

### Participation roles

| Role | When used |
|------|-----------|
| `bidder` | The party making a bid or signing an NDA as potential acquirer |
| `advisor` | Financial advisor involved in the event |
| `counterparty` | The other side (e.g., target for a bidder event) |
| `decision_maker` | Board member or committee making a decision |
| `initiator` | Party that initiated a process (activist, unsolicited bidder) |

### Example

```json
{"event_id": "pet_e15", "actor_id": "petsmart-inc/party_a", "participation_role": "bidder"}
```

```json
{"event_id": "pet_e02", "actor_id": "petsmart-inc/jp-morgan", "participation_role": "advisor"}
```

## deal.json

Deal-level metadata with per-field provenance. Values are flat;
provenance is a separate object mapping field names to source references.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `deal_slug` | string | yes | e.g., `"petsmart-inc"` |
| `target_name` | string | yes | Company name |
| `cik` | string | yes | SEC CIK |
| `primary_accession_number` | string | yes | Primary filing accession |
| `filing_type` | string | yes | DEFM14A, SC_14D_9, etc. |
| `filing_url` | string | yes | SEC EDGAR URL |
| `filing_date` | string | yes | YYYY-MM-DD |
| `winning_acquirer` | string | yes | Actor ID of winner |
| `deal_outcome` | string | yes | `completed` / `terminated` / `withdrawn` |
| `date_announced` | string | yes | YYYY-MM-DD |
| `date_effective` | string | no | YYYY-MM-DD (null for terminated deals) |
| `consideration_type` | string | yes | `all_cash` / `stock` / `mixed` |
| `deal_notes` | string | no | Free text |
| `provenance` | object | yes | Per-field source references |

### Provenance Model

Two modes for sourcing field values:

**Mode 1: direct_quote** -- Value comes directly from filing text.

```json
{
  "provenance": {
    "date_effective": {
      "mode": "direct_quote",
      "source_refs": [
        {
          "source_accession_number": "0001571049-15-000695",
          "source_line_start": 1885,
          "source_line_end": 1886,
          "source_text": "On March 11, 2015, the merger was completed."
        }
      ]
    }
  }
}
```

**Mode 2: derived_from_rows** -- Value is derived from extracted events.

```json
{
  "provenance": {
    "winning_acquirer": {
      "mode": "derived_from_rows",
      "basis": "winner is the bidder linked to the executed event",
      "supporting_event_ids": ["executed_001"]
    }
  }
}
```

Fields sourced from EDGAR metadata (`primary_accession_number`,
`filing_type`, `filing_date`, `cik`) have no provenance entry -- their
source is the EDGAR filing index itself.

### Example

```json
{
  "deal_slug": "petsmart-inc",
  "target_name": "PetSmart, Inc.",
  "cik": "0000863894",
  "primary_accession_number": "0001571049-15-000695",
  "filing_type": "DEFM14A",
  "filing_url": "https://www.sec.gov/Archives/edgar/data/863894/000157104915000695/0001571049-15-000695-index.htm",
  "filing_date": "2015-01-20",
  "winning_acquirer": "petsmart-inc/bc-partners",
  "deal_outcome": "completed",
  "date_announced": "2014-12-14",
  "date_effective": "2015-03-11",
  "consideration_type": "all_cash",
  "deal_notes": null,
  "provenance": {
    "date_announced": {
      "mode": "direct_quote",
      "source_refs": [
        {
          "source_accession_number": "0001571049-15-000695",
          "source_line_start": 1870,
          "source_line_end": 1872,
          "source_text": "On December 14, 2014, the Company announced that it had entered into an Agreement and Plan of Merger."
        }
      ]
    },
    "date_effective": {
      "mode": "direct_quote",
      "source_refs": [
        {
          "source_accession_number": "0001571049-15-000695",
          "source_line_start": 1885,
          "source_line_end": 1886,
          "source_text": "On March 11, 2015, the merger was completed."
        }
      ]
    },
    "winning_acquirer": {
      "mode": "derived_from_rows",
      "basis": "winner is the bidder linked to the executed event",
      "supporting_event_ids": ["pet_e53"]
    },
    "deal_outcome": {
      "mode": "derived_from_rows",
      "basis": "executed event exists, no termination event after it",
      "supporting_event_ids": ["pet_e53"]
    },
    "consideration_type": {
      "mode": "direct_quote",
      "source_refs": [
        {
          "source_accession_number": "0001571049-15-000695",
          "source_line_start": 1871,
          "source_line_end": 1873,
          "source_text": "pursuant to which BC Partners would acquire the Company for $83.00 per share in cash"
        }
      ]
    }
  }
}
```

## actors_extended.jsonl

Same schema as `actors.jsonl` (actor_id, actor_alias, actor_type,
bidder_subtype, lifecycle_status, first_evidence_*). Contains ONLY actors minted during
event extraction that were not in the original Skill 4 roster.

Written to a SEPARATE file to preserve independent re-run safety.
Re-running Skill 4 does not destroy Skill 5's additions, and vice
versa. Downstream skills that need the full actor list read both
`actors.jsonl` and `actors_extended.jsonl`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `actor_id` | string | yes | `<deal_slug>/<label>` |
| `actor_alias` | string | yes | Human-readable name |
| `actor_type` | string | yes | `bidder` / `advisor` / `activist` / `target_board` |
| `bidder_subtype` | string | no | `strategic` / `financial` / `non_us` / `mixed` |
| `is_grouped` | boolean | no | True if consortium |
| `group_size` | int | no | Number of parties in group |
| `lifecycle_status` | string | yes | Terminal status after lifecycle closure |
| `actor_notes` | string | no | Free text |
| `first_evidence_accession_number` | string | yes | Filing where actor first appears |
| `first_evidence_line_start` | int | yes | Line in .txt |
| `first_evidence_line_end` | int | yes | Line in .txt |
| `first_evidence_text` | string | yes | Verbatim quote establishing identity |

## decisions.jsonl

Append-only log shared across skills 4-8. Each line is one decision.
This file may already contain entries from Skill 4
(build-party-register). Skill 5 APPENDS to it, never overwrites.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `skill` | string | yes | `"extract-events"` for this skill |
| `decision_type` | string | yes | One of the types below |
| `detail` | string | yes | Human-readable explanation |
| `artifact_affected` | string | yes | Which file (e.g., `"events.jsonl"`) |
| `target_id` | string | yes | ID of the affected object |
| `confidence` | string | yes | `high` / `medium` / `low` |

### Decision types relevant to extract-events

| Type | When used |
|------|-----------|
| `approximate_date` | Filing gives vague date, recorded as specific date |
| `implicit_dropout` | No explicit dropout statement, inferred from context |
| `event_type_choice` | Ambiguous event categorization |
| `scope_exclusion` | Why a partial-asset bid was excluded |
| `alias_merge` | Two labels refer to the same entity (also used by Skill 4) |
| `actor_type_classification` | Ambiguous actor type for newly minted actor |
| `count_interpretation` | Ambiguous aggregate count |
| `cycle_boundary` | Where one process cycle ends and another begins |
| `filing_selection` | Why a supplementary filing was used for a particular event |

### Examples

```json
{"skill": "extract-events", "decision_type": "approximate_date", "detail": "Filing says 'around mid-October'; recorded as 2014-10-15 with date_precision=approximate", "artifact_affected": "events.jsonl", "target_id": "pet_e07", "confidence": "medium"}
```

```json
{"skill": "extract-events", "decision_type": "implicit_dropout", "detail": "No explicit dropout statement for Party C, but bound by standstill and absent from formal rounds. Inferred drop on execution date.", "artifact_affected": "events.jsonl", "target_id": "pet_e48", "confidence": "low"}
```

```json
{"skill": "extract-events", "decision_type": "scope_exclusion", "detail": "Party D bid for retail segment only, not whole company. Excluded per whole-company-only rule.", "artifact_affected": "events.jsonl", "target_id": "n/a", "confidence": "high"}
```

```json
{"skill": "extract-events", "decision_type": "event_type_choice", "detail": "Board meeting discussed both strategic alternatives and activist pressure. Recorded as target_sale because board initiated; activist_sale also viable.", "artifact_affected": "events.jsonl", "target_id": "pet_e01", "confidence": "medium"}
```
