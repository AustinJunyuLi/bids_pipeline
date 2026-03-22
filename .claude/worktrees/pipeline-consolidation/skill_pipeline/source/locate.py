from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from skill_pipeline.pipeline_models.common import SCHEMA_VERSION
from skill_pipeline.pipeline_models.source import ChronologyCandidate, ChronologySelection


BACKGROUND_HEADING_RE = re.compile(
    r"^(?:background\s+of\s+(?:the\s+)?"
    r"(?:offer(?:\s+and\s+(?:the\s+)?)?merger|"
    r"merger(?:\s+and\s+(?:the\s+)?)?offer|"
    r"merger|offer|transaction|proposed\s+merger|"
    r"proposed\s+transaction|acquisition|tender\s+offer)"
    r"(?:\s*;\s*[^.]{1,120})?|"
    r"background\s+and\s+reasons\s+for\s+(?:the\s+)?merger)\.?\s*$",
    re.IGNORECASE,
)
STANDALONE_BACKGROUND_RE = re.compile(r"^background\.?\s*$", re.IGNORECASE)
DATE_RE = re.compile(
    r"(?i)\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\b|\b\d{4}\b"
)
PARTY_RE = re.compile(
    r"(?i)\b(?:party\s+[a-z]|\bboard\b|\bcompany\b|\bmerger\b|\boffer\b|"
    r"\bcommittee\b|\bcorp(?:oration)?\b|\binc\.?\b|llc|l\.p\.)"
)
END_HEADING_RE = re.compile(
    r"(?i)^(?:opinion\s+of|certain\s+(?:financial\s+)?projections|"
    r"reasons\s+for\s+the\s+(?:merger|offer)|recommendation\s+of|"
    r"interests\s+of|material\s+united\s+states\s+federal\s+income\s+tax|"
    r"regulatory\s+approvals|financing|the\s+(?:merger\s+agreement|offer)|"
    r"conditions\s+to)"
)
DOT_LEADER_RE = re.compile(r"\.{2,}\s*\d+\s*$")
CROSS_REFERENCE_RE = re.compile(
    r"(?i)\b(?:see|as\s+disclosed\s+under|as\s+described\s+in|incorporated\s+herein\s+by\s+reference)\b"
)
ROMAN_HEADING_PREFIX_RE = re.compile(r"^\(?[ivxlcdm]+\)?\s+", re.IGNORECASE)
HEADING_STYLE_RE = re.compile(r"^[A-Z0-9 ,.'()\-/&]+$")


@dataclass
class _ChronologyEvaluation:
    heading: str
    start_idx: int
    end_idx: int
    confidence: str
    selection_basis: str
    score: int
    is_standalone_background: bool


def locate_chronology(lines: list[str]) -> tuple[int, int, str] | None:
    selection = select_chronology(
        lines,
        document_id="document",
        accession_number=None,
        filing_type="UNKNOWN",
    )
    if selection.selected_candidate is None:
        return None
    candidate = selection.selected_candidate
    return candidate.start_line - 1, candidate.end_line - 1, candidate.heading_text


def select_chronology(
    lines: list[str],
    *,
    document_id: str,
    accession_number: str | None,
    filing_type: str,
    run_id: str = "local",
    deal_slug: str | None = None,
    markdown_lines: list[str] | None = None,
    section_headings: list[dict[str, Any]] | None = None,
) -> ChronologySelection:
    candidates = collect_chronology_candidates(
        lines,
        document_id=document_id,
        markdown_lines=markdown_lines,
        section_headings=section_headings,
    )
    if not candidates:
        return ChronologySelection(
            schema_version=SCHEMA_VERSION,
            artifact_type="chronology_selection",
            run_id=run_id,
            deal_slug=deal_slug,
            document_id=document_id,
            accession_number=accession_number,
            filing_type=filing_type,
            selected_candidate=None,
            confidence="none",
            adjudication_basis="No acceptable background-style chronology candidates were found.",
            alternative_candidates=[],
            review_required=True,
        )

    ordered = sorted(
        candidates,
        key=lambda candidate: (
            -candidate.score,
            1 if candidate.is_standalone_background else 0,
            -(candidate.end_line - candidate.start_line),
            candidate.start_line,
        ),
    )
    winner = ordered[0]
    runner_up = ordered[1] if len(ordered) > 1 else None
    confidence, confidence_factors = classify_chronology_confidence(winner, runner_up)
    basis = (
        f"Selected heading on line {winner.start_line} using normalized heading matching "
        f"and narrative scoring; considered {len(ordered)} viable background-like candidate(s)."
    )
    review_required = confidence in {"low", "none"} or confidence_factors["ambiguity_risk"] in {"medium", "high"}
    return ChronologySelection(
        schema_version=SCHEMA_VERSION,
        artifact_type="chronology_selection",
        run_id=run_id,
        deal_slug=deal_slug,
        document_id=document_id,
        accession_number=accession_number,
        filing_type=filing_type,
        selected_candidate=winner,
        confidence=confidence,
        adjudication_basis=basis,
        alternative_candidates=ordered[1:],
        review_required=review_required,
        confidence_factors=confidence_factors,
    )


def collect_chronology_candidates(
    lines: list[str],
    *,
    document_id: str,
    markdown_lines: list[str] | None = None,
    section_headings: list[dict[str, Any]] | None = None,
) -> list[ChronologyCandidate]:
    candidates = _collect_text_candidates(lines, document_id=document_id)

    for idx, line in enumerate(markdown_lines or [], start=1):
        stripped = line.strip().lstrip("#").strip()
        normalized = normalize_heading_candidate(stripped)
        if BACKGROUND_HEADING_RE.match(normalized):
            candidates.append(
                ChronologyCandidate(
                    document_id=document_id,
                    heading_text=stripped,
                    heading_normalized=normalized,
                    start_line=idx,
                    end_line=min(len(lines), idx + 50),
                    score=200,
                    source_methods=["markdown_heading"],
                    is_standalone_background=bool(STANDALONE_BACKGROUND_RE.match(normalized)),
                    diagnostics={"representation": "markdown"},
                )
            )

    for section in section_headings or []:
        title = str(section.get("title", "")).strip()
        normalized = normalize_heading_candidate(title)
        if not BACKGROUND_HEADING_RE.match(normalized):
            continue
        start_line = int(section.get("start_line", 1))
        end_line = int(section.get("end_line", start_line))
        candidates.append(
            ChronologyCandidate(
                document_id=document_id,
                heading_text=title,
                heading_normalized=normalized,
                start_line=start_line,
                end_line=end_line,
                score=250,
                source_methods=["sections_api"],
                is_standalone_background=bool(STANDALONE_BACKGROUND_RE.match(normalized)),
                diagnostics={"representation": "sections_api"},
            )
        )

    return _dedupe_candidates(candidates)


def classify_chronology_confidence(
    winner: ChronologyCandidate,
    runner_up: ChronologyCandidate | None,
) -> tuple[str, dict[str, Any]]:
    section_length = winner.end_line - winner.start_line + 1
    score_gap = winner.score - runner_up.score if runner_up is not None else winner.score
    ambiguity_risk = _ambiguity_risk(winner, runner_up, score_gap)
    coverage_assessment = _coverage_assessment(section_length, winner.score, score_gap)

    if ambiguity_risk == "high":
        confidence = "low"
    elif winner.score >= 700 and score_gap >= 100 and coverage_assessment in {"full", "adequate"}:
        confidence = "high"
    elif winner.score >= 450 and score_gap >= 80:
        confidence = "medium"
    else:
        confidence = "low"

    return confidence, {
        "section_length": section_length,
        "score_gap": score_gap,
        "ambiguity_risk": ambiguity_risk,
        "coverage_assessment": coverage_assessment,
    }




def _ambiguity_risk(
    winner: ChronologyCandidate,
    runner_up: ChronologyCandidate | None,
    score_gap: int,
) -> str:
    if runner_up is None:
        return "low"
    same_neighborhood = abs(winner.start_line - runner_up.start_line) <= 8
    if runner_up.score >= winner.score - 40 or (same_neighborhood and runner_up.score >= winner.score - 75):
        return "high"
    if runner_up.score >= winner.score - 120:
        return "medium"
    return "low"


def _coverage_assessment(section_length: int, winner_score: int, score_gap: int) -> str:
    if section_length >= 180:
        return "full"
    if section_length >= 100:
        return "adequate"
    if winner_score >= 600 and score_gap >= 150:
        return "short_but_probably_complete"
    return "short_uncertain"

def normalize_heading_candidate(line: str) -> str:
    stripped = line.strip().strip('"“”').strip()
    stripped = ROMAN_HEADING_PREFIX_RE.sub("", stripped)
    stripped = stripped.rstrip(".")
    stripped = re.sub(r"\s+", " ", stripped)
    return stripped.strip()


def normalize_heading_candidates_batch(lines: list[str]) -> list[str]:
    return [normalize_heading_candidate(line) for line in lines]


def _collect_text_candidates(lines: list[str], *, document_id: str) -> list[ChronologyCandidate]:
    candidates: list[ChronologyCandidate] = []
    normalized_headings = normalize_heading_candidates_batch(lines)
    heading_indexes: list[int] = []
    heading_forms: list[str] = []
    standalone_flags: list[bool] = []
    for idx, line in enumerate(lines):
        heading = line.strip()
        normalized_heading = normalized_headings[idx]
        if not heading:
            continue
        is_background_heading = bool(BACKGROUND_HEADING_RE.match(normalized_heading))
        is_standalone_background = bool(STANDALONE_BACKGROUND_RE.match(normalized_heading))
        if not is_background_heading and not is_standalone_background:
            continue
        if not looks_like_heading(heading):
            continue
        heading_indexes.append(idx)
        heading_forms.append(normalized_heading)
        standalone_flags.append(is_standalone_background)

    base_scores = score_heading_context_batch(
        lines,
        heading_indexes,
        normalized_headings=heading_forms,
        standalone_flags=standalone_flags,
    )
    for idx, normalized_heading, is_standalone_background, score in zip(
        heading_indexes,
        heading_forms,
        standalone_flags,
        base_scores,
        strict=True,
    ):
        if score <= 0:
            continue
        end_idx = find_section_end(lines, idx + 1)
        score += score_chronology_candidate(lines, idx, end_idx)
        candidates.append(
            ChronologyCandidate(
                document_id=document_id,
                heading_text=lines[idx].strip(),
                heading_normalized=normalized_heading,
                start_line=idx + 1,
                end_line=end_idx + 1,
                score=score,
                source_methods=["txt_heading", "txt_search"],
                is_standalone_background=is_standalone_background,
                diagnostics={
                    "line_count": end_idx - idx + 1,
                    "raw_start_idx": idx,
                    "raw_end_idx": end_idx,
                },
            )
        )
    return candidates


def score_heading_context(
    lines: list[str],
    start_idx: int,
    *,
    normalized_heading: str,
    is_standalone_background: bool,
) -> int:
    heading = lines[start_idx].strip()
    if DOT_LEADER_RE.search(heading):
        return -1

    total_lines = len(lines)
    lookahead = lines[start_idx + 1 : start_idx + 121]
    non_blank = [line.strip() for line in lookahead if line.strip()]
    min_non_blank = min(10, max(4, total_lines // 20))
    if len(non_blank) < min_non_blank:
        return -1

    date_hits = sum(1 for line in lookahead if DATE_RE.search(line))
    party_hits = sum(1 for line in lookahead if PARTY_RE.search(line))
    paragraph_breaks = sum(1 for line in lookahead if not line.strip())
    toc_like_followers = sum(
        1 for line in lookahead[:12] if DOT_LEADER_RE.search(line.strip()) or looks_like_heading(line)
    )
    section_end_idx = find_section_end(lines, start_idx + 1)
    section_length = max(0, section_end_idx - start_idx)
    min_section_length = min(60, max(6, total_lines // 15))

    if section_length < min_section_length:
        return -1
    if is_standalone_background and (date_hits < 2 or party_hits < 2):
        return -1
    if not is_standalone_background and date_hits == 0 and party_hits < 2:
        return -1
    if start_idx <= int(total_lines * 0.05) and toc_like_followers >= 4 and date_hits == 0:
        return -1

    score = min(section_length, 1600)
    score += date_hits * 40
    score += party_hits * 20
    score += paragraph_breaks * 5
    if not is_standalone_background:
        score += 100
    if start_idx <= int(total_lines * 0.10):
        score -= 150
    if CROSS_REFERENCE_RE.search(heading):
        score -= 300
    previous_line = lines[start_idx - 1] if start_idx > 0 else ""
    if CROSS_REFERENCE_RE.search(previous_line):
        score -= 250
    if normalized_heading.endswith(";"):
        score -= 200
    return score


def score_heading_context_batch(
    lines: list[str],
    start_indexes: list[int],
    *,
    normalized_headings: list[str],
    standalone_flags: list[bool],
) -> list[int]:
    return [
        score_heading_context(
            lines,
            start_idx,
            normalized_heading=normalized_heading,
            is_standalone_background=is_standalone_background,
        )
        for start_idx, normalized_heading, is_standalone_background in zip(
            start_indexes,
            normalized_headings,
            standalone_flags,
            strict=True,
        )
    ]


def find_section_end(lines: list[str], start_idx: int) -> int:
    for idx in range(start_idx + 1, len(lines)):
        candidate = lines[idx].strip()
        if not candidate:
            continue
        if END_HEADING_RE.search(candidate) and looks_like_heading(candidate):
            return idx - 1
    return len(lines) - 1


def looks_like_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    normalized = normalize_heading_candidate(stripped)
    if len(normalized) > 140 or stripped.endswith((",", ";")):
        return False
    if DATE_RE.search(normalized):
        return False
    words = normalized.split()
    if len(words) > 16:
        return False
    if HEADING_STYLE_RE.match(normalized):
        return True

    alpha_words = [re.sub(r"[^A-Za-z]+", "", word) for word in words]
    alpha_words = [word for word in alpha_words if word]
    if not alpha_words:
        return False

    title_like = 0
    for word in alpha_words:
        if word.lower() in {"of", "the", "and", "or", "for", "to"}:
            title_like += 1
        elif word[0].isupper():
            title_like += 1
    return title_like / len(alpha_words) >= 0.75


def score_chronology_candidate(lines: list[str], start_idx: int, end_idx: int) -> int:
    section = lines[start_idx : end_idx + 1]
    non_blank = [line.strip() for line in section if line.strip()]
    date_hits = sum(1 for line in non_blank if DATE_RE.search(line))
    paragraph_breaks = sum(1 for line in section if not line.strip())
    return len(non_blank) + date_hits * 15 + paragraph_breaks * 5


def _dedupe_candidates(candidates: list[ChronologyCandidate]) -> list[ChronologyCandidate]:
    deduped: list[ChronologyCandidate] = []
    for candidate in candidates:
        merged = False
        for index, existing in enumerate(deduped):
            same_heading = candidate.heading_normalized == existing.heading_normalized
            same_section = candidate.end_line == existing.end_line and abs(
                candidate.start_line - existing.start_line
            ) <= 3
            if not (same_heading and same_section):
                continue

            merged_methods = sorted(set(existing.source_methods + candidate.source_methods))
            winner = candidate if candidate.score > existing.score else existing
            deduped[index] = winner.model_copy(
                update={
                    "start_line": min(existing.start_line, candidate.start_line),
                    "source_methods": merged_methods,
                    "diagnostics": {
                        **existing.diagnostics,
                        **candidate.diagnostics,
                        "merged_duplicate_heading": True,
                    },
                }
            )
            merged = True
            break

        if not merged:
            deduped.append(candidate)
    return deduped
