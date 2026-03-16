# Actor Scheme

Actor identification, naming, type classification, and artifact schemas
for the party register.

## Actor ID Scheme

Every actor gets a stable ID: `<deal_slug>/<label>`.

- Lowercase throughout, hyphens for spaces.
- The ID never changes after creation, even if the actor's name is
  later revealed.

**Naming priority (use the first that applies):**

1. **Filing's own label** -- "Party A" -> `party_a`, "Bidder B" ->
   `bidder_b`, "Company C" -> `company_c`.
2. **Entity name** -- "J.P. Morgan" -> `jp-morgan`, "Goldman Sachs" ->
   `goldman-sachs`.
3. **Unnamed aggregate** -- `unnamed_1`, `unnamed_2`, ... for parties
   from aggregate descriptions ("15 financial buyers") that are not
   individually identified.

## Actor Types

| Type | Who |
|------|-----|
| `bidder` | Any party making or considering an acquisition bid |
| `advisor` | Investment bank, financial advisor, or law firm retained by target |
| `activist` | Shareholder activist pressuring the target |
| `target_board` | The target company's board of directors |

## Bidder Subtypes

| Subtype | Description |
|---------|-------------|
| `strategic` | Operating company (acquires for business combination) |
| `financial` | PE firm, fund, or financial sponsor |
| `non_us` | Non-US acquirer (strategic or financial) |
| `mixed` | Consortium combining strategic and financial |

Only populated when `actor_type = "bidder"`. Null otherwise.

## actors.jsonl Schema

One JSON line per actor. All fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `actor_id` | string | yes | `<deal_slug>/<label>` |
| `actor_alias` | string | yes | Human-readable name (filing label or entity name) |
| `actor_type` | string | yes | `bidder` / `advisor` / `activist` / `target_board` |
| `bidder_subtype` | string | no | `strategic` / `financial` / `non_us` / `mixed` |
| `is_grouped` | boolean | no | True if consortium |
| `group_size` | int | no | Number of parties in group |
| `lifecycle_status` | string | yes | `bid` / `dropped` / `dropped_by_target` / `winner` / `stale` / `advisor` / `unresolved` |
| `actor_notes` | string | no | Free text |
| `first_evidence_accession_number` | string | yes | Filing where actor first appears |
| `first_evidence_line_start` | int | yes | Line in .txt |
| `first_evidence_line_end` | int | yes | Line in .txt |
| `first_evidence_text` | string | yes | Verbatim quote establishing identity |

**Example:**

```json
{"actor_id": "petsmart-inc/party_a", "actor_alias": "Party A", "actor_type": "bidder", "bidder_subtype": "financial", "is_grouped": false, "group_size": null, "lifecycle_status": "bid", "actor_notes": null, "first_evidence_accession_number": "0001571049-15-000695", "first_evidence_line_start": 1265, "first_evidence_line_end": 1267, "first_evidence_text": "representatives of Party A contacted the Company's financial advisor to express interest in a potential transaction"}
```

**lifecycle_status at roster time:** Set to `"bid"` for bidders as a
default. Skill 5 (extract-events) will update terminal statuses based
on events. Advisors get `"advisor"` immediately.

## count_assertions.json Schema

Array of assertion objects. Each represents one numeric claim the filing
makes about party counts, NDA counts, etc.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `assertion_id` | string | yes | Unique within deal (e.g., `pet_nda_count_1`) |
| `assertion_text` | string | yes | The full sentence containing the assertion |
| `metric` | string | yes | What is counted: `nda_signed`, `indication_count`, `parties_contacted`, `bidders_invited`, etc. |
| `expected_count` | int | yes | The number stated in the filing |
| `time_scope` | string | yes | As of when (e.g., "first_week_october_2014") |
| `cycle_scope` | string | yes | Which process cycle (e.g., "cycle_1") |
| `source_accession_number` | string | yes | Filing accession |
| `source_line_start` | int | yes | Line in .txt |
| `source_line_end` | int | yes | Line in .txt |
| `source_text` | string | yes | Verbatim quote from filing |

**Example:**

```json
[
  {
    "assertion_id": "pet_nda_count_1",
    "assertion_text": "15 potentially interested financial buyers were contacted",
    "metric": "parties_contacted",
    "expected_count": 15,
    "time_scope": "first_week_october_2014",
    "cycle_scope": "cycle_1",
    "source_accession_number": "0001571049-15-000695",
    "source_line_start": 1270,
    "source_line_end": 1272,
    "source_text": "During the first week of October 2014, 15 potentially interested financial buyers were contacted."
  }
]
```

## decisions.jsonl Schema

Append-only log shared across skills 4-8. Each line is one decision.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `skill` | string | yes | Skill that made the decision (e.g., `"build-party-register"`) |
| `decision_type` | string | yes | One of the decision types below |
| `detail` | string | yes | Human-readable explanation of the decision |
| `artifact_affected` | string | yes | Which file is affected (e.g., `"actors.jsonl"`) |
| `target_id` | string | yes | ID of the affected object |
| `confidence` | string | yes | `high` / `medium` / `low` |

**Decision types:**

| Type | When used |
|------|-----------|
| `alias_merge` | Two labels refer to the same entity |
| `approximate_date` | Filing gives vague date, recorded as specific date |
| `implicit_dropout` | No explicit dropout statement, inferred from context |
| `event_type_choice` | Ambiguous event categorization |
| `actor_type_classification` | Ambiguous actor type or bidder subtype |
| `count_interpretation` | Ambiguous aggregate count |
| `cycle_boundary` | Where one process cycle ends and another begins |
| `filing_selection` | Why a particular filing was chosen |
| `scope_exclusion` | Why a partial-asset bid or segment bid was excluded |

**Example (alias_merge):**

```json
{"skill": "build-party-register", "decision_type": "alias_merge", "detail": "Party A and Company A treated as same entity per paragraph context", "artifact_affected": "actors.jsonl", "target_id": "petsmart-inc/party_a", "confidence": "high"}
```

**Example (actor_type_classification):**

```json
{"skill": "build-party-register", "decision_type": "actor_type_classification", "detail": "Goldman Sachs classified as advisor (retained by target per line 1280) not bidder", "artifact_affected": "actors.jsonl", "target_id": "petsmart-inc/goldman-sachs", "confidence": "high"}
```
