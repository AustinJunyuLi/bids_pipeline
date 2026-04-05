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
window_id: w1
</deal_context>

<chronology_blocks>
B062 [L1490-L1492]: Also during this time period, at the direction of our chairman on behalf of the special committee, representatives of BofA Merrill Lynch contacted Company H and indicated that the price range Company H had submitted was not sufficient to move them forward in the process. The Company H representative was told that Company H could submit a revised indication of interest, which would be considered by the special committee.
B063 [L1494-L1496]: On May 16, 2013, a regularly scheduled board meeting was held. Messrs. Cook, Saman and Morales and representatives from BofA Merrill Lynch were in attendance. Our board of directors discussed with representatives of BofA Merrill Lynch the status of the process, preliminary valuation considerations and next steps in the process.
B064 [L1498-L1499]: After the meeting, at the direction of the board, BofA Merrill Lynch sent final round process letters and a draft merger agreement to WDC and Company D, requesting a response by May 28, 2013.
B065 [L1501-L1502]: On May 23, 2013, representatives of Company H contacted a representative of BofA Merrill Lynch and indicated that Company H remained interested in a potential acquisition of the company but that Company H was not able to increase its indicated value range.
B066 [L1504-L1508]: On May 28, 2013, WDC submitted a written second-round indication of interest at a price per share of $9.15 in cash, with a mark-up of the merger agreement and drafts of ancillary agreements, including a voting agreement to be entered into by each of sTecs officers and directors, a covenant not to sue to be entered into by Mr. Manouch Moshayedi, a technical services agreement to be entered into by Mr. Mark Moshayedi, a non-competition agreement to be entered into by each of Mr. Manouch Moshayedi and Mr. Mark Moshayedi, and a landlords consent to assignment to be entered into by an affiliate of Messrs. Moshayedi. The technical services agreement to be entered into by Mr. Mark Moshayedi did not contain any financial terms. This indication of interest contemplated signing definitive documentation with respect to a transaction by no later than June 3, 2013.
B067 [L1510-L1512]: Also on May 28, 2013, a representative of Company D contacted representatives of BofA Merrill Lynch and indicated that Company D continued to have an interest in a potential acquisition and understood they needed to move meaningfully on value; however, the representative stated that Company D needed approximately two weeks of additional time to continue its ongoing due diligence review and to submit a written indication of interest and mark-up of the merger agreement.
B068 [L1514-L1522]: On May 29, 2013, our board of directors held a telephonic special meeting. Messrs. Cook, Saman and Morales, Mr. Mike Higa, our Senior Vice President of Finance, and representatives from BofA Merrill Lynch and Gibson Dunn also attended the meeting. The board discussed the companys updated financial model on a standalone basis. The BofA Merrill Lynch representative reported on communications with both Company D and WDC in response to sTecs request for non-binding proposals on May 28, 2013, and on the most recent communications with Company H. BofA Merrill Lynch reported that WDC had presented an indication of interest of $9.15 per share, which the representative of WDC had described as the highest price that WDC was willing to offer and that the WDC representative had also disclosed that there were internal concerns regarding the price at WDC. BofA Merrill Lynch further reported that Company D had stated that it continued to be interested in an acquisition but that it needed approximately two weeks to continue its ongoing due diligence review and to submit a proposal. The board of directors then discussed with BofA Merrill Lynch financial aspects of WDCs proposal. The board of directors discussed with Messrs. Moshayedi the terms of the ancillary agreements that WDC had requested be executed by Messrs. Moshayedi and their affiliates. Finally, the board of directors also discussed the legal considerations related to the process with Gibson Dunn. After discussion, our board of directors directed BofA Merrill Lynch to request a best and final proposal from WDC and a best and final written proposal from Company D by May 30, 2013. Messrs. Moshayedi were also reminded of the direction that had been discussed with them from time-to-time during the strategic review process that they should not negotiate any financial terms relating to their agreements with an acquirer, including WDC, prior to final agreement with the potential acquirer on the price to be paid to the companys shareholders. Later that day,
B069 [L1524-L1524]: 30
B070 [L1527-L1527]: as directed by the board of directors, BofA Merrill Lynch requested a best and final proposal from WDC and a best and final written proposal from Company D.
B071 [L1529-L1530]: On May 30, 2013, representatives of WDC verbally indicated that WDCs indication of interest to acquire the company at a price of $9.15 per share was WDCs best possible price, and reiterated the concern of WDC regarding the price. The WDC representative also stated that WDC continued to be focused on being in a position to announce a transaction on June 3, 2013.
B072 [L1532-L1533]: Also on May 30, 2013 representatives of Company D reconfirmed they would require additional time to submit a written indication of interest, however, the Company D representatives also indicated they continued to believe they could be competitive on price if given additional time.
B073 [L1535-L1539]: Also on May 30, 2013, the board of directors held a telephonic special meeting. Messrs. Cook, Saman, Higa and Morales, and representatives from BofA Merrill Lynch, Latham & Watkins and Gibson Dunn also attended the meeting. The BofA Merrill Lynch representative reported on the communications from both WDC and Company D in response to BofA Merrill Lynchs communication on May 29, 2013 seeking the best and final proposals from those companies. The representative from Latham & Watkins discussed the implications of entry into the covenant not to sue that WDC had requested be executed by Mr. Manouch Moshayedi. Mr. Manouch Moshayedi indicated that his lawyers were continuing to review the proposed ancillary agreements. Our board of directors unanimously determined to move forward with WDC on their proposed terms, including endeavoring to complete diligence and negotiation of the merger agreement and ancillary agreements to be in a position to announce a transaction on June 3, 2013. The board directed that representatives of BofA Merrill Lynch communicate the boards decision to WDC.
B074 [L1541-L1542]: Later, on May 30, 2013, as directed by the board, representatives of BofA Merrill Lynch informed WDC that sTec would move forward to effect a transaction at a purchase price of $9.15 per share, subject to satisfactory negotiations of the merger agreement and ancillary agreements.
B075 [L1544-L1545]: On May 31, 2013, a representative of WDC communicated to BofA Merrill Lynch that WDC was reevaluating its interest in acquiring sTec, and that WDC was not prepared to move forward with a transaction with sTec at that time. In addition, WDC discontinued their due diligence efforts with the company at that time. BofA Merrill Lynch then contacted the companys officers and Dr. Daly to report the communication from WDC.
B076 [L1547-L1549]: On May 31, 2013, our board of directors held a telephonic special meeting, attended by four independent directors, Dr. Daly and Messrs. Bahri, Ball and Colpitts. Mr. Saman and a representative from Gibson Dunn were also in attendance. Dr. Daly reported on the communications from WDC that WDC had decided to reconsider its interest in acquiring sTec and that it was not prepared to move forward with a transaction with sTec at that time. Our board of directors then discussed potential next steps. Gibson Dunn reviewed certain legal considerations related to the process.
B077 [L1551-L1552]: At the request of our board of directors, representatives of BofA Merrill Lynch had a call with representatives of Company D on which they informed Company Ds representatives that timing for sTecs process had been delayed, and that Company D had an opportunity to continue in the process. The Company D representatives indicated that they would consider this opportunity.
B078 [L1554-L1554]: On June 1, 2013, sTec posted materials responsive to the diligence requests of Company D to the data room.
B079 [L1556-L1557]: Over the period from June 1 to June 10, 2013, at the direction of the board, representatives of BofA Merrill Lynch had several discussions with representatives of WDC. WDC indicated that a difference of opinion had emerged internally, that WDCs prior bidding approach to an acquisition of sTec had been rejected, and that they
B080 [L1559-L1559]: 31
B081 [L1562-L1562]: were reconsidering their interest in a transaction with sTec. The representatives of BofA Merrill Lynch reported these discussions to our chairman and the companys officers.
B082 [L1564-L1565]: On June 5, 2013 representatives of Company D contacted representatives of BofA Merrill Lynch and indicated that Company D would not be in a position to actively conduct due diligence for more than two weeks and was disengaging from the process. The representatives of BofA Merrill Lynch reported these discussions to our chairman and the companys officers.
B083 [L1567-L1571]: On June 10, 2013, WDC submitted a revised written indication of interest to acquire the company at a price range of $6.60 to $7.10 per share in cash. The representative from WDC also communicated to BofA Merrill Lynch that WDC had given serious consideration to not proceeding with a transaction, that WDC did not view the acquisition of sTec as essential to its SSD strategy in light of other available alternatives (including internal development efforts), and that according to WDC certain business factors related to the company had also influenced WDCs decision to lower the price from its May 30, 2013 written indication of interest at $9.15 per share in cash, as well as a change in its bidding strategy from the prior approach it had adopted. The representative from WDC also communicated that WDC was otherwise prepared to move forward on the transaction terms previously proposed on May 28, 2013.
B084 [L1573-L1578]: On June 11, 2013, our board of directors held a telephonic special meeting. Messrs. Saman, Higa and Morales, and representatives from BofA Merrill Lynch and Gibson Dunn also attended the meeting. The board of directors reviewed WDCs written indication of interest to acquire sTec at a purchase price in the range of $6.60 to $7.10 per share in cash and recent communications with WDC. The board of directors discussed with BofA Merrill Lynch the indication of interest and the related communications with WDC. Our board of directors discussed the legal considerations related to the process with Gibson Dunn. Our board of directors then discussed potential responses to WDC, and the considerations related to each. The board of directors directed BofA Merrill Lynch to communicate to WDC the board of directors disappointment in the latest proposal and the significant change from its prior proposal, that the board would not respond to a proposal with a range, and that if WDC desired to proceed, WDC must submit a proposal reflecting its best offer, and provide confirmation that such offer was supported by WDCs senior management.
B085 [L1580-L1582]: Later that day, as directed by the board of directors, representatives of BofA Merrill Lynch informed WDC that our board of directors would not consider a proposal with a range of value and requested that WDC submit a specific proposal reflecting its best offer and provide confirmation that such offer was supported by WDCs senior management.
B086 [L1584-L1586]: On June 14, 2013, WDC submitted a written indication of interest of $6.85 per share in cash and indicated it could be in a position to announce a transaction on June 24, 2013. In communicating the revised proposal to BofA Merrill Lynch, the WDC representative again stated that WDC was only interested in proceeding with the transaction at a purchase price of $6.85 per share, WDCs best and final price, for the reasons previously noted, and otherwise on the transaction terms previously proposed on May 28, 2013.
B087 [L1588-L1593]: On June 15, 2013, the special committee of the board of directors held a telephonic meeting. Messrs. Cook, Saman and Morales and representatives from BofA Merrill Lynch and Gibson Dunn were in attendance. BofA Merrill Lynch reported on their communications with WDC, including WDCs indication of interest on June 14, 2013 to acquire the company at a purchase price of $6.85 per share in cash. The members of the special committee then discussed sTecs outlook for the second and third quarters of 2013 and over the next 12 to 24 months, including the timing and impact of sTecs proposed cost reductions on the go-forward operations of the company, and the projected impact on sTecs cash position if sTec entered into an acquisition agreement with WDC and was contractually unable to make the proposed cost reductions. Gibson Dunn discussed certain legal considerations related to the process. The members of the special committee discussed with BofA Merrill Lynch certain financial matters relating to WDCs proposal. The committee continued discussion of sTecs alternative
B088 [L1595-L1595]: 32
B089 [L1598-L1601]: options to accepting WDCs proposal, including the benefits and risks of such alternatives, and the potential responses to WDCs proposal, including the possibility of making a counterproposal to WDC. The special committee determined, based on the communications from WDC, that it was unlikely that WDC would raise its price further and there was a significant risk that WDC would withdraw the indication of interest if sTec responded with a counterproposal. After further discussion, the special committee unanimously determined that they believed that it was in the best interests of sTec and its shareholders to move forward with a transaction with WDC on the terms set forth in WDCs indication of interest received on June 14, 2013, subject to negotiating final terms of the merger agreement and ancillary agreements relating to such transaction, and voted to recommend the same to the board of directors.
B090 [L1603-L1610]: Also on June 15, 2013, immediately after the special committee meeting, our board of directors held a telephonic special meeting. Messrs. Cook, Saman, Higa and Morales and representatives from BofA Merrill Lynch and Gibson Dunn were in attendance. Dr. Daly reported on the special committees decision. BofA Merrill Lynch reported on their recent communications with WDC, as shared with the special committee, including that WDC had communicated that $6.85 per share was its best and final price. The board of directors then discussed certain considerations relating to the companys business. The board of directors then discussed certain legal considerations related to the process with the representatives of Gibson Dunn. The board of directors discussed with BofA Merrill Lynch certain financial matters relating to WDCs indication of interest. The board of directors further discussed with Messrs. Mark Moshayedi and Manouch Moshayedi the terms of the ancillary agreements that they were being requested to execute. After further discussion, the board members present unanimously determined that they believed that it was in the best interests of sTec and its shareholders to move forward with a transaction with WDC on the terms set forth in WDCs proposal received on June 14, 2013, subject to negotiating final terms of the merger agreement and ancillary agreements relating to such transaction, with a goal of announcing a transaction on June 24, 2013 and instructed BofA Merrill Lynch to communicate the boards authorization to move forward to WDC.
B091 [L1612-L1614]: On June 16, 2013, as directed by our board of directors, representatives of BofA Merrill Lynch informed WDC that our board of directors had authorized moving forward with a transaction with WDC on the terms set forth in WDCs proposal received June 14, 2013, at a price of $6.85 per share, subject to negotiating final terms of the merger agreement and ancillary agreements relating to such transaction.
B092 [L1616-L1617]: From June 16 to June 22, 2013, WDC conducted additional due diligence, including confirmatory due diligence calls. Also, on June 18, 2013, sTec and WDC entered into a clean team agreement to allow certain representatives of WDC access to further information in the data room.
B093 [L1619-L1625]: On June 17, 2013, representatives from Paul Hastings LLP ( Paul Hastings), counsel to Messrs. Moshayedi, and Shearman & Sterling LLP ( Shearman), counsel to WDC, commenced negotiating the terms of the covenant not to sue, and the other agreements that Messrs. Moshayedi were being asked to execute. Negotiations of such agreements continued through June 23, 2013. The draft covenant not to sue provided by WDC required Mr. Manouch Moshayedi to relinquish all rights to indemnification under his existing arrangements with the company, but also provided that WDC would continue to pay Mr. Moshayedis legal fees in connection with the civil action filed against Mr. Moshayedi by the SEC on July 29, 2012 and release him from any obligation to reimburse the company for such legal fees under his indemnification agreement with sTec. Among other matters, in the negotiations that commenced on June 17, 2013, Paul Hastings negotiated for the continued right of indemnification for Mr. Moshayedi, subject to a cap of $20 million with respect to indemnification (other than for defense costs) related to the SECs civil action. Thereafter, Messrs. Moshayedi proposed that the company enter into letter agreements to conform their existing severance and change in control agreements to the arrangements negotiated with WDC.
B094 [L1627-L1628]: On June 19, 2013, Gibson Dunn submitted to Shearman proposed revisions to the merger agreement markup received from Shearman on May 28, 2013. On June 20, 2013, Shearman circulated a revised draft of the merger agreement to Gibson Dunn, indicating that WDC was not willing to further negotiate the terms of the merger
B095 [L1630-L1630]: 33
B096 [L1633-L1639]: agreement. Among other matters, Gibson Dunn communicated to Shearman sTecs desire to include in the merger agreement a general waiver of all dont ask dont waive provisions in its non-disclosure agreements with potential bidders. Shearman communicated that WDC would not agree to this waiver, and in addition, WDC would view it as improper if sTec unilaterally waived these provisions, indicating that WDC may not move forward with the transaction if sTec unilaterally waived these provisions. Gibson Dunn discussed this communication from WDC and other proposed changes to the merger agreement with Dr. Daly and Mr. Saman. Based on the history of the discussions with the potential bidders with dont ask dont waive provisions in their non-disclosure agreements that would continue in effect after sTec entered into an acquisition agreement, Dr. Daly, on behalf of the special committee, believed the possibility that any of these potential bidders would be willing and able to make a superior proposal was remote. Specifically, Company E and Company F had expressed an interest solely in purchasing certain assets of sTec, and Company H had repeatedly stated it could not increase its price above the range of $5.00 to $5.75 per share. Based upon direction from Dr. Daly in view of WDCs indication that it was not willing to negotiate further, and may not proceed with the transaction if sTec did not agree to certain terms, Gibson Dunn focused on a limited number of issues in the merger agreement in its continued discussions with Shearman through June 23, 2013.
B097 [L1641-L1649]: On June 23, 2013, the special committee held a telephonic meeting. Messrs. Cook, Saman and Morales and representatives from BofA Merrill Lynch and Gibson Dunn were in attendance. Gibson Dunn reviewed with the directors the terms and conditions of the proposed form of merger agreement. The special committee reviewed with representatives of BofA Merrill Lynch the process that had been conducted and the contacts with the potential acquirers. The special committee discussed the potential ability and interest of Company E, Company F and Company H to make a superior proposal to the $6.85 per share proposal of WDC, and the special committee determined that the possibility of such a proposal was remote and that it was in the best interests of the shareholders to continue with the WDC transaction notwithstanding the dont ask dont waive provisions in such parties non-disclosure agreements. BofA Merrill Lynch then reviewed its financial analysis of the merger consideration. Gibson Dunn reviewed the significant terms and conditions of the ancillary agreements to be entered into by Messrs. Moshayedi, including the covenant not to sue and the consulting agreements, and the financial terms thereof. The directors discussed the terms of the merger agreement, such ancillary agreements and the letter agreements proposed by Messrs. Moshayedi to be entered into relating to the terms and conditions of payments under their existing severance and change in control agreements. Following further discussion, the special committee unanimously determined that the merger agreement and the transactions contemplated thereby, including the merger, were in the best interests of the companys shareholders, and approved and adopted the merger agreement, and unanimously determined to recommend to our board of directors that the board approve and adopt the merger and the merger agreement and that the board recommend that the shareholders vote in favor of the approval and adoption of the merger agreement and the merger.
B098 [L1651-L1658]: Immediately thereafter, on June 23, 2013, our board of directors held a telephonic special meeting. Messrs. Cook, Saman, Higa and Morales and representatives from BofA Merrill Lynch and Gibson Dunn were in attendance. Dr. Daly reported on the special committees decision. The board reviewed with BofA Merrill Lynch the process that had been conducted at the boards direction and the contacts with each of the potential acquirers. BofA Merrill Lynch then reviewed its financial analysis of the merger consideration and delivered to our board of directors an oral opinion, which was confirmed by delivery of a written opinion dated June 23, 2013, to the effect that, as of that date and based on and subject to various assumptions and limitations described in its opinion, the merger consideration to be received by holders of sTec common stock (other than sTec, WDC, Merger Sub and their respective affiliates and dissenting shareholders) was fair, from a financial point of view, to such holders. Gibson Dunn reviewed the significant terms and conditions of the merger agreement, including, but not limited to, certain operating restrictions on sTec from the signing date of the merger agreement until the closing date of the transaction, the ability of and conditions under which our board of directors could terminate the agreement to accept a superior proposal or change its recommendation of the merger, the situations in which sTec may have to pay a termination fee, the amount of such a termination fee, the situations in which WDC may have to pay a termination fee, the amount of such a termination fee and related considerations, and the conditions to closing of the transaction. Gibson Dunn reviewed with our board of directors its fiduciary duties and related
B099 [L1660-L1660]: 34
B100 [L1663-L1669]: terms and conditions of the merger agreement and other transaction considerations. Our board of directors discussed the potential ability and interest of Company E, Company F and Company H to make a superior proposal to the $6.85 per share proposal of WDC, and our board of directors determined that the possibility of such a proposal was remote and that it was in the best interests of the shareholders to continue with the WDC transaction notwithstanding the dont ask dont waive provisions in such parties non-disclosure agreements. Gibson Dunn then reviewed with our board of directors the terms of the ancillary agreements, including the voting agreements, and the shares subject to such agreements, and the ancillary agreements to be entered into by WDC with Messrs. Moshayedi, including the covenant not to sue and the consulting agreements, and the financial terms thereof. Finally, Gibson Dunn reviewed the terms of the letter agreements proposed by Messrs. Moshayedi to be entered into relating to the terms and conditions of payments under their existing severance and change in control agreements. The directors discussed the terms of the merger agreement, the ancillary agreements and the letter agreements. Following further discussion, our board of directors unanimously determined that the merger agreement and the transactions contemplated thereby, including the merger, were in the best interests of the companys shareholders, and approved and adopted the merger agreement. Our board of directors also unanimously recommended that the companys shareholders approve and adopt the merger agreement.
B101 [L1671-L1673]: On June 23, 2013, sTec, WDC, and Merger Sub executed the merger agreement; each of our officers and directors executed their respective voting agreements with WDC; Mr. Manouch Moshayedi and WDC executed the covenant not to sue, the consulting services agreement and a non-competition agreement; Mr. Mark Moshayedi and WDC executed the technical services agreement and a non-competition agreement; sTec and Messrs. Moshayedi executed the letter agreements; and an affiliate of Messrs. Moshayedi and WDC executed a landlords consent to assignment.
B102 [L1675-L1676]: On June 24, 2013, prior to the opening of trading on the U. S. stock exchanges, WDC and sTec announced in a joint press release the execution of the merger agreement.
B103 [L1678-L1678]: sTecs Reasons for the Merger
B104 [L1680-L1680]: On June 23, 2013, our board of directors, upon the unanimous recommendation of the special committee:
B105 [L1682-L1682]: unanimously determined that the merger agreement, the merger and the other transactions contemplated by the merger agreement are in the best interests
B106 [L1684-L1686]: recommended that the shareholders of the company vote in favor of the approval and adoption of the merger agreement and the transactions contemplated thereby, subject to the right of the board to withhold, withdraw, qualify or modify its recommendation in accordance with the terms of the merger agreement. ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
B107 [L1688-L1689]: In the course of reaching the determinations and making the recommendation described above, our board of directors consulted with its outside legal and financial advisors and with sTecs management and considered a number of factors that it believed supported its decision, including the following (which are not listed in any relative order of importance):
B108 [L1691-L1691]: Best Alternative for Maximizing Shareholder Value. Our board of directors considered that receipt of the merger consideration of $6.85 per share
B109 [L1693-L1693]: sTecs historical operating and financial performance, its competitive position, its future prospects, and its resources at hand, including cash;
B110 [L1695-L1695]: 35
B111 [L1698-L1698]: the heightened risks and expanding challenges faced by the company in the dynamic storage industry, including increased competition, declining ASPs,
B112 [L1700-L1700]: the other strategic alternatives reasonably available to sTec, including the alternative of remaining a stand-alone public company and other strategic
B113 [L1702-L1702]: our board of directors belief that sTec is unlikely to achieve a sustainable trading price for its common stock in excess of the $6.85 per share
B114 [L1704-L1704]: our board of directors belief that, with the assistance of its financial advisor, it had negotiated the highest price per share for sTecs
B115 [L1706-L1706]: the contact, either directly or through the companys management or advisors, with 17 other potential buyers over the course of the strategic
B116 [L1708-L1708]: our board of directors belief that the process conducted by sTec, in conjunction with its advisors, had resulted in the highest price reasonably
B117 [L1710-L1710]: Greater Certainty of Value. Our board of directors considered that the proposed merger consideration is to be paid entirely in cash, which
</chronology_blocks>

<overlap_context>
B060 [L1484-L1485]: During the weeks of May 13 and May 20, 2013, sTec, representatives of Latham & Watkins LLP ( Latham & Watkins), litigation counsel to sTec and Mr. Manouch Moshayedi, held due diligence calls and meetings with WDC and Company D, which representatives of BofA Merrill Lynch also attended.
B061 [L1487-L1487]: 29
B118 [L1712-L1712]: Attractive Value. Our board of directors considered the value of the merger consideration of $6.85 per share in cash attractive relative to
B119 [L1714-L1714]: High Likelihood of Completion. Our board of directors considered the high degree of certainty that the closing will be achieved, particularly in
</overlap_context>

<evidence_checklist>
### Dated actions to extract
- [ ] **0001193125-13-325730:E0360** L1484-L1485 (date: May; actors: Company D, Merrill Lynch; terms: meeting, sent)
- [ ] **0001193125-13-325730:E0365** L1494-L1496 (date: May 16, 2013; actors: Merrill Lynch; terms: discussed, meeting, sent)
- [ ] **0001193125-13-325730:E0367** L1498-L1499 (date: May 28, 2013; actors: Company D, Merrill
Lynch; terms: meeting, sent)
- [ ] **0001193125-13-325730:E0371** L1501-L1502 (date: May 23, 2013; actors: Company H, Merrill Lynch; terms: contacted, sent)
- [ ] **0001193125-13-325730:E0373** L1504-L1508 (date: May 28, 2013; value: $9.15; terms: entered into, sent, submitted)
- [ ] **0001193125-13-325730:E0376** L1510-L1512 (date: May 28, 2013; actors: Company D, Merrill Lynch; terms: contacted, sent)
- [ ] **0001193125-13-325730:E0380** L1514-L1522 (date: May 29, 2013; actors: Company D, Company H, Merrill Lynch; value: $9.15 per share; terms: discussed, executed, meeting)
- [ ] **0001193125-13-325730:E0387** L1529-L1530 (date: May 30, 2013; value: $9.15 per share; terms: sent)
- [ ] **0001193125-13-325730:E0389** L1532-L1533 (date: May 30, 2013; actors: Company D; terms: sent)
- [ ] **0001193125-13-325730:E0391** L1535-L1539 (date: May 30, 2013; actors: Company D, Merrill Lynch; terms: discussed, executed, meeting)
- [ ] **0001193125-13-325730:E0395** L1541-L1542 (date: May 30, 2013; actors: Merrill Lynch; value: $9.15 per share; terms: sent)
- [ ] **0001193125-13-325730:E0399** L1544-L1545 (date: May 31, 2013; actors: Merrill Lynch; terms: contacted, sent)
- [ ] **0001193125-13-325730:E0402** L1547-L1549 (date: May 31, 2013; terms: discussed, meeting, sent)
- [ ] **0001193125-13-325730:E0405** L1556-L1557 (date: June; actors: Merrill Lynch; terms: sent)
- [ ] **0001193125-13-325730:E0408** L1564-L1565 (date: June 5, 2013; actors: Company D, Merrill Lynch; terms: contacted, sent)
- [ ] **0001193125-13-325730:E0411** L1567-L1571 (date: June 10, 2013; actors: Merrill Lynch; value: $6.60 to $7.10
per share; terms: proposed, sent, submitted)
- [ ] **0001193125-13-325730:E0414** L1573-L1578 (date: June 11, 2013; actors: Merrill Lynch; value: $6.60 to $7.10 per share; terms: discussed, meeting, offer)
- [ ] **0001193125-13-325730:E0418** L1584-L1586 (date: June 14, 2013; actors: Merrill Lynch; value: $6.85 per share; terms: proposal, proposed, sent)
- [ ] **0001193125-13-325730:E0422** L1588-L1593 (date: June 15, 2013; actors: Merrill Lynch; value: $6.85 per share; terms: discussed, entered into, meeting)
- [ ] **0001193125-13-325730:E0425** L1598-L1601 (date: June 14, 2013; terms: proposal, received)
- [ ] **0001193125-13-325730:E0428** L1603-L1610 (date: June 15, 2013; actors: Merrill Lynch; value: $6.85 per share; terms: discussed, meeting, proposal)
- [ ] **0001193125-13-325730:E0433** L1612-L1614 (date: June 16, 2013; actors: Merrill Lynch; value: $6.85 per share; terms: authorized, proposal, received)
- [ ] **0001193125-13-325730:E0437** L1616-L1617 (date: June; terms: entered into, sent)
- [ ] **0001193125-13-325730:E0439** L1619-L1625 (date: June 17, 2013; value: $20; terms: proposed, sent)
- [ ] **0001193125-13-325730:E0442** L1627-L1628 (date: June 19, 2013; terms: proposed, received, submitted)
- [ ] **0001193125-13-325730:E0444** L1633-L1639 (date: may; actors: Company E, Company F, Company H; value: $5.00 to $5.75 per share; terms: discussed, entered into, proposal)
- [ ] **0001193125-13-325730:E0449** L1641-L1649 (date: June 23, 2013; actors: Company E, Company F, Company H, Merrill Lynch; value: $6.85 per share; terms: discussed, entered into, meeting)
- [ ] **0001193125-13-325730:E0454** L1651-L1658 (date: June 23, 2013; actors: Merrill Lynch; terms: delivered, meeting, proposal)
- [ ] **0001193125-13-325730:E0462** L1671-L1673 (date: June 23, 2013; terms: executed, sent)
- [ ] **0001193125-13-325730:E0464** L1675-L1676 (date: June 24, 2013; terms: announced)

### Financial terms to capture
- [ ] **0001193125-13-325730:E0374** L1504-L1508 (date: May 28, 2013; value: $9.15; terms: $9.15)
- [ ] **0001193125-13-325730:E0381** L1514-L1522 (date: May 29, 2013; actors: Company D, Company H, Merrill Lynch; value: $9.15 per share; terms: $9.15 per share)
- [ ] **0001193125-13-325730:E0388** L1529-L1530 (date: May 30, 2013; value: $9.15 per share; terms: $9.15 per share)
- [ ] **0001193125-13-325730:E0396** L1541-L1542 (date: May 30, 2013; actors: Merrill Lynch; value: $9.15 per share; terms: $9.15 per share)
- [ ] **0001193125-13-325730:E0412** L1567-L1571 (date: June 10, 2013; actors: Merrill Lynch; value: $6.60 to $7.10
per share; terms: $6.60 to $7.10
per share, $9.15 per share)
- [ ] **0001193125-13-325730:E0415** L1573-L1578 (date: June 11, 2013; actors: Merrill Lynch; value: $6.60 to $7.10 per share; terms: $6.60 to $7.10 per share)
- [ ] **0001193125-13-325730:E0419** L1584-L1586 (date: June 14, 2013; actors: Merrill Lynch; value: $6.85 per share; terms: $6.85 per share)
- [ ] **0001193125-13-325730:E0423** L1588-L1593 (date: June 15, 2013; actors: Merrill Lynch; value: $6.85 per share; terms: $6.85 per share)
- [ ] **0001193125-13-325730:E0429** L1603-L1610 (date: June 15, 2013; actors: Merrill Lynch; value: $6.85 per share; terms: $6.85 per share)
- [ ] **0001193125-13-325730:E0434** L1612-L1614 (date: June 16, 2013; actors: Merrill Lynch; value: $6.85 per share; terms: $6.85 per share)
- [ ] **0001193125-13-325730:E0440** L1619-L1625 (date: June 17, 2013; value: $20; terms: $20)
- [ ] **0001193125-13-325730:E0445** L1633-L1639 (date: may; actors: Company E, Company F, Company H; value: $5.00 to $5.75 per share; terms: $5.00 to $5.75 per share)
- [ ] **0001193125-13-325730:E0450** L1641-L1649 (date: June 23, 2013; actors: Company E, Company F, Company H, Merrill Lynch; value: $6.85 per share; terms: $6.85 per share)
- [ ] **0001193125-13-325730:E0458** L1663-L1669 (actors: Company E, Company F, Company H; value: $6.85 per share; terms: $6.85 per share)
- [ ] **0001193125-13-325730:E0471** L1691-L1691 (value: $6.85 per share; terms: $6.85 per share)
- [ ] **0001193125-13-325730:E0474** L1702-L1702 (value: $6.85 per share; terms: $6.85 per share)
- [ ] **0001193125-13-325730:E0478** L1712-L1712 (value: $6.85 per share; terms: $6.85 per share)

### Actors to identify
- [ ] **0001193125-13-325730:E0361** L1484-L1485 (date: May; actors: Company D, Merrill Lynch; terms: counsel)
- [ ] **0001193125-13-325730:E0364** L1490-L1492 (actors: Company H, Merrill Lynch; terms: special committee)
- [ ] **0001193125-13-325730:E0366** L1494-L1496 (date: May 16, 2013; actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0368** L1498-L1499 (date: May 28, 2013; actors: Company D, Merrill
Lynch)
- [ ] **0001193125-13-325730:E0372** L1501-L1502 (date: May 23, 2013; actors: Company H, Merrill Lynch)
- [ ] **0001193125-13-325730:E0377** L1510-L1512 (date: May 28, 2013; actors: Company D, Merrill Lynch)
- [ ] **0001193125-13-325730:E0382** L1514-L1522 (date: May 29, 2013; actors: Company D, Company H, Merrill Lynch; value: $9.15 per share; terms: shareholder)
- [ ] **0001193125-13-325730:E0385** L1527-L1527 (actors: Company D, Merrill Lynch)
- [ ] **0001193125-13-325730:E0390** L1532-L1533 (date: May 30, 2013; actors: Company D)
- [ ] **0001193125-13-325730:E0392** L1535-L1539 (date: May 30, 2013; actors: Company D, Merrill Lynch)
- [ ] **0001193125-13-325730:E0397** L1541-L1542 (date: May 30, 2013; actors: Merrill Lynch; value: $9.15 per share)
- [ ] **0001193125-13-325730:E0400** L1544-L1545 (date: May 31, 2013; actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0403** L1551-L1552 (actors: Company D, Merrill Lynch)
- [ ] **0001193125-13-325730:E0404** L1554-L1554 (date: June 1, 2013; actors: Company D)
- [ ] **0001193125-13-325730:E0406** L1556-L1557 (date: June; actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0407** L1562-L1562 (actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0409** L1564-L1565 (date: June 5, 2013; actors: Company D, Merrill Lynch)
- [ ] **0001193125-13-325730:E0413** L1567-L1571 (date: June 10, 2013; actors: Merrill Lynch; value: $6.60 to $7.10
per share)
- [ ] **0001193125-13-325730:E0416** L1573-L1578 (date: June 11, 2013; actors: Merrill Lynch; value: $6.60 to $7.10 per share)
- [ ] **0001193125-13-325730:E0417** L1580-L1582 (actors: Merrill Lynch)
- [ ] **0001193125-13-325730:E0420** L1584-L1586 (date: June 14, 2013; actors: Merrill Lynch; value: $6.85 per share)
- [ ] **0001193125-13-325730:E0424** L1588-L1593 (date: June 15, 2013; actors: Merrill Lynch; value: $6.85 per share; terms: special committee)
- [ ] **0001193125-13-325730:E0426** L1598-L1601 (date: June 14, 2013; terms: shareholder, special committee)
- [ ] **0001193125-13-325730:E0430** L1603-L1610 (date: June 15, 2013; actors: Merrill Lynch; value: $6.85 per share; terms: shareholder, special committee)
- [ ] **0001193125-13-325730:E0435** L1612-L1614 (date: June 16, 2013; actors: Merrill Lynch; value: $6.85 per share)
- [ ] **0001193125-13-325730:E0441** L1619-L1625 (date: June 17, 2013; value: $20; terms: counsel)
- [ ] **0001193125-13-325730:E0446** L1633-L1639 (date: may; actors: Company E, Company F, Company H; value: $5.00 to $5.75 per share; terms: special committee)
- [ ] **0001193125-13-325730:E0451** L1641-L1649 (date: June 23, 2013; actors: Company E, Company F, Company H, Merrill Lynch; value: $6.85 per share; terms: shareholder, special committee)
- [ ] **0001193125-13-325730:E0455** L1651-L1658 (date: June 23, 2013; actors: Merrill Lynch; terms: shareholder, special committee)
- [ ] **0001193125-13-325730:E0459** L1663-L1669 (actors: Company E, Company F, Company H; value: $6.85 per share; terms: shareholder)
- [ ] **0001193125-13-325730:E0466** L1680-L1680 (date: June 23, 2013; terms: special committee)
- [ ] **0001193125-13-325730:E0468** L1684-L1686 (terms: shareholder)
- [ ] **0001193125-13-325730:E0470** L1688-L1689 (terms: advisor, advisors, financial advisor)
- [ ] **0001193125-13-325730:E0472** L1691-L1691 (value: $6.85 per share; terms: shareholder)
- [ ] **0001193125-13-325730:E0475** L1704-L1704 (terms: advisor, financial advisor)
- [ ] **0001193125-13-325730:E0476** L1706-L1706 (terms: advisor, advisors)
- [ ] **0001193125-13-325730:E0477** L1708-L1708 (terms: advisor, advisors)

### Process signals to check
- [ ] **0001193125-13-325730:E0362** L1484-L1485 (date: May; actors: Company D, Merrill Lynch; terms: due diligence)
- [ ] **0001193125-13-325730:E0369** L1498-L1499 (date: May 28, 2013; actors: Company D, Merrill
Lynch; terms: draft merger agreement, process letter)
- [ ] **0001193125-13-325730:E0378** L1510-L1512 (date: May 28, 2013; actors: Company D, Merrill Lynch; terms: due diligence)
- [ ] **0001193125-13-325730:E0383** L1514-L1522 (date: May 29, 2013; actors: Company D, Company H, Merrill Lynch; value: $9.15 per share; terms: best and final, due diligence)
- [ ] **0001193125-13-325730:E0386** L1527-L1527 (actors: Company D, Merrill Lynch; terms: best and final)
- [ ] **0001193125-13-325730:E0393** L1535-L1539 (date: May 30, 2013; actors: Company D, Merrill Lynch; terms: best and final)
- [ ] **0001193125-13-325730:E0401** L1544-L1545 (date: May 31, 2013; actors: Merrill Lynch; terms: due diligence)
- [ ] **0001193125-13-325730:E0410** L1564-L1565 (date: June 5, 2013; actors: Company D, Merrill Lynch; terms: due diligence)
- [ ] **0001193125-13-325730:E0421** L1584-L1586 (date: June 14, 2013; actors: Merrill Lynch; value: $6.85 per share; terms: best and final)
- [ ] **0001193125-13-325730:E0431** L1603-L1610 (date: June 15, 2013; actors: Merrill Lynch; value: $6.85 per share; terms: best and final)
- [ ] **0001193125-13-325730:E0438** L1616-L1617 (date: June; terms: due diligence)
- [ ] **0001193125-13-325730:E0447** L1633-L1639 (date: may; actors: Company E, Company F, Company H; value: $5.00 to $5.75 per share; terms: non-disclosure, superior proposal)
- [ ] **0001193125-13-325730:E0452** L1641-L1649 (date: June 23, 2013; actors: Company E, Company F, Company H, Merrill Lynch; value: $6.85 per share; terms: non-disclosure, superior proposal)
- [ ] **0001193125-13-325730:E0456** L1651-L1658 (date: June 23, 2013; actors: Merrill Lynch; terms: superior proposal)
- [ ] **0001193125-13-325730:E0460** L1663-L1669 (actors: Company E, Company F, Company H; value: $6.85 per share; terms: non-disclosure, superior proposal)
- [ ] **0001193125-13-325730:E0473** L1700-L1700 (terms: strategic alternatives)

### Outcome facts to verify
- [ ] **0001193125-13-325730:E0363** L1484-L1485 (date: May; actors: Company D, Merrill Lynch; terms: litigation)
- [ ] **0001193125-13-325730:E0370** L1498-L1499 (date: May 28, 2013; actors: Company D, Merrill
Lynch; terms: merger agreement)
- [ ] **0001193125-13-325730:E0375** L1504-L1508 (date: May 28, 2013; value: $9.15; terms: merger agreement)
- [ ] **0001193125-13-325730:E0379** L1510-L1512 (date: May 28, 2013; actors: Company D, Merrill Lynch; terms: merger agreement)
- [ ] **0001193125-13-325730:E0384** L1514-L1522 (date: May 29, 2013; actors: Company D, Company H, Merrill Lynch; value: $9.15 per share; terms: executed)
- [ ] **0001193125-13-325730:E0394** L1535-L1539 (date: May 30, 2013; actors: Company D, Merrill Lynch; terms: executed, merger agreement)
- [ ] **0001193125-13-325730:E0398** L1541-L1542 (date: May 30, 2013; actors: Merrill Lynch; value: $9.15 per share; terms: merger agreement)
- [ ] **0001193125-13-325730:E0427** L1598-L1601 (date: June 14, 2013; terms: merger agreement, vote)
- [ ] **0001193125-13-325730:E0432** L1603-L1610 (date: June 15, 2013; actors: Merrill Lynch; value: $6.85 per share; terms: merger agreement)
- [ ] **0001193125-13-325730:E0436** L1612-L1614 (date: June 16, 2013; actors: Merrill Lynch; value: $6.85 per share; terms: merger agreement)
- [ ] **0001193125-13-325730:E0443** L1627-L1628 (date: June 19, 2013; terms: merger agreement)
- [ ] **0001193125-13-325730:E0448** L1633-L1639 (date: may; actors: Company E, Company F, Company H; value: $5.00 to $5.75 per share; terms: merger agreement)
- [ ] **0001193125-13-325730:E0453** L1641-L1649 (date: June 23, 2013; actors: Company E, Company F, Company H, Merrill Lynch; value: $6.85 per share; terms: merger agreement, vote)
- [ ] **0001193125-13-325730:E0457** L1651-L1658 (date: June 23, 2013; actors: Merrill Lynch; terms: closing, merger agreement, termination fee)
- [ ] **0001193125-13-325730:E0461** L1663-L1669 (actors: Company E, Company F, Company H; value: $6.85 per share; terms: merger agreement)
- [ ] **0001193125-13-325730:E0463** L1671-L1673 (date: June 23, 2013; terms: executed, merger agreement)
- [ ] **0001193125-13-325730:E0465** L1675-L1676 (date: June 24, 2013; terms: merger agreement)
- [ ] **0001193125-13-325730:E0467** L1682-L1682 (terms: merger agreement)
- [ ] **0001193125-13-325730:E0469** L1684-L1686 (terms: merger agreement, vote)
- [ ] **0001193125-13-325730:E0479** L1714-L1714 (terms: closing)
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