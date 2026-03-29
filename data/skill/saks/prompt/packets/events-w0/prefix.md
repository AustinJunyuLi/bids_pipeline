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