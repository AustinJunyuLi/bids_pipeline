from __future__ import annotations

from datetime import date
import json
from hashlib import sha256
from pathlib import Path

import pytest

from skill_pipeline.pipeline_models.source import FilingCandidate
from skill_pipeline.pipeline_models.source import SeedDeal
from skill_pipeline.raw import fetch as raw_fetch
from skill_pipeline.raw import stage
from skill_pipeline.raw.discover import build_raw_discovery_manifest


def _seed(*, primary_url: str | None) -> SeedDeal:
    return SeedDeal(
        run_id="run-1",
        pipeline_version="test",
        deal_slug="imprivata",
        target_name="IMPRIVATA INC",
        acquirer_seed="THOMA BRAVO LLC",
        date_announced_seed=date(2016, 7, 13),
        primary_url_seed=primary_url,
        is_reference=False,
    )


def test_set_identity_requires_configured_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(stage, "set_identity", lambda value: None)
    monkeypatch.delenv("PIPELINE_SEC_IDENTITY", raising=False)
    monkeypatch.delenv("SEC_IDENTITY", raising=False)
    monkeypatch.delenv("EDGAR_IDENTITY", raising=False)

    with pytest.raises(ValueError, match="EDGAR_IDENTITY"):
        stage._set_identity()


def test_set_identity_uses_explicit_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str | None] = {"value": None}
    monkeypatch.setattr(stage, "set_identity", lambda value: captured.__setitem__("value", value))

    stage._set_identity("Austin Li junyu.li.24@ucl.ac.uk")

    assert captured["value"] == "Austin Li junyu.li.24@ucl.ac.uk"


def test_build_raw_discovery_manifest_uses_only_seed_url() -> None:
    manifest = build_raw_discovery_manifest(
        _seed(
            primary_url=(
                "https://www.sec.gov/Archives/edgar/data/1328015/"
                "0001193125-16-677939-index.htm"
            )
        ),
        run_id="run-1",
        cik="1328015",
    )

    assert manifest.fetch_scope == "seed_only"
    assert len(manifest.primary_candidates) == 1
    assert manifest.supplementary_candidates == []
    candidate = manifest.primary_candidates[0]
    assert candidate.accession_number == "0001193125-16-677939"
    assert candidate.document_id == "0001193125-16-677939"
    assert candidate.sec_url == (
        "https://www.sec.gov/Archives/edgar/data/1328015/"
        "0001193125-16-677939-index.htm"
    )
    assert candidate.source_origin == "seed_accession"


def test_build_raw_discovery_manifest_rejects_nonstandard_seed_url() -> None:
    with pytest.raises(ValueError, match="standard SEC Archives filing URL"):
        build_raw_discovery_manifest(
            _seed(primary_url="https://example.com/not-a-sec-filing"),
            run_id="run-1",
            cik=None,
        )


def test_build_raw_discovery_manifest_rejects_ambiguous_seed_url() -> None:
    with pytest.raises(ValueError, match="ambiguous accession"):
        build_raw_discovery_manifest(
            _seed(
                primary_url=(
                    "https://www.sec.gov/Archives/edgar/data/1328015/"
                    "0001193125-16-677939-and-0001193125-16-662313-index.htm"
                )
            ),
            run_id="run-1",
            cik="1328015",
        )


def test_fetch_raw_deal_freezes_only_the_seed_candidate(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    result = stage.fetch_raw_deal(
        _seed(
            primary_url=(
                "https://www.sec.gov/Archives/edgar/data/1328015/"
                "0001193125-16-677939-index.htm"
            )
        ),
        run_id="run-1",
        raw_dir=raw_root,
        identity="Austin Li austin@example.com",
        fetch_contents_fn=lambda accession, sec_url=None: (
            "<html>doc</html>",
            "Background of the merger\nJuly 1, 2016 ...",
        ),
    )

    discovery = json.loads(
        (raw_root / "imprivata" / "discovery.json").read_text(encoding="utf-8")
    )
    registry = json.loads(
        (raw_root / "imprivata" / "document_registry.json").read_text(encoding="utf-8")
    )

    assert result["primary_candidate_count"] == 1
    assert result["frozen_count"] == 1
    assert discovery["supplementary_candidates"] == []
    assert len(registry["documents"]) == 1


def test_fetch_raw_deal_fails_when_primary_url_is_missing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="primary_url"):
        stage.fetch_raw_deal(
            _seed(primary_url=None),
            run_id="run-1",
            raw_dir=tmp_path / "raw",
            identity="Austin Li austin@example.com",
        )


def test_set_identity_prefers_pipeline_env_over_other_identity_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str | None] = {"value": None}
    monkeypatch.setattr(stage, "set_identity", lambda value: captured.__setitem__("value", value))
    monkeypatch.setenv("PIPELINE_SEC_IDENTITY", "pipe@example.com")
    monkeypatch.setenv("SEC_IDENTITY", "sec@example.com")
    monkeypatch.setenv("EDGAR_IDENTITY", "edgar@example.com")

    stage._set_identity()

    assert captured["value"] == "pipe@example.com"


def test_fetch_filing_contents_fails_when_edgar_has_no_text() -> None:
    filing = type(
        "Filing",
        (),
        {
            "html": lambda self: "<html>index</html>",
            "text": lambda self: "",
        },
    )()

    with pytest.raises(RuntimeError, match="0001193125-16-677939"):
        raw_fetch.fetch_filing_contents(
            "0001193125-16-677939",
            sec_url="https://www.sec.gov/Archives/example-index.htm",
            get_filing_fn=lambda accession: filing,
        )


def test_fetch_raw_deal_does_not_publish_updated_discovery_on_failed_rerun(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    seed = _seed(
        primary_url=(
            "https://www.sec.gov/Archives/edgar/data/1328015/"
            "0001193125-16-677939-index.htm"
        )
    )
    stage.fetch_raw_deal(
        seed,
        run_id="run-1",
        raw_dir=raw_root,
        identity="Austin Li austin@example.com",
        fetch_contents_fn=lambda accession, sec_url=None: (
            "<html>doc</html>",
            "Background of the merger\nJuly 1, 2016 ...",
        ),
    )
    original_discovery = json.loads(
        (raw_root / "imprivata" / "discovery.json").read_text(encoding="utf-8")
    )

    with pytest.raises(FileExistsError, match="Immutable raw file"):
        stage.fetch_raw_deal(
            seed,
            run_id="run-2",
            raw_dir=raw_root,
            identity="Austin Li austin@example.com",
            fetch_contents_fn=lambda accession, sec_url=None: (
                "<html>doc</html>",
                "Different immutable filing text",
            ),
        )

    rerun_discovery = json.loads(
        (raw_root / "imprivata" / "discovery.json").read_text(encoding="utf-8")
    )
    assert rerun_discovery == original_discovery


def test_freeze_raw_filing_metadata_matches_written_bytes(tmp_path: Path) -> None:
    candidate = FilingCandidate(
        document_id="0001193125-16-677939",
        accession_number="0001193125-16-677939",
        filing_type="DEFM14A",
        sec_url="https://www.sec.gov/Archives/example-index.htm",
        source_origin="seed_accession",
    )

    document = raw_fetch.freeze_raw_filing(
        candidate,
        deal_slug="imprivata",
        raw_dir=tmp_path / "raw",
        html_text="<html>doc</html>\n",
        txt_text="Background of the merger\nJuly 1, 2016 ...\n",
    )

    txt_path = tmp_path / document.txt_path
    written_bytes = txt_path.read_bytes()

    assert document.byte_count_txt == len(written_bytes)
    assert document.sha256_txt == sha256(written_bytes).hexdigest()


def test_freeze_raw_filing_metadata_matches_existing_crlf_bytes_on_rerun(tmp_path: Path) -> None:
    candidate = FilingCandidate(
        document_id="0001193125-16-677939",
        accession_number="0001193125-16-677939",
        filing_type="DEFM14A",
        sec_url="https://www.sec.gov/Archives/example-index.htm",
        source_origin="seed_accession",
    )
    txt_path = tmp_path / "raw" / "imprivata" / "filings" / "0001193125-16-677939.txt"
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    existing_bytes = b"Background of the merger\r\nJuly 1, 2016 ...\r\n"
    txt_path.write_bytes(existing_bytes)

    document = raw_fetch.freeze_raw_filing(
        candidate,
        deal_slug="imprivata",
        raw_dir=tmp_path / "raw",
        html_text=None,
        txt_text="Background of the merger\nJuly 1, 2016 ...\n",
    )

    assert document.byte_count_txt == len(existing_bytes)
    assert document.sha256_txt == sha256(existing_bytes).hexdigest()
