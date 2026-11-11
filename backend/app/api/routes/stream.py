"""WebSocket Streaming route — WS /ws/stream.

Provides real-time full-duplex speech-to-speech translation:
1. Ingests raw 16kHz PCM audio frames over WebSocket.
2. VAD buffers and detects speech pause boundaries.
3. Transcribes Vietnamese utterances with PhoASR (`asr_final`).
4. Streams translation tokens live with TranslateGemma (`trans_delta`, `trans_final`).
5. Synthesizes translated speech with Pocket TTS / Edge-TTS (`tts_audio`).
"""
from __future__ import annotations

import asyncio
import base64
import collections
import io
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.vram_monitor import vram_tracker
from app.models.manager import get_model_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Streaming"])

# Sentinel object used to signal the worker to stop.
_STOP = object()

# 16kHz, 16-bit PCM: 2 bytes per sample.
_BYTES_PER_SAMPLE: int = 2
_SAMPLE_RATE: int = 16000


def _encode_audio_b64(audio_array: np.ndarray, sample_rate: int) -> str:
    """Encode float32 audio numpy array to base64 WAV."""
    buf = io.BytesIO()
    sf.write(buf, audio_array, sample_rate, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


class VADSettings:
    """Voice Activity Detection configuration."""
    min_speech_bytes: int = 3200  # 100ms at 16kHz 16-bit
    rms_threshold: float = 0.012
    silence_duration_s: float = 0.45
    min_speech_samples: int = 4800  # 300ms speech minimum


# ---------------------------------------------------------------------------
# Worker: processes queued utterances so the receive loop is never blocked.
# ---------------------------------------------------------------------------

async def _utterance_worker(
    queue: asyncio.Queue[Any],
    websocket: WebSocket,
    ws_lock: asyncio.Lock,
    config_ref: list[dict[str, Any]],
) -> None:
    """Drain the job queue and process utterances in order.

    Jobs are either:
      ("utterance", pcm_bytes)  — run ASR → translation → TTS
      ("text",      text_str)   — run translation → TTS only (translate_text action)
      _STOP sentinel            — exit the loop
    """
    while True:
        job = await queue.get()
        try:
            if job is _STOP:
                return

            kind, payload = job
            config = config_ref[0]

            if kind == "utterance":
                pcm_bytes: bytes = payload
                try:
                    await _process_utterance(websocket, ws_lock, pcm_bytes, config)
                except Exception as exc:
                    logger.exception("Worker: utterance processing failed")
                    async with ws_lock:
                        await websocket.send_json({
                            "type": "error",
                            "event": "error",
                            "message": str(exc),
                        })

            elif kind == "text":
                text: str = payload
                try:
                    async with ws_lock:
                        await websocket.send_json({
                            "type": "asr_final",
                            "event": "asr_final",
                            "text": text,
                            "elapsed_ms": 0.0,
                        })
                    await _stream_translation_and_tts(websocket, ws_lock, text, config)
                except Exception as exc:
                    logger.exception("Worker: text job failed")
                    async with ws_lock:
                        await websocket.send_json({
                            "type": "error",
                            "event": "error",
                            "message": str(exc),
                        })

        finally:
            queue.task_done()


# ---------------------------------------------------------------------------
# Core pipeline helpers
# ---------------------------------------------------------------------------

async def _process_utterance(
    websocket: WebSocket,
    ws_lock: asyncio.Lock,
    pcm_bytes: bytes,
    config: dict[str, Any],
) -> None:
    """Run ASR → Streaming Translation → TTS for one completed utterance."""
    if len(pcm_bytes) < VADSettings.min_speech_bytes:
        return

    manager = get_model_manager()
    loop = asyncio.get_event_loop()

    # Convert raw int16 PCM to float32 WAV temp file
    pcm_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
    pcm_float32 = pcm_int16.astype(np.float32) / 32768.0

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        sf.write(tmp_path, pcm_float32, 16000, subtype="PCM_16")

        # ── Step 1: ASR ────────────────────────────────────────────────────
        t0 = time.monotonic()
        asr = await manager.get_asr()
        try:
            asr_res = await loop.run_in_executor(None, asr.transcribe, tmp_path)
        except ValueError as exc:
            # Enforce audio-quality / duration guard from the ASR adapter.
            logger.warning("ASR rejected utterance: %s", exc)
            async with ws_lock:
                await websocket.send_json({
                    "type": "error",
                    "event": "error",
                    "message": str(exc),
                })
            return

        asr_ms = (time.monotonic() - t0) * 1000
        vram_tracker.record_warm_inference("phoasr", asr_ms)

        transcript = asr_res.get("text", "").strip()
        async with ws_lock:
            await websocket.send_json({
                "type": "asr_final",
                "event": "asr_final",
                "text": transcript,
                "elapsed_ms": round(asr_ms, 2),
            })

        if not transcript:
            return

        # ── Steps 2 & 3: Translation & Speech Synthesis ────────────────────
        await _stream_translation_and_tts(websocket, ws_lock, transcript, config)

    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def _stream_translation_and_tts(
    websocket: WebSocket,
    ws_lock: asyncio.Lock,
    text: str,
    config: dict[str, Any],
) -> None:
    """Stream translation tokens progressively and synthesize translated speech audio."""
    manager = get_model_manager()
    loop = asyncio.get_event_loop()
    target_lang = config.get("target_lang", "en")
    source_lang = config.get("source_lang", "vi")
    context = config.get("context", "")

    # ── Step 1: Token Streaming Translation ────────────────────────────────
    t1 = time.monotonic()
    translation_adapter = await manager.get_translation()

    async with ws_lock:
        await websocket.send_json({"type": "trans_start", "event": "trans_start"})
    full_tokens: list[str] = []
    token_queue: asyncio.Queue[str | None] = asyncio.Queue()

    def _producer() -> None:
        try:
            for tok in translation_adapter.translate_stream(
                text=text,
                target_language=target_lang,
                source_language=source_lang,
                context=context,
            ):
                loop.call_soon_threadsafe(token_queue.put_nowait, tok)
        except Exception as err:
            logger.warning("Error in translation generator: %s", err)
        finally:
            loop.call_soon_threadsafe(token_queue.put_nowait, None)

    producer_future = loop.run_in_executor(None, _producer)

    while True:
        tok = await token_queue.get()
        if tok is None:
            break
        full_tokens.append(tok)
        async with ws_lock:
            await websocket.send_json({
                "type": "trans_delta",
                "event": "trans_delta",
                "delta": tok,
                "token": tok,
            })

    await producer_future

    translated_text = "".join(full_tokens).strip()
    trans_ms = (time.monotonic() - t1) * 1000
    vram_tracker.record_warm_inference("gemma", trans_ms)

    async with ws_lock:
        await websocket.send_json({
            "type": "trans_final",
            "event": "trans_final",
            "text": translated_text,
            "elapsed_ms": round(trans_ms, 2),
        })

    if not translated_text:
        return

    # ── Step 2: Speech Synthesis ───────────────────────────────────────────
    t2 = time.monotonic()
    tts_adapter = await manager.get_tts()
    tts_result = await tts_adapter.synthesize(text=translated_text, language=target_lang)
    audio_np, sample_rate = tts_result[0], tts_result[1]
    tts_ms = (time.monotonic() - t2) * 1000
    vram_tracker.record_warm_inference("tts", tts_ms)

    audio_b64 = _encode_audio_b64(audio_np, sample_rate)
    async with ws_lock:
        await websocket.send_json({
            "type": "tts_audio",
            "event": "tts_audio",
            "audio_b64": audio_b64,
            "format": "wav",
            "sample_rate": sample_rate,
            "elapsed_ms": round(tts_ms, 2),
            "is_final": True,
        })


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@router.websocket("/ws/stream")
async def websocket_stream_endpoint(websocket: WebSocket) -> None:
    """Full-duplex real-time streaming endpoint."""
    if settings.API_KEY:
        api_key = websocket.query_params.get("api_key") or websocket.headers.get("x-api-key")
        if api_key != settings.API_KEY:
            await websocket.close(code=4001, reason="Unauthorized")
            return

    await websocket.accept()
    logger.info("Client connected to /ws/stream")

    # Mutable config reference shared with the worker (list-wrapping for mutation).
    config: dict[str, Any] = {
        "source_lang": "vi",
        "target_lang": "en",
        "context": "Casual",
        "clone_voice": False,
    }
    config_ref: list[dict[str, Any]] = [config]

    # Per-utterance cap in bytes: MAX_AUDIO_DURATION_S * 16000 samples/s * 2 bytes/sample
    _max_utterance_bytes: int = int(
        settings.MAX_AUDIO_DURATION_S * _SAMPLE_RATE * _BYTES_PER_SAMPLE
    )

    # Ring buffer for pre-speech audio: last 300 ms = 4800 samples = 9600 bytes
    _ring_bytes: int = VADSettings.min_speech_samples * _BYTES_PER_SAMPLE
    ring_buffer: collections.deque[bytes] = collections.deque()
    ring_buffer_size: int = 0  # total bytes currently in ring_buffer

    # Active speech state
    audio_buffer = bytearray()
    in_speech = False
    silence_samples = 0
    speech_samples = 0
    silence_threshold_samples = int(_SAMPLE_RATE * VADSettings.silence_duration_s)

    # Odd-length byte carry-over
    pending_byte: bytes = b""

    # Job queue and worker task
    job_queue: asyncio.Queue[Any] = asyncio.Queue()
    ws_lock = asyncio.Lock()

    worker_task = asyncio.ensure_future(
        _utterance_worker(job_queue, websocket, ws_lock, config_ref)
    )

    try:
        # Acknowledge connection
        async with ws_lock:
            await websocket.send_json({
                "type": "ready",
                "event": "ready",
                "status": "listening",
                "config": config,
            })

        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            # ── 1. Handle JSON Control Messages ────────────────────────────
            if "text" in message:
                try:
                    payload = json.loads(message["text"])
                except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                    logger.debug("Failed to parse JSON message: %s", exc)
                    continue

                action = payload.get("action", "")

                if action == "start":
                    config["source_lang"] = payload.get("source_lang", config["source_lang"])
                    config["target_lang"] = payload.get("target_lang", config["target_lang"])
                    preset = payload.get("context_preset", "")
                    custom = payload.get("custom_context", "")
                    config["context"] = f"{preset} {custom}".strip()
                    config["clone_voice"] = payload.get("clone_voice", False)
                    async with ws_lock:
                        await websocket.send_json({
                            "type": "config_updated",
                            "event": "config_updated",
                            "config": config,
                        })

                elif action == "flush":
                    # Enqueue only if we have enough speech; never process silence.
                    if in_speech and speech_samples >= VADSettings.min_speech_samples:
                        job_queue.put_nowait(("utterance", bytes(audio_buffer)))
                    audio_buffer.clear()
                    ring_buffer.clear()
                    ring_buffer_size = 0
                    in_speech = False
                    silence_samples = 0
                    speech_samples = 0

                elif action == "translate_text":
                    # Direct text streaming test / trigger — enqueue as text job.
                    input_text = payload.get("text", "").strip()
                    if input_text:
                        job_queue.put_nowait(("text", input_text))

                elif action == "stop":
                    # If mid-utterance with enough speech, enqueue it first.
                    if in_speech and speech_samples >= VADSettings.min_speech_samples:
                        job_queue.put_nowait(("utterance", bytes(audio_buffer)))
                    audio_buffer.clear()
                    ring_buffer.clear()
                    ring_buffer_size = 0
                    in_speech = False
                    silence_samples = 0
                    speech_samples = 0

                    # Signal the worker to stop after finishing queued jobs.
                    job_queue.put_nowait(_STOP)
                    # Wait for all queued jobs (including the utterance) to drain.
                    await job_queue.join()
                    async with ws_lock:
                        await websocket.send_json({"type": "stopped", "event": "stopped"})
                    break

            # ── 2. Handle Binary Audio Frames (16kHz 16-bit PCM) ───────────
            elif message.get("bytes"):
                raw_chunk: bytes = message["bytes"]

                # ── 2a. Odd-length fix: carry one byte across frames ────────
                raw_chunk = pending_byte + raw_chunk
                if len(raw_chunk) % 2 != 0:
                    pending_byte = raw_chunk[-1:]
                    raw_chunk = raw_chunk[:-1]
                else:
                    pending_byte = b""

                if len(raw_chunk) == 0:
                    continue

                # ── 2b. Decode samples for VAD RMS ─────────────────────────
                samples = np.frombuffer(raw_chunk, dtype=np.int16).astype(np.float32) / 32768.0
                rms = float(np.sqrt(np.mean(samples ** 2))) if len(samples) > 0 else 0.0

                if rms > VADSettings.rms_threshold:
                    # ── Speech active ───────────────────────────────────────
                    if not in_speech:
                        # Start a fresh utterance from the ring buffer content.
                        in_speech = True
                        silence_samples = 0
                        speech_samples = len(samples)
                        # Seed the audio buffer with pre-speech ring buffer.
                        audio_buffer.clear()
                        for chunk in ring_buffer:
                            audio_buffer.extend(chunk)
                        ring_buffer.clear()
                        ring_buffer_size = 0
                        audio_buffer.extend(raw_chunk)
                        async with ws_lock:
                            await websocket.send_json({
                                "type": "asr_interim",
                                "event": "asr_interim",
                                "text": "...",
                                "is_speaking": True,
                            })
                    else:
                        silence_samples = 0
                        speech_samples += len(samples)
                        audio_buffer.extend(raw_chunk)

                    # ── 2c. Utterance cap ───────────────────────────────────
                    if len(audio_buffer) >= _max_utterance_bytes:
                        job_queue.put_nowait(("utterance", bytes(audio_buffer)))
                        audio_buffer.clear()
                        in_speech = False
                        silence_samples = 0
                        speech_samples = 0
                        ring_buffer.clear()
                        ring_buffer_size = 0

                else:
                    if in_speech:
                        # Silence while in speech — accumulate for pause detection.
                        audio_buffer.extend(raw_chunk)
                        silence_samples += len(samples)
                        # Check pause boundary (>450ms silence after speech)
                        if (
                            silence_samples >= silence_threshold_samples
                            and speech_samples >= VADSettings.min_speech_samples
                        ):
                            job_queue.put_nowait(("utterance", bytes(audio_buffer)))
                            audio_buffer.clear()
                            in_speech = False
                            silence_samples = 0
                            speech_samples = 0
                            ring_buffer.clear()
                            ring_buffer_size = 0
                    else:
                        # Not in speech — maintain pre-speech ring buffer (last 300 ms).
                        ring_buffer.append(raw_chunk)
                        ring_buffer_size += len(raw_chunk)
                        while ring_buffer_size > _ring_bytes and ring_buffer:
                            evicted = ring_buffer.popleft()
                            ring_buffer_size -= len(evicted)

    except WebSocketDisconnect:
        logger.info("Client disconnected from /ws/stream")
    except Exception:
        logger.exception("Error in /ws/stream")
    finally:
        # Signal the worker and wait for it to exit cleanly.
        job_queue.put_nowait(_STOP)
        try:
            await asyncio.wait_for(job_queue.join(), timeout=0.5)
        except asyncio.TimeoutError:
            pass
        worker_task.cancel()
        try:
            await worker_task
        except (asyncio.CancelledError, Exception):
            pass
