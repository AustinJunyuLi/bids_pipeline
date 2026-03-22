from __future__ import annotations

import re
from dataclasses import dataclass

from skill_pipeline.pipeline_models.source import EvidenceItem, EvidenceType
from skill_pipeline.source.locate import looks_like_heading


DATE_FRAGMENT_RE = re.compile(
    r"(?i)\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"(?:\s+\d{1,2},\s+\d{4}|\s+\d{4})?\b|\bq[1-4]\s+\d{4}\b|\b(?:early|mid|late)[-\s]+"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4}\b"
)
MONEY_RE = re.compile(
    r"(?i)\$\s?\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:to|-|–)\s*\$?\d+(?:,\d{3})*(?:\.\d+)?)?"
    r"(?:\s+per\s+share)?|\b\d+(?:\.\d+)?\s*(?:million|billion)\b"
)
ACTION_TERMS = {
    "met",
    "meeting",
    "contacted",
    "called",
    "submitted",
    "received",
    "proposed",
    "proposal",
    "offer",
    "offered",
    "signed",
    "executed",
    "entered into",
    "engaged",
    "retained",
    "authorized",
    "withdrew",
    "declined",
    "announced",
    "requested",
    "sent",
    "delivered",
    "discussed",
}
ACTOR_TERMS = {
    "advisor",
    "advisors",
    "law firm",
    "counsel",
    "investment bank",
    "financial advisor",
    "legal advisor",
    "special committee",
    "transaction committee",
    "shareholder",
    "stockholder",
    "activist",
    "consortium",
    "party ",
    "bidder ",
    "parent",
}
PROCESS_TERMS = {
    "confidentiality agreement",
    "standstill",
    "due diligence",
    "management presentation",
    "strategic alternatives",
    "process letter",
    "draft merger agreement",
    "marked-up",
    "markup of the agreement",
    "go-shop",
    "non-disclosure",
    "confidentiality and standstill",
    "bid deadline",
    "final bid",
    "instruction letter",
    "written instruction",
    "best and final",
    "exclusivity",
    "topping bid",
    "superior proposal",
}
HIGH_VALUE_PROCESS_TERMS = {
    "confidentiality agreement",
    "standstill",
    "due diligence",
    "process letter",
    "draft merger agreement",
    "go-shop",
}
OUTCOME_TERMS = {
    "closing",
    "effective time",
    "executed",
    "merger agreement",
    "lawsuit",
    "litigation",
    "stockholder approval",
    "shareholder approval",
    "vote",
    "termination fee",
    "terminated",
}
PRESS_RELEASE_TERMS = {"press release", "announced"}
ACTIVIST_TERMS = {"activist", "shareholder", "stockholder", "jana", "gamco", "gabelli"}


@dataclass(slots=True)
class Paragraph:
    start_line: int
    end_line: int
    text: str


def iter_paragraphs(lines: list[str]) -> list[Paragraph]:
    paragraphs: list[Paragraph] = []
    buffer: list[str] = []
    start_line: int | None = None

    def flush(end_line: int) -> None:
        nonlocal buffer, start_line
        if not buffer or start_line is None:
            buffer = []
            start_line = None
            return
        paragraphs.append(
            Paragraph(
                start_line=start_line,
                end_line=end_line,
                text="\n".join(buffer),
            )
        )
        buffer = []
        start_line = None

    for idx, line in enumerate(lines, start=1):
        if not line.strip():
            flush(idx - 1)
            continue
        if start_line is None:
            start_line = idx
        buffer.append(line)
    flush(len(lines))
    return paragraphs


def scan_document_evidence(
    lines: list[str],
    *,
    document_id: str,
    filing_type: str,
    accession_number: str | None = None,
) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    seen: set[tuple[str, int, int, str]] = set()
    ordinal = 1

    for paragraph in iter_paragraphs(lines):
        raw_text = paragraph.text.strip()
        if not raw_text:
            continue
        if looks_like_heading(raw_text) and len(raw_text.split()) <= 18:
            continue

        lowered = _normalize(raw_text)
        matches = _classify_paragraph(raw_text, lowered)
        for evidence_type, matched_terms in matches:
            key = (evidence_type.value, paragraph.start_line, paragraph.end_line, lowered)
            if key in seen:
                continue
            seen.add(key)
            evidence.append(
                EvidenceItem(
                    evidence_id=(
                        f"{accession_number}:E{ordinal:04d}"
                        if accession_number
                        else f"{document_id}:E{ordinal:04d}"
                    ),
                    document_id=document_id,
                    accession_number=accession_number,
                    filing_type=filing_type,
                    start_line=paragraph.start_line,
                    end_line=paragraph.end_line,
                    raw_text=raw_text,
                    evidence_type=evidence_type,
                    confidence=_score_confidence(evidence_type, matched_terms, raw_text),
                    matched_terms=matched_terms,
                    date_text=_first_match(DATE_FRAGMENT_RE, raw_text),
                    actor_hint=_extract_actor_hint(raw_text),
                    value_hint=_first_match(MONEY_RE, raw_text),
                    note=_build_note(evidence_type, matched_terms),
                )
            )
            ordinal += 1

    return evidence


def group_evidence_by_type(items: list[EvidenceItem]) -> dict[EvidenceType, list[EvidenceItem]]:
    grouped: dict[EvidenceType, list[EvidenceItem]] = {evidence_type: [] for evidence_type in EvidenceType}
    for item in items:
        grouped.setdefault(item.evidence_type, []).append(item)
    return grouped


def _classify_paragraph(raw_text: str, lowered: str) -> list[tuple[EvidenceType, list[str]]]:
    matches: list[tuple[EvidenceType, list[str]]] = []

    dated_terms = [term for term in ACTION_TERMS if term in lowered]
    if DATE_FRAGMENT_RE.search(raw_text) and dated_terms:
        matches.append((EvidenceType.DATED_ACTION, sorted(dated_terms)))

    money_terms = MONEY_RE.findall(raw_text)
    if money_terms:
        normalized_terms = sorted({term.strip() for term in money_terms})
        matches.append((EvidenceType.FINANCIAL_TERM, normalized_terms))

    actor_terms = [term for term in ACTOR_TERMS if term in lowered]
    if actor_terms or _extract_actor_hint(raw_text):
        matches.append((EvidenceType.ACTOR_IDENTIFICATION, sorted(set(actor_terms))))

    process_terms = [term for term in PROCESS_TERMS if term in lowered]
    if process_terms:
        matches.append((EvidenceType.PROCESS_SIGNAL, sorted(set(process_terms))))

    outcome_terms = [term for term in OUTCOME_TERMS if term in lowered]
    if outcome_terms:
        matches.append((EvidenceType.OUTCOME_FACT, sorted(set(outcome_terms))))

    return matches


def _score_confidence(
    evidence_type: EvidenceType,
    matched_terms: list[str],
    raw_text: str,
) -> str:
    score = len(matched_terms)
    if evidence_type == EvidenceType.DATED_ACTION and DATE_FRAGMENT_RE.search(raw_text):
        score += 2
    if evidence_type == EvidenceType.FINANCIAL_TERM and "per share" in raw_text.lower():
        score += 2
    if evidence_type == EvidenceType.PROCESS_SIGNAL and any(
        term in HIGH_VALUE_PROCESS_TERMS for term in matched_terms
    ):
        score += 2
    if evidence_type == EvidenceType.OUTCOME_FACT and any(term in raw_text.lower() for term in {"closing", "executed", "termination fee"}):
        score += 2
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _first_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(0) if match else None


def _extract_actor_hint(text: str) -> str | None:
    patterns = [
        re.compile(r"\b(?:Party|Bidder)\s+[A-Z]\b"),
        re.compile(r"\b(?:Board|Special Committee|Transaction Committee)\b"),
        re.compile(r"\b[A-Z][A-Za-z&'.,-]+\s+(?:Partners|Sachs|Lynch|Morgan|Cooley|Gabelli|JANA|GAMCO|BMO)\b"),
    ]
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def _build_note(evidence_type: EvidenceType, matched_terms: list[str]) -> str | None:
    if not matched_terms:
        return None
    label = evidence_type.value.replace("_", " ")
    return f"detected {label}: {', '.join(matched_terms[:5])}"
