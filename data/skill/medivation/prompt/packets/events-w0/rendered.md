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
window_id: w0
</deal_context>

<chronology_blocks>
B001 [L640-L640]: (i)      Background of Offer and Merger
B002 [L642-L645]: The Medivation board of directors frequently reviews, with Medivations management, and with the assistance of its outside financial and legal advisors, Medivations strategic and financial alternatives in light of developments in Medivations business, in the sectors in which it competes, in the economy generally and in financial markets. The alternatives reviewed have included large and small acquisitions, mergers and a sale of Medivation, and, from time to time, Medivation has received inquiries from third parties seeking to determine Medivations interest in a sale transaction.
B003 [L647-L648]: On March 22, 2016, Olivier Brandicourt, Chief Executive Officer of Sanofi, contacted David Hung, M. D., President and Chief Executive Officer of Medivation, on an unsolicited basis, and requested a telephone discussion.
B004 [L650-L654]: On March 24, 2016, the Medivation board of directors held a special meeting attended by management of Medivation and representatives of Cooley LLP ( Cooley), Medivations legal advisor, and J. P. Morgan Securities LLC ( J. P. Morgan), retained as independent financial advisor to Medivation in connection with routine advanced preparedness for defense and general strategic advice and based on J. P. Morgans long history with the Company and expertise in Medivations general industry (see Item 5.  Person/Assets Retained, Employed Compensated or Usedbelow). At this meeting, the Medivation board of directors discussed Dr. Brandicourts request for a call and meeting. At the conclusion of the meeting, the Medivation board of directors directed Dr. Hung to proceed with an initial call and report any relevant discussion.
B005 [L656-L658]: On March 25, 2016, Drs. Brandicourt and Hung had an initial telephone discussion during which Dr. Brandicourt expressed interest in pursuing a possible strategic transaction. Dr. Brandicourt did not indicate a potential price or range of prices for any such transaction. Dr. Hung told Dr. Brandicourt that he would report Sanofis interest to the Medivation board of directors.
B006 [L660-L662]: In late March 2016, media publications reported rumors of Sanofis potential acquisition interest in Medivation and that Medivation had hired financial advisors in connection with the defense of a possible strategic transaction. Following those media reports, three industry participants contacted J. P. Morgan to indicate an interest in participating in any strategic discussions Medivation might initiate and a fourth industry participant contacted Dr. Hung to express interest in the same.
B007 [L664-L668]: On April 1, 2016, the Medivation board of directors held a special meeting attended by management of Medivation and representatives of J. P. Morgan and Cooley to discuss the preliminary interest conveyed by Dr. Brandicourt, as well as the communications received from the four other parties. The Medivation board of directors evaluated, with input from its financial and legal advisors, Sanofis expression of interest, as well as the communications received from the four other parties. The Medivation board of directors determined that, given the speculative nature of the expressions of interest, the then-current market price of Medivations Common Stock (as well as the relative position of the equity markets generally) and the potential value in Medivations well-defined strategic plan, it was not the appropriate time for Medivation to engage in discussions relating to a strategic transaction with Sanofi or any other party.
B008 [L670-L672]: On April 3, 2016, Dr. Hung informed Dr. Brandicourt that the Medivation board of directors, following a review and discussion of Dr. Brandicourts expression of interest, had determined that it was not an appropriate time for Medivation to engage in discussions relating to a possible strategic transaction.
B009 [L674-L676]: On April 15, 2016, Dr. Hung received an unsolicited letter, dated April 13, 2016, from Dr. Brandicourt, setting forth a non-binding proposal from Sanofi to acquire Medivation for $52.50 per share of Medivations Common Stock, subject to the completion of due diligence, the negotiation and execution of definitive agreements, and the approval of Sanofis board of directors ( Sanofis $52.50 proposal).
B010 [L678-L678]: 16
B011 [L681-L683]: Later that day, the Medivation board of directors convened a special meeting to discuss, with management of Medivation and representatives of J. P. Morgan and Cooley, Sanofis $52.50 proposal. The Medivation board of directors determined that additional review, discussion and analysis were required prior to any formal response to Sanofi.
B012 [L685-L686]: On April 20, 2016, Douglas Giordano, Senior Vice President, Worldwide Business Development at Pfizer contacted Dr. Hung to indicate an interest in participating in any strategic discussions Medivation might initiate.
B013 [L688-L692]: On April 22, 2016, the Medivation board of directors held a regular meeting at which, among other topics, the Medivation board of directors continued to discuss and evaluate Sanofis $52.50 proposal with its legal advisors and determined to engage Evercore Group L. L. C. ( Evercore) as an additional independent financial advisor to Medivation, based on Evercores historical work with key constituents in Medivations industry and Evercores reputation as a financial advisor to companies in unsolicited strategic transaction scenarios. At this meeting, the Medivation board of directors also scheduled special meetings of the Medivation board of directors to be held on April 27, 2016 and April 28, 2016 to further review and analyze Sanofis $52.50 proposal.
B014 [L694-L695]: At a special meeting of the Medivation board of directors on April 27, 2016, the Medivation board of directors continued its review of Sanofis $52.50 proposal with input from management of Medivation and representatives of J. P. Morgan and Cooley.
B015 [L697-L697]: On April 28, 2016, Sanofi issued a press release publicly announcing Sanofis $52.50 proposal.
B016 [L699-L702]: Later that morning, the Medivation board of directors held its previously scheduled special meeting at which it continued its review of Sanofis $52.50 proposal with input from management of Medivation and representatives of Evercore, J. P. Morgan, Cooley and Wachtell, Lipton, Rosen & Katz ( Wachtell Lipton), which Medivation had retained as an additional legal advisor. Following those discussions, the Medivation board of directors unanimously rejected Sanofis $52.50 proposal, concluding that Sanofis $52.50 proposal substantially undervalued Medivation, and was not in the best interests of Medivation and its stockholders.
B017 [L704-L708]: On April 29, 2016, Medivation issued a press release announcing the Medivation board of directors determination. Later that same day, the Medivation board of directors held a special meeting attended by management of Medivation and representatives of Cooley, Wachtell Lipton and Richards, Layton & Finger, P. A., Medivations Delaware counsel, at which it approved amendments to the Medivation Bylaws in order to (i) put in place certain procedural requirements in connection with any stockholder action by written consent (including the appointment by Medivation of independent inspectors of election in the event of any stockholder consent solicitation) and (ii) select the Court of Chancery of the State of Delaware as the sole and exclusive forum for certain actions or proceedings brought on behalf of, or against, Medivation.
B018 [L710-L711]: On May 2, 2016, Mr. Giordano and Dr. Hung spoke by phone and Mr. Giordano expressed Pfizers continued interest in participating in any strategic discussions Medivation might initiate.
B019 [L713-L715]: Early on the morning of May 5, 2016, Sanofi issued a press release restating the terms of Sanofis $52.50 proposal and threatening to commence a stockholder consent solicitation to remove and replace the Medivation board of directors if Medivation did not engage in discussions with Sanofi. Later that morning, Medivation issued a press release reiterating its rejection of Sanofis substantially inadequate proposal.
B020 [L717-L718]: On May 5, 2016, Medivation hosted a live teleconference in which members of Medivations senior management team discussed Medivations first quarter 2016 results and presented an overview of Medivations business performance and future prospects.
B021 [L720-L722]: From May 9, 2016 through May 17, 2016, Sanofi and Weil Gotshal & Manges LLP ( Weil Gotshal), Sanofis legal counsel, contacted Medivation and its legal counsel, respectively, to express Sanofis interest in signing a confidentiality agreement and receiving due diligence materials on Medivation. Weil Gotshal on behalf of Sanofi stated that Sanofi could pay more (but did not indicate how much more), but that Sanofi would need to
B022 [L724-L724]: 17
B023 [L727-L730]: receive confidential information before doing so. Representatives of Wachtell Lipton and Cooley informed representatives of Weil Gotshal that this was a matter for the Medivation board of directors to decide but that the Medivation board of directors had already determined that the price offered by Sanofi was substantially inadequate and that Sanofis $52.50 proposal was not a reasonable basis to begin a negotiation. Representatives of Wachtell Lipton and Cooley also noted that Sanofi was free to send a confidentiality agreement to Medivation to show the terms to which it would be willing to agree in order to obtain access to certain confidential information of Medivation.
B024 [L732-L733]: On May 12, 2016, Sanofi announced that it had filed for premerger notification under the HSR Act with the U. S. Department of Justice Antitrust Division (the  Antitrust Division) and the Federal Trade Commission (the  FTC).
B025 [L735-L735]: On
B026 [L736-L738]: May 13, 2016, at a meeting of the board of directors of Medivation, Dr. Hung and representatives of Evercore and J. P. Morgan updated the board with respect to matters involving Sanofis $52.50 proposal. Representatives of Cooley and Wachtell Lipton also reviewed certain legal matters with respect to the anticipated consent solicitation process. The Medivation board of directors asked questions and discussed matters related to Sanofis $52.50 proposal and the anticipated consent solicitation process, with input from its financial and legal advisors.
B027 [L740-L741]: On May 17, 2016, Dr. Brandicourt sent Dr. Hung a letter expressing Sanofis desire to sign a confidentiality agreement and engage in discussions with respect to a strategic transaction. In response, Dr. Hung sent the following letter to Dr. Brandicourt:
B028 [L743-L743]: May 17, 2016
B029 [L745-L745]: Olivier Brandicourt
B030 [L747-L747]: Chief Executive Officer
B031 [L749-L749]: 54, rue La Boetie
B032 [L751-L751]: 75008 Paris, France
B033 [L753-L753]: Dear Olivier:
B034 [L755-L758]: Over the past week, representatives and advisors of Sanofi have made a number of phone calls to our advisors, all conveying a similar messagethat Sanofi may consider an increase to its proposed price but first must review Medivations proprietary information. While we appreciate the measured tone of your most recent letter dated May 17, Sanofis proposal remains unchanged. What matters for Medivation and its Board is value for our shareholders. As we have previously said, Sanofis proposal of $52.50 per share in cash for Medivation substantially undervalues our company and is not an appropriate basis upon which to consider evaluation of a potential strategic combination.
B035 [L760-L763]: We are extremely comfortable that our Boards position is well understood by and reflects the overwhelming sentiment of our shareholders. Our Board reached its view about Sanofis proposal based on a thorough analysis of our companys marketed products commercial momentum and outlook, our pipelines excellent prospects and our companys track record of successful drug development and delivering outstanding value to our shareholders. We are confident that what we continue to build will be highly beneficial to patients and, we believe, extraordinarily valuable to our shareholders.
B036 [L765-L766]: Our Board is committed to act so that our shareholders realize the value we have created and are continuing to create. The value which Sanofi proposes is not close to a reasonable starting point for providing information or commencing discussions.
B037 [L768-L768]: Very truly yours,
B038 [L770-L770]: /s/ David Hung, M. D.
B039 [L772-L772]: David Hung, M. D.
B040 [L774-L774]: 18
B041 [L777-L778]: On May 20, 2016, Mr. Giordano contacted Dr. Hung by telephone. During that conversation, Mr. Giordano reiterated Pfizers interest in participating in any potential negotiated transaction process that Medivation might initiate and highlighted the strategic fit of Pfizer and Medivation.
B042 [L780-L782]: On May 25, 2016, Sanofi filed with the SEC a preliminary consent solicitation statement (as amended, the  Consent Solicitation), seeking the consent of Medivation stockholder to four proposals, including (1) the removal of each of the eight existing directors of the Medivation board and (2) the replacement of those directors with eight nominees selected by Sanofi (the  Sanofi Proposals).
B043 [L784-L785]: On May 27, 2016, Medivation filed with the SEC a preliminary consent revocation statement (the  Consent Revocation), urging the Medivation stockholders to revoke consent to the Sanofi Proposals for the reasons set forth at length in the Consent Revocation.
B044 [L787-L796]: On June 21 and 22, 2016, the Medivation board of directors met with Medivations senior management team, and Medivations outside financial advisors and legal advisors to review and discuss, among other matters, the ongoing Consent Solicitation. The board considered the possibility that Sanofi would revise and make public an increased proposal offer, but that the offer would remain unattractive in terms of value. The Medivation board considered that an unattractive offer made at such time could result in market pressure to engage in a change of control transaction in which the Medivation stockholders would not receive appropriate value for their shares. In light of the foregoing, the Medivation board was of the view that it should seek to control any process to explore the value that might be obtained in a transaction with a third party. Accordingly, the Medivation board directed J. P. Morgan and Evercore to contact select industry participants, to determine respective levels of preliminary interest in a strategic process, with the objective of expeditiously entering into confidentiality agreements. These industry participants would include the four companies that had contacted J. P. Morgan and Dr. Hung in late March 2016, Pfizer, which had first contacted Dr. Hung on April 20, 2016, as well as a number of other parties selected by the Medivation board of directors based on perceived interest and ability to review and consummate a transaction. Cooley summarized for the board the principal terms of the contemplated form of confidentiality agreement, which included a customary standstill provision with a fall-away upon an alternative transaction. The Medivation board of directors determined that following execution of satisfactory confidentiality agreements with one or more other parties, Medivation would privately offer Sanofi the opportunity to enter into the process and receive confidential information, provided that Sanofi entered into a confidentiality and standstill agreement on substantially the same terms as the other interested parties, and terminate the Consent Solicitation.
B045 [L798-L800]: From late June 2016 through early July 2016, J. P. Morgan and Evercore contacted eleven industry participants, which included Pfizer and the four companies that had initially indicated interest in late March 2016. Medivation also contacted a twelfth industry participant to explore preliminary interest in a potential strategic transaction.
B046 [L802-L803]: On June 27, 2016, Medivation received a private letter with an increased proposal from Sanofi of $58.00 per share in cash plus a contingent value right ( CVR) of up to $3.00 per share, conditioned on certain revenue metrics.
B047 [L805-L806]: On June 29, 2016, Medivation entered into confidentiality agreements with Pfizer and one additional party initially contacted by Medivations financial advisors.
B048 [L808-L811]: On June 30, 2016, the Medivation board of directors met telephonically to discuss Sanofis revised unsolicited proposal, together with members of Medivations senior management, and the Companys legal and financial advisors. Cooley provided an update for the board on current contacts with third parties and the executed confidentiality agreements. Medivations financial advisors provided their respective preliminary valuation overviews and analyses for Medivation. Following these presentations and further discussion, the Medivation board of directors unanimously rejected Sanofis unsolicited revised proposal as not in the best interests of Medivation and its stockholders and directed the management team and advisors to communicate the
B049 [L813-L813]: 19
B050 [L816-L817]: determination to Sanofi while at the same time offering Sanofi the opportunity to enter into a confidentiality and standstill agreement with Medivation on substantially the same terms being offered to (and entered into) by other interested parties.
B051 [L819-L823]: On July 5, 2016, Medivation entered into a confidentiality agreement with Sanofi, pursuant to which Sanofi agreed to terminate its Consent Solicitation and be bound by a six-month standstill, subject to limited termination events, in order to facilitate friendly confidential discussions and a due diligence investigation. Later that day, Medivation announced in a press release that, among other things: (1) Medivation had entered into confidentiality agreements with Sanofi and a number of other parties, and (2) prior to entering into the confidentiality agreement with Sanofi, Medivation had received the revised unsolicited proposal from Sanofi for $58.00 per share and a CVR of up to $3.00 per share and the board of directors of Medivation had unanimously rejected it as not in the best interests of Medivation and its stockholders.
B052 [L825-L827]: On July 7, 2016, Medivation granted Pfizer, and the other interested parties that had executed confidentiality agreements with Medivation, access to an electronic data room containing certain information regarding Medivations business and operations. Throughout the diligence process, Medivation engaged in diligence calls and responded to written diligence requests from each of the parties that entered into confidentiality agreements with Medivation.
B053 [L829-L831]: Also on July 7, 2016, Dr. Hung met with Ian Read, Chief Executive Officer of Pfizer, Dr. Mace Rothenberg, Chief Development Officer, Oncology at Pfizer and Dr. Mikael Dolsten, President of Worldwide Research and Development at Pfizer. During this meeting, the Pfizer management team expressed Pfizers continued interest in exploring a potential negotiated strategic transaction with Medivation.
B054 [L833-L833]: On
B055 [L834-L834]: July 9, 2016, Medivation entered into a confidentiality agreement with a fourth industry participant initially contacted by Medivations financial advisors.
B056 [L836-L837]: On July 13, Medivation entered into a confidentiality agreement with a fifth industry participant initially contacted by Medivations financial advisors.
B057 [L839-L841]: For reference, other than Pfizer, the industry participants with which Medivation entered into confidentiality agreements as described above are hereinafter referred to as  Company 1,  Company 2,  Company 3, and  Company 4. Together, Pfizer, Company 1, Company 2, Company 3 and Company 4 are referred to as the  Interested Parties.
B058 [L843-L844]: On July 14, 2016, Medivation held a management presentation at Cooleys offices in San Francisco with Pfizer. That night, Dr. Hung and other members of Medivations management team had dinner with members of Pfizers management team.
B059 [L846-L847]: Over the course of July 15, 2016 through July 21, 2016, Medivation held a series of in-person full-day management presentations with core business teams from each of the other Interested Parties.
B060 [L849-L852]: On July 19 and 20, 2016, representatives of J. P. Morgan and Evercore sent a letter to each of the Interested Parties with guidelines for the Interested Party to submit a written, non-binding preliminary proposal for the potential acquisition of Medivation. The letter requested submission of the preliminary proposal by 5:00 p. m. Pacific Time on August 8, 2016 and stated that if Medivation decided to continue exploring potential interest in a transaction, a limited number of qualified parties might be invited to enter into further discussions and be provided additional due diligence materials.
B061 [L854-L855]: In the five week period between Medivations initial opening of the electronic data room on July 7, 2016 and the deadline for preliminary proposals on August 8, 2016, Medivation held a series of calls regarding due diligence and the potential strategic transaction process with each Interested Party at its request.
B062 [L857-L857]: 20
B063 [L860-L861]: Also in that five week period, the Medivation board of directors met five times telephonically. During each of those meetings, the Medivation board of directors discussed the course of due diligence and the potential strategic transaction process with Medivations management team and advisors.
B064 [L863-L866]: On August 8, 2016, each of the Interested Parties submitted non-binding written preliminary proposals for the acquisition of Medivation. Pfizer submitted a preliminary proposal for the all-cash acquisition of Medivation for $65.00 per Share. Company 1 submitted a preliminary proposal for the all-cash acquisition of Medivation for $71.00 per Share. Company 2 submitted a preliminary proposal for the all-cash acquisition of Medivation for $62.00$64.00 per Share. Company 3 submitted a preliminary proposal to acquire Medivation for $60.00 per Share in cash, plus CVRs of up to $10.00 per Share, conditioned on certain revenue metrics. Company 4 submitted a preliminary proposal to acquire Medivation for $63.00 per Share in cash, plus CVRs of up to $5.00 per Share conditioned on certain regulatory milestones for pipeline assets.
B065 [L868-L874]: On August 10, 2016, the Medivation board of directors met telephonically with Medivations senior management and legal and financial advisors to discuss the preliminary proposals. After a presentation from the financial advisors, including a review of the Companys stock price and a comparison of the non-binding proposals, the Medivation board of directors discussed strategies for next steps and a proposed timeline for the transaction process. Following that discussion, the Medivation board of directors authorized Medivations financial advisors to advance Pfizer, Company 1, and Company 4 into a second and confirmatory round of due diligence and the continuation of the strategic transaction process, including negotiation of a proposed acquisition agreement. The Medivation board of directors also authorized Medivations financial advisors to inform Company 2 and Company 3 that their preliminary proposals were not competitive with those of the other Interested Parties and that they would not be invited to continue in the strategic transaction process. Following the meeting, at the direction of Medivations board of directors, Medivations financial advisors notified each of Pfizer, Company 1 and Company 4 that such Interested Party, together with several other Interested Parties, was being invited to a subsequent round of the potential strategic transaction process.
B066 [L876-L880]: On August 11, 2016, at the direction of Medivations board of directors, Medivations financial advisors distributed a draft merger agreement to Pfizer, Company 1, and Company 4. Later that day, Medivations financial advisors communicated to Company 2 and Company 3 that their preliminary proposals had not been competitive from a valuation perspective and that Company 2 and Company 3 would not advance in the transaction process at their then-current valuation. At that time, Company 2 communicated by telephone to Medivations financial advisors that Company 2 would submit a revised initial bid proposal for an all-cash acquisition of Medivation at $70.00 per Share. Medivations financial advisors responded that Company 2 would not be advanced in the process in the absence of a competitive revised proposal in writing.
B067 [L882-L883]: On August 12, 2016, Company 2 and Company 3 submitted written revised proposals for an all-cash acquisition of Medivation, at $70.00 per Share and $70.50 per Share, respectively. Later that day, Medivations financial advisors provided Company 2 and Company 3 with the draft merger agreement and access to the second stage of confirmatory diligence.
B068 [L885-L886]: On August 14, 2016, J. P. Morgan and Evercore sent a written instruction letter to each Interested Party, requiring a definitive written proposal by 12:00 p. m. Pacific Time on Friday, August 19, 2016. The instructions also requested that each Interested Party submit any comments on the draft of the merger agreement by 5:00 p. m. Pacific Time on Thursday, August 18, 2016.
B069 [L888-L889]: On August 18, 2016, each Interested Party submitted a revised draft of the merger agreement to Medivation representatives. That evening, Medivations legal advisors met telephonically with members of Medivations management team to review the marked agreements and to discuss response strategy.
B070 [L891-L892]: On Friday, August 19, 2016, each of Pfizer, Company 1, Company 2, and Company 3 submitted a definitive proposal for an all-cash acquisition of Medivation. Company 4 declined to submit a definitive proposal and
B071 [L894-L894]: 21
B072 [L897-L898]: ceased participation in the strategic transaction process. The definitive proposals, in order of increasing valuation, were from Company 3 for $72.50 per Share in cash, Company 1 for $73.00 per Share in cash, Company 2 for $75.50 per Share in cash, and Pfizer for $77.00 per Share in cash. Together with their definitive proposals, each of Company 1 and Company 3 also submitted a revised version of the merger agreement.
B073 [L900-L909]: That afternoon, the Medivation board of directors met telephonically with Medivations senior management and legal and financial advisors to discuss the definitive proposals and marked agreements received from Pfizer, Company 1, Company 2 and Company 3. Medivations management team provided an overview of the conversations and meetings with the Interested Parties over the course of the diligence process. The financial advisors presented to the board of directors a review of the bidding process and positions of the Interested Parties over the course of the bidding process. Cooley and Wachtell Lipton summarized and compared the revised drafts of the merger agreements provided by the relevant Interested Parties, including a thorough discussion of the material adverse effect provision and other conditions to closing the proposed transaction. After further discussions, including as to the matters discussed in the section entitled  Reasons for the Merger; Recommendation of the Medivation Board of Directors, the Medivation board of directors authorized Medivations financial advisors to communicate to the remaining Interested Parties that best and final proposals (to include confirmation that no further diligence would be required) would be due on August 20, 2016, by 12:00 p. m. Pacific Time. The Medivation board of directors authorized Medivations financial advisors to inform the Interested Parties that the Medivation board of directors intended to review the proposals promptly after the deadline at a meeting scheduled for the afternoon of Saturday, August 20, 2016, with the intention of identifying a successful bidder and executing a merger agreement promptly following the completion of that meeting. The Medivation board of directors authorized Medivations financial advisors to inform each Interested Party that such Interested Party should assume that it would not receive a call or other notification on August 20, 2016, if its proposal was not the highest, and, accordingly, each Interested Party was urged to put forward its best proposal at that time. Following the meeting, Medivations financial advisors delivered that message to each of Pfizer, Company 1, Company 2 and Company 3.
B074 [L911-L912]: During the evening of Friday, August 19, 2016 and early morning of Saturday, August 20, 2016, Wachtell Lipton and Cooley sent revised drafts of the merger agreement to each of Pfizer, Company 1, Company 2 and Company 3. In the evening of August 19, 2016, Company 3 notified Medivations financial advisors that Company 3 would not be submitting a revised proposal.
B075 [L914-L918]: On the morning of Saturday, August 20, 2016, at the request of legal advisors of Pfizer and Company 2, Wachtell Lipton and Cooley met telephonically with those legal advisors to answer questions concerning the form of merger agreement provided by Medivations legal advisors the previous evening. In each of these separate discussions, the representatives of Pfizer and the representatives of Company 2 indicated that Pfizer and Company 2, respectively, were prepared to accept and enter into a merger agreement substantially in the form proposed by Medivation the previous evening. During these conversations, Medivations legal advisors also repeated the instructions previously given to the Interested Parties to the effect that the Interested Party should expect that Medivation would enter into a merger agreement with the party submitting the best proposal at the noon deadline, and the Interested Party should not assume it would have any further opportunity to improve or increase its proposal should its proposal not be the highest and best.
</chronology_blocks>

<overlap_context>
B076 [L920-L922]: Later that morning, on August 20, 2016, beginning at 11:51 a. m. Pacific Time, each of Pfizer, Company 1, and Company 2 submitted a final proposal, each of which had been approved by the board of directors of the respective bidding party and each of which included confirmation that it was not subject to further diligence, and a revised draft of the merger agreement. Pfizer submitted a revised final proposal to acquire Medivation for $81.50 per share. Company 1 submitted a revised final proposal to acquire Medivation for $80.25 per share. Company 2 submitted a revised final proposal to acquire Medivation for $80.00 per share.
B077 [L924-L925]: Immediately thereafter, at 12:15 p. m. Pacific Time on August 20, 2016, the Medivation board of directors met telephonically with representatives of Medivations senior management and the Companys legal and
</overlap_context>

<evidence_checklist>
### Dated actions to extract
- [ ] **0001193125-16-696911:E0097** L647-L648 (date: March 22, 2016; terms: contacted, requested)
- [ ] **0001193125-16-696911:E0098** L650-L654 (date: March 24, 2016; actor: P. Morgan; terms: discussed, meeting, retained)
- [ ] **0001193125-16-696911:E0100** L660-L662 (date: late March 2016; actor: P. Morgan; terms: contacted)
- [ ] **0001193125-16-696911:E0102** L664-L668 (date: April 1, 2016; actor: P.
Morgan; terms: meeting, received, sent)
- [ ] **0001193125-16-696911:E0104** L674-L676 (date: April 15, 2016; value: $52.50 per share; terms: proposal, received)
- [ ] **0001193125-16-696911:E0109** L685-L686 (date: April 20, 2016; terms: contacted)
- [ ] **0001193125-16-696911:E0110** L688-L692 (date: April 22, 2016; value: $52.50; terms: meeting, proposal)
- [ ] **0001193125-16-696911:E0113** L694-L695 (date: April 27, 2016; actor: P. Morgan; value: $52.50; terms: meeting, proposal, sent)
- [ ] **0001193125-16-696911:E0116** L697-L697 (date: April 28, 2016; value: $52.50; terms: proposal)
- [ ] **0001193125-16-696911:E0120** L704-L708 (date: April 29, 2016; terms: meeting, sent)
- [ ] **0001193125-16-696911:E0122** L713-L715 (date: May 5, 2016; value: $52.50; terms: proposal, sent)
- [ ] **0001193125-16-696911:E0125** L717-L718 (date: May 5, 2016; terms: discussed, sent)
- [ ] **0001193125-16-696911:E0126** L720-L722 (date: May 9, 2016; terms: contacted)
- [ ] **0001193125-16-696911:E0131** L732-L733 (date: May 12, 2016; terms: announced)
- [ ] **0001193125-16-696911:E0132** L735-L738 (date: May 13, 2016; actor: P. Morgan; value: $52.50; terms: discussed, meeting, proposal)
- [ ] **0001193125-16-696911:E0135** L740-L741 (date: May 17, 2016; terms: sent)
- [ ] **0001193125-16-696911:E0137** L755-L758 (date: may; actor: Board; value: $52.50 per share; terms: proposal, proposed, sent)
- [ ] **0001193125-16-696911:E0142** L777-L778 (date: May 20, 2016; terms: contacted)
- [ ] **0001193125-16-696911:E0143** L780-L782 (date: May 25, 2016; terms: proposal, sent)
- [ ] **0001193125-16-696911:E0145** L784-L785 (date: May 27, 2016; terms: proposal, sent)
- [ ] **0001193125-16-696911:E0147** L787-L796 (date: June; actor: P. Morgan; terms: contacted, entered into, met)
- [ ] **0001193125-16-696911:E0150** L798-L800 (date: late June 2016; actor: P. Morgan; terms: contacted)
- [ ] **0001193125-16-696911:E0152** L802-L803 (date: June 27, 2016; value: $58.00 per share; terms: met, proposal, received)
- [ ] **0001193125-16-696911:E0154** L805-L806 (date: June 29, 2016; terms: contacted, entered into)
- [ ] **0001193125-16-696911:E0157** L808-L811 (date: June 30, 2016; terms: executed, met, proposal)
- [ ] **0001193125-16-696911:E0162** L819-L823 (date: July 5, 2016; value: $58.00 per share; terms: announced, entered into, proposal)
- [ ] **0001193125-16-696911:E0166** L825-L827 (date: July 7, 2016; terms: engaged, entered into, executed)
- [ ] **0001193125-16-696911:E0169** L829-L831 (date: July 7, 2016; terms: meeting, met)
- [ ] **0001193125-16-696911:E0170** L833-L834 (date: July 9, 2016; terms: contacted, entered into)
- [ ] **0001193125-16-696911:E0173** L836-L837 (date: July; terms: contacted, entered into)
- [ ] **0001193125-16-696911:E0177** L843-L844 (date: July 14, 2016; terms: sent)
- [ ] **0001193125-16-696911:E0179** L846-L847 (date: July 15, 2016; terms: sent)
- [ ] **0001193125-16-696911:E0181** L849-L852 (date: July; actor: P. Morgan; terms: proposal, requested, sent)
- [ ] **0001193125-16-696911:E0184** L854-L855 (date: July
7, 2016; terms: proposal)
- [ ] **0001193125-16-696911:E0189** L863-L866 (date: August 8, 2016; value: $65.00 per Share; terms: met, proposal, submitted)
- [ ] **0001193125-16-696911:E0191** L868-L874 (date: August 10, 2016; terms: authorized, discussed, meeting)
- [ ] **0001193125-16-696911:E0194** L876-L880 (date: August 11, 2016; value: $70.00 per Share; terms: proposal)
- [ ] **0001193125-16-696911:E0199** L882-L883 (date: August 12, 2016; value: $70.00 per Share; terms: proposal, submitted)
- [ ] **0001193125-16-696911:E0204** L885-L886 (date: August 14, 2016; actor: P. Morgan; terms: proposal, requested, sent)
- [ ] **0001193125-16-696911:E0208** L888-L889 (date: August 18, 2016; terms: met, sent, submitted)
- [ ] **0001193125-16-696911:E0211** L891-L892 (date: August 19, 2016; terms: declined, proposal, submitted)
- [ ] **0001193125-16-696911:E0214** L900-L909 (date: August 20, 2016; actor: Board; terms: authorized, delivered, discussed)
- [ ] **0001193125-16-696911:E0218** L911-L912 (date: August 19, 2016; terms: proposal, sent)
- [ ] **0001193125-16-696911:E0221** L914-L918 (date: August 20, 2016; terms: met, proposal, proposed)
- [ ] **0001193125-16-696911:E0224** L920-L922 (date: August 20, 2016; value: $81.50 per share; terms: proposal, submitted)
- [ ] **0001193125-16-696911:E0228** L924-L925 (date: August 20, 2016; terms: met, sent)

### Financial terms to capture
- [ ] **0001193125-16-696911:E0105** L674-L676 (date: April 15, 2016; value: $52.50 per share; terms: $52.50, $52.50 per share)
- [ ] **0001193125-16-696911:E0107** L681-L683 (actor: P. Morgan; value: $52.50; terms: $52.50)
- [ ] **0001193125-16-696911:E0111** L688-L692 (date: April 22, 2016; value: $52.50; terms: $52.50)
- [ ] **0001193125-16-696911:E0114** L694-L695 (date: April 27, 2016; actor: P. Morgan; value: $52.50; terms: $52.50)
- [ ] **0001193125-16-696911:E0117** L697-L697 (date: April 28, 2016; value: $52.50; terms: $52.50)
- [ ] **0001193125-16-696911:E0118** L699-L702 (actor: P. Morgan; value: $52.50; terms: $52.50)
- [ ] **0001193125-16-696911:E0123** L713-L715 (date: May 5, 2016; value: $52.50; terms: $52.50)
- [ ] **0001193125-16-696911:E0129** L727-L730 (value: $52.50; terms: $52.50)
- [ ] **0001193125-16-696911:E0133** L735-L738 (date: May 13, 2016; actor: P. Morgan; value: $52.50; terms: $52.50)
- [ ] **0001193125-16-696911:E0138** L755-L758 (date: may; actor: Board; value: $52.50 per share; terms: $52.50 per share)
- [ ] **0001193125-16-696911:E0153** L802-L803 (date: June 27, 2016; value: $58.00 per share; terms: $3.00 per share, $58.00 per share)
- [ ] **0001193125-16-696911:E0163** L819-L823 (date: July 5, 2016; value: $58.00 per share; terms: $3.00 per share, $58.00 per share)
- [ ] **0001193125-16-696911:E0190** L863-L866 (date: August 8, 2016; value: $65.00 per Share; terms: $10.00 per Share, $5.00 per Share, $60.00 per Share)
- [ ] **0001193125-16-696911:E0195** L876-L880 (date: August 11, 2016; value: $70.00 per Share; terms: $70.00 per Share)
- [ ] **0001193125-16-696911:E0200** L882-L883 (date: August 12, 2016; value: $70.00 per Share; terms: $70.00 per Share, $70.50 per Share)
- [ ] **0001193125-16-696911:E0212** L897-L898 (value: $72.50 per Share; terms: $72.50 per Share, $73.00 per
Share, $75.50 per Share)
- [ ] **0001193125-16-696911:E0225** L920-L922 (date: August 20, 2016; value: $81.50 per share; terms: $80.00 per share, $80.25 per share, $81.50 per share)

### Actors to identify
- [ ] **0001193125-16-696911:E0096** L642-L645 (terms: advisor, advisors, legal advisor)
- [ ] **0001193125-16-696911:E0099** L650-L654 (date: March 24, 2016; actor: P. Morgan; terms: advisor, financial advisor, legal advisor)
- [ ] **0001193125-16-696911:E0101** L660-L662 (date: late March 2016; actor: P. Morgan; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0103** L664-L668 (date: April 1, 2016; actor: P.
Morgan; terms: advisor, advisors, legal advisor)
- [ ] **0001193125-16-696911:E0108** L681-L683 (actor: P. Morgan; value: $52.50)
- [ ] **0001193125-16-696911:E0112** L688-L692 (date: April 22, 2016; value: $52.50; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0115** L694-L695 (date: April 27, 2016; actor: P. Morgan; value: $52.50)
- [ ] **0001193125-16-696911:E0119** L699-L702 (actor: P. Morgan; value: $52.50; terms: advisor, legal advisor, stockholder)
- [ ] **0001193125-16-696911:E0121** L704-L708 (date: April 29, 2016; terms: counsel, stockholder)
- [ ] **0001193125-16-696911:E0124** L713-L715 (date: May 5, 2016; value: $52.50; terms: stockholder)
- [ ] **0001193125-16-696911:E0127** L720-L722 (date: May 9, 2016; terms: counsel)
- [ ] **0001193125-16-696911:E0134** L735-L738 (date: May 13, 2016; actor: P. Morgan; value: $52.50; terms: advisor, advisors, legal advisor)
- [ ] **0001193125-16-696911:E0139** L755-L758 (date: may; actor: Board; value: $52.50 per share; terms: advisor, advisors, shareholder)
- [ ] **0001193125-16-696911:E0140** L760-L763 (actor: Board; terms: shareholder)
- [ ] **0001193125-16-696911:E0141** L765-L766 (actor: Board; terms: shareholder)
- [ ] **0001193125-16-696911:E0144** L780-L782 (date: May 25, 2016; terms: stockholder)
- [ ] **0001193125-16-696911:E0146** L784-L785 (date: May 27, 2016; terms: stockholder)
- [ ] **0001193125-16-696911:E0148** L787-L796 (date: June; actor: P. Morgan; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0151** L798-L800 (date: late June 2016; actor: P. Morgan)
- [ ] **0001193125-16-696911:E0155** L805-L806 (date: June 29, 2016; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0158** L808-L811 (date: June 30, 2016; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0164** L819-L823 (date: July 5, 2016; value: $58.00 per share; terms: stockholder)
- [ ] **0001193125-16-696911:E0171** L833-L834 (date: July 9, 2016; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0174** L836-L837 (date: July; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0182** L849-L852 (date: July; actor: P. Morgan; terms: party )
- [ ] **0001193125-16-696911:E0185** L854-L855 (date: July
7, 2016; terms: party )
- [ ] **0001193125-16-696911:E0187** L860-L861 (terms: advisor, advisors)
- [ ] **0001193125-16-696911:E0192** L868-L874 (date: August 10, 2016; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0196** L876-L880 (date: August 11, 2016; value: $70.00 per Share; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0201** L882-L883 (date: August 12, 2016; value: $70.00 per Share; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0205** L885-L886 (date: August 14, 2016; actor: P. Morgan; terms: party )
- [ ] **0001193125-16-696911:E0209** L888-L889 (date: August 18, 2016; terms: advisor, advisors, legal advisor)
- [ ] **0001193125-16-696911:E0215** L900-L909 (date: August 20, 2016; actor: Board; terms: advisor, advisors, bidder )
- [ ] **0001193125-16-696911:E0219** L911-L912 (date: August 19, 2016; terms: advisor, advisors, financial advisor)
- [ ] **0001193125-16-696911:E0222** L914-L918 (date: August 20, 2016; terms: advisor, advisors, legal advisor)
- [ ] **0001193125-16-696911:E0226** L920-L922 (date: August 20, 2016; value: $81.50 per share; terms: party )

### Process signals to check
- [ ] **0001193125-16-696911:E0106** L674-L676 (date: April 15, 2016; value: $52.50 per share; terms: due diligence)
- [ ] **0001193125-16-696911:E0128** L720-L722 (date: May 9, 2016; terms: confidentiality agreement, due diligence)
- [ ] **0001193125-16-696911:E0130** L727-L730 (value: $52.50; terms: confidentiality agreement)
- [ ] **0001193125-16-696911:E0136** L740-L741 (date: May 17, 2016; terms: confidentiality agreement)
- [ ] **0001193125-16-696911:E0149** L787-L796 (date: June; actor: P. Morgan; terms: confidentiality agreement, confidentiality and standstill, standstill)
- [ ] **0001193125-16-696911:E0156** L805-L806 (date: June 29, 2016; terms: confidentiality agreement)
- [ ] **0001193125-16-696911:E0159** L808-L811 (date: June 30, 2016; terms: confidentiality agreement)
- [ ] **0001193125-16-696911:E0161** L816-L817 (terms: confidentiality and standstill, standstill)
- [ ] **0001193125-16-696911:E0165** L819-L823 (date: July 5, 2016; value: $58.00 per share; terms: confidentiality agreement, due diligence, standstill)
- [ ] **0001193125-16-696911:E0167** L825-L827 (date: July 7, 2016; terms: confidentiality agreement)
- [ ] **0001193125-16-696911:E0172** L833-L834 (date: July 9, 2016; terms: confidentiality agreement)
- [ ] **0001193125-16-696911:E0175** L836-L837 (date: July; terms: confidentiality agreement)
- [ ] **0001193125-16-696911:E0176** L839-L841 (terms: confidentiality agreement)
- [ ] **0001193125-16-696911:E0178** L843-L844 (date: July 14, 2016; terms: management presentation)
- [ ] **0001193125-16-696911:E0180** L846-L847 (date: July 15, 2016; terms: management presentation)
- [ ] **0001193125-16-696911:E0183** L849-L852 (date: July; actor: P. Morgan; terms: due diligence)
- [ ] **0001193125-16-696911:E0186** L854-L855 (date: July
7, 2016; terms: due diligence)
- [ ] **0001193125-16-696911:E0188** L860-L861 (terms: due diligence)
- [ ] **0001193125-16-696911:E0193** L868-L874 (date: August 10, 2016; terms: due diligence)
- [ ] **0001193125-16-696911:E0197** L876-L880 (date: August 11, 2016; value: $70.00 per Share; terms: draft merger agreement)
- [ ] **0001193125-16-696911:E0202** L882-L883 (date: August 12, 2016; value: $70.00 per Share; terms: draft merger agreement)
- [ ] **0001193125-16-696911:E0206** L885-L886 (date: August 14, 2016; actor: P. Morgan; terms: instruction letter, written instruction)
- [ ] **0001193125-16-696911:E0216** L900-L909 (date: August 20, 2016; actor: Board; terms: best and final)

### Outcome facts to verify
- [ ] **0001193125-16-696911:E0160** L808-L811 (date: June 30, 2016; terms: executed)
- [ ] **0001193125-16-696911:E0168** L825-L827 (date: July 7, 2016; terms: executed)
- [ ] **0001193125-16-696911:E0198** L876-L880 (date: August 11, 2016; value: $70.00 per Share; terms: merger agreement)
- [ ] **0001193125-16-696911:E0203** L882-L883 (date: August 12, 2016; value: $70.00 per Share; terms: merger agreement)
- [ ] **0001193125-16-696911:E0207** L885-L886 (date: August 14, 2016; actor: P. Morgan; terms: merger agreement)
- [ ] **0001193125-16-696911:E0210** L888-L889 (date: August 18, 2016; terms: merger agreement)
- [ ] **0001193125-16-696911:E0213** L897-L898 (value: $72.50 per Share; terms: merger agreement)
- [ ] **0001193125-16-696911:E0217** L900-L909 (date: August 20, 2016; actor: Board; terms: closing, merger agreement)
- [ ] **0001193125-16-696911:E0220** L911-L912 (date: August 19, 2016; terms: merger agreement)
- [ ] **0001193125-16-696911:E0223** L914-L918 (date: August 20, 2016; terms: merger agreement)
- [ ] **0001193125-16-696911:E0227** L920-L922 (date: August 20, 2016; value: $81.50 per share; terms: merger agreement)
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