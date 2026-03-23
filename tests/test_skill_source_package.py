from __future__ import annotations

import importlib

import pytest

import skill_pipeline.source as source_module


def test_source_package_has_no_public_package_level_exports() -> None:
    assert source_module.__all__ == []


@pytest.mark.parametrize(
    "module_name",
    [
        "skill_pipeline.source.fetch",
        "skill_pipeline.source.discovery",
        "skill_pipeline.source.ranking",
        "skill_pipeline.source.supplementary",
    ],
)
def test_legacy_source_modules_are_removed(module_name: str) -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)


@pytest.mark.parametrize(
    "attribute_name",
    [
        "build_chronology_blocks",
        "canonical_form_name",
        "collect_chronology_candidates",
        "extract_accession_from_url",
        "extract_cik_from_url",
        "locate_chronology",
        "parse_filing_date",
        "rank_filing_candidates",
        "search_terms_for_form",
        "select_chronology",
        "_atomic_write_json",
        "_atomic_write_text",
        "_canonical_form_name",
        "_search_terms_for_form",
        "atomic_write_json",
        "atomic_write_text",
        "fetch_filing_contents",
        "freeze_filing",
        "load_filing_overrides",
        "search_candidates_with_fallback",
    ],
)
def test_legacy_source_package_exports_are_removed(attribute_name: str) -> None:
    assert not hasattr(source_module, attribute_name)
