"""Tests for BE1: per-adapter threading.Lock serialization.

Verifies that two concurrent calls on the same adapter instance are
serialized (the second call cannot enter the inference block while the
first holds the lock), without requiring GPU or downloaded model weights.

These tests mock ``torch`` and other heavy dependencies at the ``sys.modules``
level so the suite runs on any CI machine without a GPU or ML packages.
"""
from __future__ import annotations

import sys
import threading
import time
import types
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Lightweight sys.modules stubs for packages not installed in the test env.
# Must be done before any app import that transitively pulls these packages.
# ---------------------------------------------------------------------------

def _stub_module(name: str, **attrs: object) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules.setdefault(name, mod)
    return sys.modules[name]


# torch stub (needed by app.core.config and app.models.asr_adapter)
_torch = _stub_module("torch")
_torch.cuda = MagicMock()  # type: ignore[attr-defined]
_torch.cuda.is_available = MagicMock(return_value=False)  # type: ignore[attr-defined]
_torch.cuda.empty_cache = MagicMock()  # type: ignore[attr-defined]
_torch.tensor = MagicMock()  # type: ignore[attr-defined]

# transformers stub (needed by app.models.asr_adapter top-level import)
_stub_module("transformers", pipeline=MagicMock())

# numpy stub (needed by app.models.asr_adapter top-level import)
_np = _stub_module("numpy")
_np.ndarray = type("ndarray", (), {})  # type: ignore[attr-defined]

# soundfile stub
_stub_module("soundfile")

# pydantic_settings stub (needed by app.core.config)
_base = type("BaseSettings", (), {"__init_subclass__": classmethod(lambda cls, **kw: None)})
_stub_module("pydantic_settings", BaseSettings=_base, SettingsConfigDict=MagicMock())

# ---------------------------------------------------------------------------
# Now safe to import app modules
# ---------------------------------------------------------------------------

from app.models.asr_adapter import ASRAdapter  # noqa: E402
from app.models.translation_adapter import TranslationAdapter  # noqa: E402

# ---------------------------------------------------------------------------
# TranslationAdapter – non-streaming concurrency
# ---------------------------------------------------------------------------


class TestTranslationAdapterLock:
    def test_lock_exists(self):
        """TranslationAdapter must expose a threading.Lock as _lock."""
        adapter = TranslationAdapter(model_path=None)
        assert isinstance(adapter._lock, type(threading.Lock()))

    def test_two_concurrent_non_streaming_calls_are_serialized(self):
        """Second translate() call must wait for first to release the lock."""
        adapter = TranslationAdapter(model_path=None)

        call_order: list[str] = []
        event_first_inside = threading.Event()
        event_let_first_finish = threading.Event()
        call_count = [0]

        def counting_llm(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                call_order.append("first_enter")
                event_first_inside.set()
                event_let_first_finish.wait()
                call_order.append("first_exit")
            else:
                call_order.append("second_enter")
            return {"choices": [{"text": "translated"}]}

        adapter._llm = counting_llm

        def call_translate():
            with patch.object(adapter, "_query_ollama", return_value=None), \
                 patch.object(adapter, "load"):
                adapter.translate(text="Xin chào", target_language="en")

        t1 = threading.Thread(target=call_translate)
        t2 = threading.Thread(target=call_translate)

        t1.start()
        # Wait until first thread is inside the lock
        event_first_inside.wait(timeout=2)

        t2.start()
        # Give t2 a moment to try to acquire the lock
        time.sleep(0.05)

        # At this point t2 should be blocked — "second_enter" must NOT be in list
        assert "second_enter" not in call_order, (
            "Second call entered inference before first released the lock"
        )

        # Let first thread finish
        event_let_first_finish.set()
        t1.join(timeout=2)
        t2.join(timeout=2)

        # After both finish: ordering must be first_enter → first_exit → second_enter
        assert call_order == ["first_enter", "first_exit", "second_enter"], (
            f"Unexpected call order: {call_order}"
        )


# ---------------------------------------------------------------------------
# TranslationAdapter – streaming concurrency
# ---------------------------------------------------------------------------


class TestTranslationAdapterStreamLock:
    def test_streaming_lock_is_plain_lock(self):
        """The _lock must be a plain Lock (not RLock) so it cannot be re-entered."""
        adapter = TranslationAdapter(model_path=None)
        assert type(adapter._lock).__name__ == "lock"

    def test_two_concurrent_streaming_calls_are_serialized(self):
        """Second translate_stream() must wait until first generator is exhausted."""
        adapter = TranslationAdapter(model_path=None)

        call_order: list[str] = []
        event_first_inside = threading.Event()
        event_let_first_finish = threading.Event()
        call_count = [0]

        def stream_llm(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                call_order.append("stream1_enter")
                event_first_inside.set()
                event_let_first_finish.wait()
                yield {"choices": [{"text": "tok1"}]}
                call_order.append("stream1_exit")
            else:
                call_order.append("stream2_enter")
                yield {"choices": [{"text": "tok2"}]}

        adapter._llm = stream_llm

        def consume_stream():
            with patch.object(adapter, "load"):
                list(adapter.translate_stream(text="Xin chào", target_language="en"))

        t1 = threading.Thread(target=consume_stream)
        t2 = threading.Thread(target=consume_stream)

        t1.start()
        event_first_inside.wait(timeout=2)
        t2.start()
        time.sleep(0.05)

        assert "stream2_enter" not in call_order, (
            "Second streaming call entered inference before first released the lock"
        )

        event_let_first_finish.set()
        t1.join(timeout=2)
        t2.join(timeout=2)

        assert call_order == ["stream1_enter", "stream1_exit", "stream2_enter"], (
            f"Unexpected streaming call order: {call_order}"
        )


# ---------------------------------------------------------------------------
# ASRAdapter – transcribe concurrency
# ---------------------------------------------------------------------------


class TestASRAdapterLock:
    def test_lock_exists(self):
        """ASRAdapter must expose a threading.Lock as _lock."""
        adapter = ASRAdapter(device="cpu")
        assert isinstance(adapter._lock, type(threading.Lock()))

    def test_two_concurrent_transcribe_calls_are_serialized(self, tmp_path):
        """Second transcribe() must wait for first to release the lock.

        A real WAV file is written so ``load_audio_file`` succeeds; the
        pipeline call itself is replaced with a fake that records entry order.
        """

        # If the real numpy/soundfile are unavailable, create bytes manually
        # so the test can still validate the lock without I/O.
        try:
            real_np = sys.modules.get("numpy")
            # Try a real attribute that only exists on actual numpy
            _ = real_np.float32  # type: ignore[union-attr]
            has_real_numpy = True
        except (AttributeError, TypeError):
            has_real_numpy = False

        adapter = ASRAdapter(device="cpu")

        call_order: list[str] = []
        event_first_inside = threading.Event()
        event_let_first_finish = threading.Event()
        call_count = [0]

        def fake_pipe(data, generate_kwargs=None):
            call_count[0] += 1
            if call_count[0] == 1:
                call_order.append("asr1_enter")
                event_first_inside.set()
                event_let_first_finish.wait()
                call_order.append("asr1_exit")
            else:
                call_order.append("asr2_enter")
            return {"text": "hello"}

        adapter._pipe = fake_pipe  # skip real load()

        if has_real_numpy:
            import numpy as _np_real
            import soundfile as _sf_real
            wav_path = tmp_path / "dummy.wav"
            samples = _np_real.ones(16000, dtype=_np_real.float32) * 0.1
            _sf_real.write(str(wav_path), samples, 16000)
            audio_arg = str(wav_path)
        else:
            # Patch load_audio_file to avoid needing real numpy/soundfile
            audio_arg = "/fake/path.wav"

        def do_transcribe():
            with patch.object(adapter, "load"), \
                 patch("app.models.asr_adapter.load_audio_file",
                       return_value=(MagicMock(), 1.0)):
                adapter.transcribe(audio_arg)

        t1 = threading.Thread(target=do_transcribe)
        t2 = threading.Thread(target=do_transcribe)

        t1.start()
        event_first_inside.wait(timeout=2)
        t2.start()
        time.sleep(0.05)

        assert "asr2_enter" not in call_order, (
            "Second ASR call entered inference before first released the lock"
        )

        event_let_first_finish.set()
        t1.join(timeout=2)
        t2.join(timeout=2)

        assert call_order == ["asr1_enter", "asr1_exit", "asr2_enter"], (
            f"Unexpected ASR call order: {call_order}"
        )
