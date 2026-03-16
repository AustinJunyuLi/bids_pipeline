from datetime import date

from pipeline.models.common import DatePrecision
from pipeline.normalize.dates import parse_date_value


def test_parse_exact_day_date():
    parsed = parse_date_value("March 9, 2016")

    assert parsed.precision == DatePrecision.EXACT_DAY
    assert parsed.normalized_start == date(2016, 3, 9)
    assert parsed.normalized_end == date(2016, 3, 9)
    assert parsed.sort_date == date(2016, 3, 9)


def test_parse_mid_month_date():
    parsed = parse_date_value("mid-February 2013")

    assert parsed.precision == DatePrecision.MONTH_MID
    assert parsed.normalized_start == date(2013, 2, 11)
    assert parsed.normalized_end == date(2013, 2, 20)
    assert parsed.sort_date == date(2013, 2, 15)


def test_parse_month_only_date():
    parsed = parse_date_value("June 2014")

    assert parsed.precision == DatePrecision.MONTH
    assert parsed.normalized_start == date(2014, 6, 1)
    assert parsed.normalized_end == date(2014, 6, 30)
    assert parsed.sort_date == date(2014, 6, 1)


def test_parse_quarter_reference():
    parsed = parse_date_value("third quarter 2015")

    assert parsed.precision == DatePrecision.QUARTER
    assert parsed.normalized_start == date(2015, 7, 1)
    assert parsed.normalized_end == date(2015, 9, 30)
    assert parsed.sort_date == date(2015, 7, 1)


def test_parse_relative_date_anchored_to_prior_event():
    anchor = parse_date_value("March 9, 2016")
    parsed = parse_date_value(
        "the following day",
        anchor_date=anchor,
        anchor_event_id="event-1",
    )

    assert parsed.precision == DatePrecision.RELATIVE
    assert parsed.normalized_start == date(2016, 3, 10)
    assert parsed.normalized_end == date(2016, 3, 10)
    assert parsed.sort_date == date(2016, 3, 10)
    assert parsed.anchor_event_id == "event-1"
    assert parsed.is_inferred is True
