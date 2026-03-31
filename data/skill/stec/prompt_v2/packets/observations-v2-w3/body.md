<deal_context>
deal_slug: stec
target_name: S T E C INC
source_accession_number: 0001193125-13-325730
source_form_type: UNKNOWN
chunk_mode: chunked
window_id: w3
</deal_context>

<chronology_blocks>
B234 [L2036-L2041]: BofA Merrill Lynch and its affiliates in the past have provided, currently are providing, and in the future may provide investment banking, commercial banking and other financial services to WDC and certain of its affiliates and have received or in the future may receive compensation for the rendering of these services, including (a) having acted or acting as administrative agent, lead arranger and bookrunner for, and/or as a lender under, certain term loans, letters of credit and credit and leasing facilities and other credit arrangements of WDC and certain of its affiliates (including acquisition financing), (b) having acted as financial advisor to WDC in connection with an acquisition transaction, (c) having provided or providing certain derivatives, foreign exchange and other trading services to WDC and certain of its affiliates, and (d) having provided or providing certain treasury management products and services to WDC and certain of its affiliates. From January 1, 2011 through June 30, 2013, BofA Merrill Lynch and its affiliates received aggregate revenues from WDC and certain of its affiliates of approximately $45 million for corporate, commercial and investment banking services.
B235 [L2043-L2043]: 44
</chronology_blocks>

<overlap_context>
B232 [L2025-L2028]: sTec has agreed to pay BofA Merrill Lynch for its services in connection with the merger an aggregate fee of approximately $4.3 million, $250,000 of which was payable in connection with its opinion and the remainder of which is contingent upon the completion of the merger, subject to certain initial and quarterly retainer fee payments which will be credited against the portion of the fee that will be paid upon completion of the merger. sTec also has agreed to reimburse BofA Merrill Lynch for its expenses incurred in connection with BofA Merrill Lynchs engagement and to indemnify BofA Merrill Lynch, any controlling person of BofA Merrill Lynch and each of their respective directors, officers, employees, agents and affiliates against specified liabilities, including liabilities under the federal securities laws.
B233 [L2030-L2034]: BofA Merrill Lynch and its affiliates comprise a full service securities firm and commercial bank engaged in securities, commodities and derivatives trading, foreign exchange and other brokerage activities, and principal investing as well as providing investment, corporate and private banking, asset and investment management, financing and financial advisory services and other commercial services and products to a wide range of companies, governments and individuals. In the ordinary course of their businesses, BofA Merrill Lynch and its affiliates invest on a principal basis or on behalf of customers or manage funds that invest, make or hold long or short positions, finance positions or trade or otherwise effect transactions in the equity, debt or other securities or financial instruments (including derivatives, bank loans or other obligations) of sTec, WDC and certain of their respective affiliates.
</overlap_context>

<evidence_checklist>
### Dated actions to extract
- [ ] **0001193125-13-325730:E0539** L2036-L2041 (date: may; actor: Merrill Lynch; value: $45; terms: received)

### Financial terms to capture
- [ ] **0001193125-13-325730:E0536** L2025-L2028 (actor: Merrill Lynch; value: $4.3; terms: $250,000, $4.3)
- [ ] **0001193125-13-325730:E0540** L2036-L2041 (date: may; actor: Merrill Lynch; value: $45; terms: $45)

### Actors to identify
- [ ] **0001193125-13-325730:E0537** L2025-L2028 (actor: Merrill Lynch; value: $4.3)
- [ ] **0001193125-13-325730:E0538** L2030-L2034 (actor: Merrill Lynch; terms: advisor, financial advisor)
- [ ] **0001193125-13-325730:E0541** L2036-L2041 (date: may; actor: Merrill Lynch; value: $45; terms: advisor, financial advisor, investment bank)
</evidence_checklist>

<task_instructions>
IMPORTANT: You MUST follow the quote-before-extract protocol.

Step 1 - QUOTE: Read the chronology blocks above. Copy every verbatim passage needed to support party, cohort, and observation extraction into the quotes array. Each quote needs a unique quote_id (Q001, Q002, ...), the source block_id, and the exact filing text.

Step 2 - EXTRACT: Return filing-literal structure only. Build:
- parties: named bidders, advisors, activists, target-side boards/entities, and aliases
- cohorts: unnamed bidder groups with exact_count, known members when explicit, and the observation that created the cohort
- observations: only the six v2 observation types (process, agreement, solicitation, proposal, status, outcome)

Observation rules:
- Do not emit analyst rows, benchmark rows, dropout labels, bid labels, or other derived judgments.
- Keep every field filing-literal. If a structured field is ambiguous, set it to null or use the appropriate `other` escape hatch with a short detail string.
- Use quote_ids, never evidence_refs or inline anchor_text.
- Proposals must use bidder or bidder-cohort subject_refs.
- Solicitation observations should represent the request/announcement, with due_date when the filing gives a deadline.
- Status observations cover expressed interest, withdrawal, exclusion, cannot-improve, selected-to-advance, and similar literal process states.

Return a single JSON object with keys in this order: quotes, parties, cohorts, observations, exclusions, coverage.
</task_instructions>