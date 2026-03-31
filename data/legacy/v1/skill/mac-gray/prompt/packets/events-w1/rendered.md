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
deal_slug: mac-gray
target_name: MAC GRAY CORP
source_accession_number: 0001047469-13-010973
source_form_type: UNKNOWN
chunk_mode: chunked
window_id: w1
</deal_context>

<chronology_blocks>
B077 [L1890-L1896]: Special Committee discussed that the preliminary indications of interest were lower than expected and suggested that additional due diligence, including with regard to the potential synergies, should result in improved offers by the strategic parties. The Special Committee then discussed the highly competitive nature of Mac-Gray's industry and expressed concern over permitting access to and the potential misuse of sensitive and competitive information, including customer terms and locations, especially by strategic bidders. Accordingly, the Special Committee concluded that it would be advisable to stage the disclosure of such information to each of the bidders to the extent that a bidder's indication of interest and other actions demonstrated its seriousness in acquiring Mac-Gray on terms viewed favorably by the Special Committee. Based on this discussion, BofA Merrill Lynch discussed with the Special Committee a proposed process for the second stage of the on-going sale process. As part of this review, BofA Merrill Lynch recommended that management meetings be arranged between members of Mac-Gray management (other than Mr. MacDonald) and each of Party A (if Party A
B078 [L1898-L1898]: 33
B079 [L1901-L1905]: agreed to enter into a confidentiality agreement), Party B, Party C and CSC/Pamplona to provide these parties with access to high level information concerning Mac-Gray's technology, pipeline, management team, regional operations, contracts, operations and growth initiatives, and in the case of CSC/Pamplona and Party A, synergies, and to then request that each of these parties submit a revised indication of interest. After discussion and in an effort to drive offers with increased value, the Special Committee authorized and instructed BofA Merrill Lynch to proceed with the staged disclosure as discussed at this meeting and to reach out to each of the four interested bidders and arrange management meetings.
B080 [L1907-L1907]: Later
B081 [L1908-L1908]: on July 25, 2013, Party C submitted a written indication of interest at an all-cash purchase price of $16.00 to $16.50 per share.
B082 [L1910-L1910]: Discussions
B083 [L1911-L1913]: with Party A resumed on July 27, 2103 and Party A and the Transaction Committee agreed to the terms of the customer and employee non-solicitation provisions. On August 5, 2013, Party A entered into a confidentiality and standstill agreement with Mac-Gray and was provided with an informational package for the purpose of providing Party A with data to potentially improve the terms of the Party A June 21 proposal.
B084 [L1915-L1915]: On
B085 [L1916-L1917]: August 6, 2013, representatives of Party B attended a management presentation at the Boston office of Goodwin Procter with members of Mac-Gray management, representatives of BofA Merrill Lynch and a member of the Transaction Committee.
B086 [L1919-L1919]: On
B087 [L1920-L1921]: August 8, 2013, representatives of Party C attended a management presentation at the Boston office of Goodwin Procter with members of Mac-Gray management, representatives of BofA Merrill Lynch and a member of the Transaction Committee.
B088 [L1923-L1923]: On
B089 [L1924-L1925]: August 12, 2013, representatives of CSC and Pamplona attended a management presentation at the Boston office of Goodwin Procter with members of Mac-Gray management, representatives of BofA Merrill Lynch and the two members of the Transaction Committee.
B090 [L1927-L1927]: On
B091 [L1928-L1929]: August 14, 2013, representatives of Party A attended a management presentation at the Boston office of Goodwin Procter with members of Mac-Gray management, representatives of BofA Merrill Lynch and the two members of the Transaction Committee.
B092 [L1931-L1931]: On
B093 [L1932-L1935]: August 15, 2013, the Special Committee held a telephonic meeting for the purpose of reviewing the on-going strategic alternatives process. By invitation of the Special Committee, representatives from BofA Merrill Lynch and Goodwin Procter were also in attendance. BofA Merrill Lynch updated the Special Committee as to the current status of the strategic alternatives process, including the due diligence process and the management presentations with Party A, Party B, Party C and CSC/Pamplona. After discussion and as discussed at the July 25 th
B094 [L1937-L1937]: Between
B095 [L1938-L1941]: August 6, 2013 and August 27, 2013, the four bidders conducted business and legal due diligence. During this time, Party B and Party C, in light of the fact that they were financial bidders, were given broad access to an electronic data site, and Party A and CSC/Pamplona, in light of the fact that they were strategic bidders, were given somewhat limited access to this electronic data site, with access to customer data, including customer locations, being reserved until later in the process as part of the staging discussed at the July 25 th
B096 [L1943-L1943]: 34
B097 [L1946-L1946]: On
B098 [L1947-L1950]: August 27, 2013, BofA Merrill Lynch, as instructed by the Special Committee, sent a letter to each of Party A, Party B, Party C and CSC/Pamplona instructing such bidders to submit revised written proposals no later than September 9, 2013 if such bidders wished to proceed further in the process to pursue an in-depth evaluation of Mac-Gray with the objective of making a revised offer. The letter requested that the revised proposals address, among other things, valuation, sources and structures of financing, regulatory approvals and other post-signing covenants and focus areas for due diligence.
B099 [L1952-L1952]: Also
B100 [L1953-L1954]: on August 27, 2013, members of Mac-Gray management, representatives from BofA Merrill Lynch and representatives of Party B participated in a telephone conference call for Party B to conduct follow-up and confirmatory due diligence.
B101 [L1956-L1956]: On
B102 [L1957-L1958]: August 29, 2013, members of Mac-Gray management, representatives from BofA Merrill Lynch and representatives of Party C participated in an in-person session for Party C to conduct follow-up and confirmatory due diligence.
B103 [L1960-L1960]: On
B104 [L1961-L1962]: September 3, 2013, members of Mac-Gray management, representatives from BofA Merrill Lynch and representatives of Party A participated in a telephone conference call for Party A to conduct follow-up and confirmatory due diligence.
B105 [L1964-L1964]: On
B106 [L1965-L1968]: September 9, 2013, CSC/Pamplona submitted a revised indication of interest with an all-cash purchase price of $19.50 per share, indicating that Pamplona was committed to provide 100% of the capital required to consummate the transaction and requesting that CSC/Pamplona and Mac-Gray agree to exclusive negotiations for two weeks. On September 9, 2013, Party B also submitted a revised indication of interest with an all-cash purchase price of $18.50 per share and proposed to finance the transaction with a combination of equity from affiliated funds and third party debt. Party B's revised indication of interest did not include a firm financing commitment.
B107 [L1970-L1970]: On
B108 [L1971-L1974]: September 10, 2013, Party A submitted a revised indication of interest with an all-cash purchase price of $18.00 to $19.00 per share, to be financed by outstanding credit facilities or affiliated equity sources. Also on September 10, 2013, in a telephone call to a representative of BofA Merrill Lynch, a representative of Party C indicated that it was submitting a revised oral indication of interest with an all-cash purchase price of $16.00 to $17.00 per share. Neither Party A's nor Party C's revised indication of interest included a firm financing commitment.
B109 [L1976-L1976]: On
B110 [L1977-L1980]: September 11, 2013, members of the Transaction Committee, in a telephone call, without identifying Party A, Party B, Party C or CSC/Pamplona and without indicating any proposed purchase prices, provided Mr. MacDonald with a limited overview of the status of the Special Committee's review of strategic alternatives, including the decision to engage in strategic alternatives process, and the negotiations between Mac-Gray and CSC/Pamplona so that Mr. MacDonald could consider whether he continued to have an interest in potentially rolling over any of his Mac-Gray shares in a transaction. During this call, Mr. MacDonald indicated that he had decided that he was not interested in rolling over any of his shares in any transaction.
B111 [L1982-L1982]: Later
B112 [L1983-L1988]: on September 11, 2013, the Special Committee held a telephonic meeting to review the revised indications of interest submitted by Party A, Party B, Party C and CSC/Pamplona. By invitation of the Special Committee, Mr. Shea and Mr. Emma, as well as representatives from BofA Merrill Lynch and Goodwin Procter, were present for all or portions of the meeting. BofA Merrill Lynch reviewed with the Special Committee the current status of the revised indications of interest. The Special Committee also reviewed and discussed the Projections, including the risks and opportunities relating to Mac-Gray's ability to execute its strategic plan as an independent, stand-alone company. The Special Committee also considered the Projections in light of the revised indications of interest. BofA Merrill Lynch then indicated that, based on conversations with Party A, Party B, Party C and CSC/Pamplona, it was unlikely that any of these parties would move forward in the process without the express support of Mr. MacDonald. The Transaction Committee reported that Mr. MacDonald had
B113 [L1990-L1990]: 35
B114 [L1993-L2000]: decided that he was not interested in rolling over any of his shares in a transaction and recommended that Mr. MacDonald be fully briefed of the process to date. The Special Committee agreed, noting that Mr. MacDonald's perspective on the purchase price of a sale transaction was critical to the Special Committee's evaluation, as any potential acquiror would be unlikely to proceed without knowing that Mr. MacDonald would support the transaction. Based on the amount of due diligence conducted by Party A, Party B, Party C and CSC/Pamplona, and discussions with such parties to date, and in an effort to maximize value for Mac-Gray's stockholders, the Special Committee instructed BofA Merrill Lynch to call each of Party A, Party B, Party C and CSC/Pamplona to request final indications of interest by September 18, 2013 and to indicate that Mac-Gray would consider engaging in a short period of exclusive negotiations with one of the bidders depending upon, among other things, the proposed purchase price and the level of deal certainty indicated in the bidder's final proposal. As authorized and instructed by the Special Committee, representatives of BofA Merrill Lynch called each of Party A, Party B, Party C and CSC/Pamplona on September 11, 2013 with such instructions.
B115 [L2002-L2002]: On
B116 [L2003-L2005]: September 12, 2013, at the instruction of the Transaction Committee, representatives of BofA Merrill Lynch participated in a telephone conference call with Mr. MacDonald and provided him with a detailed overview of the strategic alternatives process, including the status of negotiations with and the identity of Party A, Party B, Party C and CSC/Pamplona. Although Mr. MacDonald voiced his general support for continuing with the process, he expressed his view that Mac-Gray should continue to seek a higher value for stockholders.
B117 [L2007-L2007]: Between
B118 [L2008-L2008]: September 11, 2013 and September 18, 2013, Party A, Party B, Party C and CSC/Pamplona continued to conduct business and legal due diligence.
B119 [L2010-L2010]: On
B120 [L2011-L2018]: September 18, 2013, CSC/Pamplona submitted a proposal for an all-cash purchase price of $20.75 per share, reiterating that Pamplona was committed to provide 100% of the capital required to consummate the transaction and requesting that CSC/Pamplona and Mac-Gray agree to engage in exclusive negotiations for two weeks. Also on September 18, 2013, Party A reiterated in a telephone call to a representative of BofA Merrill Lynch that its previous indication of interest with an all-cash purchase price of $18.00 to $19.00 per share was its best and final offer. On September 18, 2013, Party B also submitted a revised indication of interest with a purchase price that Party B valued at $21.50 per share, including $19.00 of cash to be paid at closing and the remaining per share price to be paid in the form of options to be issued to Mac-Gray stockholders, representing 10% of the new equity with a strike price equal to Party B's initial cost basis. These options, which we refer to as the Party B options, would vest on the achievement of the base case management projections (i. e., over five years), excluding any future acquisitions. Party B's proposal stated that it valued the Party B options at $2.50 of incremental value per share. Party C did not submit a revised indication of interest or reiterate its prior indication of interest of an all-cash purchase price of $16.00 to $17.00 per share nor did it specify any reasons in connection therewith.
B121 [L2020-L2020]: On
B122 [L2021-L2027]: September 19, 2013, the Special Committee held an in-person meeting. By invitation of the Special Committee, Mr. MacDonald and Mr. Shea, as well as representatives from BofA Merrill Lynch and Goodwin Procter, were also present for all or portions of the meeting. At this meeting, BofA Merrill Lynch updated the Special Committee as to the current status of the revised indications of interest submitted by Party A, Party B and CSC/Pamplona and reported that Party C did not submit a revised indication of interest or reiterate its prior indication of interest. BofA Merrill Lynch also reported to the Special Committee on Mr. MacDonald's general support for continuing with the process and his view that Mac-Gray should continue to seek a higher value for stockholders. Mr. Shea again reviewed the Projections with the Special Committee and BofA Merrill Lynch. The Special Committee again discussed the Projections, including the risks relating to Mac-Gray's ability to execute its strategic plan as an independent, stand-alone company (including Mac-Gray's ability to identify, acquire and successfully integrate laundry facilities management businesses, establish new and/or renew existing laundry facility management leases and penetrate markets historically dominated by smaller
B123 [L2029-L2029]: 36
B124 [L2032-L2041]: local and regional operators, the impact of general economic and market trends on Mac-Gray's sales and the general risks of market conditions that could reduce Mac-Gray's stock price). The Special Committee also again discussed the potential opportunities if Mac-Gray were able to execute its strategic plan as an independent, stand-alone company (including the ability to improve profitability and EBITDA margins by increasing scale and density through organic growth and/or strategic acquisitions as well as the ability to increase revenue through vend increases and the conversion from coin-operated technology to card-based technology). The Special Committee also discussed the risks involved if Mac-Gray did not execute on its strategic business plan, including the difficulties with increasing the Company's stock price without a significant or transformative transaction, such as a major acquisition or restructuring. The Special Committee then considered the Projections in light of the revised indications of interest. Representatives from Goodwin Procter again reviewed the Special Committee's fiduciary duties in the context of a sale of the company. The Special Committee then discussed each of the three revised proposals, including their advantages and disadvantages. The Special Committee discussed the risks and complexities of the Party B options, including their contingent and deferred nature and the uncertainties associated with how Mac-Gray's performance would be measured, especially in light of the fact that current Mac-Gray management would not be in control of the surviving corporation to monitor or drive the growth necessary to trigger payment under the Party B options.
B125 [L2043-L2043]: The
B126 [L2044-L2052]: representatives from BofA Merrill Lynch were then excused from the meeting and the Special Committee continued its discussion. The Special Committee noted that the indication of interest submitted by Party B, including the Party B options, was on its face higher than the CSC/Pamplona proposal but further discussed the risks and complexities involved with measuring and achieving the performance required to vest the Party B options. The Special Committee also noted that Party B would likely be financing the transaction with a combination of equity from affiliated funds and third party debt capital, which would involve more risk than the Pamplona-funded CSC/Pamplona proposal, which did not require any third party financing. Following a discussion, the Special Committee concluded that the revised indication of interest submitted by CSC/Pamplona had the potential of delivering the most value to stockholders, provided greater certainty and involved less potential risk than the other indications. However, the Special Committee also concluded that, primarily in view of potential synergies between Mac-Gray and CSC, CSC/Pamplona should be in a position to increase their offer price above $20.75. The Special Committee then authorized the Transaction Committee to inform CSC/Pamplona that the Special Committee would be prepared to move into exclusivity at a price of $21.25 per share and authorized the Transaction Committee and Goodwin Procter to negotiate the terms of such exclusivity based on guidance provided by the Special Committee. In addition, at this meeting Mr. MacDonald indicated that he would be supportive of a price of $21.25 per share.
B127 [L2054-L2054]: On
B128 [L2055-L2059]: September 21, 2013, the members of the Transaction Committee called the representative of CSC/Pamplona to propose that Mac-Gray was prepared to move forward with CSC/Pamplona on an exclusive basis for two weeks subject to CSC/Pamplona increasing their all-cash purchase price to $21.25 per share. Later that same day, the representative of CSC/Pamplona called the members of the Transaction Committee to confirm that CSC/Pamplona were willing to increase their all-cash purchase price to $21.25 per share as a last and best offer, provided that Mac-Gray agree to a two week period of exclusive negotiations. The representative of CSC/Pamplona also requested that shares of Mac-Gray common stock owned beneficially and of record by Mr. MacDonald and his immediate family be subject to a customary voting agreement, which we refer to as the MacDonald voting agreements.
B129 [L2061-L2061]: Between
B130 [L2062-L2064]: September 21, 2013 and September 23, 2013, the parties negotiated the terms of the exclusivity agreement, including an expiration date of October 12, 2013, the inclusion of a $15 million "reverse" termination fee payable by CSC/Pamplona to Mac-Gray in the event regulatory clearance is not obtained, which we refer to as the CSC reverse termination fee, agreements regarding certain post-signing covenants, the fact that there would be no financing contingency and that Pamplona was
B131 [L2066-L2066]: 37
B132 [L2069-L2071]: committing to fund 100% of the capital needed for closing, which, together with the all-cash per share purchase price of $21.25, we refer to as the CSC/Pamplona final proposal. The parties also agreed that the exclusivity agreement would automatically terminate if CSC or Pamplona adversely changed any of the terms of the CSC/Pamplona final proposal.
B133 [L2073-L2073]: On
B134 [L2074-L2077]: September 23, 2013, representatives from Goodwin Procter participated in a telephone conference call with Mr. Rothenberg and his counsel to inform Mr. Rothenberg, on a limited basis, of the status of the Special Committee's review of strategic alternatives and the negotiations between Mac-Gray and CSC and Pamplona to provide Moab with the opportunity to resume discussions with CSC/Pamplona regarding a possible equity rollover of Moab's shares in the transaction if Moab still had an interest in such a rollover. Mr. Rothenberg indicated he would like to discuss the possibility of an equity rollover with CSC/Pamplona and it was agreed that representatives of BofA Merrill Lynch would arrange and facilitate such a discussion.
B135 [L2079-L2079]: Later
B136 [L2080-L2085]: on September 23, 2013, the Special Committee held a telephonic meeting, the purpose of which was to receive an update on the negotiations from the Transaction Committee and Goodwin Procter regarding the CSC/Pamplona final proposal and request for exclusivity. Representatives from Goodwin Procter reviewed the terms of the CSC/Pamplona final proposal with the Special Committee, including the $21.25 per share cash consideration, the $15 million CSC reverse termination fee, certain post-signing covenants, the fact that there would be no financing contingency and that Pamplona was committing to fund 100% of the capital needed for closing. After discussion, the Special Committee authorized Mac-Gray to enter into an exclusivity agreement providing for exclusive negotiations until 5 p. m. ET on October 12, 2013 on the terms included in the CSC/Pamplona final proposal and authorized the Transaction Committee and Goodwin Procter to continue negotiations with CSC/Pamplona based on guidance provided by the Special Committee at this meeting.
B137 [L2087-L2087]: On
B138 [L2088-L2089]: September 24, 2013, CSC, Pamplona and Mac-Gray executed the exclusivity agreement providing for exclusive negotiations until 5 p. m. ET on October 12, 2013, subject to certain conditions, including that CSC and Pamplona not adversely change or modify the terms of the CSC/Pamplona final proposal.
B139 [L2091-L2091]: On
B140 [L2092-L2102]: September 25, 2013, Goodwin Procter delivered to Kirkland & Ellis LLP, outside legal counsel to CSC/Pamplona, whom we refer to as Kirkland, the initial draft of the merger agreement. Between September 25, 2013 and October 7, 2013, the Transaction Committee and representatives from CSC/Pamplona, Goodwin Procter and Kirkland negotiated the terms of the merger agreement (including our ability to respond to unsolicited inquiries following the announcement of the transaction and our right to terminate the merger agreement to accept a superior proposal) and the Pamplona commitment letter. The parties discussed various open points in the merger agreement and the Pamplona commitment letter, including the proposal by Mac-Gray that both Pamplona and CSC be responsible in the event CSC failed to consummate the merger, including liability for any and all damages resulting from a breach of the merger agreement, certain post-signing covenants and the parties' termination rights, including the amount of the termination fee payable by Mac-Gray to CSC under certain circumstances (which we refer to as the Mac-Gray termination fee), which Mac-Gray proposed should approximate 2.5% of the total equity value of the transaction. Also during this time, CSC and Pamplona were granted full access to the electronic data site and access to certain members of management and conducted confirmatory business and legal due diligence on Mac-Gray. Mr. Rothenberg engaged in various discussions with representatives of Pamplona during this time to discuss a possible rollover of Moab shares. As a result of such discussions, it was determined that Moab would not rollover any Moab shares in the transaction. Following such determination, BofA Merrill Lynch and the Transaction Committee provided Mr. Rothenberg with the details regarding the Special Committee's review of strategic alternatives and the negotiations between Mac-Gray and CSC/Pamplona.
B141 [L2104-L2104]: 38
B142 [L2107-L2107]: Between
B143 [L2108-L2109]: September 24, 2013 and September 27, 2013, Kirkland and outside counsel to Mr. MacDonald negotiated the terms of the MacDonald voting agreements, which were entered into by Mr. MacDonald, his wife and one of his trusts on September 27, 2013, and which became effective upon entry into the merger agreement.
B144 [L2111-L2111]: On
B145 [L2112-L2114]: October 1, 2013, representatives of Mac-Gray management, along with representatives from BofA Merrill Lynch and representatives from CSC/Pamplona attended a meeting at the Boston offices of Goodwin Procter for purposes of conducting confirmatory business due diligence. Representatives of Mac-Gray, Goodwin Procter, BofA Merrill Lynch and representatives of CSC/Pamplona and Kirkland participated in various telephone conference calls over the subsequent days to finalize business and legal due diligence.
B146 [L2116-L2116]: On
B147 [L2117-L2119]: October 5, 2013, Kirkland delivered to Goodwin Procter a revised draft of the Pamplona commitment letter which, among other things, proposed that, in addition to CSC, Pamplona would be responsible in the event CSC failed to consummate the merger, but that Pamplona's liability for damages resulting from a breach of the merger agreement would be limited to an unspecified dollar amount.
B148 [L2121-L2121]: On
B149 [L2122-L2125]: October 7, 2013, the Special Committee held a telephonic meeting, the purpose of which was to receive an update on the transaction negotiations from the Transaction Committee and Goodwin Procter. By invitation of the Special Committee, Mr. MacDonald was also present for a portion of the meeting. Mr. Daoust reported to the Special Committee that, after discussions between Moab and representatives of Pamplona, it was determined that Moab would not rollover any Moab shares in the transaction. Mr. Daoust also provided the Special Committee with an overview of the open business points and the progress the parties had made since the September 23 rd
B150 [L2127-L2127]: Also
B151 [L2128-L2129]: on October 7, 2013, Kirkland delivered to Goodwin Procter a revised draft of the merger agreement which, among other things, proposed a $15 million Mac-Gray termination fee, which represented approximately 4.4% of the total equity value of the transaction, and certain positions on the scope of various post-signing covenants.
B152 [L2131-L2131]: On
B153 [L2132-L2137]: October 8, 2013, representatives from Goodwin Procter and Kirkland participated in a telephone conference call to discuss the open points in the merger agreement and the Pamplona commitment letter, including to what extent Pamplona would also have liability in the event CSC failed to consummate the merger, which Kirkland proposed, at the direction of CSC/Pamplona, be capped at $50 million. Kirkland and Goodwin Procter also discussed CSC's and Pamplona's liability for damages resulting from a breach of the merger agreement, certain post-signing covenants and the parties' termination rights, including the amounts of the Mac-Gray termination fee and the CSC reverse termination fee. The parties also discussed potential compromises on the post-signing covenants. Goodwin Procter and Kirkland agreed to communicate these positions to their respective clients. Later that day, after various discussions among representatives from CSC/Pamplona, Kirkland, Goodwin Procter and the members of the Transaction Committee, and on behalf of the Special Committee, Goodwin Procter sent an e-mail to the representatives of Kirkland that proposed to accept the
B154 [L2139-L2139]: 39
B155 [L2142-L2143]: $50 million liability cap proposed by Pamplona and proposed a $10.5 million Mac-Gray termination fee, which represented approximately 3.0% of the total equity value of the transaction.
B156 [L2145-L2145]: On
B157 [L2146-L2148]: October 9, 2013, in follow up to the October 8, 2013 negotiations and proposals made by Goodwin Procter, the members of the Transaction Committee participated in a telephone conference call with a representative from CSC/Pamplona to discuss the open issues in the merger agreement, including certain post-signing covenants and the parties' termination rights, including the amounts of the Mac-Gray termination fee and the CSC reverse termination fee, but did not reach agreement on these issues.
B158 [L2150-L2150]: Later
B159 [L2151-L2158]: on October 9, 2013, the Special Committee held a telephonic meeting, the purpose of which was to receive an update on the transaction negotiations from the Transaction Committee and Goodwin Procter. By invitation of the Special Committee, Mr. MacDonald was also present at this meeting. The Transaction Committee reported to the Special Committee on the negotiations that had taken place since the meeting of the Special Committee held on October 7, 2013. The Transaction Committee reported that the parties had come to an agreement that Pamplona's liability for certain damages would be limited to $50 million, but that certain post-signing covenants and the amounts of the termination fees remained open issues. The Special Committee discussed various alternatives that could be proposed to CSC/Pamplona on the open issues. Goodwin Procter then reported that Kirkland had requested on behalf of CSC/Pamplona that the exclusivity agreement, due to expire at 5 p. m. ET on October 12, 2013, be extended to allow for continued negotiations of these open issues. After discussion, the Special Committee authorized the Transaction Committee to negotiate the open issues within certain parameters and in connection therewith to extend exclusivity to October 15, 2013. The Special Committee also determined to reconvene for an update telephone conference call on October 11, 2013.
B160 [L2160-L2160]: On
</chronology_blocks>

<overlap_context>
B075 [L1880-L1887]: July 25, 2013, the Board held a regularly scheduled in-person meeting. By invitation of the Board, Mr. Shea and representatives from BofA Merrill Lynch and Goodwin Procter were also present for all or portions of this meeting. Prior to the start of the meeting, because the Board expected to discuss matters related to the sale process, and in light of Moab's continuing interest in a potential equity rollover in any sale transaction, Mr. Rothenberg recused himself from the meeting and the meeting proceeded as a meeting of the Special Committee. At this meeting, representatives of BofA Merrill Lynch reviewed the preliminary indications of interest received from Party B, Party C and CSC/Pamplona as well as the Party A June 21 proposal, in each case from a financial point of view. The Board reviewed management's five-year strategic business plan and Projections. During this meeting, representatives of Goodwin Procter reviewed for the Special Committee its fiduciary duties in the context of considering a potential sale. The Special Committee then discussed the potential conflict of interest arising from Moab's continuing desire to consider an equity rollover and decided that Mr. Rothenberg should be asked to recuse himself from participating in Board meetings for the duration of the sale process so he would not be privy to confidential information about Mac-Gray and our business.
B076 [L1889-L1889]: The
B161 [L2161-L2165]: October 10, 2013, the members of the Transaction Committee and the representative of CSC/Pamplona engaged in various discussions regarding the open issues, including certain post-signing covenants and the amounts of the termination fees. While the parties reached a compromise on the post-signing covenants, no agreement was reached on the amount of the Mac-Gray termination fee. On October 11, 2013, the Special Committee held a telephonic meeting to discuss the proposed terms of the transaction and the status of discussions with CSC/Pamplona. By invitation of the Special Committee, Mr. Rothenberg and representatives of Goodwin Procter were also present. The members of the Transaction Committee reviewed with the Special Committee the negotiations that had taken place with representatives from CSC/Pamplona since the October 9 th th
B162 [L2167-L2167]: Later
</overlap_context>

<evidence_checklist>
### Dated actions to extract
- [ ] **0001047469-13-010973:E0438** L1879-L1887 (date: July 25, 2013; actor: Party B; terms: discussed, meeting, proposal)
- [ ] **0001047469-13-010973:E0444** L1907-L1908 (date: July 25, 2013; actor: Party C; value: $16.00 to $16.50 per share; terms: submitted)
- [ ] **0001047469-13-010973:E0447** L1910-L1913 (date: July 27, 2103; actor: Party A; terms: entered into, proposal)
- [ ] **0001047469-13-010973:E0450** L1915-L1917 (date: August 6, 2013; actor: Party B; terms: sent)
- [ ] **0001047469-13-010973:E0453** L1919-L1921 (date: August 8, 2013; actor: Party C; terms: sent)
- [ ] **0001047469-13-010973:E0456** L1923-L1925 (date: August 12, 2013; actor: Transaction Committee; terms: sent)
- [ ] **0001047469-13-010973:E0459** L1927-L1929 (date: August 14, 2013; actor: Party A; terms: sent)
- [ ] **0001047469-13-010973:E0462** L1931-L1935 (date: August 15, 2013; actor: Party A; terms: discussed, meeting, sent)
- [ ] **0001047469-13-010973:E0465** L1937-L1941 (date: August 6, 2013; actor: Party B; terms: discussed)
- [ ] **0001047469-13-010973:E0468** L1946-L1950 (date: August 27, 2013; actor: Party A; terms: offer, proposal, requested)
- [ ] **0001047469-13-010973:E0471** L1952-L1954 (date: August 27, 2013; actor: Party B; terms: sent)
- [ ] **0001047469-13-010973:E0474** L1956-L1958 (date: August 29, 2013; actor: Party C; terms: sent)
- [ ] **0001047469-13-010973:E0477** L1960-L1962 (date: September 3, 2013; actor: Party A; terms: sent)
- [ ] **0001047469-13-010973:E0480** L1964-L1968 (date: September 9, 2013; actor: Party B; value: $19.50 per share; terms: proposed, submitted)
- [ ] **0001047469-13-010973:E0483** L1970-L1974 (date: September 10, 2013; actor: Party A; value: $18.00 to $19.00 per share; terms: sent, submitted)
- [ ] **0001047469-13-010973:E0486** L1976-L1980 (date: September 11, 2013; actor: Party A; terms: proposed)
- [ ] **0001047469-13-010973:E0489** L1982-L1988 (date: September 11, 2013; actor: Party A; terms: discussed, meeting, sent)
- [ ] **0001047469-13-010973:E0491** L1993-L2000 (date: September 18, 2013; actor: Party A; terms: authorized, called, proposal)
- [ ] **0001047469-13-010973:E0494** L2002-L2005 (date: September 12, 2013; actor: Party A; terms: sent)
- [ ] **0001047469-13-010973:E0499** L2010-L2018 (date: September 18, 2013; actor: Party A; value: $20.75 per share; terms: offer, proposal, sent)
- [ ] **0001047469-13-010973:E0504** L2020-L2027 (date: September 19, 2013; actor: Party A; terms: discussed, meeting, sent)
- [ ] **0001047469-13-010973:E0510** L2054-L2059 (date: September 21, 2013; actor: Transaction Committee; value: $21.25 per share; terms: called, offer, requested)
- [ ] **0001047469-13-010973:E0519** L2073-L2077 (date: September 23, 2013; actor: Special Committee; terms: sent)
- [ ] **0001047469-13-010973:E0522** L2079-L2085 (date: September 23, 2013; actor: Special Committee; value: $21.25 per share; terms: authorized, meeting, proposal)
- [ ] **0001047469-13-010973:E0527** L2087-L2089 (date: September 24, 2013; terms: executed, proposal)
- [ ] **0001047469-13-010973:E0530** L2091-L2102 (date: September 25, 2013; actor: Transaction Committee; terms: delivered, discussed, engaged)
- [ ] **0001047469-13-010973:E0534** L2107-L2109 (date: September 24, 2013; terms: entered into)
- [ ] **0001047469-13-010973:E0537** L2111-L2114 (date: October 1, 2013; actor: Merrill Lynch; terms: meeting, sent)
- [ ] **0001047469-13-010973:E0540** L2116-L2119 (date: October 5, 2013; terms: delivered, proposed)
- [ ] **0001047469-13-010973:E0542** L2121-L2125 (date: October 7, 2013; actor: Special Committee; terms: meeting, sent)
- [ ] **0001047469-13-010973:E0544** L2127-L2129 (date: October 7, 2013; value: $15; terms: delivered, proposed, sent)
- [ ] **0001047469-13-010973:E0547** L2131-L2137 (date: October 8, 2013; actor: Transaction Committee; value: $50; terms: discussed, proposed, sent)
- [ ] **0001047469-13-010973:E0553** L2145-L2148 (date: October 9, 2013; actor: Transaction Committee; terms: proposal, sent)
- [ ] **0001047469-13-010973:E0556** L2150-L2158 (date: October 9, 2013; actor: Special Committee; value: $50; terms: authorized, discussed, meeting)
- [ ] **0001047469-13-010973:E0561** L2160-L2165 (date: October 10, 2013; actor: Transaction Committee; terms: engaged, meeting, proposed)
- [ ] **0001047469-13-010973:E0564** L2167-L2169 (date: October 11, 2013; actor: Transaction Committee; value: $11; terms: sent)

### Financial terms to capture
- [ ] **0001047469-13-010973:E0445** L1907-L1908 (date: July 25, 2013; actor: Party C; value: $16.00 to $16.50 per share; terms: $16.00 to $16.50 per share)
- [ ] **0001047469-13-010973:E0481** L1964-L1968 (date: September 9, 2013; actor: Party B; value: $19.50 per share; terms: $18.50 per share, $19.50 per share)
- [ ] **0001047469-13-010973:E0484** L1970-L1974 (date: September 10, 2013; actor: Party A; value: $18.00 to $19.00 per share; terms: $16.00 to $17.00 per share, $18.00 to $19.00 per share)
- [ ] **0001047469-13-010973:E0500** L2010-L2018 (date: September 18, 2013; actor: Party A; value: $20.75 per share; terms: $16.00 to $17.00 per share, $18.00 to $19.00 per share, $19.00)
- [ ] **0001047469-13-010973:E0507** L2043-L2052 (actor: Party B; value: $20.75; terms: $20.75, $21.25 per share)
- [ ] **0001047469-13-010973:E0511** L2054-L2059 (date: September 21, 2013; actor: Transaction Committee; value: $21.25 per share; terms: $21.25 per share)
- [ ] **0001047469-13-010973:E0513** L2061-L2064 (date: September 21, 2013; value: $15; terms: $15)
- [ ] **0001047469-13-010973:E0516** L2069-L2071 (value: $21.25; terms: $21.25)
- [ ] **0001047469-13-010973:E0523** L2079-L2085 (date: September 23, 2013; actor: Special Committee; value: $21.25 per share; terms: $15, $21.25 per share)
- [ ] **0001047469-13-010973:E0545** L2127-L2129 (date: October 7, 2013; value: $15; terms: $15)
- [ ] **0001047469-13-010973:E0548** L2131-L2137 (date: October 8, 2013; actor: Transaction Committee; value: $50; terms: $50)
- [ ] **0001047469-13-010973:E0551** L2142-L2143 (value: $50; terms: $10.5, $50)
- [ ] **0001047469-13-010973:E0557** L2150-L2158 (date: October 9, 2013; actor: Special Committee; value: $50; terms: $50)
- [ ] **0001047469-13-010973:E0565** L2167-L2169 (date: October 11, 2013; actor: Transaction Committee; value: $11; terms: $11)

### Actors to identify
- [ ] **0001047469-13-010973:E0439** L1879-L1887 (date: July 25, 2013; actor: Party B; terms: party , special committee)
- [ ] **0001047469-13-010973:E0440** L1889-L1896 (actor: Party A; terms: party , special committee)
- [ ] **0001047469-13-010973:E0442** L1901-L1905 (actor: Party B; terms: party , special committee)
- [ ] **0001047469-13-010973:E0446** L1907-L1908 (date: July 25, 2013; actor: Party C; value: $16.00 to $16.50 per share; terms: party )
- [ ] **0001047469-13-010973:E0448** L1910-L1913 (date: July 27, 2103; actor: Party A; terms: party , transaction committee)
- [ ] **0001047469-13-010973:E0451** L1915-L1917 (date: August 6, 2013; actor: Party B; terms: party , transaction committee)
- [ ] **0001047469-13-010973:E0454** L1919-L1921 (date: August 8, 2013; actor: Party C; terms: party , transaction committee)
- [ ] **0001047469-13-010973:E0457** L1923-L1925 (date: August 12, 2013; actor: Transaction Committee; terms: transaction committee)
- [ ] **0001047469-13-010973:E0460** L1927-L1929 (date: August 14, 2013; actor: Party A; terms: party , transaction committee)
- [ ] **0001047469-13-010973:E0463** L1931-L1935 (date: August 15, 2013; actor: Party A; terms: party , special committee)
- [ ] **0001047469-13-010973:E0466** L1937-L1941 (date: August 6, 2013; actor: Party B; terms: party )
- [ ] **0001047469-13-010973:E0469** L1946-L1950 (date: August 27, 2013; actor: Party A; terms: party , special committee)
- [ ] **0001047469-13-010973:E0472** L1952-L1954 (date: August 27, 2013; actor: Party B; terms: party )
- [ ] **0001047469-13-010973:E0475** L1956-L1958 (date: August 29, 2013; actor: Party C; terms: party )
- [ ] **0001047469-13-010973:E0478** L1960-L1962 (date: September 3, 2013; actor: Party A; terms: party )
- [ ] **0001047469-13-010973:E0482** L1964-L1968 (date: September 9, 2013; actor: Party B; value: $19.50 per share; terms: party )
- [ ] **0001047469-13-010973:E0485** L1970-L1974 (date: September 10, 2013; actor: Party A; value: $18.00 to $19.00 per share; terms: party )
- [ ] **0001047469-13-010973:E0487** L1976-L1980 (date: September 11, 2013; actor: Party A; terms: party , special committee, transaction committee)
- [ ] **0001047469-13-010973:E0490** L1982-L1988 (date: September 11, 2013; actor: Party A; terms: party , special committee, transaction committee)
- [ ] **0001047469-13-010973:E0492** L1993-L2000 (date: September 18, 2013; actor: Party A; terms: party , special committee, stockholder)
- [ ] **0001047469-13-010973:E0495** L2002-L2005 (date: September 12, 2013; actor: Party A; terms: party , stockholder, transaction committee)
- [ ] **0001047469-13-010973:E0497** L2007-L2008 (date: September 11, 2013; actor: Party A; terms: party )
- [ ] **0001047469-13-010973:E0501** L2010-L2018 (date: September 18, 2013; actor: Party A; value: $20.75 per share; terms: party , stockholder)
- [ ] **0001047469-13-010973:E0505** L2020-L2027 (date: September 19, 2013; actor: Party A; terms: party , special committee, stockholder)
- [ ] **0001047469-13-010973:E0506** L2032-L2041 (actor: Party B; terms: party , special committee)
- [ ] **0001047469-13-010973:E0508** L2043-L2052 (actor: Party B; value: $20.75; terms: party , special committee, stockholder)
- [ ] **0001047469-13-010973:E0512** L2054-L2059 (date: September 21, 2013; actor: Transaction Committee; value: $21.25 per share; terms: transaction committee)
- [ ] **0001047469-13-010973:E0520** L2073-L2077 (date: September 23, 2013; actor: Special Committee; terms: counsel, special committee)
- [ ] **0001047469-13-010973:E0524** L2079-L2085 (date: September 23, 2013; actor: Special Committee; value: $21.25 per share; terms: special committee, transaction committee)
- [ ] **0001047469-13-010973:E0531** L2091-L2102 (date: September 25, 2013; actor: Transaction Committee; terms: counsel, special committee, transaction committee)
- [ ] **0001047469-13-010973:E0535** L2107-L2109 (date: September 24, 2013; terms: counsel)
- [ ] **0001047469-13-010973:E0538** L2111-L2114 (date: October 1, 2013; actor: Merrill Lynch)
- [ ] **0001047469-13-010973:E0543** L2121-L2125 (date: October 7, 2013; actor: Special Committee; terms: special committee, transaction committee)
- [ ] **0001047469-13-010973:E0549** L2131-L2137 (date: October 8, 2013; actor: Transaction Committee; value: $50; terms: special committee, transaction committee)
- [ ] **0001047469-13-010973:E0554** L2145-L2148 (date: October 9, 2013; actor: Transaction Committee; terms: transaction committee)
- [ ] **0001047469-13-010973:E0558** L2150-L2158 (date: October 9, 2013; actor: Special Committee; value: $50; terms: special committee, transaction committee)
- [ ] **0001047469-13-010973:E0562** L2160-L2165 (date: October 10, 2013; actor: Transaction Committee; terms: special committee, transaction committee)
- [ ] **0001047469-13-010973:E0566** L2167-L2169 (date: October 11, 2013; actor: Transaction Committee; value: $11; terms: special committee, transaction committee)

### Process signals to check
- [ ] **0001047469-13-010973:E0441** L1889-L1896 (actor: Party A; terms: due diligence)
- [ ] **0001047469-13-010973:E0443** L1901-L1905 (actor: Party B; terms: confidentiality agreement)
- [ ] **0001047469-13-010973:E0449** L1910-L1913 (date: July 27, 2103; actor: Party A; terms: confidentiality and standstill, standstill)
- [ ] **0001047469-13-010973:E0452** L1915-L1917 (date: August 6, 2013; actor: Party B; terms: management presentation)
- [ ] **0001047469-13-010973:E0455** L1919-L1921 (date: August 8, 2013; actor: Party C; terms: management presentation)
- [ ] **0001047469-13-010973:E0458** L1923-L1925 (date: August 12, 2013; actor: Transaction Committee; terms: management presentation)
- [ ] **0001047469-13-010973:E0461** L1927-L1929 (date: August 14, 2013; actor: Party A; terms: management presentation)
- [ ] **0001047469-13-010973:E0464** L1931-L1935 (date: August 15, 2013; actor: Party A; terms: due diligence, management presentation, strategic alternatives)
- [ ] **0001047469-13-010973:E0467** L1937-L1941 (date: August 6, 2013; actor: Party B; terms: due diligence)
- [ ] **0001047469-13-010973:E0470** L1946-L1950 (date: August 27, 2013; actor: Party A; terms: due diligence)
- [ ] **0001047469-13-010973:E0473** L1952-L1954 (date: August 27, 2013; actor: Party B; terms: due diligence)
- [ ] **0001047469-13-010973:E0476** L1956-L1958 (date: August 29, 2013; actor: Party C; terms: due diligence)
- [ ] **0001047469-13-010973:E0479** L1960-L1962 (date: September 3, 2013; actor: Party A; terms: due diligence)
- [ ] **0001047469-13-010973:E0488** L1976-L1980 (date: September 11, 2013; actor: Party A; terms: strategic alternatives)
- [ ] **0001047469-13-010973:E0493** L1993-L2000 (date: September 18, 2013; actor: Party A; terms: due diligence)
- [ ] **0001047469-13-010973:E0496** L2002-L2005 (date: September 12, 2013; actor: Party A; terms: strategic alternatives)
- [ ] **0001047469-13-010973:E0498** L2007-L2008 (date: September 11, 2013; actor: Party A; terms: due diligence)
- [ ] **0001047469-13-010973:E0502** L2010-L2018 (date: September 18, 2013; actor: Party A; value: $20.75 per share; terms: best and final)
- [ ] **0001047469-13-010973:E0509** L2043-L2052 (actor: Party B; value: $20.75; terms: exclusivity)
- [ ] **0001047469-13-010973:E0514** L2061-L2064 (date: September 21, 2013; value: $15; terms: exclusivity)
- [ ] **0001047469-13-010973:E0517** L2069-L2071 (value: $21.25; terms: exclusivity)
- [ ] **0001047469-13-010973:E0521** L2073-L2077 (date: September 23, 2013; actor: Special Committee; terms: strategic alternatives)
- [ ] **0001047469-13-010973:E0525** L2079-L2085 (date: September 23, 2013; actor: Special Committee; value: $21.25 per share; terms: exclusivity)
- [ ] **0001047469-13-010973:E0528** L2087-L2089 (date: September 24, 2013; terms: exclusivity)
- [ ] **0001047469-13-010973:E0532** L2091-L2102 (date: September 25, 2013; actor: Transaction Committee; terms: due diligence, strategic alternatives, superior proposal)
- [ ] **0001047469-13-010973:E0539** L2111-L2114 (date: October 1, 2013; actor: Merrill Lynch; terms: due diligence)
- [ ] **0001047469-13-010973:E0559** L2150-L2158 (date: October 9, 2013; actor: Special Committee; value: $50; terms: exclusivity)

### Outcome facts to verify
- [ ] **0001047469-13-010973:E0503** L2010-L2018 (date: September 18, 2013; actor: Party A; value: $20.75 per share; terms: closing)
- [ ] **0001047469-13-010973:E0515** L2061-L2064 (date: September 21, 2013; value: $15; terms: termination fee)
- [ ] **0001047469-13-010973:E0518** L2069-L2071 (value: $21.25; terms: closing)
- [ ] **0001047469-13-010973:E0526** L2079-L2085 (date: September 23, 2013; actor: Special Committee; value: $21.25 per share; terms: closing, termination fee)
- [ ] **0001047469-13-010973:E0529** L2087-L2089 (date: September 24, 2013; terms: executed)
- [ ] **0001047469-13-010973:E0533** L2091-L2102 (date: September 25, 2013; actor: Transaction Committee; terms: merger agreement, termination fee)
- [ ] **0001047469-13-010973:E0536** L2107-L2109 (date: September 24, 2013; terms: merger agreement)
- [ ] **0001047469-13-010973:E0541** L2116-L2119 (date: October 5, 2013; terms: merger agreement)
- [ ] **0001047469-13-010973:E0546** L2127-L2129 (date: October 7, 2013; value: $15; terms: merger agreement, termination fee)
- [ ] **0001047469-13-010973:E0550** L2131-L2137 (date: October 8, 2013; actor: Transaction Committee; value: $50; terms: merger agreement, termination fee)
- [ ] **0001047469-13-010973:E0552** L2142-L2143 (value: $50; terms: termination fee)
- [ ] **0001047469-13-010973:E0555** L2145-L2148 (date: October 9, 2013; actor: Transaction Committee; terms: merger agreement, termination fee)
- [ ] **0001047469-13-010973:E0560** L2150-L2158 (date: October 9, 2013; actor: Special Committee; value: $50; terms: termination fee)
- [ ] **0001047469-13-010973:E0563** L2160-L2165 (date: October 10, 2013; actor: Transaction Committee; terms: termination fee)
</evidence_checklist>

<actor_roster>
{
  "quotes": [
    {
      "quote_id": "Q001",
      "block_id": "B003",
      "text": "Mac-Gray Board of Directors"
    },
    {
      "quote_id": "Q002",
      "block_id": "B017",
      "text": "the Transaction Committee"
    },
    {
      "quote_id": "Q003",
      "block_id": "B042",
      "text": "the Special Committee"
    },
    {
      "quote_id": "Q004",
      "block_id": "B005",
      "text": "Mac-Gray engaged BofA Merrill Lynch"
    },
    {
      "quote_id": "Q005",
      "block_id": "B011",
      "text": "Goodwin Procter LLP, outside legal counsel to Mac-Gray"
    },
    {
      "quote_id": "Q006",
      "block_id": "B140",
      "text": "Kirkland & Ellis LLP, outside legal counsel to CSC/Pamplona"
    },
    {
      "quote_id": "Q007",
      "block_id": "B007",
      "text": "another strategic party, whom we refer to as Party A"
    },
    {
      "quote_id": "Q008",
      "block_id": "B057",
      "text": "Party B"
    },
    {
      "quote_id": "Q009",
      "block_id": "B059",
      "text": "Party C"
    },
    {
      "quote_id": "Q010",
      "block_id": "B051",
      "text": "including CSC and Pamplona"
    },
    {
      "quote_id": "Q011",
      "block_id": "B034",
      "text": "Moab Partners, L. P."
    },
    {
      "quote_id": "Q012",
      "block_id": "B177",
      "text": "Moab and Parent executed"
    },
    {
      "quote_id": "Q013",
      "block_id": "B051",
      "text": "a total of 50 parties"
    },
    {
      "quote_id": "Q014",
      "block_id": "B051",
      "text": "15 of which were potential strategic buyers"
    },
    {
      "quote_id": "Q015",
      "block_id": "B051",
      "text": "35 of which were potential financial buyers"
    },
    {
      "quote_id": "Q016",
      "block_id": "B053",
      "text": "a total of 20 potential bidders"
    },
    {
      "quote_id": "Q017",
      "block_id": "B053",
      "text": "two strategic bidders"
    },
    {
      "quote_id": "Q018",
      "block_id": "B053",
      "text": "18 financial bidders"
    },
    {
      "quote_id": "Q019",
      "block_id": "B019",
      "text": "invite three nationally recognized investment banks"
    }
  ],
  "actors": [
    {
      "actor_id": "target_mac_gray_board",
      "display_name": "Mac-Gray Board of Directors",
      "canonical_name": "MAC-GRAY BOARD OF DIRECTORS",
      "aliases": [
        "Board"
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
      "actor_id": "target_transaction_committee",
      "display_name": "Transaction Committee",
      "canonical_name": "TRANSACTION COMMITTEE",
      "aliases": [],
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
      "actor_id": "target_special_committee",
      "display_name": "Special Committee",
      "canonical_name": "SPECIAL COMMITTEE",
      "aliases": [],
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
        "Q003"
      ],
      "notes": []
    },
    {
      "actor_id": "advisor_bofa_merrill_lynch",
      "display_name": "BofA Merrill Lynch",
      "canonical_name": "BOFA MERRILL LYNCH",
      "aliases": [],
      "role": "advisor",
      "advisor_kind": "financial",
      "advised_actor_id": "target_mac_gray_board",
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
      "actor_id": "advisor_goodwin_procter",
      "display_name": "Goodwin Procter LLP",
      "canonical_name": "GOODWIN PROCTER LLP",
      "aliases": [
        "Goodwin Procter"
      ],
      "role": "advisor",
      "advisor_kind": "legal",
      "advised_actor_id": "target_mac_gray_board",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q005"
      ],
      "notes": []
    },
    {
      "actor_id": "advisor_kirkland",
      "display_name": "Kirkland & Ellis LLP",
      "canonical_name": "KIRKLAND & ELLIS LLP",
      "aliases": [
        "Kirkland"
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
        "The filing identifies Kirkland as outside legal counsel to CSC/Pamplona jointly."
      ]
    },
    {
      "actor_id": "bidder_party_a",
      "display_name": "Party A",
      "canonical_name": "PARTY A",
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
        "Q007"
      ],
      "notes": []
    },
    {
      "actor_id": "bidder_party_b",
      "display_name": "Party B",
      "canonical_name": "PARTY B",
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
      "quote_ids": [
        "Q008"
      ],
      "notes": []
    },
    {
      "actor_id": "bidder_party_c",
      "display_name": "Party C",
      "canonical_name": "PARTY C",
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
      "quote_ids": [
        "Q009"
      ],
      "notes": []
    },
    {
      "actor_id": "bidder_csc",
      "display_name": "CSC",
      "canonical_name": "CSC",
      "aliases": [
        "CSC/Pamplona"
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
        "Q010"
      ],
      "notes": [
        "The filing often describes CSC and Pamplona jointly as CSC/Pamplona."
      ]
    },
    {
      "actor_id": "bidder_pamplona",
      "display_name": "Pamplona",
      "canonical_name": "PAMPLONA",
      "aliases": [
        "CSC/Pamplona"
      ],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": "financial",
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q010"
      ],
      "notes": [
        "The filing often describes CSC and Pamplona jointly as CSC/Pamplona."
      ]
    },
    {
      "actor_id": "activist_moab",
      "display_name": "Moab",
      "canonical_name": "MOAB PARTNERS, L. P.",
      "aliases": [],
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
        "Q011"
      ],
      "notes": []
    },
    {
      "actor_id": "bidder_parent",
      "display_name": "Parent",
      "canonical_name": "PARENT",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": [
        "Q012"
      ],
      "notes": [
        "The chronology identifies this acquisition vehicle only as Parent."
      ]
    }
  ],
  "count_assertions": [
    {
      "subject": "parties solicited for potential interest in a transaction with Mac-Gray",
      "count": 50,
      "quote_ids": [
        "Q013"
      ]
    },
    {
      "subject": "potential strategic buyers solicited",
      "count": 15,
      "quote_ids": [
        "Q014"
      ]
    },
    {
      "subject": "potential financial buyers solicited",
      "count": 35,
      "quote_ids": [
        "Q015"
      ]
    },
    {
      "subject": "potential bidders entering confidentiality agreements",
      "count": 20,
      "quote_ids": [
        "Q016"
      ]
    },
    {
      "subject": "strategic bidders entering confidentiality agreements",
      "count": 2,
      "quote_ids": [
        "Q017"
      ]
    },
    {
      "subject": "financial bidders entering confidentiality agreements",
      "count": 18,
      "quote_ids": [
        "Q018"
      ]
    },
    {
      "subject": "investment banks invited to submit proposals",
      "count": 3,
      "quote_ids": [
        "Q019"
      ]
    }
  ],
  "unresolved_mentions": [
    "Two additional nationally recognized investment banks invited to submit proposals were not named.",
    "Most of the 50 solicited parties and 20 confidentiality-agreement counterparties were not individualized in the filing."
  ]
}
</actor_roster>

<task_instructions>
IMPORTANT: You MUST follow the quote-before-extract protocol.

Step 1 - QUOTE: Read the chronology blocks above. For every passage that describes an M&A event, copy the exact verbatim text into the quotes array. Each quote needs a unique quote_id (Q001, Q002, ...), the block_id it comes from, and the verbatim text.

Step 2 - EXTRACT: Build the events array using the locked actor roster. Each event references quote_ids from Step 1 instead of inline evidence. Do not include anchor_text or evidence_refs.

Return a single JSON object with: quotes, events, exclusions, coverage_notes. The quotes array MUST appear first.
</task_instructions>