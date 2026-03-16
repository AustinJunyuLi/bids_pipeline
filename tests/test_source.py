from pipeline.source import _atomic_write_text, _search_terms_for_form, locate_chronology


FAKE_FILING = """
TABLE OF CONTENTS

Background of the Merger............................15

BACKGROUND OF THE MERGER

On January 15, 2015, the Board of Directors of the Company met to discuss
strategic alternatives. Representatives of Goldman Sachs presented a
preliminary analysis of potential transaction structures.

On February 1, 2015, Party A submitted an indication of interest at $25.00
per share. On February 5, 2015, Party B submitted an indication of interest
at $23.00 to $25.00 per share.

OPINION OF GOLDMAN SACHS & CO. LLC

Goldman Sachs rendered its oral opinion to the Board.
""".strip()


def test_locate_chronology_finds_real_section():
    lines = FAKE_FILING.splitlines()
    result = locate_chronology(lines)
    assert result is not None
    start, end, heading = result
    assert "BACKGROUND OF THE MERGER" in heading
    assert start > 3
    assert end > start


def test_locate_chronology_rejects_toc():
    lines = FAKE_FILING.splitlines()
    start, end, _heading = locate_chronology(lines)
    section = "\n".join(lines[start : end + 1])
    assert "January 15, 2015" in section


def test_atomic_write_text_replaces_existing_contents(tmp_path):
    output_path = tmp_path / "snapshot.txt"
    output_path.write_text("old", encoding="utf-8")

    _atomic_write_text(output_path, "new")

    assert output_path.read_text(encoding="utf-8") == "new"


MEDIVATION_LIKE_FILING = """
SUMMARY TERM SHEET

THE TENDER OFFER - Section 10 ("Background of the Offer; Past Contacts or Negotiations with Medivation")

Item 4. The Solicitation or Recommendation.

(i) Background of Offer and Merger

The Medivation board of directors frequently reviewed strategic alternatives.

On March 22, 2016, Olivier Brandicourt contacted David Hung.

On March 24, 2016, the board met with J. P. Morgan and Cooley.

On March 25, 2016, Sanofi expressed interest in a strategic transaction.

Certain Projections
""".strip()


ZEP_LIKE_FILING = """
See "The Merger - Background of the Merger" for more information.

Go-Shop Period

During the go-shop period, the company considered strategic alternatives.

submitted by such person is withdrawn or terminated. As disclosed under "Background of the Merger," the go-shop period ended at 11:59 p.m. on May 7, 2015.

Background of the Merger

The following chronology summarizes material key events and contacts.

At a June 20, 2013 meeting, the board discussed strategic alternatives.

At a July 1, 2013 meeting, the board agreed to explore a potential sale.

Opinion of Financial Advisor
""".strip()


def test_locate_chronology_prefers_real_heading_over_cross_reference():
    lines = MEDIVATION_LIKE_FILING.splitlines()
    start, end, heading = locate_chronology(lines)

    assert heading == "(i) Background of Offer and Merger"
    assert "Olivier Brandicourt" in "\n".join(lines[start : end + 1])


def test_locate_chronology_rejects_sentence_level_reference():
    lines = ZEP_LIKE_FILING.splitlines()
    start, end, heading = locate_chronology(lines)

    assert heading == "Background of the Merger"
    assert start > 4
    assert "June 20, 2013" in "\n".join(lines[start : end + 1])


def test_search_terms_include_sc_14d9_alias():
    assert _search_terms_for_form("SC 14D-9") == ("SC 14D-9", "SC 14D9")
