from __future__ import annotations

from pipeline.models.common import QuoteMatchType


TRANSLATIONS = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
    "\u00a0": " ",
    "\x91": "'",
    "\x92": "'",
    "\x93": '"',
    "\x94": '"',
    "\x96": "-",
    "\x97": "-",
}


def normalize_for_matching(text: str) -> str:
    normalized, _index_map = normalize_for_matching_with_map(text)
    return normalized


def normalize_for_matching_batch(texts: list[str]) -> list[str]:
    return [normalize_for_matching(text) for text in texts]


def normalize_for_matching_with_map(text: str) -> tuple[str, list[int]]:
    chars: list[str] = []
    index_map: list[int] = []
    previous_space = False

    for index, char in enumerate(text):
        replacement = TRANSLATIONS.get(char, char)
        for normalized_char in replacement.lower():
            if normalized_char.isspace():
                if previous_space:
                    continue
                chars.append(" ")
                index_map.append(index)
                previous_space = True
                continue

            chars.append(normalized_char)
            index_map.append(index)
            previous_space = False

    while chars and chars[0] == " ":
        chars.pop(0)
        index_map.pop(0)
    while chars and chars[-1] == " ":
        chars.pop()
        index_map.pop()

    return "".join(chars), index_map


def reconstruct_quote_text(lines: list[str]) -> str:
    return " ".join(line.strip() for line in lines if line.strip())


def find_anchor_in_segment(
    raw_segment: str,
    anchor_text: str,
) -> tuple[QuoteMatchType, int | None, int | None]:
    exact_start = raw_segment.find(anchor_text)
    if exact_start != -1:
        return QuoteMatchType.EXACT, exact_start, exact_start + len(anchor_text)

    normalized_segment, index_map = normalize_for_matching_with_map(raw_segment)
    normalized_anchor = normalize_for_matching(anchor_text)
    if normalized_anchor:
        normalized_start = normalized_segment.find(normalized_anchor)
        if normalized_start != -1:
            normalized_end = normalized_start + len(normalized_anchor) - 1
            original_start = index_map[normalized_start]
            original_end = index_map[normalized_end] + 1
            return QuoteMatchType.NORMALIZED, original_start, original_end

    return QuoteMatchType.UNRESOLVED, None, None
