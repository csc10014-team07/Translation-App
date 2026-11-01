"""Unit and seam tests for TranslationAdapter (Ticket 02)."""
from unittest.mock import MagicMock, patch

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


def test_fallback_tier2_ollama():
    """Verify Tier 2 probes Ollama when _llm is None."""
    adapter = TranslationAdapter()
    adapter._llm = None

    with patch.object(adapter, "_query_ollama", return_value="Ollama translated text") as mock_ollama:
        text, engine = adapter.translate_with_engine(
            text="Kiểm tra",
            target_language="English",
            source_language="vi",
        )
        assert text == "Ollama translated text"
        assert engine == "ollama:gemma2"
        assert mock_ollama.called


def test_fallback_tier3_mymemory():
    """Verify Tier 3 falls back to MyMemoryTranslator when _llm and Ollama fail."""
    adapter = TranslationAdapter()
    adapter._llm = None

    with (
        patch.object(adapter, "_query_ollama", return_value=None),
        patch("deep_translator.MyMemoryTranslator.translate", return_value="Neural fallback text") as mock_mm,
    ):
        text, engine = adapter.translate_with_engine(
            text="Xin chào",
            target_language="English",
            source_language="vi",
        )
        assert text == "Neural fallback text"
        assert engine == "mymemory"
        assert mock_mm.called


def test_fallback_tier4_degraded():
    """Verify Tier 4 produces degraded echo when all inference engines fail."""
    adapter = TranslationAdapter()
    adapter._llm = None

    with (
        patch.object(adapter, "_query_ollama", return_value=None),
        patch("deep_translator.MyMemoryTranslator.translate", side_effect=Exception("Network down")),
    ):
        text, engine = adapter.translate_with_engine(
            text="Xin chào",
            target_language="English",
            source_language="vi",
        )
        assert text == "[English] Xin chào"
        assert engine == "fallback:degraded"



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
