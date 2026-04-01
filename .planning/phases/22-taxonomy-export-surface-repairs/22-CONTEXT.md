# Phase 22: Taxonomy + Export Surface Repairs - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning
**Mode:** Auto-generated from the GPT Pro round_1 diagnosis

<domain>
## Phase Boundary

Expand the analyst-facing v2 surface without relaxing filing-grounded rules:

1. export agreement-family observations with distinct analyst event types
2. support advisor-termination process rows and keep bidder-originated sale
   surfaces explicit
3. stop leaking proxy sort dates as exact `date_recorded` values on analyst and
   benchmark CSVs
4. carry enterprise-value-only proposals through derive and export
5. pin the new row/event/export behavior with focused derive and export tests

This phase should not change prompt instructions, extraction skill docs, or the
v2 gate suite beyond what the surfaced row contract requires.

</domain>

<decisions>
## Implementation Decisions

### Analyst Taxonomy
- **D-01:** Additive analyst event types may expand for agreement/process
  families as long as existing event types remain stable.
- **D-02:** `amendment` should surface as `nda_amendment`; `standstill`,
  `exclusivity`, and `clean_team` should each get their own analyst type.
- **D-03:** `advisor_termination` gets an `ib_terminated` analyst row.

### Export Precision
- **D-04:** `date_recorded` should be reserved for exact-day dates only.
- **D-05:** When a row carries a proxy date, keep it in a separate
  `date_sort_proxy` field and surface the original precision explicitly.

### Value Surface
- **D-06:** Enterprise-value proposals should remain additive to the current
  proposal row contract; do not overload `value` or range columns with
  enterprise-value amounts.

### the agent's Discretion
- Exact column order for new export fields, provided analyst and benchmark CSVs
  stay aligned and tests pin the contract.
- Whether exact-day rows also carry `date_precision`, as long as proxy dates no
  longer masquerade as exact `date_recorded`.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 22 goal and success criteria
- `.planning/REQUIREMENTS.md` — SURFACE-01 through SURFACE-04
- `diagnosis/gptpro/2026-04-01/round_1/v2_analytical_gap_inventory_3aa65f7.md`
- `skill_pipeline/models_v2.py`
- `skill_pipeline/derive.py`
- `skill_pipeline/db_export_v2.py`
- `tests/test_skill_derive.py`
- `tests/test_skill_db_export_v2.py`

</canonical_refs>

<specifics>
## Specific Ideas

- Keep event-family changes additive so existing consumers can ignore unknown
  event types rather than breaking.
- For proxy dates, keep the midpoint only in `date_sort_proxy`; exact dates can
  stay in `date_recorded` and `date_public`.
- Enterprise-value-only proposals should export with `enterprise_value` and
  leave `value`, `range_low`, and `range_high` empty.

</specifics>

<deferred>
## Deferred Ideas

- prompt/skill doc updates
- gate warnings for lossy agreement-family collapse or proxy-date leakage
- solicitation recipient contract tightening

</deferred>
