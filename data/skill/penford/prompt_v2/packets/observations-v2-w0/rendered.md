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
deal_slug: penford
target_name: PENFORD CORP
source_accession_number: 0001193125-14-455030
source_form_type: UNKNOWN
chunk_mode: single_pass
window_id: w0
</deal_context>

<chronology_blocks>
B001 [L1270-L1270]: Background of the Merger
B002 [L1272-L1273]: Penfords management and its board of directors have regularly reviewed the Companys strategic options to enhance shareholder value as part of Penfords ongoing strategic planning. These strategic options included potential acquisitions and divestitures, as well as potential strategic transactions involving the acquisition of Penford.
B003 [L1275-L1276]: As a consequence of such reviews during the past six years, Penford determined, among other things, to dispose of its two Australian facilities, its New Zealand facility and its dextrose products business.
B004 [L1278-L1279]: Penford also acquired additional assets and businesses, including Carolina Starches in 2012, the Pegetables®brand of pet treats in 2013 and Gum Technology in 2014.
B005 [L1281-L1282]: In 2007 and 2009, the Company received unsolicited indications of interest to acquire Penford from two parties engaged in the Companys industry. In each case, the Company entered into a confidentiality agreement and engaged in discussions and exchanged information with the party expressing interest. These discussions did not result in offers to acquire the Company.
B006 [L1284-L1284]: 23
B007 [L1287-L1289]: On July 8, 2014, Ilene Gordon, Ingredions Chairman and Chief Executive Officer, left a voicemail message for Penfords Chief Executive Officer Thomas Malkoski, seeking a meeting. Ms. Gordon did not indicate the purpose of the meeting. Due to Mr. Malkoskis travel schedule, he did not receive the voicemail message until July 9, 2014.
B008 [L1291-L1293]: On July 9, 2014, Mr. Malkoski and Ms. Gordon exchanged emails regarding proposed dates for a meeting and they agreed to meet for lunch on July 17, 2014. Mr. Malkoski informed Paul Hatfield, the Chairman of the board, as well as Christopher Lawlor, the Companys general counsel, of the planned meeting. Although the purpose of the meeting was not yet known, Mr. Hatfield supported Mr. Malkoskis efforts to meet with Ms. Gordon.
B009 [L1295-L1295]: On
B010 [L1296-L1297]: July 11, 2014, SEACOR filed an amendment to its Schedule 13D (referred to as the SEACOR Filing) with the Securities and Exchange Commission (referred to as the SEC) in which SEACOR stated its intent to nominate four candidates for election as directors of our board at Penfords next annual meeting of shareholders.
B011 [L1299-L1304]: On July 17, 2014, Mr. Malkoski and Ms. Gordon met for lunch, during which meeting Ms. Gordon advised Mr. Malkoski of Ingredions interest in acquiring Penford. Ms. Gordon noted that the business strategies of Ingredion and Penford were similar, with both having success, and that Ingredion was impressed with Penfords execution of its specialty products business model. When Mr. Malkoski asked about potential valuation, Ms. Gordon did not cite a specific number but noted Penfords 52-week high of approximately $16.00 per share and the current trading price of approximately $12.00 per share. Ms. Gordon noted the recent sales of shares of Penford common stock by the Zell funds, the owners of, prior to such sales, approximately 9.80% of the Companys outstanding common stock, which Mr. Malkoski said might be putting downward pressure on the price of Penfords common stock, together with the recent removal of the stock from the Russell 3000 index. Ms. Gordon then asked if Mr. Malkoski would meet with Jack Fortnum, Ingredions Chief Financial Officer, to discuss valuation of the Company.
B012 [L1306-L1307]: Following the July 17 lunch meeting with Ms. Gordon, Mr. Malkoski and Mr. Hatfield discussed Mr. Malkoskis recent discussions with Ms. Gordon regarding Ingredions interest in acquiring the Company.
B013 [L1309-L1310]: On July 18, 2014, Mr. Malkoski spoke with Mr. Fortnum by phone and they agreed to meet the following day to discuss Ingredions interest in acquiring Penford.
B014 [L1312-L1317]: On July 19, 2014, Mr. Malkoski and Mr. Fortnum discussed general strategic considerations for a proposed transaction, such as the food segment and the complimentary portfolios, value added green technologies, industrial products and production, reloading plants for efficiencies, technology development, including research and development of applications, and the specialty products strategy. Mr. Malkoski and Mr. Fortnum also discussed potential synergies, including public company costs, consolidation of benefits, potential tax savings and Ingredions lower cost of capital. Mr. Fortnum did not discuss a potential purchase price, but like Ms. Gordon, referenced Penfords 52-week high of approximately $16.00 per share, stating that it could be a challenge for Ingredion to reach this value given the implied enterprise value and EBITDA multiple at that price. Mr. Fortnum and Mr. Malkoski discussed considering Penfords adjusted EBITDA, which would take into account certain non-recurring events that affected results of operations of the Company, in order to provide a more complete understanding of the results of operations and to support a valuation and offer a price that Penfords board would be willing to consider.
B015 [L1319-L1320]: Subsequently, Penford and Ingredion executed a Secrecy Agreement, effective as of July 20, 2014, providing for limited exchange of confidential information and obligating the companies to keep their discussions confidential in order to facilitate the providing of confidential information of Penford to Ingredion.
B016 [L1322-L1325]: In order to update and gather insight from certain board members on an expedited basis, Mr. Hatfield decided to utilize the Executive Committee to discuss recent developments, due to the Executive Committees ability to meet with little advance notice and the authority vested in this committee under the Companys bylaws. Therefore, on July 22, 2014, Mr. Lawlor, as secretary of the Company, provided notice of a meeting of the Executive Committee of the Penford board for the purpose of discussing, among other things, recent Schedule 13D filings, including the SEACOR Filing and strategic developments, including the discussions with Ingredion.
B017 [L1327-L1327]: 24
B018 [L1330-L1332]: On July 23, 2014, Mr. Fortnum and Mr. Malkoski discussed expectations on timing and next steps for a potential transaction. Mr. Fortnum indicated that Ingredion would not have a specific offer until after the Ingredion earnings call scheduled for July 30, 2014. Mr. Fortnum and Mr. Malkoski discussed setting up another meeting for the week of August 4, and Mr. Fortnum stated that he would reach out to Mr. Malkoski during the week following Ingredions earnings call.
B019 [L1334-L1340]: On July 24, 2014, the Executive Committee of the Penford board held a telephonic meeting, at which all members of the Executive Committee, as well as certain other directors, members of Penfords management and representatives of Perkins Coie LLP (referred to as Perkins Coie), Penfords legal counsel, were present. At the meeting, members of management updated the Executive Committee on the recent Schedule 13D filings, including the SEACOR Filing. Mr. Malkoski also reported on the recent oral indication of interest he had received from Ingredion to acquire the Company. The Executive Committee discussed the oral indication of interest from Ingredion. Mr. Hatfield recommended that the Executive Committee consider retaining a financial advisor on the Companys behalf in light of these developments, and management reviewed the credentials of several firms and reported on interview meetings management had with certain firms regarding a potential engagement. Following discussion of potential financial advisors, the Executive Committee directed management to proceed to retain Deutsche Bank as the Companys financial advisor and to advise on shareholder matters and to evaluate strategic alternatives, and directed management to negotiate a suitable engagement letter. An engagement letter with Deutsche Bank was executed on September 11, 2014.
B020 [L1342-L1343]: On July 25, 2014, Mr. Lawlor, as secretary of the Company, provided notice to the Penford board of a meeting to be held on July 30, 2014.
B021 [L1345-L1348]: On July 30, 2014, the board of directors held a special meeting primarily for the purpose of approving the Companys new credit facility. Also in attendance were certain members of Penfords management and representatives of Perkins Coie. The board discussed the new credit facility, a recent meeting of the Executive Committee and the Executive Committees decision to engage Deutsche Bank with regard to shareholder matters and to evaluate strategic alternatives. Mr. Malkoski reported to the board about the process used to identify Deutsche Bank, the interview meetings conducted with Deutsche Bank by management earlier that month and Deutsche Banks qualifications to act in its role as financial advisor to the Company.
B022 [L1350-L1352]: On August 1, 2014, a representative acting on behalf of a company in the industry (referred to as Party A) sent Mr. Malkoski an email asking for a call. On August 4, 2014, Mr. Malkoski and the representative acting on behalf of Party A discussed scheduling a meeting with the Chief Executive Officer of Party A for August 11, 2014. Party As representative did not indicate the purpose of the meeting.
B023 [L1354-L1355]: On August 5, 2014, Mr. Malkoski followed up with Mr. Fortnum by text message, asking if Mr. Fortnum was ready to set up a follow-up meeting as discussed on July 23, 2014. Mr. Malkoski and Mr. Fortnum scheduled a meeting for August 6, 2014.
B024 [L1357-L1359]: On August 6, 2014, Mr. Malkoski met with Mr. Fortnum, at which meeting Mr. Fortnum indicated Ingredion was prepared to submit a proposal to acquire the Company. Mr. Fortnum suggested that a price of $17.00 per share on a fully diluted basis could likely get support from Ingredions board. Mr. Malkoski responded that, in his opinion, the proposed price would probably not be high enough to get support from Penfords board of directors.
B025 [L1361-L1364]: On August 10, 2014, Penford received a letter from Mr. Fortnum, confirming Ingredions interest in a possible business combination between Ingredion and the Company, citing certain strategic reasons for the proposed acquisition, and providing an indicative valuation of $18.00 per share in cash for all of the outstanding capital stock of Penford on a fully diluted basis. Based on the $12.10 per share closing price of Penfords common stock on August 8, 2014, the last business day prior to receiving this indication of interest, the indication of interest represented a premium of 49%.
B026 [L1366-L1368]: On August 11, 2014, the Executive Committee met with members of management and representatives of each of Perkins Coie and Deutsche Bank, at which meeting they discussed Ingredions indication of interest received on August 10. Deutsche Bank reviewed with the Executive Committee Ingredions proposal to acquire the Company, as well as its analysis of Ingredion, including its view that Ingredion was a credible and well-
B027 [L1370-L1370]: 25
B028 [L1373-L1382]: financed party with clear strategic reasons for acquiring the Company. Deutsche Bank also reviewed with the Executive Committee the Companys strategic plan, potential alternatives to an acquisition of the Company and potential approaches to valuing the Company. Deutsche Bank also reviewed with the Executive Committee other potential counterparties, which were selected by Deutsche Bank based on factors including, but not limited to, financial capacity, perceived level of interest, prior acquisition track record and ability to timely execute a transaction. Deutsche Bank also reviewed with the Executive Committee certain categories of potential counterparties, including financial sponsors and strategic purchasers, and noted their view that, based on the Companys free cash flow profile and the potential synergies a strategic purchaser may be able to realize in connection with an acquisition of the Company, strategic purchasers likely would be able to provide a more compelling valuation relative to a financial sponsor purchaser. Deutsche Bank identified SEACOR as one of the parties that might be interested in exploring an acquisition of the Company. Following further discussion among the Executive Committee members, the Executive Committee unanimously determined that it would be in the best interests of the Company and its shareholders to proceed with further review and investigation of Ingredions indication of interest to acquire Penford. In addition, since SEACOR had been identified by Penfords financial advisor as a potential counterparty, the Executive Committee determined that Mr. Hatfield should promptly contact Mr. Behrens, the SEACOR representative on the board, to discuss whether SEACOR had an interest in acquiring the Company. The Executive Committee indicated that if SEACOR did have such an interest, Mr. Behrens should recuse himself from future board discussions related to a possible sale process due to the potential conflict between Mr. Behrens duties to the Companys shareholders and his duties to SEACOR. The Executive Committee also determined that a meeting of the board of directors be held to discuss the recent developments with respect to the Ingredion indication of interest.
B029 [L1384-L1388]: Also on August 11, 2014, Mr. Malkoski met with the Chief Executive Officer of Party A. Mr. Malkoski and Party As Chief Executive Officer briefly discussed the recent SEACOR Filing. Party As Chief Executive Officer also informally discussed Party As potential interest in acquiring or combining with Penford. Party A noted that it saw value in Penford but only at a typical takeover premium based on current trading price, due to the fact that it would base any offer price on Penfords performance over the last twelve months, instead of Penfords strategic plan and any synergies that could be realized in the future. On August 12, 2014, Mr. Hatfield discussed the Ingredion indication of interest with Mr. Behrens to determine if SEACOR was interested in acquiring the Company. Mr. Behrens stated that SEACOR was not interested in participating in any potential sale process at that time.
B030 [L1390-L1399]: On August 13, 2014, the board of directors held a special meeting to discuss Ingredions indication of interest. In addition to members of management, representatives of Deutsche Bank and representatives of Perkins Coie attended the meeting. Prior to engaging in substantive discussions, Mr. Hatfield requested that Mr. Behrens confirm the position of SEACOR with respect to a potential transaction with Penford. Mr. Behrens confirmed that SEACOR was not interested in participating in any potential sale process at that time. Mr. Malkoski then reported to the board on the discussions that had taken place with representatives of Ingredion regarding a potential transaction. Deutsche Bank then reviewed with the board the contents of Ingredions August 10, 2014 indication of interest, an overview of Ingredion, certain preliminary implied valuation metrics and comparison of valuation metrics against other companies, initial observations and considerations regarding strategic alternatives and process considerations and next steps. Deutsche Bank noted that while Ingredions proposal was non-binding, Ingredion appeared to be a credible and financially capable buyer with clear strategic reasons for acquiring the Company. Deutsche Bank then provided the board with information and insights on Ingredion, and reviewed with the board the Companys strategic plan, the alternatives to an acquisition of the Company and other potential acquirers. The board and Deutsche Bank then discussed potential next steps, including sharing information with Ingredion to identify additional areas that may add to the value of the Company and, assuming progress was made with Ingredion with respect to a transaction and Penford received an acceptable offer price, engaging in a market check process to contact potential counterparties regarding an alternative transaction. Following discussion among the board members, the board members present at the meeting unanimously directed management to proceed with further investigation and development of the proposal from Ingredion.
B031 [L1401-L1402]: On August 14, 2014, Mr. Malkoski contacted Mr. Fortnum by telephone to respond to Ingredions August 10, 2014 indication of interest and expressed that Penfords board found Ingredions proposal interesting but did not
B032 [L1404-L1404]: 26
B033 [L1407-L1410]: believe that it reflected the full value of Penfords business. However, the board authorized management to engage with Ingredion and provide additional information regarding the Company, which the board believed would assist Ingredion in recognizing Penfords additional value and result in Ingredion raising its price. Therefore, to provide Ingredion with relevant information about the Company, Mr. Malkoski and Mr. Fortnum agreed to schedule a management presentation by Penford to representatives of Ingredion and its advisors on August 21, 2014 and discussed the process for submitting and responding to due diligence requests. Mr. Fortnum asked whether Penford would consider whether to enter into exclusive negotiations with Ingredion. Mr. Malkoski indicated that the current status of negotiations and the proposed price did not justify providing exclusivity.
B034 [L1412-L1413]: On August 15, 2014, Mr. Fortnum and Mr. Malkoski discussed a revised nondisclosure agreement, including the addition of a standstill provision.
B035 [L1415-L1416]: On August 19, 2014, SEACOR filed an amendment to its Schedule 13D identifying its four nominees for election as directors at Penfords next annual meeting of shareholders. Also on August 19, 2014, Mr. Fortnum and Mr. Malkoski discussed the terms of a non-disclosure agreement.
B036 [L1418-L1419]: On August 20 and 21, 2014, Ingredion and Penford negotiated provisions relating to, and exchanged drafts of, a nondisclosure and standstill agreement. Penford again declined to enter into exclusive negotiations with Ingredion. On August 21, 2014, Ingredion and Penford executed a nondisclosure and standstill agreement that superseded the prior Secrecy Agreement.
B037 [L1421-L1424]: On August 21, 2014, members of Penfords management team provided a presentation to Ms. Gordon, Mr. Fortnum, and certain other members of Ingredions senior management and representatives of J. P. Morgan Securities, Ingredions financial advisor. This presentation provided information regarding Penfords operations, corporate strategy, business segments, product applications and technologies, end markets, supply chain and manufacturing, facilities, historical financial performance and financial projections, as well as additional information on key leadership, headcount, pension obligations and information technology systems.
B038 [L1426-L1426]: On August 26, 2014, Ingredion provided Penford with an initial due diligence request list.
B039 [L1428-L1438]: On August 28, 2014, the board of directors held a regularly scheduled meeting. In addition to certain members of Penfords management team, representatives of Deutsche Bank and representatives of Perkins Coie also attended the meeting. At that meeting, members of management reviewed with the board the estimated consolidated financial results, including financial performance during the Companys fiscal fourth quarter, 2015 operating plans and proposed capital expenditures. Mr. Malkoski reported on the status of discussions and negotiations with Ingredion, noting that a management presentation had been given to the Chairman and Chief Executive Officer of Ingredion, as well as to other senior management of Ingredion and Ingredions financial advisor, on August 21, and that a nondisclosure and standstill agreement had been entered into immediately preceding the presentation that replaced the Secrecy Agreement. Mr. Malkoski also informed the board that management was proceeding with plans to establish an electronic dataroom to enable Ingredion to conduct additional due diligence. Deutsche Bank then described next steps and timing for the due diligence process. The board and Deutsche Bank also discussed the market check process whereby companies other than Ingredion would be queried by Deutsche Bank about their potential interest in acquiring the Company. Deutsche Bank again reviewed with the board the other potential counterparties and the basis for identifying such counterparties, including, but not limited to, financial capacity, perceived level of interest, prior acquisition track record, strong strategic rationale and ability to timely execute a transaction. Deutsche Bank further noted that any inquiries to potential counterparties likely would be directed to the chief executive officers of selected companies, with any substantive exchanges of information about the Company to be subject to an acceptable nondisclosure agreement. The board of directors discussed the due diligence and market check processes, including the companies that would be contacted in the market check process and any risks of loss of confidentiality during the process. Following discussion, the board directed management to continue negotiations with Ingredion and engage in the due diligence process with Ingredion. The board also authorized management and Deutsche Bank to proceed with the market check process as described at the meeting.
B040 [L1440-L1440]: 27
B041 [L1443-L1444]: As part of the August 28, 2014 board meeting, Perkins Coie provided a review, and led a discussion, of the fiduciary duties of Penfords board, including in connection with strategic proposals involving a change in control of Penford.
B042 [L1446-L1446]: Also on August 28, 2014, a more comprehensive due diligence request list was sent to J. P. Morgan Securities for delivery to Deutsche Bank.
B043 [L1448-L1450]: Starting in early September, Penford provided Ingredion access to an online dataroom to review due diligence materials and continued to respond to the initial and supplemental due diligence requests and inquiries from Ingredion. Penfords management team also conducted numerous calls and arranged for in-person meetings or site visits with Ingredion covering a range of due diligence topics in an effort to encourage Ingredion to improve the proposed terms in its indication of interest.
B044 [L1452-L1454]: On September 3, 2014, Mr. Fortnum, Mr. Malkoski and John F. Saucier, Ingredions Senior Vice President Corporate Strategy and Global Business Development, participated in a teleconference and discussed various process-related items, including populating the online dataroom with diligence materials, the status of a draft merger agreement, timing of certain milestones, comments on management presentations and priority of certain due diligence requests.
B045 [L1456-L1457]: On September 6, 2014, J. P. Morgan Securities provided Deutsche Bank with an initial draft of a merger agreement, that, among other things, contemplated the entry by certain significant shareholders into a voting and support agreement with Ingredion.
B046 [L1459-L1462]: Throughout early- to mid-September, in accordance with the boards authorization, Deutsche Bank contacted six potential strategic counterparties in the same or similar industries to gauge initial interest regarding a potential transaction with Penford. On September 9, 2014, Party A expressed interest in having further discussions regarding a transaction and Deutsche Bank forwarded Party A a nondisclosure and standstill agreement. Also on September 9, 2014, another strategic counterparty contacted by Deutsche Bank (referred to as Party B) expressed interest in further discussions, and Deutsche Bank forwarded a nondisclosure and standstill agreement to proceed with additional discussions with Party B.
B047 [L1464-L1466]: On September 10, 2014, a third potential strategic counterparty contacted by Deutsche Bank (referred to as Party C) expressed interest in pursuing a transaction, and Deutsche Bank forwarded Party C a nondisclosure and standstill agreement on September 11, 2014. Also on September 10, 2014, Mr. Malkoski, Mr. Fortnum and Mr. Saucier had a telephone conversation regarding certain diligence topics, including environmental matters, dates for Ingredion to visit Penfords facilities, antitrust considerations and other process-related items.
B048 [L1468-L1469]: On September 11, 2014, a fourth potential strategic counterparty contacted by Deutsche Bank (referred to as Party D) expressed interest, and Deutsche Bank forwarded a nondisclosure and standstill agreement to Party D.
B049 [L1471-L1472]: On September 12, 2014, Party B informed Deutsche Bank that it had decided not to move forward with discussions or sign a nondisclosure agreement with respect to a potential transaction.
B050 [L1474-L1475]: Also on September 12, 2014, Deutsche Bank left a voicemail for another strategic counterparty (referred to as Party E) regarding a potential transaction. In the following two weeks, Deutsche Bank also left several other voicemails for Party E regarding a potential transaction and received no response.
B051 [L1477-L1480]: On September 15, 2014, Penford and Party C executed a nondisclosure and standstill agreement, which included standard confidentiality restrictions and a standstill provision that automatically expired upon the public announcement of the entering into a definitive agreement for a sale of 50% or more of the capital stock of Penford, and Penford provided Party C with information regarding Penford including, but not limited to, information regarding Penfords corporate strategy, business segments, product applications and technologies, end markets, supply chain and manufacturing facilities, historical financial performance and financial projections.
B052 [L1482-L1482]: 28
B053 [L1485-L1489]: On September 17, 2014, Mr. Fortnum contacted Mr. Malkoski to update him on Ingredions board meeting that was held on September 16, 2014, reporting that Ingredions board had discussed Ingredions strategy, including the proposed acquisition of Penford. Mr. Fortnum indicated during the conversation that Ingredion could potentially increase its proposal from $18.00 to $18.25 or $18.50 per share on a fully diluted basis. Based on the $14.70 per share closing price of Penfords common stock on September 16, 2014, the last business day prior to receiving the revised indication of interest, a price of $18.25 to $18.50 represented a 24% premium and 26% premium, respectively. Mr. Fortnum and Mr. Malkoski discussed the status of due diligence, set dates for visits by Ingredions management team to Penfords facilities and also discussed a potential timeline for the transaction.
B054 [L1491-L1491]: On
B055 [L1492-L1494]: September 19, 2014, members of management briefed the Executive Committee on the status of the operation of the business, including an update on fourth quarter fiscal 2014 and first quarter 2015. Perkins Coie and Deutsche Bank were also present at the briefing. Deutsche Bank then reported on the status of the market check process and the ongoing due diligence process with Ingredion. The Executive Committee expressed disappointment with respect to Ingredions proposed price, but decided to proceed with the facility visits by Ingredion in an effort to provide Ingredion with additional information that would enhance Ingredions valuation of the Company.
B056 [L1496-L1497]: On September 23, 2014, Penford and Party D executed a nondisclosure and standstill agreement, which included standard confidentiality restrictions and a standstill provision that automatically expired upon the public announcement of the entering into a definitive agreement for a sale of 50% or more of the capital stock of Penford.
B057 [L1499-L1502]: Also on September 23, 2014, Mr. Fortnum and Mr. Malkoski had a call to discuss the potential transaction with Ingredion. Mr. Malkoski reported to Mr. Fortnum that Penfords Executive Committee was disappointed with the small increase from $18.00 to $18.25 or $18.50 per share, especially given the fact the Executive Committee believed that the information provided supported an increase in the valuation of the Company. Mr. Fortnum and Mr. Malkoski also discussed providing Ingredion with additional information to support an increased valuation of the Company. Mr. Malkoski indicated that further discussions would need to take place internally regarding the proposed transaction given the Executive Committees disappointment with the revised proposal.
B058 [L1504-L1512]: On September 24, 2014, the board of directors met with members of management and representatives of Perkins Coie and Deutsche Bank. Deutsche Bank reviewed with the board the status of negotiations with Ingredion, as well as the due diligence process. Deutsche Bank advised the board that Ingredion had indicated verbally that it could increase its price from $18.00 per share into the range of $18.25 to $18.50 per share. Deutsche Bank further reported to the board on the status of the market check process, stating that nondisclosure agreements had been executed with two potential counterparties, and that a third potential counterparty was reviewing a draft nondisclosure agreement. Deutsche Bank reported that based on discussions with all of the companies contacted in connection with the market process, the general level of interest of those companies in pursuing a transaction with Penford was not particularly strong. The board also discussed with management and Deutsche Bank whether the two largest companies in Penfords industry (referred to as Party F and Party G) should be approached regarding a potential transaction, including without limitation, the likely interest of those potential counterparties in a transaction with Penford, the ability of those potential counterparties to move forward with a transaction in the near future, as well as other factors, such as the risks and concerns regarding confidentiality and possible misuse of any proprietary or confidential information obtained as part of confidential negotiations regarding a possible strategic transaction with Penford. The board determined that Party F should be approached regarding a potential transaction with Penford, but due to the factors noted above, Party G should not be contacted. Deutsche Bank and Mr. Malkoski then reviewed with the board next steps in the negotiations with Ingredion and the market check process, noting that a management presentation was scheduled with one potential counterparty on the following day.
B059 [L1514-L1515]: On September 24, 2014, in accordance with the boards authorization, Deutsche Bank contacted Party F regarding a potential transaction with Penford.
B060 [L1517-L1518]: On September 25, 2014, members of Penfords management team provided a presentation to Party C regarding Penfords operations, specialty products, technology, supply chain and manufacturing, business segments, strategy, facilities, financial performance and financial projections.
B061 [L1520-L1520]: 29
B062 [L1523-L1524]: On September 29, 2014, Party F communicated to Deutsche Bank that a combination with Penford was not a suitable strategic fit and declined to pursue further discussions regarding a transaction.
B063 [L1526-L1530]: Also on September 29, 2014, the board met with members of management and representatives of Perkins Coie and Deutsche Bank. Deutsche Bank reviewed with the board a current status report on the market check process, including the recent management presentation provided to Party C and its discussions with Party F. Deutsche Bank also updated the board on the status of ongoing due diligence. The board discussed the current proposal from Ingredion, and Mr. Malkoski observed that the proposed price of $18.25 or $18.50 per share represented a significant increase from Ingredions initial indication of $16.00 (based on the 52-week high). However, the board indicated it would prefer to see the per share price increase by an additional $0.50 to $1.00 in order to increase the value ultimately to be received by Penfords shareholders. The board approved moving forward with further negotiations with Ingredion.
B064 [L1532-L1535]: On September 30, 2014, Penford and Party A executed a nondisclosure and standstill agreement, which included standard confidentiality restrictions and a standstill provision that automatically expired upon the public announcement of the entering into a definitive agreement for a sale of 50% or more of the capital stock of Penford, and Deutsche Bank provided Party A with information regarding Penfords operations, business segments, product applications and technologies, end markets, key leadership, supply chain and manufacturing facilities, historical financial performance and financial projections. Deutsche Bank informed Party A that Penford would not provide in-person management presentations unless there was an indication that Party As proposed offer price would be competitive, which Deutsche Bank advised would likely be over $20.00 per share.
B065 [L1537-L1540]: On October 1, 2014, Deutsche Bank contacted J. P. Morgan Securities to provide feedback on the potential price increase discussed on September 17, 2014, advising J. P. Morgan Securities that Penfords board of directors was disappointed with the $18.25 to $18.50 proposal, and that, based on Deutsche Banks discussions with Penfords board of directors, Penford expected a higher value based on the additional information regarding Penford that had been provided to Ingredion as part of the due diligence process. Deutsche Bank further explained that Penfords board of directors had wanted a purchase price of at least $20.00 per share.
B066 [L1542-L1548]: On October 2, 2014, Mr. Malkoski and Mr. Fortnum had a call to discuss the October 1 discussion between Deutsche Bank and J. P. Morgan Securities. Mr. Fortnum asked Mr. Malkoski to confirm whether Penfords board was unwilling to move forward with a transaction unless Ingredion was able to offer a price in the $20.00 per share range. Mr. Malkoski clarified that the board wanted that offer price, but was willing to proceed with negotiations. However, Mr. Malkoski then stated that because Ingredions proposal was below that preferred price, Penford felt it necessary to provide more information and schedule additional meetings in order to provide Ingredion with the support it needed to increase the offer price. Mr. Malkoski noted that the impact of this would be to delay a potential signing of a definitive agreement beyond Ingredions preferred timing for announcement of a transaction. Mr. Fortnum stated that Ingredion was still struggling to justify the valuation for a transaction at a higher price. Mr. Fortnum then stated that Ingredion was prepared to move forward based on a proposed price of $18.50 per share on a fully diluted basis. Mr. Malkoski responded that that price was unlikely to be high enough for Penfords board of directors to recommend the transaction to shareholders.
B067 [L1550-L1552]: On October 2, 2014, Penford received a letter from Ingredion regarding its indication of interest and increasing the proposed price to $19.00 per share of outstanding Penford capital stock on a fully diluted basis. Based on the $12.77 per share closing price of Penfords common stock on October 1, 2014, the last business day prior to receiving this revised indication of interest, the proposed price of $19.00 represented a 49% premium.
B068 [L1554-L1558]: On October 3, 2014, the board met with members of management and representatives of Perkins Coie and representatives of Deutsche Bank. Deutsche Bank reviewed with the board recent developments, including reviewing in detail the revised indication of interest from Ingredion increasing the proposed price per share of the Companys stock on a fully diluted basis to $19.00 per share. Deutsche Bank also provided the board with an update on the status of the market check process, stating that based on transaction size and market conditions, it was unlikely Party A would submit any indication of interest that would reflect the requested price of $20.00 per share. Deutsche Bank also updated the board that no other companies that had been contacted during the market check process indicated they would provide a proposal or other indication of interest. The board discussed the
B069 [L1560-L1560]: 30
B070 [L1563-L1564]: status of negotiations and the market check process, including whether Party G should be contacted given the status of the negotiations and the market check. After further discussion, with input from Deutsche Bank, the directors present at the board meeting unanimously directed management to proceed to negotiate and finalize a definitive agreement with Ingredion.
B071 [L1566-L1567]: Later on October 3, 2014, Mr. Malkoski informed Mr. Fortnum that the Penford board had authorized management to move forward with negotiating the draft merger agreement. Mr. Malkoski and Mr. Fortnum agreed that their teams should meet in person in Chicago the following week to review and negotiate the draft merger agreement.
B072 [L1569-L1571]: Later on October 3, 2014, Perkins Coie sent a revised draft of the merger agreement to Sidley Austin LLP (referred to as Sidley Austin), Ingredions legal counsel. On October 4, Deutsche Bank followed up with Party A regarding the potential transaction with Penford, pursuant to which Party A indicated any offer would be below $17.50 - $18.00 per share in cash. Deutsche Bank encouraged Party A to submit a letter of interest that could be reviewed by the board of directors.
B073 [L1573-L1576]: On October 6, 2014, Perkins Coie and Sidley Austin discussed the draft merger agreement and certain open issues, including, but not limited to, the requirement for significant shareholders to enter into voting and support agreements, the finalization of fiscal 2014 financial statements and delivery thereof as a closing condition, the scope of certain representations and warranties of the Company, the scope of the restrictions on the operations of Penford prior to closing, the non-solicitation obligations of the Company with respect to acquisition proposals, the circumstances under which a termination fee would be payable by the Company and the requirement to divest or otherwise agree to any business restrictions in the context of antitrust approvals.
B074 [L1578-L1580]: On October 7, 2014, Perkins Coie contacted Milbank, Tweed, Hadley & McCloy, LLP (referred to as Milbank), legal counsel to SEACOR, regarding Ingredions request for SEACOR to enter into a voting and support agreement, during which conversation, Milbank indicated that conceptually, a voting and support agreement to support the transaction would be acceptable, subject to discussions with SEACOR, provided that the voting and support agreement terminated in the event the executed merger agreement would be terminated in the event of a superior offer.
B075 [L1582-L1582]: On October 8, 2014, Sidley Austin circulated a revised draft of the merger agreement to Perkins Coie.
B076 [L1584-L1585]: Also on October 8, 2014, Deutsche Bank met with representatives from Party D, who indicated that it did not intend to move forward with discussions regarding a potential transaction involving the Company.
B077 [L1587-L1591]: On October 9, 2014, certain members of management of each of Penford and Ingredion, and representatives of their legal advisors, Perkins Coie and Sidley Austin, respectively, and their financial advisors, Deutsche Bank and J. P. Morgan Securities, respectively, met in person in Chicago at the offices of Sidley Austin to assist in reviewing and negotiating remaining open issues in the draft merger agreement, including with respect to the delivery of fiscal 2014 financial statements as a closing condition, the scope of certain representations and warranties of the Company, the scope of the restrictions on the operations of Penford prior to the closing of the merger agreement, the non-solicitation obligations of the Company with respect to acquisition proposals, the circumstances under which a termination fee would be payable by the Company and the requirement to divest or otherwise agree to any business restrictions in the context of antitrust approvals.
B078 [L1593-L1595]: On October 10, 2014, Sidley Austin provided an updated draft of the merger agreement to Perkins Coie, and on October 11, 2014, Perkins Coie sent a revised draft of the merger agreement to Sidley Austin. Also, on October 10, 2014, Sidley Austin distributed an initial draft of the voting and support agreement to be entered into with SEACOR. Later on October 11, 2014, Perkins Coie sent an initial draft of the disclosure letter to Sidley Austin, followed by a revised version on October 12, 2014.
B079 [L1597-L1598]: On October 11, 2014, Penford provided Ingredion with draft financial statements for the fiscal year ended August 31, 2014 (referred to as the 2014 draft financial statements), which reflected lower volume, lower revenue
B080 [L1600-L1600]: 31
B081 [L1603-L1605]: and lower EBITDA than was projected in the materials previously provided to Ingredion from Penfords strategic plan. Later on October 11, members of the accounting teams at Penford and Ingredion, as well as their respective financial advisors, Deutsche Bank and J. P. Morgan Securities, held a conference call to discuss Penfords 2014 draft financial statements, including the determination of the final numbers used in the draft financial statements. Also on October 11, 2014 Milbank and Sidley Austin discussed the proposed voting and support agreement.
B082 [L1607-L1607]: On
B083 [L1608-L1610]: October 12, 2014, members of the accounting teams at Penford and Ingredion, as well as their respective financial advisors, held another conference call to discuss the reconciliation of the 2014 draft financial statements compared to the materials previously provided to Ingredion from Penfords strategic plan. Also on October 12, 2014, Milbank discussed the voting and support agreement to be entered into by SEACOR with Sidley Austin, and distributed a revised draft of such voting and support agreement, and Sidley Austin and Perkins Coie had a teleconference to discuss certain open items in the merger agreement.
B084 [L1612-L1614]: On October 13, 2014, Mr. Malkoski and Mr. Fortnum discussed the 2014 draft financial statements as compared with the projections included in the materials provided to Ingredion from Penfords strategic plan. Mr. Fortnum stated that the figures reflected in the 2014 draft financial statements might have an adverse impact on Ingredions view of the valuation of the Company. Also on October 13, 2014, Milbank and Sidley Austin discussed and traded drafts of the voting and support agreement to be entered into by SEACOR.
B085 [L1616-L1617]: On October 13, 2014, Deutsche Bank had a discussion with representatives of Party A, who indicated that its value range for a potential transaction had been reduced from $17.50 - $18.00 per share to $16.00 - $18.00 per share, due to increased volatility in the markets.
B086 [L1619-L1620]: Also on October 13, 2014, Sidley Austin circulated a revised draft of the merger agreement to Perkins Coie. Perkins Coie and Sidley Austin also discussed the draft disclosure letter and later on October 13, 2014, Perkins Coie and Sidley Austin exchanged revised drafts of the disclosure letter.
B087 [L1622-L1623]: On October 14, 2014, Mr. Fortnum called Mr. Malkoski to confirm the proposed price of $19.00 and discuss finalizing the draft merger agreement and proceeding with the transaction as previously planned.
B088 [L1625-L1626]: Also on October 14, 2014, Perkins Coie and Sidley Austin exchanged successive drafts of the merger agreement and disclosure letter, and discussed the updated drafts, and Milbank and Sidley Austin finalized the voting and support agreement to be entered into by SEACOR.
B089 [L1628-L1630]: Later on October 14, 2014, Party A provided a formal letter with its indication of interest with respect to an acquisition of the Company at a price of $16.00 per share, citing increased volatility in the markets as the reason for the decrease in the offer price. Based on the $11.07 per share closing price of Penfords common stock as of October 13, 2014, the day immediately prior to receiving this indication of interest, the offer price of $16.00 per share represented a 45% premium.
B090 [L1632-L1632]: On
B091 [L1633-L1639]: October 14, 2014, a meeting of the board was held, at which members of Penfords management and representatives of Penfords legal and financial advisors were present. Perkins Coie provided a review, and led a discussion, of the fiduciary duties of Penfords board under Washington law, including in connection with strategic proposals involving a change in control of Penford. The board discussed these issues, asked questions of management and of Perkins Coie, and received guidance and advice. Mr. Malkoski then reported to the board on recent discussions and negotiations with Ingredion regarding the proposed transaction, including the lower than expected figures reflected in the 2014 draft financial statements, and that Ingredion had confirmed that it desired to promptly enter into the merger agreement and that the purchase price per share, on a fully diluted basis, remained at $19.00 per share. Deutsche Bank then reviewed with the board the key terms of the proposed transaction and the process that the Company followed after it was first contacted by Ingredion, including the market check process. Deutsche Bank reported that as part of the market check process, it had contacted a total of six potential counterparties, two of which declined to enter into nondisclosure agreements, one of which never returned Deutsche Banks voicemail regarding a potential transaction and the remaining three of which either did not move forward in a timely manner or made a lower indication of value. Deutsche Bank then reviewed with the
B092 [L1641-L1641]: 32
B093 [L1644-L1649]: board its financial analysis of the transaction, and noted that based on the $11.07 per share closing price of Penfords common stock as of October 13, 2014, the day immediately prior to the board meeting, the purchase price of $19.00 per share represented a 72% premium. Following discussion, Deutsche Bank rendered to the board its oral opinion that as of October 14, 2014 and based on and subject to various assumptions, limitations, qualifications and conditions stated in its opinion, the merger consideration (as defined in the merger agreement) provided pursuant to the merger agreement was fair, from a financial point of view, to the holders of the Companys common stock. Perkins Coie then reviewed with the board material terms of the merger agreement, including without limitation the representations and warranties, covenants, including those covenants that would restrict operations prior to the closing of the transaction, the process for responding to, and the limitations with respect to soliciting, any competing offers and the conditions to closing. Perkins Coie also reviewed with the board the terms of the voting and support agreement to be entered into with SEACOR and Ingredion, including certain limited restrictions on Penford with respect to calling an annual or special meeting for the election of directors.
B094 [L1651-L1653]: Believing they were fully informed, on October 14, 2014, the Penford board unanimously determined that the merger agreement, the voting and support agreement, the merger and other transactions contemplated thereby were in the best interest of Penford and its shareholders and approved the merger agreement and the merger and recommended approval of the merger agreement to Penfords shareholders.
B095 [L1655-L1656]: During the evening on October 14, 2014, Penford and Ingredion finalized and executed the merger agreement, and Penford, Ingredion and SEACOR executed the voting and support agreement. Penford and Ingredion issued press releases announcing the transaction on October 15, 2014 prior to the opening of trading.
</chronology_blocks>

<evidence_checklist>
### Dated actions to extract
- [ ] **0001193125-14-455030:E0305** L1287-L1289 (date: July 8, 2014; terms: meeting)
- [ ] **0001193125-14-455030:E0306** L1291-L1293 (date: July 9, 2014; terms: meeting, proposed)
- [ ] **0001193125-14-455030:E0308** L1295-L1297 (date: July 11, 2014; terms: meeting)
- [ ] **0001193125-14-455030:E0310** L1299-L1304 (date: July 17, 2014; value: $16.00 per share; terms: meeting, met)
- [ ] **0001193125-14-455030:E0312** L1306-L1307 (date: July; terms: discussed, meeting)
- [ ] **0001193125-14-455030:E0313** L1312-L1317 (date: July 19, 2014; value: $16.00 per share; terms: discussed, offer, proposed)
- [ ] **0001193125-14-455030:E0315** L1319-L1320 (date: July 20, 2014; terms: executed)
- [ ] **0001193125-14-455030:E0317** L1322-L1325 (date: July 22, 2014; terms: meeting)
- [ ] **0001193125-14-455030:E0318** L1330-L1332 (date: July 23, 2014; terms: discussed, meeting, offer)
- [ ] **0001193125-14-455030:E0319** L1334-L1340 (date: July 24, 2014; terms: discussed, executed, meeting)
- [ ] **0001193125-14-455030:E0323** L1342-L1343 (date: July 25, 2014; terms: meeting)
- [ ] **0001193125-14-455030:E0324** L1345-L1348 (date: July 30, 2014; terms: discussed, meeting, sent)
- [ ] **0001193125-14-455030:E0327** L1350-L1352 (date: August 1, 2014; actors: Party A; terms: discussed, meeting, sent)
- [ ] **0001193125-14-455030:E0329** L1354-L1355 (date: August 5, 2014; terms: discussed, meeting)
- [ ] **0001193125-14-455030:E0330** L1357-L1359 (date: August 6, 2014; value: $17.00 per share; terms: meeting, met, proposal)
- [ ] **0001193125-14-455030:E0332** L1361-L1364 (date: August 10, 2014; value: $18.00
per share; terms: proposed, received, sent)
- [ ] **0001193125-14-455030:E0335** L1366-L1368 (date: August 11, 2014; terms: discussed, meeting, met)
- [ ] **0001193125-14-455030:E0336** L1373-L1382 (date: may; terms: meeting, sent)
- [ ] **0001193125-14-455030:E0338** L1384-L1388 (date: August 11, 2014; actors: Party A; terms: discussed, met, offer)
- [ ] **0001193125-14-455030:E0340** L1390-L1399 (date: August 13, 2014; terms: discussed, meeting, met)
- [ ] **0001193125-14-455030:E0342** L1401-L1402 (date: August 14, 2014; terms: contacted, proposal)
- [ ] **0001193125-14-455030:E0343** L1407-L1410 (date: August 21, 2014; terms: authorized, discussed, proposed)
- [ ] **0001193125-14-455030:E0346** L1412-L1413 (date: August 15, 2014; terms: discussed)
- [ ] **0001193125-14-455030:E0348** L1415-L1416 (date: August 19, 2014; terms: discussed, meeting)
- [ ] **0001193125-14-455030:E0351** L1418-L1419 (date: August; terms: declined, executed)
- [ ] **0001193125-14-455030:E0354** L1421-L1424 (date: August 21, 2014; actors: P. Morgan; terms: sent)
- [ ] **0001193125-14-455030:E0357** L1428-L1438 (date: August 28, 2014; terms: authorized, contacted, discussed)
- [ ] **0001193125-14-455030:E0360** L1443-L1444 (date: August 28, 2014; terms: meeting, proposal)
- [ ] **0001193125-14-455030:E0361** L1446-L1446 (date: August 28, 2014; actors: P. Morgan; terms: sent)
- [ ] **0001193125-14-455030:E0364** L1448-L1450 (date: September; terms: meeting, proposed)
- [ ] **0001193125-14-455030:E0366** L1452-L1454 (date: September 3,
2014; terms: discussed, sent)
- [ ] **0001193125-14-455030:E0371** L1459-L1462 (date: September; actors: Party A, Party B; terms: contacted)
- [ ] **0001193125-14-455030:E0374** L1464-L1466 (date: September 10, 2014; actors: Party C; terms: contacted)
- [ ] **0001193125-14-455030:E0377** L1468-L1469 (date: September 11, 2014; actors: Party D; terms: contacted)
- [ ] **0001193125-14-455030:E0381** L1474-L1475 (date: September 12, 2014; actors: Party E; terms: received)
- [ ] **0001193125-14-455030:E0383** L1477-L1480 (date: September 15, 2014; actors: Party C; terms: executed)
- [ ] **0001193125-14-455030:E0387** L1485-L1489 (date: September 17, 2014; value: $18.00 to $18.25; terms: contacted, discussed, meeting)
- [ ] **0001193125-14-455030:E0391** L1491-L1494 (date: September 19, 2014; terms: proposed, sent)
- [ ] **0001193125-14-455030:E0393** L1496-L1497 (date: September 23, 2014; actors: Party D; terms: executed)
- [ ] **0001193125-14-455030:E0397** L1499-L1502 (date: September 23, 2014; value: $18.00 to $18.25; terms: discussed, proposal, proposed)
- [ ] **0001193125-14-455030:E0399** L1504-L1512 (date: September 24, 2014; actors: Party F, Party G; value: $18.00 per share; terms: contacted, discussed, executed)
- [ ] **0001193125-14-455030:E0404** L1514-L1515 (date: September 24, 2014; actors: Party F; terms: contacted)
- [ ] **0001193125-14-455030:E0406** L1517-L1518 (date: September 25, 2014; actors: Party C; terms: sent)
- [ ] **0001193125-14-455030:E0408** L1523-L1524 (date: September 29, 2014; actors: Party F; terms: declined)
- [ ] **0001193125-14-455030:E0410** L1526-L1530 (date: September 29, 2014; actors: Party C, Party F; value: $18.25; terms: discussed, met, proposal)
- [ ] **0001193125-14-455030:E0414** L1532-L1535 (date: September 30, 2014; actors: Party A; value: $20.00 per share; terms: executed, offer, proposed)
- [ ] **0001193125-14-455030:E0419** L1537-L1540 (date: October 1, 2014; actors: P. Morgan; value: $18.25 to $18.50; terms: contacted, discussed, proposal)
- [ ] **0001193125-14-455030:E0423** L1542-L1548 (date: October 2, 2014; actors: P. Morgan; value: $20.00 per share; terms: meeting, offer, proposal)
- [ ] **0001193125-14-455030:E0426** L1550-L1552 (date: October 2, 2014; value: $19.00 per share; terms: proposed, received, sent)
- [ ] **0001193125-14-455030:E0429** L1554-L1558 (date: October 3, 2014; actors: Party A; value: $19.00 per
share; terms: contacted, discussed, met)
- [ ] **0001193125-14-455030:E0433** L1566-L1567 (date: October 3, 2014; terms: authorized)
- [ ] **0001193125-14-455030:E0436** L1569-L1571 (date: October 3, 2014; actors: Party A; value: $17.50 - $18.00 per share; terms: offer, sent)
- [ ] **0001193125-14-455030:E0440** L1573-L1576 (date: October 6, 2014; terms: discussed, proposal, sent)
- [ ] **0001193125-14-455030:E0444** L1578-L1580 (date: October 7, 2014; terms: contacted, executed, offer)
- [ ] **0001193125-14-455030:E0448** L1584-L1585 (date: October 8, 2014; actors: Party D; terms: met, sent)
- [ ] **0001193125-14-455030:E0450** L1587-L1591 (date: October 9, 2014; actors: P. Morgan; terms: met, proposal, sent)
- [ ] **0001193125-14-455030:E0454** L1593-L1595 (date: October 10, 2014; terms: entered into, sent)
- [ ] **0001193125-14-455030:E0456** L1603-L1605 (date: October; actors: P. Morgan; terms: discussed, proposed)
- [ ] **0001193125-14-455030:E0458** L1607-L1610 (date: October 12, 2014; terms: discussed, entered into)
- [ ] **0001193125-14-455030:E0461** L1612-L1614 (date: October 13, 2014; terms: discussed, entered into)
- [ ] **0001193125-14-455030:E0462** L1616-L1617 (date: October 13, 2014; actors: Party A; value: $17.50 - $18.00 per share; terms: sent)
- [ ] **0001193125-14-455030:E0465** L1619-L1620 (date: October 13, 2014; terms: discussed)
- [ ] **0001193125-14-455030:E0467** L1622-L1623 (date: October 14, 2014; value: $19.00; terms: called, proposed)
- [ ] **0001193125-14-455030:E0471** L1625-L1626 (date: October 14, 2014; terms: discussed, entered into)
- [ ] **0001193125-14-455030:E0473** L1628-L1630 (date: October 14, 2014; actors: Party A; value: $16.00 per share; terms: offer, sent)
- [ ] **0001193125-14-455030:E0477** L1632-L1639 (date: October 14, 2014; value: $19.00 per share; terms: contacted, declined, discussed)
- [ ] **0001193125-14-455030:E0481** L1644-L1649 (date: October 13, 2014; value: $11.07 per share; terms: entered into, meeting, offer)
- [ ] **0001193125-14-455030:E0486** L1655-L1656 (date: October 14, 2014; terms: executed)

### Financial terms to capture
- [ ] **0001193125-14-455030:E0311** L1299-L1304 (date: July 17, 2014; value: $16.00 per share; terms: $12.00 per share, $16.00 per share)
- [ ] **0001193125-14-455030:E0314** L1312-L1317 (date: July 19, 2014; value: $16.00 per share; terms: $16.00 per share)
- [ ] **0001193125-14-455030:E0331** L1357-L1359 (date: August 6, 2014; value: $17.00 per share; terms: $17.00 per share)
- [ ] **0001193125-14-455030:E0333** L1361-L1364 (date: August 10, 2014; value: $18.00
per share; terms: $12.10 per share, $18.00
per share)
- [ ] **0001193125-14-455030:E0388** L1485-L1489 (date: September 17, 2014; value: $18.00 to $18.25; terms: $14.70 per share, $18.00 to $18.25, $18.25 to $18.50)
- [ ] **0001193125-14-455030:E0398** L1499-L1502 (date: September 23, 2014; value: $18.00 to $18.25; terms: $18.00 to $18.25, $18.50 per share)
- [ ] **0001193125-14-455030:E0400** L1504-L1512 (date: September 24, 2014; actors: Party F, Party G; value: $18.00 per share; terms: $18.00 per share, $18.25 to $18.50 per share)
- [ ] **0001193125-14-455030:E0411** L1526-L1530 (date: September 29, 2014; actors: Party C, Party F; value: $18.25; terms: $0.50 to $1.00, $16.00, $18.25)
- [ ] **0001193125-14-455030:E0415** L1532-L1535 (date: September 30, 2014; actors: Party A; value: $20.00 per share; terms: $20.00 per share)
- [ ] **0001193125-14-455030:E0420** L1537-L1540 (date: October 1, 2014; actors: P. Morgan; value: $18.25 to $18.50; terms: $18.25 to $18.50, $20.00 per share)
- [ ] **0001193125-14-455030:E0424** L1542-L1548 (date: October 2, 2014; actors: P. Morgan; value: $20.00 per share; terms: $18.50 per share, $20.00 per share)
- [ ] **0001193125-14-455030:E0427** L1550-L1552 (date: October 2, 2014; value: $19.00 per share; terms: $12.77 per share, $19.00, $19.00 per share)
- [ ] **0001193125-14-455030:E0430** L1554-L1558 (date: October 3, 2014; actors: Party A; value: $19.00 per
share; terms: $19.00 per
share, $20.00 per share)
- [ ] **0001193125-14-455030:E0437** L1569-L1571 (date: October 3, 2014; actors: Party A; value: $17.50 - $18.00 per share; terms: $17.50 - $18.00 per share)
- [ ] **0001193125-14-455030:E0463** L1616-L1617 (date: October 13, 2014; actors: Party A; value: $17.50 - $18.00 per share; terms: $16.00 - $18.00 per share, $17.50 - $18.00 per share)
- [ ] **0001193125-14-455030:E0468** L1622-L1623 (date: October 14, 2014; value: $19.00; terms: $19.00)
- [ ] **0001193125-14-455030:E0474** L1628-L1630 (date: October 14, 2014; actors: Party A; value: $16.00 per share; terms: $11.07 per share, $16.00 per share)
- [ ] **0001193125-14-455030:E0478** L1632-L1639 (date: October 14, 2014; value: $19.00 per share; terms: $19.00 per share)
- [ ] **0001193125-14-455030:E0482** L1644-L1649 (date: October 13, 2014; value: $11.07 per share; terms: $11.07 per share, $19.00 per share)

### Actors to identify
- [ ] **0001193125-14-455030:E0302** L1272-L1273 (terms: shareholder)
- [ ] **0001193125-14-455030:E0303** L1281-L1282 (terms: party )
- [ ] **0001193125-14-455030:E0307** L1291-L1293 (date: July 9, 2014; terms: counsel)
- [ ] **0001193125-14-455030:E0309** L1295-L1297 (date: July 11, 2014; terms: shareholder)
- [ ] **0001193125-14-455030:E0320** L1334-L1340 (date: July 24, 2014; terms: advisor, advisors, counsel)
- [ ] **0001193125-14-455030:E0325** L1345-L1348 (date: July 30, 2014; terms: advisor, financial advisor, shareholder)
- [ ] **0001193125-14-455030:E0328** L1350-L1352 (date: August 1, 2014; actors: Party A; terms: party )
- [ ] **0001193125-14-455030:E0337** L1373-L1382 (date: may; terms: advisor, financial advisor, party )
- [ ] **0001193125-14-455030:E0339** L1384-L1388 (date: August 11, 2014; actors: Party A; terms: party )
- [ ] **0001193125-14-455030:E0344** L1407-L1410 (date: August 21, 2014; terms: advisor, advisors)
- [ ] **0001193125-14-455030:E0349** L1415-L1416 (date: August 19, 2014; terms: shareholder)
- [ ] **0001193125-14-455030:E0355** L1421-L1424 (date: August 21, 2014; actors: P. Morgan; terms: advisor, financial advisor)
- [ ] **0001193125-14-455030:E0358** L1428-L1438 (date: August 28, 2014; terms: advisor, financial advisor)
- [ ] **0001193125-14-455030:E0362** L1446-L1446 (date: August 28, 2014; actors: P. Morgan)
- [ ] **0001193125-14-455030:E0369** L1456-L1457 (date: September 6, 2014; actors: P. Morgan; terms: shareholder)
- [ ] **0001193125-14-455030:E0372** L1459-L1462 (date: September; actors: Party A, Party B; terms: party )
- [ ] **0001193125-14-455030:E0375** L1464-L1466 (date: September 10, 2014; actors: Party C; terms: party )
- [ ] **0001193125-14-455030:E0378** L1468-L1469 (date: September 11, 2014; actors: Party D; terms: party )
- [ ] **0001193125-14-455030:E0380** L1471-L1472 (date: September 12, 2014; actors: Party B; terms: party )
- [ ] **0001193125-14-455030:E0382** L1474-L1475 (date: September 12, 2014; actors: Party E; terms: party )
- [ ] **0001193125-14-455030:E0384** L1477-L1480 (date: September 15, 2014; actors: Party C; terms: party )
- [ ] **0001193125-14-455030:E0394** L1496-L1497 (date: September 23, 2014; actors: Party D; terms: party )
- [ ] **0001193125-14-455030:E0401** L1504-L1512 (date: September 24, 2014; actors: Party F, Party G; value: $18.00 per share; terms: party )
- [ ] **0001193125-14-455030:E0405** L1514-L1515 (date: September 24, 2014; actors: Party F; terms: party )
- [ ] **0001193125-14-455030:E0407** L1517-L1518 (date: September 25, 2014; actors: Party C; terms: party )
- [ ] **0001193125-14-455030:E0409** L1523-L1524 (date: September 29, 2014; actors: Party F; terms: party )
- [ ] **0001193125-14-455030:E0412** L1526-L1530 (date: September 29, 2014; actors: Party C, Party F; value: $18.25; terms: party , shareholder)
- [ ] **0001193125-14-455030:E0416** L1532-L1535 (date: September 30, 2014; actors: Party A; value: $20.00 per share; terms: party )
- [ ] **0001193125-14-455030:E0421** L1537-L1540 (date: October 1, 2014; actors: P. Morgan; value: $18.25 to $18.50)
- [ ] **0001193125-14-455030:E0425** L1542-L1548 (date: October 2, 2014; actors: P. Morgan; value: $20.00 per share; terms: shareholder)
- [ ] **0001193125-14-455030:E0431** L1554-L1558 (date: October 3, 2014; actors: Party A; value: $19.00 per
share; terms: party )
- [ ] **0001193125-14-455030:E0432** L1563-L1564 (actors: Party G; terms: party )
- [ ] **0001193125-14-455030:E0438** L1569-L1571 (date: October 3, 2014; actors: Party A; value: $17.50 - $18.00 per share; terms: counsel, party )
- [ ] **0001193125-14-455030:E0441** L1573-L1576 (date: October 6, 2014; terms: shareholder)
- [ ] **0001193125-14-455030:E0445** L1578-L1580 (date: October 7, 2014; terms: counsel)
- [ ] **0001193125-14-455030:E0449** L1584-L1585 (date: October 8, 2014; actors: Party D; terms: party )
- [ ] **0001193125-14-455030:E0451** L1587-L1591 (date: October 9, 2014; actors: P. Morgan; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-14-455030:E0457** L1603-L1605 (date: October; actors: P. Morgan; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-14-455030:E0459** L1607-L1610 (date: October 12, 2014; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-14-455030:E0464** L1616-L1617 (date: October 13, 2014; actors: Party A; value: $17.50 - $18.00 per share; terms: party )
- [ ] **0001193125-14-455030:E0475** L1628-L1630 (date: October 14, 2014; actors: Party A; value: $16.00 per share; terms: party )
- [ ] **0001193125-14-455030:E0479** L1632-L1639 (date: October 14, 2014; value: $19.00 per share; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-14-455030:E0484** L1651-L1653 (date: October 14, 2014; terms: shareholder)

### Process signals to check
- [ ] **0001193125-14-455030:E0304** L1281-L1282 (terms: confidentiality agreement)
- [ ] **0001193125-14-455030:E0321** L1334-L1340 (date: July 24, 2014; terms: strategic alternatives)
- [ ] **0001193125-14-455030:E0326** L1345-L1348 (date: July 30, 2014; terms: strategic alternatives)
- [ ] **0001193125-14-455030:E0341** L1390-L1399 (date: August 13, 2014; terms: strategic alternatives)
- [ ] **0001193125-14-455030:E0345** L1407-L1410 (date: August 21, 2014; terms: due diligence, exclusivity, management presentation)
- [ ] **0001193125-14-455030:E0347** L1412-L1413 (date: August 15, 2014; terms: standstill)
- [ ] **0001193125-14-455030:E0350** L1415-L1416 (date: August 19, 2014; terms: non-disclosure)
- [ ] **0001193125-14-455030:E0352** L1418-L1419 (date: August; terms: standstill)
- [ ] **0001193125-14-455030:E0356** L1426-L1426 (date: August 26, 2014; terms: due diligence)
- [ ] **0001193125-14-455030:E0359** L1428-L1438 (date: August 28, 2014; terms: due diligence, management presentation, standstill)
- [ ] **0001193125-14-455030:E0363** L1446-L1446 (date: August 28, 2014; actors: P. Morgan; terms: due diligence)
- [ ] **0001193125-14-455030:E0365** L1448-L1450 (date: September; terms: due diligence)
- [ ] **0001193125-14-455030:E0367** L1452-L1454 (date: September 3,
2014; terms: draft merger agreement, due diligence, management presentation)
- [ ] **0001193125-14-455030:E0373** L1459-L1462 (date: September; actors: Party A, Party B; terms: standstill)
- [ ] **0001193125-14-455030:E0376** L1464-L1466 (date: September 10, 2014; actors: Party C; terms: standstill)
- [ ] **0001193125-14-455030:E0379** L1468-L1469 (date: September 11, 2014; actors: Party D; terms: standstill)
- [ ] **0001193125-14-455030:E0385** L1477-L1480 (date: September 15, 2014; actors: Party C; terms: standstill)
- [ ] **0001193125-14-455030:E0389** L1485-L1489 (date: September 17, 2014; value: $18.00 to $18.25; terms: due diligence)
- [ ] **0001193125-14-455030:E0392** L1491-L1494 (date: September 19, 2014; terms: due diligence)
- [ ] **0001193125-14-455030:E0395** L1496-L1497 (date: September 23, 2014; actors: Party D; terms: standstill)
- [ ] **0001193125-14-455030:E0402** L1504-L1512 (date: September 24, 2014; actors: Party F, Party G; value: $18.00 per share; terms: due diligence, management presentation)
- [ ] **0001193125-14-455030:E0413** L1526-L1530 (date: September 29, 2014; actors: Party C, Party F; value: $18.25; terms: due diligence, management presentation)
- [ ] **0001193125-14-455030:E0417** L1532-L1535 (date: September 30, 2014; actors: Party A; value: $20.00 per share; terms: management presentation, standstill)
- [ ] **0001193125-14-455030:E0422** L1537-L1540 (date: October 1, 2014; actors: P. Morgan; value: $18.25 to $18.50; terms: due diligence)
- [ ] **0001193125-14-455030:E0434** L1566-L1567 (date: October 3, 2014; terms: draft merger agreement)
- [ ] **0001193125-14-455030:E0442** L1573-L1576 (date: October 6, 2014; terms: draft merger agreement)
- [ ] **0001193125-14-455030:E0452** L1587-L1591 (date: October 9, 2014; actors: P. Morgan; terms: draft merger agreement)
- [ ] **0001193125-14-455030:E0469** L1622-L1623 (date: October 14, 2014; value: $19.00; terms: draft merger agreement)

### Outcome facts to verify
- [ ] **0001193125-14-455030:E0316** L1319-L1320 (date: July 20, 2014; terms: executed)
- [ ] **0001193125-14-455030:E0322** L1334-L1340 (date: July 24, 2014; terms: executed)
- [ ] **0001193125-14-455030:E0334** L1361-L1364 (date: August 10, 2014; value: $18.00
per share; terms: closing)
- [ ] **0001193125-14-455030:E0353** L1418-L1419 (date: August; terms: executed)
- [ ] **0001193125-14-455030:E0368** L1452-L1454 (date: September 3,
2014; terms: merger agreement)
- [ ] **0001193125-14-455030:E0370** L1456-L1457 (date: September 6, 2014; actors: P. Morgan; terms: merger agreement)
- [ ] **0001193125-14-455030:E0386** L1477-L1480 (date: September 15, 2014; actors: Party C; terms: executed)
- [ ] **0001193125-14-455030:E0390** L1485-L1489 (date: September 17, 2014; value: $18.00 to $18.25; terms: closing)
- [ ] **0001193125-14-455030:E0396** L1496-L1497 (date: September 23, 2014; actors: Party D; terms: executed)
- [ ] **0001193125-14-455030:E0403** L1504-L1512 (date: September 24, 2014; actors: Party F, Party G; value: $18.00 per share; terms: executed)
- [ ] **0001193125-14-455030:E0418** L1532-L1535 (date: September 30, 2014; actors: Party A; value: $20.00 per share; terms: executed)
- [ ] **0001193125-14-455030:E0428** L1550-L1552 (date: October 2, 2014; value: $19.00 per share; terms: closing)
- [ ] **0001193125-14-455030:E0435** L1566-L1567 (date: October 3, 2014; terms: merger agreement)
- [ ] **0001193125-14-455030:E0439** L1569-L1571 (date: October 3, 2014; actors: Party A; value: $17.50 - $18.00 per share; terms: merger agreement)
- [ ] **0001193125-14-455030:E0443** L1573-L1576 (date: October 6, 2014; terms: closing, merger agreement, termination fee)
- [ ] **0001193125-14-455030:E0446** L1578-L1580 (date: October 7, 2014; terms: executed, merger agreement, terminated)
- [ ] **0001193125-14-455030:E0447** L1582-L1582 (date: October 8, 2014; terms: merger agreement)
- [ ] **0001193125-14-455030:E0453** L1587-L1591 (date: October 9, 2014; actors: P. Morgan; terms: closing, merger agreement, termination fee)
- [ ] **0001193125-14-455030:E0455** L1593-L1595 (date: October 10, 2014; terms: merger agreement)
- [ ] **0001193125-14-455030:E0460** L1607-L1610 (date: October 12, 2014; terms: merger agreement)
- [ ] **0001193125-14-455030:E0466** L1619-L1620 (date: October 13, 2014; terms: merger agreement)
- [ ] **0001193125-14-455030:E0470** L1622-L1623 (date: October 14, 2014; value: $19.00; terms: merger agreement)
- [ ] **0001193125-14-455030:E0472** L1625-L1626 (date: October 14, 2014; terms: merger agreement)
- [ ] **0001193125-14-455030:E0476** L1628-L1630 (date: October 14, 2014; actors: Party A; value: $16.00 per share; terms: closing)
- [ ] **0001193125-14-455030:E0480** L1632-L1639 (date: October 14, 2014; value: $19.00 per share; terms: merger agreement)
- [ ] **0001193125-14-455030:E0483** L1644-L1649 (date: October 13, 2014; value: $11.07 per share; terms: closing, merger agreement)
- [ ] **0001193125-14-455030:E0485** L1651-L1653 (date: October 14, 2014; terms: merger agreement)
- [ ] **0001193125-14-455030:E0487** L1655-L1656 (date: October 14, 2014; terms: executed, merger agreement)
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