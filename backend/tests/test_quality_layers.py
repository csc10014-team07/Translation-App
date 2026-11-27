"""Layered quality tests: unit, integration, system, stress, and regression bugs."""
from __future__ import annotations

import io
import sys
import threading
import time
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import app.api.routes.ocr as ocr_route
import numpy as np
import pytest
import soundfile as sf
from app.api.deps import dep_model_manager
from app.core import vram_monitor
from app.core.vram_monitor import (
    _MAX_SAMPLES_PER_MODEL,
    _MAX_VRAM_SNAPSHOTS,
    VRAMTracker,
)
from app.main import app
from app.models.translation_adapter import TranslationAdapter
from app.models.tts_adapter import TTSAdapter, TTSResult
from PIL import Image
from starlette.testclient import TestClient


class _FakeTranslation:
    def __init__(self, delay_s: float = 0.0) -> None:
        self.delay_s = delay_s

    def translate_with_engine(self, text: str, **kwargs) -> tuple[str, str]:
        time.sleep(self.delay_s)
        return f"translated:{text}", "fake"

    def translate(self, text: str, **kwargs) -> str:
        time.sleep(self.delay_s)
        return f"translated:{text}"


class _FakeManager:
    _is_started = True

    def __init__(self, translation: _FakeTranslation | None = None) -> None:
        self.translation = translation or _FakeTranslation()
        self.ocr = SimpleNamespace(extract_text=self._extract_text)

    @staticmethod
    def _extract_text(image_bytes: bytes) -> tuple[str, str, list]:
        time.sleep(0.05)
        return "Hello", "en", []

    async def get_translation(self) -> _FakeTranslation:
        return self.translation

    async def get_ocr(self):
        return self.ocr

    def get_status(self) -> dict:
        return {
            "device": "cpu",
            "started": True,
            "models_loaded": {"asr": False, "translation": True, "ocr": True, "tts_pocket": False},
            "load_errors": {},
        }


def _client_with_manager(manager: _FakeManager) -> TestClient:
    app.dependency_overrides[dep_model_manager] = lambda: manager
    return TestClient(app)


def _clear_overrides() -> None:
    app.dependency_overrides.pop(dep_model_manager, None)


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (120, 40), color=(255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _wav_bytes(duration_s: float = 3.5, sample_rate: int = 16000) -> bytes:
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    signal = (0.3 * np.sin(2 * np.pi * 220 * t) * 32767).astype(np.int16)
    buf = io.BytesIO()
    sf.write(buf, signal, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


@pytest.mark.integration
def test_bug_01_tts_reference_audio_is_persisted(monkeypatch):
    """BUG-01: uploaded reference audio must reach the TTS adapter unmangled."""
    captured: dict[str, object] = {}

    async def fake_synthesize(
        self,
        text: str,
        language: str = "English",
        reference_audio_path=None,
        voice_style=None,
        preferred_engine=None,
    ) -> TTSResult:
        path = Path(reference_audio_path)
        captured["path"] = path
        captured["exists"] = path.exists()
        normalized, sample_rate = sf.read(str(path), dtype="float32")
        captured["sample_rate"] = sample_rate
        captured["duration_s"] = len(normalized) / sample_rate
        return TTSResult(np.zeros(1600, dtype=np.float32), 16000, engine="pocket_tts")

    monkeypatch.setattr(TTSAdapter, "synthesize", fake_synthesize)
    payload = _wav_bytes()

    response = TestClient(app).post(
        "/api/tts",
        data={"text": "hello", "language": "English"},
        files={"reference_audio": ("voice.wav", payload, "audio/wav")},
    )

    assert response.status_code == 200, response.text
    assert captured["exists"] is True
    path = captured["path"]
    assert isinstance(path, Path)
    assert path.suffix == ".wav"
    assert captured["sample_rate"] == 24_000
    assert captured["duration_s"] >= 3.0


@pytest.mark.stress
def test_bug_03_concurrent_load_calls_llama_once(tmp_path, monkeypatch):
    """BUG-03: concurrent lazy loads must not construct two GGUF models."""
    calls: list[str] = []
    start_barrier = threading.Barrier(2)

    class FakeLlama:
        def __init__(self, *args, **kwargs) -> None:
            calls.append("constructed")
            time.sleep(0.25)

        def __call__(self, *args, **kwargs):
            return {"choices": [{"text": "ok"}]}

    fake_module = types.ModuleType("llama_cpp")
    fake_module.Llama = FakeLlama
    fake_module.llama_supports_gpu_offload = lambda: False
    fake_module.llama_print_system_info = lambda: "fake"
    monkeypatch.setitem(sys.modules, "llama_cpp", fake_module)

    model_file = tmp_path / "fake.gguf"
    model_file.write_bytes(b"fake")
    adapter = TranslationAdapter(model_path=str(model_file))
    adapter.device = "cpu"

    def run_load() -> None:
        start_barrier.wait(timeout=2)
        adapter.load()

    threads = [threading.Thread(target=run_load) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert calls == ["constructed"]
    assert adapter._llm is not None


@pytest.mark.unit
@pytest.mark.stress
def test_bug_04_vram_metrics_are_bounded(monkeypatch):
    """BUG-04: long-running servers must not grow latency history without bound."""
    monkeypatch.setattr(
        vram_monitor,
        "get_vram_info",
        lambda: {"used_mb": 0.0, "free_mb": 0.0, "total_mb": 0.0, "allocated_mb": 0.0},
    )
    tracker = VRAMTracker()

    for index in range(_MAX_SAMPLES_PER_MODEL + 5):
        tracker.record_warm_inference("gemma", float(index))
        tracker.record_cold_start("phoasr", float(index))
    for _ in range(_MAX_VRAM_SNAPSHOTS + 5):
        tracker.snapshot_vram("stress")

    assert len(tracker._warm_inferences["gemma"]) == _MAX_SAMPLES_PER_MODEL
    assert len(tracker._cold_starts["phoasr"]) == _MAX_SAMPLES_PER_MODEL
    assert len(tracker._vram_snapshots) == _MAX_VRAM_SNAPSHOTS
    assert tracker._warm_inferences["gemma"][-1] == float(_MAX_SAMPLES_PER_MODEL + 4)


@pytest.mark.integration
@pytest.mark.profiling
def test_bug_05_ocr_latency_excludes_translation_stage(monkeypatch):
    """BUG-05: the rapidocr metric must measure OCR, not OCR plus translation."""
    recorded: dict[str, float] = {}
    manager = _FakeManager(translation=_FakeTranslation(delay_s=0.2))
    client = _client_with_manager(manager)

    def fake_record(model_name: str, latency_ms: float) -> None:
        recorded[model_name] = latency_ms

    monkeypatch.setattr(ocr_route.vram_tracker, "record_warm_inference", fake_record)
    try:
        response = client.post(
            "/api/ocr",
            files={"image": ("notice.png", _png_bytes(), "image/png")},
            data={"target_language": "vi"},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["translated_text"] == "translated:Hello"
    assert "rapidocr" in recorded
    assert recorded["rapidocr"] < body["elapsed_ms"] * 0.75


@pytest.mark.integration
def test_system_health_translate_and_metrics_contract(monkeypatch):
    """System path: health probe -> translation -> metrics share a working manager."""
    manager = _FakeManager(translation=_FakeTranslation(delay_s=0.01))
    monkeypatch.setattr("app.models.manager.get_model_manager", lambda: manager)
    client = _client_with_manager(manager)
    try:
        health = client.get("/health")
        translated = client.post(
            "/api/translate",
            json={"text": "Xin chào", "target_language": "English"},
        )
        metrics = client.get("/api/metrics")
    finally:
        _clear_overrides()

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert translated.status_code == 200
    translated_body = translated.json()
    assert translated_body["translated_text"] == "translated:Xin chào"
    assert translated_body["elapsed_ms"] >= 0
    assert metrics.status_code == 200
    assert metrics.json()["model_status"]["models_loaded"]["translation"] is True


@pytest.mark.stress
def test_stress_concurrent_translate_calls_are_serialized():
    """Stress: many concurrent calls must never enter the LLM at the same time."""
    adapter = TranslationAdapter(model_path=None)
    state = {"active": 0, "max_active": 0}
    state_lock = threading.Lock()

    def fake_llm(prompt: str, **kwargs):
        with state_lock:
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
        time.sleep(0.01)
        with state_lock:
            state["active"] -= 1
        return {"choices": [{"text": "ok"}]}

    adapter._llm = fake_llm

    def call_translate(_: int) -> str:
        return adapter.translate(text="Xin chào", target_language="en")

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(call_translate, range(24)))

    assert results == ["ok"] * 24
    assert state["max_active"] == 1
