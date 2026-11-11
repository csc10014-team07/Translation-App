"""Unit and seam tests for TranslationAdapter (Ticket 02)."""
from unittest.mock import MagicMock

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
