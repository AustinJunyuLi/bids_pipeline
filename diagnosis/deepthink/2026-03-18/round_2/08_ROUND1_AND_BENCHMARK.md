# Round 1 Feedback and Our Assessment

## Your Round 1 Analysis (Summary of Key Claims)

In Round 1, you reviewed our pipeline and provided recommendations. We
found many valuable insights but also identified places where you
conflated the SKILL system (prompt instructions for quick analysis) with
the DETERMINISTIC PIPELINE (production Python code).

Here is our assessment of your key claims:

### Claims We Agree With (Pipeline Issues)

1. **`prompted_json` + assistant prefilling is broken on Claude 4.6.**
   Verified — HTTP 400 errors. Must move to `provider_native` with
   `output_config.format`. This is a real production blocker.

2. **LLM told to classify `DROP_BELOW_M` without market data.**
   The LLM prompt asks it to output relative dropout types but never
   provides the market price or prior bid values. The LLM is guessing.
   Fix: LLM extracts only `DROP` + `drop_reason_text`, deterministic
   Stage 5 sub-classifies using CRSP/COMPUSTAT.

3. **Missing `is_subject_to_financing` on ProposalEvent.**
   Genuine schema gap. Financing conditionality is economically significant.

4. **Missing `representing_actor_id` on ActorRecord.**
   Legal counsel attribution (target-side vs bidder-side) is missing.

5. **Missing `invited_actor_ids` on RoundEvent.**
   Alex's instructions say formal bids are those after "a final round of
   bidding that only a SUBSET of bidders is invited to." Round selectivity
   must be captured.

6. **Repair loop violates i.i.d. measurement error assumptions.**
   Reasonable statistical argument. Repaired outputs come from a different
   conditional distribution than first-pass successes.

7. **Chunking destroys coreference resolution.**
   Verified: our largest deal (STEC) is ~60K tokens. All 9 deals fit
   within 1M context. Chunking is obsolete for these deal sizes.

8. **Date convention already exists in `pipeline/normalize/dates.py`.**
   You were right — we listed this as a gap when lines 90-97 already
   map "early"→5th, "mid"→15th, "late"→25th. Our mistake.

### Claims We Disagree With

9. **"Delete the audit-and-enrich skill entirely."**
   The skill is NOT a shadow pipeline. It's a facilitating tool for:
   (a) Quick preliminary extraction before the pipeline is tuned
   (b) Testing what the LLM can extract, informing pipeline design
   (c) Complementary quality checks the pipeline can't do (count
       reconciliation reasoning, structural completeness)
   The right fix: move DATA outputs into the pipeline schema (e.g., add
   `initiation_judgment` to `DealEnrichment`), but keep the skill as a
   complementary QA tool.

10. **"Keep cycle boundaries strictly deterministic at 180 days."**
    Some deals have 90-day gaps that are clearly new processes (board
    reconvenes after failed negotiation). Others have 200-day gaps that
    are continuations (long regulatory review). 180 days is a reasonable
    default with a `review_required` flag for ambiguous cases.

11. **"Delete fuzzy matching entirely."**
    The parenthetical concern is valid (stripping "(subject to financing)"
    is dangerous). But the fix is to tighten fuzzy matching (flag
    `review_required` instead of auto-accepting), not to delete it.
    Some anchor texts have legitimate minor variations.

### Claims That Need More Discussion

12. **N=5 consensus extraction.** The Wang & Wang (2025) paper supports
    this. Cost is manageable (~$135-270 for all 9 deals). But
    temperature=0.2 recommendation needs testing — it introduces more
    variance while detecting extraction uncertainty.

13. **Initiation judgment should be 100% LLM, not partially deterministic.**
    Your argument that SEC filings are legally stylized retrospective
    narratives is strong. But the first event type still provides a useful
    heuristic that the LLM can refine.

## What We Need From Round 2

Round 1 mixed up criticism of the SKILL (prompt instructions) with
criticism of the PIPELINE (production code). This round, we need you to
keep them clearly separated and focus on:

1. Critically calibrate the PIPELINE against Alex's collection instructions
2. Assess the SKILL as a facilitating development tool
3. Recommend the optimal LLM/deterministic mix for academic rigor


---


================================================================================
DEAL: Providence & Worcester (starting at Excel row 6024)
================================================================================
TargetName: PROVIDENCE & WORCESTER RR CO
Events: 36
Acquirer: GENESEE & WYOMING INC
DateAnnounced: 2016-08-15 00:00:00
URL: https://www.sec.gov/Archives/edgar/data/831968/0001193125-16-713780-index.htm...
  [0.3] | note=Bidder Interest | bidder=Party A | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2015-12-31 00:00:00 | date_p=2016-07-22 00:00:00 | cash=NA | c1=Bidder interest suggested, but no bid
  [0.5] | note=IB | bidder=Greene Holcomb & Fisher | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-01-27 00:00:00 | date_p=NA | cash=NA | c1=Legal advisor: Hinckley Allen
  [0.7] | note=Target Sale | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-03-14 00:00:00 | date_p=2016-07-22 00:00:00 | cash=NA | c1=No concrete offer from Party A and a large time gap, so perh
  [1] | note=NDA | bidder=25 parties, including Parties A, B | type=11S, 14F | bid_type=NA | val=NA | range=NA-NA | date_r=2016-03-28 00:00:00 | date_p=NA | cash=NA
  [2] | note=NA | bidder=G&W | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-04-13 00:00:00 | date_p=2016-04-13 00:00:00 | cash=NA
  [3] | note=NA | bidder=9 parties | type=NA | bid_type=Informal | val=17.93 | range=17.93-26.5 | date_r=2016-05-19 00:00:00 | date_p=NA | cash=NA
  [4] | note=Drop | bidder=16 parties | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-06-01 00:00:00 | date_p=2016-06-01 00:00:00 | cash=NA
  [5] | note=DropTarget | bidder=2 parties | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-06-01 00:00:00 | date_p=2016-06-01 00:00:00 | cash=NA | c1=In view of the substantial amount of management time that wo
  [6] | note=Final Round Inf Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-06-15 00:00:00 | date_p=NA | cash=NA | c1=Mid-june 2016 | c2=This is probably something we will not collect, but for now…
  [7] | note=NDA | bidder=Party C | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-07-01 00:00:00 | date_p=NA | cash=NA | c1=Early july 2016 - what should be the appropriate date? July 
  [8] | note=NA | bidder=Party C | type=S | bid_type=Informal | val=21 | range=21-21 | date_r=2016-07-12 00:00:00 | date_p=2016-07-12 00:00:00 | cash=NA
  [9] | note=NA | bidder=Party B | type=S | bid_type=Formal | val=24 | range=24-24 | date_r=2016-07-20 00:00:00 | date_p=2016-07-20 00:00:00 | cash=NA | c1=Late july -- but the deadline was july 20 | c2=expedited DD; what is the threshold for "formal"?
  [10] | note=NA | bidder=Party E | type=S | bid_type=Informal | val=21.26 | range=21.26-21.26 | date_r=2016-07-20 00:00:00 | date_p=2016-07-20 00:00:00 | cash=NA | c2=60 day exclusive DD + negotiation of documentation
  [11] | note=NA | bidder=Party D | type=F | bid_type=Informal | val=21 | range=21-21 | date_r=2016-07-20 00:00:00 | date_p=2016-07-20 00:00:00 | cash=NA | c2=4 week DD
  [12] | note=NA | bidder=Party C | type=S | bid_type=Informal | val=19.3 | range=19.3-19.3 | date_r=2016-07-20 00:00:00 | date_p=2016-07-20 00:00:00 | cash=NA | c2=30 day DD
  [13] | note=NA | bidder=Party F | type=F | bid_type=Informal | val=19.2 | range=19.2-19.2 | date_r=2016-07-20 00:00:00 | date_p=2016-07-20 00:00:00 | cash=NA | c2=30 day DD
  [13.5] | note=Final Round Inf | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-07-20 00:00:00 | date_p=NA | cash=NA
  [14] | note=NA | bidder=G&W | type=S | bid_type=Informal | val=21.15 | range=21.15-21.15 | date_r=2016-07-21 00:00:00 | date_p=2016-07-21 00:00:00 | cash=1 | c1=20.02 cash + 1.13 CVR | c2=3 week exclusive DD
  [15] | note=Drop | bidder=Party A | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-07-22 00:00:00 | date_p=2016-07-22 00:00:00 | cash=NA
  [16] | note=Drop | bidder=1 party | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-07-22 00:00:00 | date_p=2016-07-22 00:00:00 | cash=NA
  [17] | note=NA | bidder=G&W | type=S | bid_type=Formal | val=22.15 | range=22.15-22.15 | date_r=2016-07-26 00:00:00 | date_p=2016-07-26 00:00:00 | cash=1 | c1=21.02 cash + 1.13 CVR
  [17.5] | note=Final Round Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-07-27 00:00:00 | date_p=NA | cash=NA | c1= Target worried about the delays inherent in managing on-sit
  [18] | note=DropTarget | bidder=Party E | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-07-27 00:00:00 | date_p=2016-07-27 00:00:00 | cash=NA
  [19] | note=DropTarget | bidder=Party D | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2016-07-27 00:00:00 | date_p=2016-07-27 00:00:00 | cash=NA
  [20] | note=DropTarget | bidder=Party C | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-07-27 00:00:00 | date_p=2016-07-27 00:00:00 | cash=NA
  [21] | note=DropTarget | bidder=Party F | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2016-07-27 00:00:00 | date_p=2016-07-27 00:00:00 | cash=NA
  [22] | note=NA | bidder=Party D | type=F | bid_type=Informal | val=24 | range=24-24 | date_r=2016-08-01 00:00:00 | date_p=2016-08-01 00:00:00 | cash=NA | c1=Reengaged | c2=30 day exclusive DD
  [23] | note=NA | bidder=Party E/F | type=S/F | bid_type=Informal | val=23.81 | range=23.81-23.81 | date_r=2016-08-01 00:00:00 | date_p=2016-08-01 00:00:00 | cash=NA | c1=Reengaged | c2=30 day DD; Financing support from Party F
  [24] | note=NA | bidder=Party E/F | type=S/F | bid_type=Informal | val=21.26 | range=21.26-21.26 | date_r=2016-08-02 00:00:00 | date_p=2016-08-02 00:00:00 | cash=NA
  [25] | note=Drop | bidder=Party D | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2016-08-02 00:00:00 | date_p=2016-08-02 00:00:00 | cash=NA
  [25.5] | note=Executed | bidder=Party B | type=S | bid_type=Formal | val=24 | range=24-24 | date_r=2016-08-04 00:00:00 | date_p=2016-07-20 00:00:00 | cash=NA | c1=Confirm 7/20/2016 bid after DD | c2=Restrict from soliciting competing bids
  [26] | note=NA | bidder=G&W | type=S | bid_type=Formal | val=25 | range=25-25 | date_r=2016-08-12 00:00:00 | date_p=2016-08-12 00:00:00 | cash=1 | c1=all cash | c2=Expire 8/13/2016, restrict from soliciting competing bids, r
  [27] | note=Drop | bidder=Party B | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-08-12 00:00:00 | date_p=2016-08-12 00:00:00 | cash=NA | c1=Refused to increase offer
  [28] | note=Drop | bidder=Party E/F | type=S/F | bid_type=NA | val=NA | range=NA-NA | date_r=2016-08-12 00:00:00 | date_p=2016-08-12 00:00:00 | cash=NA | c1=Did not engage for a while
  [28.3] | note=Final Round | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-08-12 00:00:00 | date_p=NA | cash=NA | c1=The deadline apparently was not announced to the bidders, th
  [28.5] | note=Executed | bidder=G&W | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-08-12 00:00:00 | date_p=2016-08-15 00:00:00 | cash=NA | c1=Latest bid executed

================================================================================
DEAL: Medivation (starting at Excel row 6060)
================================================================================
TargetName: MEDIVATION INC
Events: 16
Acquirer: PFIZER INC
DateAnnounced: 2016-08-22 00:00:00
URL: https://www.sec.gov/Archives/edgar/data/1011835/0001193125-16-696889-index.htm...
  [0.7] | note=Bidder Sale | bidder=Sanofi | type=Non-US public S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-04-13 00:00:00 | date_p=2016-04-13 00:00:00 | cash=NA
  [1] | note=NA | bidder=Sanofi | type=Non-US public S | bid_type=Informal | val=52.5 | range=52.5-52.5 | date_r=2016-04-13 00:00:00 | date_p=2016-04-13 00:00:00 | cash=NA
  [1.3] | note=Bid Press Release | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-04-28 00:00:00 | date_p=2016-04-13 00:00:00 | cash=NA
  [1.5] | note=IB | bidder=J.P. Morgan | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-05-02 00:00:00 | date_p=2016-06-29 00:00:00 | cash=NA | c1=Legal advisor: Cooley. May 2: Pfizer's contact that was view
  [2] | note=NDA | bidder=Pfizer | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-06-29 00:00:00 | date_p=2016-06-29 00:00:00 | cash=NA
  [3] | note=NDA | bidder=Several parties, including Sanofi | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-07-05 00:00:00 | date_p=NA | cash=NA
  [5] | note=Final Round Inf Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-07-19 00:00:00 | date_p=2016-08-14 00:00:00 | cash=NA
  [4] | note=NA | bidder=Pfizer | type=S | bid_type=Informal | val=65 | range=65-65 | date_r=2016-08-08 00:00:00 | date_p=2016-08-08 00:00:00 | cash=1 | c2=DD 1 week
  [4.5] | note=Final Round Inf | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-08-08 00:00:00 | date_p=2016-08-14 00:00:00 | cash=NA
  [4.7] | note=Final Round Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-08-10 00:00:00 | date_p=2016-08-14 00:00:00 | cash=NA | c1=(Pfizer + several other parties); [SEVERAL: at least 3?]
  [5] | note=Final Round | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-08-14 00:00:00 | date_p=2016-08-14 00:00:00 | cash=NA
  [6] | note=NA | bidder=Pfizer | type=S | bid_type=Formal | val=77 | range=77-77 | date_r=2016-08-19 00:00:00 | date_p=2016-08-19 00:00:00 | cash=1
  [7] | note=NA | bidder=Pfizer | type=S | bid_type=Formal | val=81.5 | range=81.5-81.5 | date_r=2016-08-20 00:00:00 | date_p=2016-08-20 00:00:00 | cash=1
  [7.5] | note=Executed | bidder=Pfizer | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-08-20 00:00:00 | date_p=2016-08-20 00:00:00 | cash=NA 
  [8] | note=Drop | bidder=Sanofi | type=Non-US public S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-08-20 00:00:00 | date_p=2016-08-20 00:00:00 | cash=NA
  [9] | note=Drop | bidder=Several parties | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-08-20 00:00:00 | date_p=2016-08-20 00:00:00 | cash=NA

================================================================================
DEAL: Imprivata (starting at Excel row 6076)
================================================================================
TargetName: IMPRIVATA INC
Events: 29
Acquirer: THOMA BRAVO, LLC
DateAnnounced: 2016-07-13 00:00:00
URL: https://www.sec.gov/Archives/edgar/data/1328015/0001193125-16-677939-index.htm...
  [0.5] | note=Bidder Interest | bidder=Thoma Bravo | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2016-01-31 00:00:00 | date_p=2016-03-09 00:00:00 | cash=NA | c2=Confirmatory DD <=30 days
  [0.7] | note=Bidder Sale | bidder=Thoma Bravo | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2016-03-09 00:00:00 | date_p=2016-03-09 00:00:00 | cash=NA | c2=Confirmatory DD <=30 days
  [1] | note=NA | bidder=Thoma Bravo | type=F | bid_type=Informal | val=15 | range=15-15 | date_r=2016-03-09 00:00:00 | date_p=2016-03-09 00:00:00 | cash=1 | c2=Confirmatory DD <=30 days
  [1.5] | note=IB | bidder=Barclays | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-04-15 00:00:00 | date_p=2016-03-09 00:00:00 | cash=NA | c1=Legal counsel: Goodwin
  [2] | note=NDA | bidder=Strategic 1 | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-05-06 00:00:00 | date_p=NA | cash=NA | c1=Telecom company. bid_date is 5/6-6/9. How to record this? | c2=These parties were selected based on their experience and in
  [3] | note=NDA | bidder=Strategic 2 | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-05-06 00:00:00 | date_p=NA | cash=NA | c1=Software company | c2=In particular, the Board discussed the potential disruptions
  [4] | note=NDA | bidder=Strategic 3 | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-05-06 00:00:00 | date_p=NA | cash=NA | c1=Software company | c2=The Board also discussed the potential need to disclose duri
  [5] | note=NDA | bidder=Sponsor A | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2016-05-06 00:00:00 | date_p=NA | cash=NA
  [6] | note=NDA | bidder=Sponsor B | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2016-05-06 00:00:00 | date_p=NA | cash=NA
  [7] | note=NDA | bidder=Another financial sponsor | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2016-05-06 00:00:00 | date_p=NA | cash=NA
  [8] | note=NDA | bidder=Thoma Bravo | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2016-05-10 00:00:00 | date_p=2016-05-10 00:00:00 | cash=NA
  [9] | note=Drop | bidder=Another financial sponsor | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2016-05-07 00:00:00 | date_p=NA | cash=NA | c1=Dropped shortly after NDA, how to record given that we do no
  [9.5] | note=Final Round Inf Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-06-03 00:00:00 | date_p=2016-06-09 00:00:00 | cash=NA
  [10] | note=Drop | bidder=Strategic 1 | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-06-08 00:00:00 | date_p=2016-06-08 00:00:00 | cash=NA | c1=Deadline for indications of interest 6/9 | c2=Not a strategic fit for bidder
  [11] | note=NA | bidder=Sponsor A | type=F | bid_type=Informal | val=16.5 | range=16.5-16.5 | date_r=2016-06-09 00:00:00 | date_p=2016-06-09 00:00:00 | cash=NA | c1=F bidder, so all cash | c2=DD, no financing "among other conditions"
  [12] | note=NA | bidder=Sponsor B | type=F | bid_type=Informal | val=17 | range=17-18 | date_r=2016-06-09 00:00:00 | date_p=2016-06-09 00:00:00 | cash=NA | c1=F bidder, so all cash | c2=DD, no financing "among other conditions"
  [13] | note=NA | bidder=Thoma Bravo | type=F | bid_type=Informal | val=17.25 | range=17.25-17.25 | date_r=2016-06-09 00:00:00 | date_p=2016-06-09 00:00:00 | cash=1 | c2=DD, no financing "among other conditions"
  [13.5] | note=Final Round Inf | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-06-09 00:00:00 | date_p=2016-06-09 00:00:00 | cash=NA
  [14] | note=Drop | bidder=Strategic 2 | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-06-12 00:00:00 | date_p=2016-06-12 00:00:00 | cash=NA | c2=Other internal corporate priorities
  [14.5] | note=Final Round Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-06-12 00:00:00 | date_p=2016-06-09 00:00:00 | cash=NA | c1=[VARIANCE OF PROPOSALS MATTERS -- ON TOP OF THE AVERAGE AND  | c2=Because Sponsor A, Sponsor B and Thoma Bravo had submitted p
  [15] | note=Drop | bidder=Strategic 3 | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2016-06-14 00:00:00 | date_p=2016-06-14 00:00:00 | cash=NA | c2=Other internal corporate priorities, overlap in tech
  [16] | note=DropAtInf | bidder=Sponsor A | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2016-06-15 00:00:00 | date_p=2016-06-15 00:00:00 | cash=NA | c2=After DD: confirmed in communications their informal bid bas
  [17] | note=Final Round | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-06-24 00:00:00 | date_p=2016-06-24 00:00:00 | cash=NA
  [17.5] | note=Final Round Ext Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-06-24 00:00:00 | date_p=2016-06-24 00:00:00 | cash=NA
  [18] | note=DropBelowInf | bidder=Sponsor B | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2016-06-29 00:00:00 | date_p=2016-06-29 00:00:00 | cash=NA
  [19] | note=NA | bidder=Thoma Bravo | type=F | bid_type=Formal | val=19 | range=19-19 | date_r=2016-07-08 00:00:00 | date_p=2016-07-08 00:00:00 | cash=1
  [19.5] | note=Final Round Ext | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2016-07-08 00:00:00 | date_p=2016-06-24 00:00:00 | cash=NA
  [20] | note=NA | bidder=Thoma Bravo | type=F | bid_type=Formal | val=19.25 | range=19.25-19.25 | date_r=2016-07-09 00:00:00 | date_p=2016-07-09 00:00:00 | cash=1
  [20.5] | note=Executed | bidder=Thoma Bravo | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2016-07-13 00:00:00 | date_p=2016-07-09 00:00:00 | cash=NA

================================================================================
DEAL: Zep (starting at Excel row 6385)
================================================================================
TargetName: ZEP INC
Events: 23
Acquirer: NEW MOUNTAIN CAPITAL
DateAnnounced: 2015-04-08 00:00:00
URL: https://www.sec.gov/Archives/edgar/data/1408287/0001047469-15-004989-index.htm...
  [0.5] | note=IB | bidder=BofA Merrill Lynch | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-01-28 00:00:00 | date_p=NA | cash=NA | c1=Legal advisor: King & Spalding
  [0.7] | note=Target Sale | bidder=BofA Merrill Lynch | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-01-31 00:00:00 | date_p=NA | cash=NA | c1=Legal advisor: King & Spalding
  [1] | note=NDA | bidder=24 parties | type=S and F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-02-27 00:00:00 | date_p=NA | cash=NA
  [2] | note=NDA | bidder=New Mountain Capital | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-03-19 00:00:00 | date_p=2014-03-19 00:00:00 | cash=NA
  [2.5] | note=Final Round Inf Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-03-27 00:00:00 | date_p=NA | cash=NA
  [3] | note=NA | bidder=5 parties, 4F and 1S | type=NA | bid_type=Informal | val=20 | range=20-22 | date_r=2014-04-14 00:00:00 | date_p=2014-04-14 00:00:00 | cash=NA | c1=This field needs to be expanded to 5 bidders; one of them bi
  [4] | note=Drop | bidder=New Mountain Capital | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-04-14 00:00:00 | date_p=2014-04-14 00:00:00 | cash=NA
  [5] | note=Drop | bidder=19 parties | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-04-14 00:00:00 | date_p=2014-04-14 00:00:00 | cash=NA
  [5.5] | note=Final Round Inf | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-04-14 00:00:00 | date_p=NA | cash=NA
  [5.7] | note=Final Round | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-05-07 00:00:00 | date_p=NA | cash=NA
  [6] | note=NA | bidder=Party X | type=F | bid_type=Informal | val=21.5 | range=21.5-23 | date_r=2014-05-09 00:00:00 | date_p=2014-05-09 00:00:00 | cash=NA
  [7] | note=Drop | bidder=Party X | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-05-14 00:00:00 | date_p=2014-05-14 00:00:00 | cash=NA
  [8] | note=NA | bidder=Party Y | type=S | bid_type=Informal | val=19.5 | range=19.5-20.5 | date_r=2014-05-20 00:00:00 | date_p=2014-05-20 00:00:00 | cash=NA
  [8.5] | note=NDA | bidder=Party Y | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2014-05-20 00:00:00 | date_p=NA | cash=NA
  [9] | note=Drop | bidder=5 parties | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-05-23 00:00:00 | date_p=NA | cash=NA | c1=[OVER THE NEXT FEW WEEKS: WHAT SHOULD BE THE DATE?] | c2=Over the next few weeks, five of the remaining six intereste
  [10] | note=Drop | bidder=Party Y | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2014-05-23 00:00:00 | date_p=NA | cash=NA
  [10.5] | note=Terminated | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-06-26 00:00:00 | date_p=NA | cash=NA | c1=[THIS IS THE EXAMPLE OF THE EARLIER AUCTION THAT WAS TERMINA
  [10.7] | note=Restarted | bidder=New Mountain Capital | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2015-02-19 00:00:00 | date_p=NA | cash=NA | c2=No financing condition (highly conf letter), 45 days exclusi
  [11] | note=NA | bidder=New Mountain Capital | type=F | bid_type=Informal | val=19.25 | range=19.25-19.25 | date_r=2015-02-19 00:00:00 | date_p=2015-02-10 00:00:00 | cash=NA
  [12] | note=NA | bidder=New Mountain Capital | type=F | bid_type=Informal | val=20.05 | range=20.05-20.05 | date_r=2015-02-26 00:00:00 | date_p=2015-02-26 00:00:00 | cash=NA | c2=[USEFUL FOR TARGET MOTIVATION] Our board of directors also c
  [13] | note=Exclusivity 30 days | bidder=New Mountain Capital | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2015-02-27 00:00:00 | date_p=2015-02-27 00:00:00 | cash=NA
  [14] | note=NA | bidder=New Mountain Capital | type=F | bid_type=Formal | val=20.05 | range=20.05-20.05 | date_r=2015-03-13 00:00:00 | date_p=2015-03-29 00:00:00 | cash=1 | c2=Go-shop 30 days, term fee, reverse term fee
  [14.5] | note=Executed | bidder=New Mountain Capital | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2015-04-08 00:00:00 | date_p=NA | cash=NA

================================================================================
DEAL: Petsmart (starting at Excel row 6408)
================================================================================
TargetName: PETSMART INC
Events: 53
Acquirer: BC Partners, Inc., La Caisse de dÃ©pÃ´t et placement du QuÃ©bec, affiliates of GIC Special Investments Pte Ltd, affiliates of StepStone Group LP and Longview Asset Management, LLC
DateAnnounced: 2014-12-14 00:00:00
URL: https://www.sec.gov/Archives/edgar/data/863157/0001571049-15-000695-index.htm...
  [0.7] | note=IB | bidder=J.P. Morgan | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-07-01 00:00:00 | date_p=NA | cash=NA | c1=Legal advisor: Wachtell Lipton
  [0.8] | note=Activist Sale | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-07-03 00:00:00 | date_p=NA | cash=NA
  [0.9] | note=Target Sale Public | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-08-13 00:00:00 | date_p=NA | cash=NA
  [0.95] | note=Sale Press Release | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-08-19 00:00:00 | date_p=NA | cash=NA
  [1] | note=NDA | bidder=Unnamed party 1 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-07 00:00:00 | date_p=NA | cash=NA | c1=PetSmart tried to acquire a firm from the same industry in M
  [2] | note=NDA | bidder=Unnamed party 2 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-07 00:00:00 | date_p=NA | cash=NA | c1=May 21, 2014: quarter earnings announcement, weaker than exp
  [3] | note=NDA | bidder=Unnamed party 3 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-07 00:00:00 | date_p=NA | cash=NA | c1=NDA first week of October
  [4] | note=NDA | bidder=Unnamed party 4 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-07 00:00:00 | date_p=NA | cash=NA
  [5] | note=NDA | bidder=Unnamed party 5 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-07 00:00:00 | date_p=NA | cash=NA
  [6] | note=NDA | bidder=Unnamed party 6 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-07 00:00:00 | date_p=NA | cash=NA
  [7] | note=NDA | bidder=Unnamed party 7 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-07 00:00:00 | date_p=NA | cash=NA
  [8] | note=NDA | bidder=Unnamed party 8 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-07 00:00:00 | date_p=NA | cash=NA
  [9] | note=NDA | bidder=Unnamed party 9 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-07 00:00:00 | date_p=NA | cash=NA
  [10] | note=NDA | bidder=Unnamed party 10 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-07 00:00:00 | date_p=NA | cash=NA
  [11] | note=NDA | bidder=Unnamed party 11 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-07 00:00:00 | date_p=NA | cash=NA
  [12] | note=NDA | bidder=Unnamed party 12 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-07 00:00:00 | date_p=NA | cash=NA
  [13] | note=NDA | bidder=Bidder 1 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-07 00:00:00 | date_p=NA | cash=NA
  [14] | note=NDA | bidder=Bidder 2 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-07 00:00:00 | date_p=NA | cash=NA
  [15] | note=NDA | bidder=Buyer Group | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-07 00:00:00 | date_p=NA | cash=NA
  [15.5] | note=Final Round Inf Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-15 00:00:00 | date_p=NA | cash=NA
  [16] | note=NA | bidder=Unnamed party 1 | type=F | bid_type=Informal | val=NA | range=80-NA | date_r=2014-10-30 00:00:00 | date_p=2014-10-30 00:00:00 | cash=NA
  [17] | note=NA | bidder=Unnamed party 2 | type=F | bid_type=Informal | val=NA | range=NA-NA | date_r=2014-10-30 00:00:00 | date_p=2014-10-30 00:00:00 | cash=NA
  [18] | note=NA | bidder=Unnamed party 3 | type=F | bid_type=Informal | val=NA | range=NA-NA | date_r=2014-10-30 00:00:00 | date_p=2014-10-30 00:00:00 | cash=NA
  [19] | note=NA | bidder=Buyer Group | type=F | bid_type=Informal | val=81 | range=81-83 | date_r=2014-10-30 00:00:00 | date_p=2014-10-30 00:00:00 | cash=NA
  [20] | note=NA | bidder=Unnamed party 4 | type=F | bid_type=Informal | val=80 | range=80-85 | date_r=2014-10-30 00:00:00 | date_p=2014-10-30 00:00:00 | cash=NA
  [21] | note=NA | bidder=Bidder 2 | type=F | bid_type=Informal | val=78 | range=78-78 | date_r=2014-10-30 00:00:00 | date_p=2014-10-30 00:00:00 | cash=NA
  [21.5] | note=Final Round Inf | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-30 00:00:00 | date_p=NA | cash=NA
  [22] | note=NA | bidder=Bidder 2 | type=F | bid_type=Informal | val=81 | range=81-84 | date_r=2014-11-02 00:00:00 | date_p=2014-10-30 00:00:00 | cash=NA
  [22.5] | note=Drop | bidder=Unnamed party 5 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-30 00:00:00 | date_p=2014-10-30 00:00:00 | cash=NA
  [23] | note=Drop | bidder=Unnamed party 6 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-30 00:00:00 | date_p=2014-10-30 00:00:00 | cash=NA
  [24] | note=Drop | bidder=Unnamed party 7 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-30 00:00:00 | date_p=2014-10-30 00:00:00 | cash=NA
  [25] | note=Drop | bidder=Unnamed party 8 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-30 00:00:00 | date_p=2014-10-30 00:00:00 | cash=NA
  [26] | note=Drop | bidder=Unnamed party 9 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-30 00:00:00 | date_p=2014-10-30 00:00:00 | cash=NA
  [27] | note=Drop | bidder=Unnamed party 10 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-30 00:00:00 | date_p=2014-10-30 00:00:00 | cash=NA
  [28] | note=Drop | bidder=Unnamed party 11 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-30 00:00:00 | date_p=2014-10-30 00:00:00 | cash=NA
  [29] | note=Drop | bidder=Unnamed party 12 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-30 00:00:00 | date_p=2014-10-30 00:00:00 | cash=NA
  [31] | note=DropTarget | bidder=Unnamed party 2 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-11-03 00:00:00 | date_p=NA | cash=NA
  [32] | note=DropTarget | bidder=Unnamed party 3 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-11-03 00:00:00 | date_p=NA | cash=NA
  [34.5] | note=Final Round Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-11-15 00:00:00 | date_p=NA | cash=NA
  [36] | note=NA | bidder=Buyer Group | type=F | bid_type=Formal | val=80.7 | range=80.7-80.7 | date_r=2014-12-10 00:00:00 | date_p=2014-12-10 00:00:00 | cash=1
  [37] | note=NA | bidder=Bidder 2 | type=F | bid_type=Formal | val=80.35 | range=80.35-80.35 | date_r=2014-12-10 00:00:00 | date_p=2014-12-10 00:00:00 | cash=1
  [38] | note=NA | bidder=Bidder 3 | type=F | bid_type=Informal | val=78 | range=78-78 | date_r=2014-12-10 00:00:00 | date_p=2014-12-10 00:00:00 | cash=NA
  [38.2] | note=Drop | bidder=Unnamed party 1 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-12-10 00:00:00 | date_p=2014-11-03 00:00:00 | cash=NA
  [38.3] | note=Drop | bidder=Unnamed party 4 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-12-10 00:00:00 | date_p=NA | cash=NA
  [38.5] | note=Final Round | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-12-10 00:00:00 | date_p=NA | cash=NA
  [38.7] | note=Final Round Ext Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-12-10 00:00:00 | date_p=NA | cash=NA
  [39] | note=NA | bidder=Bidder 2 | type=F | bid_type=Formal | val=81.5 | range=81.5-81.5 | date_r=2014-12-12 00:00:00 | date_p=2014-12-12 00:00:00 | cash=1
  [40] | note=NA | bidder=Buyer Group | type=F | bid_type=Formal | val=82.5 | range=82.5-82.5 | date_r=2014-12-12 00:00:00 | date_p=2014-12-12 00:00:00 | cash=1
  [40.3] | note=NA | bidder=Buyer Group | type=F | bid_type=Formal | val=83 | range=83-83 | date_r=2014-12-12 00:00:00 | date_p=2014-12-12 00:00:00 | cash=1
  [40.5] | note=Final Round Ext | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-12-12 00:00:00 | date_p=NA | cash=NA
  [42] | note=Drop | bidder=Bidder 2 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-12-14 00:00:00 | date_p=2014-12-14 00:00:00 | cash=NA
  [43] | note=Drop | bidder=Bidder 3 | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-12-14 00:00:00 | date_p=2014-12-14 00:00:00 | cash=NA
  [43.5] | note=Executed | bidder=Buyer Group | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2014-12-14 00:00:00 | date_p=2014-12-12 00:00:00 | cash=1

================================================================================
DEAL: Penford (starting at Excel row 6461)
================================================================================
TargetName: PENFORD CORP
Events: 25
Acquirer: INGREDION INC
DateAnnounced: 2014-10-15 00:00:00
URL: https://www.sec.gov/Archives/edgar/data/739608/0001193125-14-455030-index.htm...
  [1] | note=NDA | bidder=1 party | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2007-01-15 00:00:00 | date_p=NA | cash=NA | c1=[EVERYTHING IN GREY SHOULD NOT BE HERE]
  [2] | note=Drop | bidder=1 party | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2007-01-15 00:00:00 | date_p=NA | cash=NA
  [3] | note=NDA | bidder=A diffferent party | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2009-01-15 00:00:00 | date_p=NA | cash=NA
  [4] | note=Drop | bidder=A diffferent party | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2009-01-15 00:00:00 | date_p=NA | cash=NA
  [4.5] | note=Bidder Interest | bidder=Ingredion | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2014-07-17 00:00:00 | date_p=2014-07-20 00:00:00 | cash=NA
  [5] | note=NDA | bidder=Ingredion | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2014-07-20 00:00:00 | date_p=2014-07-20 00:00:00 | cash=NA | c1=This NDA is a 'Secrecy Agreement', i.e. lacks certain featur
  [5.5] | note=IB | bidder=Deutsche Bank | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-07-30 00:00:00 | date_p=2014-08-21 00:00:00 | cash=NA | c1=Legal counsel: Perkins Coie | c2=It looks like DB was already seleected on July 30, and provi
  [6] | note=NA | bidder=Ingredion | type=S | bid_type=Informal | val=17 | range=17-17 | date_r=2014-08-06 00:00:00 | date_p=2014-08-06 00:00:00 | cash=NA
  [7] | note=NA | bidder=Ingredion | type=S | bid_type=Informal | val=18 | range=18-18 | date_r=2014-08-10 00:00:00 | date_p=2014-08-10 00:00:00 | cash=1
  [8] | note=NDA | bidder=Ingredion | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2014-08-21 00:00:00 | date_p=2014-08-21 00:00:00 | cash=NA
  [9] | note=NDA | bidder=Party C | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2014-09-15 00:00:00 | date_p=2014-09-15 00:00:00 | cash=NA
  [10] | note=NA | bidder=Ingredion | type=S | bid_type=Informal | val=18.25 | range=18.25-18.5 | date_r=2014-09-17 00:00:00 | date_p=2014-09-17 00:00:00 | cash=1
  [11] | note=NDA | bidder=Party D | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2014-09-23 00:00:00 | date_p=2014-09-23 00:00:00 | cash=NA
  [12] | note=NDA | bidder=Party A | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2014-09-30 00:00:00 | date_p=2014-09-30 00:00:00 | cash=NA
  [13] | note=NA | bidder=Ingredion | type=S | bid_type=Informal | val=18.5 | range=18.5-18.5 | date_r=2014-10-02 00:00:00 | date_p=2014-10-02 00:00:00 | cash=1
  [14] | note=NA | bidder=Ingredion | type=S | bid_type=Informal | val=19 | range=19-19 | date_r=2014-10-02 00:00:00 | date_p=2014-10-02 00:00:00 | cash=1
  [14.5] | note=Final Round Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-03 00:00:00 | date_p=NA | cash=NA | c1=After further discussion, with input from Deutsche Bank, the
  [15] | note=NA | bidder=Party A | type=S | bid_type=Informal | val=17.5 | range=17.5-18 | date_r=2014-10-04 00:00:00 | date_p=2014-10-03 00:00:00 | cash=1
  [17] | note=Drop | bidder=Party D | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-08 00:00:00 | date_p=2014-10-08 00:00:00 | cash=NA | c1=10/11/2014: draft financial statements for the fiscal year e
  [18] | note=NA | bidder=Party A | type=S | bid_type=Informal | val=16 | range=16-18 | date_r=2014-10-13 00:00:00 | date_p=2014-10-13 00:00:00 | cash=1
  [18.5] | note=NA | bidder=Ingredion | type=S | bid_type=Formal | val=19 | range=19-19 | date_r=2014-10-14 00:00:00 | date_p=2014-10-08 00:00:00 | cash=1
  [19] | note=NA | bidder=Party A | type=S | bid_type=Informal | val=16 | range=16-16 | date_r=2014-10-14 00:00:00 | date_p=2014-10-14 00:00:00 | cash=1
  [20] | note=Drop | bidder=Party A | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-14 00:00:00 | date_p=2014-10-14 00:00:00 | cash=NA
  [21] | note=Drop | bidder=Party C | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-14 00:00:00 | date_p=2014-10-14 00:00:00 | cash=NA
  [21.5] | note=Executed | bidder=Ingredion | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2014-10-14 00:00:00 | date_p=2014-10-08 00:00:00 | cash=NA

================================================================================
DEAL: Mac Gray (starting at Excel row 6927)
================================================================================
TargetName: MAC GRAY CORP
Events: 34
Acquirer: CSC SERVICEWORKS, INC.
DateAnnounced: 2013-10-15 00:00:00
URL: https://www.sec.gov/Archives/edgar/data/1038280/0001047469-13-010973-index.htm...
  [0.5] | note=IB | bidder=BofA Merrill Lynch | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-04-05 00:00:00 | date_p=NA | cash=NA
  [0.7] | note=Target Interest | bidder=Party A | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-04-08 00:00:00 | date_p=NA | cash=NA | c1=Not an official sale, but T approached Party A
  [0.8] | note=IB Terminated | bidder=BofA Merrill Lynch | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-05-15 00:00:00 | date_p=NA | cash=NA
  [0.9] | note=IB | bidder=BofA Merrill Lynch | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-05-31 00:00:00 | date_p=NA | cash=NA | c1=Sale process discussed since May 9; BofA offered some valuat
  [0.95] | note=Bidder Sale | bidder=Party A | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-06-21 00:00:00 | date_p=2013-06-21 00:00:00 | cash=NA
  [1] | note=NA | bidder=Party A | type=S | bid_type=Informal | val=17 | range=17-19 | date_r=2013-06-21 00:00:00 | date_p=2013-06-21 00:00:00 | cash=1
  [1.5] | note=Final Round Inf Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-06-24 00:00:00 | date_p=NA | cash=NA
  [2] | note=NDA | bidder=16 financial bidders | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2013-07-15 00:00:00 | date_p=NA | cash=NA
  [3] | note=NDA | bidder=Party B | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2013-06-28 00:00:00 | date_p=2013-06-28 00:00:00 | cash=NA
  [4] | note=NDA | bidder=Party C | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2013-06-30 00:00:00 | date_p=2013-06-20 00:00:00 | cash=NA
  [5] | note=NDA | bidder=CSC/Pamplona | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-07-11 00:00:00 | date_p=2013-07-11 00:00:00 | cash=NA
  [6] | note=NA | bidder=CSC/Pamplona | type=S | bid_type=Informal | val=18.5 | range=18.5-18.5 | date_r=2013-07-23 00:00:00 | date_p=2013-07-23 00:00:00 | cash=1
  [6.5] | note=Final Round Inf | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-07-23 00:00:00 | date_p=NA | cash=NA | c1=the Special Committee concluded that it would be advisable t
  [7] | note=NA | bidder=Party B | type=F | bid_type=Informal | val=17 | range=17-18 | date_r=2013-07-24 00:00:00 | date_p=2013-07-24 00:00:00 | cash=1
  [8] | note=NA | bidder=Party C | type=F | bid_type=Informal | val=15 | range=15-17 | date_r=2013-07-24 00:00:00 | date_p=2013-07-24 00:00:00 | cash=1
  [9] | note=Drop | bidder=16 financial bidders | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2013-07-25 00:00:00 | date_p=2013-07-25 00:00:00 | cash=NA
  [9.5] | note=Final Round Inf Ext Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-07-25 00:00:00 | date_p=NA | cash=NA
  [10] | note=NA | bidder=Party C | type=F | bid_type=Informal | val=16 | range=16-16.5 | date_r=2013-07-25 00:00:00 | date_p=2013-07-25 00:00:00 | cash=1
  [11] | note=NDA | bidder=Party A | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-08-05 00:00:00 | date_p=2013-08-05 00:00:00 | cash=NA | c1=[DIFFERENT DD INFO FOR DIFFERENT BIDDERS, S VS F + DEGREE OF
  [12] | note=NA | bidder=CSC/Pamplona | type=S | bid_type=Informal | val=19.5 | range=19.5-19.5 | date_r=2013-09-09 00:00:00 | date_p=2013-09-09 00:00:00 | cash=1 | c2=Exclusivity 2 weeks
  [13] | note=NA | bidder=Party B | type=F | bid_type=Informal | val=18.5 | range=18.5-18.5 | date_r=2013-09-09 00:00:00 | date_p=2013-09-09 00:00:00 | cash=1 | c2=No firm financing commitment
  [13.5] | note=Final Round Inf Ext | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-09-09 00:00:00 | date_p=NA | cash=NA
  [14] | note=NA | bidder=Party A | type=S | bid_type=Informal | val=18 | range=18-19 | date_r=2013-09-10 00:00:00 | date_p=2013-09-10 00:00:00 | cash=1 | c2=No firm financing commitment
  [15] | note=NA | bidder=Party C | type=F | bid_type=Informal | val=16 | range=16-17 | date_r=2013-09-10 00:00:00 | date_p=2013-09-10 00:00:00 | cash=1 | c2=No firm financing commitment
  [16] | note=Final Round Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-09-11 00:00:00 | date_p=2013-09-11 00:00:00 | cash=NA
  [17] | note=NA | bidder=CSC/Pamplona | type=S | bid_type=Formal | val=20.75 | range=20.75-20.75 | date_r=2013-09-18 00:00:00 | date_p=2013-09-18 00:00:00 | cash=1 | c2=Exclusivity 2 weeks
  [18] | note=NA | bidder=Party A | type=S | bid_type=Formal | val=18 | range=18-19 | date_r=2013-09-18 00:00:00 | date_p=2013-09-18 00:00:00 | cash=1
  [19] | note=NA | bidder=Party B | type=F | bid_type=Formal | val=21.5 | range=21.5-21.5 | date_r=2013-09-18 00:00:00 | date_p=2013-09-18 00:00:00 | c1=19 in cash, rest in options/earnouts (2.5 is the bidder's va | c2=No firm financing commitment
  [20] | note=Drop | bidder=Party C | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2013-09-18 00:00:00 | date_p=2013-09-18 00:00:00 | cash=NA
  [20.5] | note=Final Round | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-09-18 00:00:00 | date_p=2013-09-11 00:00:00 | cash=NA
  [21] | note=NA | bidder=CSC/Pamplona | type=S | bid_type=Formal | val=21.25 | range=21.25-21.25 | date_r=2013-09-21 00:00:00 | date_p=2013-09-21 00:00:00 | cash=1 | c2=Exclusivity 2 weeks
  [22] | note=DropTarget | bidder=Party A | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-09-24 00:00:00 | date_p=2013-09-24 00:00:00 | cash=NA
  [23] | note=DropTarget | bidder=Party B | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2013-09-24 00:00:00 | date_p=2013-09-24 00:00:00 | cash=NA
  [21] | note=Executed | bidder=CSC/Pamplona | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-10-14 00:00:00 | date_p=2013-09-21 00:00:00 | cash=NA | c2=Exclusivity 2 weeks

================================================================================
DEAL: Saks (starting at Excel row 6996)
================================================================================
TargetName: SAKS INC
Events: 25
Acquirer: HUDSON'S BAY COMPANy
DateAnnounced: 2013-07-29 00:00:00
URL: https://www.sec.gov/Archives/edgar/data/812900/0001193125-13-390275-index.htm...
  [0.3] | note=IB | bidder=Goldman Sachs | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2012-12-15 00:00:00 | date_p=NA | cash=NA | c1=For the past several years, Goldman Sachs, one of Saks’ long
  [0.5] | note=Bidder Interest | bidder=Sponsor A | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2013-02-15 00:00:00 | date_p=NA | cash=NA | c1=In February 2013
  [1] | note=NA | bidder=Hudson's Bay | type=Non-US public S | bid_type=Informal | val=NA | range=15-NA | date_r=2013-04-15 00:00:00 | date_p=NA | cash=1 | c1=Legal counsel: Wachtell Lipton
  [2] | note=NA | bidder=Sponsor A | type=F | bid_type=Informal | val=NA | range=15-NA | date_r=2013-04-15 00:00:00 | date_p=NA | cash=1
  [3] | note=Drop | bidder=Sponsor A | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2013-04-26 00:00:00 | date_p=2013-04-26 00:00:00 | cash=NA
  [4] | note=NDA | bidder=Sponsor A | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2013-04-26 00:00:00 | date_p=2013-04-26 00:00:00 | cash=NA
  [5] | note=NDA | bidder=Sponsor E | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2013-04-26 00:00:00 | date_p=2013-04-26 00:00:00 | cash=NA
  [6] | note=NDA | bidder=Hudson's Bay | type=Non-US public S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-04-30 00:00:00 | date_p=2013-04-30 00:00:00 | cash=NA
  [7] | note=NA | bidder=Hudson's Bay | type=Non-US public S | bid_type=Informal | val=15 | range=15-15.25 | date_r=2013-06-03 00:00:00 | date_p=NA | cash=1 | c1=In late May 2013, media reports began to appear stating that
  [8] | note=NA | bidder=Sponsor A/E | type=F | bid_type=Informal | val=15 | range=15-16 | date_r=2013-06-03 00:00:00 | date_p=NA | cash=1
  [9] | note=Final Round Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-07-02 00:00:00 | date_p=2013-07-02 00:00:00 | cash=NA
  [10] | note=Drop | bidder=Sponsor A/E | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2013-07-07 00:00:00 | date_p=NA | cash=NA | c1=[This clearly happened after Final Round Ann -- so the day i
  [11] | note=NDA | bidder=Sponsor G | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2013-07-08 00:00:00 | date_p=2013-07-08 00:00:00 | cash=NA
  [12] | note=NA | bidder=Hudson's Bay | type=Non-US public S | bid_type=Formal | val=15.25 | range=15.25-15.25 | date_r=2013-07-11 00:00:00 | date_p=2013-07-11 00:00:00 | cash=1 | c1=formal, with committed debt and equity financing
  [13] | note=NA | bidder=Sponsor A/E | type=F | bid_type=Informal | val=14.5 | range=14.5-15.5 | date_r=2013-07-11 00:00:00 | date_p=2013-07-11 00:00:00 | cash=1 | c1=Several weeks of DD required, no availability of financing
  [13.5] | note=Final Round | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-07-11 00:00:00 | date_p=2013-07-02 00:00:00 | cash=NA
  [14] | note=Drop | bidder=Sponsor G | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=NA | date_p=NA | cash=NA
  [15] | note=NA | bidder=Company H | type=S | bid_type=Informal | val=NA | range=2.6-2.6 | date_r=2013-07-21 00:00:00 | date_p=2013-07-21 00:00:00 | cash=1 | c1=Should be deleted: unsolicited letter, no NDA, no further co
  [16] | note=Drop | bidder=Company H | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=NA | date_p=NA | cash=NA
  [17] | note=NA | bidder=Sponsor A/E | type=F | bid_type=Informal | val=14.5 | range=14.5-15.5 | date_r=2013-07-22 00:00:00 | date_p=NA | cash=1 | c1=Not a separate bid, should be deleted
  [18] | note=NA | bidder=Hudson's Bay | type=Non-US public S | bid_type=Formal | val=16 | range=16-16 | date_r=2013-07-24 00:00:00 | date_p=2013-07-24 00:00:00 | cash=1
  [19] | note=DropTarget | bidder=Spnosor A/E | type=F | bid_type=NA | val=NA | range=NA-NA | date_r=2013-07-28 00:00:00 | date_p=2013-07-28 00:00:00 | cash=NA
  [19.5] | note=Executed | bidder=Hudson's Bay | type=Non-US public S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-07-28 00:00:00 | date_p=NA | cash=NA
  [20] | note=NDA | bidder=Company I | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-07-29 00:00:00 | date_p=NA | cash=NA | c1=Go-shop until Sep 6
  [21] | note=Drop | bidder=Company I | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-09-06 00:00:00 | date_p=2013-09-06 00:00:00 | cash=NA

================================================================================
DEAL: STec (starting at Excel row 7144)
================================================================================
TargetName: S T E C INC
Events: 28
Acquirer: WESTERN DIGITAL CORP
DateAnnounced: 2013-06-24 00:00:00
URL: https://www.sec.gov/Archives/edgar/data/1102741/0001193125-13-325730-index.htm...
  [0.5] | note=Bidder Interest | bidder=Company B | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-02-13 00:00:00 | date_p=2013-04-04 00:00:00 | cash=NA | c1=Approximately two weeks later, the President of Company B co
  [0.7] | note=Bidder Interest | bidder=Company D | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-03-15 00:00:00 | date_p=2013-04-04 00:00:00 | cash=NA | c1=In mid-March, 2013, the head of corporate development for Co
  [0.8] | note=IB | bidder=BofA Merrill Lynch | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-03-28 00:00:00 | date_p=2013-04-04 00:00:00 | cash=NA | c1=On March 26, a board meeting discussed "the lack of interest
  [1] | note=NDA | bidder=Company E | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-04-04 00:00:00 | date_p=2013-04-04 00:00:00 | cash=NA | c1=Legal counsel: Gibson Dunn
  [2] | note=NDA | bidder=Company D | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-04-10 00:00:00 | date_p=2013-04-10 00:00:00 | cash=NA
  [3] | note=NDA | bidder=Company F | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-04-11 00:00:00 | date_p=2013-04-11 00:00:00 | cash=NA
  [4] | note=NDA | bidder=Company G | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-04-17 00:00:00 | date_p=2013-04-17 00:00:00 | cash=NA
  [5] | note=NDA | bidder=WDC | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-04-17 00:00:00 | date_p=2013-04-17 00:00:00 | cash=NA
  [5.5] | note=Final Round Inf Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-04-23 00:00:00 | date_p=2013-04-23 00:00:00 | cash=NA
  [5.7] | note=NA | bidder=Company D | type=S | bid_type=Informal | val=NA | range=5.6-NA | date_r=2013-04-23 00:00:00 | date_p=2013-04-23 00:00:00 | cash=NA
  [6] | note=DropTarget | bidder=Company F | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-04-24 00:00:00 | date_p=2013-04-24 00:00:00 | cash=NA | c1=indicated it was also only interested in purchasing limited,
  [7] | note=DropTarget | bidder=Company E | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-04-24 00:00:00 | date_p=2013-04-24 00:00:00 | cash=NA | c1=indicated it was also only interested in purchasing limited,
  [9] | note=NA | bidder=WDC | type=S | bid_type=Informal | val=6.6 | range=6.6-7.1 | date_r=2013-05-03 00:00:00 | date_p=2013-05-03 00:00:00 | cash=1
  [10] | note=Drop | bidder=Company G | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-05-03 00:00:00 | date_p=2013-05-03 00:00:00 | cash=NA | c1=Indicated it would not continue the process
  [10.5] | note=Final Round Inf | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-05-03 00:00:00 | date_p=2013-04-23 00:00:00 | cash=NA
  [11] | note=NDA | bidder=Company H | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-05-08 00:00:00 | date_p=2013-05-08 00:00:00 | cash=NA
  [12] | note=NA | bidder=Company D | type=S | bid_type=Informal | val=5.75 | range=5.75-5.75 | date_r=2013-05-10 00:00:00 | date_p=2013-05-10 00:00:00 | cash=1
  [13] | note=NA | bidder=Company H | type=S | bid_type=Informal | val=5 | range=5-5.75 | date_r=2013-05-15 00:00:00 | date_p=2013-05-15 00:00:00 | cash=1
  [14] | note=Final Round Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-05-16 00:00:00 | date_p=2013-05-16 00:00:00 | cash=NA
  [15] | note=Drop | bidder=Company H | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-05-23 00:00:00 | date_p=2013-05-23 00:00:00 | cash=NA | c1=Indicated it is not able to increase its indicated value ran
  [16] | note=NA | bidder=WDC | type=S | bid_type=Formal | val=9.15 | range=9.15-9.15 | date_r=2013-05-28 00:00:00 | date_p=2013-05-28 00:00:00 | cash=1 | c1=various interesting covenants, e.g. not to sue by target CEO
  [16.5] | note=Final Round | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-05-28 00:00:00 | date_p=2013-05-16 00:00:00 | cash=NA
  [16.6] | note=Final Round Ext Ann | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-05-28 00:00:00 | date_p=2013-05-16 00:00:00 | cash=NA | c1=For Company D
  [16.7] | note=Final Round Ext | bidder=NA | type=NA | bid_type=NA | val=NA | range=NA-NA | date_r=2013-05-30 00:00:00 | date_p=2013-05-16 00:00:00 | cash=NA | c1=Later extended until 6/10/2023 as WDC was thinking about dro
  [17] | note=Drop | bidder=Company D | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-06-05 00:00:00 | date_p=2013-06-05 00:00:00 | cash=NA | c1=Company D would not be in a position to actively conduct due
  [18] | note=NA | bidder=WDC | type=S | bid_type=Informal | val=6.6 | range=6.6-7.1 | date_r=2013-06-10 00:00:00 | date_p=2013-06-10 00:00:00 | cash=1 | c1=WDC had given serious consideration to not proceeding with a | c2=The board of directors’ disappointment in the latest proposa
  [19] | note=NA | bidder=WDC | type=S | bid_type=Formal | val=6.85 | range=6.85-6.85 | date_r=2013-06-14 00:00:00 | date_p=2013-06-14 00:00:00 | cash=1 | c1=From June 16 to June 22, 2013, WDC conducted additional due 
  [20] | note=Executed | bidder=WDC | type=S | bid_type=NA | val=NA | range=NA-NA | date_r=2013-06-23 00:00:00 | date_p=2013-06-14 00:00:00 | cash=NA | c1=From June 16 to June 22, 2013, WDC conducted additional due 
