# Structural Integrity Audit

The 5-point structural audit checklist. Every check must pass or
produce a `needs_review` flag. These checks catch systematic extraction
gaps that quote verification and count reconciliation cannot detect.

## Check 1: NDA Coverage

**Rule:** Every actor with `actor_type=bidder` MUST have either:
- (a) An `nda` event in `event_actor_links.jsonl` where the actor
  appears, OR
- (b) A `needs_review` flag with reason `missing_nda`.

**Rationale:** A bidder who submitted proposals must have signed an
NDA at some point. The filing almost always mentions this. A bidder
without an NDA who submitted proposals is a hard error -- the filing
must mention their NDA somewhere, and extraction missed it.

**Pass criteria:** Every bidder has NDA coverage (event or flag).
**Fail action:** List each bidder without NDA coverage. Record as
`missing_nda` in `structural_audit.failures`. Set the overall
`nda_coverage` check to `needs_review`.

## Check 2: Round Pair Check

**Rule:** Every `*_ann` round event must have a matching deadline
event. The pairs are:

| Announcement Event | Deadline Event |
|-------------------|---------------|
| `final_round_inf_ann` | `final_round_inf` |
| `final_round_ann` | `final_round` |
| `final_round_ext_ann` | `final_round_ext` |

**Rationale:** Round announcements without deadlines indicate
incomplete extraction. The filing always provides a deadline date
when it describes a process letter or round announcement.

**Pass criteria:** Every extracted `*_ann` event has a corresponding
deadline event of the matching type.
**Fail action:** This is a hard error. The missing deadline likely
exists in the filing but was not extracted. Record in
`structural_audit.failures` with the orphaned announcement event_id.
Set `round_pairs` to `needs_review`.

## Check 3: Process Initiation Check

**Rule:** At least one process initiation event must exist. Valid
initiation types: `target_sale`, `bidder_sale`, `activist_sale`, or
`bidder_interest`.

**Rationale:** Every deal has some initiating event. Its absence means
the extraction missed the opening of the chronology narrative.

**Pass criteria:** >= 1 process initiation event in events.jsonl.
**Fail action:** Set `process_initiation` to `needs_review`. Record
in `structural_audit.failures`.

Note: `target_sale_public`, `sale_press_release`, and
`bid_press_release` are public disclosure events, not initiation
events. They do not satisfy this check on their own, though they
may co-occur with a valid initiation event.

## Check 4: Lifecycle-Event Consistency

**Rule:** Every non-advisor actor with `lifecycle_status` in
{`dropped`, `dropped_by_target`, `winner`} must have a corresponding
event in events.jsonl:

| Lifecycle Status | Required Event Type |
|-----------------|-------------------|
| `dropped` | `drop`, `drop_below_m`, `drop_below_inf`, `drop_at_inf` |
| `dropped_by_target` | `drop_target` |
| `winner` | `executed` |

**Rationale:** A terminal lifecycle status without a supporting event
means either the status is wrong or the event was missed.

**Pass criteria:** Every non-advisor actor's lifecycle status is
backed by a corresponding event.
**Fail action:** List each inconsistency. The auditor should check
whether the event exists in the filing (go back to .txt) or whether
the lifecycle status was incorrectly assigned. Record in
`structural_audit.failures`. Set `lifecycle_consistency` to
`needs_review`.

## Check 5: Proposal Completeness

**Rule:** For each round (as identified in events.jsonl round
announcement events), every actor who was invited to that round
must have one of:
- (a) A proposal event linked to them for that round period
  (between the round announcement and deadline dates), OR
- (b) A dropout event (`drop*`) before or during the round, OR
- (c) A `needs_review` flag.

No actor should silently disappear between rounds.

**How to determine invited set:** The round announcement event's
`source_text` usually names or counts the invited parties. Cross-
reference with `event_actor_links.jsonl` for actors linked to the
round announcement event.

**Pass criteria:** Every invited actor is accounted for.
**Fail action:** List each actor who silently disappeared. Record
in `structural_audit.failures` with the round_id and actor_id. Set
`proposal_completeness` to `needs_review`.

---

## Recording Results

Write the structural audit results into `census.json` under
`self_check.structural_audit`:

```json
{
  "structural_audit": {
    "nda_coverage": "pass",
    "round_pairs": "pass",
    "process_initiation": "pass",
    "lifecycle_consistency": "needs_review",
    "proposal_completeness": "pass",
    "failures": [
      {
        "check": "lifecycle_consistency",
        "detail": "Party D has lifecycle_status=dropped but no drop event found",
        "actor_id": "deal-slug/party_d"
      }
    ]
  }
}
```

Each check value is either `"pass"` or `"needs_review"`.
The `failures` array contains one entry per specific issue found.
Each failure entry includes `check` (which of the 5), `detail`
(human-readable), and optionally `actor_id`, `event_id`, or
`round_id` for traceability.
