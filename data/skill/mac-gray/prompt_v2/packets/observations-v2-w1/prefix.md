You are extracting filing-literal v2 observation artifacts from a single M&A chronology window.

Ground rules:
- The filing is the only source of truth.
- Quote before extract: every structured record must cite verbatim quote_ids.
- Extract only literal parties, cohorts, and observations.
- Do not emit analyst rows, benchmark rows, dropout labels, bid labels, or inferred outcomes beyond the schema fields explicitly supported below.

Return valid JSON only.

Schema reminders:

- `parties`: named actors only. Roles are `bidder`, `advisor`, `activist`, `target_board`, or `other`.
- `cohorts`: unnamed bidder groups only. Use exact counts when the filing states them.
- `observations` use exactly one of:
  - `process`
  - `agreement`
  - `solicitation`
  - `proposal`
  - `status`
  - `outcome`

Examples:

- A launch of a sale process -> `process` with `process_kind: "sale_launch"`.
- A confidentiality agreement -> `agreement` with `agreement_kind: "nda"`.
- A request for best and final bids due on a later date -> `solicitation` with `due_date`.
- A price-bearing indication of interest -> `proposal` with `terms`.
- "Party X was no longer interested" -> `status` with `status_kind: "not_interested"`.
- "The merger agreement was executed" -> `outcome` with `outcome_kind: "executed"`.