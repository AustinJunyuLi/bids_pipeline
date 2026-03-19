---
name: verify-extraction
description: Use when checking and repairing skill-workflow extraction artifacts against filing text before enrichment.
---

# verify-extraction

## Design Principles

1. The filing is the single source of truth.
2. Verification is substring matching, not semantic judgment.
3. Fix what you find. Do not flag and move on.
4. Two rounds maximum. If round 2 still has errors, stop.

## Purpose

Fact-check the extraction output against the filing text. Fix errors in place.
Log every finding, every fix, and the final disposition.

## When To Use

- Called by deal-agent after extract-deal, or independently via
  `/verify-extraction <slug>`.
- Prerequisite: `extract-deal` has already produced `actors_raw.json` and
  `events_raw.json`.

**Deterministic pre-step:** Run `skill-pipeline verify --deal <slug>` first.
This writes `verification_findings.json` (with repairability tags) and
`verification_log.json`. Verification is strict: EXACT and NORMALIZED resolve;
FUZZY does not. The LLM repair loop should run only when **all** error-level
findings are `repairable`; any `non_repairable` error fails closed.

## Reads

| File | What it provides |
|---|---|
| `data/skill/<slug>/extract/actors_raw.json` | Extracted actor roster |
| `data/skill/<slug>/extract/events_raw.json` | Extracted events with evidence refs |
| `data/deals/<slug>/source/chronology_blocks.jsonl` | Narrative blocks (the text the quotes should match) |
| `data/deals/<slug>/source/evidence_items.jsonl` | Pre-tagged evidence anchors |
| `raw/<slug>/filings/*.txt` | Frozen filing text for resolving block-boundary edge cases |

## Checks

### 1. Quote Verification

For every `evidence_ref.anchor_text` in both `actors_raw.json` and
`events_raw.json`:

**Search procedure:**

1. Look up the referenced block text from `chronology_blocks.jsonl` (by
   `block_id`) or `evidence_items.jsonl` (by `evidence_id`).
2. Search for `anchor_text` as a substring of that block's raw text.
3. If not found: expand search to +/- 3 lines beyond the block boundaries in
   the source filing (`raw/<slug>/filings/*.txt`).
4. If still not found: classify as UNRESOLVED.

**Match classification:**

| Level | Rule |
|---|---|
| EXACT | Literal substring match on the raw text |
| NORMALIZED | Matched after: lowercasing, collapsing whitespace, translating smart quotes/dashes to ASCII equivalents |
| UNRESOLVED | No match at EXACT or NORMALIZED level within the search window |

**There is no FUZZY tier.** The pipeline's FUZZY match (stripping quotes,
parentheticals, non-alphanumeric characters) is too permissive for verification.
It can match semantically different phrases that happen to share alphanumeric
content. If a quote does not match at EXACT or NORMALIZED level, it is
UNRESOLVED and enters the fix loop.

**Why +/- 3 lines, not wider.** A wider search (+/- 50 lines, full-file) creates
false confidence by finding the same phrase in a different context. If the quote
is not within 3 lines of the referenced block, the correct fix is to update the
`block_id` or `anchor_text` -- not to widen the search. The Round 1 fix loop
absorbs the difference: the agent re-reads the filing and provides the correct
attribution.

### 2. Actor-Event Referential Integrity

Three sub-checks:

| Check | Rule |
|---|---|
| Event actor_ids | Every `actor_id` in every event's `actor_ids` list exists in `actors_raw.json` |
| Invited actor_ids | Every `actor_id` in any event's `invited_actor_ids` exists in `actors_raw.json` |
| Advisory links | Every `advised_actor_id` on advisor actors exists in `actors_raw.json` |

### 3. Structural Integrity

`skill-pipeline verify` currently enforces this deterministic subset:

| # | Check | Severity |
|---|---|---|
| 1 | At least one process initiation event exists (`target_sale`, `target_sale_public`, `bidder_sale`, `activist_sale`, or `bidder_interest`) | error |
| 2 | At least one outcome event exists (`executed`, `terminated`, or `restarted`) | error |
| 3 | Every executed event has a non-null counterparty (`executed_with_actor_id` or `actor_ids` non-empty) | error |
| 4 | Every proposal has non-empty `actor_ids` | error |

Additional structural review that still happens inside this skill after the
deterministic pass:

| Check | Severity |
|---|---|
| Every round announcement has a corresponding deadline of the same type | warning |
| Every drop event references an actor with a prior NDA or proposal | error |
| Dates are non-decreasing globally across all events (when dates are exact). This is a global monotonicity check; cycle boundaries are not yet computed. | warning |

## Procedure

### Round 1

1. **Start from the deterministic pass.** Run `skill-pipeline verify --deal <slug>`
   and treat `verification_findings.json` as authoritative for quote
   verification, actor-event referential integrity, and the deterministic
   structural subset above.

2. **Review the remaining structural items.** Check the round/deadline pairing,
   drop-history consistency, and exact-date monotonicity items that are not yet
   implemented in `skill-pipeline verify`. Append those findings to the same
   Round 1 log using `check_type`, `severity` (error or warning), `description`,
   affected `actor_ids` or `event_ids`, `anchor_text` if relevant, and
   `repairability`.

3. **Repairability gate.** Before invoking the LLM repair loop: if any
   error-level finding is `non_repairable`, fail closed. Do not attempt repair.
   Only when all error-level findings are `repairable` may the LLM fix loop run.

4. **Fix errors in place.** For each error-severity finding (when repair is allowed):

   | Finding type | Fix action |
   |---|---|
   | Unresolved quote | Re-read the filing around the referenced section. Find the correct verbatim text. Update `anchor_text` (and `block_id` if misattributed) in the JSON. |
   | Missing actor reference | Add the missing actor to `actors_raw.json` with evidence from the filing. |
   | Broken structural check | Re-read the filing. Add the missing event or fix the attribution. |

5. **Write updated files.** Rewrite `actors_raw.json` and `events_raw.json`
   with fixes applied.

### Round 2

1. **Re-check all.** Run every check again on the updated files. Log findings.

2. **Evaluate disposition:**
   - If any error-severity findings remain: **STOP.** Report the cumulative log
     to the user. Do not proceed to enrich-deal.
   - If only warnings remain: **PASS.** Warnings surface in `review_flags` at
     export time.

## Writes

| File | Content |
|---|---|
| `data/skill/<slug>/extract/actors_raw.json` | Updated in place if fixes were applied |
| `data/skill/<slug>/extract/events_raw.json` | Updated in place if fixes were applied |
| `data/skill/<slug>/verify/verification_findings.json` | Deterministic findings with repairability tags (from `skill-pipeline verify`) |
| `data/skill/<slug>/verify/verification_log.json` | Full log of both rounds; gate artifact |

## Log Format

```json
{
  "round_1": {
    "findings": [
      {
        "check_type": "quote_verification",
        "severity": "error",
        "repairability": "repairable",
        "description": "anchor_text not found within +/-3 lines of block B042",
        "event_id": "evt_007",
        "anchor_text": "representatives of Thoma Bravo informally approached"
      }
    ],
    "fixes_applied": [
      {
        "finding_index": 0,
        "action": "Updated anchor_text to exact substring from B042 lines 1162-1164",
        "old_value": "representatives of Thoma Bravo informally approached",
        "new_value": "representatives of Thoma Bravo informally approached representatives of Imprivata"
      }
    ]
  },
  "round_2": {
    "findings": [],
    "status": "pass"
  },
  "summary": {
    "total_checks": 147,
    "round_1_errors": 3,
    "round_1_warnings": 5,
    "fixes_applied": 3,
    "round_2_errors": 0,
    "round_2_warnings": 5,
    "status": "pass"
  }
}
```

`round_2.status` is `"pass"` when no error-severity findings remain, `"fail"`
when errors persist. The deal-agent orchestrator reads this field as its gate
condition.
