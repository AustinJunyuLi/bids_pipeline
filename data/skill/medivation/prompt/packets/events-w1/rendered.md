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
- quotes: [{"quote_id": "Q001", "block_id": "B020", "text": "Party A submitted an indication of interest of $7.50 to $8.00 per share for all outstanding shares"}]
- proposal event for Party A: quote_ids=["Q001"], range $7.50-$8.00, whole_company_scope=true, contains_range=true, mentions_indication_of_interest=true
- exclusion for B019: partial_company_bid (UK and Europe business only)

### Example 2: Formal-round signal

Input:
B112 [L282-L282]: Beginning on December 19, 2012, representatives of BofA Merrill Lynch and Deutsche Bank, on behalf of the Company, sent final round process letters to OTPP, Bidder A and Bidder B, which process letters requested bidders to submit a final binding offer.

Expected:
- quotes: [{"quote_id": "Q001", "block_id": "B112", "text": "representatives of BofA Merrill Lynch and Deutsche Bank, on behalf of the Company, sent final round process letters"}]
- final_round_ann event: quote_ids=["Q001"], date December 19, 2012, round_scope=formal

</few_shot_examples>

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

<actor_roster>
{
  "quotes": [
    {
      "quote_id": "Q001",
      "block_id": "B002",
      "text": "outside financial and legal advisors"
    },
    {
      "quote_id": "Q002",
      "block_id": "B003",
      "text": "Olivier Brandicourt, Chief Executive Officer of Sanofi"
    },
    {
      "quote_id": "Q003",
      "block_id": "B003",
      "text": "David Hung, M. D., President and Chief Executive Officer of Medivation"
    },
    {
      "quote_id": "Q004",
      "block_id": "B004",
      "text": "representatives of Cooley LLP ( Cooley), Medivations legal advisor"
    },
    {
      "quote_id": "Q005",
      "block_id": "B004",
      "text": "J. P. Morgan Securities LLC ( J. P. Morgan)"
    },
    {
      "quote_id": "Q006",
      "block_id": "B004",
      "text": "retained as independent financial advisor to Medivation"
    },
    {
      "quote_id": "Q007",
      "block_id": "B009",
      "text": "non-binding proposal from Sanofi to acquire Medivation for $52.50 per share"
    },
    {
      "quote_id": "Q008",
      "block_id": "B012",
      "text": "Douglas Giordano, Senior Vice President, Worldwide Business Development at Pfizer"
    },
    {
      "quote_id": "Q009",
      "block_id": "B013",
      "text": "Evercore Group L. L. C. ( Evercore) as an additional independent financial advisor"
    },
    {
      "quote_id": "Q010",
      "block_id": "B016",
      "text": "Wachtell, Lipton, Rosen & Katz ( Wachtell Lipton)"
    },
    {
      "quote_id": "Q011",
      "block_id": "B016",
      "text": "which Medivation had retained as an additional legal advisor"
    },
    {
      "quote_id": "Q012",
      "block_id": "B017",
      "text": "Richards, Layton & Finger, P. A., Medivations Delaware counsel"
    },
    {
      "quote_id": "Q013",
      "block_id": "B006",
      "text": "three industry participants contacted J. P. Morgan"
    },
    {
      "quote_id": "Q014",
      "block_id": "B006",
      "text": "a fourth industry participant contacted Dr. Hung"
    },
    {
      "quote_id": "Q015",
      "block_id": "B021",
      "text": "Weil Gotshal & Manges LLP ( Weil Gotshal), Sanofis legal counsel"
    },
    {
      "quote_id": "Q016",
      "block_id": "B044",
      "text": "directed J. P. Morgan and Evercore to contact select industry participants"
    },
    {
      "quote_id": "Q017",
      "block_id": "B044",
      "text": "the four companies that had contacted J. P. Morgan and Dr. Hung in late March 2016"
    },
    {
      "quote_id": "Q018",
      "block_id": "B044",
      "text": "Pfizer, which had first contacted Dr. Hung on April 20, 2016"
    },
    {
      "quote_id": "Q019",
      "block_id": "B045",
      "text": "J. P. Morgan and Evercore contacted eleven industry participants"
    },
    {
      "quote_id": "Q020",
      "block_id": "B045",
      "text": "Medivation also contacted a twelfth industry participant"
    },
    {
      "quote_id": "Q021",
      "block_id": "B047",
      "text": "Medivation entered into confidentiality agreements with Pfizer"
    },
    {
      "quote_id": "Q022",
      "block_id": "B047",
      "text": "one additional party initially contacted by Medivations financial advisors"
    },
    {
      "quote_id": "Q023",
      "block_id": "B051",
      "text": "Medivation entered into a confidentiality agreement with Sanofi"
    },
    {
      "quote_id": "Q024",
      "block_id": "B057",
      "text": "hereinafter referred to as Company 1, Company 2, Company 3, and Company 4"
    },
    {
      "quote_id": "Q025",
      "block_id": "B057",
      "text": "Pfizer, Company 1, Company 2, Company 3 and Company 4 are referred to as the Interested Parties"
    },
    {
      "quote_id": "Q026",
      "block_id": "B053",
      "text": "Ian Read, Chief Executive Officer of Pfizer"
    },
    {
      "quote_id": "Q027",
      "block_id": "B064",
      "text": "Pfizer submitted a preliminary proposal for the all-cash acquisition"
    },
    {
      "quote_id": "Q028",
      "block_id": "B064",
      "text": "Company 1 submitted a preliminary proposal for the all-cash acquisition"
    },
    {
      "quote_id": "Q029",
      "block_id": "B064",
      "text": "Company 2 submitted a preliminary proposal for the all-cash acquisition"
    },
    {
      "quote_id": "Q030",
      "block_id": "B064",
      "text": "Company 3 submitted a preliminary proposal to acquire Medivation"
    },
    {
      "quote_id": "Q031",
      "block_id": "B064",
      "text": "Company 4 submitted a preliminary proposal to acquire Medivation"
    },
    {
      "quote_id": "Q032",
      "block_id": "B079",
      "text": "representatives of J. P. Morgan and Evercore presented the final proposals"
    },
    {
      "quote_id": "Q033",
      "block_id": "B079",
      "text": "Representatives of Cooley and Wachtell Lipton reviewed each proposal"
    },
    {
      "quote_id": "Q034",
      "block_id": "B080",
      "text": "Pfizer and Medivation executed the merger agreement"
    },
    {
      "quote_id": "Q035",
      "block_id": "B090",
      "text": "representatives of Medivation contacted 15 parties"
    },
    {
      "quote_id": "Q036",
      "block_id": "B044",
      "text": "the Medivation board of directors determined that"
    },
    {
      "quote_id": "Q037",
      "block_id": "B042",
      "text": "Sanofi filed with the SEC a preliminary consent solicitation statement"
    },
    {
      "quote_id": "Q038",
      "block_id": "B015",
      "text": "Sanofi issued a press release publicly announcing"
    },
    {
      "quote_id": "Q039",
      "block_id": "B046",
      "text": "increased proposal from Sanofi of $58.00 per share in cash"
    },
    {
      "quote_id": "Q040",
      "block_id": "B091",
      "text": "none of the other four bidders expressed a willingness"
    },
    {
      "quote_id": "Q041",
      "block_id": "B045",
      "text": "which included Pfizer and the four companies"
    },
    {
      "quote_id": "Q042",
      "block_id": "B065",
      "text": "authorized Medivations financial advisors to advance Pfizer, Company 1, and Company 4"
    },
    {
      "quote_id": "Q043",
      "block_id": "B128",
      "text": "Scenario 3 Case was provided to Parent and to each of Company 1, Company 2, Company 3 and Company 4"
    },
    {
      "quote_id": "Q044",
      "block_id": "B051",
      "text": "Sanofi agreed to terminate its Consent Solicitation"
    }
  ],
  "actors": [
    {
      "actor_id": "target_board_medivation",
      "display_name": "Medivation Board of Directors",
      "canonical_name": "MEDIVATION INC BOARD OF DIRECTORS",
      "aliases": [
        "Board of Directors",
        "our Board of Directors",
        "Medivation board of directors"
      ],
      "role": "target_board",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": null,
      "listing_status": "public",
      "geography": "domestic",
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": ["Q001", "Q036"],
      "notes": []
    },
    {
      "actor_id": "bidder_sanofi",
      "display_name": "Sanofi",
      "canonical_name": "SANOFI",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": "strategic",
      "listing_status": "public",
      "geography": "non_us",
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": ["Q002", "Q007", "Q037", "Q038", "Q039", "Q044"],
      "notes": [
        "Based in Paris, France. Initiated unsolicited approach. Filed consent solicitation to replace Medivation board."
      ]
    },
    {
      "actor_id": "bidder_pfizer",
      "display_name": "Pfizer",
      "canonical_name": "PFIZER INC",
      "aliases": [
        "Parent",
        "Purchaser"
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
      "quote_ids": ["Q008", "Q018", "Q021", "Q026", "Q027", "Q034"],
      "notes": [
        "First contacted Dr. Hung on April 20, 2016. Winning bidder at $81.50 per share."
      ]
    },
    {
      "actor_id": "bidder_company1",
      "display_name": "Company 1",
      "canonical_name": "COMPANY 1",
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
      "quote_ids": ["Q024", "Q028"],
      "notes": [
        "Filing alias. Industry participant that signed NDA and submitted bids."
      ]
    },
    {
      "actor_id": "bidder_company2",
      "display_name": "Company 2",
      "canonical_name": "COMPANY 2",
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
      "quote_ids": ["Q024", "Q029"],
      "notes": [
        "Filing alias. Initially excluded after first round ($62-$64), re-entered with $70.00 revised bid."
      ]
    },
    {
      "actor_id": "bidder_company3",
      "display_name": "Company 3",
      "canonical_name": "COMPANY 3",
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
      "quote_ids": ["Q024", "Q030"],
      "notes": [
        "Filing alias. Initially excluded after first round ($60 + CVRs), re-entered with $70.50 revised bid. Dropped before final round."
      ]
    },
    {
      "actor_id": "bidder_company4",
      "display_name": "Company 4",
      "canonical_name": "COMPANY 4",
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
      "quote_ids": ["Q024", "Q031"],
      "notes": [
        "Filing alias. Advanced to second round but declined to submit definitive proposal on August 19, 2016."
      ]
    },
    {
      "actor_id": "advisor_jpmorgan",
      "display_name": "J.P. Morgan",
      "canonical_name": "J. P. MORGAN SECURITIES LLC",
      "aliases": [
        "J. P. Morgan"
      ],
      "role": "advisor",
      "advisor_kind": "financial",
      "advised_actor_id": "target_board_medivation",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": ["Q005", "Q006", "Q016", "Q032"],
      "notes": [
        "Retained as independent financial advisor based on long history with the Company."
      ]
    },
    {
      "actor_id": "advisor_evercore",
      "display_name": "Evercore",
      "canonical_name": "EVERCORE GROUP L.L.C.",
      "aliases": [
        "Evercore"
      ],
      "role": "advisor",
      "advisor_kind": "financial",
      "advised_actor_id": "target_board_medivation",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": ["Q009", "Q016", "Q032"],
      "notes": [
        "Engaged on April 22, 2016 as additional independent financial advisor."
      ]
    },
    {
      "actor_id": "advisor_cooley",
      "display_name": "Cooley LLP",
      "canonical_name": "COOLEY LLP",
      "aliases": [
        "Cooley"
      ],
      "role": "advisor",
      "advisor_kind": "legal",
      "advised_actor_id": "target_board_medivation",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": ["Q004", "Q033"],
      "notes": [
        "Medivation's primary legal advisor throughout the process."
      ]
    },
    {
      "actor_id": "advisor_wachtell",
      "display_name": "Wachtell, Lipton, Rosen & Katz",
      "canonical_name": "WACHTELL, LIPTON, ROSEN & KATZ",
      "aliases": [
        "Wachtell Lipton"
      ],
      "role": "advisor",
      "advisor_kind": "legal",
      "advised_actor_id": "target_board_medivation",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": ["Q010", "Q011", "Q033"],
      "notes": [
        "Retained as additional legal advisor by April 28, 2016."
      ]
    },
    {
      "actor_id": "advisor_richards_layton",
      "display_name": "Richards, Layton & Finger, P.A.",
      "canonical_name": "RICHARDS, LAYTON & FINGER, P.A.",
      "aliases": [],
      "role": "advisor",
      "advisor_kind": "legal",
      "advised_actor_id": "target_board_medivation",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": ["Q012"],
      "notes": [
        "Medivation's Delaware counsel."
      ]
    },
    {
      "actor_id": "advisor_weil_gotshal",
      "display_name": "Weil Gotshal & Manges LLP",
      "canonical_name": "WEIL GOTSHAL & MANGES LLP",
      "aliases": [
        "Weil Gotshal"
      ],
      "role": "advisor",
      "advisor_kind": "legal",
      "advised_actor_id": "bidder_sanofi",
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": false,
      "group_size": null,
      "group_label": null,
      "quote_ids": ["Q015"],
      "notes": [
        "Sanofi's legal counsel."
      ]
    },
    {
      "actor_id": "group_late_march_parties",
      "display_name": "Four industry participants (late March 2016)",
      "canonical_name": "FOUR LATE MARCH 2016 INDUSTRY PARTICIPANTS",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": true,
      "group_size": 4,
      "group_label": "four industry participants that indicated interest in late March 2016",
      "quote_ids": ["Q013", "Q014", "Q017"],
      "notes": [
        "Three contacted J.P. Morgan and one contacted Dr. Hung. Later included among the parties contacted by Medivation's financial advisors in late June 2016."
      ]
    },
    {
      "actor_id": "group_contacted_parties",
      "display_name": "Twelve contacted industry participants",
      "canonical_name": "TWELVE CONTACTED INDUSTRY PARTICIPANTS",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": true,
      "group_size": 12,
      "group_label": "twelve industry participants contacted in late June through early July 2016",
      "quote_ids": ["Q019", "Q020", "Q041"],
      "notes": [
        "J.P. Morgan and Evercore contacted eleven; Medivation contacted a twelfth directly. Includes Pfizer and the four late-March parties."
      ]
    },
    {
      "actor_id": "group_fifteen_parties",
      "display_name": "Fifteen parties contacted",
      "canonical_name": "FIFTEEN PARTIES CONTACTED",
      "aliases": [],
      "role": "bidder",
      "advisor_kind": null,
      "advised_actor_id": null,
      "bidder_kind": null,
      "listing_status": null,
      "geography": null,
      "is_grouped": true,
      "group_size": 15,
      "group_label": "15 parties contacted by representatives of Medivation",
      "quote_ids": ["Q035"],
      "notes": [
        "Board stated that representatives of Medivation contacted 15 parties. This is the broadest count referenced."
      ]
    }
  ],
  "count_assertions": [
    {
      "subject": "parties contacted",
      "count": 15,
      "quote_ids": ["Q035"]
    },
    {
      "subject": "industry participants contacted by financial advisors in late June-early July 2016",
      "count": 11,
      "quote_ids": ["Q019"]
    },
    {
      "subject": "twelfth industry participant contacted by Medivation directly",
      "count": 1,
      "quote_ids": ["Q020"]
    },
    {
      "subject": "industry participants that indicated interest in late March 2016",
      "count": 4,
      "quote_ids": ["Q013", "Q014"]
    },
    {
      "subject": "Interested Parties (NDA signatories who submitted preliminary bids)",
      "count": 5,
      "quote_ids": ["Q025"]
    },
    {
      "subject": "other four bidders besides Pfizer in final stages",
      "count": 4,
      "quote_ids": ["Q040"]
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