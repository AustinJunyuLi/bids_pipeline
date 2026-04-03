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
deal_slug: providence-worcester
target_name: PROVIDENCE & WORCESTER RR CO
source_accession_number: 0001193125-16-713780
source_form_type: UNKNOWN
chunk_mode: single_pass
window_id: w0
</deal_context>

<chronology_blocks>
B001 [L1279-L1279]: Background of the Merger
B002 [L1281-L1291]: In the fourth quarter of 2015, Robert H. Eder (the Companys Chairman and Chief Executive Officer) and Frank K. Rogers (the Companys Vice President and Chief Commercial Officer) met with one of the Companys Class I rail partners ( Party A) to discuss joint commercial opportunities. During the meeting, Party A suggested possible joint venture arrangements and expressed some interest in acquiring equity in the Company to further develop strategic opportunities and enhance regional connectivity. Upon receiving a report of this meeting, in recognition of its public company obligations, the Board appointed a subcommittee of two independent directors, Frank W. Barrett and Richard W. Anderson, to interview potential investment bankers to represent the Company in possible negotiations with Party A and to assist the Board in evaluating additional strategic options for the realization of shareholder value, including potential change in control transactions. The subcommittee interviewed several investment banking firms, including Greene Holcomb & Fisher LLC (the business of which was subsequently acquired by BMO Capital Markets Corp. and which we refer to as  GHF prior to such acquisition and  BMO thereafter). During the executive session of the Boards regular quarterly meeting held on January 27, 2016 (which Director Alfred P. Smith did not attend), the subcommittee recommended to the Board that the Company retain GHF as its investment banking firm. At that meeting, representatives of GHF discussed with the Board its qualifications and a proposed process should the directors ultimately decide to proceed with a change in control transaction. As part of the interview process, GHF represented to the Company that it would not represent any potential buyer of the Company in connection with an offer to purchase the Company or any person proposing to provide financing in connection with such an offer. Following this presentation, the Board approved the subcommittees recommendation and the Company engaged GHF. In selecting GHF, the Board considered, among other things, the fact that GHF was a reputable investment banking firm with substantial experience advising companies in the rail sector and in providing strategic advisory services in general, GHF had recent experience providing strategic advisory services in connection with the sale of a short-line railroad and, in the Boards opinion, GHF would commit appropriate attention, resources and personnel to the process.
B003 [L1293-L1297]: At a special meeting of the Board held on March 14, 2016, representatives of GHF discussed their evaluation of the Companys business operations and strategy for improving operational and financial performance, as well as railroad industry dynamics more generally and their impact on current railroad valuations. Representatives of GHF then proposed a process pursuant to which the Company would proceed with discussions with Party A and also solicit interest from other potential third parties regarding a change in control transaction. The Board considered various factors, including the marketplace, the risks attendant to engaging in the process discussed with representatives of GHF, the Companys overall strategic position, and the challenges attendant to improving the Companys financial performance in order to maximize shareholder value and concluded, based upon its examination of these and other factors, that it was in the best interest of the Company
B004 [L1299-L1299]: 27
B005 [L1302-L1307]: and its shareholders to proceed with the transaction strategy discussed with representatives of GHF. In light of the potentially significant time and effort involved in pursuing such exploratory transaction strategy, as well as the possible need to provide guidance to GHF and management on short notice, at the conclusion of the meeting, the Board appointed a special committee of independent directors of the Board (which we refer to as the  Transaction Committee), composed of Frank W. Barrett (Chair), Richard W. Anderson and James C. Garvey, for the purpose of assisting in the supervision and oversight of the process on the full Boards behalf and making a recommendation to the full Board. The Transaction Committee did not have the authority to approve or enter into a change of control transaction, which, under Rhode Island law, is an authority that can only be exercised by the full Board. At the time of appointment, Messrs. Barrett and Garvey had been elected by the preferred shareholders and Mr. Anderson had been elected by the common shareholders at the 2015 annual shareholders meeting. At the Companys 2016 annual shareholders meeting on April 27, 2016, Messrs. Barrett and Anderson were re-elected as directors by the common shareholders and Mr. Garvey was re-elected as a director by the preferred shareholders.
B006 [L1309-L1310]: On March 22, 2016 and March 23, 2016, Daniel T. Noreck (the Companys Chief Financial Officer and Treasurer) and other members of the senior management team of the Company met with various representatives of Party A.
B007 [L1312-L1318]: On March 24, 2016, the Transaction Committee met by telephone conference to discuss the results of managements meeting with Party A and to discuss next steps in the process. Members of management and representatives of each of GHF and the Companys legal counsel, Hinckley, Allen & Snyder LLP (which we refer to as  Hinckley Allen), participated in all meetings of the Transaction Committee, except as otherwise indicated. At this meeting, Mr. Noreck reported that he and other members of the senior management team had met with various representatives of Party A on March 22 and 23, 2016 and had informed Party A of GHFs engagement. The Transaction Committee authorized GHF to contact Party A as well as other potential buyers to determine their level of interest in a change in control transaction. During the week of March 28, 2016, in accordance with the Transaction Committees directives, representatives of GHF contacted 11 potential strategic buyers (including Party A) and 18 potential financial buyers. Each of the potential strategic buyers and 14 potential financial buyers subsequently executed confidentiality agreements. The confidentiality agreements did not contain any standstill or similar provision that would prohibit a potential buyer from submitting a proposal or making an offer to acquire the Company.
B008 [L1320-L1322]: Between April 3, 2016 and April 6, 2016, representatives of GHF and members of the Companys management held a series of introductory meetings with five potential strategic buyers (including G& W) at the American Short Line and Regional Railroad Associations 2016 Connections Convention (2016 Connections Convention).
B009 [L1324-L1328]: On April 7, 2016, the Transaction Committee met by telephone conference and discussed the process to date with representatives of GHF. Representatives of GHF reported that they and Company management had held a series of introductory meetings with five potential strategic buyers (including G& W) at the 2016 Connections Convention. Mr. Noreck reported that the Company had also approached two additional Class I railroads to determine their interest in a possible transaction. After discussion, the Transaction Committee authorized representatives of GHF, on behalf of the Company, to contact each of the five interested parties with whom management had met at the 2016 Connections Convention, as well as other potential strategic buyers (including certain Class I railroads) and private equity firms who had entered into confidentiality agreements with the Company to confirm their continuing interest. Subsequently, on April 21, 2016, the Company and representatives of GHF held an introductory meeting with another potential strategic buyer ( Party B).
B010 [L1330-L1332]: With the assistance of GHF, the Company prepared a memorandum concerning the Company and its prospects, which was distributed to the potential buyers, including Party A, Party B and G& W, that had executed confidentiality agreements. The Transaction Committee met with representatives of GHF by telephone conference on April 22, 2016 and discussed the status of discussions with potential buyers. On April 27, 2016,
B011 [L1334-L1334]: 28
B012 [L1337-L1338]: the Board met in executive session (without Mr. Eder present) with representatives of GHF and discussed the status of the process, including that each potential buyer had been advised to submit a non-binding indication of interest by May 10, 2016 (which deadline was subsequently postponed to May 19, 2016 to ensure the potential buyers had sufficient time to formulate their most compelling offers).
B013 [L1340-L1344]: Between May 19, 2016 and June 1, 2016, the Company received nine written indications of interest ( IOIs) from potential buyers, with offer prices per share ranging from $17.93 to $26.50 (assuming the conversion of preferred stock into common stock), implying equity values of $90 million to $134 million. The Transaction Committee met by telephone conference on May 23, 2016 and again on June 1, 2016 to consider the IOIs. In view of the substantial amount of management time that would be required for management presentations, the Transaction Committee concluded that the two low bidders should be excluded from that process. The Transaction Committee authorized representatives of GHF to schedule in-person management presentations with the remaining seven potential buyers and allow these parties to conduct additional due diligence. These potential buyers were given access to an internet data site to conduct legal and financial due diligence.
B014 [L1346-L1349]: In mid-June 2016, at the direction of the Transaction Committee, representatives of GHF instructed all potential buyers to submit non-binding letters of intent ( LOIs) by July 20, 2016, together with mark-ups of the forms of merger agreement, disclosure letter and voting agreement, which GHF indicated would be posted to the internet data site. Potential buyers were instructed to provide a valuation for the Company based on the purchase of 100% of the outstanding common stock on a dollar per share basis (assuming conversion of the preferred stock into common stock) or the financial terms of any non-cash proposal.
B015 [L1351-L1353]: On June 29, 2016, the Company posted an initial draft of merger agreement to the internet data site, and on June 30, 2016, the Company posted an initial draft of voting agreement with respect to the common stock and preferred stock held by the Eder Trusts. On July 11, 2016, the Company posted an initial draft of disclosure letter to the internet data site.
B016 [L1355-L1360]: Over the course of June and July 2016, each of the potential buyers and their respective advisors engaged in due diligence of the Companys business and financial condition, including holding meetings with certain members of the Companys management team. The Transaction Committee met on June 30, 2016 to receive a status update on the management presentations and due diligence efforts of the potential buyers. In early July 2016, a potential strategic buyer that had not previously been part of the process ( Party C) approached the Companys management and expressed interest in acquiring the Company. After executing a confidentiality agreement, Party C was provided the memorandum concerning the Company provided to the other potential buyers. On July 12, 2016, Party C submitted an IOI with an offer price per share of $21.00 (implying an equity value of $108 million). Subsequently, Party C was provided access to the internet data site and the Companys management held a management presentation with Party C by telephone on July 14, 2016.
B017 [L1362-L1364]: In late July 2016, the Company received six LOIs with offer prices per share ranging from $19.20 to $24.00 (implying equity values of $96 million to $121 million). Party B, G& W and another bidder ( Party D) also provided mark-ups of the draft merger agreement and voting agreement. One bidder ( Party E) provided a summary of material issues and proposed changes to the merger agreement and voting agreement with respect to those issues.
B018 [L1366-L1366]: Party B submitted an LOI to acquire the Company for a price of $24.00 per share (subject to an expedited diligence review).
B019 [L1368-L1368]: G& W submitted an LOI on July 21, 2016 to acquire the Company for a price of $21.15 per share (subject to a three-week exclusive diligence period). The price included $20.02 cash at closing and...
B020 [L1370-L1370]: 29
B021 [L1373-L1373]: Party E (a strategic buyer) submitted an LOI to acquire the Company for a price of $21.26 per share (subject to a 60-day exclusivity period for due diligence and negotiation of definitive docum...
B022 [L1375-L1375]: Party D (a financial buyer) submitted an LOI to acquire the Company for a price of $21.00 per share (subject to a four-week diligence period).
B023 [L1377-L1377]: Party C submitted an LOI to acquire the Company for a price of $19.30 per share (subject to a 30-day diligence period).
B024 [L1379-L1379]: Party F (a strategic buyer) submitted an LOI to acquire the Company for a price of $19.20 per share (subject to a 30-day due diligence period).
B025 [L1381-L1382]: In addition to various due diligence requirements, the LOI prices were based on different assumptions and requirements related to transaction expenses and change in control payments, which GHF and the Transaction Committee observed could affect the ultimate offer price. One strategic buyer and one financial buyer elected not to submit an LOI.
B026 [L1384-L1391]: The Transaction Committee met by telephone conference on July 22, 2016 and in person after the regular quarterly Board meeting on July 27, 2016, to review the LOIs with representatives of GHF. Representatives of GHF reviewed the material financial terms of each LOI, including the offer price, and additional due diligence requested. The Transaction Committee discussed the process for the on-site due diligence requested by the bidders, the delays inherent in managing on-site due diligence by multiple parties and the difficulties of maintaining the confidentiality of the discussions. The Transaction Committee concluded that the Company should proceed with confirmatory due diligence and negotiations with G& W and Party B because of the higher offers made by each of G& W and Party B relative to the other potential buyers. At the direction of the Transaction Committee, representatives of GHF subsequently contacted the remaining bidders to inform them that they were no longer involved in the process. The Transaction Committee updated the independent directors (other than Director Smith) regarding the process at a meeting held immediately prior to the Boards regular quarterly meeting on July 27, 2016. Director Smith is Vice President and Group Executive, Locomotive Group of GATX Corporation ( GATX), which owns 4.92% of the Companys common stock. In order to avoid any potential conflict, Mr. Smith elected to recuse himself from participating in this and other Board meetings at which the bidding process and any potential transaction were to be discussed because of the possibility that GATX might be a potential buyer of the Company.
B027 [L1393-L1399]: On July 29, 2016, representatives of GHF had calls with Party D and Party E. During those calls, Party D and Party E both expressed interest in reengaging and enhancing their offers. On August 1, 2016, Party D submitted a revised LOI at a price of $24.00 per share and Party E submitted a revised LOI, along with financing support, from Party F, at a price of $23.81 per share. Both revised proposals contained a 30-day due diligence period. The Transaction Committee convened by telephone conference on August 1, 2016, to consider the revised LOIs submitted by Party D and Party E and subsequently directed representatives of BMO (which acquired the business of GHF on August 1, 2016) to clarify certain elements of the revised proposals and the bidders respective due diligence requirements. Party E withdrew its revised proposal on August 2, 2016 (but confirmed its original proposal of $21.26 per share) and Party D declined to shorten its due diligence period and requested that the Company commit that it would not enter into an agreement with another bidder during its30-daydue diligence period. In light of the active interest of Party B and G& W, the Company declined to make such a commitment, at which point Party D indicated that it would not proceed with further due diligence at that time.
B028 [L1401-L1404]: On August 1, 2016, Hinckley Allen provided Party B with a revised merger agreement and voting agreement, reflecting changes from the marked-up documents included with Party Bs LOI. On August 3, 2016, Hinckley Allen provided G& W with a revised merger agreement and voting agreement, reflecting changes from the marked-up documents included with G& Ws LOI. On August 3, 2016, the Company and Hinckley Allen also responded to additional due diligence questions submitted by Party B. On August 4, 2016, the Transaction Committee met by conference call to discuss the process with representatives of BMO and Hinckley Allen on the
B029 [L1406-L1406]: 30
B030 [L1409-L1411]: status of negotiations and due diligence. During that discussion, the Transaction Committee directed the management team and representatives of each of BMO and Hinckley Allen to continue diligence and negotiations with both G& W and Party B, but given the higher price offered by Party B, to prioritize Party B and proceed to complete the negotiation of the merger agreement with Party B. From July 27, 2016 through August 11, 2016, Party B and G& W conducted on-site financial, legal and environmental due diligence, including hi-rail trips to inspect the Companys track infrastructure.
B031 [L1413-L1419]: On August 4, 2016, legal counsel for Party B provided a revised draft of the merger agreement and, following negotiations between their respective legal counsels, the Company provided Party B with a revised draft of the merger agreement and disclosure letter on August 5, 2016. On August 9, 2016, the Transaction Committee met by telephone conference to review the status of the negotiations and due diligence. Following that discussion, the Transaction Committee directed representatives of BMO to inform G& W that the Company intended to enter into a merger agreement with another bidder. G& W requested that it be allowed to continue its due diligence, including physical due diligence on August 10 and August 11, 2016, to potentially facilitate an improved offer, which request was granted. On August 10, 2016, representatives of Hinckley Allen and Simpson Thacher & Bartlett LLP (which we refer to as  Simpson Thacher), G& Ws legal counsel, discussed various provisions of the draft merger agreement and voting agreement that had been provided to G& W on August 3, 2016, and Hinckley Allen provided Simpson Thacher with a revised disclosure letter to accompany the August 3 draft merger agreement. On August 11, 2016, G& W indicated its possible intention to submit a revised LOI on August 12, 2016, having just completed its physical diligence of the Companys track infrastructure.
B032 [L1421-L1427]: Based upon progress made in due diligence and the negotiations with Party B during the week of August 8, 2016, meetings of the Transaction Committee and Board were scheduled for August 12, 2016 in anticipation of reviewing final agreements and approving a transaction with Party B. On the morning of August 12, 2016, following a discussion between representatives of BMO and G& W in which G& W indicated it would be submitting a revised LOI, G& W submitted a revised LOI to acquire the Company for a price of $25.00 per share in cash, which excluded the previously proposed CVR, together withmark-upsof the merger agreement and the voting agreement. G& Ws LOI further indicated that the offer would expire at 6:00 p. m. on the following day. Later that day, Simpson Thacher submitted a mark-up of the disclosure letter. Upon receipt of the revised LOI and related merger documents, Hinckley Allen and Simpson Thacher negotiated revisions to the merger agreement and disclosure letter. The Transaction Committee met at 10:30 a. m. on August 12, 2016, and reviewed the status of the negotiations and merger documents with both Party B and G& W. Following that discussion, the Transaction Committee directed representatives of BMO to inform Party B that another party had submitted a revised LOI at a higher price.
B033 [L1429-L1436]: On the afternoon of August 12, 2016, following the meeting of the Transaction Committee, the Board held a special meeting to review and consider the recommendation of the Transaction Committee with respect to a potential sale transaction. All directors were present in person or by telephone other than Director Smith. The Transaction Committee reported on the process and the status of the negotiations with Party B and G& W. Drafts of the Party B merger agreement, voting agreement and disclosure letter and drafts of the G& W merger agreement, voting agreement and disclosure letter were provided to the directors at the meeting. Hinckley Allen reviewed the material terms of the draft merger agreements provided by Party B and G& W, and the differences between the G& W draft merger agreement and the Party B draft merger agreement. Hinckley Allen also reviewed the Boards fiduciary obligations in connection with the proposed transaction and responded to questions from the directors. Hinckley Allen advised the Board that both Party Bs and G& Ws draft merger agreements restricted the Company from soliciting a competing proposal, subject to a fiduciary out for an unsolicited superior proposal, which required the Company to pay a termination fee equal to 3% of the transaction value in the case of G& W (which the Company had negotiated down from 3.85%) and 3% plus Party Bs transaction expenses (capped at 1% of transaction value) in the case of Party B, in the event the merger agreement was terminated as a result of the Boards decision to pursue such a proposal.
B034 [L1438-L1438]: Hinckley Allen advised the Board
B035 [L1439-L1439]: that the draft merger agreement and disclosure letter for both Party B and G& W had minor differences but were substantively the same, except for the following: (1) the price offered by
B036 [L1441-L1441]: 31
B037 [L1444-L1449]: G& W was $1.00 more per share; (2) the termination fee payable by the Company in the event the Board exercised its fiduciary out in order to accept a superior proposal was less under the G& W draft agreement than the Party B draft agreement; and (3) the STB approval process for G& W and Party B would be different since G& W owned connecting railroads. The Board arranged a telephone call with the Companys STB counsel to discuss the process for obtaining the required regulatory approval or exemption for the transaction, the risks associated with each process, the use of a voting trust to enable an earlier closing of the transaction (as contemplated by the G& W merger agreement) and the likely timeframe for obtaining any regulatory clearance for a transaction with either Party B or G& W. Based upon that discussion, the Board determined that the timeframe for, and the likelihood of, obtaining the required regulatory approval was not materially different for a transaction with G& W versus a transaction with Party B. At the request of the Board, representatives of BMO then contacted Party B to determine if it would increase its offer price. Party B indicated that it would not increase its price.
B038 [L1451-L1460]: The Board determined that the G& W offer represented the superior proposal. At the request of the Board, representatives of BMO reviewed BMOs financial analyses supporting its opinion to the Board as to the fairness, from a financial point of view, to the holders of our common stock of the consideration to be received by those holders (other than the Eder Trusts) in the merger pursuant to the merger agreement as of August 12, 2016. At the request of the Board, BMO confirmed that it did not have any existing or contemplated material relationships with G& W in connection with the provision of any financial advisory or financing services to G& W. BMO then rendered an oral opinion to the Board, subsequently confirmed by delivery of a written opinion, dated August 12, 2016 to the effect that, as of that date, and based upon and subject to the various assumptions made, procedures followed, matters considered and qualifications and limitations on the scope of review undertaken by BMO as set forth in its written opinion, the merger consideration to be received by the holders of our common stock in the merger pursuant to the merger agreement was fair, from a financial point of view, to those holders (other than the Eder Trusts). Following a discussion of the terms of the merger agreement and related matters, the Board (other than Director Smith, who recused himself from the August 12, 2016 meeting) (i) determined that the merger agreement, the plan of merger and the merger and other transactions contemplated by the merger agreement are fair to, advisable and in the best interests of the Company and its shareholders, (ii) approved and declared advisable the merger agreement and the transactions contemplated thereby, including the merger and the plan of merger, (iii) directed that the merger agreement be submitted to the Companys shareholders for approval and (iv) resolved to recommend that the Companys shareholders approve the merger agreement and the transactions contemplated thereby, including the merger and the plan of merger.
B039 [L1462-L1464]: Shortly thereafter, Hinckley Allen and Simpson Thacher finalized the transaction documents and the Company and G& W executed the merger agreement, and the Company, G& W and the Eder Trusts executed the voting agreement. The Company issued a press release publicly announcing the transaction on Monday, August 15, 2016 prior to the opening of trading of the Companys common stock on the NASDAQ.
B040 [L1466-L1466]: Subsequent to the delivery of BMOs opinion and the Boards approval of the
B041 [L1467-L1469]: merger agreement and voting agreement, representatives of BMO advised the Board that when checking to determine if there were any financial advisory or financing relationships with G& W, it had inadvertently failed to identify that a BMO affiliate has a participation in G& Ws existing secured syndicated debt facility as described under the section titled  Summary of Financial Analysis of BMO Capital Markets Corp. Miscellaneous on page 41. On September 6, 2016, the Board considered this new information, determined this relationship was not material to BMOs independence and confirmed that the Board remained comfortable with the engagement and opinion of BMO.
</chronology_blocks>

<evidence_checklist>
### Dated actions to extract
- [ ] **0001193125-16-713780:E0315** L1281-L1291 (date: January 27, 2016; actor: Party A; terms: discussed, engaged, meeting)
- [ ] **0001193125-16-713780:E0317** L1293-L1297 (date: March 14, 2016; actor: Party A; terms: discussed, meeting, proposed)
- [ ] **0001193125-16-713780:E0319** L1302-L1307 (date: April 27, 2016; actor: Board; terms: discussed, meeting, sent)
- [ ] **0001193125-16-713780:E0321** L1309-L1310 (date: March 22, 2016; actor: Party A; terms: met, sent)
- [ ] **0001193125-16-713780:E0323** L1312-L1318 (date: March 24, 2016; actor: Party A; terms: authorized, contacted, executed)
- [ ] **0001193125-16-713780:E0327** L1320-L1322 (date: April 3, 2016; terms: meeting, sent)
- [ ] **0001193125-16-713780:E0328** L1324-L1328 (date: April 7, 2016; actor: Party B; terms: authorized, discussed, entered into)
- [ ] **0001193125-16-713780:E0331** L1330-L1332 (date: April 22, 2016; actor: Party A; terms: discussed, executed, met)
- [ ] **0001193125-16-713780:E0335** L1337-L1338 (date: May 10, 2016; actor: Board; terms: discussed, met, offer)
- [ ] **0001193125-16-713780:E0337** L1340-L1344 (date: May 19, 2016; actor: Transaction Committee; value: $17.93 to $26.50; terms: authorized, met, offer)
- [ ] **0001193125-16-713780:E0341** L1346-L1349 (date: mid-June 2016; terms: proposal, sent)
- [ ] **0001193125-16-713780:E0345** L1355-L1360 (date: June; actor: Party C; value: $21.00; terms: engaged, meeting, met)
- [ ] **0001193125-16-713780:E0349** L1362-L1364 (date: late July 2016; actor: Party B; value: $19.20 to $24.00; terms: offer, proposed, received)
- [ ] **0001193125-16-713780:E0356** L1368-L1368 (date: July 21, 2016; value: $21.15 per share; terms: submitted)
- [ ] **0001193125-16-713780:E0371** L1384-L1391 (date: July 22, 2016; actor: Party B; terms: contacted, discussed, meeting)
- [ ] **0001193125-16-713780:E0374** L1393-L1399 (date: July 29, 2016; actor: Party D; value: $24.00 per share; terms: declined, offer, proposal)
- [ ] **0001193125-16-713780:E0378** L1401-L1404 (date: August 1, 2016; actor: Party B; terms: met, sent, submitted)
- [ ] **0001193125-16-713780:E0382** L1409-L1411 (date: July 27, 2016; actor: Party B; terms: offer, offered, sent)
- [ ] **0001193125-16-713780:E0386** L1413-L1419 (date: August 4, 2016; actor: Party B; terms: discussed, met, offer)
- [ ] **0001193125-16-713780:E0390** L1421-L1427 (date: August 8, 2016; actor: Party B; value: $25.00 per share; terms: meeting, met, offer)
- [ ] **0001193125-16-713780:E0395** L1429-L1436 (date: August 12, 2016; actor: Party B; terms: meeting, proposal, proposed)
- [ ] **0001193125-16-713780:E0406** L1451-L1460 (date: August 12, 2016; actor: Board; terms: meeting, offer, proposal)
- [ ] **0001193125-16-713780:E0410** L1462-L1464 (date: August 15, 2016; terms: executed)
- [ ] **0001193125-16-713780:E0412** L1466-L1469 (date: September
6, 2016; actor: Board; terms: sent)

### Financial terms to capture
- [ ] **0001193125-16-713780:E0338** L1340-L1344 (date: May 19, 2016; actor: Transaction Committee; value: $17.93 to $26.50; terms: $134, $17.93 to $26.50, $90)
- [ ] **0001193125-16-713780:E0346** L1355-L1360 (date: June; actor: Party C; value: $21.00; terms: $108, $21.00)
- [ ] **0001193125-16-713780:E0350** L1362-L1364 (date: late July 2016; actor: Party B; value: $19.20 to $24.00; terms: $121, $19.20 to $24.00, $96)
- [ ] **0001193125-16-713780:E0354** L1366-L1366 (actor: Party B; value: $24.00 per share; terms: $24.00 per share)
- [ ] **0001193125-16-713780:E0357** L1368-L1368 (date: July 21, 2016; value: $21.15 per share; terms: $20.02, $21.15 per share)
- [ ] **0001193125-16-713780:E0359** L1373-L1373 (actor: Party E; value: $21.26 per share; terms: $21.26 per share)
- [ ] **0001193125-16-713780:E0362** L1375-L1375 (actor: Party D; value: $21.00 per share; terms: $21.00 per share)
- [ ] **0001193125-16-713780:E0364** L1377-L1377 (actor: Party C; value: $19.30 per share; terms: $19.30 per share)
- [ ] **0001193125-16-713780:E0366** L1379-L1379 (actor: Party F; value: $19.20 per share; terms: $19.20 per share)
- [ ] **0001193125-16-713780:E0375** L1393-L1399 (date: July 29, 2016; actor: Party D; value: $24.00 per share; terms: $21.26 per share, $23.81 per share, $24.00 per share)
- [ ] **0001193125-16-713780:E0391** L1421-L1427 (date: August 8, 2016; actor: Party B; value: $25.00 per share; terms: $25.00 per share)
- [ ] **0001193125-16-713780:E0402** L1444-L1449 (actor: Party B; value: $1.00; terms: $1.00)

### Actors to identify
- [ ] **0001193125-16-713780:E0316** L1281-L1291 (date: January 27, 2016; actor: Party A; terms: advisor, investment bank, party )
- [ ] **0001193125-16-713780:E0318** L1293-L1297 (date: March 14, 2016; actor: Party A; terms: party , shareholder)
- [ ] **0001193125-16-713780:E0320** L1302-L1307 (date: April 27, 2016; actor: Board; terms: shareholder, special committee, transaction committee)
- [ ] **0001193125-16-713780:E0322** L1309-L1310 (date: March 22, 2016; actor: Party A; terms: party )
- [ ] **0001193125-16-713780:E0324** L1312-L1318 (date: March 24, 2016; actor: Party A; terms: counsel, party , transaction committee)
- [ ] **0001193125-16-713780:E0329** L1324-L1328 (date: April 7, 2016; actor: Party B; terms: party , transaction committee)
- [ ] **0001193125-16-713780:E0332** L1330-L1332 (date: April 22, 2016; actor: Party A; terms: party , transaction committee)
- [ ] **0001193125-16-713780:E0336** L1337-L1338 (date: May 10, 2016; actor: Board)
- [ ] **0001193125-16-713780:E0339** L1340-L1344 (date: May 19, 2016; actor: Transaction Committee; value: $17.93 to $26.50; terms: transaction committee)
- [ ] **0001193125-16-713780:E0342** L1346-L1349 (date: mid-June 2016; terms: transaction committee)
- [ ] **0001193125-16-713780:E0347** L1355-L1360 (date: June; actor: Party C; value: $21.00; terms: advisor, advisors, party )
- [ ] **0001193125-16-713780:E0351** L1362-L1364 (date: late July 2016; actor: Party B; value: $19.20 to $24.00; terms: bidder , party )
- [ ] **0001193125-16-713780:E0355** L1366-L1366 (actor: Party B; value: $24.00 per share; terms: party )
- [ ] **0001193125-16-713780:E0360** L1373-L1373 (actor: Party E; value: $21.26 per share; terms: party )
- [ ] **0001193125-16-713780:E0363** L1375-L1375 (actor: Party D; value: $21.00 per share; terms: party )
- [ ] **0001193125-16-713780:E0365** L1377-L1377 (actor: Party C; value: $19.30 per share; terms: party )
- [ ] **0001193125-16-713780:E0367** L1379-L1379 (actor: Party F; value: $19.20 per share; terms: party )
- [ ] **0001193125-16-713780:E0369** L1381-L1382 (actor: Transaction Committee; terms: transaction committee)
- [ ] **0001193125-16-713780:E0372** L1384-L1391 (date: July 22, 2016; actor: Party B; terms: party , transaction committee)
- [ ] **0001193125-16-713780:E0376** L1393-L1399 (date: July 29, 2016; actor: Party D; value: $24.00 per share; terms: bidder , party , transaction committee)
- [ ] **0001193125-16-713780:E0379** L1401-L1404 (date: August 1, 2016; actor: Party B; terms: party , transaction committee)
- [ ] **0001193125-16-713780:E0383** L1409-L1411 (date: July 27, 2016; actor: Party B; terms: party , transaction committee)
- [ ] **0001193125-16-713780:E0387** L1413-L1419 (date: August 4, 2016; actor: Party B; terms: counsel, party , transaction committee)
- [ ] **0001193125-16-713780:E0392** L1421-L1427 (date: August 8, 2016; actor: Party B; value: $25.00 per share; terms: party , transaction committee)
- [ ] **0001193125-16-713780:E0396** L1429-L1436 (date: August 12, 2016; actor: Party B; terms: party , transaction committee)
- [ ] **0001193125-16-713780:E0399** L1438-L1439 (actor: Party B; terms: party )
- [ ] **0001193125-16-713780:E0403** L1444-L1449 (actor: Party B; value: $1.00; terms: counsel, party )
- [ ] **0001193125-16-713780:E0407** L1451-L1460 (date: August 12, 2016; actor: Board; terms: advisor, financial advisor, shareholder)
- [ ] **0001193125-16-713780:E0413** L1466-L1469 (date: September
6, 2016; actor: Board; terms: advisor, financial advisor)

### Process signals to check
- [ ] **0001193125-16-713780:E0325** L1312-L1318 (date: March 24, 2016; actor: Party A; terms: confidentiality agreement, standstill)
- [ ] **0001193125-16-713780:E0330** L1324-L1328 (date: April 7, 2016; actor: Party B; terms: confidentiality agreement)
- [ ] **0001193125-16-713780:E0333** L1330-L1332 (date: April 22, 2016; actor: Party A; terms: confidentiality agreement)
- [ ] **0001193125-16-713780:E0340** L1340-L1344 (date: May 19, 2016; actor: Transaction Committee; value: $17.93 to $26.50; terms: due diligence, management presentation)
- [ ] **0001193125-16-713780:E0348** L1355-L1360 (date: June; actor: Party C; value: $21.00; terms: confidentiality agreement, due diligence, management presentation)
- [ ] **0001193125-16-713780:E0352** L1362-L1364 (date: late July 2016; actor: Party B; value: $19.20 to $24.00; terms: draft merger agreement)
- [ ] **0001193125-16-713780:E0361** L1373-L1373 (actor: Party E; value: $21.26 per share; terms: due diligence, exclusivity)
- [ ] **0001193125-16-713780:E0368** L1379-L1379 (actor: Party F; value: $19.20 per share; terms: due diligence)
- [ ] **0001193125-16-713780:E0370** L1381-L1382 (actor: Transaction Committee; terms: due diligence)
- [ ] **0001193125-16-713780:E0373** L1384-L1391 (date: July 22, 2016; actor: Party B; terms: due diligence)
- [ ] **0001193125-16-713780:E0377** L1393-L1399 (date: July 29, 2016; actor: Party D; value: $24.00 per share; terms: due diligence)
- [ ] **0001193125-16-713780:E0380** L1401-L1404 (date: August 1, 2016; actor: Party B; terms: due diligence, marked-up)
- [ ] **0001193125-16-713780:E0384** L1409-L1411 (date: July 27, 2016; actor: Party B; terms: due diligence)
- [ ] **0001193125-16-713780:E0388** L1413-L1419 (date: August 4, 2016; actor: Party B; terms: draft merger agreement, due diligence)
- [ ] **0001193125-16-713780:E0393** L1421-L1427 (date: August 8, 2016; actor: Party B; value: $25.00 per share; terms: due diligence)
- [ ] **0001193125-16-713780:E0397** L1429-L1436 (date: August 12, 2016; actor: Party B; terms: draft merger agreement, superior proposal)
- [ ] **0001193125-16-713780:E0400** L1438-L1439 (actor: Party B; terms: draft merger agreement)
- [ ] **0001193125-16-713780:E0404** L1444-L1449 (actor: Party B; value: $1.00; terms: superior proposal)
- [ ] **0001193125-16-713780:E0408** L1451-L1460 (date: August 12, 2016; actor: Board; terms: superior proposal)

### Outcome facts to verify
- [ ] **0001193125-16-713780:E0326** L1312-L1318 (date: March 24, 2016; actor: Party A; terms: executed)
- [ ] **0001193125-16-713780:E0334** L1330-L1332 (date: April 22, 2016; actor: Party A; terms: executed)
- [ ] **0001193125-16-713780:E0343** L1346-L1349 (date: mid-June 2016; terms: merger agreement)
- [ ] **0001193125-16-713780:E0344** L1351-L1353 (date: June 29, 2016; terms: merger agreement)
- [ ] **0001193125-16-713780:E0353** L1362-L1364 (date: late July 2016; actor: Party B; value: $19.20 to $24.00; terms: merger agreement)
- [ ] **0001193125-16-713780:E0358** L1368-L1368 (date: July 21, 2016; value: $21.15 per share; terms: closing)
- [ ] **0001193125-16-713780:E0381** L1401-L1404 (date: August 1, 2016; actor: Party B; terms: merger agreement)
- [ ] **0001193125-16-713780:E0385** L1409-L1411 (date: July 27, 2016; actor: Party B; terms: merger agreement)
- [ ] **0001193125-16-713780:E0389** L1413-L1419 (date: August 4, 2016; actor: Party B; terms: merger agreement)
- [ ] **0001193125-16-713780:E0394** L1421-L1427 (date: August 8, 2016; actor: Party B; value: $25.00 per share; terms: merger agreement)
- [ ] **0001193125-16-713780:E0398** L1429-L1436 (date: August 12, 2016; actor: Party B; terms: merger agreement, terminated, termination fee)
- [ ] **0001193125-16-713780:E0401** L1438-L1439 (actor: Party B; terms: merger agreement)
- [ ] **0001193125-16-713780:E0405** L1444-L1449 (actor: Party B; value: $1.00; terms: closing, merger agreement, termination fee)
- [ ] **0001193125-16-713780:E0409** L1451-L1460 (date: August 12, 2016; actor: Board; terms: merger agreement)
- [ ] **0001193125-16-713780:E0411** L1462-L1464 (date: August 15, 2016; terms: executed, merger agreement)
- [ ] **0001193125-16-713780:E0414** L1466-L1469 (date: September
6, 2016; actor: Board; terms: merger agreement)
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