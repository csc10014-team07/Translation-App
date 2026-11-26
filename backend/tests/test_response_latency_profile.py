"""Response contract, latency budget, and cProfile tests."""
from __future__ import annotations

import cProfile
import io
import pstats
import time

import pytest
from app.api.deps import dep_model_manager
from app.main import app
from app.models.translation_adapter import TranslationAdapter
from starlette.testclient import TestClient


class _LatencyTranslation:
    def __init__(self, delay_s: float = 0.02) -> None:
        self.delay_s = delay_s

    def translate_with_engine(self, text: str, **kwargs) -> tuple[str, str]:
        time.sleep(self.delay_s)
        return f"translated:{text}", "fake"


class _LatencyManager:
    _is_started = True

    def __init__(self) -> None:
        self.translation = _LatencyTranslation()

    async def get_translation(self) -> _LatencyTranslation:
        return self.translation

    def get_status(self) -> dict:
        return {
            "device": "cpu",
            "started": True,
            "models_loaded": {"translation": True},
            "load_errors": {},
        }


@pytest.mark.integration
@pytest.mark.profiling
def test_translate_response_contract_and_latency_budget():
    """Translation latency is reported and stays within a mocked fast-path budget."""
    manager = _LatencyManager()
    app.dependency_overrides[dep_model_manager] = lambda: manager
    client = TestClient(app)
    try:
        started = time.perf_counter()
        response = client.post(
            "/api/translate",
            json={"text": "Xin chào", "target_language": "English"},
        )
        wall_ms = (time.perf_counter() - started) * 1000
        metrics = client.get("/api/metrics")
    finally:
        app.dependency_overrides.pop(dep_model_manager, None)

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) >= {
        "translated_text",
        "source_language",
        "target_language",
        "engine_used",
        "elapsed_ms",
    }
    assert body["translated_text"] == "translated:Xin chào"
    assert body["elapsed_ms"] >= 15.0
    assert body["elapsed_ms"] <= wall_ms
    assert wall_ms < 1000.0

    assert metrics.status_code == 200
    metrics_body = metrics.json()
    assert metrics_body["model_status"]["models_loaded"]["translation"] is True
    assert metrics_body["latency_metrics"]["warm_inferences"]["gemma"]["count"] >= 1


@pytest.mark.unit
@pytest.mark.profiling
def test_profile_translate_hot_path_records_translate_and_prompt_builder():
    """cProfile must see the route hot path helpers, not just the test harness."""
    adapter = TranslationAdapter(model_path=None)
    adapter._llm = lambda prompt, **kwargs: {"choices": [{"text": "ok"}]}

    profile = cProfile.Profile()
    profile.enable()
    assert adapter.translate(text="Xin chào", target_language="en") == "ok"
    profile.disable()

    stream = io.StringIO()
    stats = pstats.Stats(profile, stream=stream)
    stats.sort_stats("cumulative").print_stats()
    rendered = stream.getvalue()

    assert "translate" in rendered
    assert "build_prompt" in rendered
    assert stats.total_calls > 0


@pytest.mark.integration
def test_health_response_latency_budget():
    """The liveness probe must not initialize models or block on GPU work."""
    client = TestClient(app)
    started = time.perf_counter()
    response = client.get("/health")
    wall_ms = (time.perf_counter() - started) * 1000

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert wall_ms < 1000.0
