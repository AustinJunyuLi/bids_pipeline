You are extracting filing-literal v2 observation artifacts from a single M&A chronology window.

Ground rules:
- The filing is the only source of truth.
- Quote before extract: every structured record must cite verbatim quote_ids.
- Extract only literal parties, cohorts, and observations.
- Do not emit analyst rows, benchmark rows, dropout labels, bid labels, or inferred outcomes beyond the schema fields explicitly supported below.

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

Examples:

- A launch of a sale process -> `process` with `process_kind: "sale_launch"`.
- A confidentiality agreement -> `agreement` with `agreement_kind: "nda"`.
- A request for best and final bids due on a later date -> `solicitation` with `due_date`.
- A price-bearing indication of interest -> `proposal` with `terms`.
- "Party X was no longer interested" -> `status` with `status_kind: "not_interested"`.
- "The merger agreement was executed" -> `outcome` with `outcome_kind: "executed"`.

<deal_context>
deal_slug: zep
target_name: ZEP INC
source_accession_number: 0001047469-15-004989
source_form_type: UNKNOWN
chunk_mode: single_pass
window_id: w0
</deal_context>

<chronology_blocks>
B001 [L1710-L1710]: Background of the Merger
B002 [L1712-L1713]: The following chronology summarizes material key events and contacts that led to the signing of the merger agreement. It does not purport to catalogue every conversation among our board of directors, members of our management or our representatives and other parties with respect to the merger.
B003 [L1715-L1715]: As
B004 [L1716-L1717]: part of the ongoing evaluation of our business, our board of directors and members of senior management periodically review and assess our business, operations and financial performance and industry and market conditions as they may impact our long-term strategic goals and plans, including the assessment of potential opportunities to maximize stockholder value.
B005 [L1719-L1719]: Over
B006 [L1720-L1723]: the past two years, in view of industry and market conditions, our business and financial performance, the complexities in the distribution channels and supply chain associated with our business, and the relatively limited trading volume of our stock, our board of directors focused on and considered potential strategic alternatives presented or available to us, as well as the opportunities and risks associated with our continuing to operate as an independent company. Alternatives reviewed included a return of capital to stockholders, business combinations, acquisitions, dispositions, internal restructurings and large-scale investments into our business to reduce complexities in our business model and our supply chain.
B007 [L1725-L1725]: At
B008 [L1726-L1726]: a June 20, 2013 meeting, our board of directors first discussed the possibility of exploring strategic alternatives, including a potential sale of the Company.
B009 [L1728-L1728]: At
B010 [L1729-L1733]: a July 1, 2013 meeting of our board of directors, Mr. John K. Morgan ("Mr. Morgan"), our President and Chief Executive Officer, summarized the discussions of our board of directors over the previous year regarding our strategic direction and position in the industry. Our board of directors unanimously agreed to proceed with certain initial steps related to exploring our strategic alternatives, including a potential sale of the Company. Our board of directors determined to appoint two members of our board of directors, Mr. Sidney J. Nurkin ("Mr. Nurkin") and Mr. Joseph Squicciarino ("Mr. Squicciarino"), to be directly involved in the oversight of the review of strategic alternatives and to update all members of our board of directors on a regular basis, as appropriate.
B011 [L1735-L1737]: Also, on July 1, 2013, Mr. Nurkin and Mr. Squicciarino, in their capacity as representatives of our board of directors, met with Mr. Morgan and our then general counsel to consider the engagement of a financial advisor to advise us in our consideration of strategic alternatives to maximize stockholder
B012 [L1739-L1739]: 27
B013 [L1742-L1743]: value. Following discussion, it was concluded that our board of directors should invite a number of investment banking firms to present their credentials to our full board of directors.
B014 [L1745-L1745]: Following
B015 [L1746-L1747]: the July 1, 2013 board meeting, Mr. Nurkin and Mr. Squicciarino, members of the Company's management and representatives from King & Spalding LLP ("King & Spalding"), legal counsel to the Company, conducted introductory discussions with representatives of BofA Merrill Lynch and three other investment banks.
B016 [L1749-L1749]: At
B017 [L1750-L1757]: an August 20, 2013 meeting of our board of directors, the Company's management provided our board of directors with a detailed review of the upcoming fiscal 2014 plan and a review of the expected results from fiscal 2013, including a comparison of our expected results with planned results for fiscal 2013. Both the fiscal 2013 information and the fiscal 2014 plan were discussed at length by our board of directors. For a portion of the meeting, our board of directors invited representatives of BofA Merrill Lynch and two other investment banks to give presentations regarding each firm's qualifications, including each firm's knowledge of our business and our industry, each firm's preliminary views regarding our company and the merits of, and considerations involved in, pursuing various strategic alternatives. Following the presentations and subsequent discussion, based on its view of the opportunities and potential value that could reasonably be expected from the successful implementation of the fiscal 2014 plan and the then current trading price of our stock, our board of directors concluded that it was not an appropriate time to explore strategic alternatives or engage a financial advisor, but that we should instead continue to focus on our business and financial performance, including planned cost-reduction measures, our fiscal 2013 fourth quarter performance and our execution of the fiscal 2014 plan.
B018 [L1759-L1759]: In
B019 [L1760-L1763]: the latter part of 2013, in light of the positive movement in the trading price of our stock (which our board of directors believed could position the Company to receive a higher price in connection with a potential transaction involving the Company), the Company's financial performance which was below expectations, and the recognition of the significant investment of resources and time necessary to reduce the complexities in the Company's distribution channels and supply chain, various members of our board of directors engaged in a number of informal conversations regarding the possibility of commencing a review of strategic alternatives.
B020 [L1765-L1765]: On
B021 [L1766-L1769]: January 7 and January 8, 2014, our board of directors held meetings. At this meeting, among other things, the Company's management updated our board of directors on business developments and discussed with our board of directors potential divestitures of certain of our products. After additional discussions of our business, our recent results of operations and, at the request of our board of directors, a market update presented by representatives of BofA Merrill Lynch, our board of directors met in executive session and concluded that it was timely to revisit the previously discussed exploration of strategic alternatives.
B022 [L1771-L1771]: Following
B023 [L1772-L1773]: the January 2014 board meetings, Mr. Nurkin and Mr. Squicciarino, as board representatives, continued discussions with representatives of BofA Merrill Lynch regarding their qualifications to advise us.
B024 [L1775-L1775]: At
B025 [L1776-L1781]: a January 28, 2014 board meeting, our board of directors discussed our year to date performance, our anticipated performance against the fiscal year 2014 plan and various factors that could impact our future performance. Following discussions, our board of directors decided to engage in a process to consider strategic alternatives. Our board of directors specifically focused on the anticipated increased revenue in the second half of fiscal year 2014, our overhead structure as a public company, the challenges of a company of our size in sourcing raw materials at competitive pricing, the complexity of our distribution channels, the relatively limited trading volume of our stock, our capital structure and the capital that would be needed to support investments, including investments with respect to our supply chain and distribution channels and acquisitions. Following such discussions, our board of directors unanimously approved an engagement letter with BofA Merrill Lynch providing for
B026 [L1783-L1783]: 28
B027 [L1786-L1786]: BofA
B028 [L1787-L1789]: Merrill Lynch to act as our financial advisor in connection with reviewing our strategic alternatives. Our board of directors also agreed that Mr. Nurkin and Mr. Squicciarino, as well as Mr. Timothy M. Manganello ("Mr. Manganello", and together with Mr. Nurkin and Mr. Squicciarino, the "Board Representatives"), each as independent directors, would be directly involved in the oversight of the process and would update our full board of directors on a regular basis, as appropriate.
B029 [L1791-L1791]: On
B030 [L1792-L1794]: January 31, 2014, the Board Representatives, together with Mr. Morgan and representatives of BofA Merrill Lynch, met to review and discuss the various strategic alternatives available to us. The Board Representatives discussed with representatives of BofA Merrill Lynch certain financial matters, including recent mergers and acquisitions activity both in the industry and more generally. The Board Representatives also discussed next steps for considering our strategic alternatives and the timing of those steps moving forward.
B031 [L1796-L1796]: During
B032 [L1797-L1798]: the next several weeks in February 2014, the Company's management prepared marketing materials in anticipation of the process launch that could be shared with potential buyers. Our board of directors also reviewed and discussed with representatives of BofA Merrill Lynch and King & Spalding a list of potential buyers to invite to meetings with our management.
B033 [L1800-L1800]: On
B034 [L1801-L1806]: February 25, 2014, the Board Representatives, together with members of the Company's management and representatives of BofA Merrill Lynch and King & Spalding, reviewed the marketing materials and a list of potential buyers of the Company, and discussed next steps in respect of a potential sale process. At the meeting, the Board Representatives discussed certain financial matters, including an overview of market and business conditions, investment highlights, our historical and projected financial data and a revised fiscal year 2014 forecast prepared by the Company's management. The Board Representatives discussed and considered the assumptions, risks and key drivers underlying the revised forecast. The Board Representatives and the Company's management also discussed and considered the nature and size of investments in organic sales growth, the reduction in complexity of, and transformation of, our supply chain that would be required to attain such projected results, the challenges associated with financing such investment, and the execution risks associated with such investments.
B035 [L1808-L1808]: At
B036 [L1809-L1815]: a February 27, 2014 board meeting, our board of directors, together with members of the Company's management and representatives of BofA Merrill Lynch and King & Spalding, reviewed steps taken to date in connection with the review of strategic alternatives. Our board of directors considered preliminary and illustrative financial aspects of a potential transaction, including stockholder value and the potential cost savings associated with a transaction. During these discussions, the Company's management emphasized the existence of potential cost savings as a result of a transaction for potential buyers who could reconfigure our supply chain, eliminate public company costs and eliminate corporate and shared services costs. Our board of directors discussed the list of potential buyers and the desire to conduct the process in a way that would most effectively maximize stockholder value. Our board of directors unanimously approved moving forward with next steps, including contacting the potential buyers on the list discussed by our board of directors, executing confidentiality agreements with such parties and conducting meetings with such parties.
B037 [L1817-L1817]: During
B038 [L1818-L1821]: the next several weeks, BofA Merrill Lynch, at the direction of our board of directors, contacted fifty potential buyers (comprising twenty-eight strategic buyers and twenty-two financial buyers, including financial buyers who owned businesses similar to our businesses), and we executed confidentiality agreements with a number of the potential buyers. Each of the confidentiality agreements included employee non-solicitation provisions and a customary "standstill" provision, including a "don't ask to waive" provision. Members of the Company's management and, at the direction of our board of directors, representatives of BofA Merrill Lynch met with prospective buyers to discuss the Company's business and a potential transaction.
B039 [L1823-L1823]: 29
B040 [L1826-L1829]: During the first weeks of March 2014, BofA Merrill Lynch, at the direction of our board of directors, continued to communicate with potential buyers and to regularly provide the Board Representatives with updates with respect to a potential transaction. One of the financial buyers contacted during such time was New Mountain Capital. We entered into a confidentiality agreement with New Mountain Capital on March 19, 2014. On March 20, 2014, management delivered the marketing materials and held an introductory meeting with representatives of New Mountain Capital.
B041 [L1831-L1831]: On
B042 [L1832-L1835]: March 25 and March 26, 2014, our board of directors held meetings at which the Company's management reported on our business and recent financial performance. Our board of directors discussed the potential sale process with representatives of BofA Merrill Lynch and King & Spalding. The Board Representatives, the Company's management and, at the request of our board of directors, representatives of BofA Merrill Lynch provided an update on the potential sale process, including communications with potential buyers, since the last meeting of our board of directors, and our board of directors engaged in a general discussion regarding the potential sale process, including a discussion of next steps.
B043 [L1837-L1837]: On
B044 [L1838-L1843]: March 27, 2014, at the direction of our board of directors, BofA Merrill Lynch distributed a first round process letter, which informed potential buyers that non-binding preliminary indications of interest would be due no later than April 14, 2014. Over the next few weeks, BofA Merrill Lynch, at the direction of our board of directors, continued communications with potential buyers to assess interest in a potential transaction and provide information, and the Company's management continued to meet with prospective buyers. In all, twenty-five potential buyers informed us that they were not interested in pursuing a potential transaction and declined to enter into a confidentiality agreement with us, and twenty-five potential buyers executed confidentiality agreements with us, received a copy of the marketing materials and/or met with the Company's management. While New Mountain Capital received the marketing materials and the first round process letter, it decided at the time not to submit a preliminary indication of interest.
B045 [L1845-L1845]: On
B046 [L1846-L1848]: April 14, 2014, five parties, comprising four financial buyers and one strategic buyer, submitted preliminary and non-binding indications of interest. The bids received in the preliminary indications of interest ranged from $20.00 per share to $22.00 per share. The Board Representatives reviewed the indications of interest as well as recent progress in the potential sale process.
B047 [L1850-L1850]: On
B048 [L1851-L1853]: April 16, 2014, our board of directors held a meeting in which members of the Company's management, representatives of BofA Merrill Lynch and King & Spalding joined, to review the preliminary indications of interest and the potential sale process. Our board of directors reviewed the five preliminary indications of interest that had been received. After further discussion, our board of directors determined to continue the process with the parties who had submitted preliminary indications of interest.
B049 [L1855-L1855]: Over
B050 [L1856-L1858]: the next few weeks, the Company's management gathered information that was to be included in the electronic data room and held internal meetings to prepare for in-depth management presentations with the interested parties. Moreover, two additional parties, comprising one financial party ("Party X") and one strategic party ("Party Y"), contacted representatives of BofA Merrill Lynch on an unsolicited basis to inquire about the process.
B051 [L1860-L1860]: On
B052 [L1861-L1863]: May 7, 2014, access to an electronic data room containing diligence materials was made available to the five parties who submitted preliminary indications of interest to that point and these parties engaged in extensive due diligence investigations of our business. As part of this process, in the first half of May 2014, the Company's management met with certain of these parties and provided presentations to them about our business.
B053 [L1865-L1865]: On
B054 [L1866-L1867]: May 9, 2014, Party X submitted a preliminary and non-binding indication of interest to BofA Merrill Lynch, increasing the number of preliminary indications of interest received by us as of such date to six. The bid submitted by Party X ranged from $21.50 to $23.00 per share. However, on
B055 [L1869-L1869]: 30
B056 [L1872-L1874]: May 14, 2014, prior to receiving access to the electronic data room or meeting with the Company's management, Party X informed representatives of BofA Merrill Lynch that it was no longer interested in pursuing a potential transaction with the Company.
B057 [L1876-L1876]: On
B058 [L1877-L1879]: May 20, 2014, Party Y submitted a preliminary and non-binding indication of interest, bringing the total number of preliminary indications of interest received by us to seven. The indication of interest submitted by Party Y ranged from $19.50 to $20.50 per share. Access to the electronic data room was subsequently made available to Party Y and the Company's management met with Party Y and provided a presentation about our business.
B059 [L1881-L1881]: On
B060 [L1882-L1883]: May 22, 2014, a draft of the merger agreement was distributed to the six remaining bidders (Party X having withdrawn from the process on May 14, 2014) that had submitted preliminary indications of interest.
B061 [L1885-L1885]: On
B062 [L1886-L1887]: May 23, 2014, there was a fire at our aerosol manufacturing facility in Marietta, Georgia. The fire, and its impact on our business, added significant uncertainty to our on-going discussions with the interested parties.
B063 [L1889-L1889]: Over
B064 [L1890-L1892]: the next few weeks, five of the remaining six interested parties communicated to representatives of BofA Merrill Lynch that they were unable to proceed with the process due to concerns regarding valuation and, in some cases, the interested parties' own internal initiatives and strategic priorities. The sixth remaining interested party declined to respond to BofA Merrill Lynch's communications regarding a potential transaction.
B065 [L1894-L1894]: On
B066 [L1895-L1902]: June 19, 2014, the Board Representatives held a meeting which included other members of our board of directors, the Company's management and representatives from BofA Merrill Lynch and King & Spalding. The Board Representatives and other members of our board of directors were informed that each of the seven parties that submitted a preliminary indication of interest had expressed concerns regarding valuation and believed that they could not pay the prices indicated in their preliminary indications of interest. During this meeting, the Board Representatives considered that five of the remaining six interested parties had communicated that they were unable to proceed with the process due to concerns regarding valuation and, in some cases, the interested parties' own internal initiatives and strategic priorities and that a sixth interested party was no longer responding to BofA Merrill Lynch's communications regarding a potential transaction. The Board Representatives also considered that, based upon BofA Merrill Lynch's discussions with the interested parties, the interested parties recognized the opportunity to achieve potential cost savings, but the complexity and nature of these potential cost savings and the requisite related investments made the interested parties unwilling to give us full credit for these potential cost savings in their valuations.
B067 [L1904-L1904]: At
B068 [L1905-L1907]: a June 26, 2014 meeting of our board of directors, based on the lack of buyer interest and the uncertainty surrounding the impact of the fire at our aerosol manufacturing facility in Marietta, Georgia, our board of directors decided to terminate the process to explore potential strategic alternatives at that time and to continue to focus on our business and financial performance.
B069 [L1909-L1909]: During
B070 [L1910-L1915]: the process conducted during the first half of 2014, given that all of the parties that had signed confidentiality agreements had abandoned or withdrawn from the process, our board of directors authorized letters to be delivered to those parties waiving the "don't ask to waive" provisions in their respective confidentiality agreements, and permitting those parties to make confidential proposals to acquire the Company. As a result, following the termination of the process, no party was subject to a "don't ask to waive" provision or prohibited from making confidential acquisition proposals to the board of directors of the Company. After the termination of the 2014 potential sale process and prior to the signing of the merger agreement with New Mountain Capital, we did not receive any inquiries or proposals to acquire the Company (other than from New Mountain Capital as further described below), but instead received occasional inquiries from third parties regarding our interest in their providing minority PIPE ("private investment in public equity") financing.
B071 [L1917-L1917]: 31
B072 [L1920-L1920]: In
B073 [L1921-L1922]: the second half of 2014, our board of directors and management focused on our business and our Company's business plan, including addressing the impact on our aerosol business, completing our fiscal year 2015 plan and focusing on fiscal year 2014 performance.
B074 [L1924-L1924]: In
B075 [L1925-L1928]: early February 2015, New Mountain Capital contacted representatives of BofA Merrill Lynch and requested a meeting. On February 10, 2015, New Mountain Capital met with representatives of BofA Merrill Lynch and expressed its interest in discussions with the Company regarding a potential transaction. On February 19, 2015, New Mountain Capital delivered an unsolicited indication of interest to the Company to acquire us for a per share price of $19.25. The indication of interest was supported by a highly confident financing letter from Jefferies Finance LLC, contained a request for a forty-five day exclusivity period and contemplated a "go-shop" period following the signing of any definitive merger agreement.
B076 [L1930-L1930]: On
B077 [L1931-L1939]: February 23, 2015, our board of directors, together with representatives of BofA Merrill Lynch and King & Spalding, met to discuss New Mountain Capital's indication of interest. Our board of directors discussed the indication of interest, including the proposed per share price, the request for exclusivity and the offer to include a "go shop" provision in any definitive merger agreement. Our board of directors reviewed and discussed the advantages and disadvantages of various potential alternatives, including continuing to operate on a standalone basis and investing in a supply chain transformation project, pursuing a potential transaction with New Mountain Capital on an exclusive basis combined with a "go-shop" provision in the merger agreement, contacting a select group of potential buyers, and conducting a broad process to explore a potential sale of the Company. As part of these discussions, our board of directors reviewed the impact and distractions on our business associated with the 2014 potential sale process and emphasized the importance of limiting any distractions that might be associated with pursuing another potential sale of the Company. After further discussion, our board of directors concluded that it would consider granting New Mountain Capital a thirty day exclusivity period if New Mountain Capital raised its offer price and confirmed that a "go-shop" provision would be included in any potential definitive merger agreement.
B078 [L1941-L1941]: On
B079 [L1942-L1946]: February 24, 2015, at the direction of our board of directors, representatives of BofA Merrill Lynch communicated to New Mountain Capital that our board of directors might be willing to consider granting New Mountain Capital a thirty day exclusivity period if New Mountain Capital raised its offer price and confirmed that a "go-shop" provision would be included in any potential definitive merger agreement. On February 26, 2015, New Mountain Capital delivered a revised indication of interest reflecting an increased per share price of $20.05, and indicated that this was the highest price it was willing to offer. As part of its submission of the revised indication of interest, New Mountain Capital again requested a forty-five day exclusivity period (and contemplated a countersignature by the Company), and reiterated that it would be willing to accept a "go-shop" provision in any definitive merger agreement.
B080 [L1948-L1948]: On
B081 [L1949-L1955]: February 26, 2015, our board of directors met, together with representatives of BofA Merrill Lynch and King & Spalding, to review New Mountain Capital's revised indication of interest. Our board of directors discussed and considered the fact that New Mountain Capital was not prepared to move forward in its evaluation of a potential transaction with us without an exclusivity agreement. Our board of directors also considered the fact that New Mountain Capital was unwilling to further increase its indicative price above $20.05 per share at this time. Our board of directors discussed at length the potential strategic alternatives available to the Company, including remaining as a standalone company. Our board of directors also considered again the importance of limiting any distractions that might be associated with pursuing another potential sale of the Company. After further deliberation regarding the potential advantages and disadvantages of a sale of the Company and consideration of the opportunities and risks associated with remaining a standalone company, our board of directors determined to move forward with negotiations with New Mountain Capital regarding the proposed sale of the Company. In view of the increased offer price, the commitment by New Mountain Capital to
B082 [L1957-L1957]: 32
B083 [L1960-L1963]: include a "go-shop" provision in any potential definitive merger agreement and the other considerations described above, our board of directors determined that it would be willing to offer to New Mountain Capital an exclusivity period of approximately thirty days. Our board of directors also determined not to form a transaction committee because the full board would remain actively involved in overseeing the negotiations with New Mountain Capital.
B084 [L1965-L1965]: On
B085 [L1966-L1967]: February 27, 2015, we signed an agreement with New Mountain Capital extending the term of the confidentiality provision, the "standstill" provision and the employee non-solicitation provision in our original confidentiality agreement with them as well as providing for an exclusivity period with New Mountain Capital through March 31, 2015.
B086 [L1969-L1969]: On
B087 [L1970-L1973]: March 2, 2015, we granted New Mountain Capital access to the electronic data room that had been populated with due diligence documentation during the 2014 potential sale process. Pursuant to the instruction of our board of directors, BofA Merrill Lynch asked New Mountain Capital to confirm its offer price after reviewing the due diligence materials. Over the next few weeks, New Mountain Capital requested additional information, and the Company's management provided this information and updated the electronic data room in response to these requests. New Mountain Capital and their representatives and advisors reviewed the contents of the electronic data room, including our fiscal year 2015 plan and an updated fiscal year 2015 forecast.
B088 [L1975-L1975]: Throughout
B089 [L1976-L1978]: March 2015, the Company's management (including Mr. Morgan) participated in various in-person due diligence meetings with New Mountain Capital and hosted New Mountain Capital on multiple site visits to the Company's facilities. During these meetings, the Company's management discussed with New Mountain various aspects of our business and prospects, including our business plan and potential initiatives.
B090 [L1980-L1980]: On
B091 [L1981-L1983]: March 13, 2015, New Mountain Capital communicated that the $20.05 per share offer price was New Mountain Capital's "best and final" offer. New Mountain Capital also indicated a willingness to work expeditiously towards the signing of a definitive merger agreement by April 15, 2015 and requested an extension of its exclusivity period through that date. Subsequently, on March 15, 2015, New Mountain Capital indicated that it would accelerate its due diligence process and requested that the exclusivity period be extended through April 7, 2015.
B092 [L1985-L1985]: On
B093 [L1986-L1992]: March 16, 2015, our board of directors met, together with representatives of BofA Merrill Lynch and King & Spalding, to discuss the status of the discussions with New Mountain Capital. At this meeting, at the request of our board of directors, representatives of BofA Merrill Lynch, reviewed and discussed with our board of directors, on a preliminary basis, certain financial matters. Our board of directors also discussed our recent financial performance and our business on a standalone basis, including the opportunities, risks and capital investment associated with transforming our supply chain. Our board of directors also reviewed the progress with New Mountain Capital and the recent discussions with New Mountain Capital, including New Mountain Capital's request to extend the exclusivity period. After further discussion, based upon progress in negotiations with New Mountain Capital and New Mountain Capital's reiteration that any definitive merger agreement would contain a "go-shop" provision, our board of directors authorized an extension of exclusivity with New Mountain Capital through April 7, 2015, which extension letter was signed on March 18, 2015.
B094 [L1994-L1994]: On
B095 [L1995-L1997]: March 18, 2015, a draft merger agreement was delivered to New Mountain Capital and its advisors. The draft merger agreement included, among other terms, a "go-shop" provision permitting us to solicit alternative acquisition proposals for sixty days after signing the merger agreement, and the draft agreement permitted us to terminate the merger agreement in order to accept a superior offer from another potential buyer.
B096 [L1999-L1999]: On
B097 [L2000-L2001]: March 24, 2015, our board of directors reviewed again the opportunities, risks and investment associated with transforming our supply chain. After further discussion, our board of directors determined not to proceed with an investment in a supply chain transformation project due to
B098 [L2003-L2003]: 33
B099 [L2006-L2007]: execution risk and resource constraints, and decided to continue discussions with New Mountain Capital.
B100 [L2009-L2009]: On
B101 [L2010-L2014]: March 29, 2015, we received a revised draft of the merger agreement from New Mountain Capital. Among other things, the revised merger agreement reduced the "go-shop" period from sixty days to thirty days. During the week of March 30, 2015, we engaged in a series of negotiations with New Mountain Capital and its advisors regarding the provisions the merger agreement, including negotiations regarding the terms of the "go-shop" and "no-shop" provisions (including the length of the "go-shop" period), our ability to consider alternative proposals, the size of the termination fees and circumstances under which termination fees would be payable, representations and warranties, pre-closing conduct of business covenants, and conditions to closing. In addition, we negotiated the terms of other agreements relating to the proposed transaction, including the debt commitment letter, equity commitment letter and limited guaranty.
B102 [L2016-L2016]: As
B103 [L2017-L2019]: negotiations of the merger agreement continued into April, at the direction of our board of directors, both Mr. Morgan and representatives of BofA Merrill Lynch separately approached New Mountain Capital in an effort to negotiate an increase in the $20.05 per share offer price. New Mountain Capital reiterated its previous position that the $20.05 per share price offer was New Mountain Capital's "best and final" offer.
B104 [L2021-L2031]: On April 6, 2015, our board of directors met, together with members of the Company's management and representatives of BofA Merrill Lynch and King & Spalding, to consider the proposed transaction with New Mountain Capital. At this meeting, at the request of our board of directors, representatives of BofA Merrill Lynch reviewed and discussed with our board of directors certain financial matters, including the financial analyses of the merger consideration. The board of directors considered these financial matters with reference to the price proposed by New Mountain Capital in connection with the proposed transaction. In so doing, our board of directors took into account its understanding that New Mountain Capital's offer price of $20.05 per share was, in fact, the highest and best price New Mountain Capital was willing to pay for the Company. In addition, representatives of King & Spalding reviewed the terms of the draft merger agreement and other transaction documents, including the debt and equity commitment letters relating to the proposed transaction. In connection with this review, King & Spalding discussed with the board remaining open issues in the merger agreement, including the terms of the "go-shop" provision and the size of the termination fees. Our board of directors was advised that New Mountain Capital continued to insist on a thirty day "go-shop" period, a go-shop termination fee of $10 million, a termination fee following the end of the go-shop period of $20 million and a reverse termination fee payable by New Mountain Capital of $30 million. Our board of directors engaged in discussions regarding the materials presented at the meeting and the proposed transaction. At the end of the meeting, our board of directors instructed the Company's advisors to proceed to finalize the merger agreement on as favorable terms as possible to the Company.
B105 [L2033-L2033]: Following
B106 [L2034-L2038]: the April 6, 2015 board meeting, representatives of King & Spalding continued to negotiate the final terms of the merger agreement with New Mountain Capital's advisors. New Mountain Capital expressed its willingness to agree to the Company's proposal that the go-shop termination fee be limited to $8.75 million, that the termination fee following the end of the go-shop period be limited to $17.5 million and that the reverse termination fee payable by New Mountain Capital be $33.75 million. However, although New Mountain Capital was willing to provide additional time following the go-shop period to permit the Company to negotiate with respect to potential superior proposals arising during the go-shop period, New Mountain Capital insisted that it was unwilling to increase the length of the go-shop period beyond thirty days.
B107 [L2040-L2040]: On
B108 [L2041-L2042]: April 7, 2015, our board of directors met again, together with members of the Company's management and representatives of BofA Merrill Lynch and King & Spalding, to discuss and review the transaction documents and to consider approval of the proposed transaction with New Mountain
B109 [L2044-L2044]: 34
B110 [L2047-L2047]: Capital.
B111 [L2048-L2057]: Representatives of King & Spalding reviewed the key provisions of the merger agreement, and discussed with our board of directors the negotiations with New Mountain Capital with respect to the key remaining issues, including the length of the "go-shop" provision and the size of the termination fees. After taking into account (a) the robust process conducted in the first half of 2014, (b) the fact that the Company did not receive any acquisition proposals other than from New Mountain Capital since the termination of the 2014 process, (c) the ability of the Company to promptly initiate a go-shop process especially in view of the prior 2014 process and (d) New Mountain Capital's willingness to agree to the Company's proposals regarding the size of the termination fees, our board of directors was willing to accept a thirty day "go-shop" period. Also at this meeting, our board of directors reviewed with BofA Merrill Lynch the financial analyses of the merger consideration and BofA Merrill Lynch delivered to our board of directors an oral opinion, which was confirmed by delivery of a written opinion dated April 7, 2015, to the effect that, as of that date and based upon and subject to the assumptions made, procedures followed, factors considered and limitations on the review undertaken, as described in its opinion, the merger consideration to be received by our holders of common stock was fair, from a financial point of view, to such holders. Following discussion, our board of directors unanimously determined that the merger agreement and the transactions contemplated thereby, including the merger, were advisable and in the best interests of our stockholders and the Company, and our board of directors resolved to recommend that our stockholders approve the adoption of the merger agreement.
B112 [L2059-L2059]: Following
B113 [L2060-L2061]: the meeting of our board of directors, the parties executed the merger agreement and the related transaction documents and issued a press release announcing the transaction on the morning of April 8, 2015.
B114 [L2063-L2069]: Under the merger agreement, during the "go-shop period" that began on the date of the merger agreement and continued until 11:59 p. m., New York City time, on May 7, 2015, we and our subsidiaries and our respective representatives were permitted to, directly or indirectly, solicit, initiate, facilitate and encourage proposals relating to certain alternative transactions, including by providing access to non-public information relating to us and our subsidiaries pursuant to an acceptable confidentiality agreement, and to enter into and maintain or continue discussions or negotiations with respect to potential acquisition proposals. Representatives of BofA Merrill Lynch commenced the go-shop process on our behalf on April 8, 2015. During the go-shop process, representatives of BofA Merrill Lynch contacted a total of fifty-eight parties (including potential strategic and financial buyers) regarding each such party's interest in exploring a transaction with us. As of the end of the go-shop period, none of the parties contacted during the go-shop process had submitted a competing acquisition proposal to us or our representatives, and no such party remained engaged in discussions or negotiations with us or our representatives with respect to a potential acquisition proposal.
</chronology_blocks>

<evidence_checklist>
### Dated actions to extract
- [ ] **0001047469-15-004989:E0368** L1725-L1726 (date: June 20, 2013; terms: discussed, meeting)
- [ ] **0001047469-15-004989:E0370** L1728-L1733 (date: July 1, 2013; actor: K. Morgan; terms: meeting)
- [ ] **0001047469-15-004989:E0373** L1735-L1737 (date: July 1, 2013; actor: Mr. Morgan; terms: met, sent)
- [ ] **0001047469-15-004989:E0377** L1745-L1747 (date: July 1, 2013; actor: Merrill Lynch; terms: meeting, sent)
- [ ] **0001047469-15-004989:E0379** L1749-L1757 (date: August 20, 2013; actor: Merrill Lynch; terms: discussed, meeting, sent)
- [ ] **0001047469-15-004989:E0383** L1765-L1769 (date: January; actor: Merrill Lynch; terms: discussed, meeting, met)
- [ ] **0001047469-15-004989:E0386** L1771-L1773 (date: January 2014; actor: Merrill Lynch; terms: meeting, sent)
- [ ] **0001047469-15-004989:E0388** L1775-L1781 (date: January 28, 2014; actor: Merrill Lynch; terms: discussed, meeting)
- [ ] **0001047469-15-004989:E0393** L1791-L1794 (date: January 31, 2014; actor: Board; terms: discussed, met, sent)
- [ ] **0001047469-15-004989:E0396** L1796-L1798 (date: February 2014; actor: Merrill Lynch; terms: discussed, meeting, sent)
- [ ] **0001047469-15-004989:E0398** L1800-L1806 (date: February 25, 2014; actor: Board; terms: discussed, meeting, sent)
- [ ] **0001047469-15-004989:E0400** L1808-L1815 (date: February 27, 2014; actor: Merrill Lynch; terms: discussed, meeting, sent)
- [ ] **0001047469-15-004989:E0406** L1826-L1829 (date: March 2014; actor: Board; terms: contacted, delivered, entered into)
- [ ] **0001047469-15-004989:E0409** L1831-L1835 (date: March; actor: Board; terms: discussed, engaged, meeting)
- [ ] **0001047469-15-004989:E0411** L1837-L1843 (date: March 27, 2014; actor: Merrill Lynch; terms: declined, executed, met)
- [ ] **0001047469-15-004989:E0415** L1845-L1848 (date: April 14, 2014; actor: Board; value: $20.00 per share; terms: received, sent, submitted)
- [ ] **0001047469-15-004989:E0418** L1850-L1853 (date: April 16, 2014; actor: Merrill Lynch; terms: meeting, received, sent)
- [ ] **0001047469-15-004989:E0422** L1860-L1863 (date: May 7, 2014; terms: engaged, met, sent)
- [ ] **0001047469-15-004989:E0424** L1865-L1867 (date: May 9, 2014; actor: Party X; value: $21.50 to $23.00 per share; terms: received, submitted)
- [ ] **0001047469-15-004989:E0427** L1872-L1874 (date: May 14,
2014; actor: Party X; terms: meeting, sent)
- [ ] **0001047469-15-004989:E0429** L1876-L1879 (date: May 20, 2014; actor: Party Y; value: $19.50 to $20.50 per share; terms: met, received, sent)
- [ ] **0001047469-15-004989:E0432** L1881-L1883 (date: May 22, 2014; actor: Party X; terms: submitted)
- [ ] **0001047469-15-004989:E0436** L1894-L1902 (date: June 19, 2014; actor: Board; terms: meeting, sent, submitted)
- [ ] **0001047469-15-004989:E0438** L1904-L1907 (date: June 26, 2014; terms: meeting)
- [ ] **0001047469-15-004989:E0443** L1924-L1928 (date: early February 2015; actor: Merrill Lynch; value: $19.25; terms: contacted, delivered, meeting)
- [ ] **0001047469-15-004989:E0448** L1930-L1939 (date: February 23, 2015; actor: Merrill Lynch; terms: discussed, met, offer)
- [ ] **0001047469-15-004989:E0452** L1941-L1946 (date: February 24, 2015; actor: Merrill Lynch; value: $20.05; terms: delivered, offer, requested)
- [ ] **0001047469-15-004989:E0457** L1948-L1955 (date: February 26, 2015; actor: Merrill Lynch; value: $20.05 per share; terms: discussed, met, offer)
- [ ] **0001047469-15-004989:E0464** L1965-L1967 (date: February 27, 2015; terms: signed)
- [ ] **0001047469-15-004989:E0466** L1969-L1973 (date: March 2, 2015; actor: Merrill Lynch; terms: offer, requested, sent)
- [ ] **0001047469-15-004989:E0469** L1975-L1978 (date: March 2015; actor: Mr. Morgan; terms: discussed, meeting)
- [ ] **0001047469-15-004989:E0472** L1980-L1983 (date: March 13, 2015; value: $20.05 per share; terms: offer, requested)
- [ ] **0001047469-15-004989:E0476** L1985-L1992 (date: March 16, 2015; actor: Merrill Lynch; terms: authorized, discussed, meeting)
- [ ] **0001047469-15-004989:E0480** L1994-L1997 (date: March 18, 2015; terms: delivered, offer, proposal)
- [ ] **0001047469-15-004989:E0484** L2009-L2014 (date: March 29, 2015; terms: engaged, proposal, proposed)
- [ ] **0001047469-15-004989:E0488** L2016-L2019 (date: April; actor: Mr. Morgan; value: $20.05 per share; terms: offer, sent)
- [ ] **0001047469-15-004989:E0493** L2021-L2031 (date: April 6, 2015; actor: Merrill Lynch; value: $20.05 per share; terms: discussed, engaged, meeting)
- [ ] **0001047469-15-004989:E0498** L2033-L2038 (date: April 6, 2015; value: $8.75; terms: meeting, proposal, sent)
- [ ] **0001047469-15-004989:E0503** L2040-L2042 (date: April 7, 2015; actor: Merrill Lynch; terms: met, proposed, sent)
- [ ] **0001047469-15-004989:E0505** L2047-L2057 (date: April 7, 2015; actor: Merrill Lynch; terms: delivered, discussed, meeting)
- [ ] **0001047469-15-004989:E0509** L2059-L2061 (date: April 8, 2015; terms: executed, meeting)
- [ ] **0001047469-15-004989:E0511** L2063-L2069 (date: May 7, 2015; actor: Merrill Lynch; terms: contacted, engaged, proposal)

### Financial terms to capture
- [ ] **0001047469-15-004989:E0416** L1845-L1848 (date: April 14, 2014; actor: Board; value: $20.00 per share; terms: $20.00 per share, $22.00 per share)
- [ ] **0001047469-15-004989:E0425** L1865-L1867 (date: May 9, 2014; actor: Party X; value: $21.50 to $23.00 per share; terms: $21.50 to $23.00 per share)
- [ ] **0001047469-15-004989:E0430** L1876-L1879 (date: May 20, 2014; actor: Party Y; value: $19.50 to $20.50 per share; terms: $19.50 to $20.50 per share)
- [ ] **0001047469-15-004989:E0444** L1924-L1928 (date: early February 2015; actor: Merrill Lynch; value: $19.25; terms: $19.25)
- [ ] **0001047469-15-004989:E0453** L1941-L1946 (date: February 24, 2015; actor: Merrill Lynch; value: $20.05; terms: $20.05)
- [ ] **0001047469-15-004989:E0458** L1948-L1955 (date: February 26, 2015; actor: Merrill Lynch; value: $20.05 per share; terms: $20.05 per share)
- [ ] **0001047469-15-004989:E0473** L1980-L1983 (date: March 13, 2015; value: $20.05 per share; terms: $20.05 per share)
- [ ] **0001047469-15-004989:E0489** L2016-L2019 (date: April; actor: Mr. Morgan; value: $20.05 per share; terms: $20.05 per share)
- [ ] **0001047469-15-004989:E0494** L2021-L2031 (date: April 6, 2015; actor: Merrill Lynch; value: $20.05 per share; terms: $10, $20, $20.05 per share)
- [ ] **0001047469-15-004989:E0499** L2033-L2038 (date: April 6, 2015; value: $8.75; terms: $17.5, $33.75, $8.75)

### Actors to identify
- [ ] **0001047469-15-004989:E0365** L1715-L1717 (date: may; terms: stockholder)
- [ ] **0001047469-15-004989:E0366** L1719-L1723 (terms: stockholder)
- [ ] **0001047469-15-004989:E0371** L1728-L1733 (date: July 1, 2013; actor: K. Morgan)
- [ ] **0001047469-15-004989:E0374** L1735-L1737 (date: July 1, 2013; actor: Mr. Morgan; terms: advisor, counsel, financial advisor)
- [ ] **0001047469-15-004989:E0376** L1742-L1743 (terms: investment bank)
- [ ] **0001047469-15-004989:E0378** L1745-L1747 (date: July 1, 2013; actor: Merrill Lynch; terms: counsel, investment bank)
- [ ] **0001047469-15-004989:E0380** L1749-L1757 (date: August 20, 2013; actor: Merrill Lynch; terms: advisor, financial advisor, investment bank)
- [ ] **0001047469-15-004989:E0384** L1765-L1769 (date: January; actor: Merrill Lynch)
- [ ] **0001047469-15-004989:E0387** L1771-L1773 (date: January 2014; actor: Merrill Lynch)
- [ ] **0001047469-15-004989:E0389** L1775-L1781 (date: January 28, 2014; actor: Merrill Lynch)
- [ ] **0001047469-15-004989:E0391** L1786-L1789 (actor: Board; terms: advisor, financial advisor)
- [ ] **0001047469-15-004989:E0394** L1791-L1794 (date: January 31, 2014; actor: Board)
- [ ] **0001047469-15-004989:E0397** L1796-L1798 (date: February 2014; actor: Merrill Lynch)
- [ ] **0001047469-15-004989:E0399** L1800-L1806 (date: February 25, 2014; actor: Board)
- [ ] **0001047469-15-004989:E0401** L1808-L1815 (date: February 27, 2014; actor: Merrill Lynch; terms: stockholder)
- [ ] **0001047469-15-004989:E0403** L1817-L1821 (actor: Merrill Lynch)
- [ ] **0001047469-15-004989:E0407** L1826-L1829 (date: March 2014; actor: Board)
- [ ] **0001047469-15-004989:E0410** L1831-L1835 (date: March; actor: Board)
- [ ] **0001047469-15-004989:E0412** L1837-L1843 (date: March 27, 2014; actor: Merrill Lynch)
- [ ] **0001047469-15-004989:E0417** L1845-L1848 (date: April 14, 2014; actor: Board; value: $20.00 per share)
- [ ] **0001047469-15-004989:E0419** L1850-L1853 (date: April 16, 2014; actor: Merrill Lynch)
- [ ] **0001047469-15-004989:E0420** L1855-L1858 (actor: Party X; terms: party )
- [ ] **0001047469-15-004989:E0426** L1865-L1867 (date: May 9, 2014; actor: Party X; value: $21.50 to $23.00 per share; terms: party )
- [ ] **0001047469-15-004989:E0428** L1872-L1874 (date: May 14,
2014; actor: Party X; terms: party )
- [ ] **0001047469-15-004989:E0431** L1876-L1879 (date: May 20, 2014; actor: Party Y; value: $19.50 to $20.50 per share; terms: party )
- [ ] **0001047469-15-004989:E0433** L1881-L1883 (date: May 22, 2014; actor: Party X; terms: party )
- [ ] **0001047469-15-004989:E0435** L1889-L1892 (actor: Merrill Lynch; terms: party )
- [ ] **0001047469-15-004989:E0437** L1894-L1902 (date: June 19, 2014; actor: Board; terms: party )
- [ ] **0001047469-15-004989:E0440** L1909-L1915 (terms: party )
- [ ] **0001047469-15-004989:E0445** L1924-L1928 (date: early February 2015; actor: Merrill Lynch; value: $19.25)
- [ ] **0001047469-15-004989:E0449** L1930-L1939 (date: February 23, 2015; actor: Merrill Lynch)
- [ ] **0001047469-15-004989:E0454** L1941-L1946 (date: February 24, 2015; actor: Merrill Lynch; value: $20.05)
- [ ] **0001047469-15-004989:E0459** L1948-L1955 (date: February 26, 2015; actor: Merrill Lynch; value: $20.05 per share)
- [ ] **0001047469-15-004989:E0461** L1960-L1963 (terms: transaction committee)
- [ ] **0001047469-15-004989:E0467** L1969-L1973 (date: March 2, 2015; actor: Merrill Lynch; terms: advisor, advisors)
- [ ] **0001047469-15-004989:E0470** L1975-L1978 (date: March 2015; actor: Mr. Morgan)
- [ ] **0001047469-15-004989:E0477** L1985-L1992 (date: March 16, 2015; actor: Merrill Lynch)
- [ ] **0001047469-15-004989:E0481** L1994-L1997 (date: March 18, 2015; terms: advisor, advisors)
- [ ] **0001047469-15-004989:E0485** L2009-L2014 (date: March 29, 2015; terms: advisor, advisors)
- [ ] **0001047469-15-004989:E0490** L2016-L2019 (date: April; actor: Mr. Morgan; value: $20.05 per share)
- [ ] **0001047469-15-004989:E0495** L2021-L2031 (date: April 6, 2015; actor: Merrill Lynch; value: $20.05 per share; terms: advisor, advisors)
- [ ] **0001047469-15-004989:E0500** L2033-L2038 (date: April 6, 2015; value: $8.75; terms: advisor, advisors)
- [ ] **0001047469-15-004989:E0504** L2040-L2042 (date: April 7, 2015; actor: Merrill Lynch)
- [ ] **0001047469-15-004989:E0506** L2047-L2057 (date: April 7, 2015; actor: Merrill Lynch; terms: stockholder)
- [ ] **0001047469-15-004989:E0512** L2063-L2069 (date: May 7, 2015; actor: Merrill Lynch; terms: party )

### Process signals to check
- [ ] **0001047469-15-004989:E0367** L1719-L1723 (terms: strategic alternatives)
- [ ] **0001047469-15-004989:E0369** L1725-L1726 (date: June 20, 2013; terms: strategic alternatives)
- [ ] **0001047469-15-004989:E0372** L1728-L1733 (date: July 1, 2013; actor: K. Morgan; terms: strategic alternatives)
- [ ] **0001047469-15-004989:E0375** L1735-L1737 (date: July 1, 2013; actor: Mr. Morgan; terms: strategic alternatives)
- [ ] **0001047469-15-004989:E0381** L1749-L1757 (date: August 20, 2013; actor: Merrill Lynch; terms: strategic alternatives)
- [ ] **0001047469-15-004989:E0382** L1759-L1763 (terms: strategic alternatives)
- [ ] **0001047469-15-004989:E0385** L1765-L1769 (date: January; actor: Merrill Lynch; terms: strategic alternatives)
- [ ] **0001047469-15-004989:E0390** L1775-L1781 (date: January 28, 2014; actor: Merrill Lynch; terms: strategic alternatives)
- [ ] **0001047469-15-004989:E0392** L1786-L1789 (actor: Board; terms: strategic alternatives)
- [ ] **0001047469-15-004989:E0395** L1791-L1794 (date: January 31, 2014; actor: Board; terms: strategic alternatives)
- [ ] **0001047469-15-004989:E0402** L1808-L1815 (date: February 27, 2014; actor: Merrill Lynch; terms: confidentiality agreement, strategic alternatives)
- [ ] **0001047469-15-004989:E0404** L1817-L1821 (actor: Merrill Lynch; terms: confidentiality agreement, standstill)
- [ ] **0001047469-15-004989:E0408** L1826-L1829 (date: March 2014; actor: Board; terms: confidentiality agreement)
- [ ] **0001047469-15-004989:E0413** L1837-L1843 (date: March 27, 2014; actor: Merrill Lynch; terms: confidentiality agreement, process letter)
- [ ] **0001047469-15-004989:E0421** L1855-L1858 (actor: Party X; terms: management presentation)
- [ ] **0001047469-15-004989:E0423** L1860-L1863 (date: May 7, 2014; terms: due diligence)
- [ ] **0001047469-15-004989:E0439** L1904-L1907 (date: June 26, 2014; terms: strategic alternatives)
- [ ] **0001047469-15-004989:E0441** L1909-L1915 (terms: confidentiality agreement)
- [ ] **0001047469-15-004989:E0446** L1924-L1928 (date: early February 2015; actor: Merrill Lynch; value: $19.25; terms: exclusivity, go-shop)
- [ ] **0001047469-15-004989:E0450** L1930-L1939 (date: February 23, 2015; actor: Merrill Lynch; terms: exclusivity, go-shop)
- [ ] **0001047469-15-004989:E0455** L1941-L1946 (date: February 24, 2015; actor: Merrill Lynch; value: $20.05; terms: exclusivity, go-shop)
- [ ] **0001047469-15-004989:E0460** L1948-L1955 (date: February 26, 2015; actor: Merrill Lynch; value: $20.05 per share; terms: exclusivity, strategic alternatives)
- [ ] **0001047469-15-004989:E0462** L1960-L1963 (terms: exclusivity, go-shop)
- [ ] **0001047469-15-004989:E0465** L1965-L1967 (date: February 27, 2015; terms: confidentiality agreement, exclusivity, standstill)
- [ ] **0001047469-15-004989:E0468** L1969-L1973 (date: March 2, 2015; actor: Merrill Lynch; terms: due diligence)
- [ ] **0001047469-15-004989:E0471** L1975-L1978 (date: March 2015; actor: Mr. Morgan; terms: due diligence)
- [ ] **0001047469-15-004989:E0474** L1980-L1983 (date: March 13, 2015; value: $20.05 per share; terms: best and final, due diligence, exclusivity)
- [ ] **0001047469-15-004989:E0478** L1985-L1992 (date: March 16, 2015; actor: Merrill Lynch; terms: exclusivity, go-shop)
- [ ] **0001047469-15-004989:E0482** L1994-L1997 (date: March 18, 2015; terms: draft merger agreement, go-shop)
- [ ] **0001047469-15-004989:E0486** L2009-L2014 (date: March 29, 2015; terms: go-shop)
- [ ] **0001047469-15-004989:E0491** L2016-L2019 (date: April; actor: Mr. Morgan; value: $20.05 per share; terms: best and final)
- [ ] **0001047469-15-004989:E0496** L2021-L2031 (date: April 6, 2015; actor: Merrill Lynch; value: $20.05 per share; terms: draft merger agreement, go-shop)
- [ ] **0001047469-15-004989:E0501** L2033-L2038 (date: April 6, 2015; value: $8.75; terms: go-shop, superior proposal)
- [ ] **0001047469-15-004989:E0507** L2047-L2057 (date: April 7, 2015; actor: Merrill Lynch; terms: go-shop)
- [ ] **0001047469-15-004989:E0513** L2063-L2069 (date: May 7, 2015; actor: Merrill Lynch; terms: confidentiality agreement, go-shop)

### Outcome facts to verify
- [ ] **0001047469-15-004989:E0364** L1712-L1713 (terms: merger agreement)
- [ ] **0001047469-15-004989:E0405** L1817-L1821 (actor: Merrill Lynch; terms: executed)
- [ ] **0001047469-15-004989:E0414** L1837-L1843 (date: March 27, 2014; actor: Merrill Lynch; terms: executed)
- [ ] **0001047469-15-004989:E0434** L1881-L1883 (date: May 22, 2014; actor: Party X; terms: merger agreement)
- [ ] **0001047469-15-004989:E0442** L1909-L1915 (terms: merger agreement)
- [ ] **0001047469-15-004989:E0447** L1924-L1928 (date: early February 2015; actor: Merrill Lynch; value: $19.25; terms: merger agreement)
- [ ] **0001047469-15-004989:E0451** L1930-L1939 (date: February 23, 2015; actor: Merrill Lynch; terms: merger agreement)
- [ ] **0001047469-15-004989:E0456** L1941-L1946 (date: February 24, 2015; actor: Merrill Lynch; value: $20.05; terms: merger agreement)
- [ ] **0001047469-15-004989:E0463** L1960-L1963 (terms: merger agreement)
- [ ] **0001047469-15-004989:E0475** L1980-L1983 (date: March 13, 2015; value: $20.05 per share; terms: merger agreement)
- [ ] **0001047469-15-004989:E0479** L1985-L1992 (date: March 16, 2015; actor: Merrill Lynch; terms: merger agreement)
- [ ] **0001047469-15-004989:E0483** L1994-L1997 (date: March 18, 2015; terms: merger agreement)
- [ ] **0001047469-15-004989:E0487** L2009-L2014 (date: March 29, 2015; terms: closing, merger agreement, termination fee)
- [ ] **0001047469-15-004989:E0492** L2016-L2019 (date: April; actor: Mr. Morgan; value: $20.05 per share; terms: merger agreement)
- [ ] **0001047469-15-004989:E0497** L2021-L2031 (date: April 6, 2015; actor: Merrill Lynch; value: $20.05 per share; terms: merger agreement, termination fee)
- [ ] **0001047469-15-004989:E0502** L2033-L2038 (date: April 6, 2015; value: $8.75; terms: merger agreement, termination fee)
- [ ] **0001047469-15-004989:E0508** L2047-L2057 (date: April 7, 2015; actor: Merrill Lynch; terms: merger agreement, termination fee)
- [ ] **0001047469-15-004989:E0510** L2059-L2061 (date: April 8, 2015; terms: executed, merger agreement)
- [ ] **0001047469-15-004989:E0514** L2063-L2069 (date: May 7, 2015; actor: Merrill Lynch; terms: merger agreement)
</evidence_checklist>

<task_instructions>
IMPORTANT: You MUST follow the quote-before-extract protocol.

Step 1 - QUOTE: Read the chronology blocks above. Copy every verbatim passage needed to support party, cohort, and observation extraction into the quotes array. Each quote needs a unique quote_id (Q001, Q002, ...), the source block_id, and the exact filing text.

Step 2 - EXTRACT: Return filing-literal structure only. Build:
- parties: named bidders, advisors, activists, target-side boards/entities, and aliases
- cohorts: unnamed bidder groups with exact_count, known members when explicit, and the observation that created the cohort
- observations: only the six v2 observation types (process, agreement, solicitation, proposal, status, outcome)

Observation rules:
- Do not emit analyst rows, benchmark rows, dropout labels, bid labels, or other derived judgments.
- Keep every field filing-literal. If a structured field is ambiguous, set it to null or use the appropriate `other` escape hatch with a short detail string.
- Use quote_ids, never evidence_refs or inline anchor_text.
- Proposals must use bidder or bidder-cohort subject_refs.
- Solicitation observations should represent the request/announcement, with due_date when the filing gives a deadline.
- Status observations cover expressed interest, withdrawal, exclusion, cannot-improve, selected-to-advance, and similar literal process states.

Return a single JSON object with keys in this order: quotes, parties, cohorts, observations, exclusions, coverage.
</task_instructions>