# Gate Conditions

The orchestrator checks each gate BY READING FILES ON DISK after the
subagent returns. Gate checks use file existence and line counts only —
never parse artifact content.

## Per-Skill Gates

| # | Skill | Gate Condition | Check Method |
|---|-------|---------------|--------------|
| 1 | select-anchor-filing | `source/source_selection.json` exists with >= 1 filing where `disposition == "selected"` | File exists + grep for `"selected"` |
| 2 | freeze-filing-text | Primary filing `.html` and `.txt` files exist in `source/filings/` | File exists (glob `*.html` and `*.txt`) |
| 3 | locate-chronology | `source/chronology_bookmark.json` exists with valid `start_line` / `end_line` | File exists |
| 4 | build-party-register | `extraction/actors.jsonl` has >= 1 line | File exists + line count >= 1 |
| 5 | extract-events | `extraction/events.jsonl` has >= 1 line | File exists + line count >= 1 |
| 6 | audit-and-reconcile | `extraction/census.json` exists | File exists |
| 7 | segment-processes | `enrichment/process_cycles.jsonl` exists | File exists |
| 8 | classify-bids-and-boundary | `enrichment/judgments.jsonl` exists | File exists |
| 9 | render-review-rows | `master_rows.csv` exists | File exists |

All paths are relative to `Data/deals/<slug>/`.

## Failure Policy

| Skills | Policy | Behavior on Gate Failure |
|--------|--------|-------------------------|
| 1-3 | **Fail closed** | No usable source material. Write `source/failure_bundle.json` with error details. STOP — do not run remaining skills. Report failure to user. |
| 4-8 | **Fail open** | Write what you can. Flag `needs_review` on incomplete artifacts. Log warning. Continue to next skill. |
| 9 | **Always succeeds** | Pure denormalization — if input artifacts exist, CSV assembly cannot fail. |

### Fail-Closed Triggers (Skills 1-3)

- **Skill 1:** No filing found with disposition `selected` across all 6 types.
- **Skill 2:** Primary filing curl returns non-200 or empty content.
  Supplementary failures are logged but do NOT block.
- **Skill 3:** No "Background of the Merger/Offer" section found in `.txt`.

### Fail-Open Examples (Skills 4-8)

- Incomplete actor roster (Skill 4): proceed — Skill 5 can mint new actors.
- Unresolved actor lifecycle (Skill 5): flag `needs_review`, proceed.
- Count reconciliation residual (Skill 6): flag `needs_review`, proceed.
- Uncertain cycle boundary (Skill 7): flag `needs_review`, proceed.
- Ambiguous formal/informal classification (Skill 8): flag `needs_review`, proceed.

### failure_bundle.json Schema

Written to `source/failure_bundle.json` on fail-closed:

```json
{
  "deal_slug": "<slug>",
  "failed_skill": "<skill-name>",
  "failure_reason": "<description>",
  "timestamp": "<ISO 8601>",
  "partial_artifacts": ["<list of any artifacts written before failure>"]
}
```
