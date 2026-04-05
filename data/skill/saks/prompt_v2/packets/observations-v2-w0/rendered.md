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
deal_slug: saks
target_name: SAKS INC
source_accession_number: 0001193125-13-390275
source_form_type: UNKNOWN
chunk_mode: single_pass
window_id: w0
</deal_context>

<chronology_blocks>
B001 [L1109-L1109]: Background of the Merger
B002 [L1111-L1113]: As part of their ongoing evaluation of Saks business, the board and Saks senior management periodically review, consider and assess Saks operations and financial performance and industry conditions as they may affect Saks long-term strategic goals and plans, including the consideration of potential opportunities for business combinations, acquisitions and other financial and strategic alternatives. For the past several years, Goldman Sachs, one of Saks longstanding financial advisors, has participated in these reviews. One such review took place in December 2012.
B003 [L1115-L1117]: In February 2013, Stephen I. Sadove, Saks Chairman and Chief Executive Officer, received an unsolicited phone call from a representative of a private equity firm, which we refer to as Sponsor A, expressing interest in a potential acquisition of Saks. In early March 2013, Mr. Sadove met with senior representatives of Sponsor A to discuss the possibility of a potential transaction. No specific proposals were made by Sponsor A, and no specific transaction terms were discussed.
B004 [L1119-L1123]: On March 7, 2013, the board held a regularly scheduled telephonic meeting. At this meeting, Mr. Sadove informed the board of the contacts with Sponsor A. The board had a general discussion of potential strategic transactions, including a potential acquisition of Saks and the potential for Saks to make a strategic acquisition of a privately held retail company, which we refer to as Company B. The board requested that Saks advisors and senior management provide the Finance committee of the board with ongoing updates with respect to these matters, and that the Finance committee provide guidance to Saks advisors and senior management throughout the process of evaluating actions of this type, due to the expertise and background of the members of the Finance committee and the boards belief that it would be more efficient for a smaller group of directors than the entire board to receive more frequent updates.
B005 [L1125-L1127]: On April 1, 2013, Mr. Sadove met with Richard Baker, the Director, Governor, and Chief Executive Officer of Hudsons Bay, at the request of Mr. Baker and discussed a potential acquisition of Saks by Hudsons Bay. No specific proposals were made by Hudsons Bay, and no specific transaction terms were discussed.
B006 [L1129-L1131]: On April 4, 2013, the board held a regularly scheduled telephonic meeting. At this meeting, Mr. Sadove reviewed with the board the expressions of interest in a potential acquisition of Saks from Hudsons Bay and Sponsor A. The board discussed these expressions of interest, as well as a potential strategic acquisition of Company B. The board directed Mr. Sadove and Saks management to continue exploring these potential transactions.
B007 [L1133-L1133]: -23-
B008 [L1136-L1139]: On April 11, 2013, the Finance committee of the board and the Executive committee of the board held a special joint telephonic meeting attended by representatives of Goldman Sachs and Wachtell, Lipton, Rosen & Katz, referred to as Wachtell Lipton, Saks external counsel. At this meeting, Mr. Sadove updated the committee members on discussions with Hudsons Bay and Sponsor A regarding a potential acquisition of Saks, and discussed with the committee members the potential acquisition of Company B. The committee members directed that Mr. Sadove and Saks management continue evaluating these potential transactions.
B009 [L1141-L1143]: Following the April 11 joint committee meeting, representatives of Saks management and of Goldman Sachs met separately with representatives of two private equity firms, which we refer to as Sponsor C and Sponsor D, respectively, to discuss the possibility of their providing equity financing for an acquisition of Company B. Management and representatives of Saks and Sponsor C and Sponsor D continued these discussions over the next several weeks.
B010 [L1145-L1145]: During the week of
B011 [L1146-L1148]: April 15, 2013, representatives of Goldman Sachs met separately with representatives of each of Hudsons Bay and Sponsor A in order to discuss their respective consideration of a potential acquisition of Saks. Each of Hudsons Bay and Sponsor A indicated that they were considering making an offer to acquire Saks for at least $15 per share, in cash. A private equity firm that we refer to as Sponsor E and that Sponsor A had stated was in discussions with Sponsor A regarding participation in a potential joint acquisition of Saks also participated in the meeting with Sponsor A.
B012 [L1150-L1151]: On April 17, 2013, Saks and Sponsor C entered into a confidentiality agreement. On April 19, 2013, Saks and Sponsor D entered into a confidentiality agreement.
B013 [L1153-L1156]: On April 25, 2013, the board held a regularly scheduled telephonic meeting attended by representatives of Goldman Sachs and Wachtell Lipton. At this meeting, representatives of Goldman Sachs discussed with the board the following alternatives available to Saks  the potential acquisition of Saks by a third party, a potential acquisition of Company B and remaining as an independent public company. Mr. Sadove and Goldman Sachs updated the board on the status of discussions with Hudsons Bay and Sponsor A and Sponsor E, as well as the discussions with Sponsor C and Sponsor D regarding the possibility of providing equity financing for an acquisition of Company B if the board decided to pursue such a transaction.
B014 [L1158-L1159]: On April 26, 2013, Saks entered into a confidentiality agreement with each of Sponsor A and Sponsor E, who were considering participating in a potential joint acquisition of Saks.
B015 [L1161-L1161]: On April 30, 2013, Saks and Hudsons Bay entered into a confidentiality agreement.
B016 [L1163-L1164]: Following each partys entry into a confidentiality agreement, Saks made an online dataroom available to Sponsor A, Sponsor E and Hudsons Bay. Sponsor A, Sponsor E and Hudsons Bay each engaged in due diligence and meetings with Saks management over the next several weeks.
B017 [L1166-L1168]: During this period, members of Saks management reviewed with the members of the Finance committee the terms of the equity financing for a potential acquisition of Company B that had been negotiated with Sponsor C and those that had been negotiated with Sponsor D. The committee members determined that the terms negotiated with Sponsor C were more favorable than those negotiated with Sponsor D.
B018 [L1170-L1174]: On May 15, 2013, the Finance committee of the board held a special telephonic meeting attended by representatives of Goldman Sachs and Wachtell Lipton. At this meeting, Mr. Sadove and Goldman Sachs updated the committee on the status of discussions with Hudsons Bay and Sponsor A and Sponsor E, including a request from Hudsons Bay that it be permitted under the confidentiality agreement it had signed with Saks to contact a limited number of potential sources of equity financing for a potential acquisition of Saks. The committee also discussed the potential acquisition of Company B. Following discussion, the Finance committee agreed to grant Hudsons Bays request, subject to compliance with the terms of the confidentiality agreement. The committee also recommended that management continue exploring the potential transactions described above.
B019 [L1176-L1176]: -24-
B020 [L1179-L1181]: Following the May 15 committee meeting, Goldman Sachs contacted Company Bs principal shareholders to express Saks interest in exploring a potential acquisition of Company B. No proposals were made, and no specific transaction terms were discussed. During this period, representatives of Saks continued to discuss with representatives of Sponsor C the possibility of Saks making an offer to acquire Company B.
B021 [L1183-L1185]: On May 17, 2013, representatives of Goldman Sachs orally communicated to the principal shareholders of Company B Saks preliminary, non-binding proposal to acquire Company B in a cash transaction, with flexibility to include some stock consideration (which proposal Saks confirmed in a letter on May 20, 2013). Shortly thereafter, the principal shareholders of Company B informed representatives of Goldman Sachs that the proposal was insufficient.
B022 [L1187-L1187]: In late May 2013, media reports began to appear stating that Saks had engaged Goldman Sachs to explore a potential sale of Saks.
B023 [L1189-L1191]: On June 1, 2013, the Finance committee of the board held a special telephonic meeting attended by representatives of Goldman Sachs and Wachtell Lipton. At this meeting, the committee reviewed with Mr. Sadove and Saks advisors the discussions with each of Hudsons Bay, Sponsor A and Company Bs principal shareholders regarding potential transactions, including a financial evaluation of Company B. The committee determined to discuss the matters further with the full board at the next board meeting.
B024 [L1193-L1195]: During the week of June 3, 2013, representatives of Goldman Sachs spoke with representatives of each of Hudsons Bay, Sponsor A and Sponsor E and were informed that Hudsons Bay, on the one hand, and Sponsor A and Sponsor E, on the other hand, were each preliminarily prepared to proceed with the submission of a proposal to acquire Saks at indicative price ranges of $15 to $15.25 per share of common stock (in the case of Hudsons Bay) and $15 to $16 per share of common stock (in the case of Sponsor A and Sponsor E).
B025 [L1197-L1200]: On June 5, 2013, the board held a regularly scheduled meeting attended by representatives of Goldman Sachs and Wachtell Lipton. At this meeting, the board reviewed with Mr. Sadove and Saks advisors the discussions with each of Hudsons Bay, Sponsor A and Company Bs principal shareholders regarding potential transactions, and authorized (1) the implementation of a process to determine whether a transaction with one of the potential acquirors which had executed a confidentiality agreement could be reached on terms that would offer attractive value to Saks shareholders and (2) the submission of a revised proposal to acquire Company B.
B026 [L1202-L1203]: On June 6, 2013, Saks submitted a revised and non-binding proposal with a higher price to acquire Company B in a cash transaction, with flexibility to include some stock consideration.
B027 [L1205-L1207]: During the week of June 10, 2013, Saks was informed that a privately held retail company, which we refer to as Company F, had indicated interest in participating with Sponsor A and Sponsor E in a potential acquisition of Saks. Company F engaged in due diligence of Saks. However, no meetings were held between representatives of Saks and representatives of Company F, and Company F did not participate in the offer that was ultimately submitted by Sponsor A and Sponsor G.
B028 [L1209-L1210]: During the second and third weeks of June, representatives of Saks, including members of management, held multiple meetings with representatives of Sponsor A and Sponsor E as part of Sponsor As and Sponsor Es due diligence evaluation of Saks.
B029 [L1212-L1213]: On July 2, 2013, at the direction of Saks, Goldman Sachs distributed a draft merger agreement and process details to each of Hudsons Bay, Sponsor A and Sponsor E, with a request for submission of offers for an all-cash acquisition of Saks, along with comments on the draft merger agreement, no later than July 11, 2013.
B030 [L1215-L1216]: On July 5, 2013, Saks received a letter from Company Bs principal shareholders indicating that Saks proposed price in its previously submitted proposal was still insufficient for the principal shareholders of Company B to consider entering into a transaction, and stating the minimum proposed purchase price that would be required in
B031 [L1218-L1218]: -25-
B032 [L1221-L1223]: order for Company Bs principal shareholders to consider a potential acquisition of Company B by Saks. Company Bs principal shareholders, however, suggested that Saks senior management meet with their counterparts at Company B, to discuss, among other items, potential synergies, which might assist in closing the valuation gap. After consultation between board members and members of Saks senior management, it was determined that Saks senior management would not meet with Company Bs management in light of the substantial differences in the parties position, including on price, and the other transactions being considered.
B033 [L1225-L1227]: In early July 2013, Sponsor E informed Saks that Sponsor A was no longer intending to be a primary participant in a potential transaction and that Sponsor E had entered into discussions with Sponsor G, a private equity firm, regarding a potential joint acquisition of Saks. On July 8, 2013, Saks entered into a confidentiality agreement with Sponsor G. Following execution of the confidentiality agreement, representatives of Saks, including members of management, met with representatives of Sponsor E and Sponsor G as part of their due diligence evaluation of Saks.
B034 [L1229-L1230]: On July 10, 2013, the Finance committee of the board held a special telephonic meeting attended by representatives of Goldman Sachs and Wachtell Lipton. At this meeting, Goldman Sachs updated the committee members regarding the process to solicit offers from Hudsons Bay, Sponsor E and Sponsor G and the ongoing discussions with Company Bs principal shareholders.
B035 [L1232-L1237]: On July 11, 2013, each of Hudsons Bay, on the one hand, and Sponsor E, together with Sponsor G, on the other hand, submitted proposals expressing their continued interest in an acquisition of Saks. Hudsons Bays proposal included a price of $15.25 per share of common stock, a revised draft merger agreement and information and documentation relating to Hudsons Bays committed debt and equity financing for the potential transaction. The joint proposal from Sponsor E and Sponsor G included an indicative price range of $14.50$15.50 per share of common stock, but noted that the parties would require several weeks to continue their due diligence evaluation in order to submit a more definitive proposal and did not include a revised draft merger agreement or any documents supporting availability of financing for the proposal. Saks was subsequently informed that Sponsor G was no longer participating in the process, and that Sponsor E would again be joined in its proposal by Sponsor A as a primary participant. Saks negotiations with Hudsons Bay, Sponsor A and Sponsor E did not include any discussions regarding post-closing employment terms for the Companys executives or senior management.
B036 [L1239-L1241]: Upon the further suggestion of the principal shareholders of Company B that direct discussions between the senior management of the parties would be productive, on July 13, 2013, senior management of Saks met with senior management of Company B to discuss the possibility of an acquisition of Company B and the potential role of management of Company B following the proposed acquisition of Company B by Saks.
B037 [L1243-L1243]: During the week of
B038 [L1244-L1245]: July 15, 2013, at the direction of the board, representatives of Goldman Sachs indicated to representatives of Sponsor A and Sponsor E that a proposed purchase price in the lower half of the previously submitted price range would not be acceptable to the board in light of the $15.25 bid from Hudsons Bay and the boards view of the Companys value.
B039 [L1247-L1247]: On
B040 [L1248-L1251]: July 17, 2013, the board held a special telephonic meeting attended by representatives of Goldman Sachs and Wachtell Lipton. At this meeting, the board reviewed the proposal from Hudsons Bay and the joint proposal from Sponsor E and Sponsor A and the status of discussions with Company Bs principal shareholders. The board discussed these potential transactions for Saks as compared to the merits and considerations of remaining as a standalone entity. The board authorized Goldman Sachs to inform each of Hudsons Bay, on the one hand, and Sponsor E and Sponsor A, on the other hand, that their initial price proposals were insufficient and authorized Wachtell Lipton to provide a revised draft of the merger agreement to Hudsons Bay and its counsel.
B041 [L1253-L1254]: On July 18, 2013, Wachtell Lipton provided a revised draft of the merger agreement to representatives of Hudsons Bay.
B042 [L1256-L1257]: Also on July 18, 2013, Saks entered into a confidentiality agreement with Company B for Saks to engage in due diligence with respect to Company B. Thereafter, during the second and third weeks of July, members of
B043 [L1259-L1259]: -26-
B044 [L1262-L1263]: management of Saks met with members of management of Company B to discuss a potential acquisition of Company B by Saks. During that period, Company B made an online dataroom available to Saks as part of Saks due diligence evaluation of Company B.
B045 [L1265-L1268]: On July 21, 2013, Saks received a letter from Company H, a privately held company based in the U. S. unknown to Saks and its advisors, purporting to propose to acquire Saks for an aggregate price of $2.6 billion in cash, with no details or further information. Goldman Sachs subsequently attempted on more than one occasion to contact the appropriate person at Company H both by telephone and by e-mail to discuss the purported offer further but was unsuccessful in making contact with such person. Neither Saks nor Goldman Sachs received any subsequent communications from Company H.
B046 [L1270-L1272]: During the week of July 22, 2013, representatives of Goldman Sachs again indicated to representatives of Sponsor A and Sponsor E that a proposed purchase price would need to be above $15 per share of common stock, and Sponsor A and Sponsor E indicated a willingness to continue to pursue a transaction based on that valuation assumption but believed that it would be unlikely that they would achieve a value above the top end of their indicated range of $14.50 to $15.50 per share of common stock.
B047 [L1274-L1280]: On July 23, 2013, the board held a special telephonic meeting to review the status of discussions with each of Hudsons Bay, Sponsor A and Sponsor E, and Company Bs principal shareholders. Goldman Sachs informed the board that discussions to date with Company Bs principal shareholders indicated that the parties would be unable to agree on financial terms for a business combination between Saks and Company B. In addition, management of Saks informed the board of the purported offer received from Company H. Wachtell Lipton and Goldman Sachs discussed with the board the then-outstanding issues raised by Hudsons Bays comments to the draft merger agreement. The board discussed the foregoing matters. The board concluded that it would not be willing to make an offer to acquire Company B at or above the minimum price indicated by the principal shareholders of Company B. The board then authorized Goldman Sachs and Mr. Sadove to communicate to Hudsons Bay that the board would not agree to an acquisition of Saks at a price below $16 per share of common stock and that significant open issues in the draft merger agreement (including certain provisions related to Saks ability to solicit alternative offers following signing of the merger agreement and the consequences of Hudsons Bays failure to close the merger) and the draft agreements relating to Hudsons Bays committed financing of the merger needed to be resolved to Saks satisfaction.
B048 [L1282-L1284]: On July 23, 2013, following the board meeting and at the boards direction, Goldman Sachs informed Hudsons Bays financial advisor that Hudsons Bay would need to increase the per share price of its offer to at least $16 per share of common stock and communicated Saks view on certain significant issues arising out of the draft merger agreement and the draft agreements relating to Hudsons Bays committed financing of the merger.
B049 [L1286-L1287]: Also following the July 23 board meeting, representatives of Saks informed Company Bs principal shareholders that Saks was not willing to make an offer to acquire Company B at or above the minimum price indicated by the principal shareholders of Company B. Following this communication, Saks and Company Bs principal shareholders ceased discussion of a potential acquisition of Company B by Saks.
B050 [L1289-L1291]: In the evening of July 23, 2013, senior management of Saks met with representatives of Sponsor A and Sponsor E in connection with their evaluation of an acquisition of Saks. There was no indication from Sponsor A or Sponsor E that they were prepared to increase their indicated price beyond their initially indicated range of $14.50 to $15.50 per share of common stock, nor did it appear likely that Sponsor A and Sponsor E would be prepared to conclude their diligence more quickly than they had previously indicated.
B051 [L1293-L1293]: On
B052 [L1294-L1295]: July 24, 2013, representatives of Hudsons Bay advised Goldman Sachs that, subject to negotiating a definitive, binding agreement, Hudsons Bay was prepared to offer $16 per share of common stock and was agreeable to Saks position on substantially all of the significant issues in the draft merger agreement and the draft agreements relating to Hudsons Bays committed financing of the merger conveyed by Goldman Sachs to Hudsons Bay.
B053 [L1297-L1297]: -27-
B054 [L1300-L1303]: On July 25, 2013, Mr. Sadove and Mr. Baker briefly spoke telephonically regarding Hudsons Bays willingness to proceed with the potential acquisition of Saks at a price of $16 per share of common stock and to resolve the open issues in the draft merger agreement and Hudsons Bays financing documents. Mr. Sadove suggested to Mr. Baker that they meet in person the following day if the parties were to make sufficient progress in negotiations over the next 24 hours. Following this conversation, the parties and their advisors worked to finalize mutually agreeable merger documentation, including negotiation of the final merger agreement and revised documentation for Hudsons Bays financing.
B055 [L1305-L1307]: Also on July 25, 2013, the board held a regularly scheduled telephonic meeting attended by representatives of Goldman Sachs and Wachtell Lipton to review the status of discussions with each of Hudsons Bay, Sponsor A and Sponsor E, and Company Bs principal shareholders. Goldman Sachs informed the board that the principal shareholders of Company B had rejected Saks most recent proposal, and that discussions with Company B regarding a potential acquisition by Saks of Company B had ceased. The board authorized senior management and Saks advisors to proceed with negotiations with Hudsons Bay to determine if an agreement could be reached.
B056 [L1309-L1310]: Over the next few days, Saks, Hudsons Bay and their respective advisors continued to work on finalizing the merger agreement, revised documentation for Hudsons Bays committed financing and related documents.
B057 [L1312-L1313]: On July 26, 2013, Mr. Sadove and Mr. Baker met to discuss Hudsons Bays potential acquisition of Saks. At this meeting Messrs. Sadove and Baker discussed certain remaining open issues regarding the transaction, and Mr. Sadove discussed the results of the quarter to date.
B058 [L1315-L1317]: Also on July 26, 2013, the board held a special telephonic meeting attended by representatives of Goldman Sachs, Morgan Stanley & Co. LLC (a long-time advisor to Saks, referred to as  Morgan Stanley) and Wachtell Lipton. The board, Saks management and the legal and financial advisors again reviewed the terms of the proposal by Hudsons Bay, and discussed the status of negotiations with Hudsons Bay.
B059 [L1319-L1323]: On July 28, 2013, the board held a special telephonic meeting attended by representatives of Goldman Sachs, Morgan Stanley and Wachtell Lipton. The board, Saks management and the legal and financial advisors again reviewed the terms of the proposal by Hudsons Bay, including as compared to the merits and considerations of remaining as a standalone entity. Representatives of Goldman Sachs reviewed with the board Goldman Sachss financial analysis of the $16 per share of common stock in cash to be paid to Saks shareholders in the proposed merger and then delivered to the board Goldman Sachss oral opinion, subsequently confirmed in writing, that, as of such date and based upon and subject to the various limitations and assumptions set forth in the opinion, the $16 per share of common stock in cash to be paid to the holders of common stock pursuant to the merger agreement was fair, from a financial point of view, to such holders. See  The Merger (Proposal 1) Opinion of Goldman, Sachs & Co.
B060 [L1325-L1326]: Following the boards approval of the merger and the merger agreement, Saks, Hudsons Bay and Merger Sub finalized and executed the merger agreement and other transaction documents later on July 28, 2013.
B061 [L1328-L1329]: On July 29, 2013, Saks and Hudsons Bay issued a joint press release announcing entry into the transaction.
B062 [L1331-L1335]: The go shop period ended on September 6, 2013, and no party has been designated by Saks as an excluded party. During the go shop process, Goldman Sachs, on behalf of Saks, contacted 58 potentially interested third parties, including private equity firms, companies involved in the retail industry and other potential acquirors. Of those contacted, only six parties expressed interest, and only one of the six (which we refer to as Company I) executed a confidentiality agreement with, and conducted a due diligence investigation of, Saks. None of the parties contacted as part of the go shop process, including Company I, has submitted an acquisition proposal for Saks. Approximately two weeks after the end of the go shop period, Saks received a letter from Company I raising issues concerning what Company I characterized as the limited duration of the go shop period and its inability
B063 [L1337-L1337]: -28-
B064 [L1340-L1344]: to obtain certain information from Saks. In its reply to the letter, Saks pointed out to Company I that Company I had not signed a confidentiality agreement until approximately two weeks after the merger agreement was executed, that Company I had been given access to the same information that was provided to Hudsons Bay and other third parties with whom Saks had held discussions (as well as certain requested information that had not been (but then was) provided to Hudsons Bay) and that Company I had not requested a meeting with, or access to, any member of management of Saks. Company I and Saks have engaged in subsequent correspondence regarding, among other things, the go shop process, in which Saks has reiterated, among other things, that, as described above, there is a procedure under the merger agreement for a bona fide bidder to make an unsolicited proposal to the board and, if the proposal meets certain requirements, receive information concerning Saks, even following the end of the go shop period.
B065 [L1346-L1347]: As of the date of this proxy statement, Saks has not received any communications regarding any potential alternative transaction from any third party that the board has determined constitutes a superior proposal under the merger agreement.
</chronology_blocks>

<evidence_checklist>
### Dated actions to extract
- [ ] **0001193125-13-390275:E0272** L1115-L1117 (date: February 2013; actors: Sponsor A; terms: discussed, met, proposal)
- [ ] **0001193125-13-390275:E0274** L1119-L1123 (date: March 7, 2013; actors: Sponsor A, Company B; terms: meeting, requested)
- [ ] **0001193125-13-390275:E0276** L1125-L1127 (date: April 1, 2013; terms: discussed, met, proposal)
- [ ] **0001193125-13-390275:E0277** L1129-L1131 (date: April 4, 2013; actors: Sponsor A, Company B; terms: discussed, meeting)
- [ ] **0001193125-13-390275:E0279** L1136-L1139 (date: April 11, 2013; actors: Sponsor A, Company B, Goldman Sachs; terms: discussed, meeting, sent)
- [ ] **0001193125-13-390275:E0281** L1141-L1143 (date: April; actors: Sponsor C, Sponsor D, Company B, Goldman Sachs; terms: meeting, met, sent)
- [ ] **0001193125-13-390275:E0283** L1145-L1148 (date: April 15, 2013; actors: Sponsor A, Sponsor E, Goldman Sachs; value: $15 per share; terms: meeting, met, offer)
- [ ] **0001193125-13-390275:E0286** L1150-L1151 (date: April 17, 2013; actors: Sponsor C, Sponsor D; terms: entered into)
- [ ] **0001193125-13-390275:E0289** L1153-L1156 (date: April 25, 2013; actors: Company B, Sponsor A, Sponsor E, Sponsor C, Sponsor D, Goldman Sachs; terms: discussed, meeting, sent)
- [ ] **0001193125-13-390275:E0291** L1158-L1159 (date: April 26, 2013; actors: Sponsor A, Sponsor E; terms: entered into)
- [ ] **0001193125-13-390275:E0294** L1161-L1161 (date: April 30, 2013; terms: entered into)
- [ ] **0001193125-13-390275:E0299** L1170-L1174 (date: May 15, 2013; actors: Sponsor A, Sponsor E, Company B, Goldman Sachs; terms: discussed, meeting, sent)
- [ ] **0001193125-13-390275:E0302** L1179-L1181 (date: May; actors: Company B, Sponsor C, Goldman Sachs; terms: contacted, discussed, meeting)
- [ ] **0001193125-13-390275:E0304** L1183-L1185 (date: May 17, 2013; actors: Company B, Goldman Sachs; terms: proposal, sent)
- [ ] **0001193125-13-390275:E0306** L1187-L1187 (date: late May 2013; actors: Goldman Sachs; terms: engaged)
- [ ] **0001193125-13-390275:E0308** L1189-L1191 (date: June 1, 2013; actors: Sponsor A, Company B, Goldman Sachs; terms: meeting, sent)
- [ ] **0001193125-13-390275:E0310** L1193-L1195 (date: June 3, 2013; actors: Sponsor A, Sponsor E, Goldman Sachs; value: $15 to $15.25 per share; terms: proposal, sent)
- [ ] **0001193125-13-390275:E0313** L1197-L1200 (date: June 5, 2013; actors: Sponsor A, Company B, Goldman Sachs; terms: authorized, executed, meeting)
- [ ] **0001193125-13-390275:E0317** L1202-L1203 (date: June 6, 2013; actors: Company
B; terms: proposal, submitted)
- [ ] **0001193125-13-390275:E0319** L1205-L1207 (date: June 10, 2013; actors: Company F, Sponsor A, Sponsor E, Sponsor G; terms: engaged, meeting, offer)
- [ ] **0001193125-13-390275:E0322** L1209-L1210 (date: June; actors: Sponsor A, Sponsor E; terms: meeting, sent)
- [ ] **0001193125-13-390275:E0325** L1212-L1213 (date: July 2, 2013; actors: Sponsor A, Sponsor E, Goldman Sachs; terms: offer)
- [ ] **0001193125-13-390275:E0329** L1215-L1216 (date: July 5, 2013; actors: Company B; terms: proposal, proposed, received)
- [ ] **0001193125-13-390275:E0333** L1225-L1227 (date: early July 2013; actors: Sponsor E, Sponsor A, Sponsor G; terms: entered into, met, sent)
- [ ] **0001193125-13-390275:E0336** L1229-L1230 (date: July 10, 2013; actors: Sponsor E, Sponsor G, Company B, Goldman Sachs; terms: meeting, offer, sent)
- [ ] **0001193125-13-390275:E0338** L1232-L1237 (date: July 11, 2013; actors: Sponsor E, Sponsor G, Sponsor A; value: $15.25 per share; terms: proposal, submitted)
- [ ] **0001193125-13-390275:E0343** L1239-L1241 (date: July 13, 2013; actors: Company B; terms: met, proposed)
- [ ] **0001193125-13-390275:E0345** L1243-L1245 (date: July 15, 2013; actors: Sponsor A, Sponsor E, Goldman Sachs; value: $15.25; terms: proposed, sent, submitted)
- [ ] **0001193125-13-390275:E0348** L1247-L1251 (date: July 17, 2013; actors: Sponsor E, Sponsor A, Company B, Goldman Sachs; terms: authorized, discussed, meeting)
- [ ] **0001193125-13-390275:E0351** L1253-L1254 (date: July 18, 2013; terms: sent)
- [ ] **0001193125-13-390275:E0353** L1256-L1257 (date: July 18, 2013; actors: Company B; terms: entered into)
- [ ] **0001193125-13-390275:E0358** L1265-L1268 (date: July 21, 2013; actors: Company H, Goldman Sachs; value: $2.6; terms: offer, received)
- [ ] **0001193125-13-390275:E0361** L1270-L1272 (date: July 22, 2013; actors: Sponsor A, Sponsor E, Goldman Sachs; value: $15 per share; terms: proposed, sent)
- [ ] **0001193125-13-390275:E0364** L1274-L1280 (date: July 23, 2013; actors: Sponsor A, Sponsor E, Company B, Company H, Goldman Sachs, Goldman
Sachs; value: $16 per share; terms: authorized, discussed, meeting)
- [ ] **0001193125-13-390275:E0369** L1282-L1284 (date: July 23, 2013; actors: Goldman Sachs; value: $16 per share; terms: meeting, offer)
- [ ] **0001193125-13-390275:E0374** L1286-L1287 (date: July; actors: Company B; terms: meeting, offer, sent)
- [ ] **0001193125-13-390275:E0376** L1289-L1291 (date: July 23, 2013; actors: Sponsor A, Sponsor E; value: $14.50 to $15.50 per share; terms: met, sent)
- [ ] **0001193125-13-390275:E0379** L1293-L1295 (date: July 24, 2013; actors: Goldman Sachs; value: $16 per share; terms: offer, sent)
- [ ] **0001193125-13-390275:E0388** L1305-L1307 (date: July 25, 2013; actors: Sponsor A, Sponsor E, Company B, Goldman Sachs; terms: authorized, meeting, proposal)
- [ ] **0001193125-13-390275:E0392** L1312-L1313 (date: July 26, 2013; terms: discussed, meeting, met)
- [ ] **0001193125-13-390275:E0393** L1315-L1317 (date: July 26, 2013; actors: Goldman Sachs; terms: discussed, meeting, proposal)
- [ ] **0001193125-13-390275:E0395** L1319-L1323 (date: July 28, 2013; actors: Goldman Sachs, Goldman, Sachs; value: $16 per share; terms: delivered, meeting, proposal)
- [ ] **0001193125-13-390275:E0399** L1325-L1326 (date: July 28, 2013; terms: executed)
- [ ] **0001193125-13-390275:E0401** L1331-L1335 (date: September 6, 2013; actors: Company I, Goldman Sachs; terms: contacted, executed, proposal)

### Financial terms to capture
- [ ] **0001193125-13-390275:E0284** L1145-L1148 (date: April 15, 2013; actors: Sponsor A, Sponsor E, Goldman Sachs; value: $15 per share; terms: $15 per share)
- [ ] **0001193125-13-390275:E0311** L1193-L1195 (date: June 3, 2013; actors: Sponsor A, Sponsor E, Goldman Sachs; value: $15 to $15.25 per share; terms: $15 to $15.25 per share, $15 to $16 per share)
- [ ] **0001193125-13-390275:E0339** L1232-L1237 (date: July 11, 2013; actors: Sponsor E, Sponsor G, Sponsor A; value: $15.25 per share; terms: $14.50, $15.25 per share, $15.50 per share)
- [ ] **0001193125-13-390275:E0346** L1243-L1245 (date: July 15, 2013; actors: Sponsor A, Sponsor E, Goldman Sachs; value: $15.25; terms: $15.25)
- [ ] **0001193125-13-390275:E0359** L1265-L1268 (date: July 21, 2013; actors: Company H, Goldman Sachs; value: $2.6; terms: $2.6)
- [ ] **0001193125-13-390275:E0362** L1270-L1272 (date: July 22, 2013; actors: Sponsor A, Sponsor E, Goldman Sachs; value: $15 per share; terms: $14.50 to $15.50 per share, $15 per share)
- [ ] **0001193125-13-390275:E0365** L1274-L1280 (date: July 23, 2013; actors: Sponsor A, Sponsor E, Company B, Company H, Goldman Sachs, Goldman
Sachs; value: $16 per share; terms: $16 per share)
- [ ] **0001193125-13-390275:E0370** L1282-L1284 (date: July 23, 2013; actors: Goldman Sachs; value: $16 per share; terms: $16 per share)
- [ ] **0001193125-13-390275:E0377** L1289-L1291 (date: July 23, 2013; actors: Sponsor A, Sponsor E; value: $14.50 to $15.50 per share; terms: $14.50 to $15.50 per share)
- [ ] **0001193125-13-390275:E0380** L1293-L1295 (date: July 24, 2013; actors: Goldman Sachs; value: $16 per share; terms: $16 per share)
- [ ] **0001193125-13-390275:E0384** L1300-L1303 (date: July 25, 2013; value: $16 per share; terms: $16 per share)
- [ ] **0001193125-13-390275:E0396** L1319-L1323 (date: July 28, 2013; actors: Goldman Sachs, Goldman, Sachs; value: $16 per share; terms: $16 per share)

### Actors to identify
- [ ] **0001193125-13-390275:E0270** L1111-L1113 (date: may; actors: Goldman Sachs; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-13-390275:E0273** L1115-L1117 (date: February 2013; actors: Sponsor A)
- [ ] **0001193125-13-390275:E0275** L1119-L1123 (date: March 7, 2013; actors: Sponsor A, Company B; terms: advisor, advisors)
- [ ] **0001193125-13-390275:E0278** L1129-L1131 (date: April 4, 2013; actors: Sponsor A, Company B)
- [ ] **0001193125-13-390275:E0280** L1136-L1139 (date: April 11, 2013; actors: Sponsor A, Company B, Goldman Sachs; terms: counsel)
- [ ] **0001193125-13-390275:E0282** L1141-L1143 (date: April; actors: Sponsor C, Sponsor D, Company B, Goldman Sachs)
- [ ] **0001193125-13-390275:E0285** L1145-L1148 (date: April 15, 2013; actors: Sponsor A, Sponsor E, Goldman Sachs; value: $15 per share)
- [ ] **0001193125-13-390275:E0287** L1150-L1151 (date: April 17, 2013; actors: Sponsor C, Sponsor D)
- [ ] **0001193125-13-390275:E0290** L1153-L1156 (date: April 25, 2013; actors: Company B, Sponsor A, Sponsor E, Sponsor C, Sponsor D, Goldman Sachs)
- [ ] **0001193125-13-390275:E0292** L1158-L1159 (date: April 26, 2013; actors: Sponsor A, Sponsor E)
- [ ] **0001193125-13-390275:E0296** L1163-L1164 (actors: Sponsor A, Sponsor E)
- [ ] **0001193125-13-390275:E0298** L1166-L1168 (actors: Company B, Sponsor C, Sponsor D)
- [ ] **0001193125-13-390275:E0300** L1170-L1174 (date: May 15, 2013; actors: Sponsor A, Sponsor E, Company B, Goldman Sachs)
- [ ] **0001193125-13-390275:E0303** L1179-L1181 (date: May; actors: Company B, Sponsor C, Goldman Sachs; terms: shareholder)
- [ ] **0001193125-13-390275:E0305** L1183-L1185 (date: May 17, 2013; actors: Company B, Goldman Sachs; terms: shareholder)
- [ ] **0001193125-13-390275:E0307** L1187-L1187 (date: late May 2013; actors: Goldman Sachs)
- [ ] **0001193125-13-390275:E0309** L1189-L1191 (date: June 1, 2013; actors: Sponsor A, Company B, Goldman Sachs; terms: advisor, advisors, shareholder)
- [ ] **0001193125-13-390275:E0312** L1193-L1195 (date: June 3, 2013; actors: Sponsor A, Sponsor E, Goldman Sachs; value: $15 to $15.25 per share)
- [ ] **0001193125-13-390275:E0314** L1197-L1200 (date: June 5, 2013; actors: Sponsor A, Company B, Goldman Sachs; terms: advisor, advisors, shareholder)
- [ ] **0001193125-13-390275:E0318** L1202-L1203 (date: June 6, 2013; actors: Company
B)
- [ ] **0001193125-13-390275:E0320** L1205-L1207 (date: June 10, 2013; actors: Company F, Sponsor A, Sponsor E, Sponsor G)
- [ ] **0001193125-13-390275:E0323** L1209-L1210 (date: June; actors: Sponsor A, Sponsor E)
- [ ] **0001193125-13-390275:E0326** L1212-L1213 (date: July 2, 2013; actors: Sponsor A, Sponsor E, Goldman Sachs)
- [ ] **0001193125-13-390275:E0330** L1215-L1216 (date: July 5, 2013; actors: Company B; terms: shareholder)
- [ ] **0001193125-13-390275:E0331** L1221-L1223 (actors: Company B; terms: shareholder)
- [ ] **0001193125-13-390275:E0334** L1225-L1227 (date: early July 2013; actors: Sponsor E, Sponsor A, Sponsor G)
- [ ] **0001193125-13-390275:E0337** L1229-L1230 (date: July 10, 2013; actors: Sponsor E, Sponsor G, Company B, Goldman Sachs; terms: shareholder)
- [ ] **0001193125-13-390275:E0340** L1232-L1237 (date: July 11, 2013; actors: Sponsor E, Sponsor G, Sponsor A; value: $15.25 per share)
- [ ] **0001193125-13-390275:E0344** L1239-L1241 (date: July 13, 2013; actors: Company B; terms: shareholder)
- [ ] **0001193125-13-390275:E0347** L1243-L1245 (date: July 15, 2013; actors: Sponsor A, Sponsor E, Goldman Sachs; value: $15.25)
- [ ] **0001193125-13-390275:E0349** L1247-L1251 (date: July 17, 2013; actors: Sponsor E, Sponsor A, Company B, Goldman Sachs; terms: counsel, shareholder)
- [ ] **0001193125-13-390275:E0354** L1256-L1257 (date: July 18, 2013; actors: Company B)
- [ ] **0001193125-13-390275:E0356** L1262-L1263 (actors: Company B)
- [ ] **0001193125-13-390275:E0360** L1265-L1268 (date: July 21, 2013; actors: Company H, Goldman Sachs; value: $2.6; terms: advisor, advisors)
- [ ] **0001193125-13-390275:E0363** L1270-L1272 (date: July 22, 2013; actors: Sponsor A, Sponsor E, Goldman Sachs; value: $15 per share)
- [ ] **0001193125-13-390275:E0366** L1274-L1280 (date: July 23, 2013; actors: Sponsor A, Sponsor E, Company B, Company H, Goldman Sachs, Goldman
Sachs; value: $16 per share; terms: shareholder)
- [ ] **0001193125-13-390275:E0371** L1282-L1284 (date: July 23, 2013; actors: Goldman Sachs; value: $16 per share; terms: advisor, financial advisor)
- [ ] **0001193125-13-390275:E0375** L1286-L1287 (date: July; actors: Company B; terms: shareholder)
- [ ] **0001193125-13-390275:E0378** L1289-L1291 (date: July 23, 2013; actors: Sponsor A, Sponsor E; value: $14.50 to $15.50 per share)
- [ ] **0001193125-13-390275:E0381** L1293-L1295 (date: July 24, 2013; actors: Goldman Sachs; value: $16 per share)
- [ ] **0001193125-13-390275:E0385** L1300-L1303 (date: July 25, 2013; value: $16 per share; terms: advisor, advisors)
- [ ] **0001193125-13-390275:E0389** L1305-L1307 (date: July 25, 2013; actors: Sponsor A, Sponsor E, Company B, Goldman Sachs; terms: advisor, advisors, shareholder)
- [ ] **0001193125-13-390275:E0390** L1309-L1310 (terms: advisor, advisors)
- [ ] **0001193125-13-390275:E0394** L1315-L1317 (date: July 26, 2013; actors: Goldman Sachs; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-13-390275:E0397** L1319-L1323 (date: July 28, 2013; actors: Goldman Sachs, Goldman, Sachs; value: $16 per share; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-13-390275:E0402** L1331-L1335 (date: September 6, 2013; actors: Company I, Goldman Sachs; terms: party )
- [ ] **0001193125-13-390275:E0405** L1340-L1344 (actors: Company I; terms: bidder )
- [ ] **0001193125-13-390275:E0408** L1346-L1347 (terms: party )

### Process signals to check
- [ ] **0001193125-13-390275:E0271** L1111-L1113 (date: may; actors: Goldman Sachs; terms: strategic alternatives)
- [ ] **0001193125-13-390275:E0288** L1150-L1151 (date: April 17, 2013; actors: Sponsor C, Sponsor D; terms: confidentiality agreement)
- [ ] **0001193125-13-390275:E0293** L1158-L1159 (date: April 26, 2013; actors: Sponsor A, Sponsor E; terms: confidentiality agreement)
- [ ] **0001193125-13-390275:E0295** L1161-L1161 (date: April 30, 2013; terms: confidentiality agreement)
- [ ] **0001193125-13-390275:E0297** L1163-L1164 (actors: Sponsor A, Sponsor E; terms: confidentiality agreement, due diligence)
- [ ] **0001193125-13-390275:E0301** L1170-L1174 (date: May 15, 2013; actors: Sponsor A, Sponsor E, Company B, Goldman Sachs; terms: confidentiality agreement)
- [ ] **0001193125-13-390275:E0315** L1197-L1200 (date: June 5, 2013; actors: Sponsor A, Company B, Goldman Sachs; terms: confidentiality agreement)
- [ ] **0001193125-13-390275:E0321** L1205-L1207 (date: June 10, 2013; actors: Company F, Sponsor A, Sponsor E, Sponsor G; terms: due diligence)
- [ ] **0001193125-13-390275:E0324** L1209-L1210 (date: June; actors: Sponsor A, Sponsor E; terms: due diligence)
- [ ] **0001193125-13-390275:E0327** L1212-L1213 (date: July 2, 2013; actors: Sponsor A, Sponsor E, Goldman Sachs; terms: draft merger agreement)
- [ ] **0001193125-13-390275:E0335** L1225-L1227 (date: early July 2013; actors: Sponsor E, Sponsor A, Sponsor G; terms: confidentiality agreement, due diligence)
- [ ] **0001193125-13-390275:E0341** L1232-L1237 (date: July 11, 2013; actors: Sponsor E, Sponsor G, Sponsor A; value: $15.25 per share; terms: draft merger agreement, due diligence)
- [ ] **0001193125-13-390275:E0355** L1256-L1257 (date: July 18, 2013; actors: Company B; terms: confidentiality agreement, due diligence)
- [ ] **0001193125-13-390275:E0357** L1262-L1263 (actors: Company B; terms: due diligence)
- [ ] **0001193125-13-390275:E0367** L1274-L1280 (date: July 23, 2013; actors: Sponsor A, Sponsor E, Company B, Company H, Goldman Sachs, Goldman
Sachs; value: $16 per share; terms: draft merger agreement)
- [ ] **0001193125-13-390275:E0372** L1282-L1284 (date: July 23, 2013; actors: Goldman Sachs; value: $16 per share; terms: draft merger agreement)
- [ ] **0001193125-13-390275:E0382** L1293-L1295 (date: July 24, 2013; actors: Goldman Sachs; value: $16 per share; terms: draft merger agreement)
- [ ] **0001193125-13-390275:E0386** L1300-L1303 (date: July 25, 2013; value: $16 per share; terms: draft merger agreement)
- [ ] **0001193125-13-390275:E0403** L1331-L1335 (date: September 6, 2013; actors: Company I, Goldman Sachs; terms: confidentiality agreement, due diligence)
- [ ] **0001193125-13-390275:E0406** L1340-L1344 (actors: Company I; terms: confidentiality agreement)
- [ ] **0001193125-13-390275:E0409** L1346-L1347 (terms: superior proposal)

### Outcome facts to verify
- [ ] **0001193125-13-390275:E0316** L1197-L1200 (date: June 5, 2013; actors: Sponsor A, Company B, Goldman Sachs; terms: executed)
- [ ] **0001193125-13-390275:E0328** L1212-L1213 (date: July 2, 2013; actors: Sponsor A, Sponsor E, Goldman Sachs; terms: merger agreement)
- [ ] **0001193125-13-390275:E0332** L1221-L1223 (actors: Company B; terms: closing)
- [ ] **0001193125-13-390275:E0342** L1232-L1237 (date: July 11, 2013; actors: Sponsor E, Sponsor G, Sponsor A; value: $15.25 per share; terms: closing, merger agreement)
- [ ] **0001193125-13-390275:E0350** L1247-L1251 (date: July 17, 2013; actors: Sponsor E, Sponsor A, Company B, Goldman Sachs; terms: merger agreement)
- [ ] **0001193125-13-390275:E0352** L1253-L1254 (date: July 18, 2013; terms: merger agreement)
- [ ] **0001193125-13-390275:E0368** L1274-L1280 (date: July 23, 2013; actors: Sponsor A, Sponsor E, Company B, Company H, Goldman Sachs, Goldman
Sachs; value: $16 per share; terms: merger agreement)
- [ ] **0001193125-13-390275:E0373** L1282-L1284 (date: July 23, 2013; actors: Goldman Sachs; value: $16 per share; terms: merger agreement)
- [ ] **0001193125-13-390275:E0383** L1293-L1295 (date: July 24, 2013; actors: Goldman Sachs; value: $16 per share; terms: merger agreement)
- [ ] **0001193125-13-390275:E0387** L1300-L1303 (date: July 25, 2013; value: $16 per share; terms: merger agreement)
- [ ] **0001193125-13-390275:E0391** L1309-L1310 (terms: merger agreement)
- [ ] **0001193125-13-390275:E0398** L1319-L1323 (date: July 28, 2013; actors: Goldman Sachs, Goldman, Sachs; value: $16 per share; terms: merger agreement)
- [ ] **0001193125-13-390275:E0400** L1325-L1326 (date: July 28, 2013; terms: executed, merger agreement)
- [ ] **0001193125-13-390275:E0404** L1331-L1335 (date: September 6, 2013; actors: Company I, Goldman Sachs; terms: executed)
- [ ] **0001193125-13-390275:E0407** L1340-L1344 (actors: Company I; terms: executed, merger agreement)
- [ ] **0001193125-13-390275:E0410** L1346-L1347 (terms: merger agreement)
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