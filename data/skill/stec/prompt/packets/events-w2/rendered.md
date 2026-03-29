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
window_id: w2
</deal_context>

<chronology_blocks>
B118 [L1712-L1712]: Attractive Value. Our board of directors considered the value of the merger consideration of $6.85 per share in cash attractive relative to
B119 [L1714-L1714]: High Likelihood of Completion. Our board of directors considered the high degree of certainty that the closing will be achieved, particularly in
B120 [L1716-L1716]: WDCs financial capacity to complete an acquisition of this size;
B121 [L1718-L1718]: that WDCs obligation to complete the merger is not subject to receipt of financing or to any other financing-related condition;
B122 [L1720-L1720]: that WDC represented in the merger agreement that it has (and at the closing of the merger will have) sufficient cash to enable it to pay the merger
B123 [L1722-L1722]: that WDC committed in the merger agreement to use its reasonable best efforts to cause the merger to be completed and to avoid or eliminate each and
B124 [L1724-L1726]: the provision of the merger agreement that allows the end date for completing the merger to be extended to February 28, 2014, if the merger has not been completed by the initial December 31, 2013 deadline because certain required antitrust approvals have not been obtained or because of ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
B125 [L1728-L1728]: 36
B126 [L1731-L1731]: the issuance or enactment by a governmental authority of an order or law prohibiting or restraining the merger (which prohibition or restraint is in respect of an antitrust law); and
B127 [L1733-L1733]: sTecs ability to seek specific performance to prevent breaches of the merger agreement by WDC and to enforce specifically the terms of the merger
B128 [L1735-L1738]: Receipt of Opinion from BofA Merrill Lynch. Our board of directors considered the opinion of BofA Merrill Lynch, dated June 23, 2013, to our board of directors as to the fairness, from a financial point of view and as of the date of the opinion, of the merger consideration to be received by holders of sTec common stock (other th... and dissenting shareholders), as more fully described below in the section entitled  Financial Advisors Opinion. ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
B129 [L1740-L1740]: Support of sTecs Principal Shareholders. Our board of directors considered that Messrs. Moshayedi, who combined hold 13.8% of the
B130 [L1742-L1742]: Other Terms of the Transaction. The board of directors of sTec considered the terms and conditions of the merger agreement and related
B131 [L1744-L1744]: the availability of statutory dissenters rights to all of sTecs shareholders who desire to exercise such rights, and who comply with all
B132 [L1746-L1746]: the provision of the merger agreement allowing our board of directors to terminate the merger agreement in order to accept a superior proposal, subject
B133 [L1748-L1748]: the fact that the voting agreement entered into by the directors and officers terminates upon termination of the merger agreement.
B134 [L1750-L1751]: Our board of directors also considered a variety of potential risks and other potentially negative factors relating to the transaction, including the following, but concluded that the anticipated benefits of the transaction outweigh these considerations (which are not listed in any relative order of importance):
B135 [L1753-L1753]: that sTecs shareholders will have no ongoing equity participation in sTec or in WDC following the merger, and that such shareholders will cease
B136 [L1755-L1757]: the risk that one or more conditions to the parties obligations to complete the merger will not be satisfied, and the related risk that the merger may not be completed even if the merger agreement is adopted and approved by sTecs shareholders; ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
B137 [L1759-L1759]: the fact that sTec cannot implement significant cost reductions pending the merger;
B138 [L1761-L1761]: the risks and costs to sTec if the merger does not close, including the diversion of management and employee attention, potential employee attrition
B139 [L1763-L1763]: the requirement under the merger agreement that, unless the merger agreement is terminated by sTec in certain circumstances in order to accept a
B140 [L1765-L1767]: that certain terms of the merger agreement prohibit sTec and its representatives from soliciting third-party bids and from accepting, approving or recommending third-party bids except in limited circumstances, which terms could reduce the likelihood that other potential acquirers would propose an alternative transaction that may be more a... ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
B141 [L1769-L1771]: the risk of incurring substantial expenses related to the merger, including in connection with any litigation that may result from the announcement or pendency of the merger; ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
B142 [L1773-L1773]: 37
B143 [L1776-L1776]: the risk of sTec experiencing a material adverse change as defined in the merger agreement prior to closing that would allow WDC to terminate the
B144 [L1778-L1778]: that the receipt of cash in exchange for shares of sTec common stock pursuant to the merger will be a taxable transaction for U. S. federal income tax
B145 [L1780-L1780]: the possibility that, in certain circumstances under the merger agreement primarily related to the existence of an alternative acquisition proposal or
B146 [L1782-L1782]: In
B147 [L1783-L1784]: addition, our board of directors was aware of and considered the interests that sTec directors and executive officers may have with respect to the transaction that differ from, or are in addition to, their interests as shareholders of sTec generally, as described in the section entitled  The Merger Interests of sTecs Directors and Executive Officers in the Merger.
B148 [L1786-L1789]: The foregoing discussion of the information and factors considered by our board of directors is not intended to be exhaustive, but includes the material factors considered by our board of directors in reaching its determination and recommendation. In view of the variety of factors considered in connection with its evaluation of the merger, our board of directors did not find it practicable to, and did not, quantify or otherwise assign relative weights to the specific factors considered in reaching its determination and recommendation. In addition, individual directors may have given different weights to different factors. Our board of directors unanimously recommended the merger agreement and the merger based upon the totality of the information it considered.
B149 [L1791-L1791]: sTec Board of Directors
B150 [L1792-L1792]: Recommendation
B151 [L1794-L1796]: After careful consideration, our board of directors, upon the unanimous recommendation the special committee, adopted resolutions approving and adopting the merger and the merger agreement, determining that the merger agreement and the terms and conditions of the merger are in the best interests of sTec and its shareholders and resolved that the merger agreement be submitted for approval and adoption by the shareholders of sTec.
B152 [L1798-L1799]: Accordingly, our board of directors recommends that all of our shareholders vote:
B153 [L1801-L1801]: FOR the approval and adoption of the merger agreement;
B154 [L1803-L1803]: FOR the say-on-golden-parachute proposal; and
B155 [L1805-L1805]: FOR the adjournment proposal.
B156 [L1807-L1807]: Financial Advisors Opinion
B157 [L1809-L1812]: sTec has retained BofA Merrill Lynch to act as sTecs financial advisor in connection with the merger. BofA Merrill Lynch is an internationally recognized investment banking firm which is regularly engaged in the valuation of businesses and securities in connection with mergers and acquisitions, negotiated underwritings, secondary distributions of listed and unlisted securities, private placements and valuations for corporate and other purposes. sTec selected BofA Merrill Lynch to act as sTecs financial advisor in connection with the merger on the basis of BofA Merrill Lynchs experience in transactions similar to the merger, and its reputation in the investment community.
B158 [L1814-L1817]: On June 23, 2013, at a meeting of sTecs board of directors held to evaluate the merger, BofA Merrill Lynch delivered to sTecs board of directors an oral opinion, which was confirmed by delivery of a written opinion dated June 23, 2013, to the effect that, as of the date of the opinion and based on and subject to various assumptions and limitations described in its opinion, the merger consideration to be received by holders of sTec common stock (other than sTec, WDC, Merger Sub and their respective affiliates and dissenting shareholders) was fair, from a financial point of view, to such holders.
B159 [L1819-L1819]: 38
B160 [L1822-L1828]: The full text of BofA Merrill Lynchs written opinion to sTecs board of directors, which describes, among other things, the assumptions made, procedures followed, factors considered and limitations on the review undertaken, is attached as Annex B to this proxy statement and is incorporated by reference herein in its entirety. The following summary of BofA Merrill Lynchs opinion is qualified in its entirety by reference to the full text of the opinion. BofA Merrill Lynch delivered its opinion to sTecs board of directors for the benefit and use of sTecs board of directors (in its capacity as such) in connection with and for purposes of its evaluation of the merger consideration from a financial point of view. BofA Merrill Lynchs opinion does not address any other aspect of the merger and no opinion or view was expressed as to the relative merits of the merger in comparison to other strategies or transactions that might be available to sTec or in which sTec might engage or as to the underlying business decision of sTec to proceed with or effect the merger. BofA Merrill Lynchs opinion does not address any other aspect of the merger and does not constitute a recommendation to any shareholder as to how to vote or act in connection with the proposed merger or any related matter.
B161 [L1830-L1830]: In connection with rendering its opinion, BofA Merrill Lynch:
B162 [L1832-L1832]: (1)      reviewed certain publicly available business and financial information relating to sTec;
B163 [L1834-L1834]: (2)      reviewed certain internal financial and operating information with respect to the business, operations and prospects of sTec furnished to or discussed with BofA Merrill
B164 [L1836-L1836]: (3)      reviewed certain publicly available financial forecasts relating to sTec, referred to herein as sTec public forecasts;
B165 [L1838-L1838]: (4)      discussed the past and current business, operations, financial condition and prospects of sTec with members of senior management of sTec;
B166 [L1840-L1840]: (5)      reviewed the trading history for sTec common stock and a comparison of that trading history with the trading histories of other companies BofA Merrill Lynch deemed
B167 [L1842-L1842]: (6)      compared certain financial and stock market information of sTec with similar information of other companies BofA Merrill Lynch deemed relevant;
B168 [L1844-L1844]: (7)      compared certain financial terms of the merger to financial terms, to the extent publicly available, of other transactions BofA Merrill Lynch deemed relevant;
B169 [L1846-L1846]: (8)      considered the results of BofA Merrill Lynchs efforts to solicit, at the direction of sTec, indications of interest and definitive proposals from third parties
B170 [L1848-L1848]: (9)      reviewed a draft dated June 23, 2013 of the merger agreement, referred to herein as the draft agreement; and
B171 [L1850-L1850]: (10)      performed such other analyses and studies and considered such other information and factors as BofA Merrill Lynch deemed appropriate.
B172 [L1852-L1856]: In arriving at its opinion, BofA Merrill Lynch assumed and relied upon, without independent verification, the accuracy and completeness of the financial and other information and data publicly available or provided to or otherwise reviewed by or discussed with it and relied upon the assurances of the management of sTec that they were not aware of any facts or circumstances that would make such information or data inaccurate or misleading in any material respect. With respect to the sTec management forecasts, BofA Merrill Lynch was advised by sTec, and assumed, that they were reasonably prepared on bases reflecting the best currently available estimates and good faith judgments of the management of sTec as to the future financial performance of sTec. With respect to the sTec public forecasts, BofA Merrill Lynch was advised by sTec, and assumed, that such forecasts were a reasonable basis upon which to evaluate the future financial performance of sTec. BofA Merrill Lynch did not make and was not provided with any independent evaluation or appraisal of the assets or liabilities (contingent or
B173 [L1858-L1858]: 39
B174 [L1861-L1867]: otherwise) of sTec, nor did it make any physical inspection of the properties or assets of sTec. BofA Merrill Lynch did not evaluate the solvency or fair value of sTec or WDC or any of their respective affiliates under any state, federal or other laws relating to bankruptcy, insolvency or similar matters. BofA Merrill Lynch assumed, at the direction of sTec, that the merger would be consummated in accordance with its terms, without waiver, modification or amendment of any material term, condition or agreement and that, in the course of obtaining the necessary governmental, regulatory and other approvals, consents, releases and waivers for the merger, no delay, limitation, restriction or condition, including any divestiture requirements or amendments or modifications, would be imposed that would have an adverse effect on sTec or the merger (including the contemplated benefits of the merger). With respect to any litigation in which sTec or any of its affiliates is or may be engaged, BofA Merrill Lynch assumed, with sTecs consent and without independent verification, that neither any such litigation nor any outcome of any such litigation will affect sTec or the merger (including the contemplated benefits of the merger) or its analyses or opinion in any material respect. BofA Merrill Lynch also assumed, at the direction of sTec, that the final executed merger agreement would not differ in any material respect from the draft agreement reviewed by BofA Merrill Lynch.
B175 [L1869-L1878]: BofA Merrill Lynch expressed no view or opinion as to any terms or other aspects or implications of the merger (other than the merger consideration to the extent expressly specified in its opinion), including, without limitation, the form or structure of the merger or any terms, aspects or implications of the voting agreements, the non-competition agreements, the release and covenant not to sue, the technical services and consulting services agreements (each as defined or described in the merger agreement) or any other agreement, arrangement or understanding entered into in connection or related to the merger or otherwise. BofA Merrill Lynchs opinion was limited to the fairness, from a financial point of view, of the merger consideration to be received by the holders of sTec common stock (other than sTec, WDC, Merger Sub and their respective affiliates and dissenting shareholders) and no opinion or view was expressed with respect to any consideration received in connection with the merger by the holders of any other class of securities, creditors or other constituencies of any party. In addition, no opinion or view was expressed with respect to the fairness (financial or otherwise) of the amount, nature or any other aspect of any compensation to any of the officers, directors or employees of any party to the merger, or class of such persons, relative to the merger consideration or otherwise. Furthermore, no opinion or view was expressed as to the relative merits of the merger in comparison to other strategies or transactions that might be available to sTec or in which sTec might engage or as to the underlying business decision of sTec to proceed with or effect the merger. In addition, BofA Merrill Lynch expressed no opinion or recommendation as to how any shareholder should vote or act in connection with the merger or any related matter. Except as described above, sTec imposed no other limitations on the investigations made or procedures followed by BofA Merrill Lynch in rendering its opinion.
B176 [L1880-L1882]: BofA Merrill Lynchs opinion was necessarily based on financial, economic, monetary, market and other conditions and circumstances as in effect on, and the information made available to BofA Merrill Lynch as of, the date of its opinion. It should be understood that subsequent developments may affect its opinion, and BofA Merrill Lynch does not have any obligation to update, revise or reaffirm its opinion. The issuance of BofA Merrill Lynchs opinion was approved by BofA Merrill Lynchs Americas Fairness Opinion Review Committee.
B177 [L1884-L1887]: The following represents a brief summary of the material financial analyses presented by BofA Merrill Lynch to sTecs board of directors in connection with its opinion. The financial analyses summarized below include information presented in tabular format. In order to fully understand the financial analyses performed by BofA Merrill Lynch, the tables must be read together with the text of each summary. The tables alone do not constitute a complete description of the financial analyses performed by BofA Merrill Lynch. Considering the data set forth in the tables below without considering the full narrative description of the financial analyses, including the methodologies and assumptions underlying the analyses, could create a misleading or incomplete view of the financial analyses performed by BofA Merrill Lynch.
B178 [L1889-L1889]: 40
B179 [L1892-L1892]: sTec Financial Analyses.
B180 [L1894-L1894]: Selected Publicly Traded Companies Analysis.
B181 [L1896-L1896]: Fusion-io, Inc.
B182 [L1898-L1898]: Micron Technology, Inc.
B183 [L1900-L1900]: OCZ Technology Group, Inc.
B184 [L1902-L1902]: SanDisk Corporation
B185 [L1904-L1904]: Seagate Technology plc
B186 [L1906-L1906]: SK Hynix Inc.
B187 [L1908-L1908]: Western Digital Corporation
B188 [L1910-L1913]: BofA Merrill Lynch reviewed enterprise values of the selected publicly traded companies, calculated as equity values based on closing stock prices on June 21, 2013, plus total debt, minority interest and preferred stock, less cash and cash equivalents, as a multiple of calendar year 2013 estimated revenues. The range of revenue multiples for the selected publicly traded companies was 0.17x to 2.54x and the mean and median revenue multiples for the selected publicly traded companies were 1.49x and 1.82x, respectively. BofA Merrill Lynch then applied estimated revenue multiples of 0.20x to 1.85x derived from the selected publicly traded companies to sTecs calendar year 2013 estimated revenue, using both the sTec public forecasts (Street Case) and the sTec management forecasts (Management Case).
B189 [L1915-L1915]: Estimated
B190 [L1916-L1916]: financial data of the selected publicly traded companies were based on publicly available research analysts estimates, and estimated financial data of sTec were based on the sTec public forecasts and the sTec management forecasts.
B191 [L1918-L1919]: This analysis indicated the following approximate implied per share equity value reference ranges for sTec, rounded to the nearest $0.25, as compared to the merger consideration:
B192 [L1921-L1921]: Implied Per Share Equity Value Reference                                     Merger Consideration
B193 [L1922-L1922]: 2013E Revenue (Street Case)                   2013E Revenue (Management
B194 [L1923-L1923]: $3.00 - $6.50                                 $3.25 - $8.50                  $                         6.85
B195 [L1925-L1927]: No company used in this analysis is identical or directly comparable to sTec. Accordingly, an evaluation of the results of this analysis is not entirely mathematical. Rather, this analysis involves complex considerations and judgments concerning differences in financial and operating characteristics and other factors that could affect the public trading or other values of the companies to which sTec was compared.
B196 [L1929-L1929]: Selected Precedent Transactions Analysis
B197 [L1931-L1931]: Acquiror                   Target
B198 [L1932-L1932]:  PMC-Sierra, Inc.          Integrated Device Technology, Inc. (Enterprise Flash Controller Business)
B199 [L1933-L1933]:  LSI Corporation           SandForce, Inc.
B200 [L1934-L1934]:  SanDisk Corporation       Pliant Technology, Inc.
B201 [L1936-L1936]: 41
B202 [L1939-L1939]:  Seagate Technology plc            Samsung Electronics Co., Inc. (HDD Unit)
B203 [L1940-L1940]:  Western Digital Corporation       Hitachi Global Storage Technologies
B204 [L1941-L1941]:  Western Digital Corporation       SiliconSystems, Inc.
B205 [L1942-L1942]:  Toshiba Corporation               Fujitsu Limited (Hard Drive Disk Business)
B206 [L1944-L1950]: BofA Merrill Lynch reviewed transaction values, calculated as the enterprise value implied for the target company (or its business segment being sold) based on the consideration payable in the selected transaction, as a multiple of the target companys last twelve months, or LTM, revenue (or if applicable such revenue of the business segment being sold). Based on such LTM revenue, the range of revenue multiples for the selected transactions was 0.11x to 16.35x (or 0.11x to 5.37x, excluding the multiple of 16.35x from the acquisition of Pliant Technology, Inc. by SanDisk Corporation) and the mean and median revenue multiples for the selected transactions were 1.59x and 0.71x, respectively (excluding from the calculation of the mean and median multiples the multiple for the acquisition of Pliant Technology, Inc. by SanDisk Corporation due to certain attributes of Pliant Technology, Inc. that rendered that acquisition less relevant for the analysis ). BofA Merrill Lynch then applied LTM revenue multiples of 0.70x to 2.50x derived from the selected transactions to sTecs LTM revenue as of the end of the first quarter of 2013. Financial data of the selected transactions were based on publicly available information at the time of announcement of each relevant transaction. This analysis indicated the following approximate implied per share equity value reference ranges for sTec, rounded to the nearest $0.25, as compared to the merger consideration:
B207 [L1952-L1952]: Implied Per Share Equity Value Reference Ranges for      Merger Consideration
B208 [L1953-L1954]: 2013 LTM Revenue $4.75 - $9.75                                            $                         6.85
B209 [L1956-L1958]: No company, business or transaction used in this analysis is identical or directly comparable to sTec or the merger. Accordingly, an evaluation of the results of this analysis is not entirely mathematical. Rather, this analysis involves complex considerations and judgments concerning differences in financial and operating characteristics and other factors that could affect the acquisition or other values of the companies, business segments or transactions to which sTec and the merger were compared.
B210 [L1960-L1960]: Discounted Cash Flow Analysis.
B211 [L1962-L1963]: This analysis indicated the following approximate implied per share equity value reference ranges for sTec, rounded to the nearest $0.25, as compared to the merger consideration:
B212 [L1965-L1965]: Implied Per Share Equity Value Reference Ranges for sTec      Merger Consideration
B213 [L1966-L1966]: $5.25 - $8.50                                                 $                         6.85
B214 [L1968-L1968]: Other Factors.
B215 [L1970-L1971]: historical trading prices and trading volumes of sTec common stock during the one-year period ended June 21, 2013; ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
B216 [L1973-L1973]: 42
B217 [L1976-L1976]: the present value of targets for sTecs common stock price published by eight equity analysts during the period from May 8, 2013 to
B218 [L1978-L1978]: the results of the selected premiums paid analysis described immediately below.
B219 [L1980-L1983]: BofA Merrill Lynch identified, to the extent publicly available, selected transactions for publicly traded companies in the technology industry, announced since January 1, 2009. BofA Merrill Lynch calculated the premium over the target companys closing stock price one day, one month and three months prior to the announcement of each transaction, or to the extent applicable, the target companys unaffected stock price, of the per share price paid in each selected transaction, and calculated the premium over the target companys enterprise value one day, one month and three months prior to the announcement of the transaction, or to the extent applicable, the target companys enterprise value based on its unaffected stock price, of the price paid in each selected transaction.
B220 [L1985-L1985]: Selected Technology Equity
B221 [L1987-L1987]: Value Premiums
B222 [L1988-L1993]: ──────────────────────────────────────────────────────────────── Mean                                40.9      44.5      48.0 Median                              33.4      37.1      43.1 Selected Technology Enterprise Mean                                47.7      52.7      59.1 Median                              38.6      41.6      46.1
B223 [L1995-L1998]: BofA Merrill Lynch then applied a range of calculated premiums from 30%  50% to the price per share of $3.59 of sTec common stock as of the close of trading on the trading day immediately prior to the announcement of the merger, and applied a range of 35%  55% of calculated premiums to the enterprise value of sTec based on the price per share of $3.59 of sTec common stock as of the close of trading on the trading day immediately prior to the announcement of the merger. This analysis indicated the following approximate per share equity value reference ranges, rounded to the nearest $0.25, for sTec, as compared to the merger consideration:
B224 [L2000-L2000]: Implied Reference Ranges                         Merger Consideration
B225 [L2001-L2001]: Equity Value                  $4.75 - $5.50      $                         6.85
B226 [L2002-L2002]: Enterprise Value              $4.00 - $4.00
B227 [L2004-L2006]: No company used in this analysis is identical or directly comparable to sTec. Accordingly, an evaluation of the results of this analysis is not entirely mathematical. Rather, this analysis involves complex considerations and judgments concerning differences in financial and operating characteristics and other factors that could affect the public trading or other values of the companies to which sTec was compared.
B228 [L2008-L2008]: Miscellaneous.
B229 [L2010-L2010]: 43
B230 [L2013-L2018]: In performing its analyses, BofA Merrill Lynch considered industry performance, general business and economic conditions and other matters, many of which are beyond the control of sTec and WDC. The estimates of the future performance of sTec and WDC in or underlying BofA Merrill Lynchs analyses are not necessarily indicative of actual values or actual future results, which may be significantly more or less favorable than those estimates or those suggested by BofA Merrill Lynchs analyses. These analyses were prepared solely as part of BofA Merrill Lynchs analysis of the fairness, from a financial point of view, of the merger consideration and were provided to sTecs board of directors in connection with the delivery of BofA Merrill Lynchs opinion. The analyses do not purport to be appraisals or to reflect the prices at which a company might actually be sold or the prices at which any securities have traded or may trade at any time in the future. Accordingly, the estimates used in, and the ranges of valuations resulting from, any particular analysis described above are inherently subject to substantial uncertainty and should not be taken to be BofA Merrill Lynchs view of the actual values of sTec or WDC.
B231 [L2020-L2023]: The type and amount of consideration payable in the merger was determined through negotiations between sTec and WDC, rather than by any financial advisor, and was approved by sTecs board of directors. The decision to enter into the merger agreement was solely that of sTecs board of directors. As described above, BofA Merrill Lynchs opinion and analyses were only one of many factors considered by sTecs board of directors in its evaluation of the proposed merger and should not be viewed as determinative of the views of sTecs board of directors or management with respect to the merger or the merger consideration.
B232 [L2025-L2028]: sTec has agreed to pay BofA Merrill Lynch for its services in connection with the merger an aggregate fee of approximately $4.3 million, $250,000 of which was payable in connection with its opinion and the remainder of which is contingent upon the completion of the merger, subject to certain initial and quarterly retainer fee payments which will be credited against the portion of the fee that will be paid upon completion of the merger. sTec also has agreed to reimburse BofA Merrill Lynch for its expenses incurred in connection with BofA Merrill Lynchs engagement and to indemnify BofA Merrill Lynch, any controlling person of BofA Merrill Lynch and each of their respective directors, officers, employees, agents and affiliates against specified liabilities, including liabilities under the federal securities laws.
B233 [L2030-L2034]: BofA Merrill Lynch and its affiliates comprise a full service securities firm and commercial bank engaged in securities, commodities and derivatives trading, foreign exchange and other brokerage activities, and principal investing as well as providing investment, corporate and private banking, asset and investment management, financing and financial advisory services and other commercial services and products to a wide range of companies, governments and individuals. In the ordinary course of their businesses, BofA Merrill Lynch and its affiliates invest on a principal basis or on behalf of customers or manage funds that invest, make or hold long or short positions, finance positions or trade or otherwise effect transactions in the equity, debt or other securities or financial instruments (including derivatives, bank loans or other obligations) of sTec, WDC and certain of their respective affiliates.
</chronology_blocks>

<overlap_context>
B116 [L1708-L1708]: our board of directors belief that the process conducted by sTec, in conjunction with its advisors, had resulted in the highest price reasonably
B117 [L1710-L1710]: Greater Certainty of Value. Our board of directors considered that the proposed merger consideration is to be paid entirely in cash, which
B234 [L2036-L2041]: BofA Merrill Lynch and its affiliates in the past have provided, currently are providing, and in the future may provide investment banking, commercial banking and other financial services to WDC and certain of its affiliates and have received or in the future may receive compensation for the rendering of these services, including (a) having acted or acting as administrative agent, lead arranger and bookrunner for, and/or as a lender under, certain term loans, letters of credit and credit and leasing facilities and other credit arrangements of WDC and certain of its affiliates (including acquisition financing), (b) having acted as financial advisor to WDC in connection with an acquisition transaction, (c) having provided or providing certain derivatives, foreign exchange and other trading services to WDC and certain of its affiliates, and (d) having provided or providing certain treasury management products and services to WDC and certain of its affiliates. From January 1, 2011 through June 30, 2013, BofA Merrill Lynch and its affiliates received aggregate revenues from WDC and certain of its affiliates of approximately $45 million for corporate, commercial and investment banking services.
B235 [L2043-L2043]: 44
</overlap_context>

<evidence_checklist>
### Dated actions to extract
- [ ] **0001193125-13-325730:E0473** L1735-L1738 (date: June 23, 2013; actor: Merrill Lynch; terms: received, sent)
- [ ] **0001193125-13-325730:E0485** L1765-L1767 (date: may; terms: sent)
- [ ] **0001193125-13-325730:E0499** L1814-L1817 (date: June 23, 2013; actor: Merrill Lynch; terms: delivered, meeting, received)
- [ ] **0001193125-13-325730:E0511** L1861-L1867 (date: may; actor: Merrill Lynch; terms: engaged, executed, sent)
- [ ] **0001193125-13-325730:E0526** L1976-L1976 (date: May 8, 2013; terms: sent)
- [ ] **0001193125-13-325730:E0527** L1980-L1983 (date: January 1, 2009; actor: Merrill Lynch; terms: announced)
- [ ] **0001193125-13-325730:E0539** L2036-L2041 (date: may; actor: Merrill Lynch; value: $45; terms: received)

### Financial terms to capture
- [ ] **0001193125-13-325730:E0467** L1712-L1712 (value: $6.85 per share; terms: $6.85 per share)
- [ ] **0001193125-13-325730:E0520** L1918-L1919 (value: $0.25; terms: $0.25)
- [ ] **0001193125-13-325730:E0521** L1921-L1923 (value: $3.00 - $6.50; terms: $3.00 - $6.50, $3.25 - $8.50)
- [ ] **0001193125-13-325730:E0522** L1944-L1950 (actor: Merrill Lynch; value: $0.25; terms: $0.25)
- [ ] **0001193125-13-325730:E0524** L1952-L1954 (value: $4.75 - $9.75; terms: $4.75 - $9.75)
- [ ] **0001193125-13-325730:E0525** L1962-L1963 (value: $0.25; terms: $0.25)
- [ ] **0001193125-13-325730:E0530** L1995-L1998 (actor: Merrill Lynch; value: $3.59; terms: $0.25, $3.59)
- [ ] **0001193125-13-325730:E0532** L2000-L2002 (value: $4.75 - $5.50; terms: $4.00 - $4.00, $4.75 - $5.50)
- [ ] **0001193125-13-325730:E0536** L2025-L2028 (actor: Merrill Lynch; value: $4.3; terms: $250,000, $4.3)
- [ ] **0001193125-13-325730:E0540** L2036-L2041 (date: may; actor: Merrill Lynch; value: $45; terms: $45)

### Actors to identify
- [ ] **0001193125-13-325730:E0466** L1708-L1708 (terms: advisor, advisors)
- [ ] **0001193125-13-325730:E0474** L1735-L1738 (date: June 23, 2013; actor: Merrill Lynch; terms: advisor, financial advisor, shareholder)
- [ ] **0001193125-13-325730:E0475** L1740-L1740 (terms: shareholder)
- [ ] **0001193125-13-325730:E0477** L1744-L1744 (terms: shareholder)
- [ ] **0001193125-13-325730:E0481** L1753-L1753 (terms: shareholder)
- [ ] **0001193125-13-325730:E0482** L1755-L1757 (date: may; terms: shareholder)
- [ ] **0001193125-13-325730:E0486** L1765-L1767 (date: may; terms: party )
- [ ] **0001193125-13-325730:E0491** L1782-L1784 (date: may; terms: shareholder)
- [ ] **0001193125-13-325730:E0493** L1794-L1796 (terms: shareholder, special committee)
- [ ] **0001193125-13-325730:E0495** L1798-L1799 (terms: shareholder)
- [ ] **0001193125-13-325730:E0498** L1809-L1812 (actor: Merrill Lynch; terms: advisor, financial advisor, investment bank)
- [ ] **0001193125-13-325730:E0500** L1814-L1817 (date: June 23, 2013; actor: Merrill Lynch; terms: shareholder)
- [ ] **0001193125-13-325730:E0501** L1822-L1828 (actor: Merrill Lynch; terms: shareholder)
- [ ] **0001193125-13-325730:E0503** L1830-L1830 (actor: Merrill Lynch)
- [ ] **0001193125-13-325730:E0504** L1840-L1840 (actor: Merrill Lynch)
- [ ] **0001193125-13-325730:E0505** L1842-L1842 (actor: Merrill Lynch)
- [ ] **0001193125-13-325730:E0506** L1844-L1844 (actor: Merrill Lynch)
- [ ] **0001193125-13-325730:E0507** L1846-L1846 (actor: Merrill Lynch)
- [ ] **0001193125-13-325730:E0509** L1850-L1850 (actor: Merrill Lynch)
- [ ] **0001193125-13-325730:E0510** L1852-L1856 (actor: Merrill Lynch)
- [ ] **0001193125-13-325730:E0512** L1861-L1867 (date: may; actor: Merrill Lynch)
- [ ] **0001193125-13-325730:E0514** L1869-L1878 (actor: Merrill Lynch; terms: party , shareholder)
- [ ] **0001193125-13-325730:E0516** L1880-L1882 (date: may; actor: Merrill Lynch)
- [ ] **0001193125-13-325730:E0517** L1884-L1887 (actor: Merrill Lynch)
- [ ] **0001193125-13-325730:E0518** L1910-L1913 (date: June 21, 2013; actor: Merrill Lynch)
- [ ] **0001193125-13-325730:E0523** L1944-L1950 (actor: Merrill Lynch; value: $0.25)
- [ ] **0001193125-13-325730:E0528** L1980-L1983 (date: January 1, 2009; actor: Merrill Lynch)
- [ ] **0001193125-13-325730:E0531** L1995-L1998 (actor: Merrill Lynch; value: $3.59)
- [ ] **0001193125-13-325730:E0533** L2013-L2018 (date: may; actor: Merrill Lynch)
- [ ] **0001193125-13-325730:E0534** L2020-L2023 (actor: Merrill Lynch; terms: advisor, financial advisor)
- [ ] **0001193125-13-325730:E0537** L2025-L2028 (actor: Merrill Lynch; value: $4.3)
- [ ] **0001193125-13-325730:E0538** L2030-L2034 (actor: Merrill Lynch; terms: advisor, financial advisor)
- [ ] **0001193125-13-325730:E0541** L2036-L2041 (date: may; actor: Merrill Lynch; value: $45; terms: advisor, financial advisor, investment bank)

### Process signals to check
- [ ] **0001193125-13-325730:E0478** L1746-L1746 (terms: superior proposal)

### Outcome facts to verify
- [ ] **0001193125-13-325730:E0468** L1714-L1714 (terms: closing)
- [ ] **0001193125-13-325730:E0469** L1720-L1720 (terms: closing, merger agreement)
- [ ] **0001193125-13-325730:E0470** L1722-L1722 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0471** L1724-L1726 (date: February 28, 2014; terms: merger agreement)
- [ ] **0001193125-13-325730:E0472** L1733-L1733 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0476** L1742-L1742 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0479** L1746-L1746 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0480** L1748-L1748 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0483** L1755-L1757 (date: may; terms: merger agreement)
- [ ] **0001193125-13-325730:E0484** L1763-L1763 (terms: merger agreement, terminated)
- [ ] **0001193125-13-325730:E0487** L1765-L1767 (date: may; terms: merger agreement)
- [ ] **0001193125-13-325730:E0488** L1769-L1771 (date: may; terms: litigation)
- [ ] **0001193125-13-325730:E0489** L1776-L1776 (terms: closing, merger agreement)
- [ ] **0001193125-13-325730:E0490** L1780-L1780 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0492** L1786-L1789 (date: may; terms: merger agreement)
- [ ] **0001193125-13-325730:E0494** L1794-L1796 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0496** L1798-L1799 (terms: vote)
- [ ] **0001193125-13-325730:E0497** L1801-L1801 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0502** L1822-L1828 (actor: Merrill Lynch; terms: vote)
- [ ] **0001193125-13-325730:E0508** L1848-L1848 (date: June 23, 2013; terms: merger agreement)
- [ ] **0001193125-13-325730:E0513** L1861-L1867 (date: may; actor: Merrill Lynch; terms: executed, litigation, merger agreement)
- [ ] **0001193125-13-325730:E0515** L1869-L1878 (actor: Merrill Lynch; terms: merger agreement, vote)
- [ ] **0001193125-13-325730:E0519** L1910-L1913 (date: June 21, 2013; actor: Merrill Lynch; terms: closing)
- [ ] **0001193125-13-325730:E0529** L1980-L1983 (date: January 1, 2009; actor: Merrill Lynch; terms: closing)
- [ ] **0001193125-13-325730:E0535** L2020-L2023 (actor: Merrill Lynch; terms: merger agreement)
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