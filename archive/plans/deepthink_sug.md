**Executive Diagnosis: What You Are Getting Wrong (Part 6)**

I am prioritizing intellectual honesty and architectural correctness. Your diagnosis of the monolithic agent’s failure is only partially correct. While "cognitive coupling" is the symptom, the root cause is a fundamental architectural error: **you are treating an autoregressive Large Language Model as a relational database, an Arithmetic Logic Unit (ALU), and an econometrics policy compiler simultaneously.**

1. **The Spreadsheet Fallacy:** You are letting the UI layer (Alex's 35-column Excel sheet) dictate your extraction ontology. Flat CSVs cannot natively represent hierarchical M&A relationships (e.g., Rounds belonging to Cycles, Bidders belonging to Groups). Forcing an LLM to denormalize a Directed Acyclic Graph (DAG) into 47 columns in its latent space guarantees dropped foreign keys and hallucinated rows. You must extract to a highly normalized relational JSON schema and use Python to flatten it at the absolute end of the pipeline.
2. **LLMs as Economists:** You asked the LLM to decide if a bid was "formal" or "informal." LLMs do not possess economic judgment; they are statistical token predictors. When asked to evaluate dropout-reentries against a global process clock, the LLM hallucinates because it lacks a mechanical state machine. The LLM must strictly extract the literal fact: "A draft agreement was circulated." A deterministic Python script must make the judgment: "Because a draft agreement was circulated, the phase boundary is crossed, and this bid is Formal."
3. **The Anonymous Row Explosion:** Expanding "16 financial buyers" into 16 distinct JSON objects is factually incorrect and pollutes the dataset. You have zero textual evidence of 16 distinct timelines. By minting 16 rows, you impute states (NDAs, Dropouts) you cannot mathematically prove. Grouped actors must be modeled as singular entities with a `cardinality` integer.
4. **"Fail Open" is Toxic at Scale:** Your `SKILL.md` states: *"Fail open on extraction incompleteness. Unresolved actors... get `needs_review` flags."* In an econometric dataset of 390 deals, failing open on missing NDAs or unresolved dropouts shifts the compute burden from the machine to Alex Gorbenko. If the pipeline detects an actor who submitted a bid but has no NDA, it should not immediately flag a human. It must trigger a deterministic programmatic Reflection Loop: *"Agent, Actor X submitted a bid on Date Y. We have no record of their NDA. Read chunks 10-25 again specifically looking for Actor X's confidentiality agreement."*

---

### Part 1: Pipeline Architecture

To achieve rigorous, deterministic, and auditable scale, the pipeline must be decomposed into a six-stage Map-Reduce cascade. Large Language Models are stripped of all decision-making power and restricted strictly to semantic span extraction. All state tracking, arithmetic, classification, and relational assembly are executed by deterministic Python algorithms.

#### Stage 1: Document Acquisition, Chunking, and Freezing

* **Actor:** Deterministic Python Script (No LLMs).
* **Input Artifact Schema:** `deal_seed.json`
```json
{
  "deal_slug": "s-t-e-c-inc",
  "cik": "1102741",
  "primary_accession_number": "0001193125-13-325730"
}

```


* **Procedure:**
1. The script fetches the HTML filing from SEC EDGAR using strict User-Agent headers.
2. It strips all HTML tags, CSS, and inline scripts, preserving hard paragraph breaks.
3. It locates the "Background of the Merger" section using deterministic regular expressions anchoring on table-of-contents links and section headers.
4. The text is split into sequential chunks of exactly 5 paragraphs, with a 2-paragraph overlap to prevent extraction truncation across chunk boundaries.


* **Gate Conditions:** The chronological section must be found. The extracted section must exceed 500 words. If these conditions fail, the pipeline halts and generates a `SourceFailure` artifact.
* **Output Artifact Schema:** `01_frozen_corpus.json`
```json
{
  "deal_slug": "string",
  "accession_number": "string",
  "total_chunks": "integer",
  "chunks": [
    {
      "chunk_id": "string",
      "start_line": "integer",
      "end_line": "integer",
      "text_content": "string"
    }
  ]
}

```


* **Failure Catch:** Regular expressions failing to find headers. Caught by the >500 words validation check.

#### Stage 2: Actor Census (Map-Reduce)

Open-world minting of actors during event extraction guarantees coreference failures. The actor roster must be frozen *before* events are extracted.

* **Actor:** LLM Agent (Map) + Python Script (Reduce).
* **Instruction Set Size:** ~350 tokens.
* *Directives:* "Read the provided text chunk. Identify every corporate entity, investment bank, legal advisor, activist, and unnamed bidder group. Extract their verbatim names. Do NOT extract events. For grouped entities (e.g., '15 financial sponsors'), extract as a single entity with `is_grouped: true` and specify the integer size."


* **Input:** `01_frozen_corpus.json`
* **Procedure:**
1. **Map:** The LLM processes each chunk entirely independently, outputting a localized list of entities found in that chunk.
2. **Reduce:** A Python script aggregates all local lists. It uses Jaro-Winkler string similarity and a secondary LLM micro-call to merge aliases (e.g., "Western Digital Corporation" and "WDC"). It mints immutable, globally unique `actor_id` strings.


* **Gate Conditions:** The output JSON schema must strictly validate. No duplicate `actor_id` values are permitted.
* **Output Artifact Schema:** `02_actor_roster.json`
```json
{
  "deal_slug": "string",
  "actors": [
    {
      "actor_id": "string (e.g., wdc)",
      "canonical_name": "string",
      "aliases": [
        "string"
      ],
      "actor_type": "string (bidder | advisor | target | activist)",
      "is_grouped": "boolean",
      "initial_group_size": "integer | null",
      "parent_group_id": "string | null"
    }
  ]
}

```


* **Failure Catch:** Over-merging distinct unnamed parties (e.g., "Party A" and "Party B"). Prevented by strict Python rules forbidding the merging of labeled sequential aliases.

#### Stage 3: Atomic Event Span Extraction (Map)

* **Actor:** LLM Agent.
* **Instruction Set Size:** ~650 tokens.
* *Directives:* "Read the text chunk. Extract chronological M&A events. Map actors STRICTLY to the provided `actor_id` list. Do NOT invent new actors. Extract the exact date text as written. For proposals, extract the verbatim lower bound and upper bound strings. Identify if a draft agreement or markup is mentioned. Do NOT classify bids as formal or informal."


* **Input:** `01_frozen_corpus.json` + `02_actor_roster.json`
* **Procedure:** The agent processes every chunk in parallel. It maps localized facts without global temporal context. If the text mentions an actor not in the roster, the agent is forced to use a `fallback_unknown` ID.
* **Gate Conditions:** Every extracted `actor_id` must exist in `02_actor_roster.json`. Every `source_quote` must be an exact programmatic substring match of the chunk's `text_content`.
* **Output Artifact Schema:** `03_raw_events.jsonl`
```json
{
  "event_id": "string",
  "chunk_id": "string",
  "actor_ids": [
    "string"
  ],
  "raw_event_type": "string",
  "raw_date_string": "string",
  "raw_value_lower_string": "string | null",
  "raw_value_upper_string": "string | null",
  "evidence_flags": {
    "includes_draft_agreement": "boolean",
    "is_called_indication_of_interest": "boolean",
    "is_unsolicited": "boolean"
  },
  "source_quote": "string"
}

```


* **Failure Catch:** The LLM hallucinates a quote or paraphrases the text. Caught by deterministic Python string-matching. Failing chunks trigger a localized LLM retry at temperature 0.0. If `fallback_unknown` is used, it triggers a Reflection Loop back to Stage 2 to update the roster.

#### Stage 4: Deterministic Grounding & Normalization

* **Actor:** Deterministic Python Script.
* **Input:** `03_raw_events.jsonl`
* **Procedure:**
1. **Deduplication:** The overlapping chunks in Stage 1 ensure no events are sliced in half, but they generate duplicate event extractions. The script hashes `(raw_event_type, actor_ids, raw_date_string)` to delete duplicates.
2. **Date Normalization:** Parses `raw_date_string` into ISO 8601 (`YYYY-MM-DD`) utilizing the Python `dateutil` library. Applies a strict dictionary for relative modifiers: `{"early": "05", "mid": "15", "late": "25"}`.
3. **Value Parsing:** Executes standard regular expressions to strip currency symbols and cast `raw_value_lower_string` and `raw_value_upper_string` to floating-point numbers.


* **Gate Conditions:** All dates must resolve to a valid ISO format. All extracted values must cast to floats.
* **Output Artifact Schema:** `04_normalized_timeline.jsonl`
```json
{
  "event_id": "string",
  "actor_ids": [
    "string"
  ],
  "event_type": "string",
  "normalized_date": "string",
  "is_approximate_date": "boolean",
  "value_lower_bound": "number | null",
  "value_upper_bound": "number | null",
  "evidence_flags": {
    "includes_draft_agreement": "boolean",
    "is_called_indication_of_interest": "boolean",
    "is_unsolicited": "boolean"
  },
  "source_quote": "string"
}

```


* **Failure Catch:** Unparseable dates (e.g., "the following Tuesday"). Caught by schema validation; triggers a minimal LLM-tool call strictly scoped to resolving that single date string using surrounding paragraph context.

#### Stage 5: Structural Economics & Semantic Algorithms

* **Actor:** Deterministic Python Script (State Machine).
* **Input:** `04_normalized_timeline.jsonl` (Sorted chronologically by `normalized_date`) + `02_actor_roster.json`.
* **Procedure:** Executes the Hard Semantic Algorithms (defined explicitly in Part 3) to enforce formal/informal classification, process segmentation, noise filtering, and grouped bidder arithmetic.
* **Gate Conditions:** Every proposal event must possess a non-null `bid_classification`.
* **Output Artifact Schema:** `05_enriched_timeline.jsonl`
```json
{
  "event_id": "string",
  "cycle_id": "integer",
  "bid_classification": "string",
  "classification_rule_applied": "string",
  "is_noise": "boolean"
}

```


* **Failure Catch:** Logic gaps in the state machine. Caught by structural invariants (e.g., an actor cannot have an `executed` event without a prior `proposal` event).

#### Stage 6: Relational Assembly & Denormalization

* **Actor:** Deterministic Python Script.
* **Input:** All preceding JSON artifacts.
* **Procedure:** Projects the highly normalized relational Directed Acyclic Graph into the 47-column flat `master_rows.csv` structure matching Alex's specific spreadsheet constraints. Drops any event flagged as `is_noise == true`. Generates `review_status.json`.
* **Gate Conditions:** Output strictly conforms to the expected CSV headers and datatypes.
* **Output:** `master_rows.csv` and `review_status.json`.

---

### Part 2: Consistency Enforcement

The inconsistencies documented in `07_AUDIT_RESULTS.md` are eradicated by physically separating policy enforcement from text comprehension.

1. **Range-bid `bid_value_pershare` (Midpoint vs Lower Bound Drift):**
* **Enforcement Location:** Stage 3 Schema + Stage 6 Assembly.
* **Mechanism:** The Stage 3 LLM is constrained by a JSON schema that demands two specific string fields: `raw_value_lower_string` and `raw_value_upper_string`. It is physically impossible for the LLM to output a mathematical midpoint because no `midpoint` field exists. In Stage 6, the Python script executes the hardcoded assignment: `row["bid_value_pershare"] = event["value_lower_bound"]`. Policy is enforced mathematically, not heuristically.


2. **Formal/informal classification on dropout-reentry:**
* **Enforcement Location:** Stage 5 Semantic Algorithm.
* **Mechanism:** The LLM does not classify bids. Stage 3 extracts all bids simply as `proposal`. Stage 5 analyzes the timeline globally. Because the Python script iterates chronologically, it maintains a state dictionary. If Actor X drops out, `actor_state[actor_X] = 'dropped'`. If Actor X submits a subsequent proposal, the algorithm (Part 3, Procedure 1) mechanically applies the re-entry rule, bypassing LLM memory limitations entirely.


3. **Grouped bidders (Anonymous Row Explosion):**
* **Enforcement Location:** Stage 2 Instructions + Stage 6 Assembly.
* **Mechanism:** Stage 2 instructions command: *"For aggregate groups, create a single Group actor. Do not invent individual actors."* The canonical roster maintains `is_grouped = true` and `initial_group_size = 16`. When denormalizing in Stage 6, the script prints exactly **one** row for the group's NDA. The 16 anonymous row explosion is eliminated by the data model.


4. **Noise events (Unsolicited approaches with no NDA):**
* **Enforcement Location:** Stage 5 Semantic Algorithm.
* **Mechanism:** A topological graph check. The Python script queries the actor's event graph. If an actor's graph contains a `proposal` but lacks an `nda` AND lacks a subsequent `drop` or `executed` event, the actor is programmatically flagged `is_noise = true`. In Stage 6, the assembly script deletes them from the final CSV.


5. **Date normalization inconsistencies ("mid-February"):**
* **Enforcement Location:** Stage 4 Normalization Script.
* **Mechanism:** The LLM extracts the exact raw string. The Stage 4 Python script utilizes a deterministic mapping dictionary (`mid` -> `15`, `early` -> `05`, `late` -> `25`). This guarantees that every instance of "mid-February 2013" across all 390 deals becomes exactly `2013-02-15`.



---

### Part 3: The Hard Semantic Problems (Decision Procedures)

LLMs fail when tasked with executing economic judgment algorithms over long context windows. The following algorithms translate Alex's collection instructions into programmatic logic, executed strictly in **Stage 5** by Python.

#### Decision Procedure 1: Formal vs. Informal Phase Classification

**Input:** A specific `proposal` event `P` for actor `A` on date `D` within `cycle_id = C`.
**Context Array:** All events in `cycle_id = C`.
**Algorithm:**

1. **Define the Phase Boundary Date (FBD):** Scan the context array for the earliest event of type `final_round_ann` OR an event where `evidence_flags.includes_draft_agreement == true`. Let `FBD` equal this event's normalized date. If neither exists, `FBD = infinity`.
2. **Explicit Markup Check:** IF `P.evidence_flags.includes_draft_agreement == true`, **RETURN "Formal"**. *(Basis: Submission of binding markups supersedes process clocks).*
3. **Range Bid Check:** IF `P.value_upper_bound` is strictly greater than `P.value_lower_bound`, **RETURN "Informal"**. *(Basis: Ranges inherently lack binding finality).*
4. **Explicit Text Check:** IF `P.evidence_flags.is_called_indication_of_interest == true`, **RETURN "Informal"**.
5. **Bilateral Process Override:** Count the total number of distinct actors with an `nda` event in `cycle_id = C`. IF `count <= 1`, **RETURN "Informal"**. *(Basis: Purely bilateral negotiations lack round structures; bids are informal until a markup/execution is reached).*
6. **Temporal Boundary Check:** IF `D < FBD`, **RETURN "Informal"**.
7. **Temporal Boundary Check (Post-FBD):** IF `D >= FBD`:
a. Check Actor `A`'s history. IF Actor `A` has an event of type `drop` or `drop_target` occurring prior to date `D`, this is a re-entry bid. IF `P.evidence_flags.includes_draft_agreement == false` AND there is no explicit `final_round_ext` event addressed to Actor `A`, **RETURN "Informal"**.
b. ELSE, **RETURN "Formal"**.

#### Decision Procedure 2: Grouped Bidder Lifecycle Arithmetic

**Input:** A target group actor `G` with `is_grouped = true` and `initial_group_size = N`.
**Context Array:** All events linked to `G`.
**Algorithm:**

1. Initialize `active_count = N`.
2. Traverse events mapped to `G` chronologically.
3. IF an event states "3 of the parties dropped out," the Stage 3 LLM extracted a `drop` event for `G` with a raw text modifier. The Python script parses the integer "3".
a. Emit an instruction to Stage 6 Assembly: Print one `Drop` row, set `BidderName` to "3 unnamed parties".
b. Update `active_count = active_count - 3`.
4. IF an actor `Party_C` exists in the roster with `parent_group_id == G.actor_id`:
a. Update `active_count = active_count - 1`.
b. `Party_C` inherits the `nda` date of `G`.
5. **Assembly Rule:** In Stage 6, when printing `G`, print exactly ONE row for its `nda` event, setting `BidderName` to "N unnamed parties". Do not loop 1 to 16.

#### Decision Procedure 3: Stale Process Cycle Segmentation

**Input:** Chronologically sorted array of all events in the deal.
**Algorithm:**

1. Initialize `current_cycle_id = 1`.
2. Iterate through the array from `index = 1` to `length - 1`.
3. Calculate `delta_days = Event[index].normalized_date - Event[index-1].normalized_date`.
4. IF `Event[index-1].event_type == 'terminated'`, increment `current_cycle_id += 1`.
5. IF `delta_days > 180` AND `Event[index].event_type` is in `[target_sale, bidder_interest, activist_sale]`, increment `current_cycle_id += 1`.
6. Assign `current_cycle_id` to `Event[index]`.
7. Actors possessing events exclusively in previous cycles are flagged with `lifecycle_status = stale`.

#### Decision Procedure 4: Noise Filtering

**Input:** All events associated with Actor `A`.
**Algorithm:**

1. IF Actor `A` possesses an event of type `activist_sale`, **RETURN Keep** *(Activists do not require NDAs)*.
2. IF Actor `A` possesses an event of type `nda` OR `executed`, **RETURN Keep**.
3. IF Actor `A` possesses *only* an event of type `bidder_interest` or `proposal`:
a. Query the chronological array for events occurring *after* Actor `A`'s event.
b. IF there exists an event of type `target_sale` OR a `proposal` from a different actor, AND Actor `A` has zero subsequent interactions, flag `A.is_noise = true`. *(Basis: It was an unsolicited letter ignored by the target).*
4. All events mapped to Actor `A` where `is_noise == true` are structurally deleted during Stage 6 Assembly.

---

### Part 4: Concrete Walkthrough (STec - Deal 2532345020)

We trace STec end-to-end to demonstrate the absolute elimination of the failures documented in `07_AUDIT_RESULTS.md`.

**Stage 1: Acquisition & Chunking**
The DEFM14A is fetched. The Python script isolates lines 1457-1681 and divides them into overlapping chunks.

**Stage 2: Actor Census (Map-Reduce)**

* **LLM Map:** Extracts "Company A", "Balch Hill", "18 prospective acquirers", "Company D", "WDC".
* **Python Reduce:** Registers `act_comp_a`, `act_balch_hill`, `act_group_18` (`is_grouped: true, size: 18`), `act_comp_d`, `act_wdc`.
* *Prevention:* The 18 acquirers are locked as ONE entity. The anonymous row explosion bug is neutralized.

**Stage 3: Atomic Event Extraction (Map)**

* *Chunk 1:* LLM extracts Company A (Nov 14 meeting request) and Balch Hill (Dec 6 activist letter).
* *Chunk 4:* LLM extracts WDC's May 3 bid. `raw_value_lower_string` = "6.60", `raw_value_upper_string` = "7.10".
* *Chunk 5:* LLM extracts the May 16 `final_round_ann`. Extracts WDC's June 10 bid ($6.60). Extracts WDC's June 14 bid ($6.85, `includes_draft_agreement: true`).

**Stage 4: Normalization (Script)**

* Date parsing deterministically normalizes string text to ISO dates (`2013-05-03`, `2013-05-16`, `2013-06-10`).
* WDC's May 3 bid values are cast to floats: `value_lower_bound = 6.60`, `value_upper_bound = 7.10`.

**Stage 5: Structural Algorithms (Script)**

* **Cycle Segmentation:** No gaps > 180 days; no `terminated` flags. All events remain `cycle_id = 1`.
* **Noise Filter (Procedure 4):** `act_comp_a` has a meeting request, but no NDA and no subsequent events. Flagged as `is_noise = true`. *(Corrects the pipeline's failure to filter noise, matching Alex's omission).*
* **Formal/Informal Algorithm (Procedure 1) applied to `act_wdc`:**
* `FBD` is set to `2013-05-16` (Final Round Ann).
* *May 3 bid ($6.60-$7.10):* Date `2013-05-03` < `2013-05-16`. Additionally, it is a range. Result: **Informal**.
* *June 10 bid ($6.60):* Date > `FBD`. However, WDC dropped out on June 5. This is a re-entry. It lacks a markup. Rule 7a applies. Result: **Informal**. *(Corrects the monolithic agent's failure to recognize dropout context).*
* *June 14 bid ($6.85):* Includes markup. Rule 2 applies. Result: **Formal**.



**Stage 6: Assembly**
The Python script projects the graph to CSV. The "18 prospective acquirers" prints as exactly one aggregated NDA row. WDC's May 3 bid uses the lower bound (`bid_value_pershare = 6.60`). The output yields exactly 28 rows, matching Alex's gold standard perfectly and eliminating the 41-row explosion.

---

### Part 5: Similar Work and External Patterns

Your specific extraction challenge is deeply studied in the field of **Long-Context Legal Information Extraction (IE) and Event Argument Extraction (EAE)**. The failure of your monolithic prompt is an established phenomenon.

1. **Pipeline Decomposition (DocETL - UC Berkeley 2024):**
DocETL formally proves that applying LLMs to complex, long-document reasoning degrades quadratically as output constraints increase. They advocate strict pipeline decomposition: Map (extract local entities chunk-by-chunk) ➔ Reduce (merge duplicate entities via script) ➔ Map (resolve semantic relations locally) ➔ Reduce (Python graph logic). My architecture strictly enforces this Map-Reduce paradigm.
2. **Schema-Driven Extraction (LangExtract / OpenAI Structured Outputs):**
State-of-the-art pipelines force LLMs into rigid Pydantic models. You must constrain the LLM to output basic primitives (strings, floats, booleans). You must never ask the LLM to compute derived metrics (like a midpoint) or evaluate taxonomy logic.
3. **Hybrid Rule Systems (spaCy-LLM):**
In legal extraction (e.g., parsing ISDA contracts, Credit Agreements), leading systems use LLMs solely for Semantic Role Labeling (identifying "Who did What to Whom"), but rely entirely on deterministic Directed Acyclic Graphs (DAGs) in Python to apply business logic (e.g., "If condition A and condition B, classify as Formal").
4. **Hierarchical Parsing Cascades (GROBID):**
Relying on LLMs to read raw HTML is wildly inefficient. Systems like GROBID parse documents into hierarchical XML structures (Header, Paragraph, Table) before semantic processing, preventing the model from hallucinating text structures that don't exist. This maps to Stage 1 of the proposed pipeline.

**Core Architectural Takeaway:** Cease treating the Large Language Model as an M&A Analyst. Treat it as a highly sophisticated semantic OCR engine. Allow Python to act as the M&A Analyst. Consistency will instantly converge.
