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
