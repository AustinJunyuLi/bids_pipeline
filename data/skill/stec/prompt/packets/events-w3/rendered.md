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
  "actors": [
    {
      "actor_id": "target_board_stec",
      "display_name": "sTec Board of Directors / Special Committee",
      "canonical_name": "STEC BOARD OF DIRECTORS",
      "aliases": [
        "board of directors",
        "special committee",
        "independent directors"
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
      "evidence_span_ids": [
        "span_0001",
        "span_0003",
        "span_0009",
        "span_0020",
        "span_0021",
        "span_0083"
      ],
      "notes": [
        "Special committee initially composed of Dr. Daly, Messrs. Colpitts and Witte; expanded to four members with Mr. Bahri on March 26, 2013."
      ]
    },
    {
      "actor_id": "bidder_wdc",
      "display_name": "Western Digital Corporation",
      "canonical_name": "WESTERN DIGITAL CORPORATION",
      "aliases": [
        "WDC"
      ],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": "strategic",
      "listing_status": "public",
      "geography": "domestic",
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "evidence_span_ids": [
        "span_0005",
        "span_0006",
        "span_0044",
        "span_0047",
        "span_0054",
        "span_0059",
        "span_0061",
        "span_0066",
        "span_0067"
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
      "evidence_span_ids": [
        "span_0011",
        "span_0012",
        "span_0039",
        "span_0081"
      ],
      "notes": [
        "Described as a participant in the storage industry. Had an investment bank represent it. Cancelled meeting before process began. Indicated not interested during BofA outreach."
      ]
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
      "evidence_span_ids": [
        "span_0022",
        "span_0023",
        "span_0027",
        "span_0084"
      ],
      "notes": [
        "Described as a participant in the electronics industry. Determined it was not interested in acquiring sTec."
      ]
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
      "evidence_span_ids": [
        "span_0028",
        "span_0076"
      ],
      "notes": [
        "Described as a participant in the semiconductor industry. Only interested in limited, select assets."
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
      "evidence_span_ids": [
        "span_0030",
        "span_0037",
        "span_0041",
        "span_0049",
        "span_0056",
        "span_0057",
        "span_0058"
      ],
      "notes": [
        "Described as a participant in the storage industry. Submitted IOI at $5.75/share. Disengaged from process on June 5, 2013."
      ]
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
      "evidence_span_ids": [
        "span_0040",
        "span_0064",
        "span_0078"
      ],
      "notes": [
        "Described as a participant in the storage industry. Only interested in limited, select assets."
      ]
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
      "evidence_span_ids": [
        "span_0042",
        "span_0064",
        "span_0077"
      ],
      "notes": [
        "Described as another participant in the storage industry. Declined invitation to schedule management presentation. Only interested in select assets."
      ]
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
      "evidence_span_ids": [
        "span_0043",
        "span_0079"
      ],
      "notes": [
        "Described as a participant in the storage industry. Indicated it would not continue in the process on May 3, 2013."
      ]
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
      "evidence_span_ids": [
        "span_0037",
        "span_0046",
        "span_0050",
        "span_0051",
        "span_0065",
        "span_0080"
      ],
      "notes": [
        "Described as a participant in the storage industry. Submitted IOI at $5.00-$5.75/share. Could not increase its price."
      ]
    },
    {
      "actor_id": "activist_balch_hill",
      "display_name": "Balch Hill Partners, L.P.",
      "canonical_name": "BALCH HILL PARTNERS, L.P.",
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
      "evidence_span_ids": [
        "span_0015",
        "span_0016",
        "span_0018",
        "span_0019",
        "span_0074"
      ],
      "notes": [
        "Filed Schedule 13D on November 16, 2012. Started at 6.4%, later jointly held 9.8% with Potomac. Nominated three directors for 2013 annual meeting."
      ]
    },
    {
      "actor_id": "activist_potomac",
      "display_name": "Potomac Capital Partners II, L.P.",
      "canonical_name": "POTOMAC CAPITAL PARTNERS II, L.P.",
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
      "evidence_span_ids": [
        "span_0017",
        "span_0018",
        "span_0074"
      ],
      "notes": [
        "Joined Balch Hill in activist campaign. Jointly increased holdings to 9.8%."
      ]
    },
    {
      "actor_id": "advisor_bofa_merrill_lynch",
      "display_name": "BofA Merrill Lynch",
      "canonical_name": "BOFA MERRILL LYNCH",
      "aliases": [
        "Bank of America Merrill Lynch"
      ],
      "role": "advisor",
      "advisor_kind": "financial",
      "advised_actor_id": "target_board_stec",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "evidence_span_ids": [
        "span_0026",
        "span_0031",
        "span_0032",
        "span_0033",
        "span_0034",
        "span_0035",
        "span_0053",
        "span_0071",
        "span_0072"
      ],
      "notes": [
        "Engaged March 28, 2013. Fee approximately $4.3 million. Delivered fairness opinion June 23, 2013."
      ]
    },
    {
      "actor_id": "advisor_gibson_dunn",
      "display_name": "Gibson, Dunn & Crutcher LLP",
      "canonical_name": "GIBSON, DUNN & CRUTCHER LLP",
      "aliases": [
        "Gibson Dunn"
      ],
      "role": "advisor",
      "advisor_kind": "legal",
      "advised_actor_id": "target_board_stec",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "evidence_span_ids": [
        "span_0013",
        "span_0014",
        "span_0082"
      ],
      "notes": [
        "Engaged in October 2012 as outside corporate counsel."
      ]
    },
    {
      "actor_id": "advisor_latham_watkins",
      "display_name": "Latham & Watkins LLP",
      "canonical_name": "LATHAM & WATKINS LLP",
      "aliases": [
        "Latham & Watkins"
      ],
      "role": "advisor",
      "advisor_kind": "legal",
      "advised_actor_id": "target_board_stec",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "evidence_span_ids": [
        "span_0052"
      ],
      "notes": [
        "Described as litigation counsel to sTec and Mr. Manouch Moshayedi."
      ]
    },
    {
      "actor_id": "advisor_mackenzie_partners",
      "display_name": "MacKenzie Partners",
      "canonical_name": "MACKENZIE PARTNERS",
      "aliases": [],
      "role": "advisor",
      "advisor_kind": "financial",
      "advised_actor_id": "target_board_stec",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "evidence_span_ids": [
        "span_0029"
      ],
      "notes": [
        "Described as sTecs proxy solicitor."
      ]
    },
    {
      "actor_id": "advisor_shearman_sterling",
      "display_name": "Shearman & Sterling LLP",
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
      "evidence_span_ids": [
        "span_0063"
      ],
      "notes": [
        "Counsel to WDC."
      ]
    },
    {
      "actor_id": "advisor_paul_hastings",
      "display_name": "Paul Hastings LLP",
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
      "evidence_span_ids": [
        "span_0062"
      ],
      "notes": [
        "Counsel to Messrs. Moshayedi (personal counsel, not sTec)."
      ]
    },
    {
      "actor_id": "advisor_company_a_ib",
      "display_name": "Company A's Investment Bank",
      "canonical_name": "COMPANY A INVESTMENT BANK",
      "aliases": [],
      "role": "advisor",
      "advisor_kind": "financial",
      "advised_actor_id": "bidder_company_a",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "evidence_span_ids": [
        "span_0011"
      ],
      "notes": [
        "Unnamed investment bank that contacted sTec management on behalf of Company A on November 14, 2012."
      ]
    },
    {
      "actor_id": "grouped_prospective_acquirers_not_interested",
      "display_name": "Non-interested Prospective Acquirers",
      "canonical_name": "NON-INTERESTED PROSPECTIVE ACQUIRERS",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": "strategic",
      "listing_status": null,
      "geography": null,
      "is_grouped": true,
      "group_size": 9,
      "group_label": "nine prospective acquirers not interested",
      "evidence_span_ids": [
        "span_0039"
      ],
      "notes": [
        "Including the financial sponsor and Company A. Indicated they were not interested in a potential transaction."
      ]
    },
    {
      "actor_id": "grouped_asset_only_acquirers",
      "display_name": "Asset-Only Interested Acquirers",
      "canonical_name": "ASSET-ONLY INTERESTED ACQUIRERS",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": "strategic",
      "listing_status": null,
      "geography": null,
      "is_grouped": true,
      "group_size": 6,
      "group_label": "six potential strategic acquirers interested in limited assets",
      "evidence_span_ids": [
        "span_0038"
      ],
      "notes": [
        "Expressed interest only in purchasing limited, select assets of sTec."
      ]
    },
    {
      "actor_id": "grouped_financial_sponsor",
      "display_name": "Unnamed Financial Sponsor",
      "canonical_name": "UNNAMED FINANCIAL SPONSOR",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": "financial",
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "evidence_span_ids": [
        "span_0036",
        "span_0039"
      ],
      "notes": [
        "One of 18 prospective acquirers. Among the nine who indicated not interested."
      ]
    }
  ],
  "count_assertions": [
    {
      "subject": "prospective acquirers contacted by BofA Merrill Lynch",
      "count": 18,
      "evidence_span_ids": [
        "span_0035"
      ]
    },
    {
      "subject": "technology companies among prospective acquirers",
      "count": 17,
      "evidence_span_ids": [
        "span_0036"
      ]
    },
    {
      "subject": "financial sponsor among prospective acquirers",
      "count": 1,
      "evidence_span_ids": [
        "span_0036"
      ]
    },
    {
      "subject": "prospective acquirers submitting written IOIs for complete purchase",
      "count": 3,
      "evidence_span_ids": [
        "span_0037",
        "span_0073"
      ]
    },
    {
      "subject": "strategic acquirers interested in limited select assets",
      "count": 6,
      "evidence_span_ids": [
        "span_0038"
      ]
    },
    {
      "subject": "prospective acquirers not interested",
      "count": 9,
      "evidence_span_ids": [
        "span_0039"
      ]
    },
    {
      "subject": "non-disclosure agreements executed for potential sale",
      "count": 6,
      "evidence_span_ids": [
        "span_0045"
      ]
    },
    {
      "subject": "other potential buyers contacted",
      "count": 17,
      "evidence_span_ids": [
        "span_0069"
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