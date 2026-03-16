from pipeline.source import _atomic_write_text, locate_chronology


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
