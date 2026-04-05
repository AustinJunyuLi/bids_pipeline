You are extracting filing-literal v2 observation artifacts from a single M&A chronology window.

Ground rules:
- The filing is the only source of truth.
- Quote before extract: every structured record must cite verbatim quote_ids.
- Extract only literal parties, cohorts, and observations.
- Do not emit analyst rows, benchmark rows, dropout labels, bid labels, or inferred outcomes beyond the schema fields explicitly supported below.
- Populate `recipient_refs` when the filing names invitees or a reusable bidder cohort.
- Keep agreement families distinct (`nda`, `amendment`, `standstill`, `exclusivity`, `clean_team`, `merger_agreement`).
- Preserve non-exact date precision when anchoring relative timing.

CRITICAL — TEMPORAL ORDER:
`requested_by_observation_id` links a proposal to the specific solicitation that prompted it.
The linked solicitation MUST have a date on or before the proposal date.
If no solicitation occurred on or before the proposal date, set `requested_by_observation_id` to null.
"Belonging to the same sale process" is NOT sufficient — only a direct temporal predecessor qualifies.
Common mistake: linking all proposals to the final-round solicitation even when earlier proposals predate it. An unsolicited proposal predating any solicitation MUST have `requested_by_observation_id: null`.

CRITICAL — OUTCOME ACTOR:
Outcomes with `outcome_kind` of `executed` or `restarted` MUST include the bidder `party_id` or `cohort_id` in `subject_refs` or `counterparty_refs`.
If the summary names the buyer or bidder, their `party_id` MUST appear in the structured refs — do not leave it only in the summary text.

Consult the <json_schema_reference> section for exact field names, types, and enum values.

Return valid JSON only.

<json_schema_reference>
{
  "top_level_keys": [
    "quotes",
    "parties",
    "cohorts",
    "observations",
    "exclusions",
    "coverage"
  ],
  "observation_record": {
    "discriminator": "obs_type",
    "obs_type_values": [
      "process",
      "agreement",
      "solicitation",
      "proposal",
      "status",
      "outcome"
    ],
    "common_fields": {
      "observation_id": "string",
      "obs_type": "string",
      "date": "ResolvedDate | null",
      "subject_refs": "array[string]",
      "counterparty_refs": "array[string]",
      "summary": "string",
      "quote_ids": "array[string]"
    },
    "variant_fields": {
      "process": {
        "process_kind": "enum[\"sale_launch\", \"public_announcement\", \"advisor_retention\", \"press_release\", \"other\"]",
        "process_scope": "enum[\"target\", \"bidder\", \"activist\", \"other\"]",
        "other_detail": "string | null"
      },
      "agreement": {
        "agreement_kind": "enum[\"nda\", \"amendment\", \"standstill\", \"exclusivity\", \"merger_agreement\", \"clean_team\", \"other\"]",
        "signed": "boolean | null",
        "grants_diligence_access": "boolean | null",
        "includes_standstill": "boolean | null",
        "consideration_type": "enum[\"cash\", \"stock\", \"mixed\", \"other\"]",
        "supersedes_observation_id": "string | null",
        "other_detail": "string | null"
      },
      "solicitation": {
        "requested_submission": "enum[\"ioi\", \"loi\", \"binding_offer\", \"best_and_final\", \"other\"]",
        "binding_level": "enum[\"non_binding\", \"binding\", \"mixed\", \"other\"]",
        "due_date": "ResolvedDate | null",
        "recipient_refs": "array[string]",
        "attachments": "array[string]",
        "other_detail": "string | null"
      },
      "proposal": {
        "requested_by_observation_id": "string | null",
        "revises_observation_id": "string | null",
        "delivery_mode": "enum[\"oral\", \"written\", \"email\", \"phone\", \"other\"]",
        "terms": "MoneyTerms | null",
        "mentions_non_binding": "boolean | null",
        "includes_draft_merger_agreement": "boolean | null",
        "includes_markup": "boolean | null",
        "other_detail": "string | null"
      },
      "status": {
        "status_kind": "enum[\"expressed_interest\", \"withdrew\", \"not_interested\", \"cannot_improve\", \"cannot_proceed\", \"limited_assets_only\", \"excluded\", \"selected_to_advance\", \"other\"]",
        "related_observation_id": "string | null",
        "other_detail": "string | null"
      },
      "outcome": {
        "outcome_kind": "enum[\"executed\", \"terminated\", \"restarted\", \"other\"]",
        "related_observation_id": "string | null",
        "other_detail": "string | null"
      }
    }
  },
  "ResolvedDate": {
    "fields": {
      "raw_text": "string | null",
      "normalized_start": "YYYY-MM-DD | null",
      "normalized_end": "YYYY-MM-DD | null",
      "sort_date": "YYYY-MM-DD | null",
      "precision": "DatePrecision",
      "anchor_event_id": "string | null",
      "anchor_span_id": "string | null",
      "resolution_note": "string | null",
      "is_inferred": "boolean"
    },
    "precision_enum": [
      "exact_day",
      "month",
      "month_early",
      "month_mid",
      "month_late",
      "quarter",
      "year",
      "range",
      "relative",
      "unknown"
    ]
  },
  "MoneyTerms": {
    "fields": {
      "per_share": "number | null",
      "range_low": "number | null",
      "range_high": "number | null",
      "enterprise_value": "number | null",
      "consideration_type": "enum[\"cash\", \"stock\", \"mixed\", \"other\"]"
    }
  },
  "PartyRecord": {
    "fields": {
      "party_id": "string",
      "display_name": "string",
      "canonical_name": "string | null",
      "aliases": "array[string]",
      "role": "enum[\"bidder\", \"advisor\", \"activist\", \"target_board\", \"other\"]",
      "bidder_kind": "enum[\"strategic\", \"financial\", \"unknown\"]",
      "advisor_kind": "enum[\"financial\", \"legal\", \"other\"]",
      "advised_party_id": "string | null",
      "listing_status": "enum[\"public\", \"private\"]",
      "geography": "enum[\"domestic\", \"non_us\"]",
      "quote_ids": "array[string]"
    }
  },
  "CohortRecord": {
    "fields": {
      "cohort_id": "string",
      "label": "string",
      "parent_cohort_id": "string | null",
      "exact_count": "integer",
      "known_member_party_ids": "array[string]",
      "unknown_member_count": "integer",
      "membership_basis": "string",
      "created_by_observation_id": "string",
      "quote_ids": "array[string]"
    }
  },
  "SkillExclusionRecord": {
    "fields": {
      "category": "enum[\"partial_company_bid\", \"unsigned_nda\", \"stale_process_reference\", \"duplicate_mention\", \"non_event_context\", \"other\"]",
      "block_ids": "array[string]",
      "explanation": "string"
    },
    "category_enum": [
      "partial_company_bid",
      "unsigned_nda",
      "stale_process_reference",
      "duplicate_mention",
      "non_event_context",
      "other"
    ]
  }
}
</json_schema_reference>

Schema reminders:

- `parties`: named actors only. Roles are `bidder`, `advisor`, `activist`, `target_board`, or `other`.
- `cohorts`: unnamed bidder groups only. Use exact counts when the filing states them.
- `observations` use exactly one of:
  - `process`
  - `agreement`
  - `solicitation`
  - `proposal`
  - `status`
  - `outcome`
- `solicitation.recipient_refs`: required when the filing names invitees or a reusable cohort.
- `proposal.requested_by_observation_id`: only use when the proposal responds to a same-day-or-earlier solicitation; never point forward.
- `proposal`: preserve literal formality clues via `mentions_non_binding`, `includes_draft_merger_agreement`, and `includes_markup`.
- `agreement`: keep `nda`, `amendment`, `standstill`, `exclusivity`, `clean_team`, and `merger_agreement` distinct.
- `outcome`: include bidder or bidder-cohort refs when the filing names the actor.
- Relative dates should stay non-exact and anchor to the nearest explicit local date.

Examples:

- A launch of a sale process -> `process` with `process_kind: "sale_launch"`.
- A confidentiality agreement -> `agreement` with `agreement_kind: "nda"`.
- A request for best and final bids due on a later date -> `solicitation` with `due_date`.
- A price-bearing indication of interest -> `proposal` with `terms`.
- A revised proposal with a draft merger agreement -> `proposal` with `includes_draft_merger_agreement: true`.
- "Party X was no longer interested" -> `status` with `status_kind: "not_interested"`.
- "The merger agreement was executed" -> `outcome` with `outcome_kind: "executed"` and bidder refs when the buyer is named.

Temporal linking — correct vs. incorrect:

CORRECT — solicitation precedes proposal:
  solicitation obs_evt_005 dated 2016-06-09 requests best-and-final bids.
  proposal obs_evt_010 dated 2016-06-15: `"requested_by_observation_id": "obs_evt_005"`.
  The solicitation date (June 9) is before the proposal date (June 15). Valid.

CORRECT — unsolicited proposal with no prior solicitation:
  proposal obs_evt_003 dated 2016-03-09: `"requested_by_observation_id": null`.
  No solicitation exists on or before March 9. The proposal is unsolicited. Null is correct.

WRONG — proposal links to a future solicitation:
  proposal obs_evt_003 dated 2016-03-09: `"requested_by_observation_id": "obs_evt_025"`.
  solicitation obs_evt_025 dated 2016-06-24.
  The solicitation date (June 24) is AFTER the proposal date (March 9). This is a temporal inversion.
  A proposal cannot respond to a solicitation that has not yet been issued.
  Fix: set `"requested_by_observation_id": null`.

Outcome actor refs:

CORRECT — executed outcome includes bidder:
  outcome obs_evt_021 dated 2014-12-14, `outcome_kind: "executed"`:
  `"subject_refs": ["bidder_buyer_group"], "counterparty_refs": ["target_board_company"]`.
  The bidder who executed the merger appears in subject_refs.

WRONG — executed outcome omits bidder:
  outcome obs_evt_021 dated 2014-12-14, `outcome_kind: "executed"`:
  `"subject_refs": [], "counterparty_refs": ["target_board_company"]`.
  The summary says "Buyer Group executed the merger agreement" but Buyer Group is missing from refs.
  Fix: add `"bidder_buyer_group"` to `subject_refs`.

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
- [ ] **0001193125-13-325730:E0484** L1735-L1738 (date: June 23, 2013; actors: Merrill Lynch; terms: received, sent)
- [ ] **0001193125-13-325730:E0496** L1765-L1767 (date: may; terms: sent)
- [ ] **0001193125-13-325730:E0510** L1814-L1817 (date: June 23, 2013; actors: Merrill Lynch; terms: delivered, meeting, received)
- [ ] **0001193125-13-325730:E0522** L1861-L1867 (date: may; actors: Merrill Lynch; terms: engaged, executed, sent)
- [ ] **0001193125-13-325730:E0537** L1976-L1976 (date: May 8, 2013; terms: sent)
- [ ] **0001193125-13-325730:E0538** L1980-L1983 (date: January 1, 2009; actors: Merrill Lynch; terms: announced)
- [ ] **0001193125-13-325730:E0550** L2036-L2041 (date: may; actors: Merrill Lynch; value: $45; terms: received)

### Financial terms to capture
- [ ] **0001193125-13-325730:E0478** L1712-L1712 (value: $6.85 per share; terms: $6.85 per share)
- [ ] **0001193125-13-325730:E0531** L1918-L1919 (value: $0.25; terms: $0.25)
- [ ] **0001193125-13-325730:E0532** L1921-L1923 (value: $3.00 - $6.50; terms: $3.00 - $6.50, $3.25 - $8.50)
- [ ] **0001193125-13-325730:E0533** L1944-L1950 (actors: Merrill Lynch; value: $0.25; terms: $0.25)
- [ ] **0001193125-13-325730:E0535** L1952-L1954 (value: $4.75 - $9.75; terms: $4.75 - $9.75)
- [ ] **0001193125-13-325730:E0536** L1962-L1963 (value: $0.25; terms: $0.25)
- [ ] **0001193125-13-325730:E0541** L1995-L1998 (actors: Merrill Lynch; value: $3.59; terms: $0.25, $3.59)
- [ ] **0001193125-13-325730:E0543** L2000-L2002 (value: $4.75 - $5.50; terms: $4.00 - $4.00, $4.75 - $5.50)
- [ ] **0001193125-13-325730:E0547** L2025-L2028 (actors: Merrill Lynch; value: $4.3; terms: $250,000, $4.3)
- [ ] **0001193125-13-325730:E0551** L2036-L2041 (date: may; actors: Merrill Lynch; value: $45; terms: $45)

### Actors to identify
- [ ] **0001193125-13-325730:E0477** L1708-L1708 (terms: advisor, advisors)
- [ ] **0001193125-13-325730:E0485** L1735-L1738 (date: June 23, 2013; actors: Merrill Lynch; terms: advisor, financial advisor, shareholder)
- [ ] **0001193125-13-325730:E0486** L1740-L1740 (terms: shareholder)
- [ ] **0001193125-13-325730:E0488** L1744-L1744 (terms: shareholder)
- [ ] **0001193125-13-325730:E0492** L1753-L1753 (terms: shareholder)
- [ ] **0001193125-13-325730:E0493** L1755-L1757 (date: may; terms: shareholder)
- [ ] **0001193125-13-325730:E0497** L1765-L1767 (date: may; terms: party )
- [ ] **0001193125-13-325730:E0502** L1782-L1784 (date: may; terms: shareholder)
- [ ] **0001193125-13-325730:E0504** L1794-L1796 (terms: shareholder, special committee)
- [ ] **0001193125-13-325730:E0506** L1798-L1799 (terms: shareholder)
- [ ] **0001193125-13-325730:E0509** L1809-L1812 (actors: Merrill Lynch; terms: advisor, financial advisor, investment bank)
- [ ] **0001193125-13-325730:E0511** L1814-L1817 (date: June 23, 2013; actors: Merrill Lynch; terms: shareholder)
- [ ] **0001193125-13-325730:E0512** L1822-L1828 (actors: Merrill Lynch; terms: shareholder)
- [ ] **0001193125-13-325730:E0514** L1830-L1830 (actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0515** L1840-L1840 (actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0516** L1842-L1842 (actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0517** L1844-L1844 (actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0518** L1846-L1846 (actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0520** L1850-L1850 (actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0521** L1852-L1856 (actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0523** L1861-L1867 (date: may; actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0525** L1869-L1878 (actors: Merrill Lynch; terms: party , shareholder)
- [ ] **0001193125-13-325730:E0527** L1880-L1882 (date: may; actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0528** L1884-L1887 (actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0529** L1910-L1913 (date: June 21, 2013; actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0534** L1944-L1950 (actors: Merrill Lynch; value: $0.25)
- [ ] **0001193125-13-325730:E0539** L1980-L1983 (date: January 1, 2009; actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0542** L1995-L1998 (actors: Merrill Lynch; value: $3.59)
- [ ] **0001193125-13-325730:E0544** L2013-L2018 (date: may; actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0545** L2020-L2023 (actors: Merrill Lynch; terms: advisor, financial advisor)
- [ ] **0001193125-13-325730:E0548** L2025-L2028 (actors: Merrill Lynch; value: $4.3)
- [ ] **0001193125-13-325730:E0549** L2030-L2034 (actors: Merrill Lynch; terms: advisor, financial advisor)
- [ ] **0001193125-13-325730:E0552** L2036-L2041 (date: may; actors: Merrill Lynch; value: $45; terms: advisor, financial advisor, investment bank)

### Process signals to check
- [ ] **0001193125-13-325730:E0489** L1746-L1746 (terms: superior proposal)

### Outcome facts to verify
- [ ] **0001193125-13-325730:E0479** L1714-L1714 (terms: closing)
- [ ] **0001193125-13-325730:E0480** L1720-L1720 (terms: closing, merger agreement)
- [ ] **0001193125-13-325730:E0481** L1722-L1722 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0482** L1724-L1726 (date: February 28, 2014; terms: merger agreement)
- [ ] **0001193125-13-325730:E0483** L1733-L1733 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0487** L1742-L1742 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0490** L1746-L1746 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0491** L1748-L1748 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0494** L1755-L1757 (date: may; terms: merger agreement)
- [ ] **0001193125-13-325730:E0495** L1763-L1763 (terms: merger agreement, terminated)
- [ ] **0001193125-13-325730:E0498** L1765-L1767 (date: may; terms: merger agreement)
- [ ] **0001193125-13-325730:E0499** L1769-L1771 (date: may; terms: litigation)
- [ ] **0001193125-13-325730:E0500** L1776-L1776 (terms: closing, merger agreement)
- [ ] **0001193125-13-325730:E0501** L1780-L1780 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0503** L1786-L1789 (date: may; terms: merger agreement)
- [ ] **0001193125-13-325730:E0505** L1794-L1796 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0507** L1798-L1799 (terms: vote)
- [ ] **0001193125-13-325730:E0508** L1801-L1801 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0513** L1822-L1828 (actors: Merrill Lynch; terms: vote)
- [ ] **0001193125-13-325730:E0519** L1848-L1848 (date: June 23, 2013; terms: merger agreement)
- [ ] **0001193125-13-325730:E0524** L1861-L1867 (date: may; actors: Merrill Lynch; terms: executed, litigation, merger agreement)
- [ ] **0001193125-13-325730:E0526** L1869-L1878 (actors: Merrill Lynch; terms: merger agreement, vote)
- [ ] **0001193125-13-325730:E0530** L1910-L1913 (date: June 21, 2013; actors: Merrill Lynch; terms: closing)
- [ ] **0001193125-13-325730:E0540** L1980-L1983 (date: January 1, 2009; actors: Merrill Lynch; terms: closing)
- [ ] **0001193125-13-325730:E0546** L2020-L2023 (actors: Merrill Lynch; terms: merger agreement)
</evidence_checklist>

<task_instructions>
IMPORTANT: You MUST follow the quote-before-extract protocol.

Step 1 - QUOTE: Read the chronology blocks above. Copy every verbatim passage needed to support party, cohort, and observation extraction into the quotes array. Each quote needs a unique quote_id (Q001, Q002, ...), the source block_id, and the exact filing text.

Step 2 - EXTRACT: Return filing-literal structure only. Build:
- parties: named bidders, advisors, activists, target-side boards/entities, and aliases
- cohorts: unnamed bidder groups with exact_count, known members when explicit, and the observation that created the cohort
- observations: only the six v2 observation types (process, agreement, solicitation, proposal, status, outcome)

--- TEMPORAL ORDER CONSTRAINT ---
`requested_by_observation_id` links a proposal to the solicitation that prompted it.
RULE: The linked solicitation MUST have date <= proposal date.
If no solicitation occurred on or before the proposal date, set `requested_by_observation_id` to null.
Common mistake: linking all proposals to the final-round solicitation even when earlier proposals predate it. An unsolicited proposal MUST have null.
--- END TEMPORAL ORDER CONSTRAINT ---

--- OUTCOME ACTOR CONSTRAINT ---
When `outcome_kind` is `executed` or `restarted`, include the bidder or bidder-cohort in `subject_refs` or `counterparty_refs`.
If the summary names an actor like 'Buyer Group' or 'New Mountain Capital', their `party_id` MUST appear in the refs.
--- END OUTCOME ACTOR CONSTRAINT ---

Observation rules:
- Do not emit analyst rows, benchmark rows, dropout labels, bid labels, or other derived judgments.
- Keep every field filing-literal. If a structured field is ambiguous, set it to null or use the appropriate `other` escape hatch with a short detail string.
- Use quote_ids, never evidence_refs or inline anchor_text.
- Populate `recipient_refs` whenever the filing names invitees or gives a reusable cohort such as finalists, remaining bidders, or a named bidder set.
- Proposals must use bidder or bidder-cohort subject_refs.
- Preserve proposal-local formality clues when literal text supports them: `mentions_non_binding`, `includes_draft_merger_agreement`, and `includes_markup`.
- Keep agreement families distinct: `nda`, `amendment`, `standstill`, `exclusivity`, `clean_team`, and `merger_agreement` are not interchangeable.
- Solicitation observations should represent the request/announcement, with due_date when the filing gives a deadline.
- Status observations cover expressed interest, withdrawal, exclusion, cannot-improve, selected-to-advance, and similar literal process states.
- When the filing gives only a relative date, anchor it to the nearest explicit date in the same local context and preserve the resulting non-exact precision.

Return a single JSON object with keys in this order: quotes, parties, cohorts, observations, exclusions, coverage.
</task_instructions>