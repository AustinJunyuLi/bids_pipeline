"""Prompt composition regression tests for the live observations-v2 contract."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from skill_pipeline.pipeline_models.prompt import PromptChunkWindow
from skill_pipeline.pipeline_models.source import (
    ChronologyBlock,
    EvidenceItem,
    EvidenceType,
)
from skill_pipeline.prompts.checklist import build_evidence_checklist
from skill_pipeline.prompts.chunks import (
    build_chunk_windows,
    estimate_block_tokens,
)
from skill_pipeline.prompts.render import render_observation_v2_packet


def _make_block(
    block_id: str,
    ordinal: int,
    clean_text: str,
    *,
    is_heading: bool = False,
) -> ChronologyBlock:
    return ChronologyBlock(
        block_id=block_id,
        document_id="doc-test",
        ordinal=ordinal,
        start_line=ordinal * 10,
        end_line=ordinal * 10 + 5,
        raw_text=clean_text,
        clean_text=clean_text,
        is_heading=is_heading,
        date_mentions=[],
        entity_mentions=[],
        evidence_density=0,
        temporal_phase="other",
    )


def _make_evidence(
    evidence_id: str,
    evidence_type: EvidenceType,
    raw_text: str,
    *,
    start_line: int = 1,
    end_line: int = 2,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        document_id="doc-test",
        accession_number="0001193125-16-000001",
        filing_type="SC 14D9",
        start_line=start_line,
        end_line=end_line,
        raw_text=raw_text,
        evidence_type=evidence_type,
        confidence="high",
    )


class TestEstimateBlockTokens:
    def test_short_block(self):
        block = _make_block("B001", 0, "Hello world")
        tokens = estimate_block_tokens(block)
        assert tokens == math.ceil(2 * 1.35)

    def test_empty_clean_text(self):
        block = _make_block("B001", 0, "")
        assert estimate_block_tokens(block) == 0

    def test_deterministic(self):
        block = _make_block("B001", 0, "one two three four five")
        t1 = estimate_block_tokens(block)
        t2 = estimate_block_tokens(block)
        assert t1 == t2


class TestBuildChunkWindows:
    def test_single_pass_when_under_budget(self):
        blocks = [_make_block(f"B{i:03d}", i, "word " * 10) for i in range(3)]
        windows = build_chunk_windows(blocks, chunk_budget=99999)
        assert len(windows) == 1
        window = windows[0]
        assert window.chunk_count == 1
        assert window.target_block_ids == ["B000", "B001", "B002"]
        assert window.overlap_block_ids == []

    def test_chunked_windows_have_overlap(self):
        blocks = [_make_block(f"B{i:03d}", i, "word " * 10) for i in range(6)]
        windows = build_chunk_windows(blocks, chunk_budget=30)
        assert len(windows) > 1
        for window in windows:
            assert window.chunk_count == len(windows)
        for window in windows[1:]:
            assert window.overlap_block_ids, f"window {window.window_id} has no overlap"

    def test_overlap_exactly_2_blocks(self):
        blocks = [_make_block(f"B{i:03d}", i, "word " * 10) for i in range(10)]
        windows = build_chunk_windows(blocks, chunk_budget=30, overlap_blocks=2)
        for window in windows:
            assert len(window.overlap_block_ids) <= 4

    def test_target_block_ids_never_overlap_with_overlap_ids(self):
        blocks = [_make_block(f"B{i:03d}", i, "word " * 10) for i in range(8)]
        windows = build_chunk_windows(blocks, chunk_budget=30)
        for window in windows:
            target_set = set(window.target_block_ids)
            overlap_set = set(window.overlap_block_ids)
            assert target_set.isdisjoint(overlap_set)

    def test_all_blocks_covered_by_target_ids(self):
        blocks = [_make_block(f"B{i:03d}", i, "word " * 10) for i in range(8)]
        windows = build_chunk_windows(blocks, chunk_budget=30)
        all_target = []
        for window in windows:
            all_target.extend(window.target_block_ids)
        assert all_target == [f"B{i:03d}" for i in range(8)]

    def test_empty_blocks_raises(self):
        with pytest.raises(ValueError, match="blocks must not be empty"):
            build_chunk_windows([], chunk_budget=100)

    def test_zero_budget_raises(self):
        blocks = [_make_block("B000", 0, "word")]
        with pytest.raises(ValueError, match="chunk_budget must be positive"):
            build_chunk_windows(blocks, chunk_budget=0)

    def test_single_block_always_single_pass(self):
        block = _make_block("B000", 0, "word " * 5000)
        windows = build_chunk_windows([block], chunk_budget=10)
        assert len(windows) == 1
        assert windows[0].target_block_ids == ["B000"]

    def test_window_ids_are_sequential(self):
        blocks = [_make_block(f"B{i:03d}", i, "word " * 10) for i in range(6)]
        windows = build_chunk_windows(blocks, chunk_budget=30)
        for i, window in enumerate(windows):
            assert window.window_id == f"w{i}"
            assert window.chunk_index == i

    def test_single_pass_override_returns_one_window(self):
        blocks = [_make_block(f"B{i:03d}", i, "word " * 200) for i in range(12)]
        windows = build_chunk_windows(blocks, chunk_budget=30, single_pass=True)
        assert len(windows) == 1
        assert windows[0].chunk_count == 1
        assert windows[0].target_block_ids == [f"B{i:03d}" for i in range(12)]
        assert windows[0].overlap_block_ids == []


class TestDealComplexity:
    def test_classify_deal_complexity_simple(self):
        from skill_pipeline.complexity import classify_deal_complexity

        blocks = [_make_block(f"B{i:03d}", i, "word") for i in range(150)]
        assert classify_deal_complexity(blocks) == "simple"

    def test_classify_deal_complexity_complex(self):
        from skill_pipeline.complexity import classify_deal_complexity

        blocks = [_make_block(f"B{i:03d}", i, "word") for i in range(151)]
        assert classify_deal_complexity(blocks) == "complex"

    def test_classify_deal_complexity_one_block(self):
        from skill_pipeline.complexity import classify_deal_complexity

        assert classify_deal_complexity([_make_block("B000", 0, "word")]) == "simple"

    def test_classify_deal_complexity_custom_threshold(self):
        from skill_pipeline.complexity import classify_deal_complexity

        blocks = [_make_block(f"B{i:03d}", i, "word") for i in range(50)]
        assert classify_deal_complexity(blocks, max_blocks=30) == "complex"


class TestBuildEvidenceChecklist:
    def test_empty_items_returns_empty(self):
        assert build_evidence_checklist([]) == ""

    def test_grouped_by_evidence_type(self):
        items = [
            _make_evidence("E001", EvidenceType.DATED_ACTION, "some text"),
            _make_evidence("E002", EvidenceType.FINANCIAL_TERM, "price text"),
            _make_evidence("E003", EvidenceType.DATED_ACTION, "another action"),
        ]
        result = build_evidence_checklist(items)
        assert result.count("### Dated actions to extract") == 1
        assert result.count("### Financial terms to capture") == 1
        assert "E001" in result
        assert "E002" in result
        assert "E003" in result

    def test_bullets_include_evidence_id(self):
        items = [
            _make_evidence("E007", EvidenceType.ACTOR_IDENTIFICATION, "actor text"),
        ]
        result = build_evidence_checklist(items)
        assert "**E007**" in result

    def test_bullets_include_line_range(self):
        items = [
            _make_evidence(
                "E010",
                EvidenceType.PROCESS_SIGNAL,
                "signal",
                start_line=42,
                end_line=45,
            ),
        ]
        result = build_evidence_checklist(items)
        assert "L42-L45" in result

    def test_hint_parts_rendered(self):
        item = EvidenceItem(
            evidence_id="E020",
            document_id="doc",
            accession_number="0001193125-16-000001",
            filing_type="SC 14D9",
            start_line=1,
            end_line=2,
            raw_text="text",
            evidence_type=EvidenceType.FINANCIAL_TERM,
            confidence="high",
            date_text="March 15",
            value_hint="$42.00",
        )
        result = build_evidence_checklist([item])
        assert "date: March 15" in result
        assert "value: $42.00" in result


ASSETS_DIR = Path(__file__).resolve().parent.parent / "skill_pipeline" / "prompt_assets"


def _single_pass_window(block_ids: list[str]) -> PromptChunkWindow:
    return PromptChunkWindow(
        window_id="w0",
        chunk_index=0,
        chunk_count=1,
        target_block_ids=block_ids,
        overlap_block_ids=[],
        estimated_tokens=100,
    )


def _chunked_window(
    target_ids: list[str],
    overlap_ids: list[str],
    *,
    chunk_index: int = 0,
    chunk_count: int = 2,
) -> PromptChunkWindow:
    return PromptChunkWindow(
        window_id=f"w{chunk_index}",
        chunk_index=chunk_index,
        chunk_count=chunk_count,
        target_block_ids=target_ids,
        overlap_block_ids=overlap_ids,
        estimated_tokens=100,
    )


class TestRenderObservationV2Packet:
    def test_section_ordering(self):
        blocks = [_make_block("B000", 0, "chronology text here")]
        evidence = [_make_evidence("E001", EvidenceType.DATED_ACTION, "ev")]
        window = _single_pass_window(["B000"])

        _, _, rendered = render_observation_v2_packet(
            deal_slug="test-deal",
            target_name="TestCo",
            accession_number="0001",
            filing_type="SC 14D9",
            window=window,
            blocks=blocks,
            evidence_items=evidence,
            prefix_asset_path=ASSETS_DIR / "observations_v2_prefix.md",
            examples_asset_path=ASSETS_DIR / "observations_v2_examples.md",
            task_instructions="Extract observations now.",
        )

        chron_pos = rendered.index("<chronology_blocks>")
        task_pos = rendered.index("<task_instructions>")
        assert chron_pos < task_pos

    def test_no_overlap_in_single_pass(self):
        blocks = [_make_block("B000", 0, "text")]
        window = _single_pass_window(["B000"])
        _, _, rendered = render_observation_v2_packet(
            deal_slug="test",
            target_name="T",
            accession_number=None,
            filing_type=None,
            window=window,
            blocks=blocks,
            evidence_items=[],
            prefix_asset_path=ASSETS_DIR / "observations_v2_prefix.md",
            examples_asset_path=ASSETS_DIR / "observations_v2_examples.md",
            task_instructions="Do it.",
        )
        assert "<overlap_context>" not in rendered
        assert "<actor_roster>" not in rendered

    def test_overlap_in_chunked_packet(self):
        blocks = [
            _make_block("B000", 0, "first block"),
            _make_block("B001", 1, "second block"),
            _make_block("B002", 2, "third block"),
        ]
        window = _chunked_window(["B001"], ["B000", "B002"])
        _, _, rendered = render_observation_v2_packet(
            deal_slug="test",
            target_name="T",
            accession_number=None,
            filing_type=None,
            window=window,
            blocks=blocks,
            evidence_items=[],
            prefix_asset_path=ASSETS_DIR / "observations_v2_prefix.md",
            examples_asset_path=ASSETS_DIR / "observations_v2_examples.md",
            task_instructions="Do it.",
        )
        assert "<overlap_context>" in rendered
        assert "</overlap_context>" in rendered

    def test_evidence_checklist_in_rendered(self):
        blocks = [_make_block("B000", 0, "text")]
        evidence = [_make_evidence("E099", EvidenceType.OUTCOME_FACT, "outcome text")]
        window = _single_pass_window(["B000"])
        _, _, rendered = render_observation_v2_packet(
            deal_slug="test",
            target_name="T",
            accession_number=None,
            filing_type=None,
            window=window,
            blocks=blocks,
            evidence_items=evidence,
            prefix_asset_path=ASSETS_DIR / "observations_v2_prefix.md",
            examples_asset_path=ASSETS_DIR / "observations_v2_examples.md",
            task_instructions="Do it.",
        )
        assert "<evidence_checklist>" in rendered
        assert "E099" in rendered

    def test_unknown_block_ids_raise(self):
        blocks = [_make_block("B000", 0, "text")]
        window = _single_pass_window(["B999"])
        with pytest.raises(ValueError, match="Unknown block_ids"):
            render_observation_v2_packet(
                deal_slug="test",
                target_name="T",
                accession_number=None,
                filing_type=None,
                window=window,
                blocks=blocks,
                evidence_items=[],
                prefix_asset_path=ASSETS_DIR / "observations_v2_prefix.md",
                examples_asset_path=ASSETS_DIR / "observations_v2_examples.md",
                task_instructions="Do it.",
            )

    def test_missing_examples_asset_raises(self, tmp_path: Path):
        blocks = [_make_block("B000", 0, "text")]
        window = _single_pass_window(["B000"])
        missing_asset = tmp_path / "missing-observation-examples.md"
        with pytest.raises(FileNotFoundError, match="Missing prompt asset"):
            render_observation_v2_packet(
                deal_slug="test",
                target_name="T",
                accession_number=None,
                filing_type=None,
                window=window,
                blocks=blocks,
                evidence_items=[],
                prefix_asset_path=ASSETS_DIR / "observations_v2_prefix.md",
                examples_asset_path=missing_asset,
                task_instructions="Do it.",
            )


class TestRunComposePrompts:
    @staticmethod
    def _setup_deal(tmp_path: Path) -> None:
        seeds_csv = tmp_path / "data" / "seeds.csv"
        seeds_csv.parent.mkdir(parents=True, exist_ok=True)
        seeds_csv.write_text(
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            "test-deal,TestCo Inc,AcquireCo,2025-01-15,,false\n",
            encoding="utf-8",
        )

        source_dir = tmp_path / "data" / "deals" / "test-deal" / "source"
        source_dir.mkdir(parents=True, exist_ok=True)

        blocks_lines = []
        for i in range(5):
            block = ChronologyBlock(
                block_id=f"B{i:03d}",
                document_id="doc-1",
                ordinal=i,
                start_line=i * 10,
                end_line=i * 10 + 8,
                raw_text=f"Block {i} raw text " + "word " * 20,
                clean_text=f"Block {i} clean text " + "word " * 20,
                is_heading=(i == 0),
                date_mentions=[],
                entity_mentions=[],
                evidence_density=2,
                temporal_phase="bidding",
            )
            blocks_lines.append(block.model_dump_json())
        (source_dir / "chronology_blocks.jsonl").write_text(
            "\n".join(blocks_lines),
            encoding="utf-8",
        )

        evidence_lines = []
        for i in range(3):
            evidence = EvidenceItem(
                evidence_id=f"E{i:03d}",
                document_id="doc-1",
                accession_number="0001-test",
                filing_type="SC 14D9",
                start_line=i * 5,
                end_line=i * 5 + 3,
                raw_text=f"evidence text {i}",
                evidence_type=EvidenceType.DATED_ACTION,
                confidence="high",
                date_text=f"2025-0{i + 1}-15",
            )
            evidence_lines.append(evidence.model_dump_json())
        (source_dir / "evidence_items.jsonl").write_text(
            "\n".join(evidence_lines),
            encoding="utf-8",
        )

        (source_dir / "chronology_selection.json").write_text(
            json.dumps({
                "schema_version": "2.0.0",
                "artifact_type": "chronology_selection",
                "run_id": "test",
                "accession_number": "0001-test",
                "filing_type": "SC 14D9",
                "document_id": "doc-1",
                "confidence": "high",
                "adjudication_basis": "test",
                "review_required": False,
            }),
            encoding="utf-8",
        )

        raw_dir = tmp_path / "raw" / "test-deal"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "document_registry.json").write_text("{}", encoding="utf-8")

    @staticmethod
    def _setup_routing_deal(
        tmp_path: Path,
        *,
        block_count: int,
        words_per_block: int,
    ) -> None:
        seeds_csv = tmp_path / "data" / "seeds.csv"
        seeds_csv.parent.mkdir(parents=True, exist_ok=True)
        seeds_csv.write_text(
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            "test-deal,TestCo Inc,AcquireCo,2025-01-15,,false\n",
            encoding="utf-8",
        )

        source_dir = tmp_path / "data" / "deals" / "test-deal" / "source"
        source_dir.mkdir(parents=True, exist_ok=True)

        blocks = []
        evidence_items = []
        for i in range(block_count):
            blocks.append(
                ChronologyBlock(
                    block_id=f"B{i:03d}",
                    document_id="doc-1",
                    ordinal=i,
                    start_line=i * 10,
                    end_line=i * 10 + 8,
                    raw_text=f"Block {i} raw text " + ("word " * words_per_block),
                    clean_text=f"Block {i} clean text " + ("word " * words_per_block),
                    is_heading=(i == 0),
                    date_mentions=[],
                    entity_mentions=[],
                    evidence_density=1,
                    temporal_phase="bidding",
                )
            )
            evidence_items.append(
                EvidenceItem(
                    evidence_id=f"E{i:03d}",
                    document_id="doc-1",
                    accession_number="0001-test",
                    filing_type="SC 14D9",
                    start_line=i * 10,
                    end_line=i * 10 + 1,
                    raw_text=f"evidence text {i}",
                    evidence_type=EvidenceType.DATED_ACTION,
                    confidence="high",
                )
            )

        (source_dir / "chronology_blocks.jsonl").write_text(
            "\n".join(block.model_dump_json() for block in blocks),
            encoding="utf-8",
        )
        (source_dir / "evidence_items.jsonl").write_text(
            "\n".join(item.model_dump_json() for item in evidence_items),
            encoding="utf-8",
        )
        (source_dir / "chronology_selection.json").write_text(
            json.dumps({
                "schema_version": "2.0.0",
                "artifact_type": "chronology_selection",
                "run_id": "test",
                "accession_number": "0001-test",
                "filing_type": "SC 14D9",
                "document_id": "doc-1",
                "confidence": "high",
                "adjudication_basis": "test",
                "review_required": False,
            }),
            encoding="utf-8",
        )

        raw_dir = tmp_path / "raw" / "test-deal"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "document_registry.json").write_text("{}", encoding="utf-8")

    def test_observations_mode_writes_manifest_and_packets(self, tmp_path: Path):
        self._setup_deal(tmp_path)
        from skill_pipeline.compose_prompts import run_compose_prompts

        manifest = run_compose_prompts("test-deal", tmp_path, chunk_budget=99999)
        assert manifest.packets
        assert all(packet.packet_family == "observations_v2" for packet in manifest.packets)

        for packet in manifest.packets:
            assert Path(packet.prefix_path).exists()
            assert Path(packet.body_path).exists()
            assert Path(packet.rendered_path).exists()

        manifest_path = tmp_path / "data" / "skill" / "test-deal" / "prompt_v2" / "manifest.json"
        assert manifest_path.exists()

    def test_chronology_precedes_task_instructions(self, tmp_path: Path):
        self._setup_deal(tmp_path)
        from skill_pipeline.compose_prompts import run_compose_prompts

        manifest = run_compose_prompts("test-deal", tmp_path, chunk_budget=99999)
        rendered = Path(manifest.packets[0].rendered_path).read_text(encoding="utf-8")
        chron_pos = rendered.index("<chronology_blocks>")
        task_pos = rendered.index("<task_instructions>")
        assert chron_pos < task_pos

    def test_rendered_mentions_quote_before_extract_protocol(self, tmp_path: Path):
        self._setup_deal(tmp_path)
        from skill_pipeline.compose_prompts import run_compose_prompts

        manifest = run_compose_prompts("test-deal", tmp_path, chunk_budget=99999)
        rendered = Path(manifest.packets[0].rendered_path).read_text(encoding="utf-8")
        assert "quote-before-extract protocol" in rendered
        assert "quotes, parties, cohorts, observations, exclusions, coverage" in rendered
        assert "quote_ids" in rendered

    def test_evidence_ids_in_rendered(self, tmp_path: Path):
        self._setup_deal(tmp_path)
        from skill_pipeline.compose_prompts import run_compose_prompts

        manifest = run_compose_prompts("test-deal", tmp_path, chunk_budget=99999)
        rendered = Path(manifest.packets[0].rendered_path).read_text(encoding="utf-8")
        assert "<evidence_checklist>" in rendered
        assert "E000" in rendered

    def test_chunked_windows_produce_overlap(self, tmp_path: Path):
        self._setup_deal(tmp_path)
        from skill_pipeline.compose_prompts import run_compose_prompts

        manifest = run_compose_prompts(
            "test-deal",
            tmp_path,
            chunk_budget=10,
            routing="chunked",
        )
        assert len(manifest.packets) > 1
        assert any(
            "<overlap_context>" in Path(packet.rendered_path).read_text(encoding="utf-8")
            for packet in manifest.packets[1:]
        )

    def test_non_observation_mode_is_rejected(self, tmp_path: Path):
        self._setup_deal(tmp_path)
        from skill_pipeline.compose_prompts import run_compose_prompts

        with pytest.raises(ValueError, match="mode='observations'"):
            run_compose_prompts("test-deal", tmp_path, mode="actors")  # type: ignore[arg-type]

    def test_non_v2_contract_is_rejected(self, tmp_path: Path):
        self._setup_deal(tmp_path)
        from skill_pipeline.compose_prompts import run_compose_prompts

        with pytest.raises(ValueError, match="live v2 contract"):
            run_compose_prompts("test-deal", tmp_path, contract="v1")  # type: ignore[arg-type]

    def test_chunked_packets_filter_evidence_to_visible_blocks(self, tmp_path: Path):
        seeds_csv = tmp_path / "data" / "seeds.csv"
        seeds_csv.parent.mkdir(parents=True, exist_ok=True)
        seeds_csv.write_text(
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            "test-deal,TestCo Inc,AcquireCo,2025-01-15,,false\n",
            encoding="utf-8",
        )

        source_dir = tmp_path / "data" / "deals" / "test-deal" / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        blocks = []
        for i in range(6):
            blocks.append(
                ChronologyBlock(
                    block_id=f"B{i:03d}",
                    document_id="doc-1",
                    ordinal=i,
                    start_line=i * 10,
                    end_line=i * 10 + 8,
                    raw_text=f"Block {i} raw text " + "word " * 20,
                    clean_text=f"Block {i} clean text " + "word " * 20,
                    is_heading=(i == 0),
                    date_mentions=[],
                    entity_mentions=[],
                    evidence_density=1,
                    temporal_phase="bidding",
                )
            )
        (source_dir / "chronology_blocks.jsonl").write_text(
            "\n".join(block.model_dump_json() for block in blocks),
            encoding="utf-8",
        )

        evidence_items = []
        for i in range(6):
            evidence_items.append(
                EvidenceItem(
                    evidence_id=f"E{i:03d}",
                    document_id="doc-1",
                    accession_number="0001-test",
                    filing_type="SC 14D9",
                    start_line=i * 10,
                    end_line=i * 10 + 1,
                    raw_text=f"evidence text {i}",
                    evidence_type=EvidenceType.DATED_ACTION,
                    confidence="high",
                )
            )
        (source_dir / "evidence_items.jsonl").write_text(
            "\n".join(item.model_dump_json() for item in evidence_items),
            encoding="utf-8",
        )
        (source_dir / "chronology_selection.json").write_text(
            json.dumps({
                "schema_version": "2.0.0",
                "artifact_type": "chronology_selection",
                "run_id": "test",
                "accession_number": "0001-test",
                "filing_type": "SC 14D9",
                "document_id": "doc-1",
                "confidence": "high",
                "adjudication_basis": "test",
                "review_required": False,
            }),
            encoding="utf-8",
        )

        raw_dir = tmp_path / "raw" / "test-deal"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "document_registry.json").write_text("{}", encoding="utf-8")

        from skill_pipeline.compose_prompts import run_compose_prompts

        manifest = run_compose_prompts(
            "test-deal",
            tmp_path,
            chunk_budget=40,
            routing="chunked",
        )
        first_packet = manifest.packets[0]
        rendered = Path(first_packet.rendered_path).read_text(encoding="utf-8")

        assert first_packet.evidence_ids == ["E000", "E001", "E002"]
        assert "E000" in rendered
        assert "E001" in rendered
        assert "E002" in rendered
        assert "E003" not in rendered

    def test_duplicate_block_ids_fail_fast(self, tmp_path: Path):
        self._setup_deal(tmp_path)
        source_dir = tmp_path / "data" / "deals" / "test-deal" / "source"
        duplicate_blocks = [
            ChronologyBlock(
                block_id="B000",
                document_id="doc-1",
                ordinal=0,
                start_line=0,
                end_line=8,
                raw_text="first block",
                clean_text="first block",
                is_heading=False,
                date_mentions=[],
                entity_mentions=[],
                evidence_density=0,
                temporal_phase="bidding",
            ),
            ChronologyBlock(
                block_id="B000",
                document_id="doc-1",
                ordinal=1,
                start_line=10,
                end_line=18,
                raw_text="duplicate block",
                clean_text="duplicate block",
                is_heading=False,
                date_mentions=[],
                entity_mentions=[],
                evidence_density=0,
                temporal_phase="bidding",
            ),
        ]
        (source_dir / "chronology_blocks.jsonl").write_text(
            "\n".join(block.model_dump_json() for block in duplicate_blocks),
            encoding="utf-8",
        )

        from skill_pipeline.compose_prompts import run_compose_prompts

        with pytest.raises(ValueError, match="Duplicate block_id in chronology blocks"):
            run_compose_prompts("test-deal", tmp_path)

    def test_manifest_notes_contain_mode_and_budget(self, tmp_path: Path):
        self._setup_deal(tmp_path)
        from skill_pipeline.compose_prompts import run_compose_prompts

        manifest = run_compose_prompts("test-deal", tmp_path, chunk_budget=5000)
        notes_str = " ".join(manifest.notes)
        assert "mode=observations" in notes_str
        assert "chunk_budget=5000" in notes_str

    def test_routing_auto_simple_deal(self, tmp_path: Path):
        self._setup_routing_deal(tmp_path, block_count=50, words_per_block=120)
        from skill_pipeline.compose_prompts import run_compose_prompts

        manifest = run_compose_prompts(
            "test-deal",
            tmp_path,
            chunk_budget=6000,
            routing="auto",
        )
        assert len(manifest.packets) == 1
        assert manifest.packets[0].chunk_mode == "single_pass"
        assert "routing=auto" in manifest.notes
        assert "complexity=simple" in manifest.notes

    def test_routing_auto_complex_deal(self, tmp_path: Path):
        self._setup_routing_deal(tmp_path, block_count=200, words_per_block=40)
        from skill_pipeline.compose_prompts import run_compose_prompts

        manifest = run_compose_prompts(
            "test-deal",
            tmp_path,
            chunk_budget=6000,
            routing="auto",
        )
        assert len(manifest.packets) > 1
        assert all(packet.chunk_mode == "chunked" for packet in manifest.packets)
        assert "routing=auto" in manifest.notes
        assert "complexity=complex" in manifest.notes

    def test_routing_forced_single_pass(self, tmp_path: Path):
        self._setup_routing_deal(tmp_path, block_count=200, words_per_block=40)
        from skill_pipeline.compose_prompts import run_compose_prompts

        manifest = run_compose_prompts(
            "test-deal",
            tmp_path,
            chunk_budget=6000,
            routing="single-pass",
        )
        assert len(manifest.packets) == 1
        assert manifest.packets[0].chunk_mode == "single_pass"
        assert "routing=single-pass" in manifest.notes

    def test_routing_forced_chunked(self, tmp_path: Path):
        self._setup_routing_deal(tmp_path, block_count=10, words_per_block=20)
        from skill_pipeline.compose_prompts import run_compose_prompts

        manifest = run_compose_prompts(
            "test-deal",
            tmp_path,
            chunk_budget=40,
            routing="chunked",
        )
        assert len(manifest.packets) > 1
        assert all(packet.chunk_mode == "chunked" for packet in manifest.packets)
        assert "routing=chunked" in manifest.notes

    def test_cli_routing_flag(self):
        from skill_pipeline.cli import build_parser

        parser = build_parser()
        args = parser.parse_args([
            "compose-prompts",
            "--deal",
            "test-deal",
            "--routing",
            "single-pass",
        ])
        assert args.routing == "single-pass"

    def test_observation_examples_cover_literal_types(self):
        content = (ASSETS_DIR / "observations_v2_examples.md").read_text(encoding="utf-8")
        for obs_type in ("process", "agreement", "solicitation", "proposal", "status", "outcome"):
            assert f"`{obs_type}`" in content
