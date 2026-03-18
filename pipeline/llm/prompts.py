from __future__ import annotations

import json
import re
from functools import lru_cache
from hashlib import sha256
from typing import Any

from pydantic import BaseModel

from pipeline.config import PROJECT_ROOT
from pipeline.llm.json_utils import schema_outline
from pipeline.models.source import ChronologyBlock, EvidenceItem


PROMPT_SPEC_PATH = PROJECT_ROOT / "docs" / "plans" / "2026-03-16-prompt-engineering-spec.md"


@lru_cache(maxsize=1)
def _prompt_spec_text() -> str:
    return PROMPT_SPEC_PATH.read_text(encoding="utf-8")


def _extract_fenced_block(heading: str) -> str:
    pattern = rf"## {re.escape(heading)}\n\n```(?:\w+)?\n(.*?)\n```"
    match = re.search(pattern, _prompt_spec_text(), re.DOTALL)
    if match is None:
        raise ValueError(f"Heading {heading!r} not found in prompt specification.")
    return match.group(1).strip()


def _serialize_for_prompt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, BaseModel):
        return json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True)
    if isinstance(value, list):
        normalized = [
            item.model_dump(mode="json") if isinstance(item, BaseModel) else item
            for item in value
        ]
        return json.dumps(normalized, indent=2, sort_keys=True, default=str)
    return str(value)


def _format_context_value(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class PromptPack:
    ACTOR_SYSTEM_PROMPT = _extract_fenced_block("Actor Extraction System Prompt")
    EVENT_SYSTEM_PROMPT = _extract_fenced_block("Event Extraction System Prompt")
    RECOVERY_SYSTEM_PROMPT = _extract_fenced_block("Targeted Recovery Audit System Prompt")
    REPAIR_SYSTEM_PROMPT = _extract_fenced_block("JSON Repair System Prompt")

    @staticmethod
    def render_blocks(blocks: list[ChronologyBlock]) -> str:
        rendered_blocks = []
        for block in blocks:
            text = (block.clean_text or block.raw_text).strip().replace("\n", " ")
            rendered_blocks.append(
                f"{block.block_id} [L{block.start_line}-L{block.end_line}]: {text}"
            )
        return "\n".join(rendered_blocks)

    @staticmethod
    def render_evidence_items(evidence_items: list[EvidenceItem]) -> str:
        rendered_items = []
        for item in evidence_items:
            text = item.raw_text.strip().replace("\n", " ")
            rendered_items.append(
                f"{item.evidence_id} ({item.evidence_type.value}) [{item.document_id}:L{item.start_line}-L{item.end_line}]: {text}"
            )
        return "\n".join(rendered_items)

    @staticmethod
    def _render_evidence_section(evidence_items: list[EvidenceItem] | None) -> str:
        if not evidence_items:
            return ""
        return (
            "\n\n<cross_filing_evidence>\n"
            "Use evidence_id values from this appendix when a supporting fact comes from a non-chronology source.\n"
            f"{PromptPack.render_evidence_items(evidence_items)}\n"
            "</cross_filing_evidence>"
        )

    @staticmethod
    def render_actor_user_message(
        deal_context: dict[str, Any],
        blocks: list[ChronologyBlock],
        evidence_items: list[EvidenceItem] | None = None,
    ) -> str:
        return (
            "<deal_context>\n"
            f"deal_slug: {_format_context_value(deal_context.get('deal_slug'))}\n"
            f"target_name: {_format_context_value(deal_context.get('target_name'))}\n"
            f"seed_acquirer: {_format_context_value(deal_context.get('acquirer_seed'))}\n"
            "seed_announced_date: "
            f"{_format_context_value(deal_context.get('date_announced_seed'))}\n"
            "source_accession_number: "
            f"{_format_context_value(deal_context.get('accession_number'))}\n"
            f"source_form_type: {_format_context_value(deal_context.get('filing_type'))}\n"
            "</deal_context>\n\n"
            "<schema_notes>\n"
            "- first_mention_span will be resolved later from your evidence_refs\n"
            "- use block_id for chronology evidence and evidence_id for appendix evidence\n"
            "- return only the schema fields\n"
            "</schema_notes>\n\n"
            "<chronology_blocks>\n"
            f"{PromptPack.render_blocks(blocks)}\n"
            "</chronology_blocks>"
            f"{PromptPack._render_evidence_section(evidence_items)}"
        )

    @staticmethod
    def render_event_user_message(
        deal_context: dict[str, Any],
        actor_roster: list[BaseModel] | list[dict[str, Any]],
        blocks: list[ChronologyBlock],
        *,
        chunk_mode: str,
        chunk_id: str,
        prior_round_context: list[str] | str | None = None,
        evidence_items: list[EvidenceItem] | None = None,
    ) -> str:
        if isinstance(prior_round_context, list):
            prior_round_text = "\n".join(prior_round_context)
        else:
            prior_round_text = _serialize_for_prompt(prior_round_context)
        return (
            "<deal_context>\n"
            f"deal_slug: {_format_context_value(deal_context.get('deal_slug'))}\n"
            f"target_name: {_format_context_value(deal_context.get('target_name'))}\n"
            "source_accession_number: "
            f"{_format_context_value(deal_context.get('accession_number'))}\n"
            f"source_form_type: {_format_context_value(deal_context.get('filing_type'))}\n"
            f"chunk_mode: {chunk_mode}\n"
            f"chunk_id: {chunk_id}\n"
            "</deal_context>\n\n"
            "<actor_roster>\n"
            f"{_serialize_for_prompt(actor_roster)}\n"
            "</actor_roster>\n\n"
            "<prior_round_context>\n"
            f"{prior_round_text}\n"
            "</prior_round_context>\n\n"
            "<chronology_blocks>\n"
            f"{PromptPack.render_blocks(blocks)}\n"
            "</chronology_blocks>"
            f"{PromptPack._render_evidence_section(evidence_items)}"
        )

    @staticmethod
    def render_recovery_user_message(
        blocks: list[ChronologyBlock],
        extracted_events_summary: Any,
        evidence_items: list[EvidenceItem] | None = None,
    ) -> str:
        return (
            "<extracted_events_summary>\n"
            f"{_serialize_for_prompt(extracted_events_summary)}\n"
            "</extracted_events_summary>\n\n"
            "<chronology_blocks>\n"
            f"{PromptPack.render_blocks(blocks)}\n"
            "</chronology_blocks>"
            f"{PromptPack._render_evidence_section(evidence_items)}"
        )

    @staticmethod
    def render_structured_system_prompt(
        system_prompt: str,
        output_schema: type[BaseModel],
    ) -> str:
        return (
            f"{system_prompt}\n\n"
            "<json_output_contract>\n"
            "Return exactly one JSON object that matches the schema outline below.\n"
            "Do not wrap the JSON in markdown fences.\n"
            "Do not add prose before or after the JSON.\n"
            "If a fact is not supported by the provided filing text or evidence appendix, omit it rather than guessing.\n"
            "Use null only where the schema allows it.\n"
            "Schema outline:\n"
            f"{schema_outline(output_schema)}\n"
            "</json_output_contract>"
        )

    @staticmethod
    def render_repair_user_message(
        *,
        original_text: str,
        extracted_json: str,
        validation_errors: list[str],
    ) -> str:
        return (
            "<original_response>\n"
            f"{original_text}\n"
            "</original_response>\n\n"
            "<extracted_json_candidate>\n"
            f"{extracted_json}\n"
            "</extracted_json_candidate>\n\n"
            "<validation_errors>\n"
            f"{_serialize_for_prompt(validation_errors)}\n"
            "</validation_errors>\n\n"
            "Return corrected JSON only."
        )

    @staticmethod
    def prompt_version(prompt_text: str) -> str:
        return sha256(prompt_text.encode("utf-8")).hexdigest()
