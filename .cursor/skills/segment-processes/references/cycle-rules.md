# Cycle Segmentation and Round Structure Rules

Rules for identifying deal process cycles, assigning events to cycles,
and building round structure.

## Cycle Segmentation

### Boundary Events

`terminated` and `restarted` events in events.jsonl mark cycle
boundaries. Each cycle is a contiguous process from initiation
through either completion, termination, or ongoing status.

### Single-Cycle Deals

Most deals have one cycle. If no `terminated` or `restarted` events
exist:
- Create one cycle with `cycle_sequence: 1`.
- `start_event_id`: the earliest event in the deal.
- `end_event_id`: the last event in the deal (typically `executed`).
- `status`: `completed` (if executed event exists), `terminated`
  (if deal ended without execution), or `withdrawn`.
- `segmentation_basis`: brief explanation (e.g., "Single observed
  cycle from board authorization through merger execution.").

### Multi-Cycle Deals

When `terminated` and/or `restarted` events exist:

1. **Earlier terminated processes** get their own cycle with
   `status: "terminated"`. The cycle runs from the process initiation
   to the `terminated` event.

2. **Events from terminated cycles** are assigned to that cycle, not
   the subsequent active cycle. Date alone is not sufficient -- use
   the `terminated` event as the boundary.

3. **The `restarted` event** marks the beginning of the next cycle.
   Events after `restarted` belong to the new cycle.

4. **The final cycle** runs from the last `restarted` event (or from
   deal start if no restart) through the end of the deal.

5. **Liminal events** (occurring between a `terminated` and
   `restarted` event, or ambiguously near a boundary) require a
   judgment call. Assign to the most appropriate cycle and log a
   `cycle_boundary` decision to `decisions.jsonl` with confidence
   and reasoning.

### Cycle Sequencing

Number cycles sequentially: `<slug>_c1`, `<slug>_c2`, etc.
`cycle_sequence` is 1-indexed.

## Round Structure

### Announcement + Deadline Pairs

Rounds are defined by paired announcement and deadline events:

| Announcement | Deadline |
|-------------|----------|
| `final_round_inf_ann` | `final_round_inf` |
| `final_round_ann` | `final_round` |
| `final_round_ext_ann` | `final_round_ext` |

Each announcement event MUST have a matching deadline event. This is
enforced by the structural audit (Skill 6), but segment-processes
should also expect and respect paired structure.

### Round Fields

Each round object within a cycle has:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| round_id | string | yes | Unique within deal (e.g., `pet_r1`) |
| announcement_event_id | string | yes | Event ID of the `*_ann` event |
| deadline_event_id | string | yes | Event ID of the matching deadline event |
| invited_set | array | yes | Array of actor_ids invited to this round |
| source_text | string | yes | Verbatim text describing the round invitation |

### Invited Set

Determine the invited set from:
1. The round announcement event's `source_text` (usually names or
   counts the invited parties).
2. Actors linked to the announcement event in
   `event_actor_links.jsonl`.
3. Cross-reference with the actor roster to resolve aliases.

### Round Ordering

Rounds within a cycle are ordered by announcement date. A cycle may
have 0, 1, 2, or 3 rounds depending on the deal structure.

### NO round_type Field

Rounds have NO `round_type` field. The formal/informal classification
lives on individual proposals in `judgments.jsonl` (Skill 8), not on
rounds themselves. A single round may contain both informal and formal
proposals from different bidders (rare but possible). Do not add any
formality classification to the round object.

---

## process_cycles.jsonl Full Schema

One JSON line per cycle. Rounds nested within their parent cycle.

```json
{
  "cycle_id": "pet_c1",
  "cycle_sequence": 1,
  "start_event_id": "pet_e01",
  "end_event_id": "pet_e53",
  "status": "completed",
  "segmentation_basis": "Single observed cycle from board authorization through merger execution.",
  "rounds": [
    {
      "round_id": "pet_r1",
      "announcement_event_id": "pet_e12",
      "deadline_event_id": "pet_e14",
      "invited_set": ["petsmart-inc/party_a", "petsmart-inc/party_b", "petsmart-inc/party_c", "petsmart-inc/party_d"],
      "source_text": "the Company requested that the four remaining bidders submit revised proposals by October 24"
    },
    {
      "round_id": "pet_r2",
      "announcement_event_id": "pet_e30",
      "deadline_event_id": "pet_e33",
      "invited_set": ["petsmart-inc/party_a", "petsmart-inc/party_b"],
      "source_text": "the board directed the two finalists to submit best and final offers"
    }
  ]
}
```

### Multi-Cycle Example

```json
{
  "cycle_id": "acme_c1",
  "cycle_sequence": 1,
  "start_event_id": "acme_e01",
  "end_event_id": "acme_e18",
  "status": "terminated",
  "segmentation_basis": "First process terminated on June 15 after board decided market conditions were unfavorable.",
  "rounds": [
    {
      "round_id": "acme_r1",
      "announcement_event_id": "acme_e08",
      "deadline_event_id": "acme_e10",
      "invited_set": ["acme-corp/party_a", "acme-corp/party_b"],
      "source_text": "the Company sent process letters to the two interested parties"
    }
  ]
}
```

```json
{
  "cycle_id": "acme_c2",
  "cycle_sequence": 2,
  "start_event_id": "acme_e19",
  "end_event_id": "acme_e45",
  "status": "completed",
  "segmentation_basis": "Process restarted after unsolicited approach from Party C in September.",
  "rounds": []
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| cycle_id | string | yes | `<slug>_c<N>` |
| cycle_sequence | int | yes | 1-indexed order |
| start_event_id | string | yes | First event in cycle |
| end_event_id | string | yes | Last event in cycle |
| status | string | yes | `completed` / `terminated` / `withdrawn` |
| segmentation_basis | string | yes | Brief explanation of cycle boundary |
| rounds | array | yes | Array of round objects (may be empty) |
