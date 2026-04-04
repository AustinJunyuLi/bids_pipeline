# Phase 25: Repair Module + Field Parsers - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 25-repair-module-field-parsers
**Areas discussed:** Module placement, Parser confidence, Bidder kind strategy, Test fixture scope

---

## Module Placement

### Q1: Where should the new repair logic live?

| Option | Description | Selected |
|--------|-------------|----------|
| Separate module (Recommended) | skill_pipeline/repair/structured_fields_v2.py — keeps canonicalize.py lean, independently testable | ✓ |
| Inline in canonicalize | Add as private functions in canonicalize.py — consistent with existing but file grows substantially | |
| You decide | Claude picks based on code size and testability | |

**User's choice:** Separate module
**Notes:** Follows GPT Pro review recommendation

### Q2: Single entry point or individual calls?

| Option | Description | Selected |
|--------|-------------|----------|
| Single entry point (Recommended) | canonicalize.py calls repair_structured_fields() once | ✓ |
| Individual calls | canonicalize.py calls each sub-repair separately | |

**User's choice:** Single entry point

### Q3: Migrate existing repairs?

| Option | Description | Selected |
|--------|-------------|----------|
| Leave existing in place | Don't touch working code — new module handles only structured field repairs | ✓ |
| Migrate all repairs | Move existing repairs into new module for single repair layer | |
| You decide | Claude picks based on coupling and risk | |

**User's choice:** Leave existing in place

---

## Parser Confidence

### Q4: Fill from summary-only cues?

| Option | Description | Selected |
|--------|-------------|----------|
| Fill from summary (Recommended) | Summary is filing-grounded LLM output — allow fill with info log | ✓ |
| Skip and warn | Only fill when span text independently confirms | |
| You decide | Claude picks based on GPT Pro guidance | |

**User's choice:** Fill from summary

### Q5: When summary and span disagree?

| Option | Description | Selected |
|--------|-------------|----------|
| Don't fill, emit warning (Recommended) | GPT Pro says do not fill on disagreement — emit warning for review | ✓ |
| Prefer span text | Span is direct filing quote, more authoritative | |
| Prefer summary | Summary reflects LLM interpretation with more context | |

**User's choice:** Don't fill, emit warning

### Q6: Repair log format?

| Option | Description | Selected |
|--------|-------------|----------|
| Structured repair log (Recommended) | Return list of RepairAction objects — enables metrics, gate input, audit trail | ✓ |
| Python logging only | Use logger.info/warning like existing repairs | |
| Both | Structured log AND Python logging | |

**User's choice:** Structured repair log

---

## Bidder Kind Strategy

### Q7: Parenthetical list handling?

| Option | Description | Selected |
|--------|-------------|----------|
| Parse and propagate (Recommended) | Regex-parse parenthetical body, match parties by alias, assign kind | ✓ |
| Secondary signal only | Only confirm existing classification, don't assign from parenthetical alone | |
| You decide | Claude picks based on filing patterns | |

**User's choice:** Parse and propagate

### Q8: Sponsor lexicon size?

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal (5-10 names) | Only most prominent PE firms | |
| Moderate (20-30 names) | Cover common M&A sponsors, still subordinate to filing evidence | ✓ |
| None — skip lexicon | Rely entirely on filing text | |

**User's choice:** Moderate (20-30 names)

---

## Test Fixture Scope

### Q9: Test data source?

| Option | Description | Selected |
|--------|-------------|----------|
| Synthetic text (Recommended) | Hand-crafted sentences isolating each pattern | ✓ |
| Real filing snippets | Extract actual sentences from 9 deals | |
| Mix of both | Synthetic for units, real for smoke test | |

**User's choice:** Synthetic text

### Q10: Test file organization?

| Option | Description | Selected |
|--------|-------------|----------|
| Single file, parametrized (Recommended) | tests/test_skill_structured_field_repairs_v2.py with @pytest.mark.parametrize | ✓ |
| Separate files per parser | test_repair_prices.py, test_repair_delivery.py, etc. | |
| You decide | Claude picks based on test complexity | |

**User's choice:** Single file, parametrized

---

## Claude's Discretion

- Internal module structure (parser organization within repair package)
- Exact regex patterns (refine from GPT Pro starting patterns)
- RepairAction model design
- Specific PE firm names in sponsor lexicon
- Subject-aware clause restriction implementation details
- Edge case handling not explicitly covered

## Deferred Ideas

None — discussion stayed within phase scope
