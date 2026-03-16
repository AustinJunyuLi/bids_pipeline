# Reconciliation Types

Quote verification procedure and count reconciliation types for the
audit-and-reconcile skill.

## Quote Verification Procedure

For each event's `source_text`, verify it exists in the frozen .txt:

1. **Primary read:** Read the .txt at `source_line_start` to
   `source_line_end`, plus 10 lines of surrounding context on each
   side. Check that `source_text` appears in the chunk.

2. **Retry 1 (broader context):** If not found, re-read with +/- 50
   lines of context. The quote may have shifted due to line-counting
   differences between extraction and audit.

3. **Retry 2 (full-file search):** If still not found, use text search to
   search the entire .txt for a distinctive phrase (at least 8 words)
   from the source_text.

4. **After 2 failed retries:** Flag the quote as `unverified` in
   `audit_flags.json`. Do not attempt further retries. Do not modify
   the event or the .txt file.

**Max 2 retries per quote.** Most quotes should pass on the primary
read. Widespread failures suggest a systematic issue with line
numbering from extraction.

## Count Reconciliation Types

When the extracted count does not match the filing's asserted count,
the reconciliation MUST use one of these 7 typed categories. Free-text
explanations are NOT allowed.

### 1. `advisor_exclusion`

**Definition:** The filing's count includes a party that is classified
as an advisor (not a bidder) in the extraction.

**Example:** Filing says "16 parties signed NDAs" but one signer is
J.P. Morgan (target's financial advisor). Extracted bidder NDA count
is 15. The gap of 1 is explained by advisor_exclusion.

### 2. `stale_process`

**Definition:** The filing's count includes parties from a prior
terminated process cycle that are not in the current cycle's extraction.

**Example:** Filing says "25 parties were contacted" counting across
two cycles. The current cycle extraction has 18 parties because 7
were from the earlier terminated process.

### 3. `unnamed_aggregate`

**Definition:** The filing's aggregate count includes unnamed parties
that cannot be individually identified in the chronology.

**Example:** Filing says "15 financial buyers were contacted" but only
12 are individually described in the narrative. The 3 unnamed parties
are counted in the assertion but not individually extracted.

### 4. `filing_approximation`

**Definition:** The filing uses approximate language, making exact
reconciliation impossible.

**Example:** Filing says "about 15 parties" or "approximately 20
potential bidders." The count is inherently imprecise.

### 5. `consortium_counted_once`

**Definition:** A consortium of multiple entities is counted as one
bidder in the filing but has multiple member actors in the extraction
(or vice versa).

**Example:** Filing counts "Party A consortium" as 1 bidder, but
extraction has 3 actors (Party A, Party A1, Party A2) with
`is_grouped: true`.

### 6. `partial_bidder_excluded`

**Definition:** The filing's count includes parties who bid for a
partial asset (division, segment, percentage stake) that were excluded
from extraction because the extraction only covers whole-company bids.

**Example:** Filing says "8 bids received" but 2 were for a single
division. Extraction has 6 whole-company proposal events.

### 7. `unresolved`

**Definition:** The gap between expected and extracted counts cannot
be explained by any of the above categories.

**When to use:** Only after attempting all other reconciliation types.
An `unresolved` reconciliation generates a `needs_review` flag.

---

## census.json Full Schema

```json
{
  "party_roster": [
    {
      "actor_id": "petsmart-inc/party_a",
      "actor_alias": "Party A",
      "actor_type": "bidder",
      "bidder_subtype": "financial",
      "lifecycle_status": "winner",
      "source": "actors.jsonl",
      "first_evidence_accession_number": "0001571049-15-000695",
      "first_evidence_line_start": 1265,
      "first_evidence_line_end": 1267,
      "first_evidence_text": "Party A, a financial sponsor..."
    }
  ],
  "count_assertions": [
    {
      "assertion_id": "pet_nda_count_1",
      "assertion_text": "15 potentially interested financial buyers",
      "metric": "nda_signed",
      "expected_count": 15,
      "time_scope": "first_week_october_2014",
      "cycle_scope": "cycle_1",
      "source_accession_number": "0001571049-15-000695",
      "source_line_start": 1270,
      "source_line_end": 1272,
      "source_text": "During the first week of October 2014, 15 potentially interested financial buyers were contacted."
    }
  ],
  "self_check": {
    "reconciliations": [
      {
        "assertion_id": "pet_nda_count_1",
        "expected": 15,
        "extracted": 15,
        "explained": 0,
        "residual": 0,
        "status": "pass",
        "explanations": []
      },
      {
        "assertion_id": "pet_indication_count_1",
        "expected": 8,
        "extracted": 6,
        "explained": 2,
        "residual": 0,
        "status": "pass",
        "explanations": [
          {
            "type": "partial_bidder_excluded",
            "count": 1,
            "detail": "One indication was for retail segment only"
          },
          {
            "type": "unnamed_aggregate",
            "count": 1,
            "detail": "Filing counts one unnamed party not individually described"
          }
        ]
      }
    ],
    "structural_audit": {
      "nda_coverage": "pass",
      "round_pairs": "pass",
      "process_initiation": "pass",
      "lifecycle_consistency": "pass",
      "proposal_completeness": "needs_review",
      "failures": [
        {
          "check": "proposal_completeness",
          "detail": "Party F invited to round 2 but has no proposal and no dropout event",
          "actor_id": "petsmart-inc/party_f"
        }
      ]
    },
    "lifecycle_audit": {
      "total_actors": 20,
      "closed_actors": 18,
      "unresolved_actors": ["petsmart-inc/unnamed_12", "petsmart-inc/unnamed_14"]
    }
  }
}
```

### Field Definitions

**party_roster[].source:** Either `"actors.jsonl"` or
`"actors_extended.jsonl"` -- indicates which skill produced this actor.

**reconciliations[].status:** `"pass"` if `residual == 0`, otherwise
`"fail"`. A fail triggers a `count_mismatch` flag.

**reconciliations[].explanations[].type:** MUST be one of the 7 typed
categories above.

**structural_audit fields:** Each named check is `"pass"` or
`"needs_review"`. The `failures` array lists specific issues.

---

## audit_flags.json Schema

```json
{
  "deal_slug": "petsmart-inc",
  "flags": [
    "unresolved_actors",
    "proposal_completeness"
  ],
  "unresolved_actors": [
    "petsmart-inc/unnamed_12",
    "petsmart-inc/unnamed_14"
  ],
  "unresolved_counts": [],
  "unverified_quotes": [],
  "structural_failures": [
    {
      "check": "proposal_completeness",
      "detail": "Party F invited to round 2 but has no proposal and no dropout event",
      "actor_id": "petsmart-inc/party_f"
    }
  ]
}
```

### Field Definitions

- **flags:** Array of flag strings summarizing all issues found.
  Possible values: `unresolved_actors`, `unverified_quotes`,
  `count_mismatch`, `missing_nda`, `missing_round_pair`,
  `missing_initiation`, `lifecycle_inconsistency`,
  `proposal_completeness`.
- **unresolved_actors:** Actor IDs without terminal lifecycle status.
- **unresolved_counts:** Assertion IDs where reconciliation failed
  (residual != 0 after all explanations).
- **unverified_quotes:** Event IDs whose source_text could not be
  found in the .txt after 2 retries.
- **structural_failures:** Detailed records from the 5-point audit.
