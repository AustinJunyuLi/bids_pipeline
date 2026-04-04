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
deal_slug: imprivata
target_name: IMPRIVATA INC
source_accession_number: 0001193125-16-677939
source_form_type: UNKNOWN
chunk_mode: single_pass
window_id: w0
</deal_context>

<chronology_blocks>
B001 [L1148-L1148]: Background of the Merger
B002 [L1150-L1151]: The following chronology summarizes the key meetings and events that led to the signing of the merger agreement. The following chronology does not purport to catalogue every conversation among the Board, the Special Committee (as defined below), members of Company management or the Companys representatives and other parties.
B003 [L1153-L1156]: The Board, together with Company management and with the assistance of the Companys advisors, periodically reviews and considers various strategic and other opportunities available to the Company to enhance stockholder value, taking into consideration the Companys performance, competitive dynamics, macroeconomic developments and industry trends. These reviews have included discussions as to whether the continued execution of the Companys strategy as a standalone company (including possible operational and capital structure changes) or the possible sale of the Company to, or combination of the Company with, a third party offered the best avenue to enhance stockholder value, and the potential benefits and risks of any such course of action.
B004 [L1158-L1158]: In
B005 [L1159-L1159]: June 2014, the Company completed the initial public offering of its common stock priced at $15.00 per share.
B006 [L1161-L1163]: In early 2015, and again in June 2015, representatives of Thoma Bravo informally approached and had brief meetings with representatives of the Company, and expressed Thoma Bravos potential interest in exploring a possible business transaction with the Company. The Company indicated that it was focused on executing on its business plan and taking steps to enhance stockholder value. No specific proposals were made during these meetings.
B007 [L1165-L1166]: From August 5, 2015 through October 22, 2015, private equity funds affiliated with Thoma Bravo acquired an aggregate of 1,213,066 shares of Imprivata common stock (representing less than 5% of the outstanding shares of Imprivata common stock) in open market purchases for an aggregate purchase price of approximately $17.4 million (inclusive of commissions).
B008 [L1168-L1168]: On August 11, 2015, the Company completed a secondary offering of its common stock priced at $15.00 per share.
B009 [L1170-L1171]: On October 14, 2015, the Company announced that third quarter 2015 financial results would disclose less revenue growth than the Company previously forecasted. On October 15, 2015, the Companys common stock price closed at $12.00, down from $17.31 or approximately 31% from the previous days close.
B010 [L1173-L1174]: On November 2, 2015, the Company announced its financial results for the third quarter. The Company also reduced its guidance for revenue and adjusted EBITDA for the fourth quarter 2015 and for the full year 2015. On November 3, 2015, the Companys common stock price closed at $9.42, down from $10.39 or approximately 9% from the previous days close.
B011 [L1176-L1177]: In January 2016, representatives of Thoma Bravo met with members of Company management during an industry conference and reiterated Thoma Bravos interest in a potential transaction with the Company. No specific proposal was made. Company management indicated that if Thoma Bravo were to make a proposal, it would be considered by the Board.
B012 [L1179-L1180]: On February 24, 2016, the Board held a meeting to discuss, among other things, the Companys operating and financial performance for 2015, managements 2016 budget and forecasts, and the risks, challenges and strategic opportunities facing the Company in 2016, including its planned emphasis on the OneSign and Confirm
B013 [L1182-L1182]: 26
B014 [L1185-L1185]: ID products, the volume of the sales pipeline for the Companys Cortext and PatientSecure products and the potential impact of this on bookings and revenue.
B015 [L1187-L1190]: On March 9, 2016, Thoma Bravo sent an unsolicited, non-binding indication of interest letter addressed to the Board indicating that Thoma Bravo would be interested in acquiring the Company for cash at a purchase price of $15.00 per share of Imprivatas common stock. The letter also indicated that Thoma Bravo had conducted extensive diligence based on the Companys public filings, that it was prepared to finance the transaction entirely with equity from its private equity funds, and that it could complete its confirmatory diligence and execute a definitive merger agreement in 30 days or less. On March 9, 2016, the closing price of Imprivatas common stock was $11.64.
B016 [L1192-L1201]: On March 10, 2016, the Board held a meeting to consider, among other things, Thoma Bravos indication of interest. Members of Company management, Chip Linnemann, a consultant to the Company, and representatives of the Companys outside legal counsel, Goodwin Procter LLP (Goodwin), were in attendance. Representatives of Goodwin discussed with the Board their fiduciary duties in the context of evaluating Thoma Bravos indication of interest. Goodwin also discussed the Boards discretion in determining whether and how to pursue any transaction and additional considerations regarding a possible transaction with a financial sponsor. The Board engaged in a preliminary discussion of the terms of Thoma Bravos indication of interest. The Board concluded that it should defer consideration of Thoma Bravos indication of interest and any response thereto until the Board had further considered the Companys short- and long-term business strategies and the Companys intrinsic value. The Board requested that Company management review its financial forecasts and assumptions and prepare a long-term operating plan for presentation to the Board for its consideration in evaluating Thoma Bravos indication of interest and potential responses of the Board to this indication of interest. The Board also discussed the advisability of engaging a financial advisor to assist the Board in fulfilling its fiduciary duties in evaluating Thoma Bravos indication of interest and the Companys future prospects. Following discussion, the Board authorized an informal advisory committee of directors consisting of Omar Hussain, Rodger Weismann, Jack Blaeser and Paul Maeder to recommend to the Board a financial advisor to assist the Board in considering Thoma Bravos indication of interest and to negotiate the terms of an engagement letter with such financial advisor. The Board also authorized the Companys chief executive officer to inform Thoma Bravo that the Board was evaluating the indication of interest and would respond in due course.
B017 [L1203-L1204]: On March 11, 2016, the Companys chief executive officer telephoned a representative of Thoma Bravo and informed him that the Board was evaluating Thoma Bravos indication of interest and would respond in due course.
B018 [L1206-L1210]: On March 14 and March 24, 2016, the advisory committee met to discuss and consider the engagement of a financial advisor, as authorized at the March 10, 2016 Board meeting. The advisory committee authorized Company management to inquire whether Barclays would be available to act as a financial advisor to the Company in connection with a potential strategic transaction. The advisory committee considered Barclays as a potential investment banking firm candidate to assist and advise the Board because of Barclays qualifications, expertise and reputation, its knowledge of and involvement in recent transactions in the Companys industry, its knowledge of the Companys business and affairs and its understanding of the Companys business based on its long-standing relationship with the Company, including serving as an underwriter in the Companys secondary offering in 2015.
B019 [L1212-L1215]: On April 7, 2016, the Board held a meeting to discuss, among other things, Company managements long-term plan, which was provided to the Board in advance of the meeting. Members of Company management, Mr. Linnemann and representatives of Goodwin were in attendance. Company management presented the Companys updated long-term financial forecasts for the five year period of 2016 through 2020 and underlying assumptions, noting that the 2016 forecasts had been updated since the February 24, 2016 Board meeting to take into account the volume of the Companys current sales pipeline and the expectation for its existing sales team (as more fully described below under the caption  Certain Prospective Financial Information). The Board
B020 [L1217-L1217]: 27
B021 [L1220-L1224]: discussed the risks, challenges and strategic opportunities facing the Company in the context of the long-term plan, including the challenges faced by the Company in growing bookings and revenue, the execution risks associated with closing large deals at the end of each the quarter (as was experienced in the third quarter of 2015), the growth of the Companys new product offerings and the significant competition for business in the secure texting market. The Board also discussed the risk that given the current volume of the Companys sales pipeline and its dependence on sales of its OneSign product each quarter, and given the performance expectations for the existing sales team that the Company could again experience lower than expected revenue in one or more near term financial quarters as it had in the third quarter of 2015. Following discussion and extensive questions of management on the assumptions on which the plan was based, the Board approved the strategic plan. Representatives of Goodwin again reviewed the Boards fiduciary duties in context of evaluating Thoma Bravos indication of interest.
B022 [L1226-L1234]: On April 15, 2016, the Board held a meeting to discuss, among other things, the engagement of a financial advisor and Thoma Bravos indication of interest. Members of Company management, Mr. Linnemann and representatives of Goodwin were in attendance. The advisory committee discussed with the Board its work since the March 10, 2016 Board meeting regarding evaluating potential financial advisors and recommended the engagement of Barclays as the Companys financial advisor to assist the Board in its evaluation of Thoma Bravos indication of interest and any other strategic alternatives that might be available to the Company. As part of this discussion, the advisory committee outlined the material terms of the proposed engagement of Barclays. Goodwin discussed with the Board the due diligence process that was conducted as to any relationships that Barclays had with Thoma Bravo. Goodwin noted that Barclays carried out its customary procedures and that Barclays had disclosed that since 2013 Barclays had received investment banking fees of approximately $12 million to $13 million from Thoma Bravo and certain of its portfolio companies and affiliates and that Barclays M& A deal team members assigned to work for the Company agreed not to work for Thoma Bravo or its affiliates during the term of Barclays engagement with the Company (other than one Barclays industry focused managing director who was working on a concurrent and unrelated assignment for Thoma Bravo). Following review of this information, the Board determined, based in part on the advice of Goodwin, that based on the information provided by Barclays, these relationships would not impair the advice Barclays would provide to the Board, or its independence. The Board engaged Barclays as the Companys financial advisor to assist the Board in its evaluation of Thoma Bravos indication of interest, subject to execution of a mutually satisfactory engagement letter.
B023 [L1236-L1239]: Barclays joined the remainder of the meeting and discussed with the Board the long-term plan that was approved by the Board at the April 7, 2016 Board meeting, and then discussed preliminary valuation analyses, including a discounted cash flow analysis, with respect to the Company based on these financial forecasts. Representatives of Barclays also gave their preliminary views on the Companys general strategic position, potential responses to Thoma Bravos preliminary indication of interest, and the various strategies and methods by which the Board might seek to maximize stockholder value in the event the Board chose to explore a sale or other strategic transaction.
B024 [L1241-L1245]: The Board then considered Thoma Bravos indication of interest in light of the Companys business strategies and prospects as a standalone business, the competitive landscape and market trends in the industry, and the challenges confronting the Company in achieving its strategic objectives, including those discussed at the April 7, 2016 Board meeting. In light of this discussion, the Board concluded that it should further review Thoma Bravos indication of interest in the context of the Companys long-term plan and possible interest from other potential interested parties. While the Board determined to further evaluate Thoma Bravos indication of interest, it concluded as a preliminary matter that it undervalued the Company. The Board also requested that Barclays assemble a list of other parties that would likely be interested in a business combination transaction involving the Company.
B025 [L1247-L1247]: On
B026 [L1248-L1248]: April 19, 2016, the Company countersigned an engagement letter with Barclays, dated April 15, 2016, as authorized during the April 15, 2016 Board meeting.
B027 [L1250-L1250]: 28
B028 [L1253-L1262]: On April 28, 2016, the Board held a meeting to discuss, among other things, actions to be taken in response to Thoma Bravos indication of interest. Members of Company management, Mr. Linnemann and representatives of Barclays and Goodwin were in attendance. Company management updated the Board on the Companys preliminary first quarter results and managements financial forecast for the second quarter and remainder of the year. Representatives of Barclays reviewed with the Board an indicative list of parties which Barclays believed would be potentially interested in pursuing a business combination transaction involving the Company, including 11 strategic companies and four financial sponsors, including Thoma Bravo. These parties were selected based on their experience and interest in the security and/or healthcare technology and information services industries and likely capability to execute and finance such a transaction on an expeditious basis. The Board discussed the potential risks and benefits of commencing a process in which parties would be invited to review confidential information and submit indications of interest with respect to a potential business combination involving the Company. In particular, the Board discussed the potential disruptions to the Companys business during a protracted process, the risk of leaks that might arise from contacting other parties, and the potential impact of such leaks on the Companys business, including the potential loss of customers and employees. The Board also discussed the potential need to disclose during such process proprietary and confidential information to competitors and potential competitors. The Board concluded that these factors supported not adding additional parties at the outset of any process beyond the 15 parties previously discussed at the meeting. Following this discussion, the Board directed Barclays to refine an overall timetable for conducting such a process, and an overview of the materials that would be provided to bidders and at what stages, and other related matters.
B029 [L1264-L1271]: On May 5, 2016, the Board held a meeting. Members of Company management, Mr. Linnemann and representatives of Barclays and Goodwin were in attendance. Representatives of Barclays again reviewed with the Board the list of 15 parties that had been discussed at the previous Board meeting. The Board again discussed the potential risks and benefits of commencing a process in which parties would be invited to review confidential information and submit indications of interest with respect to a potential business combination involving the Company. Based on the benefits and risks discussed at this meeting and the previous Board meeting, the Board determined, based on their knowledge of the industry and the Company, the preliminary observations of Barclays, the strategic alternatives potentially available to the Company, including remaining as an independent public company, and the indication of interest received from Thoma Bravo, that it was in the best interests of the Company and its stockholders to take steps to further explore a potential business combination transaction involving the Company. The Board also approved the indicative list of parties and determined that Barclays should contact each of the parties on the indicative list on a confidential basis to gauge its interest in a potential transaction with the Company, which we refer to as the strategic process. Barclays then discussed with the Board its views on the overall timetable for the strategic process, the materials that would be provided to bidders and at what stages, and other related matters.
B030 [L1273-L1278]: During the period from May 6 through June 9, 2016, at the direction of the Board, Barclays contacted and had discussions with the 15 potentially interested parties discussed by the Board at its April 28 and May 5, 2016 meetings, including Thoma Bravo. Of the parties contacted, three strategic parties and four financial sponsors executed confidentiality agreements with the Company, including Thoma Bravo on May 10, 2016. All standstill obligations under the confidentiality agreements automatically terminated upon the Companys entry into the merger agreement with Thoma Bravo. Except for one financial sponsor that declined interest shortly after executing its confidentiality agreement, each party that entered into a confidentiality agreement attended a high-level management presentation conducted by members of Company management and attended by Barclays. These parties included a telecommunications enterprise company (Strategic 1), two large software companies (Strategic 2 and Strategic 3) and three financial sponsors (Sponsor A, Sponsor B and Thoma Bravo).
B031 [L1280-L1282]: On May 12, 2016, following the Companys annual stockholders meeting, the Board held a meeting to receive an update on the strategic process. Members of Company management, Mr. Linnemann and representatives of Barclays and Goodwin were in attendance. Barclays provided an update on the developments related to the strategic process, including its discussions to date with the strategic and financial parties, the
B032 [L1284-L1284]: 29
B033 [L1287-L1287]: proposed timetable for following up with these parties and conducting high-level management presentations with interested parties, and the perceived level of interest among these parties.
B034 [L1289-L1291]: On May 26, 2016, the Board held a meeting. Members of Company management, Mr. Linnemann and representatives of Barclays and Goodwin were in attendance. Barclays provided an update on the developments related to the strategic process since the last Board meeting, including the status of high-level management presentations and the level of interest among potential bidders. The Board then approved requesting initial non-binding indications of interest from bidders by June 9, 2016.
B035 [L1293-L1294]: On June 1, 2016, the Company announced that its senior vice president for worldwide sales would depart from the Company on August 5, 2016 to pursue other opportunities.
B036 [L1296-L1300]: On June 3, 2016, Barclays distributed a bid instruction letter on behalf of the Company to the six parties that had executed a confidentiality agreement and attended meetings with Company management by that date. The letter indicated a deadline for submitting indications of interest by June 9, 2016 and that any bidders invited to participate in a second phase of bidding would receive further access to management and more extensive diligence access. Bidders were requested to specify a per share offer price for the Company, sources of financing, a description of the future plans for the Company, the information they would need to complete due diligence and their proposed structure for a transaction. Concurrently with the bid instruction letter, Barclays distributed to the same six parties a subset of the financial information contained in the Companys long-range plan, which was materially consistent with the long-range approved by the Board on April 7, 2016 (as more fully described below under the caption  Certain Prospective Financial Information).
B037 [L1302-L1303]: On June 3, 2016, one of the strategic parties contacted by Barclays, but that did not execute a confidentiality agreement or receive a bid process letter, informed Barclays that it was not interested in participating in the strategic process.
B038 [L1305-L1307]: On June 8, 2016, Strategic 1 informed Barclays that after further internal consideration, an acquisition of the Company would not be a strategic fit for it, and therefore it was no longer interested in participating in the strategic process and would not be submitting an indication of interest.
B039 [L1309-L1312]: On June 9, 2016, three parties (Sponsor A, Sponsor B and Thoma Bravo) presented written preliminary non-binding indications of interest that were each subject to satisfactory completion of due diligence, among other conditions. Each of these indications provided for equity commitments from fund sponsors for the entire purchase price and none of these indications of interest were contingent on financing. Sponsor A indicated a price of $16.50 per share. Thoma Bravo indicated a price of $17.25 per share, and also provided a form of equity commitment letter and draft merger agreement. Sponsor B indicated a range of $17.00 - $18.00 per share. On June 9, 2016, the closing price of Imprivatas common stock was $13.46.
B040 [L1314-L1315]: On June 11, 2016, one of the strategic parties contacted by Barclays, but that did not execute a confidentiality agreement or receive a bid process letter, informed Barclays that it did not have a strategic interest in an acquisition of the Company and it would not be participating in the strategic process.
B041 [L1317-L1318]: On June 11, 2016, Strategic 3 informed representatives of Barclays, that it was still evaluating its interest in a potential transaction with the Company and that it would follow up with Barclays early in the following week.
B042 [L1320-L1321]: On June 12, 2016, Strategic 2 informed representatives of Barclays that because of other internal corporate priorities, it was no longer interested in exploring a potential transaction with the Company.
B043 [L1323-L1324]: On June 12, 2016, the Board held a meeting to receive an update on the strategic process. Members of Company management, Mr. Linnemann and representatives of Barclays and Goodwin were in attendance. The Board, with the assistance of Barclays, discussed the three preliminary indications of interest received on June 9,
B044 [L1326-L1326]: 30
B045 [L1329-L1333]: 2016. Barclays also reviewed with the Board preliminary financial information with respect to each of the three indications of interest and preliminary valuation analyses with respect to the Company based on the Companys long-term plan approved by the Board on April 7, 2016. Barclays reported to the Board that at such time ten of the 11 strategic parties contacted by Barclays had declined to participate in the strategic process, and that while Strategic 3 had executed a confidentiality agreement and met with management, it did not submit a bid by the June 9, 2016 deadline. Representatives of Goodwin reviewed with the Board its fiduciary duties in the context of evaluating the preliminary indications of interest in the context of a possible sale of the Company. Representatives of Goodwin also discussed the Boards discretion in determining whether and how to pursue a transaction and potential additional considerations in a transaction with a financial sponsor, including potentially forming a special committee of the Board consisting solely of independent and disinterested directors.
B046 [L1335-L1342]: Although the Board believed that the preliminary indications of interest received on June 9, 2016 were in a range that would provide substantial value to the Companys stockholders, the Board discussed how best to further enhance stockholder value through the next phase of the strategic process and other potential strategic alternatives involving the Company. Following these discussions, because Sponsor A, Sponsor B and Thoma Bravo had submitted proposals within close range of each other, the Board authorized Barclays to advance all three parties to the second phase of the strategic process and to encourage them to indicate a willingness to increase their respective offer prices. In an effort to attempt to have strategic parties involved in the process, the Board also directed Barclays to contact Strategic 3 and encourage it to continue to participate in the process and to submit a proposal. The Board also discussed that although there were no known actual conflicts at the time, because of the potential for management conflicts of interest to arise in the context of a potential sale to a financial sponsor, the Board would form a special committee of independent and disinterested directors that would direct the strategic process on behalf of the Board. The Board authorized Goodwin, with the assistance of the Companys general counsel, to interview each of the independent directors regarding any potential conflicts of interest on the part of each director regarding Sponsor A, Sponsor B and Thoma Bravo and in serving on a special committee of the Board to oversee the strategic process.
B047 [L1344-L1345]: On June 13, 2016, representatives of Barclays contacted Sponsor A and indicated that its June 9 bid was on the low end and that in order for Sponsor A to continue in the strategic process, it would need to materially increase its offer price. Sponsor A indicated that it would consider whether or not it could do so.
B048 [L1347-L1348]: On June 14, 2016, Strategic 3 informed representatives of Barclays that because of its internal focus on other corporate transactions and a perceived overlap in technologies, it was no longer interested in exploring a potential transaction with the Company.
B049 [L1350-L1353]: On June 15, 2016, Sponsor A informed Barclays that in light of its view of the Company after its diligence, if it were to submit a second round bid, it would not be meaningfully higher than the price indicated in its June 9, 2016 preliminary indication of interest, and inquired whether it should continue in the strategic process. Barclays informed Sponsor A that it did not believe that the Board would be interested in a transaction at a valuation at essentially the same level as Sponsor As previous indication of interest, and that Barclays would inform Sponsor A if the Board determined otherwise. Following this discussion there were no further discussions between Sponsor A and Barclays or any other Company representatives.
B050 [L1355-L1359]: On June 17, 2016, the Board held a meeting to discuss the formation of a special committee of the Board. Members of Company management, Mr. Linnemann and representatives of Goodwin were in attendance. Goodwin reported to the Board that with the assistance of the Companys general counsel, it had separately interviewed each of the independent directors since the last Board meeting regarding any potential conflicts of interest on the part of each director regarding Sponsor A, Sponsor B and Thoma Bravo, and in serving on a special committee of the Board to oversee the strategic process, and none were identified. Following this discussion, the Board established a special committee of the Board (the Special Committee) that included only independent and disinterested directors. The Special Committee was authorized to consider and evaluate the indications of interest received on June 9, 2016, and any other proposals that might be received by the Company,
B051 [L1361-L1361]: 31
B052 [L1364-L1366]: participate in and direct the negotiation of the material terms and conditions of any such transaction or any alternatives to such transactions, including the Company continuing to operate as an independent company, and recommend to the Board the advisability of entering into any such transaction or pursuing another alternative. The Special Committee consisted of all of the non-management directors on the Board, which were David Barrett, Paul Maeder, Kate Walsh, Jack Blaeser, Dr. John Halamka and Rodger Weismann.
B053 [L1368-L1373]: On June 17, 2016, following the Board meeting, the Special Committee met. Mr. Linnemann and representatives of Goodwin were in attendance. Representatives of Goodwin reviewed with the Special Committee disclosures related to relationships between each of Sponsor A, Sponsor B, Thoma Bravo and Strategic 3, and Barclays, provided by Barclays to Goodwin prior to the meeting and noted that Barclays carried out its customary procedures to provide this information. The Special Committee determined, based in part on the advice of Goodwin, those relationships would not impair the advice Barclays would provide to the Special Committee and the Board, or its independence. The Special Committee elected Ms. Walsh as its Chairperson, whom we refer to in such capacity as the Chairperson. Based on Mr. Linnemanns qualifications and experience regarding corporate strategic review processes and extensive knowledge of the Company, and to streamline and facilitate communications among the members of the Special Committee and between the Special Committee and Barclays, the Special Committee designated Mr. Linnemann to work with the Chairperson and act as a liaison between the Special Committee and Barclays.
B054 [L1375-L1384]: Barclays then joined the meeting and updated the Special Committee on its recent discussions with the strategic and financial parties since the June 9, 2016 bid deadline. Barclays noted that that both Strategic 2 and Strategic 3 had declined to participate further in the strategic process. The Special Committee directed Barclays to contact an additional strategic party, an enterprise software company (Strategic 4), to determine whether it might have interest in submitting an indication of interest. Barclays reported that, consistent with the direction from the Board, Barclays had informed each of Sponsor A, Sponsor B and Thoma Bravo that the Board was seeking improved bids from each of them. Barclays reported that in these discussions Sponsor A said that it would not be in a position to meaningfully improve upon its initial bid, and that in light of the foregoing Sponsor A was going to cease participating in the strategic process unless subsequently contacted by Barclays at the direction of the Board. The Special Committee confirmed that it was not interested in pursuing a transaction at the price indicated by Sponsor A in its initial bid. Barclays also reported to the Special Committee that it had communicated to each of Sponsor B and Thoma Bravo that the Board had requested improved bids from each of them. Barclays discussed the expected timetable for Sponsor B and Thoma Bravo to conduct confirmatory diligence, receive second round management presentations and submit acquisition proposals in the second phase of the strategic process. The Special Committee also discussed the role of Company management in the strategic process, and approved guidelines that Company management would be required to follow during the strategic process, including requirements to, except as otherwise instructed by the Special Committee, not engage in discussions regarding any compensation, retention or investment arrangements with bidders and not to favor any one bidder over other bidders. After the meeting, a document summarizing these guidelines was provided to members of Company management.
B055 [L1386-L1387]: On June 17, 2016, representatives of Barclays contacted representatives of Strategic 4 to inquire whether it would be interested in participating in the Companys strategic process.
B056 [L1389-L1390]: On June 17, 2016, Sponsor B and Thoma Bravo were provided access to an online data room containing nonpublic information regarding the Company.
B057 [L1392-L1393]: On June 23, 2016, Strategic 4 informed Barclays that an acquisition of the Company would not be a strategic fit for it and that it was not interested in participating in the strategic process.
B058 [L1395-L1396]: On June 24, 2016, the Chairperson of the Special Committee met informally with Mr. Linnemann and representatives of Barclays and Goodwin. Barclays provided an update on the strategic process since the last
B059 [L1398-L1398]: 32
B060 [L1401-L1402]: Special Committee meeting and its recommendations regarding the timetable for receiving final bids from Sponsor B and Thoma Bravo. The Chairperson approved Barclays to set a final bid deadline of July 8, 2016.
B061 [L1404-L1405]: Later on June 24, 2016, Barclays sent final bid process letters to Sponsor B and Thoma Bravo, requesting marked drafts of the Companys proposed form of merger agreement (which would be provided in due course) by July 7, 2016, and setting a final bid deadline of July 8, 2016.
B062 [L1407-L1408]: On June 27, 2016, members of Company management conducted a detailed management presentation with representatives of Sponsor B that was also attended by Barclays.
B063 [L1410-L1412]: Also on June 27, 2016, with the permission of the Special Committee members of Company management and representatives of Barclays met over dinner with representatives of Thoma Bravo to discuss the Companys business. The parties did not discuss Company management roles, compensation, retention or investment arrangements in connection with the proposed transaction. A dinner with Company management and representatives of Barclays to discuss the Companys business was also offered to Sponsor B. Sponsor B declined the offer.
B064 [L1414-L1415]: On June 28, 2016, members of Company management conducted a detailed management presentation with representatives of Thoma Bravo that was also attended by Barclays.
B065 [L1417-L1418]: From June 28 through July 7, 2016, members of Company management and representatives of Barclays and Goodwin conducted follow-up telephonic diligence sessions with Thoma Bravo and its advisors.
B066 [L1420-L1423]: On June 29, 2016, Sponsor B informed Barclays that in light of its revised views on the Companys growth outlook, if it were to submit a final bid, it would be significantly below the price indicated in its June 9, 2016 preliminary indication of interest, and inquired whether it should continue its diligence efforts. Barclays informed Sponsor B that it did not believe that the Special Committee would be interested in a transaction at a valuation significantly lower than Sponsor Bs previous indication of interest, and that Barclays would inform Sponsor B if the Special Committee determined otherwise. Following this discussion there were no further discussions between Sponsor B and Barclays or any other Company representatives.
B067 [L1425-L1430]: On June 30, 2016, the Special Committee held a meeting to receive an update on the strategic process. Mr. Linnemann and representatives of Barclays and Goodwin were in attendance. Representatives of Barclays informed the Special Committee of the conversation Barclays had with Sponsor B, in particular that Sponsor B had stated that its final bid, if it were to submit one, would be significantly lower that its previous indication of interest. The Special Committee determined that it would not be in the best interest of the Companys stockholders to pursue a proposal at price significantly below the price that Sponsor B originally indicated that it would be able to offer. Barclays also noted that Strategic 4 had declined interest. The Special Committee discussed with the representatives of Barclays and Goodwin the potential next steps that should be taken with Thoma Bravo from the present date until the final bid deadline of July 8, 2016. The Special Committee also discussed the need for transaction certainty and speed in light of potential leaks and the continued volatility in the financial markets.
B068 [L1432-L1433]: On June 30, 2016, the Companys chief executive officer informally updated the Board regarding the Companys preliminary operating results for the Companys 2016 second quarter performance, which indicated that the Company appeared to have exceeded its financial forecasts for the 2016 second quarter.
B069 [L1435-L1435]: On July 1, 2016, the Companys proposed form of merger agreement and voting agreement was made available to Thoma Bravo.
B070 [L1437-L1438]: On July 5 and 6, 2016, in response to Thoma Bravos request to work with potential debt financing sources, the Company permitted two sources of potential debt financing, each of which Barclays identified as parties that
B071 [L1440-L1440]: 33
B072 [L1443-L1443]: could potentially provide debt financing to Thoma Bravo, to join as parties under the confidentiality agreement between the Company and Thoma Bravo.
B073 [L1445-L1447]: On July 6, 2016, representatives of Barclays had a discussion with representatives of Thoma Bravo to discuss the progress of Thoma Bravos second round bid. Thoma Bravo requested to have a discussion with the Companys chief executive officer prior to submission of its second round bid. Following discussion with representatives of Goodwin and the Chairperson of the Special Committee, Barclays informed Thoma Bravo that the Special Committee would not permit the Companys chief executive officer to have the requested discussion with Thoma Bravo prior to the submission of its second round bid.
B074 [L1449-L1450]: On July 7, 2016, Thoma Bravos outside counsel, Kirkland & Ellis LLP (Kirkland) sent a revised draft of the merger agreement to Goodwin.
B075 [L1452-L1454]: On July 7, 2016, representatives of Thoma Bravo had a telephonic discussion with the Companys chief financial officer and representatives of Barclays regarding the Companys preliminary second quarter 2016 financial results, which updated certain financial information about the Company that was provided to Thoma Bravo on June 3, 2016 (see  Certain Prospective Financial Information on page 49 of this proxy statement for further detail).
B076 [L1456-L1456]: On
B077 [L1457-L1458]: July 7, 2016, the Special Committee met with Company management to discuss the Companys recently completed quarter and future financial outlook. Representatives of Goodwin were in attendance. Management made a presentation to the Special Committee on the Companys preliminary second quarter 2016 financial results and forecasts for the third quarter and remainder of 2016 and answered numerous questions on the Companys business and future prospects and the associated risks.
B078 [L1460-L1463]: On July 8, 2016, the date by which Sponsor B and Thoma Bravo had been invited to submit their final bids, only Thoma Bravo submitted a bid for the Company. Thoma Bravos bid was at a price of $19.00 per share in cash, provided for an equity commitment for the entire purchase price and indicated that Thoma Bravo had completed all of its due diligence and was prepared to execute its revised draft of the merger agreement and announce the transaction prior to the market open on July 11, 2016. Representatives of Barclays engaged in discussions with representatives of Thoma Bravo in order to obtain additional information regarding the terms of, and conditions to, its indication of interest.
B079 [L1465-L1467]: On July 8, 2016, the Special Committee held a meeting to discuss Thoma Bravos $19.00 per share offer. Mr. Linnemann and representatives of Barclays and Goodwin were in attendance. Representatives of Barclays reviewed preliminary financial information with respect to the offer. Representatives of Barclays also reviewed with the Board the outcome of the discussions with the other parties that had been approached.
B080 [L1469-L1475]: The representatives of Barclays then left the meeting and the Special Committee discussed the $19.00 per share offer in the context of the Companys strategic alternatives, including continuing as a standalone company. The Special Committee discussed the advantages and risks of the proposed transaction that are described in  Reasons for the Merger  Special Committee beginning on page 37 of this proxy statement, including, among other things, whether the offer price of $19.00 per share represented an attractive valuation of the Company for stockholders when considered in light of the Special Committees knowledge and understanding of the business, operations, management, financial condition and prospects of the Company, including the various challenges presented if the Special Committee were to reject the offer and the Company were to continue as a standalone company, including that the Company would need to secure a replacement for its senior vice president of worldwide sales position. The Special Committee also discussed that to date, Thoma Bravo had no, and had not requested to have, discussions with Company management regarding their roles, compensation, retention or investment arrangements in connection with the proposed transaction. The Special Committee discussed that Thoma Bravos offer provided for equity financing for the entire acquisition of the Company and that its offer was not conditioned on any retention or participation by Company management. Representatives of Goodwin
B081 [L1477-L1477]: 34
B082 [L1480-L1481]: reviewed with the Special Committee the key terms in Thoma Bravos revised draft of the merger agreement and the Special Committee instructed Goodwin to obtain as much certainty of closing though the terms of the merger agreement and related agreements as was possible in negotiating with Thoma Bravo and its representatives.
B083 [L1483-L1487]: Based on the discussion at this meeting and the earlier Special Committee discussions, the Special Committee concluded that the $19.00 per share offer would, if consummated, provide greater certainty of value (and less risk) to the Companys stockholders relative to the potential trading price of the Company shares over a longer period after accounting for the long-term risks to the Companys business resulting from operational execution risk and evolving industry dynamics. After considering the Companys strategic alternatives to the Thoma Bravo transaction and the Companys ability to continue as a standalone company, the Special Committee directed its advisors to continue discussions with Thoma Bravo and to seek a further price increase and other improved terms from Thoma Bravo, and concluded that Barclays should contact Thoma Bravo to indicate that the Special Committee believed that Thoma Bravos July 8, 2016 offer could still be improved upon.
B084 [L1489-L1489]: On
B085 [L1490-L1493]: July 9, 2016, representatives of Barclays contacted representatives of Thoma Bravo and informed Thoma Bravo that it should submit its best and final offer, which Barclays said the Special Committee expected would be an improvement over Thoma Bravos $19.00 bid. Representatives of Barclays also inquired as to whether Thoma Bravo would require a discussion with the Companys chief executive officer prior to the execution of the merger agreement and related agreements. Thoma Bravo indicated that it would consider a revised offer, and that while it would like to have such a discussion with the Companys chief executive officer prior to executing the merger agreement with the Company, it was not a requirement for Thoma Bravo.
B086 [L1495-L1498]: Later on July 9, 2016, Barclays received a revised written, non-binding proposal from Thoma Bravo setting forth its best and final offer of $19.25 per share, together with a revised draft of the equity commitment letter for the entire purchase price for the Company. The revised offer indicated that Thoma Bravo desired to execute the definitive merger agreement and announce the transaction prior to market open on July 11, 2016. Representatives of Barclays engaged in discussions with representatives of Thoma Bravo in order to obtain additional information regarding the terms of, and conditions to, its proposal. In those discussions, Thoma Bravo made it clear that $19.25 per share was its best and final offer.
B087 [L1500-L1505]: On July 10, 2016, representatives of Goodwin and Kirkland negotiated open items in the merger agreement, voting agreement and equity commitment letter. From that day through the execution of the merger agreement on July 13, 2016, representatives of Goodwin and Kirkland engaged in discussions regarding the terms of the draft merger agreement, voting agreement and equity commitment letter. The key issues negotiated in the draft merger agreement and related agreements included the scope of the representations and warranties, the Companys obligations to cooperate with Thoma Bravos debt financing efforts, the rights of the parties to terminate the transaction and related remedies, the limitation on Thoma Bravos liability for monetary damages in connection with the proposed acquisition of the Company, the Company being a named third party beneficiary under the equity commitment letter, the terms under which the Company could respond to unsolicited proposals, and the amount and conditions of payment by the Company of the termination fee, and the terms of and the parties to be subject to voting agreements requested by Thoma Bravo.
B088 [L1507-L1511]: On July 10, 2016, the Special Committee met to discuss Thoma Bravos increased $19.25 per share offer. Representatives of Barclays and Goodwin were in attendance. Representatives of Barclays updated the Special Committee on the discussions with Thoma Bravo since the last Special Committee meeting. Representatives of Goodwin reviewed with the Special Committee the terms of the draft merger agreement, voting agreement and equity commitment letter, including the open items being negotiated with Thoma Bravo. Representatives of Barclays reviewed preliminary financial information with respect to the $19.25 per share offer, advising the Special Committee that Thoma Bravo indicated this was its best and final offer and that Thoma Bravo was prepared to move expeditiously to negotiate and sign a definitive agreement. The Special Committee also discussed the increased risk of leaks if the negotiations with Thoma Bravo were to be prolonged. Based on the
B089 [L1513-L1513]: 35
B090 [L1516-L1518]: discussion at this meeting and the earlier Special Committee discussions, after considering the Companys lack of strategic alternatives to the Thoma Bravo transaction and the challenges facing the Company in achieving its strategic objectives, the Special Committee directed the Company and its advisors to proceed toward the execution of a definitive agreement with Thoma Bravo expeditiously. The Special Committee also instructed Barclays to arrange a call between representatives of Thoma Bravo and the Companys chief executive officer, with Mr. Linnemann present on behalf of the Special Committee.
B091 [L1520-L1521]: During the remainder of July 10, 2016 through the announcement of the execution of the merger agreement on July 13, 2016, representatives of Barclays and Goodwin, and Thoma Bravo and Kirkland, had various telephonic discussions to finalize the merger agreement and related agreements.
B092 [L1523-L1525]: On July 11, 2016, as authorized by the Special Committee, the Companys chief executive officer, with Mr. Linnemann present on behalf of the Special Committee, had a telephone call with representatives of Thoma Bravo in which they reviewed certain high-level confirmatory diligence questions regarding the Companys expected second quarter 2016 financial results and forecasts for the remainder of the year and prospects for the Companys business. In this discussion, no specific terms or conditions of employment regarding Company management, including potential compensation or retention, were discussed.
B093 [L1527-L1528]: On July 11, 2016, Kirkland sent Goodwin a draft of an exclusivity agreement, with an exclusivity term extending through July 13, 2016. Following discussion with the Chairperson of the Special Committee, Goodwin informed Kirkland that the Company would not enter into an exclusivity agreement.
B094 [L1530-L1533]: Also on July 11, 2016, Kirkland requested through Goodwin that the Company contact and enter into a confidentiality agreement with a large stockholder of the Company who was not aware of the potential transaction and request that it execute a voting agreement concurrently with the execution of the merger agreement. Following discussion with the Chairperson of the Special Committee, Goodwin informed Kirkland that the Company would not agree to contact such stockholder prior to the execution of the merger agreement, but that the Company would agree to contact such person promptly after the execution of the merger agreement and request that they execute a voting agreement.
B095 [L1535-L1540]: On July 12, 2016, after the stock market closed, the Special Committee held a meeting to discuss the final terms of the proposed transaction. Mr. Linnemann and representatives of Barclays and Goodwin were in attendance. Representatives of Goodwin reviewed the fiduciary duties of the Special Committee in connection with a potential sale of the Company. Representatives of Goodwin provided an overview of the negotiation process to date with Thoma Bravos representatives, as well as a presentation regarding the terms of the merger agreement and related agreements. Representatives of Goodwin discussed with the Special Committee the discussion between the Companys chief executive officer and representatives of Thoma Bravo the previous day. The Special Committee also reviewed certain financial projections regarding the Company for the fiscal years 2016-2020 prepared by Company management, which were materially consistent with the operating model that Company management had prepared and provided to the Board on April 7, 2016 (see  Certain Prospective Financial Information on page 49 of this proxy statement for further detail).
B096 [L1542-L1542]: Barclays
B097 [L1543-L1547]: reviewed its financial analyses of the $19.25 per share cash consideration with the Special Committee. Barclays then delivered its oral opinion (which was subsequently confirmed in writing to the Board) to the effect that, as of such date and based upon and subject to the qualifications, limitations and assumptions to be set forth in its written opinion, from a financial point of view, the $19.25 per share cash consideration to be offered to the holders of shares of common stock of the Company (other than the Excluded Shares) was fair to such holders. The full text of Barclays written opinion dated July 12, 2016, which sets forth, among other things, the assumptions made, procedures followed, factors considered and limitations upon the review undertaken in connection with the opinion, is attached to this proxy statement asAnnex B. The Special Committee further discussed the advantages and risks of the proposed transaction that are described in  Recommendation of the Board and Reasons for the Merger  Special Committee beginning on page 37 of this proxy statement. After
B098 [L1549-L1549]: 36
B099 [L1552-L1553]: further discussion, the Special Committee unanimously determined to recommend to the Board that the Company enter into the merger agreement for the transaction with Thoma Bravo on the terms presented to the Special Committee.
B100 [L1555-L1561]: Later on July 12, 2016, the Board held a meeting. Members of Company management, Mr. Linnemann and representatives of Barclays and Goodwin were in attendance. Representatives of Barclays reviewed with the Board the Special Committees review of the Companys strategic alternatives since the last Board meeting on June 17, 2016, including the events of the subsequent weeks that culminated in Thoma Bravos offer of $19.25 per share. Representatives of Goodwin reviewed with the Board its fiduciary duties and the terms of the proposed merger agreement with Thoma Bravo. Representatives of Barclays then delivered to the Board the oral fairness opinion that Barclays had previously delivered to the Special Committee. The Chairperson, on behalf of the Special Committee, informed the Board that the Special Committee unanimously recommended that the Board approve the Companys entry into a merger agreement with Thoma Bravo. After further discussing the advantages and risks of the proposed transaction that are described in  Recommendation of the Board and Reasons for the Merger  The Board beginning on page 41 of this proxy statement, the Board unanimously adopted and declared the advisability of the merger agreement, and further declared that the merger agreement was in the best interests of the Company and its stockholders, and recommended that the Companys stockholders approve the merger agreement.
B101 [L1563-L1564]: On July 13, 2016, before the stock market opened, the parties finalized and executed the merger agreement and received executed final copies of the equity commitment letter and the voting agreements. Later on July 13, 2016, before the stock market opened, the Company and Thoma Bravo issued a joint press release announcing the execution of the merger agreement.
</chronology_blocks>

<evidence_checklist>
### Dated actions to extract
- [ ] **0001193125-16-677939:E0331** L1158-L1159 (date: June 2014; value: $15.00 per share; terms: offer)
- [ ] **0001193125-16-677939:E0333** L1161-L1163 (date: June 2015; terms: meeting, proposal, sent)
- [ ] **0001193125-16-677939:E0335** L1165-L1166 (date: August 5, 2015; value: $17.4; terms: sent)
- [ ] **0001193125-16-677939:E0337** L1168-L1168 (date: August 11, 2015; value: $15.00 per share; terms: offer)
- [ ] **0001193125-16-677939:E0339** L1170-L1171 (date: October 14, 2015; value: $12.00; terms: announced)
- [ ] **0001193125-16-677939:E0341** L1173-L1174 (date: November 2, 2015; value: $9.42; terms: announced)
- [ ] **0001193125-16-677939:E0343** L1176-L1177 (date: January 2016; actors: Board; terms: met, proposal, sent)
- [ ] **0001193125-16-677939:E0345** L1179-L1180 (date: February 24, 2016; actors: Board; terms: meeting)
- [ ] **0001193125-16-677939:E0347** L1187-L1190 (date: March 9, 2016; actors: Board; value: $15.00 per share; terms: sent)
- [ ] **0001193125-16-677939:E0351** L1192-L1201 (date: March 10, 2016; actors: Board; terms: authorized, discussed, engaged)
- [ ] **0001193125-16-677939:E0353** L1203-L1204 (date: March 11, 2016; actors: Board; terms: sent)
- [ ] **0001193125-16-677939:E0355** L1206-L1210 (date: March; actors: Board; terms: authorized, meeting, met)
- [ ] **0001193125-16-677939:E0357** L1212-L1215 (date: April 7, 2016; actors: Board; terms: meeting, sent)
- [ ] **0001193125-16-677939:E0361** L1226-L1234 (date: April 15, 2016; actors: Board; value: $12; terms: discussed, engaged, meeting)
- [ ] **0001193125-16-677939:E0365** L1236-L1239 (date: April 7, 2016; actors: Board; terms: discussed, meeting, met)
- [ ] **0001193125-16-677939:E0367** L1241-L1245 (date: April 7, 2016; actors: Board; terms: discussed, meeting, requested)
- [ ] **0001193125-16-677939:E0369** L1247-L1248 (date: April 19, 2016; actors: Board; terms: authorized, meeting, signed)
- [ ] **0001193125-16-677939:E0371** L1253-L1262 (date: April 28, 2016; actors: Board; terms: discussed, meeting, met)
- [ ] **0001193125-16-677939:E0373** L1264-L1271 (date: May 5, 2016; actors: Board; terms: discussed, meeting, met)
- [ ] **0001193125-16-677939:E0376** L1273-L1278 (date: May; actors: Sponsor A, Sponsor B, Board; terms: contacted, declined, discussed)
- [ ] **0001193125-16-677939:E0380** L1280-L1282 (date: May 12,
2016; actors: Board; terms: meeting, sent)
- [ ] **0001193125-16-677939:E0383** L1289-L1291 (date: May 26, 2016; actors: Board; terms: meeting, sent)
- [ ] **0001193125-16-677939:E0386** L1293-L1294 (date: June 1, 2016; terms: announced)
- [ ] **0001193125-16-677939:E0387** L1296-L1300 (date: June 3, 2016; actors: Board; terms: executed, meeting, offer)
- [ ] **0001193125-16-677939:E0391** L1302-L1303 (date: June 3, 2016; terms: contacted)
- [ ] **0001193125-16-677939:E0393** L1309-L1312 (date: June 9, 2016; actors: Sponsor A, Sponsor B; value: $16.50 per share; terms: sent)
- [ ] **0001193125-16-677939:E0398** L1314-L1315 (date: June 11, 2016; terms: contacted)
- [ ] **0001193125-16-677939:E0400** L1317-L1318 (date: June 11, 2016; terms: sent)
- [ ] **0001193125-16-677939:E0401** L1320-L1321 (date: June 12, 2016; terms: sent)
- [ ] **0001193125-16-677939:E0402** L1323-L1324 (date: June 12, 2016; actors: Board; terms: discussed, meeting, received)
- [ ] **0001193125-16-677939:E0404** L1329-L1333 (date: April 7, 2016; actors: Board; terms: contacted, declined, discussed)
- [ ] **0001193125-16-677939:E0408** L1335-L1342 (date: June 9, 2016; actors: Sponsor A, Sponsor B, Board; terms: authorized, discussed, offer)
- [ ] **0001193125-16-677939:E0411** L1344-L1345 (date: June 13, 2016; actors: Sponsor A; terms: contacted, offer, sent)
- [ ] **0001193125-16-677939:E0413** L1347-L1348 (date: June 14, 2016; terms: sent)
- [ ] **0001193125-16-677939:E0414** L1350-L1353 (date: June 15,
2016; actors: Sponsor A, Sponsor
A, Board; terms: sent)
- [ ] **0001193125-16-677939:E0416** L1355-L1359 (date: June 17, 2016; actors: Sponsor A, Sponsor B, Board, Special Committee; terms: authorized, meeting, proposal)
- [ ] **0001193125-16-677939:E0419** L1368-L1373 (date: June 17, 2016; actors: Sponsor A, Sponsor B, Board, Special Committee; terms: meeting, met, sent)
- [ ] **0001193125-16-677939:E0421** L1375-L1384 (date: June 9, 2016; actors: Sponsor A, Sponsor B, Special Committee, Board; terms: contacted, declined, discussed)
- [ ] **0001193125-16-677939:E0424** L1386-L1387 (date: June 17, 2016; terms: contacted, sent)
- [ ] **0001193125-16-677939:E0426** L1395-L1396 (date: June 24, 2016; actors: Special Committee; terms: met, sent)
- [ ] **0001193125-16-677939:E0428** L1401-L1402 (date: July 8, 2016; actors: Sponsor B, Special Committee; terms: meeting, met)
- [ ] **0001193125-16-677939:E0431** L1404-L1405 (date: June 24, 2016; actors: Sponsor B; terms: proposed, sent)
- [ ] **0001193125-16-677939:E0435** L1407-L1408 (date: June 27, 2016; actors: Sponsor B; terms: sent)
- [ ] **0001193125-16-677939:E0438** L1410-L1412 (date: June 27, 2016; actors: Sponsor B, Special Committee; terms: declined, met, offer)
- [ ] **0001193125-16-677939:E0440** L1414-L1415 (date: June 28, 2016; terms: sent)
- [ ] **0001193125-16-677939:E0442** L1417-L1418 (date: June; terms: sent)
- [ ] **0001193125-16-677939:E0444** L1420-L1423 (date: June 29, 2016; actors: Sponsor B, Special Committee; terms: sent)
- [ ] **0001193125-16-677939:E0447** L1425-L1430 (date: June 30, 2016; actors: Sponsor B, Special Committee; terms: declined, discussed, meeting)
- [ ] **0001193125-16-677939:E0451** L1435-L1435 (date: July 1, 2016; terms: proposed)
- [ ] **0001193125-16-677939:E0454** L1445-L1447 (date: July 6, 2016; actors: Special Committee; terms: requested, sent)
- [ ] **0001193125-16-677939:E0456** L1449-L1450 (date: July 7, 2016; terms: sent)
- [ ] **0001193125-16-677939:E0459** L1452-L1454 (date: July 7, 2016; terms: sent)
- [ ] **0001193125-16-677939:E0460** L1456-L1458 (date: July 7, 2016; actors: Special Committee; terms: met, sent)
- [ ] **0001193125-16-677939:E0462** L1460-L1463 (date: July 8, 2016; actors: Sponsor B; value: $19.00 per share; terms: engaged, sent, submitted)
- [ ] **0001193125-16-677939:E0467** L1465-L1467 (date: July 8, 2016; actors: Special Committee, Board; value: $19.00 per share; terms: meeting, offer, sent)
- [ ] **0001193125-16-677939:E0475** L1483-L1487 (date: July 8, 2016; actors: Special Committee; value: $19.00 per
share; terms: meeting, offer)
- [ ] **0001193125-16-677939:E0479** L1489-L1493 (date: July 9, 2016; actors: Special Committee; value: $19.00; terms: contacted, offer, sent)
- [ ] **0001193125-16-677939:E0484** L1495-L1498 (date: July 9, 2016; value: $19.25 per share; terms: engaged, offer, proposal)
- [ ] **0001193125-16-677939:E0488** L1500-L1505 (date: July 10, 2016; terms: engaged, proposal, proposed)
- [ ] **0001193125-16-677939:E0492** L1507-L1511 (date: July 10, 2016; actors: Special Committee; value: $19.25 per share; terms: discussed, meeting, met)
- [ ] **0001193125-16-677939:E0499** L1520-L1521 (date: July 10, 2016; terms: sent)
- [ ] **0001193125-16-677939:E0501** L1523-L1525 (date: July 11, 2016; actors: Special Committee; terms: authorized, discussed, sent)
- [ ] **0001193125-16-677939:E0503** L1527-L1528 (date: July 11, 2016; actors: Special Committee; terms: sent)
- [ ] **0001193125-16-677939:E0506** L1530-L1533 (date: July 11, 2016; terms: requested)
- [ ] **0001193125-16-677939:E0510** L1535-L1540 (date: July 12, 2016; actors: Special Committee, Board; terms: discussed, meeting, proposed)
- [ ] **0001193125-16-677939:E0513** L1542-L1547 (date: July 12, 2016; actors: Special Committee, Board; value: $19.25 per share; terms: delivered, discussed, offer)
- [ ] **0001193125-16-677939:E0518** L1555-L1561 (date: July 12, 2016; actors: Board, Special Committee; value: $19.25 per share; terms: delivered, meeting, offer)
- [ ] **0001193125-16-677939:E0523** L1563-L1564 (date: July 13, 2016; terms: executed, received)

### Financial terms to capture
- [ ] **0001193125-16-677939:E0332** L1158-L1159 (date: June 2014; value: $15.00 per share; terms: $15.00 per share)
- [ ] **0001193125-16-677939:E0336** L1165-L1166 (date: August 5, 2015; value: $17.4; terms: $17.4)
- [ ] **0001193125-16-677939:E0338** L1168-L1168 (date: August 11, 2015; value: $15.00 per share; terms: $15.00 per share)
- [ ] **0001193125-16-677939:E0340** L1170-L1171 (date: October 14, 2015; value: $12.00; terms: $12.00, $17.31)
- [ ] **0001193125-16-677939:E0342** L1173-L1174 (date: November 2, 2015; value: $9.42; terms: $10.39, $9.42)
- [ ] **0001193125-16-677939:E0348** L1187-L1190 (date: March 9, 2016; actors: Board; value: $15.00 per share; terms: $11.64, $15.00 per share)
- [ ] **0001193125-16-677939:E0362** L1226-L1234 (date: April 15, 2016; actors: Board; value: $12; terms: $12, $13)
- [ ] **0001193125-16-677939:E0394** L1309-L1312 (date: June 9, 2016; actors: Sponsor A, Sponsor B; value: $16.50 per share; terms: $13.46, $16.50 per share, $17.00 - $18.00 per share)
- [ ] **0001193125-16-677939:E0463** L1460-L1463 (date: July 8, 2016; actors: Sponsor B; value: $19.00 per share; terms: $19.00 per share)
- [ ] **0001193125-16-677939:E0468** L1465-L1467 (date: July 8, 2016; actors: Special Committee, Board; value: $19.00 per share; terms: $19.00 per share)
- [ ] **0001193125-16-677939:E0470** L1469-L1475 (actors: Special Committee; value: $19.00 per share; terms: $19.00 per share)
- [ ] **0001193125-16-677939:E0476** L1483-L1487 (date: July 8, 2016; actors: Special Committee; value: $19.00 per
share; terms: $19.00 per
share)
- [ ] **0001193125-16-677939:E0480** L1489-L1493 (date: July 9, 2016; actors: Special Committee; value: $19.00; terms: $19.00)
- [ ] **0001193125-16-677939:E0485** L1495-L1498 (date: July 9, 2016; value: $19.25 per share; terms: $19.25 per share)
- [ ] **0001193125-16-677939:E0493** L1507-L1511 (date: July 10, 2016; actors: Special Committee; value: $19.25 per share; terms: $19.25 per share)
- [ ] **0001193125-16-677939:E0514** L1542-L1547 (date: July 12, 2016; actors: Special Committee, Board; value: $19.25 per share; terms: $19.25 per share)
- [ ] **0001193125-16-677939:E0519** L1555-L1561 (date: July 12, 2016; actors: Board, Special Committee; value: $19.25 per share; terms: $19.25 per share)

### Actors to identify
- [ ] **0001193125-16-677939:E0328** L1150-L1151 (actors: Board, Special Committee; terms: special committee)
- [ ] **0001193125-16-677939:E0330** L1153-L1156 (actors: Board; terms: advisor, advisors, party )
- [ ] **0001193125-16-677939:E0334** L1161-L1163 (date: June 2015; terms: stockholder)
- [ ] **0001193125-16-677939:E0344** L1176-L1177 (date: January 2016; actors: Board)
- [ ] **0001193125-16-677939:E0346** L1179-L1180 (date: February 24, 2016; actors: Board)
- [ ] **0001193125-16-677939:E0349** L1187-L1190 (date: March 9, 2016; actors: Board; value: $15.00 per share)
- [ ] **0001193125-16-677939:E0352** L1192-L1201 (date: March 10, 2016; actors: Board; terms: advisor, counsel, financial advisor)
- [ ] **0001193125-16-677939:E0354** L1203-L1204 (date: March 11, 2016; actors: Board)
- [ ] **0001193125-16-677939:E0356** L1206-L1210 (date: March; actors: Board; terms: advisor, financial advisor, investment bank)
- [ ] **0001193125-16-677939:E0358** L1212-L1215 (date: April 7, 2016; actors: Board)
- [ ] **0001193125-16-677939:E0359** L1220-L1224 (actors: Board)
- [ ] **0001193125-16-677939:E0363** L1226-L1234 (date: April 15, 2016; actors: Board; value: $12; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-677939:E0366** L1236-L1239 (date: April 7, 2016; actors: Board; terms: stockholder)
- [ ] **0001193125-16-677939:E0368** L1241-L1245 (date: April 7, 2016; actors: Board)
- [ ] **0001193125-16-677939:E0370** L1247-L1248 (date: April 19, 2016; actors: Board)
- [ ] **0001193125-16-677939:E0372** L1253-L1262 (date: April 28, 2016; actors: Board)
- [ ] **0001193125-16-677939:E0374** L1264-L1271 (date: May 5, 2016; actors: Board; terms: stockholder)
- [ ] **0001193125-16-677939:E0377** L1273-L1278 (date: May; actors: Sponsor A, Sponsor B, Board; terms: party )
- [ ] **0001193125-16-677939:E0381** L1280-L1282 (date: May 12,
2016; actors: Board; terms: stockholder)
- [ ] **0001193125-16-677939:E0384** L1289-L1291 (date: May 26, 2016; actors: Board)
- [ ] **0001193125-16-677939:E0388** L1296-L1300 (date: June 3, 2016; actors: Board)
- [ ] **0001193125-16-677939:E0395** L1309-L1312 (date: June 9, 2016; actors: Sponsor A, Sponsor B; value: $16.50 per share)
- [ ] **0001193125-16-677939:E0403** L1323-L1324 (date: June 12, 2016; actors: Board)
- [ ] **0001193125-16-677939:E0405** L1329-L1333 (date: April 7, 2016; actors: Board; terms: special committee)
- [ ] **0001193125-16-677939:E0409** L1335-L1342 (date: June 9, 2016; actors: Sponsor A, Sponsor B, Board; terms: counsel, special committee, stockholder)
- [ ] **0001193125-16-677939:E0412** L1344-L1345 (date: June 13, 2016; actors: Sponsor A)
- [ ] **0001193125-16-677939:E0415** L1350-L1353 (date: June 15,
2016; actors: Sponsor A, Sponsor
A, Board)
- [ ] **0001193125-16-677939:E0417** L1355-L1359 (date: June 17, 2016; actors: Sponsor A, Sponsor B, Board, Special Committee; terms: counsel, special committee)
- [ ] **0001193125-16-677939:E0418** L1364-L1366 (actors: Board, Special Committee; terms: special committee)
- [ ] **0001193125-16-677939:E0420** L1368-L1373 (date: June 17, 2016; actors: Sponsor A, Sponsor B, Board, Special Committee; terms: special committee)
- [ ] **0001193125-16-677939:E0422** L1375-L1384 (date: June 9, 2016; actors: Sponsor A, Sponsor B, Special Committee, Board; terms: bidder , special committee)
- [ ] **0001193125-16-677939:E0425** L1389-L1390 (date: June 17, 2016; actors: Sponsor B)
- [ ] **0001193125-16-677939:E0427** L1395-L1396 (date: June 24, 2016; actors: Special Committee; terms: special committee)
- [ ] **0001193125-16-677939:E0429** L1401-L1402 (date: July 8, 2016; actors: Sponsor B, Special Committee; terms: special committee)
- [ ] **0001193125-16-677939:E0432** L1404-L1405 (date: June 24, 2016; actors: Sponsor B)
- [ ] **0001193125-16-677939:E0436** L1407-L1408 (date: June 27, 2016; actors: Sponsor B)
- [ ] **0001193125-16-677939:E0439** L1410-L1412 (date: June 27, 2016; actors: Sponsor B, Special Committee; terms: special committee)
- [ ] **0001193125-16-677939:E0443** L1417-L1418 (date: June; terms: advisor, advisors)
- [ ] **0001193125-16-677939:E0445** L1420-L1423 (date: June 29, 2016; actors: Sponsor B, Special Committee; terms: special committee)
- [ ] **0001193125-16-677939:E0448** L1425-L1430 (date: June 30, 2016; actors: Sponsor B, Special Committee; terms: special committee, stockholder)
- [ ] **0001193125-16-677939:E0450** L1432-L1433 (date: June 30, 2016; actors: Board)
- [ ] **0001193125-16-677939:E0455** L1445-L1447 (date: July 6, 2016; actors: Special Committee; terms: special committee)
- [ ] **0001193125-16-677939:E0457** L1449-L1450 (date: July 7, 2016; terms: counsel)
- [ ] **0001193125-16-677939:E0461** L1456-L1458 (date: July 7, 2016; actors: Special Committee; terms: special committee)
- [ ] **0001193125-16-677939:E0464** L1460-L1463 (date: July 8, 2016; actors: Sponsor B; value: $19.00 per share)
- [ ] **0001193125-16-677939:E0469** L1465-L1467 (date: July 8, 2016; actors: Special Committee, Board; value: $19.00 per share; terms: special committee)
- [ ] **0001193125-16-677939:E0471** L1469-L1475 (actors: Special Committee; value: $19.00 per share; terms: special committee, stockholder)
- [ ] **0001193125-16-677939:E0473** L1480-L1481 (actors: Special Committee; terms: special committee)
- [ ] **0001193125-16-677939:E0477** L1483-L1487 (date: July 8, 2016; actors: Special Committee; value: $19.00 per
share; terms: advisor, advisors, special committee)
- [ ] **0001193125-16-677939:E0481** L1489-L1493 (date: July 9, 2016; actors: Special Committee; value: $19.00; terms: special committee)
- [ ] **0001193125-16-677939:E0489** L1500-L1505 (date: July 10, 2016; terms: party )
- [ ] **0001193125-16-677939:E0494** L1507-L1511 (date: July 10, 2016; actors: Special Committee; value: $19.25 per share; terms: special committee)
- [ ] **0001193125-16-677939:E0497** L1516-L1518 (actors: Special Committee; terms: advisor, advisors, special committee)
- [ ] **0001193125-16-677939:E0502** L1523-L1525 (date: July 11, 2016; actors: Special Committee; terms: special committee)
- [ ] **0001193125-16-677939:E0504** L1527-L1528 (date: July 11, 2016; actors: Special Committee; terms: special committee)
- [ ] **0001193125-16-677939:E0507** L1530-L1533 (date: July 11, 2016; terms: special committee, stockholder)
- [ ] **0001193125-16-677939:E0511** L1535-L1540 (date: July 12, 2016; actors: Special Committee, Board; terms: special committee)
- [ ] **0001193125-16-677939:E0515** L1542-L1547 (date: July 12, 2016; actors: Special Committee, Board; value: $19.25 per share; terms: special committee)
- [ ] **0001193125-16-677939:E0516** L1552-L1553 (actors: Special Committee, Board; terms: special committee)
- [ ] **0001193125-16-677939:E0520** L1555-L1561 (date: July 12, 2016; actors: Board, Special Committee; value: $19.25 per share; terms: special committee, stockholder)

### Process signals to check
- [ ] **0001193125-16-677939:E0364** L1226-L1234 (date: April 15, 2016; actors: Board; value: $12; terms: due diligence, strategic alternatives)
- [ ] **0001193125-16-677939:E0375** L1264-L1271 (date: May 5, 2016; actors: Board; terms: strategic alternatives)
- [ ] **0001193125-16-677939:E0378** L1273-L1278 (date: May; actors: Sponsor A, Sponsor B, Board; terms: confidentiality agreement, management presentation, standstill)
- [ ] **0001193125-16-677939:E0382** L1287-L1287 (terms: management presentation)
- [ ] **0001193125-16-677939:E0385** L1289-L1291 (date: May 26, 2016; actors: Board; terms: management presentation)
- [ ] **0001193125-16-677939:E0389** L1296-L1300 (date: June 3, 2016; actors: Board; terms: confidentiality agreement, due diligence, instruction letter)
- [ ] **0001193125-16-677939:E0392** L1302-L1303 (date: June 3, 2016; terms: confidentiality agreement, process letter)
- [ ] **0001193125-16-677939:E0396** L1309-L1312 (date: June 9, 2016; actors: Sponsor A, Sponsor B; value: $16.50 per share; terms: draft merger agreement, due diligence)
- [ ] **0001193125-16-677939:E0399** L1314-L1315 (date: June 11, 2016; terms: confidentiality agreement, process letter)
- [ ] **0001193125-16-677939:E0406** L1329-L1333 (date: April 7, 2016; actors: Board; terms: confidentiality agreement)
- [ ] **0001193125-16-677939:E0410** L1335-L1342 (date: June 9, 2016; actors: Sponsor A, Sponsor B, Board; terms: strategic alternatives)
- [ ] **0001193125-16-677939:E0423** L1375-L1384 (date: June 9, 2016; actors: Sponsor A, Sponsor B, Special Committee, Board; terms: bid deadline, management presentation)
- [ ] **0001193125-16-677939:E0430** L1401-L1402 (date: July 8, 2016; actors: Sponsor B, Special Committee; terms: bid deadline, final bid)
- [ ] **0001193125-16-677939:E0433** L1404-L1405 (date: June 24, 2016; actors: Sponsor B; terms: bid deadline, final bid, process letter)
- [ ] **0001193125-16-677939:E0437** L1407-L1408 (date: June 27, 2016; actors: Sponsor B; terms: management presentation)
- [ ] **0001193125-16-677939:E0441** L1414-L1415 (date: June 28, 2016; terms: management presentation)
- [ ] **0001193125-16-677939:E0446** L1420-L1423 (date: June 29, 2016; actors: Sponsor B, Special Committee; terms: final bid)
- [ ] **0001193125-16-677939:E0449** L1425-L1430 (date: June 30, 2016; actors: Sponsor B, Special Committee; terms: bid deadline, final bid)
- [ ] **0001193125-16-677939:E0453** L1443-L1443 (terms: confidentiality agreement)
- [ ] **0001193125-16-677939:E0465** L1460-L1463 (date: July 8, 2016; actors: Sponsor B; value: $19.00 per share; terms: due diligence, final bid)
- [ ] **0001193125-16-677939:E0472** L1469-L1475 (actors: Special Committee; value: $19.00 per share; terms: strategic alternatives)
- [ ] **0001193125-16-677939:E0478** L1483-L1487 (date: July 8, 2016; actors: Special Committee; value: $19.00 per
share; terms: strategic alternatives)
- [ ] **0001193125-16-677939:E0482** L1489-L1493 (date: July 9, 2016; actors: Special Committee; value: $19.00; terms: best and final)
- [ ] **0001193125-16-677939:E0486** L1495-L1498 (date: July 9, 2016; value: $19.25 per share; terms: best and final)
- [ ] **0001193125-16-677939:E0490** L1500-L1505 (date: July 10, 2016; terms: draft merger agreement)
- [ ] **0001193125-16-677939:E0495** L1507-L1511 (date: July 10, 2016; actors: Special Committee; value: $19.25 per share; terms: best and final, draft merger agreement)
- [ ] **0001193125-16-677939:E0498** L1516-L1518 (actors: Special Committee; terms: strategic alternatives)
- [ ] **0001193125-16-677939:E0505** L1527-L1528 (date: July 11, 2016; actors: Special Committee; terms: exclusivity)
- [ ] **0001193125-16-677939:E0508** L1530-L1533 (date: July 11, 2016; terms: confidentiality agreement)
- [ ] **0001193125-16-677939:E0521** L1555-L1561 (date: July 12, 2016; actors: Board, Special Committee; value: $19.25 per share; terms: strategic alternatives)

### Outcome facts to verify
- [ ] **0001193125-16-677939:E0329** L1150-L1151 (actors: Board, Special Committee; terms: merger agreement)
- [ ] **0001193125-16-677939:E0350** L1187-L1190 (date: March 9, 2016; actors: Board; value: $15.00 per share; terms: closing, merger agreement)
- [ ] **0001193125-16-677939:E0360** L1220-L1224 (actors: Board; terms: closing)
- [ ] **0001193125-16-677939:E0379** L1273-L1278 (date: May; actors: Sponsor A, Sponsor B, Board; terms: executed, merger agreement, terminated)
- [ ] **0001193125-16-677939:E0390** L1296-L1300 (date: June 3, 2016; actors: Board; terms: executed)
- [ ] **0001193125-16-677939:E0397** L1309-L1312 (date: June 9, 2016; actors: Sponsor A, Sponsor B; value: $16.50 per share; terms: closing, merger agreement)
- [ ] **0001193125-16-677939:E0407** L1329-L1333 (date: April 7, 2016; actors: Board; terms: executed)
- [ ] **0001193125-16-677939:E0434** L1404-L1405 (date: June 24, 2016; actors: Sponsor B; terms: merger agreement)
- [ ] **0001193125-16-677939:E0452** L1435-L1435 (date: July 1, 2016; terms: merger agreement)
- [ ] **0001193125-16-677939:E0458** L1449-L1450 (date: July 7, 2016; terms: merger agreement)
- [ ] **0001193125-16-677939:E0466** L1460-L1463 (date: July 8, 2016; actors: Sponsor B; value: $19.00 per share; terms: merger agreement)
- [ ] **0001193125-16-677939:E0474** L1480-L1481 (actors: Special Committee; terms: closing, merger agreement)
- [ ] **0001193125-16-677939:E0483** L1489-L1493 (date: July 9, 2016; actors: Special Committee; value: $19.00; terms: merger agreement)
- [ ] **0001193125-16-677939:E0487** L1495-L1498 (date: July 9, 2016; value: $19.25 per share; terms: merger agreement)
- [ ] **0001193125-16-677939:E0491** L1500-L1505 (date: July 10, 2016; terms: merger agreement, termination fee)
- [ ] **0001193125-16-677939:E0496** L1507-L1511 (date: July 10, 2016; actors: Special Committee; value: $19.25 per share; terms: merger agreement)
- [ ] **0001193125-16-677939:E0500** L1520-L1521 (date: July 10, 2016; terms: merger agreement)
- [ ] **0001193125-16-677939:E0509** L1530-L1533 (date: July 11, 2016; terms: merger agreement)
- [ ] **0001193125-16-677939:E0512** L1535-L1540 (date: July 12, 2016; actors: Special Committee, Board; terms: merger agreement)
- [ ] **0001193125-16-677939:E0517** L1552-L1553 (actors: Special Committee, Board; terms: merger agreement)
- [ ] **0001193125-16-677939:E0522** L1555-L1561 (date: July 12, 2016; actors: Board, Special Committee; value: $19.25 per share; terms: merger agreement)
- [ ] **0001193125-16-677939:E0524** L1563-L1564 (date: July 13, 2016; terms: executed, merger agreement)
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