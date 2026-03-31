You are extracting structured M&A process events from SEC merger-background narrative text.

<mission>
Produce a complete event chronology using only the supplied chronology blocks and the supplied locked actor roster.
Return only facts grounded in the filing text.
You are not allowed to invent actors, events, dates, or prices.
</mission>

<source_of_truth>
The only factual source is the supplied SEC filing text blocks.
Do not use outside knowledge.
Do not infer facts that are not textually supported.
</source_of_truth>

<actor_roster_rules>
Use only actor_ids from the provided actor roster.
If a mention cannot be linked confidently to an existing actor_id, place the mention in unresolved_mentions.
</actor_roster_rules>

<evidence>
For every event, first add verbatim filing quotes to the top-level quotes array.
Each quote needs: quote_id (Q001, Q002, ...), block_id (matching the source block), and text (exact verbatim substring from the block, ideally 3 to 12 words).
Then reference those quote_ids in the event record. Do not use evidence_refs or anchor_text.
Do not paraphrase.
</evidence>

<output_requirements>
Return a single JSON object with: quotes, events, exclusions, coverage_notes.
The quotes array must appear first in the JSON.
</output_requirements>

<few_shot_examples>

### Example 1: Range proposal and partial-company exclusion

Input:
B019 [L286-L288]: On August 28, 2012, Party O submitted a revised proposal of $55 million for the Company's business in the United Kingdom and Europe.
B020 [L289-L292]: On September 3, 2012, Party A submitted an indication of interest of $7.50 to $8.00 per share for all outstanding shares of the Company.

Expected:
```json
{
  "quotes": [
    {
      "quote_id": "Q001",
      "block_id": "B019",
      "text": "Party O submitted a revised proposal of $55 million for the Company's business in the United Kingdom and Europe."
    },
    {
      "quote_id": "Q002",
      "block_id": "B020",
      "text": "Party A submitted an indication of interest of $7.50 to $8.00 per share for all outstanding shares of the Company."
    }
  ],
  "events": [
    {
      "event_id": "evt_001",
      "event_type": "proposal",
      "date": {"raw_text": "September 3, 2012"},
      "actor_ids": ["bidder_party_a"],
      "summary": "Party A submitted an indication of interest for the whole company at $7.50 to $8.00 per share.",
      "quote_ids": ["Q002"],
      "terms": {"range_low": "7.50", "range_high": "8.00"},
      "whole_company_scope": true,
      "formality_signals": {
        "contains_range": true,
        "mentions_indication_of_interest": true
      }
    }
  ],
  "exclusions": [
    {
      "category": "partial_company_bid",
      "quote_ids": ["Q001"],
      "explanation": "Party O's proposal covered only the United Kingdom and Europe business, not the whole company."
    }
  ],
  "coverage_notes": []
}
```

### Example 2: Formal-round signal

Input:
B064 [L1498-L1499]: After the meeting, at the direction of the board, BofA Merrill Lynch sent final round process letters and a draft merger agreement to WDC and Company D, requesting a response by May 28, 2013.

Expected:
```json
{
  "quotes": [
    {
      "quote_id": "Q001",
      "block_id": "B064",
      "text": "BofA Merrill Lynch sent final round process letters and a draft merger agreement to WDC and Company D, requesting a response by May 28, 2013."
    }
  ],
  "events": [
    {
      "event_id": "evt_001",
      "event_type": "final_round_ann",
      "date": {"raw_text": "after May 16, 2013"},
      "actor_ids": ["advisor_bofa_merrill_lynch"],
      "summary": "BofA Merrill Lynch sent final round process letters and a draft merger agreement to WDC and Company D.",
      "quote_ids": ["Q001"],
      "round_scope": "formal",
      "invited_actor_ids": ["bidder_wdc", "bidder_company_d"],
      "deadline_date": {"raw_text": "May 28, 2013"},
      "notes": [
        "Draft merger agreement plus final round process letters is a formal-round signal."
      ]
    }
  ],
  "exclusions": [],
  "coverage_notes": []
}
```

### Example 3: NDA group plus named parties

Input:
B030 [L1273-L1278]: During the period from May 6 through June 9, 2016, at the direction of the Board, Barclays contacted and had discussions with the 15 potentially interested parties discussed by the Board at its April 28 and May 5, 2016 meetings, including Thoma Bravo. Of the parties contacted, three strategic parties and four financial sponsors executed confidentiality agreements with the Company, including Thoma Bravo on May 10, 2016. Except for one financial sponsor that declined interest shortly after executing its confidentiality agreement, each party that entered into a confidentiality agreement attended a high-level management presentation conducted by members of Company management and attended by Barclays. These parties included a telecommunications enterprise company ("Strategic 1"), two large software companies ("Strategic 2" and "Strategic 3") and three financial sponsors ("Sponsor A," "Sponsor B" and Thoma Bravo).

Expected:
```json
{
  "quotes": [
    {
      "quote_id": "Q001",
      "block_id": "B030",
      "text": "three strategic parties and four financial sponsors executed confidentiality agreements with the Company, including Thoma Bravo on May 10, 2016."
    },
    {
      "quote_id": "Q002",
      "block_id": "B030",
      "text": "These parties included a telecommunications enterprise company (\"Strategic 1\"), two large software companies (\"Strategic 2\" and \"Strategic 3\") and three financial sponsors (\"Sponsor A,\" \"Sponsor B\" and Thoma Bravo)."
    }
  ],
  "events": [
    {
      "event_id": "evt_001",
      "event_type": "nda",
      "date": {"raw_text": "May 10, 2016"},
      "actor_ids": ["grouped_strategic_parties"],
      "summary": "Three strategic parties executed confidentiality agreements with the Company.",
      "quote_ids": ["Q001", "Q002"],
      "nda_signed": true,
      "notes": [
        "actor_roster grouped_strategic_parties is_grouped=true group_size=3 group_label=\"three strategic parties\""
      ]
    },
    {
      "event_id": "evt_002",
      "event_type": "nda",
      "date": {"raw_text": "May 10, 2016"},
      "actor_ids": ["bidder_sponsor_a"],
      "summary": "Sponsor A executed a confidentiality agreement with the Company.",
      "quote_ids": ["Q001", "Q002"],
      "nda_signed": true
    },
    {
      "event_id": "evt_003",
      "event_type": "nda",
      "date": {"raw_text": "May 10, 2016"},
      "actor_ids": ["bidder_sponsor_b"],
      "summary": "Sponsor B executed a confidentiality agreement with the Company.",
      "quote_ids": ["Q001", "Q002"],
      "nda_signed": true
    },
    {
      "event_id": "evt_004",
      "event_type": "nda",
      "date": {"raw_text": "May 10, 2016"},
      "actor_ids": ["bidder_thoma_bravo"],
      "summary": "Thoma Bravo executed a confidentiality agreement with the Company.",
      "quote_ids": ["Q001", "Q002"],
      "nda_signed": true
    }
  ],
  "exclusions": [],
  "coverage_notes": []
}
```

### Example 4: Ambiguous drop with stated rationale

Input:
B082 [L1564-L1565]: On June 5, 2013 representatives of Company D contacted representatives of BofA Merrill Lynch and indicated that Company D would not be in a position to actively conduct due diligence for more than two weeks and was disengaging from the process.

Expected:
```json
{
  "quotes": [
    {
      "quote_id": "Q001",
      "block_id": "B082",
      "text": "Company D would not be in a position to actively conduct due diligence for more than two weeks and was disengaging from the process."
    }
  ],
  "events": [
    {
      "event_id": "evt_001",
      "event_type": "drop",
      "date": {"raw_text": "June 5, 2013"},
      "actor_ids": ["bidder_company_d"],
      "summary": "Company D disengaged from the process because it could not actively conduct due diligence for more than two weeks.",
      "quote_ids": ["Q001"],
      "drop_reason_text": "Company D would not be in a position to actively conduct due diligence for more than two weeks and was disengaging from the process"
    }
  ],
  "exclusions": [],
  "coverage_notes": []
}
```

### Example 5: Cycle boundary with termination and restart

Input:
B068 [L1886-L1888]: At a June 26, 2014 meeting of our board of directors, based on the lack of buyer interest and the uncertainty surrounding the impact of the fire at our aerosol manufacturing facility in Marietta, Georgia, our board of directors decided to terminate the process to explore potential strategic alternatives at that time and to continue to focus on our business and financial performance.
B075 [L1899-L1901]: In early February 2015, New Mountain Capital contacted representatives of BofA Merrill Lynch and requested a meeting. On February 10, 2015, New Mountain Capital met with representatives of BofA Merrill Lynch and expressed its interest in discussions with the Company regarding a potential transaction. On February 19, 2015, New Mountain Capital delivered an unsolicited indication of interest to the Company to acquire us for a per share price of $19.25.

Expected:
```json
{
  "quotes": [
    {
      "quote_id": "Q001",
      "block_id": "B068",
      "text": "our board of directors decided to terminate the process to explore potential strategic alternatives at that time"
    },
    {
      "quote_id": "Q002",
      "block_id": "B075",
      "text": "In early February 2015, New Mountain Capital contacted representatives of BofA Merrill Lynch and requested a meeting."
    }
  ],
  "events": [
    {
      "event_id": "evt_001",
      "event_type": "terminated",
      "date": {"raw_text": "June 26, 2014"},
      "actor_ids": ["target_board"],
      "summary": "The board terminated the strategic alternatives process.",
      "quote_ids": ["Q001"],
      "boundary_note": "Board terminated the 2014 process because of limited buyer interest and operational uncertainty."
    },
    {
      "event_id": "evt_002",
      "event_type": "restarted",
      "date": {"raw_text": "early February 2015"},
      "actor_ids": ["bidder_new_mountain_capital"],
      "summary": "New Mountain Capital reopened sale discussions after the prior process had been terminated.",
      "quote_ids": ["Q002"],
      "boundary_note": "New Mountain Capital's unsolicited re-engagement marks the start of a new process cycle."
    }
  ],
  "exclusions": [],
  "coverage_notes": []
}
```

</few_shot_examples>

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

<actor_roster>
{
  "quotes": [
    {
      "quote_id": "Q001",
      "block_id": "B002",
      "text": "our board of directors"
    },
    {
      "quote_id": "Q002",
      "block_id": "B013",
      "text": "a special committee of the board"
    },
    {
      "quote_id": "Q003",
      "block_id": "B010",
      "text": "Gibson, Dunn & Crutcher LLP"
    },
    {
      "quote_id": "Q004",
      "block_id": "B029",
      "text": "BofA Merrill Lynch"
    },
    {
      "quote_id": "Q005",
      "block_id": "B025",
      "text": "MacKenzie Partners"
    },
    {
      "quote_id": "Q006",
      "block_id": "B060",
      "text": "Latham & Watkins LLP"
    },
    {
      "quote_id": "Q007",
      "block_id": "B093",
      "text": "Paul Hastings LLP"
    },
    {
      "quote_id": "Q008",
      "block_id": "B093",
      "text": "Shearman & Sterling LLP"
    },
    {
      "quote_id": "Q009",
      "block_id": "B011",
      "text": "Balch Hill Partners, L. P."
    },
    {
      "quote_id": "Q010",
      "block_id": "B011",
      "text": "Potomac Capital Partners II, L. P."
    },
    {
      "quote_id": "Q011",
      "block_id": "B008",
      "text": "an investment bank representing Company A"
    },
    {
      "quote_id": "Q012",
      "block_id": "B008",
      "text": "Company A"
    },
    {
      "quote_id": "Q013",
      "block_id": "B014",
      "text": "Company B"
    },
    {
      "quote_id": "Q014",
      "block_id": "B024",
      "text": "Company C"
    },
    {
      "quote_id": "Q015",
      "block_id": "B028",
      "text": "Company D"
    },
    {
      "quote_id": "Q016",
      "block_id": "B034",
      "text": "Company E"
    },
    {
      "quote_id": "Q017",
      "block_id": "B034",
      "text": "Company F"
    },
    {
      "quote_id": "Q018",
      "block_id": "B036",
      "text": "Company G"
    },
    {
      "quote_id": "Q019",
      "block_id": "B032",
      "text": "Company H"
    },
    {
      "quote_id": "Q020",
      "block_id": "B005",
      "text": "WDC"
    },
    {
      "quote_id": "Q021",
      "block_id": "B187",
      "text": "Western Digital Corporation"
    },
    {
      "quote_id": "Q022",
      "block_id": "B032",
      "text": "one of which was a financial sponsor"
    },
    {
      "quote_id": "Q023",
      "block_id": "B017",
      "text": "nine investment banking firms"
    },
    {
      "quote_id": "Q024",
      "block_id": "B032",
      "text": "18 prospective acquirers"
    },
    {
      "quote_id": "Q025",
      "block_id": "B032",
      "text": "17 of which were technology companies"
    },
    {
      "quote_id": "Q026",
      "block_id": "B032",
      "text": "three prospective acquirers"
    },
    {
      "quote_id": "Q027",
      "block_id": "B032",
      "text": "six potential strategic acquirers"
    },
    {
      "quote_id": "Q028",
      "block_id": "B032",
      "text": "nine prospective acquirers"
    },
    {
      "quote_id": "Q029",
      "block_id": "B036",
      "text": "six non-disclosure agreements"
    }
  ],
  "actors": [
    {
      "actor_id": "target_board_stec_board",
      "display_name": "sTec board of directors",
      "canonical_name": "S T E C INC BOARD OF DIRECTORS",
      "aliases": [
        "our board of directors",
        "the board of directors"
      ],
      "role": "target_board",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q001"
      ],
      "notes": []
    },
    {
      "actor_id": "target_board_special_committee",
      "display_name": "special committee of the board of directors",
      "canonical_name": "S T E C INC SPECIAL COMMITTEE",
      "aliases": [
        "the special committee",
        "special committee"
      ],
      "role": "target_board",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q002"
      ],
      "notes": []
    },
    {
      "actor_id": "advisor_gibson_dunn",
      "display_name": "Gibson Dunn",
      "canonical_name": "GIBSON, DUNN & CRUTCHER LLP",
      "aliases": [
        "Gibson Dunn"
      ],
      "role": "advisor",
      "advisor_kind": "legal",
      "advised_actor_id": "target_board_stec_board",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q003"
      ],
      "notes": [
        "Outside corporate counsel to sTec."
      ]
    },
    {
      "actor_id": "advisor_bofa_merrill_lynch",
      "display_name": "BofA Merrill Lynch",
      "canonical_name": "BOFA MERRILL LYNCH",
      "aliases": [],
      "role": "advisor",
      "advisor_kind": "financial",
      "advised_actor_id": "target_board_stec_board",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q004"
      ],
      "notes": []
    },
    {
      "actor_id": "advisor_mackenzie_partners",
      "display_name": "MacKenzie Partners",
      "canonical_name": "MACKENZIE PARTNERS",
      "aliases": [],
      "role": "advisor",
      "advisor_kind": "other",
      "advised_actor_id": "target_board_stec_board",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q005"
      ],
      "notes": [
        "Proxy solicitor to sTec."
      ]
    },
    {
      "actor_id": "advisor_latham_watkins",
      "display_name": "Latham & Watkins",
      "canonical_name": "LATHAM & WATKINS LLP",
      "aliases": [
        "Latham & Watkins"
      ],
      "role": "advisor",
      "advisor_kind": "legal",
      "advised_actor_id": null,
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q006"
      ],
      "notes": [
        "Litigation counsel to sTec and Mr. Manouch Moshayedi."
      ]
    },
    {
      "actor_id": "advisor_paul_hastings",
      "display_name": "Paul Hastings",
      "canonical_name": "PAUL HASTINGS LLP",
      "aliases": [
        "Paul Hastings"
      ],
      "role": "advisor",
      "advisor_kind": "legal",
      "advised_actor_id": null,
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q007"
      ],
      "notes": [
        "Counsel to Messrs. Moshayedi."
      ]
    },
    {
      "actor_id": "advisor_shearman_sterling",
      "display_name": "Shearman",
      "canonical_name": "SHEARMAN & STERLING LLP",
      "aliases": [
        "Shearman"
      ],
      "role": "advisor",
      "advisor_kind": "legal",
      "advised_actor_id": "bidder_wdc",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q008"
      ],
      "notes": [
        "Counsel to WDC."
      ]
    },
    {
      "actor_id": "activist_balch_hill",
      "display_name": "Balch Hill",
      "canonical_name": "BALCH HILL PARTNERS, L. P.",
      "aliases": [
        "Balch Hill"
      ],
      "role": "activist",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q009"
      ],
      "notes": []
    },
    {
      "actor_id": "activist_potomac",
      "display_name": "Potomac",
      "canonical_name": "POTOMAC CAPITAL PARTNERS II, L. P.",
      "aliases": [
        "Potomac"
      ],
      "role": "activist",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q010"
      ],
      "notes": []
    },
    {
      "actor_id": "advisor_company_a_financial_advisor",
      "display_name": "Company A financial advisor",
      "canonical_name": "COMPANY A FINANCIAL ADVISOR",
      "aliases": [
        "investment bank representing Company A"
      ],
      "role": "advisor",
      "advisor_kind": "financial",
      "advised_actor_id": "bidder_company_a",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q011"
      ],
      "notes": []
    },
    {
      "actor_id": "bidder_company_a",
      "display_name": "Company A",
      "canonical_name": "COMPANY A",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": "strategic",
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q012"
      ],
      "notes": []
    },
    {
      "actor_id": "bidder_company_b",
      "display_name": "Company B",
      "canonical_name": "COMPANY B",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": "strategic",
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q013"
      ],
      "notes": []
    },
    {
      "actor_id": "bidder_company_c",
      "display_name": "Company C",
      "canonical_name": "COMPANY C",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": "strategic",
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q014"
      ],
      "notes": [
        "Expressed interest in particular assets of sTec."
      ]
    },
    {
      "actor_id": "bidder_company_d",
      "display_name": "Company D",
      "canonical_name": "COMPANY D",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": "strategic",
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q015"
      ],
      "notes": []
    },
    {
      "actor_id": "bidder_company_e",
      "display_name": "Company E",
      "canonical_name": "COMPANY E",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": "strategic",
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q016"
      ],
      "notes": []
    },
    {
      "actor_id": "bidder_company_f",
      "display_name": "Company F",
      "canonical_name": "COMPANY F",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": "strategic",
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q017"
      ],
      "notes": []
    },
    {
      "actor_id": "bidder_company_g",
      "display_name": "Company G",
      "canonical_name": "COMPANY G",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": "strategic",
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q018"
      ],
      "notes": []
    },
    {
      "actor_id": "bidder_company_h",
      "display_name": "Company H",
      "canonical_name": "COMPANY H",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": "strategic",
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q019"
      ],
      "notes": []
    },
    {
      "actor_id": "bidder_wdc",
      "display_name": "WDC",
      "canonical_name": "WESTERN DIGITAL CORPORATION",
      "aliases": [
        "WDC"
      ],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": "strategic",
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q020",
        "Q021"
      ],
      "notes": []
    },
    {
      "actor_id": "bidder_financial_sponsor_1",
      "display_name": "Unnamed financial sponsor",
      "canonical_name": "UNNAMED FINANCIAL SPONSOR",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": "financial",
      "listing_status": null,
      "geography": null,
      "is_grouped": true,
      "group_size": 1,
      "group_label": "Unnamed financial sponsor",
      "quote_ids": [
        "Q022"
      ],
      "notes": []
    }
  ],
  "count_assertions": [
    {
      "subject": "investment banking firms identified by the board of directors",
      "count": 9,
      "quote_ids": [
        "Q023"
      ]
    },
    {
      "subject": "prospective acquirers contacted by BofA Merrill Lynch",
      "count": 18,
      "quote_ids": [
        "Q024"
      ]
    },
    {
      "subject": "technology company prospective acquirers",
      "count": 17,
      "quote_ids": [
        "Q025"
      ]
    },
    {
      "subject": "financial sponsor prospective acquirers",
      "count": 1,
      "quote_ids": [
        "Q022"
      ]
    },
    {
      "subject": "complete-purchase written indication submitters",
      "count": 3,
      "quote_ids": [
        "Q026"
      ]
    },
    {
      "subject": "strategic acquirers interested in limited, select assets",
      "count": 6,
      "quote_ids": [
        "Q027"
      ]
    },
    {
      "subject": "prospective acquirers not interested in a potential transaction",
      "count": 9,
      "quote_ids": [
        "Q028"
      ]
    },
    {
      "subject": "executed non-disclosure agreements related to exploration of a potential sale",
      "count": 6,
      "quote_ids": [
        "Q029"
      ]
    }
  ],
  "unresolved_mentions": []
}
</actor_roster>

<task_instructions>
IMPORTANT: You MUST follow the quote-before-extract protocol.

Step 1 - QUOTE: Read the chronology blocks above. For every passage that describes an M&A event, copy the exact verbatim text into the quotes array. Each quote needs a unique quote_id (Q001, Q002, ...), the block_id it comes from, and the verbatim text.

Step 2 - EXTRACT: Build the events array using the locked actor roster. Each event references quote_ids from Step 1 instead of inline evidence. Do not include anchor_text or evidence_refs.

Return a single JSON object with: quotes, events, exclusions, coverage_notes. The quotes array MUST appear first.
</task_instructions>