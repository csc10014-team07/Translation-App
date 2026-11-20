"""
Unit tests for the Evaluation Framework (metrics and dataset loading).
"""
from __future__ import annotations

import asyncio
import json
import unicodedata
from types import SimpleNamespace

import numpy as np
import pytest
from app.core.config import settings
from app.models.asr_adapter import ASRAdapter
from benchmarks import dataset_loader
from benchmarks.dataset_loader import (
    BUILTIN_FLORES_PAIRS,
    CONTEXT_PRESET_TARGETS,
    DEFAULT_CACHE_DIR,
    MIN_EVAL_SAMPLES,
    _parse_fleurs_tsv,
    get_asr_samples,
    get_context_dataset,
    get_fleurs_asr_dataset,
    get_flores_dataset,
    get_flores_samples,
    get_tts_samples,
    load_context_dataset,
)
from benchmarks.metrics import (
    calculate_cer,
    calculate_corpus_bleu,
    calculate_sentence_bleu,
    calculate_sentence_chrf,
    calculate_wer,
    evaluate_context_preset_sample,
)


def test_wer_exact_match() -> None:
    ref = "Xin chào tôi là trợ lý phiên dịch"
    hyp = "Xin chào tôi là trợ lý phiên dịch"
    assert calculate_wer(ref, hyp) == 0.0


def test_wer_difference() -> None:
    ref = "xin chào nam"
    hyp = "xin chào bắc"
    wer = calculate_wer(ref, hyp)
    # 1 substitution out of 3 words
    assert abs(wer - (1.0 / 3.0)) < 1e-4


def test_cer_exact_match() -> None:
    ref = "công nghệ thông tin"
    hyp = "công nghệ thông tin"
    assert calculate_cer(ref, hyp) == 0.0


def test_cer_difference() -> None:
    ref = "abc"
    hyp = "abd"
    cer = calculate_cer(ref, hyp)
    assert abs(cer - (1.0 / 3.0)) < 1e-4


def test_bleu_exact_match() -> None:
    ref = "The quick brown fox jumps over the lazy dog"
    hyp = "The quick brown fox jumps over the lazy dog"
    score = calculate_sentence_bleu(ref, hyp)
    assert score > 99.0


def test_chrf_exact_match() -> None:
    ref = "Xin chào các bạn đã đến với hệ thống dịch đa phương thức"
    hyp = "Xin chào các bạn đã đến với hệ thống dịch đa phương thức"
    score = calculate_sentence_chrf(ref, hyp)
    assert score > 95.0


def test_bleu_short_perfect_sentence() -> None:
    score = calculate_sentence_bleu("xin chào", "xin chào")
    assert score == 100.0


def test_corpus_bleu_perfect() -> None:
    references = ["xin chào", "tôi là trợ lý"]
    hypotheses = ["xin chào", "tôi là trợ lý"]
    assert calculate_corpus_bleu(references, hypotheses) == 100.0


def test_corpus_bleu_length_mismatch() -> None:
    assert calculate_corpus_bleu(["một"], []) == 0.0


def test_metrics_treat_nfc_and_nfd_as_identical() -> None:
    nfc = "Tiếng Việt có dấu"
    nfd = unicodedata.normalize("NFD", nfc)
    assert nfc != nfd

    assert calculate_wer(nfc, nfd) == 0.0
    assert calculate_cer(nfc, nfd) == 0.0
    assert calculate_sentence_bleu(nfc, nfd) == 100.0
    assert calculate_sentence_chrf(nfc, nfd) == 100.0


def test_context_keyword_matches_decomposed_unicode() -> None:
    nfd_keyword = unicodedata.normalize("NFD", "quý khách")
    res = evaluate_context_preset_sample(
        preset="Formal",
        hypothesis=f"Kính gửi {nfd_keyword}, cảm ơn.",
        required_keywords=["quý khách"],
        forbidden_keywords=[],
    )
    assert res["passed"] is True
    assert res["found_required"] == ["quý khách"]


def test_builtin_flores_pairs_are_verified_when_cache_exists() -> None:
    cache_file = DEFAULT_CACHE_DIR / "flores200_en_vi.json"
    if not cache_file.exists():
        pytest.skip("FLORES cache not present; skipping offline provenance check")

    cached = json.loads(cache_file.read_text(encoding="utf-8"))
    cached_pairs = {(item["source"], item["reference"]) for item in cached}
    missing = [
        pair
        for pair in BUILTIN_FLORES_PAIRS
        if (pair["source"], pair["reference"]) not in cached_pairs
    ]
    assert not missing


def test_context_preset_evaluation_pass() -> None:
    res = evaluate_context_preset_sample(
        preset="Formal",
        hypothesis="Kính gửi quý khách hợp đồng và báo giá.",
        required_keywords=["quý khách", "kính gửi"],
        forbidden_keywords=["mày", "tao"],
    )
    assert res["passed"] is True
    assert res["score"] == 1.0
    assert "quý khách" in res["found_required"]
    assert len(res["found_forbidden"]) == 0


def test_context_preset_evaluation_fail_on_forbidden() -> None:
    res = evaluate_context_preset_sample(
        preset="Formal",
        hypothesis="Ê mày ơi, hợp đồng gửi quý khách này.",
        required_keywords=["quý khách"],
        forbidden_keywords=["mày", "tao"],
    )
    assert res["passed"] is False
    assert res["score"] < 1.0
    assert "mày" in res["found_forbidden"]


def test_context_preset_empty_hypothesis_fails() -> None:
    res = evaluate_context_preset_sample(
        preset="Formal",
        hypothesis="   ",
        required_keywords=["quý khách"],
        forbidden_keywords=[],
    )
    assert res["passed"] is False
    assert res["score"] == 0.0


def test_context_preset_keyword_uses_word_boundary() -> None:
    res = evaluate_context_preset_sample(
        preset="Formal",
        hypothesis="màymày",
        required_keywords=[],
        forbidden_keywords=["mày"],
    )
    assert res["found_forbidden"] == []


def test_context_preset_reports_coverage() -> None:
    res = evaluate_context_preset_sample(
        preset="Medical",
        hypothesis="bệnh nhân",
        required_keywords=["bệnh nhân", "triệu chứng"],
        forbidden_keywords=[],
    )
    assert res["passed"] is True
    assert res["required_coverage"] == 0.5
    assert res["score"] == 0.5


def test_dataset_loader_context() -> None:
    data = load_context_dataset()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "preset" in first
    assert "source" in first
    assert "reference" in first


def test_flores_samples_loading() -> None:
    pairs = get_flores_samples(limit=5, allow_download=False)
    assert len(pairs) == 5
    for item in pairs:
        assert "source" in item
        assert "reference" in item
        assert len(item["source"]) > 0
        assert len(item["reference"]) > 0


def test_flores_dataset_reports_builtin_source(tmp_path) -> None:
    pairs, meta = get_flores_dataset(limit=3, cache_dir=tmp_path, allow_download=False)
    assert len(pairs) == 3
    assert meta["source"] == "builtin"
    assert meta["returned_pairs"] == 3
    assert "10-pair fallback" in meta["dataset"]


def test_asr_samples_are_marked_unverified(tmp_path) -> None:
    for name in ("sample_16k.wav", "sample.wav"):
        (tmp_path / name).write_bytes(b"0" * 2048)
    samples = get_asr_samples(limit=10, workspace_root=tmp_path)
    assert len(samples) == 2
    for sample in samples:
        assert sample["reference_verified"] is False
        assert sample["reference"]


def test_flores_dataset_reports_cache_source(tmp_path) -> None:
    cached = [
        {"source": "hello", "reference": "xin chào"},
        {"source": "world", "reference": "thế giới"},
    ]
    (tmp_path / "flores200_en_vi.json").write_text(
        json.dumps(cached, ensure_ascii=False),
        encoding="utf-8",
    )
    pairs, meta = get_flores_dataset(limit=2, cache_dir=tmp_path, allow_download=False)
    assert pairs == cached
    assert meta["source"] == "cache"
    assert meta["available_pairs"] == 2


def test_asr_prefers_local_phoasr_snapshot(tmp_path, monkeypatch) -> None:
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    (tmp_path / "model.safetensors").write_bytes(b"weights")
    monkeypatch.setattr(settings, "PHOASR_LOCAL_DIR", str(tmp_path))
    assert ASRAdapter._resolve_model_source() == str(tmp_path.resolve())


def test_asr_falls_back_to_hub_id_without_local_snapshot(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "PHOASR_LOCAL_DIR", str(tmp_path / "missing"))
    assert ASRAdapter._resolve_model_source() == settings.PHOASR_MODEL_ID


def test_asr_ignores_incomplete_local_snapshot(tmp_path, monkeypatch) -> None:
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(settings, "PHOASR_LOCAL_DIR", str(tmp_path))
    assert ASRAdapter._resolve_model_source() == settings.PHOASR_MODEL_ID


def test_context_preset_targets_cover_minimum() -> None:
    assert sum(CONTEXT_PRESET_TARGETS.values()) == MIN_EVAL_SAMPLES


def test_context_dataset_reports_offline_shortfall(tmp_path) -> None:
    samples, meta = get_context_dataset(limit=MIN_EVAL_SAMPLES, cache_dir=tmp_path, allow_download=False)
    assert len(samples) == len(load_context_dataset())
    assert meta["meets_requirement"] is False
    assert meta["returned_samples"] == len(samples)


def test_parse_fleurs_tsv() -> None:
    text = (
        "id-1\t10057024225045006889.wav\tXin chào Việt Nam\tXin chào Việt Nam\t\t16000\tFEMALE\n"
        "id-2\t12028399150700370972.wav\tHôm nay trời đẹp\tHôm nay trời đẹp\t\t32000\tMALE\n"
    )
    rows = _parse_fleurs_tsv(text)
    assert len(rows) == 2
    assert rows[0]["text"] == "Xin chào Việt Nam"
    assert rows[0]["duration_s"] == 1.0
    assert rows[1]["duration_s"] == 2.0


def test_tts_samples_use_fleurs_rows(monkeypatch, tmp_path) -> None:
    rows = [
        {
            "id": "1",
            "filename": "a.wav",
            "text": "Xin chào các bạn hôm nay",
            "duration_s": 2.0,
        },
        {
            "id": "2",
            "filename": "b.wav",
            "text": "Một hai",
            "duration_s": 1.0,
        },
        {
            "id": "3",
            "filename": "c.wav",
            "text": "Xin chào các bạn hôm nay",
            "duration_s": 2.0,
        },
    ]

    def fake_rows(limit=None, cache_dir=None, allow_download=True):
        return rows, {"source": "test", "available_rows": 2}

    monkeypatch.setattr(dataset_loader, "get_fleurs_test_rows", fake_rows)
    samples, meta = get_tts_samples(limit=10, cache_dir=tmp_path)
    assert len(samples) == 1
    assert samples[0]["text"] == "Xin chào các bạn hôm nay"
    assert meta["meets_requirement"] is False


def test_fleurs_asr_falls_back_without_download(monkeypatch, tmp_path) -> None:
    fallback = [
        {
            "id": "local",
            "audio_path": "/tmp/local.wav",
            "reference": "Xin chào",
            "reference_verified": False,
        }
    ]
    monkeypatch.setattr(dataset_loader, "get_asr_samples", lambda limit=10: fallback)
    samples, meta = get_fleurs_asr_dataset(limit=100, cache_dir=tmp_path, allow_download=False)
    assert samples == fallback
    assert meta["source"] == "local_fallback"
    assert meta["meets_requirement"] is False


def test_tts_round_trip_scoring() -> None:
    from scripts.evaluate import BenchmarkRunner

    class FakeTTS:
        async def synthesize(self, text: str, language: str = "vi"):
            return SimpleNamespace(
                audio=np.ones(16000, dtype=np.float32),
                sample_rate=16000,
                engine="fake",
                voice_note="",
            )

    class FakeASR:
        def transcribe_array(self, audio: np.ndarray, duration: float | None = None):
            return {"text": "Xin chào"}

    runner = BenchmarkRunner()
    result = asyncio.run(
        runner._evaluate_tts_async(
            FakeTTS(),
            [{"id": "tts-1", "text": "Xin chào", "language": "vi"}],
            FakeASR(),
        )
    )
    assert result["status"] == "success"
    assert result["success_count"] == 1
    assert result["round_trip_scored_count"] == 1
    assert result["avg_wer_percent"] == 0.0
    assert result["avg_cer_percent"] == 0.0


def test_report_records_translation_backend_device(tmp_path) -> None:
    from scripts.evaluate import BenchmarkRunner

    runner = BenchmarkRunner()
    runner.results["hardware"]["translation"] = {
        "device_requested": "cuda",
        "device_actual": "cpu",
        "gpu_offload": False,
        "gpu_offload_supported": False,
        "n_gpu_layers": 0,
        "fallback_reason": "llama_cpp_cpu_only",
    }
    md_path = tmp_path / "report.md"
    json_path = tmp_path / "results.json"

    runner.export_reports(md_path, json_path)

    report = md_path.read_text(encoding="utf-8")
    assert "TranslateGemma backend" in report
    assert "llama_cpp_cpu_only" in report
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["hardware"]["translation"]["device_actual"] == "cpu"
