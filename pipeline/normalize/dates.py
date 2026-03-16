from __future__ import annotations

import calendar
import re
from datetime import date, timedelta

from pipeline.models.common import DatePrecision
from pipeline.models.extraction import DateValue


MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

EXACT_DAY_RE = re.compile(
    r"(?i)\b("
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    r")\s+(\d{1,2}),\s+(\d{4})\b"
)
PARTIAL_MONTH_RE = re.compile(
    r"(?i)\b(early|mid|late)[-\s]+("
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    r")\s+(\d{4})\b"
)
MONTH_ONLY_RE = re.compile(
    r"(?i)\b("
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    r")\s+(\d{4})\b"
)
QUARTER_RE = re.compile(
    r"(?i)\b(first|1st|second|2nd|third|3rd|fourth|4th|q[1-4])\s+quarter\s+(\d{4})\b|\b(q[1-4])\s+(\d{4})\b"
)
YEAR_RE = re.compile(r"^\s*(\d{4})\s*$")


def parse_date_value(
    raw_text: str,
    *,
    anchor_date: DateValue | date | None = None,
    anchor_event_id: str | None = None,
) -> DateValue:
    text = raw_text.strip()

    exact_match = EXACT_DAY_RE.search(text)
    if exact_match:
        month = MONTHS[exact_match.group(1).lower()]
        day = int(exact_match.group(2))
        year = int(exact_match.group(3))
        parsed = date(year, month, day)
        return _make_date_value(
            raw_text=text,
            normalized_start=parsed,
            normalized_end=parsed,
            sort_date=parsed,
            precision=DatePrecision.EXACT_DAY,
        )

    partial_match = PARTIAL_MONTH_RE.search(text)
    if partial_match:
        modifier = partial_match.group(1).lower()
        month = MONTHS[partial_match.group(2).lower()]
        year = int(partial_match.group(3))
        last_day = calendar.monthrange(year, month)[1]
        if modifier == "early":
            start_day, end_day, sort_day = 1, min(10, last_day), 5
            precision = DatePrecision.MONTH_EARLY
        elif modifier == "mid":
            start_day, end_day, sort_day = 11, min(20, last_day), 15
            precision = DatePrecision.MONTH_MID
        else:
            start_day, end_day, sort_day = 21, last_day, min(25, last_day)
            precision = DatePrecision.MONTH_LATE
        return _make_date_value(
            raw_text=text,
            normalized_start=date(year, month, start_day),
            normalized_end=date(year, month, end_day),
            sort_date=date(year, month, sort_day),
            precision=precision,
        )

    month_match = MONTH_ONLY_RE.search(text)
    if month_match:
        month = MONTHS[month_match.group(1).lower()]
        year = int(month_match.group(2))
        last_day = calendar.monthrange(year, month)[1]
        return _make_date_value(
            raw_text=text,
            normalized_start=date(year, month, 1),
            normalized_end=date(year, month, last_day),
            sort_date=date(year, month, 1),
            precision=DatePrecision.MONTH,
        )

    quarter_match = QUARTER_RE.search(text)
    if quarter_match:
        quarter_token = quarter_match.group(1) or quarter_match.group(3)
        year_text = quarter_match.group(2) or quarter_match.group(4)
        quarter = _quarter_number(quarter_token.lower())
        year = int(year_text)
        start_month = 1 + (quarter - 1) * 3
        end_month = start_month + 2
        last_day = calendar.monthrange(year, end_month)[1]
        return _make_date_value(
            raw_text=text,
            normalized_start=date(year, start_month, 1),
            normalized_end=date(year, end_month, last_day),
            sort_date=date(year, start_month, 1),
            precision=DatePrecision.QUARTER,
        )

    relative = _parse_relative_date(text, anchor_date=anchor_date, anchor_event_id=anchor_event_id)
    if relative is not None:
        return relative

    year_match = YEAR_RE.search(text)
    if year_match:
        year = int(year_match.group(1))
        return _make_date_value(
            raw_text=text,
            normalized_start=date(year, 1, 1),
            normalized_end=date(year, 12, 31),
            sort_date=date(year, 1, 1),
            precision=DatePrecision.YEAR,
        )

    return _make_date_value(
        raw_text=text,
        normalized_start=None,
        normalized_end=None,
        sort_date=None,
        precision=DatePrecision.UNKNOWN,
        resolution_note="Unable to parse date deterministically.",
    )


def parse_date_values(
    raw_texts: list[str],
    *,
    anchor_date: DateValue | date | None = None,
    anchor_event_id: str | None = None,
) -> list[DateValue]:
    return [
        parse_date_value(
            raw_text,
            anchor_date=anchor_date,
            anchor_event_id=anchor_event_id,
        )
        for raw_text in raw_texts
    ]


def _parse_relative_date(
    text: str,
    *,
    anchor_date: DateValue | date | None,
    anchor_event_id: str | None,
) -> DateValue | None:
    anchor = _extract_anchor_date(anchor_date)
    if anchor is None:
        return None

    lowered = text.lower()
    delta_days = None
    if lowered in {"later that day", "that day", "same day"}:
        delta_days = 0
    elif lowered in {"the following day", "the next day", "next day", "one day later"}:
        delta_days = 1
    elif lowered == "two days later":
        delta_days = 2
    elif lowered == "three days later":
        delta_days = 3
    elif lowered in {"the following week", "the next week", "one week later"}:
        delta_days = 7

    if delta_days is None:
        return None

    resolved = anchor + timedelta(days=delta_days)
    return _make_date_value(
        raw_text=text,
        normalized_start=resolved,
        normalized_end=resolved,
        sort_date=resolved,
        precision=DatePrecision.RELATIVE,
        anchor_event_id=anchor_event_id,
        resolution_note=f"Resolved relative date from anchor {anchor.isoformat()}.",
        is_inferred=True,
    )


def _extract_anchor_date(anchor_date: DateValue | date | None) -> date | None:
    if isinstance(anchor_date, date):
        return anchor_date
    if anchor_date is None:
        return None
    return anchor_date.sort_date or anchor_date.normalized_start


def _quarter_number(token: str) -> int:
    mapping = {
        "first": 1,
        "1st": 1,
        "q1": 1,
        "second": 2,
        "2nd": 2,
        "q2": 2,
        "third": 3,
        "3rd": 3,
        "q3": 3,
        "fourth": 4,
        "4th": 4,
        "q4": 4,
    }
    return mapping[token]


def _make_date_value(
    *,
    raw_text: str,
    normalized_start: date | None,
    normalized_end: date | None,
    sort_date: date | None,
    precision: DatePrecision,
    anchor_event_id: str | None = None,
    resolution_note: str | None = None,
    is_inferred: bool = False,
) -> DateValue:
    return DateValue(
        raw_text=raw_text,
        normalized_start=normalized_start,
        normalized_end=normalized_end,
        sort_date=sort_date,
        precision=precision,
        anchor_event_id=anchor_event_id,
        resolution_note=resolution_note,
        is_inferred=is_inferred,
    )
