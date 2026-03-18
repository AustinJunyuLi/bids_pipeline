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
QUOTE_CHARS = frozenset({"'", '"'})


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


def simplify_for_matching_with_map(text: str, index_map: list[int]) -> tuple[str, list[int]]:
    chars: list[str] = []
    simplified_map: list[int] = []

    for index, char in enumerate(text):
        if char in QUOTE_CHARS:
            continue
        chars.append(char)
        simplified_map.append(index_map[index])

    return "".join(chars), simplified_map


def strip_parenthetical_text_with_map(text: str, index_map: list[int]) -> tuple[str, list[int]]:
    chars: list[str] = []
    stripped_map: list[int] = []
    depth = 0

    for index, char in enumerate(text):
        if char == "(":
            depth += 1
            continue
        if char == ")" and depth:
            depth -= 1
            continue
        if depth:
            continue
        chars.append(char)
        stripped_map.append(index_map[index])

    return "".join(chars), stripped_map


def compact_alnum_with_map(text: str, index_map: list[int]) -> tuple[str, list[int]]:
    chars: list[str] = []
    compact_map: list[int] = []

    for index, char in enumerate(text):
        if not char.isalnum():
            continue
        chars.append(char)
        compact_map.append(index_map[index])

    return "".join(chars), compact_map


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

        simplified_segment, simplified_map = simplify_for_matching_with_map(normalized_segment, index_map)
        simplified_anchor, _anchor_map = simplify_for_matching_with_map(
            normalized_anchor,
            list(range(len(normalized_anchor))),
        )
        if simplified_anchor:
            simplified_start = simplified_segment.find(simplified_anchor)
            if simplified_start != -1:
                simplified_end = simplified_start + len(simplified_anchor) - 1
                original_start = simplified_map[simplified_start]
                original_end = simplified_map[simplified_end] + 1
                return QuoteMatchType.FUZZY, original_start, original_end

        parenthetical_segment, parenthetical_map = strip_parenthetical_text_with_map(
            normalized_segment,
            index_map,
        )
        parenthetical_anchor, _anchor_map = strip_parenthetical_text_with_map(
            normalized_anchor,
            list(range(len(normalized_anchor))),
        )
        if parenthetical_anchor:
            parenthetical_start = parenthetical_segment.find(parenthetical_anchor)
            if parenthetical_start != -1:
                parenthetical_end = parenthetical_start + len(parenthetical_anchor) - 1
                original_start = parenthetical_map[parenthetical_start]
                original_end = parenthetical_map[parenthetical_end] + 1
                return QuoteMatchType.FUZZY, original_start, original_end

        compact_segment, compact_map = compact_alnum_with_map(parenthetical_segment, parenthetical_map)
        compact_anchor, _anchor_map = compact_alnum_with_map(
            parenthetical_anchor,
            list(range(len(parenthetical_anchor))),
        )
        if compact_anchor:
            compact_start = compact_segment.find(compact_anchor)
            if compact_start != -1:
                compact_end = compact_start + len(compact_anchor) - 1
                original_start = compact_map[compact_start]
                original_end = compact_map[compact_end] + 1
                return QuoteMatchType.FUZZY, original_start, original_end

    return QuoteMatchType.UNRESOLVED, None, None
