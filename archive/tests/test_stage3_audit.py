import unittest

from pipeline.schemas import Event, EventActorLink, ProcessCycle, Round
from pipeline.stage3_audit import check_proposal_completeness


class ProposalCompletenessAuditTests(unittest.TestCase):
    def test_counts_same_day_responses_after_deadline_line_order(self) -> None:
        events = [
            Event(
                event_id="evt_announce",
                event_type="final_round_ann",
                date="2020-01-01",
                date_precision="exact",
                source_accession_number="0000000000-00-000001",
                source_line_start=10,
                source_line_end=10,
                source_text="The company announced the final round.",
            ),
            Event(
                event_id="evt_deadline",
                event_type="final_round",
                date="2020-01-02",
                date_precision="exact",
                source_accession_number="0000000000-00-000001",
                source_line_start=20,
                source_line_end=20,
                source_text="Final bids were due on January 2, 2020.",
            ),
            Event(
                event_id="evt_proposal",
                event_type="proposal",
                date="2020-01-02",
                date_precision="exact",
                value=10.0,
                value_lower=10.0,
                value_upper=10.0,
                value_unit="per_share",
                consideration_type="cash",
                source_accession_number="0000000000-00-000001",
                source_line_start=30,
                source_line_end=30,
                source_text="Bidder A submitted a proposal on January 2, 2020.",
            ),
            Event(
                event_id="evt_drop",
                event_type="drop",
                date="2020-01-02",
                date_precision="exact",
                source_accession_number="0000000000-00-000001",
                source_line_start=40,
                source_line_end=40,
                source_text="Bidder B dropped out on January 2, 2020.",
            ),
        ]
        links = [
            EventActorLink(event_id="evt_proposal", actor_id="bidder/a", participation_role="bidder"),
            EventActorLink(event_id="evt_drop", actor_id="bidder/b", participation_role="bidder"),
        ]
        cycles = [
            ProcessCycle(
                cycle_id="deal_c1",
                cycle_sequence=1,
                start_event_id="evt_announce",
                end_event_id="evt_drop",
                status="completed",
                segmentation_basis="single cycle",
                rounds=[
                    Round(
                        round_id="deal_r1",
                        announcement_event_id="evt_announce",
                        deadline_event_id="evt_deadline",
                        invited_set=["bidder/a", "bidder/b"],
                        source_text="The company invited bidders A and B.",
                    )
                ],
            )
        ]

        result = check_proposal_completeness(events, links, cycles)

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.failures, [])

    def test_does_not_count_responses_after_deadline_date(self) -> None:
        events = [
            Event(
                event_id="evt_announce",
                event_type="final_round_ann",
                date="2020-01-01",
                date_precision="exact",
                source_accession_number="0000000000-00-000001",
                source_line_start=10,
                source_line_end=10,
                source_text="The company announced the final round.",
            ),
            Event(
                event_id="evt_deadline",
                event_type="final_round",
                date="2020-01-02",
                date_precision="exact",
                source_accession_number="0000000000-00-000001",
                source_line_start=20,
                source_line_end=20,
                source_text="Final bids were due on January 2, 2020.",
            ),
            Event(
                event_id="evt_proposal",
                event_type="proposal",
                date="2020-01-03",
                date_precision="exact",
                value=10.0,
                value_lower=10.0,
                value_upper=10.0,
                value_unit="per_share",
                consideration_type="cash",
                source_accession_number="0000000000-00-000001",
                source_line_start=30,
                source_line_end=30,
                source_text="Bidder A submitted a proposal on January 3, 2020.",
            ),
        ]
        links = [EventActorLink(event_id="evt_proposal", actor_id="bidder/a", participation_role="bidder")]
        cycles = [
            ProcessCycle(
                cycle_id="deal_c1",
                cycle_sequence=1,
                start_event_id="evt_announce",
                end_event_id="evt_proposal",
                status="completed",
                segmentation_basis="single cycle",
                rounds=[
                    Round(
                        round_id="deal_r1",
                        announcement_event_id="evt_announce",
                        deadline_event_id="evt_deadline",
                        invited_set=["bidder/a"],
                        source_text="The company invited bidder A.",
                    )
                ],
            )
        ]

        result = check_proposal_completeness(events, links, cycles)

        self.assertEqual(result.status, "needs_review")
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(result.failures[0].actor_id, "bidder/a")


if __name__ == "__main__":
    unittest.main()
