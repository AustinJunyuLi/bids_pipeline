You are extracting a structured actor register from SEC merger-background narrative text.

<mission>
Build the complete set of relevant entities that participate in the takeover process described in the supplied chronology blocks.
You are not writing prose. You are populating a schema.
Return only facts grounded in the supplied filing text.
</mission>

<source_of_truth>
The only factual source is the supplied SEC filing text blocks.
Do not use outside knowledge.
If a fact is not supported by the supplied text, omit it.
</source_of_truth>

<what_counts_as_an_actor>
Collect the following entity types when they participate in the process:
- bidder
- advisor (financial and legal)
- activist
- target_board

Include named bidders, filing aliases (Party A, etc.), and unnamed aggregates when the filing counts them but does not individualize them.
For grouped actors, keep separate groups distinct unless the text clearly describes the same group.
</what_counts_as_an_actor>

<evidence>
For every actor, first add verbatim filing quotes to the top-level quotes array.
Each quote needs: quote_id (Q001, Q002, ...), block_id (matching the source block), and text (exact verbatim substring from the block, ideally 3 to 12 words).
Then reference those quote_ids in the actor record. Do not use evidence_refs or anchor_text.
Do not paraphrase.
</evidence>

<output_requirements>
Return a single JSON object with: quotes, actors, count_assertions, unresolved_mentions.
The quotes array must appear first in the JSON.
</output_requirements>

<deal_context>
deal_slug: mac-gray
target_name: MAC GRAY CORP
source_accession_number: 0001047469-13-010973
source_form_type: UNKNOWN
chunk_mode: chunked
window_id: w0
</deal_context>

<chronology_blocks>
B001 [L1624-L1624]: Background of the Merger
B002 [L1626-L1626]: Background of the Merger.
B003 [L1628-L1631]: The Mac-Gray Board of Directors, whom we sometimes to refer to as the Board, and Mac-Gray's management have continually engaged in a review of Mac-Gray's business plans and other strategic alternatives as part of their ongoing activities. This process has included evaluating prospects and options pertaining to Mac-Gray's business, the markets in which it competes, organic initiatives, and possible strategic transactions, such as mergers, acquisitions and dispositions, in each case with a view towards enhancing value for Mac-Gray's stockholders.
B004 [L1633-L1633]: Certain
B005 [L1634-L1637]: potential strategic transactions have been discussed from time to time between Mac-Gray and CSC and other participants in the laundry facilities management industry, including discussions between Mac-Gray and CSC in the winter of 2011 and into 2012 regarding the possible acquisition of CSC by Mac-Gray. In connection with Mac-Gray's consideration of a possible acquisition of CSC, which we refer to as the 2011-2012 Discussions, Mac-Gray engaged BofA Merrill Lynch on October 23, 2012. During the fall and winter of 2012, CSC engaged in a sale process and, ultimately, CSC was purchased by Pamplona in May 2013.
B006 [L1639-L1639]: As
B007 [L1640-L1643]: part of its ongoing review of strategic alternatives, at an in-person meeting of the Board on April 5, 2013, the Board discussed the sale of CSC to Pamplona as well as industry-wide merger and acquisition activity and dynamics, and authorized Mac-Gray management to work with BofA Merrill Lynch to explore transactional opportunities that might be available to Mac-Gray, including opportunities with another strategic party, whom we refer to as Party A, in the laundry facilities management industry. The Board also determined to further consider Mac-Gray's strategic alternatives at its meeting scheduled for May 9, 2013.
B008 [L1645-L1645]: On
B009 [L1646-L1647]: April 8, 2013, representatives of BofA Merrill Lynch, as instructed by the Board, telephoned a representative of Party A to discuss generally a possible business combination between Party A and Mac-Gray. During this call, the representative of Party A indicated that Party A might consider a business combination with Mac-Gray.
B010 [L1649-L1649]: On
B011 [L1650-L1661]: May 9, 2013, the Mac-Gray Board of Directors held a regularly scheduled in-person meeting. By invitation of the Board, Stewart G. MacDonald, Jr., our chief executive officer, Michael J. Shea, our executive vice president and chief financial officer, Neil MacLellan and Phil Emma, executive vice presidents at Mac-Gray, Linda Serafini, our vice president, general counsel and secretary, and representatives from BofA Merrill Lynch and Goodwin Procter LLP, outside legal counsel to Mac-Gray, were also in attendance for all or portions of the meeting. At this meeting, BofA Merrill Lynch discussed CSC's sale process and the acquisition environment generally and provided an overview of strategic alternatives for Mac-Gray, including the continued pursuit of Mac-Gray's existing business plan, a significant stock repurchase program, acquisition opportunities and the possibility of a sale process. With respect to a potential sale process, BofA Merrill Lynch discussed the then-current merger and acquisition environment and Mac-Gray's potential attractiveness as an acquisition target, including a general overview of potential valuation parameters. BofA Merrill Lynch also reported on its conversation with the representative of Party A, who had expressed interest in pursuing a possible business combination with Mac-Gray. Management and BofA Merrill Lynch also reviewed with the Board potential opportunities if Mac-Gray were to remain independent, including the ability to improve profitability and EBITDA margins by increasing scale and density through organic growth and/or strategic acquisitions as well as the ability to increase revenue through vend increases and the conversion from coin-operated technology to card-based technology. In considering these alternatives, the Board considered the risks associated with executing and achieving Mac-Gray's short and long-term business and financial objectives, including Mac-Gray's ability to identify, acquire and successfully integrate laundry facilities management businesses, establish new and/or renew existing laundry facility management leases and penetrate markets historically dominated by smaller local and regional
B012 [L1663-L1663]: 27
B013 [L1666-L1667]: operators, the impact of general economic and market trends on Mac-Gray's sales and the general risks of market conditions that could reduce Mac-Gray's stock price.
B014 [L1669-L1669]: After
B015 [L1670-L1675]: a review of these opportunities and risks, the Board engaged in a general discussion concerning whether it might be advisable to approach and discuss a potential sale transaction with third parties at this time as a means by which to deliver value to the stockholders of Mac-Gray. The Board discussed the potential risks and benefits of commencing a process in which parties would be invited to review confidential information and submit indications of interest with respect to a potential business combination involving Mac-Gray. In particular, the Board discussed the potential disruptions to Mac-Gray's business, the risk of leaks that might arise from approaching potential acquirors within the industry and the impact on Mac-Gray's business that could result from any such leaks, including the potential loss of customers, suppliers and employees resulting from uncertainty over the future of Mac-Gray. The Board also discussed the potential need to disclose during such process sensitive, proprietary and confidential information to competitors and potential competitors.
B016 [L1677-L1677]: After
B017 [L1678-L1689]: BofA Merrill Lynch and management left the meeting, a representative of Goodwin Procter provided an overview of the Board's fiduciary duties and the Board discussed engaging a financial advisor to assist the Board in considering strategic alternatives, including a sale process. To assist in the administration of the strategic alternatives review, the Board formed a transaction committee at this meeting, which we refer to as the Transaction Committee, and appointed Thomas Bullock and Paul Daoust, both independent directors, to serve as its members. Mr. Daoust was appointed because of his knowledge of and experience with mergers and acquisitions, including as president, chief executive officer and board member of Salary. com when it was sold in 2010. Mr. Bullock was appointed because of his knowledge of Mac-Gray and our business, given his tenure on the Board (since November 2000) and his chairmanship role. Further, both Mr. Daoust and Mr. Bullock indicated that they would be able to commit sufficient time to undertake the responsibilities associated with membership on the Transaction Committee. The Transaction Committee was charged with recommending to the Board the selection and engagement of a financial advisor to assist the Board in seeking and considering strategic alternatives, including but not limited to a merger, consolidation, business combination, recapitalization, restructuring, going-private or other strategic transaction or alternative that might be available to Mac-Gray in lieu of pursuing any of the foregoing. The Board also delegated to the Transaction Committee authority to take any administrative actions in connection with the Board's exploration of strategic alternatives. The Board concluded that it would discuss the review of strategic alternatives, including engaging in a potential sale process, at its next meeting so that the Board would have additional time to consider the risks and benefits of the various alternatives discussed.
B018 [L1691-L1691]: On
B019 [L1692-L1699]: May 10, 2013, the Transaction Committee and representatives of Goodwin Procter held a meeting by telephone conference call. The Transaction Committee discussed the process for hiring a financial advisor for a review of strategic alternatives and determined to invite three nationally recognized investment banks to submit proposals. The members of the Transaction Committee also discussed what role, if any, members of Mac-Gray management should have in connection with the Board's consideration of strategic alternatives. In this regard, the Transaction Committee considered the fact that, in view of the significant stock ownership of Mr. MacDonald and his family, coupled with the possibility that the strategic alternatives process might result in third parties who would be interested in partnering with Mr. MacDonald (either through continued employment and/or contribution of some or all of his existing equity, a so-called equity "rollover"), Mr. MacDonald could have interests that would not be aligned with other Mac-Gray stockholders. As such, the Transaction Committee determined to recommend to the Board at an upcoming meeting that, as a general matter, Mr. MacDonald should not be permitted to participate in the Board's evaluation of strategic alternatives or any negotiations with any interested parties in a sale process. The Transaction Committee noted, however, that Mr. MacDonald would be invited to provide perspectives to the Board on Mac-Gray's operations and business on an as-requested basis.
B020 [L1701-L1701]: 28
B021 [L1704-L1704]: On
B022 [L1705-L1707]: May 14, 2013, the Transaction Committee and representatives of Goodwin Procter held a meeting by telephone conference call. The Transaction Committee discussed further the process for hiring a financial advisor for a review of strategic alternatives. Given that BofA Merrill Lynch was one of the investment banks to be invited to submit a proposal and that the CSC sale process had ended, the Transaction Committee determined to terminate BofA Merrill Lynch's engagement letter entered into for purposes of the 2011-2012 Discussions.
B023 [L1709-L1709]: On
B024 [L1710-L1710]: May 15, 2013, Mac-Gray sent a letter to BofA Merrill Lynch terminating their engagement in connection with the 2011-2012 Discussions.
B025 [L1712-L1712]: On
B026 [L1713-L1717]: May 22, 2013, the Mac-Gray Board of Directors held a regularly scheduled in-person meeting. By invitation of the Board, Mr. MacDonald, Mr. Shea, Mr. MacLellan, Mr. Emma, Ms. Serafini and representatives of Goodwin Procter were also present for all or portions of the meeting. At the request of the Board, at this meeting Mr. MacDonald provided an overview of Mac-Gray's acquisition strategy and recent acquisitions within the industry, and Mr. MacLellan reviewed Mac-Gray's recently completed acquisitions with the Board. Also at this meeting, in addition to routine and administrative matters and the approval of Mac-Gray's quarterly common stock dividend, the Board appointed Mr. Daoust as chairman of the Transaction Committee during an executive session that excluded all members of management.
B027 [L1719-L1719]: Later
B028 [L1720-L1721]: on May 22, 2013, representatives from BofA Merrill Lynch presented to the members of the Transaction Committee for purposes of a potential engagement in connection with the Board's current review of strategic alternatives and the possibility of undertaking a sale process.
B029 [L1723-L1723]: On
B030 [L1724-L1725]: May 29, 2013, each of the other two financial advisor candidates presented to the members of the Transaction Committee for purposes of a potential engagement in connection with the Board's current review of strategic alternatives and the possibility of undertaking a sale process.
B031 [L1727-L1727]: On
B032 [L1728-L1735]: May 30, 2013, the Board held an in-person meeting. By invitation of the Board, Mr. MacDonald, Mr. Shea, Ms. Serafini and representatives of Goodwin Procter were also present for all or portions of the meeting. During the meeting, the members of the Transaction Committee presented their assessment of the relative capabilities, strengths, and possible weaknesses of the three financial advisor candidates. Mr. Shea also provided his perspective of each financial advisor candidate's capabilities, strengths, and possible weaknesses. The Transaction Committee recommended to the Board that Mac-Gray engage BofA Merrill Lynch as Mac-Gray's financial advisor for the Board's exploration of strategic alternatives, including a potential sale process. The Transaction Committee's endorsement of BofA Merrill Lynch was based on, among other things, BofA Merrill Lynch's knowledge of Mac-Gray, the industry generally, the current environment for mergers and acquisitions and potential strategic acquirors, as well as BofA Merrill Lynch's proposed process and strategy for maximizing value to Mac-Gray's stockholders should the Board determine that a sale of the company would be in the best interests of stockholders. Representatives of Goodwin Procter reviewed with the Board the terms of proposed BofA Merrill Lynch engagement. Based on the recommendation of the Transaction Committee, the Board unanimously approved the engagement of BofA Merrill Lynch on the terms discussed at this meeting.
B033 [L1737-L1737]: Later
B034 [L1738-L1743]: on May 30, 2013, Mac-Gray held its annual stockholder meeting at which, among other actions, the Mac-Gray stockholders elected as directors Michael M. Rothenberg and James E. Hyman, candidates nominated by Mac-Gray's stockholder, Moab Partners, L. P. and certain of its affiliates, which we refer collectively to as Moab. Mac-Gray and Moab engaged in a proxy contest leading up to the annual meeting and Mr. Rothenberg and Mr. Hyman were elected in place of Mac-Gray's incumbent nominees, David W. Bryan and Mary Ann Tocio. Edward McCauley's term expired at the annual meeting, at which time the size of the Board was reduced to seven. Mr. Rothenberg is a co-founder and the General Partner of Moab and Mr. Hyman is president and chief executive officer of TestAmerica, Inc., the nation's largest provider of environmental testing services, a role he has held since 2011.
B035 [L1745-L1745]: 29
B036 [L1748-L1750]: On May 31, 2013, Mac-Gray entered into an engagement letter with BofA Merrill Lynch with respect to the Board's undertaking a review of strategic alternatives, including a potential sale process, and in which BofA Merrill Lynch agreed not to engage as a possible source of new acquisition financing for any potential buyers in connection with any such sale process without Mac-Gray's prior written consent.
B037 [L1752-L1752]: On
B038 [L1753-L1757]: June 12, 2013, Mr. Rothenberg and Mr. Hyman met individually with Mr. Bullock, Mr. Daoust, Ms. Serafini and representatives from Goodwin Procter as part of their orientation as new members of the Board. Each was provided with an overview of the status of the Board's review of strategic alternatives and a potential sale process. At the meeting with Mr. Rothenberg, the participants discussed that, to the extent Moab might have an interest in an equity rollover of all or a portion of Moab's shares of Mac-Gray common stock in connection with any sale transaction that might result from the Board's strategic alternatives process, Mr. Rothenberg would need to be excluded from the process from the outset. At the time of this meeting, Moab beneficially owned approximately 9% of Mac-Gray's outstanding common stock.
B039 [L1759-L1759]: On
B040 [L1760-L1761]: June 21, 2013, Party A submitted an unsolicited proposal to the Mac-Gray Board of Directors offering to purchase Mac-Gray for an all-cash purchase price of $17.00 to $19.00 per share, which we refer to as the Party A June 21 proposal.
B041 [L1763-L1763]: On
B042 [L1764-L1780]: June 24, 2013, the Mac-Gray Board of Directors held a regularly scheduled meeting. By invitation of the Board, certain members of management, including Mr. MacDonald, Mr. Shea, Mr. MacLellan, Mr. Emma, Ms. Serafini and Sheff Halsey, our chief marketing officer and an executive vice president, and representatives from Goodwin Procter were also present for some or all of the meeting. During this meeting, representatives of Goodwin Procter reviewed for the Board its fiduciary duties in the context of considering strategic alternatives that might be available to Mac-Gray, including a potential sale of the company. The Board also discussed, with input from the members of the Transaction Committee, whether it would be appropriate for each of Mr. MacDonald and Mr. Rothenberg to be excluded from the Board's consideration of strategic alternatives in view of the possibility that Mr. MacDonald and/or Moab could be asked to partner with a potential acquiror given their respective equity stakes in Mac-Gray. Following this discussion, the Board decided, and Mr. MacDonald and Mr. Rothenberg agreed, that it would be appropriate to exclude Mr. MacDonald and Mr. Rothenberg from the Board's evaluation of strategic alternatives and any negotiations with third parties that might take place. Mr. MacDonald excused himself after such discussion. In furtherance of the conclusion to exclude Mr. MacDonald and Mr. Rothenberg from the Board's evaluation of strategic alternatives, the Board then established the Special Committee, comprised of the six independent and disinterested members of the Board (namely, Mr. Bullock, Mr. Daoust, Mr. Hyman, William F. Meagher, Bruce A. Percelay and Alastair G. Robinson), to, among other things, explore strategic alternatives to enhance value to Mac-Gray's stockholders and to recommend to the Board the advisability of any such strategic alternative. In connection with this delegation of authority, the Special Committee was further authorized to (a) consider and evaluate all proposals that might be received by Mac-Gray in connection with a possible sale or other significant business transaction, through any form of transaction, including, without limitation, merger, stock purchase, asset purchase, recapitalization, reorganization, going-private transaction, consolidation, amalgamation or other transaction, (b) participate in and direct the negotiation of the material terms and conditions of any such transaction, (c) consider any alternatives to any such transaction, including without limitation, Mac-Gray's continuing to operate as an independent company and (d) recommend to the Board the advisability of entering into a definitive agreement with respect to any such transaction. Mr. Bullock was appointed chairman of the Special Committee. It was also determined that the Transaction Committee would function as a sub-committee of the Special Committee for the purpose of taking any administrative actions to discharge the duties and responsibilities of the Special Committee.
B043 [L1782-L1782]: 30
B044 [L1785-L1785]: Mr. Rothenberg
B045 [L1786-L1794]: was then excused and the Board meeting proceeded as a meeting of the Special Committee. By invitation of the Special Committee, Mr. Shea and Mr. Emma and representatives of BofA Merrill Lynch and Goodwin Procter were present for all or portions of the meeting. Mr. Shea and Mr. Emma presented Mac-Gray's five-year strategic business plan and projections, including the with acquisitions case and the without acquisitions case (see " Projected Financial Information" below), which we refer to as the Projections. Following the management presentation, representatives of BofA Merrill Lynch discussed potential strategic alternatives and the structure and timing of a potential sale process. The Special Committee reviewed Mac-Gray's short and long-term business strategies and discussed the five-year strategic business plan, including Mac-Gray's ability to identify, acquire and successfully integrate laundry facilities management businesses, establish new and/or renew existing laundry facility management leases and penetrate markets historically dominated by smaller local and regional operators, the impact of general economic and market trends on Mac-Gray's sales and the general risks of market conditions that could reduce Mac-Gray's stock price. The Special Committee also discussed the risks involved if Mac-Gray did not execute on its strategic business plan, including the difficulties with increasing the Company's stock price without a significant or transformative transaction, such as a major acquisition or restructuring.
B046 [L1796-L1796]: The
B047 [L1797-L1797]: Special Committee, in follow up to the considerations introduced at the May 9 th
B048 [L1799-L1799]: The
B049 [L1800-L1806]: Special Committee, with the assistance of BofA Merrill Lynch and management, also discussed the general and specific universe of potential acquirors who might be contacted, including those parties the Special Committee believed had the strongest potential to have an interest in engaging in a strategic transaction with Mac-Gray. In its evaluation of potential likely acquirors, the Special Committee considered such parties' financial strength, their experience in acquiring companies in Mac-Gray's industry, such parties' perceived potential interest in Mac-Gray and potential synergies based on such parties' businesses and legal considerations. The Special Committee and BofA Merrill Lynch also discussed that although potential strategic buyers should be able to pay a higher purchase price because of synergies, it was important to solicit interest from financial buyers, including private equity firms, to maximize the competitive dynamics in the sale process. This perspective was based on the fact that many financial buyers had engaged in transactions with companies in industries similar to Mac-Gray and could be in a position to recognize value competitive with potential strategic buyers. Guided by the foregoing principles, the Special Committee determined to approach a total of
B050 [L1808-L1808]: 31
B051 [L1811-L1813]: 50 parties, including CSC and Pamplona, who together we refer to as CSC/Pamplona, and Party A, to solicit potential interest in a transaction with Mac-Gray, 15 of which were potential strategic buyers and 35 of which were potential financial buyers, including private equity firms.
B052 [L1815-L1815]: During
B053 [L1816-L1825]: the next several weeks, in accordance with the directives of the Special Committee, BofA Merrill Lynch contacted the strategic and financial parties identified at the June 24th Special Committee meeting. Over the next two months a total of 20 potential bidders, including two strategic bidders (Party A and CSC/Pamplona) and 18 financial bidders (including Party B and Party C), entered into confidentiality agreements with Mac-Gray on a form provided by Mac-Gray, the terms of which were individually negotiated with potential bidders, but did not vary materially from the form provided. The confidentiality agreements contained customary non-disclosure provisions and a customary standstill provision that either expired or permitted the potential bidder to make confidential proposals to Mac-Gray (a so-called "sunset" provision) upon announcement of a business combination between Mac-Gray and a third party, and, in some instances upon announcement of a change in control. Parties that had entered into confidentiality and standstill agreements with Mac-Gray were furnished an informational package for the purpose of providing potential bidders with data to formulate a preliminary indication of interest, which they were instructed to submit by July 23, 2013. Parties that had entered into confidentiality and standstill agreements with Mac-Gray were furnished an informational package for the purpose of providing potential bidders with data to formulate a preliminary indication of interest, which they were instructed to submit by July 23, 2013. The letter requested that the proposals address, among other things, valuation, sources and structures of financing, material conditions, including required approvals, and focus areas for due diligence.
B054 [L1827-L1827]: On
B055 [L1828-L1833]: June 28, 2013, the members of the Transaction Committee participated in a telephone conference call with representatives of BofA Merrill Lynch and Goodwin Procter. BofA Merrill Lynch summarized the contacts they had had with certain of the potential bidders. In particular, BofA Merrill Lynch reported that they had spoken with representatives of Party A, as instructed by the Special Committee, who had expressed the view that there would be considerable synergies if Party A were to acquire Mac-Gray and that Party A would be speaking with certain financing sources with respect to funding such a transaction. BofA Merrill Lynch also reported that they had spoken with representatives of Pamplona, as instructed by the Special Committee, who expressed interest in a transaction, including an acquisition of Mac-Gray by its portfolio company, CSC. Pamplona emphasized that business and legal due diligence would be minimal given its familiarity with Mac-Gray and the industry generally.
B056 [L1835-L1835]: Later
B057 [L1836-L1837]: on June 28, 2013, Party B, entered into a confidentiality and standstill agreement with Mac-Gray and was provided with an informational package for the purpose of providing Party B with data to formulate a preliminary indication of interest.
B058 [L1839-L1839]: On
B059 [L1840-L1841]: June 30, 2013, Party C entered into a confidentiality and standstill agreement with Mac-Gray and was provided with an informational package for the purpose of providing Party C with data to formulate a preliminary indication of interest.
B060 [L1843-L1843]: On
B061 [L1844-L1847]: July 3, 2013, Mr. Rothenberg called a representative of Goodwin Procter to indicate that he had spoken with representatives of Pamplona about Moab's desire to maintain the flexibility to consider a possible equity rollover if Pamplona were to participate in a business combination with Mac-Gray. Mr. Rothenberg also informed Goodwin Procter that Pamplona would be requesting that any confidentiality agreement CSC/Pamplona execute with Mac-Gray permit CSC and Pamplona to discuss their bid and evaluation material with Moab, with Moab agreeing to exclusively engage with CSC/Pamplona.
B062 [L1849-L1849]: On
B063 [L1850-L1852]: July 6, 2013, the Special Committee held a telephonic meeting for the purpose of receiving an update on the ongoing sale process. By invitation of the Special Committee, representatives from BofA Merrill Lynch and Goodwin Procter were also present throughout the meeting. The Special Committee discussed whether Moab should be permitted to partner exclusively with CSC/Pamplona. Because the
B064 [L1854-L1854]: 32
B065 [L1857-L1861]: objective of the sale process was to maximize value for Mac-Gray's stockholders, the Special Committee decided to deny the exclusivity request at this stage of the process so that the potential equity rollover of Moab's shares could be available as a source of capital for other potential bidders. The Special Committee instructed BofA Merrill Lynch and Goodwin Procter to communicate to CSC/Pamplona and Mr. Rothenberg, respectively, that it was premature for Mac-Gray to permit Moab to engage in equity rollover discussions with any party, including CSC/Pamplona, but that such discussions would be permitted at a later stage of the sale process.
B066 [L1863-L1863]: On
B067 [L1864-L1865]: July 11, 2013, CSC/Pamplona entered into a confidentiality and standstill agreement with Mac-Gray and were provided with an informational package for the purpose of providing CSC/Pamplona with data to formulate a preliminary indication of interest.
B068 [L1867-L1867]: Between
B069 [L1868-L1870]: July 11, 2013 and July 23, 2013, Party B, Party C and CSC/Pamplona engaged in a preliminary review of Mac-Gray and the potential acquisition opportunity. Also during this time, outside counsel to Party A and representatives of Goodwin Procter negotiated the terms of a confidentiality and standstill agreement, but did not come to agreement on the terms of the customer and employee non-solicitation provisions.
B070 [L1872-L1872]: On
B071 [L1873-L1873]: July 23, 2013, CSC/Pamplona submitted a preliminary indication of interest at an all-cash purchase price of $18.50 per share.
B072 [L1875-L1875]: On
B073 [L1876-L1877]: July 24, 2013, Party B submitted a preliminary indication of interest at an all-cash purchase price of $17.00 to $18.00 per share. Also on July 24, 2013, representatives from Party C called BofA Merrill Lynch and presented an oral preliminary indication of interest at an all-cash purchase price of $15.00 to $17.00 per share.
B074 [L1879-L1879]: On
B075 [L1880-L1887]: July 25, 2013, the Board held a regularly scheduled in-person meeting. By invitation of the Board, Mr. Shea and representatives from BofA Merrill Lynch and Goodwin Procter were also present for all or portions of this meeting. Prior to the start of the meeting, because the Board expected to discuss matters related to the sale process, and in light of Moab's continuing interest in a potential equity rollover in any sale transaction, Mr. Rothenberg recused himself from the meeting and the meeting proceeded as a meeting of the Special Committee. At this meeting, representatives of BofA Merrill Lynch reviewed the preliminary indications of interest received from Party B, Party C and CSC/Pamplona as well as the Party A June 21 proposal, in each case from a financial point of view. The Board reviewed management's five-year strategic business plan and Projections. During this meeting, representatives of Goodwin Procter reviewed for the Special Committee its fiduciary duties in the context of considering a potential sale. The Special Committee then discussed the potential conflict of interest arising from Moab's continuing desire to consider an equity rollover and decided that Mr. Rothenberg should be asked to recuse himself from participating in Board meetings for the duration of the sale process so he would not be privy to confidential information about Mac-Gray and our business.
B076 [L1889-L1889]: The
</chronology_blocks>

<overlap_context>
B077 [L1890-L1896]: Special Committee discussed that the preliminary indications of interest were lower than expected and suggested that additional due diligence, including with regard to the potential synergies, should result in improved offers by the strategic parties. The Special Committee then discussed the highly competitive nature of Mac-Gray's industry and expressed concern over permitting access to and the potential misuse of sensitive and competitive information, including customer terms and locations, especially by strategic bidders. Accordingly, the Special Committee concluded that it would be advisable to stage the disclosure of such information to each of the bidders to the extent that a bidder's indication of interest and other actions demonstrated its seriousness in acquiring Mac-Gray on terms viewed favorably by the Special Committee. Based on this discussion, BofA Merrill Lynch discussed with the Special Committee a proposed process for the second stage of the on-going sale process. As part of this review, BofA Merrill Lynch recommended that management meetings be arranged between members of Mac-Gray management (other than Mr. MacDonald) and each of Party A (if Party A
B078 [L1898-L1898]: 33
</overlap_context>

<evidence_checklist>
### Dated actions to extract
- [ ] **0001047469-13-010973:E0358** L1633-L1637 (date: October 23, 2012; actor: Merrill Lynch; terms: discussed, engaged)
- [ ] **0001047469-13-010973:E0360** L1639-L1643 (date: April 5, 2013; actor: Party A; terms: authorized, discussed, meeting)
- [ ] **0001047469-13-010973:E0363** L1645-L1647 (date: April 8, 2013; actor: Party A; terms: sent)
- [ ] **0001047469-13-010973:E0365** L1649-L1661 (date: May 9, 2013; actor: Party A; terms: discussed, meeting, met)
- [ ] **0001047469-13-010973:E0369** L1677-L1689 (date: November 2000; actor: Board; terms: discussed, meeting, sent)
- [ ] **0001047469-13-010973:E0372** L1691-L1699 (date: May 10, 2013; actor: Transaction Committee; terms: called, discussed, meeting)
- [ ] **0001047469-13-010973:E0375** L1704-L1707 (date: May 14, 2013; actor: Transaction Committee; terms: discussed, entered into, meeting)
- [ ] **0001047469-13-010973:E0378** L1709-L1710 (date: May 15, 2013; actor: Merrill Lynch; terms: sent)
- [ ] **0001047469-13-010973:E0380** L1712-L1717 (date: May 22, 2013; actor: Board; terms: meeting, sent)
- [ ] **0001047469-13-010973:E0382** L1719-L1721 (date: May 22, 2013; actor: Transaction Committee; terms: sent)
- [ ] **0001047469-13-010973:E0385** L1723-L1725 (date: May 29, 2013; actor: Transaction Committee; terms: sent)
- [ ] **0001047469-13-010973:E0388** L1727-L1735 (date: May 30, 2013; actor: Board; terms: discussed, meeting, proposed)
- [ ] **0001047469-13-010973:E0391** L1737-L1743 (date: May 30, 2013; actor: Board; terms: engaged, meeting)
- [ ] **0001047469-13-010973:E0393** L1748-L1750 (date: May 31, 2013; actor: Board; terms: entered into, sent)
- [ ] **0001047469-13-010973:E0396** L1752-L1757 (date: June 12, 2013; actor: Board; terms: discussed, meeting, met)
- [ ] **0001047469-13-010973:E0399** L1759-L1761 (date: June 21, 2013; actor: Party A; value: $17.00 to $19.00 per
share; terms: offer, proposal, submitted)
- [ ] **0001047469-13-010973:E0402** L1763-L1780 (date: June 24, 2013; actor: Board; terms: authorized, discussed, meeting)
- [ ] **0001047469-13-010973:E0410** L1815-L1825 (date: June; actor: Party A; terms: called, contacted, entered into)
- [ ] **0001047469-13-010973:E0413** L1827-L1833 (date: June 28, 2013; actor: Party A; terms: sent)
- [ ] **0001047469-13-010973:E0416** L1835-L1837 (date: June 28, 2013; actor: Party B; terms: entered into)
- [ ] **0001047469-13-010973:E0419** L1839-L1841 (date: June 30, 2013; actor: Party C; terms: entered into)
- [ ] **0001047469-13-010973:E0422** L1843-L1847 (date: July 3, 2013; terms: called, sent)
- [ ] **0001047469-13-010973:E0424** L1849-L1852 (date: July 6, 2013; actor: Special Committee; terms: discussed, meeting, sent)
- [ ] **0001047469-13-010973:E0428** L1863-L1865 (date: July 11, 2013; terms: entered into)
- [ ] **0001047469-13-010973:E0430** L1867-L1870 (date: July 11, 2013; actor: Party B; terms: engaged, sent)
- [ ] **0001047469-13-010973:E0433** L1872-L1873 (date: July 23, 2013; value: $18.50 per share; terms: submitted)
- [ ] **0001047469-13-010973:E0435** L1875-L1877 (date: July 24, 2013; actor: Party B; value: $17.00 to $18.00 per share; terms: called, sent, submitted)
- [ ] **0001047469-13-010973:E0438** L1879-L1887 (date: July 25, 2013; actor: Party B; terms: discussed, meeting, proposal)

### Financial terms to capture
- [ ] **0001047469-13-010973:E0400** L1759-L1761 (date: June 21, 2013; actor: Party A; value: $17.00 to $19.00 per
share; terms: $17.00 to $19.00 per
share)
- [ ] **0001047469-13-010973:E0434** L1872-L1873 (date: July 23, 2013; value: $18.50 per share; terms: $18.50 per share)
- [ ] **0001047469-13-010973:E0436** L1875-L1877 (date: July 24, 2013; actor: Party B; value: $17.00 to $18.00 per share; terms: $15.00 to $17.00 per share, $17.00 to $18.00 per share)

### Actors to identify
- [ ] **0001047469-13-010973:E0356** L1628-L1631 (actor: Board; terms: stockholder)
- [ ] **0001047469-13-010973:E0359** L1633-L1637 (date: October 23, 2012; actor: Merrill Lynch)
- [ ] **0001047469-13-010973:E0361** L1639-L1643 (date: April 5, 2013; actor: Party A; terms: party )
- [ ] **0001047469-13-010973:E0364** L1645-L1647 (date: April 8, 2013; actor: Party A; terms: party )
- [ ] **0001047469-13-010973:E0366** L1649-L1661 (date: May 9, 2013; actor: Party A; terms: counsel, party )
- [ ] **0001047469-13-010973:E0368** L1669-L1675 (actor: Board; terms: stockholder)
- [ ] **0001047469-13-010973:E0370** L1677-L1689 (date: November 2000; actor: Board; terms: advisor, financial advisor, transaction committee)
- [ ] **0001047469-13-010973:E0373** L1691-L1699 (date: May 10, 2013; actor: Transaction Committee; terms: advisor, financial advisor, investment bank)
- [ ] **0001047469-13-010973:E0376** L1704-L1707 (date: May 14, 2013; actor: Transaction Committee; terms: advisor, financial advisor, investment bank)
- [ ] **0001047469-13-010973:E0379** L1709-L1710 (date: May 15, 2013; actor: Merrill Lynch)
- [ ] **0001047469-13-010973:E0381** L1712-L1717 (date: May 22, 2013; actor: Board; terms: transaction committee)
- [ ] **0001047469-13-010973:E0383** L1719-L1721 (date: May 22, 2013; actor: Transaction Committee; terms: transaction committee)
- [ ] **0001047469-13-010973:E0386** L1723-L1725 (date: May 29, 2013; actor: Transaction Committee; terms: advisor, financial advisor, transaction committee)
- [ ] **0001047469-13-010973:E0389** L1727-L1735 (date: May 30, 2013; actor: Board; terms: advisor, financial advisor, stockholder)
- [ ] **0001047469-13-010973:E0392** L1737-L1743 (date: May 30, 2013; actor: Board; terms: stockholder)
- [ ] **0001047469-13-010973:E0394** L1748-L1750 (date: May 31, 2013; actor: Board)
- [ ] **0001047469-13-010973:E0397** L1752-L1757 (date: June 12, 2013; actor: Board)
- [ ] **0001047469-13-010973:E0401** L1759-L1761 (date: June 21, 2013; actor: Party A; value: $17.00 to $19.00 per
share; terms: party )
- [ ] **0001047469-13-010973:E0403** L1763-L1780 (date: June 24, 2013; actor: Board; terms: special committee, stockholder, transaction committee)
- [ ] **0001047469-13-010973:E0405** L1785-L1794 (actor: Board; terms: special committee)
- [ ] **0001047469-13-010973:E0407** L1796-L1797 (date: May; actor: Special Committee; terms: special committee)
- [ ] **0001047469-13-010973:E0408** L1799-L1806 (actor: Special Committee; terms: special committee)
- [ ] **0001047469-13-010973:E0409** L1811-L1813 (actor: Party A; terms: party )
- [ ] **0001047469-13-010973:E0411** L1815-L1825 (date: June; actor: Party A; terms: bidder , party , special committee)
- [ ] **0001047469-13-010973:E0414** L1827-L1833 (date: June 28, 2013; actor: Party A; terms: party , special committee, transaction committee)
- [ ] **0001047469-13-010973:E0417** L1835-L1837 (date: June 28, 2013; actor: Party B; terms: party )
- [ ] **0001047469-13-010973:E0420** L1839-L1841 (date: June 30, 2013; actor: Party C; terms: party )
- [ ] **0001047469-13-010973:E0425** L1849-L1852 (date: July 6, 2013; actor: Special Committee; terms: special committee)
- [ ] **0001047469-13-010973:E0426** L1857-L1861 (actor: Special Committee; terms: special committee, stockholder)
- [ ] **0001047469-13-010973:E0431** L1867-L1870 (date: July 11, 2013; actor: Party B; terms: counsel, party )
- [ ] **0001047469-13-010973:E0437** L1875-L1877 (date: July 24, 2013; actor: Party B; value: $17.00 to $18.00 per share; terms: party )
- [ ] **0001047469-13-010973:E0439** L1879-L1887 (date: July 25, 2013; actor: Party B; terms: party , special committee)
- [ ] **0001047469-13-010973:E0440** L1889-L1896 (actor: Party A; terms: party , special committee)

### Process signals to check
- [ ] **0001047469-13-010973:E0357** L1628-L1631 (actor: Board; terms: strategic alternatives)
- [ ] **0001047469-13-010973:E0362** L1639-L1643 (date: April 5, 2013; actor: Party A; terms: strategic alternatives)
- [ ] **0001047469-13-010973:E0367** L1649-L1661 (date: May 9, 2013; actor: Party A; terms: strategic alternatives)
- [ ] **0001047469-13-010973:E0371** L1677-L1689 (date: November 2000; actor: Board; terms: strategic alternatives)
- [ ] **0001047469-13-010973:E0374** L1691-L1699 (date: May 10, 2013; actor: Transaction Committee; terms: strategic alternatives)
- [ ] **0001047469-13-010973:E0377** L1704-L1707 (date: May 14, 2013; actor: Transaction Committee; terms: strategic alternatives)
- [ ] **0001047469-13-010973:E0384** L1719-L1721 (date: May 22, 2013; actor: Transaction Committee; terms: strategic alternatives)
- [ ] **0001047469-13-010973:E0387** L1723-L1725 (date: May 29, 2013; actor: Transaction Committee; terms: strategic alternatives)
- [ ] **0001047469-13-010973:E0390** L1727-L1735 (date: May 30, 2013; actor: Board; terms: strategic alternatives)
- [ ] **0001047469-13-010973:E0395** L1748-L1750 (date: May 31, 2013; actor: Board; terms: strategic alternatives)
- [ ] **0001047469-13-010973:E0398** L1752-L1757 (date: June 12, 2013; actor: Board; terms: strategic alternatives)
- [ ] **0001047469-13-010973:E0404** L1763-L1780 (date: June 24, 2013; actor: Board; terms: strategic alternatives)
- [ ] **0001047469-13-010973:E0406** L1785-L1794 (actor: Board; terms: management presentation, strategic alternatives)
- [ ] **0001047469-13-010973:E0412** L1815-L1825 (date: June; actor: Party A; terms: confidentiality agreement, confidentiality and standstill, due diligence)
- [ ] **0001047469-13-010973:E0415** L1827-L1833 (date: June 28, 2013; actor: Party A; terms: due diligence)
- [ ] **0001047469-13-010973:E0418** L1835-L1837 (date: June 28, 2013; actor: Party B; terms: confidentiality and standstill, standstill)
- [ ] **0001047469-13-010973:E0421** L1839-L1841 (date: June 30, 2013; actor: Party C; terms: confidentiality and standstill, standstill)
- [ ] **0001047469-13-010973:E0423** L1843-L1847 (date: July 3, 2013; terms: confidentiality agreement)
- [ ] **0001047469-13-010973:E0427** L1857-L1861 (actor: Special Committee; terms: exclusivity)
- [ ] **0001047469-13-010973:E0429** L1863-L1865 (date: July 11, 2013; terms: confidentiality and standstill, standstill)
- [ ] **0001047469-13-010973:E0432** L1867-L1870 (date: July 11, 2013; actor: Party B; terms: confidentiality and standstill, standstill)
- [ ] **0001047469-13-010973:E0441** L1889-L1896 (actor: Party A; terms: due diligence)
</evidence_checklist>

<task_instructions>
IMPORTANT: You MUST follow the quote-before-extract protocol.

Step 1 - QUOTE: Read the chronology blocks above. For every passage that identifies an actor, copy the exact verbatim text into the quotes array. Each quote needs a unique quote_id (Q001, Q002, ...), the block_id it comes from, and the verbatim text.

Step 2 - EXTRACT: Build the actors array. Each actor references quote_ids from Step 1 instead of inline evidence. Do not include anchor_text or evidence_refs.

Return a single JSON object with: quotes, actors, count_assertions, unresolved_mentions. The quotes array MUST appear first.
</task_instructions>