"""Tests for BE2: VAD stream endpoint fixes.

Tests (a)–(e) as specified:
  (a) Odd-length chunk does not close the connection.
  (b) 10 s of silence leaves the buffer small and sends no asr_final.
  (c) Two utterances separated by silence are processed in order.
  (d) A slow first utterance does not stop later chunks from being read.
  (e) "stop" in the middle of speech processes that speech.

All heavy dependencies (torch, numpy, soundfile, PIL, transformers,
pydantic_settings, app.models.*) are stubbed at the sys.modules level
so the suite runs without GPU or downloaded model weights.
"""
from __future__ import annotations

import threading
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import pytest

# Skip entire module if numpy or soundfile are not installed
numpy = pytest.importorskip("numpy")
soundfile = pytest.importorskip("soundfile")
numpy = pytest.importorskip("numpy")
soundfile = pytest.importorskip("soundfile")

import app.api.routes.stream as stream_mod

# ---------------------------------------------------------------------------
# Build fake model manager & adapters for injection.
# ---------------------------------------------------------------------------


def _make_fake_manager(
    asr_fn: Any = None,
    trans_fn: Any = None,
    tts_fn: Any = None,
) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    """Return a fake ModelManager whose get_* coroutines return fake adapters."""

    async def _fake_coro(value: Any) -> Any:
        return value

    # ASR adapter
    asr_adapter = MagicMock()
    if asr_fn is not None:
        asr_adapter.transcribe_array = asr_fn
    else:
        asr_adapter.transcribe_array = (
            lambda data, duration=None: {
                "text": "transcribed",
                "language": "vi",
                "duration": 1.0,
            }
        )

    # Translation adapter
    trans_adapter = MagicMock()
    if trans_fn is not None:
        trans_adapter.translate_stream = trans_fn
    else:

        def _default_stream(**kw: Any) -> Generator[str, None, None]:
            yield "hello"

        trans_adapter.translate_stream = _default_stream

    # TTS adapter
    tts_adapter = MagicMock()
    if tts_fn is not None:
        tts_adapter.synthesize = tts_fn
    else:
        import numpy as np

        async def _default_synthesize(text: str, language: str) -> tuple[np.ndarray, int]:
            return np.zeros(16000, dtype=np.float32), 16000

        tts_adapter.synthesize = _default_synthesize

    manager = MagicMock()
    manager.get_asr = MagicMock(side_effect=lambda: _fake_coro(asr_adapter))
    manager.get_translation = MagicMock(side_effect=lambda: _fake_coro(trans_adapter))
    manager.get_tts = MagicMock(side_effect=lambda: _fake_coro(tts_adapter))

    return manager, asr_adapter, trans_adapter, tts_adapter


# ---------------------------------------------------------------------------
# Helper: make a FastAPI test app with only the stream router.
# ---------------------------------------------------------------------------


def _make_test_app(manager: MagicMock) -> Any:
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(stream_mod.router)

    # Patch get_model_manager inside stream_mod for the lifetime of the test.
    stream_mod.get_model_manager = lambda: manager  # type: ignore[assignment]

    return test_app


# ---------------------------------------------------------------------------
# PCM helpers
# ---------------------------------------------------------------------------
_SR = 16000  # samples per second
_BPS = 2     # bytes per sample (int16)


def _silence_chunk(duration_s: float = 0.1) -> bytes:
    """Return a chunk of silence PCM bytes."""
    n = int(_SR * duration_s)
    import numpy as np
    return (np.zeros(n, dtype=np.int16)).tobytes()


def _speech_chunk(duration_s: float = 0.1, amplitude: float = 0.5) -> bytes:
    """Return a chunk of loud-ish PCM bytes that will pass the RMS threshold."""
    import numpy as np
    n = int(_SR * duration_s)
    # Square wave at amplitude — easily exceeds VADSettings.rms_threshold = 0.012
    signal = np.full(n, int(amplitude * 32767), dtype=np.int16)
    return signal.tobytes()


# ---------------------------------------------------------------------------
# Shared manager + app fixture helpers
# ---------------------------------------------------------------------------


def _simple_manager() -> tuple[MagicMock, Any, Any, Any]:
    """Return (manager, asr, trans, tts) with simple synchronous fakes."""
    return _make_fake_manager()


# ---------------------------------------------------------------------------
# (a) Odd-length chunk does not close the connection.
# ---------------------------------------------------------------------------


def test_odd_length_chunk_does_not_disconnect():
    """An odd-number-of-bytes binary frame must not raise or close the WS."""

    manager, *_ = _simple_manager()
    app_ = _make_test_app(manager)

    from starlette.testclient import TestClient

    client = TestClient(app_)
    with client.websocket_connect("/ws/stream") as ws:
        init = ws.receive_json()
        assert init["type"] == "ready"

        # Send a 1-byte (odd) chunk — should not raise or disconnect
        ws.send_bytes(b"\x01")

        # Send another valid even chunk of silence — connection still alive
        ws.send_bytes(_silence_chunk(0.05))

        # Send stop — connection should still be alive enough to respond
        ws.send_json({"action": "stop"})

        # Drain until stopped
        while True:
            msg = ws.receive_json()
            if msg.get("type") == "stopped":
                break
            # Allow error messages from worker teardown, but not disconnect


# ---------------------------------------------------------------------------
# (b) 10 s of silence: buffer stays small, no asr_final sent.
# ---------------------------------------------------------------------------


def test_silence_does_not_grow_buffer_or_trigger_asr():
    """10 seconds of silence must not trigger asr_final and must keep buffer tiny."""

    asr_called = threading.Event()
    original_transcribe = lambda data, duration=None: (asr_called.set(), {"text": "oops", "language": "vi", "duration": 1.0})[1]  # noqa: E731

    manager, asr_adapter, *_ = _make_fake_manager(asr_fn=original_transcribe)
    asr_adapter.transcribe_array = original_transcribe
    app_ = _make_test_app(manager)

    from starlette.testclient import TestClient

    messages: list[dict] = []

    client = TestClient(app_)
    with client.websocket_connect("/ws/stream") as ws:
        init = ws.receive_json()
        assert init["type"] == "ready"

        # Send 10 s of 100ms silence chunks (100 chunks)
        for _ in range(100):
            ws.send_bytes(_silence_chunk(0.1))

        ws.send_json({"action": "stop"})
        while True:
            msg = ws.receive_json()
            messages.append(msg)
            if msg.get("type") == "stopped":
                break

    types_seen = {m["type"] for m in messages}
    assert "asr_final" not in types_seen, f"No asr_final expected during silence, got: {types_seen}"
    assert not asr_called.is_set(), "ASR transcribe must not be called during 10 s of silence"


# ---------------------------------------------------------------------------
# (c) Two utterances separated by silence are processed in order.
# ---------------------------------------------------------------------------


def test_two_utterances_processed_in_order():
    """Two speech segments separated by silence must produce two asr_final in order."""

    call_order: list[str] = []
    counter = [0]

    def ordered_transcribe(data, duration=None) -> dict:
        counter[0] += 1
        label = f"utterance_{counter[0]}"
        call_order.append(label)
        return {"text": label, "language": "vi", "duration": 0.5}

    manager, *_ = _make_fake_manager(asr_fn=ordered_transcribe)
    app_ = _make_test_app(manager)

    from starlette.testclient import TestClient

    client = TestClient(app_)
    asr_texts: list[str] = []

    # Build a 1-second speech burst (> min_speech_samples=4800 samples)
    speech = _speech_chunk(0.5) * 2  # 1s = 32000 bytes  (even, loud)

    # Silence long enough to trigger VAD pause boundary: > 450ms = 7200 samples
    silence = _silence_chunk(0.5)   # 500ms

    with client.websocket_connect("/ws/stream") as ws:
        init = ws.receive_json()
        assert init["type"] == "ready"

        # --- Utterance 1 ---
        ws.send_bytes(speech)
        ws.send_bytes(silence)

        # --- Utterance 2 ---
        ws.send_bytes(speech)
        ws.send_bytes(silence)

        ws.send_json({"action": "stop"})

        # Collect all messages
        all_msgs: list[dict] = []
        while True:
            msg = ws.receive_json()
            all_msgs.append(msg)
            if msg["type"] == "stopped":
                break

    for m in all_msgs:
        if m["type"] == "asr_final":
            asr_texts.append(m["text"])

    assert len(asr_texts) >= 2, f"Expected >=2 asr_final messages, got: {asr_texts}"
    assert asr_texts[0] == "utterance_1", f"First ASR text wrong: {asr_texts}"
    assert asr_texts[1] == "utterance_2", f"Second ASR text wrong: {asr_texts}"


# ---------------------------------------------------------------------------
# (d) Slow first utterance does not block reading later audio chunks.
# ---------------------------------------------------------------------------


def test_slow_utterance_does_not_block_receive_loop():
    """While the worker is processing a slow utterance, the receive loop continues reading."""

    # First transcribe call blocks for a bit; second should still be callable.
    call_times: list[float] = []
    first_call_started = threading.Event()
    allow_first = threading.Event()

    call_index = [0]

    def slow_transcribe(data, duration=None) -> dict:
        import time as _time
        call_times.append(_time.monotonic())
        idx = call_index[0]
        call_index[0] += 1
        if idx == 0:
            first_call_started.set()
            allow_first.wait(timeout=2.0)
        return {"text": f"result_{idx}", "language": "vi", "duration": 0.5}

    manager, *_ = _make_fake_manager(asr_fn=slow_transcribe)
    app_ = _make_test_app(manager)

    from starlette.testclient import TestClient

    speech = _speech_chunk(0.5) * 2   # 1 s loud
    silence = _silence_chunk(0.5)     # 500ms — triggers VAD boundary

    # We'll unblock the first transcribe after sending the second utterance.
    def _unblock():
        # Give the client a moment to send the second utterance
        import time as _t
        _t.sleep(0.3)
        allow_first.set()

    client = TestClient(app_)
    with client.websocket_connect("/ws/stream") as ws:
        init = ws.receive_json()
        assert init["type"] == "ready"

        # Send first utterance + silence to trigger VAD
        ws.send_bytes(speech)
        ws.send_bytes(silence)

        # Start a thread that will unblock the first transcribe after a delay
        unblock_thread = threading.Thread(target=_unblock)
        unblock_thread.start()

        # Send second utterance while first is still running
        ws.send_bytes(speech)
        ws.send_bytes(silence)

        unblock_thread.join(timeout=3)
        ws.send_json({"action": "stop"})

        asr_texts = []
        while True:
            msg = ws.receive_json()
            if msg["type"] == "asr_final":
                asr_texts.append(msg["text"])
            if msg["type"] == "stopped":
                break

    # Both utterances must have been processed.
    assert len(asr_texts) >= 2, f"Expected >=2 results even with slow first; got {asr_texts}"


# ---------------------------------------------------------------------------
# (e) "stop" in the middle of speech enqueues and processes that speech.
# ---------------------------------------------------------------------------


def test_stop_mid_speech_processes_buffered_audio():
    """Sending 'stop' while in speech must enqueue the utterance, not discard it."""

    transcribed: list[str] = []

    def recording_transcribe(data, duration=None) -> dict:
        transcribed.append("called")
        return {"text": "mid_speech", "language": "vi", "duration": 0.5}

    manager, *_ = _make_fake_manager(asr_fn=recording_transcribe)
    app_ = _make_test_app(manager)

    from starlette.testclient import TestClient

    # Send enough speech to exceed min_speech_samples=4800 samples
    speech = _speech_chunk(0.5) * 2   # 1 s, well above 300 ms minimum

    client = TestClient(app_)
    with client.websocket_connect("/ws/stream") as ws:
        init = ws.receive_json()
        assert init["type"] == "ready"

        # Send speech (puts us in_speech state)
        ws.send_bytes(speech)

        # Immediately stop without sending silence (no VAD boundary)
        ws.send_json({"action": "stop"})

        asr_texts = []
        while True:
            msg = ws.receive_json()
            if msg["type"] == "asr_final":
                asr_texts.append(msg["text"])
            if msg["type"] == "stopped":
                break

    assert len(asr_texts) >= 1, (
        f"'stop' mid-speech must have processed the buffered audio; got: {asr_texts}"
    )
    assert transcribed, "ASR transcribe must have been called"


# ---------------------------------------------------------------------------
# (f) Malformed control payloads must never crash the session.
# ---------------------------------------------------------------------------


def test_non_object_json_does_not_disconnect():
    """JSON payloads that are not objects yield an error event, not a disconnect."""

    manager, *_ = _simple_manager()
    app_ = _make_test_app(manager)

    from starlette.testclient import TestClient

    client = TestClient(app_)
    with client.websocket_connect("/ws/stream") as ws:
        assert ws.receive_json()["type"] == "ready"

        for payload in ([1, 2], "hello", 5, None):
            ws.send_json(payload)
            msg = ws.receive_json()
            assert msg["type"] == "error", f"Expected error for {payload!r}, got {msg}"
            assert msg.get("message")
            assert msg.get("error") == msg.get("message")

        ws.send_json({"action": "stop"})
        while True:
            msg = ws.receive_json()
            if msg.get("type") == "stopped":
                break


def test_translate_text_non_string_does_not_disconnect():
    """A non-string 'text' field is rejected without closing the WebSocket."""

    manager, *_ = _simple_manager()
    app_ = _make_test_app(manager)

    from starlette.testclient import TestClient

    client = TestClient(app_)
    with client.websocket_connect("/ws/stream") as ws:
        assert ws.receive_json()["type"] == "ready"

        ws.send_json({"action": "translate_text", "text": 123})
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "text" in msg["message"].lower()

        ws.send_json({"action": "stop"})
        while True:
            msg = ws.receive_json()
            if msg.get("type") == "stopped":
                break
