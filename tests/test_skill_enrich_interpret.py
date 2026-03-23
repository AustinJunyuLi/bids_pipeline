from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from skill_pipeline import cli


def _write_enrich_interpret_fixture(tmp_path: Path, *, slug: str = "imprivata") -> None:
    data_dir = tmp_path / "data"
    source_dir = data_dir / "deals" / slug / "source"
    materialize_dir = data_dir / "skill" / slug / "materialize"
    enrich_dir = data_dir / "skill" / slug / "enrich"

    source_dir.mkdir(parents=True, exist_ok=True)
    materialize_dir.mkdir(parents=True, exist_ok=True)
    enrich_dir.mkdir(parents=True, exist_ok=True)

    (source_dir / "chronology_blocks.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "block_id": "B001",
                        "document_id": "DOC001",
                        "ordinal": 1,
                        "start_line": 1,
                        "end_line": 1,
                        "raw_text": "The board began exploring strategic alternatives.",
                        "clean_text": "The board began exploring strategic alternatives.",
                        "is_heading": False,
                        "page_break_before": False,
                        "page_break_after": False,
                    }
                ),
                json.dumps(
                    {
                        "block_id": "B002",
                        "document_id": "DOC001",
                        "ordinal": 2,
                        "start_line": 2,
                        "end_line": 2,
                        "raw_text": "Party A submitted an indication of interest.",
                        "clean_text": "Party A submitted an indication of interest.",
                        "is_heading": False,
                        "page_break_before": False,
                        "page_break_after": False,
                    }
                ),
                json.dumps(
                    {
                        "block_id": "B003",
                        "document_id": "DOC001",
                        "ordinal": 3,
                        "start_line": 3,
                        "end_line": 3,
                        "raw_text": "The Company informed Party A that it would not be invited to submit a final bid.",
                        "clean_text": "The Company informed Party A that it would not be invited to submit a final bid.",
                        "is_heading": False,
                        "page_break_before": False,
                        "page_break_after": False,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    (materialize_dir / "actors.json").write_text(
        json.dumps(
            {
                "actors": [
                    {
                        "actor_id": "party_a",
                        "display_name": "Party A",
                        "canonical_name": "PARTY A",
                        "aliases": [],
                        "role": "bidder",
                        "advisor_kind": None,
                        "advised_actor_id": None,
                        "bidder_kind": "financial",
                        "listing_status": "private",
                        "geography": "domestic",
                        "is_grouped": False,
                        "group_size": None,
                        "group_label": None,
                        "evidence_span_ids": ["span_0001"],
                        "notes": [],
                    },
                    {
                        "actor_id": "advisor_001",
                        "display_name": "XYZ Advisors",
                        "canonical_name": "XYZ ADVISORS",
                        "aliases": [],
                        "role": "advisor",
                        "advisor_kind": "financial",
                        "advised_actor_id": None,
                        "bidder_kind": None,
                        "listing_status": None,
                        "geography": None,
                        "is_grouped": False,
                        "group_size": None,
                        "group_label": None,
                        "evidence_span_ids": ["span_0004"],
                        "notes": [],
                    },
                ],
                "count_assertions": [
                    {
                        "subject": "nda_signers",
                        "count": 2,
                        "evidence_span_ids": ["span_0005"],
                    }
                ],
                "unresolved_mentions": [],
            }
        ),
        encoding="utf-8",
    )
    (materialize_dir / "events.json").write_text(
        json.dumps(
            {
                "events": [
                    {
                        "event_id": "evt_001",
                        "event_type": "target_sale",
                        "date": {
                            "raw_text": "July 1, 2016",
                            "normalized_start": "2016-07-01",
                            "normalized_end": "2016-07-01",
                            "sort_date": "2016-07-01",
                            "precision": "exact_day",
                            "anchor_event_id": None,
                            "anchor_span_id": None,
                            "resolution_note": None,
                            "is_inferred": False,
                        },
                        "actor_ids": [],
                        "summary": "Board began exploring strategic alternatives.",
                        "evidence_span_ids": ["span_0002"],
                        "terms": None,
                        "formality_signals": None,
                        "whole_company_scope": True,
                        "drop_reason_text": None,
                        "round_scope": None,
                        "invited_actor_ids": [],
                        "deadline_date": None,
                        "executed_with_actor_id": None,
                        "boundary_note": None,
                        "nda_signed": None,
                        "notes": [],
                    },
                    {
                        "event_id": "evt_002",
                        "event_type": "proposal",
                        "date": {
                            "raw_text": "July 5, 2016",
                            "normalized_start": "2016-07-05",
                            "normalized_end": "2016-07-05",
                            "sort_date": "2016-07-05",
                            "precision": "exact_day",
                            "anchor_event_id": None,
                            "anchor_span_id": None,
                            "resolution_note": None,
                            "is_inferred": False,
                        },
                        "actor_ids": ["party_a"],
                        "summary": "Party A submitted an indication of interest.",
                        "evidence_span_ids": ["span_0003"],
                        "terms": {
                            "per_share": 25.0,
                            "range_low": None,
                            "range_high": None,
                            "enterprise_value": None,
                            "consideration_type": "cash",
                        },
                        "formality_signals": {
                            "contains_range": False,
                            "mentions_indication_of_interest": True,
                            "mentions_preliminary": False,
                            "mentions_non_binding": False,
                            "mentions_binding_offer": False,
                            "includes_draft_merger_agreement": False,
                            "includes_marked_up_agreement": False,
                            "requested_binding_offer_via_process_letter": False,
                            "after_final_round_announcement": False,
                            "after_final_round_deadline": False,
                            "is_subject_to_financing": None,
                        },
                        "whole_company_scope": True,
                        "drop_reason_text": None,
                        "round_scope": None,
                        "invited_actor_ids": [],
                        "deadline_date": None,
                        "executed_with_actor_id": None,
                        "boundary_note": None,
                        "nda_signed": None,
                        "notes": [],
                    },
                    {
                        "event_id": "evt_003",
                        "event_type": "drop",
                        "date": {
                            "raw_text": "July 10, 2016",
                            "normalized_start": "2016-07-10",
                            "normalized_end": "2016-07-10",
                            "sort_date": "2016-07-10",
                            "precision": "exact_day",
                            "anchor_event_id": None,
                            "anchor_span_id": None,
                            "resolution_note": None,
                            "is_inferred": False,
                        },
                        "actor_ids": ["party_a"],
                        "summary": "Party A was excluded from the next round.",
                        "evidence_span_ids": ["span_0006"],
                        "terms": None,
                        "formality_signals": None,
                        "whole_company_scope": True,
                        "drop_reason_text": "The Company informed Party A that it would not be invited to submit a final bid.",
                        "round_scope": None,
                        "invited_actor_ids": [],
                        "deadline_date": None,
                        "executed_with_actor_id": None,
                        "boundary_note": None,
                        "nda_signed": None,
                        "notes": [],
                    },
                ],
                "exclusions": [],
                "coverage_notes": [],
            }
        ),
        encoding="utf-8",
    )
    (materialize_dir / "spans.json").write_text(
        json.dumps(
            {
                "spans": [
                    {
                        "span_id": "span_0001",
                        "document_id": "DOC001",
                        "accession_number": "DOC001",
                        "filing_type": "DEFM14A",
                        "start_line": 2,
                        "end_line": 2,
                        "start_char": 1,
                        "end_char": 7,
                        "block_ids": ["B002"],
                        "evidence_ids": [],
                        "anchor_text": "Party A",
                        "quote_text": "Party A submitted an indication of interest.",
                        "quote_text_normalized": "party a submitted an indication of interest.",
                        "match_type": "exact",
                        "resolution_note": None,
                    },
                    {
                        "span_id": "span_0002",
                        "document_id": "DOC001",
                        "accession_number": "DOC001",
                        "filing_type": "DEFM14A",
                        "start_line": 1,
                        "end_line": 1,
                        "start_char": 1,
                        "end_char": 10,
                        "block_ids": ["B001"],
                        "evidence_ids": [],
                        "anchor_text": "strategic alternatives",
                        "quote_text": "The board began exploring strategic alternatives.",
                        "quote_text_normalized": "the board began exploring strategic alternatives.",
                        "match_type": "exact",
                        "resolution_note": None,
                    },
                    {
                        "span_id": "span_0003",
                        "document_id": "DOC001",
                        "accession_number": "DOC001",
                        "filing_type": "DEFM14A",
                        "start_line": 2,
                        "end_line": 2,
                        "start_char": 1,
                        "end_char": 18,
                        "block_ids": ["B002"],
                        "evidence_ids": [],
                        "anchor_text": "submitted an indication of interest",
                        "quote_text": "Party A submitted an indication of interest.",
                        "quote_text_normalized": "party a submitted an indication of interest.",
                        "match_type": "exact",
                        "resolution_note": None,
                    },
                    {
                        "span_id": "span_0004",
                        "document_id": "DOC001",
                        "accession_number": "DOC001",
                        "filing_type": "DEFM14A",
                        "start_line": 1,
                        "end_line": 1,
                        "start_char": 1,
                        "end_char": 12,
                        "block_ids": ["B001"],
                        "evidence_ids": [],
                        "anchor_text": "XYZ Advisors",
                        "quote_text": "XYZ Advisors acted as financial advisor to the Company.",
                        "quote_text_normalized": "xyz advisors acted as financial advisor to the company.",
                        "match_type": "exact",
                        "resolution_note": None,
                    },
                    {
                        "span_id": "span_0005",
                        "document_id": "DOC001",
                        "accession_number": "DOC001",
                        "filing_type": "DEFM14A",
                        "start_line": 1,
                        "end_line": 1,
                        "start_char": 1,
                        "end_char": 10,
                        "block_ids": ["B001"],
                        "evidence_ids": [],
                        "anchor_text": "two parties signed confidentiality agreements",
                        "quote_text": "Two parties signed confidentiality agreements.",
                        "quote_text_normalized": "two parties signed confidentiality agreements.",
                        "match_type": "exact",
                        "resolution_note": None,
                    },
                    {
                        "span_id": "span_0006",
                        "document_id": "DOC001",
                        "accession_number": "DOC001",
                        "filing_type": "DEFM14A",
                        "start_line": 3,
                        "end_line": 3,
                        "start_char": 1,
                        "end_char": 20,
                        "block_ids": ["B003"],
                        "evidence_ids": [],
                        "anchor_text": "would not be invited to submit a final bid",
                        "quote_text": "The Company informed Party A that it would not be invited to submit a final bid.",
                        "quote_text_normalized": "the company informed party a that it would not be invited to submit a final bid.",
                        "match_type": "exact",
                        "resolution_note": None,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (enrich_dir / "deterministic_enrichment.json").write_text(
        json.dumps(
            {
                "rounds": [],
                "bid_classifications": {
                    "evt_002": {
                        "label": "Informal",
                        "rule_applied": 1,
                        "basis": "Observable informal signal from formality_signals.",
                    }
                },
                "cycles": [
                    {
                        "cycle_id": "cycle_1",
                        "start_event_id": "evt_001",
                        "end_event_id": "evt_003",
                        "boundary_basis": "Single cycle -- no termination events",
                    }
                ],
                "formal_boundary": {
                    "cycle_1": {
                        "event_id": None,
                        "basis": "No formal proposals in this cycle.",
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def test_skill_cli_supports_enrich_interpret_subcommand() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["enrich-interpret", "--deal", "imprivata"])

    assert args.command == "enrich-interpret"
    assert args.deal == "imprivata"


def test_run_enrich_interpret_merges_outputs_into_final_enrichment(
    tmp_path: Path,
) -> None:
    from skill_pipeline.stages.enrich.interpret import (
        AdvisoryVerificationOutput,
        CountReconciliationOutput,
        DropoutClassificationsOutput,
        run_enrich_interpret,
    )
    from skill_pipeline.schemas.runtime import (
        AdvisoryVerificationRecord,
        CountReconciliationRecord,
        DropoutClassification,
        InitiationJudgment,
    )

    _write_enrich_interpret_fixture(tmp_path)

    with patch(
        "skill_pipeline.stages.enrich.interpret.invoke_structured",
        side_effect=[
            DropoutClassificationsOutput(
                dropout_classifications={
                    "evt_003": DropoutClassification(
                        label="DropTarget",
                        basis="Target excluded Party A from the next round.",
                        source_text="would not be invited to submit a final bid",
                    )
                }
            ),
            InitiationJudgment(
                type="target_driven",
                basis="The board began exploring strategic alternatives before bidder contact.",
                source_text="The board began exploring strategic alternatives.",
                confidence="high",
            ),
            AdvisoryVerificationOutput(
                advisory_verification={
                    "advisor_001": AdvisoryVerificationRecord(
                        advised_actor_id=None,
                        verified=False,
                        source_text="XYZ Advisors acted as financial advisor to the Company.",
                    )
                }
            ),
            CountReconciliationOutput(
                count_reconciliation=[
                    CountReconciliationRecord(
                        assertion="nda_signers",
                        extracted_count=1,
                        classification="unresolved",
                        note="One NDA signer remains unaccounted for.",
                    )
                ]
            ),
        ],
    ) as mock_invoke:
        result = run_enrich_interpret("imprivata", project_root=tmp_path)

    assert result == 0
    assert mock_invoke.call_count == 4

    enrichment_path = (
        tmp_path / "data" / "skill" / "imprivata" / "enrich" / "enrichment.json"
    )
    payload = json.loads(enrichment_path.read_text(encoding="utf-8"))

    assert payload["bid_classifications"]["evt_002"]["label"] == "Informal"
    assert payload["dropout_classifications"]["evt_003"]["label"] == "DropTarget"
    assert payload["initiation_judgment"]["type"] == "target_driven"
    assert payload["advisory_verification"]["advisor_001"]["verified"] is False
    assert payload["count_reconciliation"][0]["classification"] == "unresolved"
    assert "advisory_missing_link:advisor_001" in payload["review_flags"]
    assert "count_reconciliation_unresolved:0" in payload["review_flags"]
