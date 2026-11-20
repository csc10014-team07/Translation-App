"""Unit and seam tests for TranslationAdapter (Ticket 02)."""
import sys
import types
from unittest.mock import MagicMock

from app.core.config import settings
from app.models.translation_adapter import (
    CONTEXT_PRESETS,
    TranslationAdapter,
)


def test_context_presets_coverage():
    """Verify all 5 required presets plus variants exist in CONTEXT_PRESETS."""
    required = ["Formal", "Friendly", "Casual", "IT", "Technical", "Medical", "Travel"]
    for preset in required:
        assert preset in CONTEXT_PRESETS, f"Preset '{preset}' must be defined"
        assert len(CONTEXT_PRESETS[preset]) > 0


def test_build_prompt_with_presets_and_custom_context():
    """Verify Gemma instruction prompt formatting adheres to official specification."""
    adapter = TranslationAdapter()

    # 1. Formal Preset
    prompt_formal = adapter.build_prompt(
        text="Xin chào",
        source_lang="vi",
        target_lang="en",
        context_preset="Formal",
    )
    assert "<start_of_turn>user" in prompt_formal
    assert "<end_of_turn>" in prompt_formal
    assert "<start_of_turn>model" in prompt_formal
    assert "Vietnamese to English translator" in prompt_formal
    assert CONTEXT_PRESETS["Formal"] in prompt_formal
    assert "Xin chào" in prompt_formal

    # 2. Friendly / Casual Preset
    prompt_friendly = adapter.build_prompt(
        text="Xin chào",
        source_lang="vi",
        target_lang="en",
        context_preset="Friendly",
    )
    assert CONTEXT_PRESETS["Friendly"] in prompt_friendly
    assert prompt_formal != prompt_friendly, "Formal and Friendly prompts must produce distinct instructions"

    # 3. IT / Technical Preset with Custom Context
    prompt_tech = adapter.build_prompt(
        text="Refactor lại API",
        source_lang="vi",
        target_lang="en",
        context_preset="IT/Technical",
        custom_context="Deploying to AWS Kubernetes cluster",
    )
    assert CONTEXT_PRESETS["Technical"] in prompt_tech
    assert "Deploying to AWS Kubernetes cluster" in prompt_tech

    # 4. Empty context fallback
    prompt_empty = adapter.build_prompt(
        text="Test",
        source_lang="vi",
        target_lang="en",
    )
    assert "General natural translation" in prompt_empty


def test_build_prompt_preserves_unmatched_free_text_context():
    """Free text passed via context_preset must not be silently dropped."""
    adapter = TranslationAdapter()

    prompt = adapter.build_prompt(
        text="Cho tôi xem thực đơn",
        source_lang="vi",
        target_lang="en",
        context_preset="Hội thoại nhà hàng",
    )

    assert "Hội thoại nhà hàng" in prompt
    assert "General natural translation" not in prompt


def test_fallback_tier1_translategemma():
    """Verify Tier 1 uses TranslateGemma 4B when _llm is available."""
    adapter = TranslationAdapter()
    fake_llm = MagicMock()
    fake_llm.return_value = {
        "choices": [{"text": "Hello, how are you today?"}]
    }
    adapter._llm = fake_llm

    text, engine = adapter.translate_with_engine(
        text="Chào bạn, hôm nay thế nào?",
        target_language="English",
        source_language="vi",
        context_preset="Friendly",
    )
    assert text == "Hello, how are you today?"
    assert engine == "translategemma-4b"
    assert fake_llm.called


def test_translation_model_not_loaded_raises_runtime_error():
    """Verify RuntimeError is raised when _llm is not loaded (fallback removed in 1628c44)."""
    import pytest

    adapter = TranslationAdapter()
    adapter.model_path = None
    adapter._llm = None

    with pytest.raises(RuntimeError, match="TranslateGemma model is not loaded"):
        adapter.translate(
            text="Kiểm tra",
            target_language="English",
            source_language="vi",
        )


def test_translation_empty_output_raises_runtime_error():
    """Verify RuntimeError is raised when TranslateGemma produces empty output."""
    import pytest

    adapter = TranslationAdapter()
    fake_llm = MagicMock(return_value={"choices": [{"text": ""}]})
    adapter._llm = fake_llm

    with pytest.raises(RuntimeError, match="returned empty response"):
        adapter.translate(
            text="Xin chào",
            target_language="English",
            source_language="vi",
        )


def test_translation_inference_failure_raises_runtime_error():
    """Verify inference exceptions are converted to RuntimeError."""
    import pytest

    adapter = TranslationAdapter()
    fake_llm = MagicMock(side_effect=Exception("CUDA out of memory"))
    adapter._llm = fake_llm

    with pytest.raises(RuntimeError, match="Translation failed"):
        adapter.translate(
            text="Xin chào",
            target_language="English",
            source_language="vi",
        )



def test_translate_stream_generator():
    """Verify translate_stream yields chunks correctly."""
    adapter = TranslationAdapter()
    fake_llm = MagicMock()
    fake_llm.return_value = [
        {"choices": [{"text": "Hello"}]},
        {"choices": [{"text": " world"}]},
    ]
    adapter._llm = fake_llm

    tokens = list(adapter.translate_stream(
        text="Xin chào",
        target_language="English",
        source_language="vi",
    ))
    assert tokens == ["Hello", " world"]


def _install_fake_llama_cpp(monkeypatch, supports_gpu: bool, fail_gpu_load: bool = False):
    calls = []

    class FakeLlama:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            if fail_gpu_load and kwargs.get("n_gpu_layers", 0) != 0:
                raise RuntimeError("CUDA out of memory")

    fake_module = types.ModuleType("llama_cpp")
    fake_module.Llama = FakeLlama
    fake_module.llama_supports_gpu_offload = lambda: supports_gpu
    fake_module.llama_print_system_info = lambda: b"fake llama.cpp CPU"
    monkeypatch.setitem(sys.modules, "llama_cpp", fake_module)
    return calls


def _make_adapter(tmp_path):
    model_path = tmp_path / "fake.gguf"
    model_path.write_bytes(b"fake")
    return TranslationAdapter(model_path=str(model_path))


def test_load_uses_gpu_when_offload_supported(tmp_path, monkeypatch):
    adapter = _make_adapter(tmp_path)
    adapter.device = "cuda"
    monkeypatch.setattr(settings, "GEMMA_N_GPU_LAYERS", -1)
    calls = _install_fake_llama_cpp(monkeypatch, supports_gpu=True)

    adapter.load()

    info = adapter.backend_info()
    assert info["device_actual"] == "cuda"
    assert info["gpu_offload"] is True
    assert info["n_gpu_layers"] == -1
    assert calls[0]["n_gpu_layers"] == -1


def test_load_falls_back_to_cpu_when_llama_cpp_cpu_only(tmp_path, monkeypatch):
    adapter = _make_adapter(tmp_path)
    adapter.device = "cuda"
    monkeypatch.setattr(settings, "GEMMA_N_GPU_LAYERS", -1)
    calls = _install_fake_llama_cpp(monkeypatch, supports_gpu=False)

    adapter.load()

    info = adapter.backend_info()
    assert info["device_actual"] == "cpu"
    assert info["gpu_offload"] is False
    assert info["n_gpu_layers"] == 0
    assert info["fallback_reason"] == "llama_cpp_cpu_only"
    assert calls[0]["n_gpu_layers"] == 0


def test_load_falls_back_to_cpu_when_gpu_load_fails(tmp_path, monkeypatch):
    adapter = _make_adapter(tmp_path)
    adapter.device = "cuda"
    monkeypatch.setattr(settings, "GEMMA_N_GPU_LAYERS", -1)
    calls = _install_fake_llama_cpp(monkeypatch, supports_gpu=True, fail_gpu_load=True)

    adapter.load()

    info = adapter.backend_info()
    assert info["device_actual"] == "cpu"
    assert info["n_gpu_layers"] == 0
    assert info["fallback_reason"] == "gpu_load_failed"
    assert calls[0]["n_gpu_layers"] == -1
    assert calls[1]["n_gpu_layers"] == 0
    assert calls[1]["n_ctx"] == 2048
