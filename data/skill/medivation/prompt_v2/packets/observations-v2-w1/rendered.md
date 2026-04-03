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

Return valid JSON only.

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
deal_slug: medivation
target_name: MEDIVATION INC
source_accession_number: 0001193125-16-696911
source_form_type: UNKNOWN
chunk_mode: chunked
window_id: w1
</deal_context>

<chronology_blocks>
B076 [L920-L922]: Later that morning, on August 20, 2016, beginning at 11:51 a. m. Pacific Time, each of Pfizer, Company 1, and Company 2 submitted a final proposal, each of which had been approved by the board of directors of the respective bidding party and each of which included confirmation that it was not subject to further diligence, and a revised draft of the merger agreement. Pfizer submitted a revised final proposal to acquire Medivation for $81.50 per share. Company 1 submitted a revised final proposal to acquire Medivation for $80.25 per share. Company 2 submitted a revised final proposal to acquire Medivation for $80.00 per share.
B077 [L924-L925]: Immediately thereafter, at 12:15 p. m. Pacific Time on August 20, 2016, the Medivation board of directors met telephonically with representatives of Medivations senior management and the Companys legal and
B078 [L927-L927]: 22
B079 [L930-L943]: financial advisors to consider the final proposals and corresponding merger agreements. At that meeting, representatives of J. P. Morgan and Evercore presented the final proposals from Pfizer, Company 1 and Company 2. Representatives of Cooley and Wachtell Lipton reviewed each proposal and confirmed that the final proposal merger agreements had substantially similar principal terms, with minor revisions to be made, and no material changes from the terms reviewed in the previous days meeting on August 19, 2016. The Medivation board of directors and its advisors then discussed the final valuation proposals. After discussion among the board of directors and its advisors, each of J. P. Morgan and Evercore delivered an oral opinion with respect to the Pfizer final proposal, confirmed by delivery of a written opinion dated August 20, 2016, to the board of directors of Medivation to the effect that, as of such date and based on and subject to various assumptions made, procedures followed, matters considered and limitations and qualifications on the review undertaken described in each financial advisors written opinion, the consideration to be paid to the holders of Medivation common stock in the proposed Offer and the Merger, consisting of $81.50 per share in cash, was fair, from a financial point of view, to such holders. Representatives of Wachtell Lipton then reviewed the principal terms of the merger agreement that had been negotiated with Pfizer, including (1) the fiduciary duty exceptions that would permit Medivation to negotiate and accept an unsolicited superior proposal, subject to compliance with Pfizers match rights, (2) the size of the termination fee to be paid by Medivation in the event Medivation were to terminate the Pfizer transaction in order to accept an alternative transaction with another party, and (3) the conditions to consummation of the tender offer, including those with respect to antitrust legal requirements and a material adverse effect, and answered questions from the Medivation board of directors about the conditions to the tender offer. The Medivation board also discussed amending the Rights Agreement in order to permit the tender offer, the merger and the other transactions contemplated by the merger agreement to occur without triggering any distribution or other adverse event to Pfizer or its affiliates under the Rights Agreement (the  Rights Amendment). Representatives of J. P. Morgan and Evercore reviewed the financial analyses supporting their fairness opinions. Representatives of Cooley provided a review for the board of the boards fiduciary duties. Following the delivery of such oral opinions, and after further discussion, including as to the matters discussed in the section entitled  Reasons for the Merger; Recommendation of the Medivation Board of Directors, the Medivation board of directors unanimously determined that to enter into the Pfizer merger agreement would be advisable, fair, and in the best interests of Medivation and its stockholders and unanimously approved that merger agreement and the merger.
B080 [L945-L946]: Also on August 20, 2016, following approval of the Medivation board of directors, Pfizer and Medivation executed the merger agreement and Medivation executed the Rights Amendment. On August 22, 2016, the parties issued a joint press release announcing the transaction.
B081 [L948-L948]: (ii)      Reasons for Recommendation
B082 [L950-L950]: Our Board of Directors, with the assistance of
B083 [L951-L954]: Medivations senior management and its financial and legal advisors, evaluated the Merger Agreement and the Transactions and unanimously (i) determined that the Merger Agreement and the Transactions, including the Offer and the Merger, are fair to, and in the best interest of, Medivation and its stockholders, (ii) declared it advisable to enter into the Merger Agreement with Parent and Purchaser, (iii) approved the execution, delivery and performance by Medivation of the Merger Agreement and the consummation of the Transactions, including the Offer and the Merger, (iv) agreed that the Merger shall be effected under Section 251(h) of the DGCL and (v) resolved to recommend that the stockholders of Medivation tender their Shares to Purchaser pursuant to the Offer.
B084 [L956-L957]: In the course of reaching its unanimous determination, our Board of Directors carefully considered the following reasons that weighed positively in favor of its decision, among others and not necessarily in order of relative importance:
B085 [L959-L959]: Premium to Market Price. Our Board of Directors considered the current and historical market prices
B086 [L961-L961]: 23
B087 [L964-L964]: premium to the closing price of the Shares on April 27, 2016, the last full trading day prior to the public announcement of the initial unsolicited proposal by Sanofi; (2) a 27.2% premium to the
B088 [L966-L966]: Certainty of Value. Our Board of Directors considered that the Offer Price and the Merger Consideration is all cash, so that the Transactions provide certainty, immediate value and liquidity to...
B089 [L968-L968]: Best Strategic Alternative for Maximizing Stockholder Value. Our Board of Directors determined, after a thorough review of strategic alternatives and discussions with Medivation management and ...
B090 [L970-L970]: Our Board of Directors considered that Medivation had conducted a lengthy and thorough process, directed by our Board of Directors, during which representatives of Medivation contacted 15 parti...
B091 [L972-L972]: Our Board of Directors noted that none of the other four bidders expressed a willingness to make a definitive offer at a price per Share above $80.25, which was lower than the $81.50 price per ...
B092 [L974-L977]: On several occasions in 2016, including at meetings in March through August, our Board of Directors evaluated carefully, with the assistance of legal and financial advisors and members of Mediv... management, the risks and potential benefits associated with other strategic or financial alternatives and the potential for shareholder value creation associated with those alternatives. As pa... considered: ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
B093 [L979-L979]: an assessment of Medivations business, assets (including pipeline assets), prospects, competitive position, regulatory landscape, historical and projected financial performance, short and long...
B094 [L981-L981]: the risks associated with Medivations business and remaining a standalone public company, including risks associated with Medivations ability to obtain regulatory approval for its products or...
B095 [L983-L983]: Likelihood and Speed of Consummation. Our Board of Directors considered the likelihood of completion of the Transactions to be high, particularly in light of the terms of the Merger Agreement a...
B096 [L985-L985]: the conditions to the Offer and the Merger being specific and limited;
B097 [L987-L987]: 24
B098 [L990-L990]: the absence of any financing condition in the Merger Agreement;
B099 [L992-L992]: the size and financial strength of Parent, and Parents ability to fund the Offer Price with cash;
B100 [L994-L994]: the likelihood of obtaining required regulatory approvals;
B101 [L996-L996]: the remedy of specific performance available to Medivation under the Merger Agreement in the event of breaches by Parent and Purchaser;
B102 [L998-L998]: the fact that the Offer and the Merger are not subject to the conditionality and execution risk of any required approval by Parents stockholders; and
B103 [L1000-L1000]: the structure of the transaction as a cash tender offer for all outstanding Shares, with the expected result that a relatively short period will elapse before our stockholders receive the Offer...
B104 [L1002-L1002]: Opportunity to Receive Unsolicited Alternative Proposals and to Terminate the Transactions in Order to Accept a Superior Proposal. Our Board of Directors considered the terms of the Merger Agre...
B105 [L1004-L1004]: Medivations right, subject to certain conditions, to respond to and negotiate unsolicited acquisition proposals that are made prior to the time that the Offer is consummated;
B106 [L1006-L1006]: the provision of the Merger Agreement allowing our Board of Directors to terminate the Merger Agreement in order to accept and enter into a definitive agreement with respect to an unsolicited s...
B107 [L1008-L1008]: the ability of our Board of Directors under the Merger Agreement to withdraw or modify its recommendation that Medivations stockholders tender their Shares to Purchaser pursuant to the Offer i...
B108 [L1010-L1015]: Fairness Opinions from J. P. Morgan and Evercore. Our Board of Directors considered the separate financial analyses presentations of J. P. Morgan and Evercore and the oral opinions of J. P. Mor... subsequently confirmed in writing, rendered to our Board of Directors, to the effect that, as of August 20, 2016 and based upon and subject to the assumptions made, procedures followed, matters... J. P. Morgan and Evercore in preparing the opinions, as set forth therein, the consideration to be paid to Medivations common stockholders in the proposed Offer and the Merger was fair, from a... below under  Opinions of Financial Advisors). The full text of the written opinions of J. P. Morgan and Evercore, each dated August 20, 2016, which set forth, among other things, the assumpt... considered and limitations on the review undertaken in rendering the opinion, have been included as Annex I and Annex II, respectively, to this Schedule 14D-9 and are incorporated herein by ref... ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
B109 [L1017-L1018]: Our Board of Directors also considered a variety of risks and other potentially adverse factors in determining whether to approve the Merger Agreement and the Transactions, including the following, which are not necessarily listed in order of relative importance:
B110 [L1020-L1020]: the fact that Medivation would no longer exist as an independent, publicly traded company, and our stockholders would no longer participate in any future earnings or growth of Medivation or ben...
B111 [L1022-L1022]: 25
B112 [L1025-L1025]: the potential risk of diverting management attention and resources from the operation of Medivations business and towards completion of the Offer and the Merger;
B113 [L1027-L1027]: the risk of incurring substantial expenses related to the Offer and the Merger;
B114 [L1029-L1029]: the risk that all conditions to the parties obligations to complete the Offer and the Merger are not satisfied, and as a result, the Merger is not completed;
B115 [L1031-L1033]: the risks and costs to Medivation if the Transactions do not close, including uncertainty about the effect of the proposed Offer and Merger on Medivations employees, customers and other partie... Medivations ability to attract, retain and motivate key personnel, and could cause customers, suppliers and others to seek to change existing business relationships with Medivation; ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
B116 [L1035-L1035]: the possibility that under certain circumstances, Medivation may be required to pay Parent a termination fee of $510 million;
B117 [L1037-L1037]: the fact that the gain realized by Medivations stockholders as a result of the Offer and the Merger generally will be taxable to the stockholders for U. S. federal income tax purposes;
B118 [L1039-L1041]: the restrictions in the Merger Agreement on the conduct of Medivations business prior to the consummation of the Merger, which may delay or prevent Medivation from undertaking business or othe... may arise prior to the consummation of the Offer or the Merger; and ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
B119 [L1043-L1043]: various other risks associated with the Merger and the business of Medivation described in the section entitled  Risk Factors.
B120 [L1045-L1046]: Our Board of Directors concluded that the risks, uncertainties, restrictions and potentially negative reasons associated with the Offer and Merger were outweighed by the potential benefits of the Offer and Merger.
B121 [L1048-L1053]: The foregoing discussion of our Board of Directors reasons for its recommendation to accept the Offer is not meant to be exhaustive, but addresses the material information and factors considered by our Board of Directors in connection with its recommendation. In view of the wide variety of reasons considered by our Board of Directors in connection with the evaluation of the Offer and the complexity of these matters, our Board of Directors did not find it practicable to, and did not, quantify or otherwise assign relative weights to the specific reasons considered in reaching its determination and recommendation. Rather, our directors made their determinations and recommendations based on the totality of the information presented to them, and the judgments of individual members of our Board of Directors may have been influenced to a greater or lesser degree by different reasons. In arriving at their respective recommendations, the members of our Board of Directors considered the interests of our executive officers and directors as described under  Past Contacts, Transactions, Negotiations and Agreements in Item 3 above.
B122 [L1055-L1057]: The foregoing description of the consideration by our Board of Directors of the reasons supporting the Merger Agreement, the Offer, the Merger and the other Transactions contemplated by the Merger Agreement is forward-looking in nature. This information should be read in light of the factors discussed in the section entitled Cautionary Note Regarding Forward-Looking Statements.
B123 [L1059-L1059]: (iii)      Certain Unaudited Prospective Financial Information
B124 [L1061-L1065]: Medivation does not, as a matter of course, publicly disclose forecasts or internal projections as to future performance or results of operations due to the inherent unpredictability of the underlying assumptions and projections. However, in connection with the review of potential strategic alternatives, at the direction of the Board of Directors, management of Medivation prepared three sets of unaudited, long-range financial projections (collectively  Projections), reflecting three different scenarios, with each scenario using a different set of assumptions about future regulatory approvals for Medivations products: (a) a case that included (i) indications for which Medivation has or has filed for regulatory approval, (ii) indications that are being evaluated in ongoing registrational trials, (iii)
B125 [L1067-L1067]: 26
B126 [L1070-L1074]: indications that are being evaluated in ongoing trials where top-line results are expected to be available in calendar year 2016 and (iv) indications for which Medivation expected registrational trials to be initiated in calendar year 2016 (collectively, the  Scenario 1 Case)1; (b) a case that included all of the indications described in the foregoing clause (a) and also included (i) all indications that are being evaluated in ongoing trials where top-line results are expected to be reported in calendar year 2017 or in later years and (ii) indications for enzalutamide and pidilizumab where Medivation planned to initiate studies in 2017 or in later years (collectively, the  Scenario 2 Case)2; and (c) a case that included all of the indications described in the foregoing clauses (a) and (b) and also included all indications for talazoparib where Medivation planned to initiate clinical studies in calendar year 2017 or in later years (collectively, the  Scenario 3 Case)3.
B127 [L1076-L1076]: Medivation provided the Projections to the Board of Directors and to J. P. Morgan and
B128 [L1077-L1078]: Evercore and directed each of J. P. Morgan and Evercore, respectively, to use the Projections in connection with the rendering of its fairness opinion to the Board of Directors and performing its related financial analyses, as described above under the heading  Opinions of Financial Advisors in this Item 4 of this Schedule 14D-9. The Scenario 3 Case was provided to Parent and to each of Company 1, Company 2, Company 3 and Company 4.
B129 [L1080-L1085]: The summary of the Projections set forth below is included solely to give Medivation stockholders access to certain financial projections that were made available to the Board of Directors and advisors and, solely with respect to the Scenario 3 Case, Parent, Company 1, Company 2, Company 3 and Company 4, and is not being included in this Schedule 14D-9 in order to influence any stockholders decision to tender Shares in the Offer or any other purpose. The Projections were prepared by management for internal use. The Projections were not prepared with a view toward public disclosure, or with a view toward compliance with published guidelines of the SEC, the guidelines established by the American Institute of Certified Public Accountants for preparation and presentation of financial forecasts, or United States generally accepted accounting principles ( GAAP). Neither our independent registered public accounting firm, nor any other independent accountants, have compiled, examined or performed any procedures with respect to the prospective financial information included below, or expressed any opinion or any other form of assurance on such information or its achievability.
B130 [L1087-L1090]: The Projections reflect numerous estimates and assumptions made by Medivations management with respect to general business, economic, competitive, regulatory, reimbursement and other market and financial conditions and other future events, all of which are difficult to predict and many of which are beyond Medivations control. For example, in preparing the Projections, Medivations management assumed and applied a 20% probability to the Scenario 1 Case and a 40% probability to each of the Scenario 2 Case and the Scenario 3 Case, which assumptions were provided to Medivations financial advisors, but not to Parent, Company 1, Company 2, Company 3 and Company 4.
B131 [L1092-L1092]: 1      The Scenario 1 Case includes management projections accounting for (i) XTANDI in three indications for prostate cancer (its currently approved indication of metastatic castration-resistant pros...
B132 [L1094-L1094]: 2      The Scenario 2 Case includes the management projections for XTANDI, talazoparib and pidilizumab included in the Scenario 1 Case, together with management projections accounting for (i) XTANDI f...
B133 [L1096-L1096]: 3      The Scenario 3 Case includes the management projections for XTANDI, pidilizumab and talazoparib included in the Scenario 2 Case, together with management projections accounting for talazoparib ...
B134 [L1098-L1098]: 27
B135 [L1101-L1106]: The Projections reflect subjective judgment in many respects and, therefore, are susceptible to multiple interpretations and periodic revisions based on actual experience and business developments. There can be no assurance that the underlying assumptions will prove to be accurate or that the forecasted results will be realized, and actual results likely will differ, and may differ materially, from those reflected in the Projections, whether or not the Offer and the Merger are completed. The inclusion of the Projections should not be regarded as an indication that we, J. P. Morgan, Evercore, any of their respective affiliates or anyone else who received the Projections then considered, or now considers, the Projections to be necessarily predictive of actual future events, and this information should not be relied upon as such. Medivations management views the Projections as being subject to inherent risks and uncertainties associated with such long-range projections. Medivations management, J. P. Morgan and Evercore do not intend to, and disclaims any obligation to, update, revise or correct the Projections if any of them are or become inaccurate (even in the short term).
B136 [L1108-L1111]: In particular, the Projections, while presented with numerical specificity, necessarily were based on numerous variables and assumptions that are inherently uncertain. Because the Projections cover multiple years, by their nature, they become subject to greater uncertainty with each successive year and are unlikely to anticipate each circumstance that will have an effect on Medivations business and its results of operations. The Projections also reflect assumptions as to certain business decisions that are subject to change. Modeling and forecasting the future in the pharmaceutical industry is, in particular, a highly speculative endeavor.
B137 [L1113-L1116]: By including the summary of the Projections in this Schedule 14D-9, none of Medivation, J. P. Morgan, Evercore or any of their respective affiliates or representatives has made or makes any representation to any person regarding the information included in the Projections or the ultimate performance of Medivation, Parent, Buyer or any of their respective affiliates compared to the information contained in the Projections. Medivation has made no representation to Parent or Buyer, in the Merger Agreement or otherwise, concerning the Projections. Neither Medivation nor J. P. Morgan nor Evercore nor any of their respective affiliates assumes any responsibility to holders of Shares for the accuracy of this information.
B138 [L1118-L1120]: The Projections summarized in this section were prepared during the periods described below and have not been updated to reflect any changes after the date they were prepared. The Projections do not take into account any circumstances or events occurring after the date they were prepared. Stockholders are cautioned not to place undue, if any, reliance on the Projections included in this Schedule 14D-9.
B139 [L1122-L1122]: Scenario 1 Case
B140 [L1124-L1124]: (dollars in millions)
B141 [L1126-L1134]: ────────────────────────────────────────────────────────────────────────────────────────────────────── Total revenue(1)           1,543      1,942      2,497      2,993      3,634      4,507      1,248 Operating expenses(2)        702        736        740        718        835      1,002        437 EBIT(3)                      841      1,205      1,757      2,275      2,799      3,505        811 EBIAT(4)                     510        771      1,142      1,477      1,820      2,325        602 D& A                          11         14         17         20         26         33         13 Capex                         12         16         22         27         38         52         13 Change in NWC                  0          1          2          2          5          7         10 Free Cash Flow(5)            510        767      1,136      1,469      1,803      2,298        612
B142 [L1136-L1136]: (1)      Revenues shown account for Medivations share of XTANDI revenues in accordance with Medivations collaboration agreement with Astellas Pharma, Inc. and deductions for certain royalty and milest...
B143 [L1138-L1138]: (2)      Excludes early research development expenses not allocable to the programs described in the Scenario 1 Case.
B144 [L1140-L1140]: (3)      EBIT is calculated as total revenue minus cost of goods sold, sales, general and administrative expenses, research and development costs, in each case, determined in accordance with GAAP, and n...
B145 [L1142-L1142]: (4)      EBIAT is calculated as EBIT minus taxes. EBIAT is a non-GAAP financial measure and should not be considered as an alternative to operating income or net income as a measure of operating perform...
B146 [L1144-L1144]: (5)      Free Cash Flow is calculated as EBIAT plus depreciation & amortization minus capital expenditure and change in net working capital. Free Cash Flow is a non-GAAP financial measure and should not...
B147 [L1146-L1146]: 28
B148 [L1149-L1149]: Scenario 2 Case
B149 [L1151-L1151]: (dollars in millions)
B150 [L1153-L1161]: ────────────────────────────────────────────────────────────────────────────────────────────────────── Total revenue(1)           1,543      1,942      2,497      2,994      3,699      5,821      1,790 Operating expenses(2)        767        807        816        792        901      1,363        634 EBIT(3)                      776      1,135      1,681      2,202      2,798      4,458      1,156 EBIAT(4)                     469        726      1,094      1,431      1,819      2,961        821 D& A                          11         14         17         20         26         44         19 Capex                         12         16         22         27         39         72         19 Change in NWC                  0          1          2          2          5         10         11 Free Cash Flow(5)            468        723      1,087      1,423      1,802      2,922        832
B151 [L1163-L1163]: (1)      Revenues shown account for Medivations share of XTANDI revenues in accordance with Medivations collaboration agreement with Astellas Pharma, Inc. and deductions for certain royalty and milest...
B152 [L1165-L1165]: (2)      Excludes early research development expenses not allocable to the programs described in the Scenario 2 Case.
B153 [L1167-L1167]: (3)      EBIT is calculated as total revenue minus cost of goods sold, sales, general and administrative expenses, research and development costs, in each case, determined in accordance with GAAP, and n...
B154 [L1169-L1169]: (4)      EBIAT is calculated as EBIT minus taxes. EBIAT is a non-GAAP financial measure and should not be considered as an alternative to operating income or net income as a measure of operating perform...
B155 [L1171-L1171]: (5)      Free Cash Flow is calculated as EBIAT plus depreciation & amortization minus capital expenditure and change in net working capital. Free Cash Flow is a non-GAAP financial measure and should not...
B156 [L1173-L1173]: Scenario 3 Case
B157 [L1175-L1175]: (dollars in millions)
B158 [L1177-L1185]: ────────────────────────────────────────────────────────────────────────────────────────────────────── Total revenue(1)           1,541      5,157      6,374      7,264      7,989      8,523      2,590 Operating expenses(2)        888      1,291      1,576      1,735      1,857      1,936        923 EBIT(3)                      653      3,866      4,798      5,528      6,132      6,588      1,667 EBIAT(4)                     346      2,583      3,233      3,734      4,145      4,467      1,229 D& A                          11         38         49         58         63         67         27 Capex                         12         65         87         99        104        105         27 Change in NWC                  0         11         14         10          7          5         21 Free Cash Flow(5)            345      2,546      3,182      3,682      4,097      4,425      1,250
B159 [L1187-L1187]: (1)      Revenues shown account for Medivations share of XTANDI revenues in accordance with Medivations collaboration agreement with Astellas Pharma, Inc. and deductions for certain royalty and milest...
B160 [L1189-L1189]: (2)      Excludes early research development expenses not allocable to the programs described in the Scenario 3 Case.
B161 [L1191-L1191]: (3)      EBIT is calculated as total revenue minus cost of goods sold, sales, general and administrative expenses, research and development costs, in each case, determined in accordance with GAAP, and n...
B162 [L1193-L1193]: (4)      EBIAT is calculated as EBIT minus taxes. EBIAT is a non-GAAP financial measure and should not be considered as an alternative to operating income or net income as a measure of operating perform...
B163 [L1195-L1195]: (5)      Free Cash Flow is calculated as EBIAT plus depreciation & amortization minus capital expenditure and change in net working capital. Free Cash Flow is a non-GAAP financial measure and should not...
B164 [L1197-L1197]: 29
B165 [L1200-L1200]: (iv)      Opinions of Financial Advisors
</chronology_blocks>

<overlap_context>
B074 [L911-L912]: During the evening of Friday, August 19, 2016 and early morning of Saturday, August 20, 2016, Wachtell Lipton and Cooley sent revised drafts of the merger agreement to each of Pfizer, Company 1, Company 2 and Company 3. In the evening of August 19, 2016, Company 3 notified Medivations financial advisors that Company 3 would not be submitting a revised proposal.
B075 [L914-L918]: On the morning of Saturday, August 20, 2016, at the request of legal advisors of Pfizer and Company 2, Wachtell Lipton and Cooley met telephonically with those legal advisors to answer questions concerning the form of merger agreement provided by Medivations legal advisors the previous evening. In each of these separate discussions, the representatives of Pfizer and the representatives of Company 2 indicated that Pfizer and Company 2, respectively, were prepared to accept and enter into a merger agreement substantially in the form proposed by Medivation the previous evening. During these conversations, Medivations legal advisors also repeated the instructions previously given to the Interested Parties to the effect that the Interested Party should expect that Medivation would enter into a merger agreement with the party submitting the best proposal at the noon deadline, and the Interested Party should not assume it would have any further opportunity to improve or increase its proposal should its proposal not be the highest and best.
</overlap_context>

<evidence_checklist>
### Dated actions to extract
- [ ] **0001193125-16-696911:E0218** L911-L912 (date: August 19, 2016; terms: proposal, sent)
- [ ] **0001193125-16-696911:E0221** L914-L918 (date: August 20, 2016; terms: met, proposal, proposed)
- [ ] **0001193125-16-696911:E0224** L920-L922 (date: August 20, 2016; value: $81.50 per share; terms: proposal, submitted)
- [ ] **0001193125-16-696911:E0228** L924-L925 (date: August 20, 2016; terms: met, sent)
- [ ] **0001193125-16-696911:E0229** L930-L943 (date: August 19, 2016; actor: Board; value: $81.50 per share; terms: delivered, discussed, meeting)
- [ ] **0001193125-16-696911:E0234** L945-L946 (date: August 20, 2016; terms: executed)
- [ ] **0001193125-16-696911:E0240** L964-L964 (date: April 27, 2016; terms: proposal)
- [ ] **0001193125-16-696911:E0248** L974-L977 (date: March; actor: Board; terms: meeting)
- [ ] **0001193125-16-696911:E0264** L1010-L1015 (date: August 20, 2016; actor: Board; terms: offer, proposed, sent)
- [ ] **0001193125-16-696911:E0273** L1039-L1041 (date: may; terms: offer)
- [ ] **0001193125-16-696911:E0276** L1048-L1053 (date: may; actor: Board; terms: offer, sent)
- [ ] **0001193125-16-696911:E0285** L1101-L1106 (date: may; actor: P. Morgan; terms: offer, received)

### Financial terms to capture
- [ ] **0001193125-16-696911:E0225** L920-L922 (date: August 20, 2016; value: $81.50 per share; terms: $80.00 per share, $80.25 per share, $81.50 per share)
- [ ] **0001193125-16-696911:E0230** L930-L943 (date: August 19, 2016; actor: Board; value: $81.50 per share; terms: $81.50 per share)
- [ ] **0001193125-16-696911:E0246** L972-L972 (actor: Board; value: $80.25; terms: $80.25, $81.50)
- [ ] **0001193125-16-696911:E0269** L1035-L1035 (date: may; value: $510; terms: $510)

### Actors to identify
- [ ] **0001193125-16-696911:E0219** L911-L912 (date: August 19, 2016; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0222** L914-L918 (date: August 20, 2016; terms: advisor, advisors, legal advisor)
- [ ] **0001193125-16-696911:E0226** L920-L922 (date: August 20, 2016; value: $81.50 per share; terms: party )
- [ ] **0001193125-16-696911:E0231** L930-L943 (date: August 19, 2016; actor: Board; value: $81.50 per share; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0236** L950-L954 (actor: Board; terms: advisor, advisors, legal advisor)
- [ ] **0001193125-16-696911:E0238** L956-L957 (actor: Board)
- [ ] **0001193125-16-696911:E0239** L959-L959 (actor: Board)
- [ ] **0001193125-16-696911:E0242** L966-L966 (actor: Board)
- [ ] **0001193125-16-696911:E0243** L968-L968 (actor: Board; terms: stockholder)
- [ ] **0001193125-16-696911:E0245** L970-L970 (actor: Board)
- [ ] **0001193125-16-696911:E0247** L972-L972 (actor: Board; value: $80.25)
- [ ] **0001193125-16-696911:E0249** L974-L977 (date: March; actor: Board; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0250** L983-L983 (actor: Board)
- [ ] **0001193125-16-696911:E0253** L992-L992 (terms: parent)
- [ ] **0001193125-16-696911:E0254** L996-L996 (terms: parent)
- [ ] **0001193125-16-696911:E0256** L998-L998 (terms: parent, stockholder)
- [ ] **0001193125-16-696911:E0257** L1000-L1000 (terms: stockholder)
- [ ] **0001193125-16-696911:E0258** L1002-L1002 (actor: Board)
- [ ] **0001193125-16-696911:E0260** L1006-L1006 (actor: Board)
- [ ] **0001193125-16-696911:E0262** L1008-L1008 (actor: Board; terms: stockholder)
- [ ] **0001193125-16-696911:E0265** L1010-L1015 (date: August 20, 2016; actor: Board; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0266** L1017-L1018 (actor: Board)
- [ ] **0001193125-16-696911:E0268** L1020-L1020 (terms: stockholder)
- [ ] **0001193125-16-696911:E0270** L1035-L1035 (date: may; value: $510; terms: parent)
- [ ] **0001193125-16-696911:E0272** L1037-L1037 (terms: stockholder)
- [ ] **0001193125-16-696911:E0275** L1045-L1046 (actor: Board)
- [ ] **0001193125-16-696911:E0277** L1048-L1053 (date: may; actor: Board)
- [ ] **0001193125-16-696911:E0278** L1055-L1057 (actor: Board)
- [ ] **0001193125-16-696911:E0280** L1061-L1065 (actor: Board)
- [ ] **0001193125-16-696911:E0282** L1076-L1078 (actor: Board; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0283** L1080-L1085 (actor: Board; terms: advisor, advisors, parent)
- [ ] **0001193125-16-696911:E0284** L1087-L1090 (terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0286** L1101-L1106 (date: may; actor: P. Morgan)
- [ ] **0001193125-16-696911:E0287** L1113-L1116 (actor: P. Morgan; terms: parent)
- [ ] **0001193125-16-696911:E0289** L1118-L1120 (terms: stockholder)

### Process signals to check
- [ ] **0001193125-16-696911:E0232** L930-L943 (date: August 19, 2016; actor: Board; value: $81.50 per share; terms: superior proposal)
- [ ] **0001193125-16-696911:E0244** L968-L968 (actor: Board; terms: strategic alternatives)
- [ ] **0001193125-16-696911:E0259** L1002-L1002 (actor: Board; terms: superior proposal)
- [ ] **0001193125-16-696911:E0281** L1061-L1065 (actor: Board; terms: strategic alternatives)

### Outcome facts to verify
- [ ] **0001193125-16-696911:E0220** L911-L912 (date: August 19, 2016; terms: merger agreement)
- [ ] **0001193125-16-696911:E0223** L914-L918 (date: August 20, 2016; terms: merger agreement)
- [ ] **0001193125-16-696911:E0227** L920-L922 (date: August 20, 2016; value: $81.50 per share; terms: merger agreement)
- [ ] **0001193125-16-696911:E0233** L930-L943 (date: August 19, 2016; actor: Board; value: $81.50 per share; terms: merger agreement, termination fee)
- [ ] **0001193125-16-696911:E0235** L945-L946 (date: August 20, 2016; terms: executed, merger agreement)
- [ ] **0001193125-16-696911:E0237** L950-L954 (actor: Board; terms: merger agreement)
- [ ] **0001193125-16-696911:E0241** L964-L964 (date: April 27, 2016; terms: closing)
- [ ] **0001193125-16-696911:E0251** L983-L983 (actor: Board; terms: merger agreement)
- [ ] **0001193125-16-696911:E0252** L990-L990 (terms: merger agreement)
- [ ] **0001193125-16-696911:E0255** L996-L996 (terms: merger agreement)
- [ ] **0001193125-16-696911:E0261** L1006-L1006 (actor: Board; terms: merger agreement)
- [ ] **0001193125-16-696911:E0263** L1008-L1008 (actor: Board; terms: merger agreement)
- [ ] **0001193125-16-696911:E0267** L1017-L1018 (actor: Board; terms: merger agreement)
- [ ] **0001193125-16-696911:E0271** L1035-L1035 (date: may; value: $510; terms: termination fee)
- [ ] **0001193125-16-696911:E0274** L1039-L1041 (date: may; terms: merger agreement)
- [ ] **0001193125-16-696911:E0279** L1055-L1057 (actor: Board; terms: merger agreement)
- [ ] **0001193125-16-696911:E0288** L1113-L1116 (actor: P. Morgan; terms: merger agreement)
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