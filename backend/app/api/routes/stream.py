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

from app.core.vram_monitor import vram_tracker
from app.models.manager import get_model_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Streaming"])


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


async def stream_translation_and_tts(
    websocket: WebSocket,
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

    await websocket.send_json({"type": "trans_start", "event": "trans_start"})
    full_tokens: list[str] = []
    token_queue: asyncio.Queue[str | None] = asyncio.Queue()

    def _producer():
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
    tts_result = await loop.run_in_executor(
        None,
        lambda: tts_adapter.synthesize(text=translated_text, language=target_lang),
    )
    audio_np, sample_rate = tts_result[0], tts_result[1]
    tts_ms = (time.monotonic() - t2) * 1000
    vram_tracker.record_warm_inference("tts", tts_ms)

    audio_b64 = _encode_audio_b64(audio_np, sample_rate)
    await websocket.send_json({
        "type": "tts_audio",
        "event": "tts_audio",
        "audio_b64": audio_b64,
        "format": "wav",
        "sample_rate": sample_rate,
        "elapsed_ms": round(tts_ms, 2),
        "is_final": True,
    })


async def process_utterance(
    websocket: WebSocket,
    pcm_bytes: bytes,
    config: dict[str, Any],
) -> None:
    """Run ASR -> Streaming Translation -> TTS for a completed utterance."""
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
        asr_res = await loop.run_in_executor(None, asr.transcribe, tmp_path)
        asr_ms = (time.monotonic() - t0) * 1000
        vram_tracker.record_warm_inference("phoasr", asr_ms)

        transcript = asr_res.get("text", "").strip()
        await websocket.send_json({
            "type": "asr_final",
            "event": "asr_final",
            "text": transcript,
            "elapsed_ms": round(asr_ms, 2),
        })

        if not transcript:
            return

        # ── Steps 2 & 3: Translation & Speech Synthesis ────────────────────
        await stream_translation_and_tts(websocket, transcript, config)

    finally:
        Path(tmp_path).unlink(missing_ok=True)



@router.websocket("/ws/stream")
async def websocket_stream_endpoint(websocket: WebSocket) -> None:
    """Full-duplex real-time streaming endpoint."""
    await websocket.accept()
    logger.info("Client connected to /ws/stream")

    config: dict[str, Any] = {
        "source_lang": "vi",
        "target_lang": "en",
        "context": "Casual",
        "clone_voice": False,
    }

    audio_buffer = bytearray()
    in_speech = False
    silence_samples = 0
    speech_samples = 0
    silence_threshold_samples = int(16000 * VADSettings.silence_duration_s)

    try:
        # Acknowledge connection
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
                    await websocket.send_json({
                        "type": "config_updated",
                        "event": "config_updated",
                        "config": config,
                    })

                elif action == "flush":
                    if len(audio_buffer) >= VADSettings.min_speech_bytes:
                        await process_utterance(websocket, bytes(audio_buffer), config)
                        audio_buffer.clear()
                        in_speech = False
                        silence_samples = 0
                        speech_samples = 0

                elif action == "translate_text":
                    # Direct text streaming test / trigger
                    input_text = payload.get("text", "").strip()
                    if input_text:
                        await websocket.send_json({
                            "type": "asr_final",
                            "event": "asr_final",
                            "text": input_text,
                            "elapsed_ms": 0.0,
                        })
                        await stream_translation_and_tts(websocket, input_text, config)

                elif action == "stop":
                    audio_buffer.clear()
                    await websocket.send_json({"type": "stopped", "event": "stopped"})
                    break

            # ── 2. Handle Binary Audio Frames (16kHz 16-bit PCM) ───────────
            elif message.get("bytes"):
                raw_chunk: bytes = message["bytes"]
                audio_buffer.extend(raw_chunk)

                # Compute frame RMS for VAD
                samples = np.frombuffer(raw_chunk, dtype=np.int16).astype(np.float32) / 32768.0
                rms = float(np.sqrt(np.mean(samples ** 2))) if len(samples) > 0 else 0.0

                if rms > VADSettings.rms_threshold:
                    if not in_speech:
                        in_speech = True
                        silence_samples = 0
                        speech_samples = len(samples)
                        # Emit interim speech activity event
                        await websocket.send_json({
                            "type": "asr_interim",
                            "event": "asr_interim",
                            "text": "...",
                            "is_speaking": True,
                        })
                    else:
                        silence_samples = 0
                        speech_samples += len(samples)
                else:
                    if in_speech:
                        silence_samples += len(samples)
                        # Check pause boundary (>450ms silence after speech)
                        if (
                            silence_samples >= silence_threshold_samples
                            and speech_samples >= VADSettings.min_speech_samples
                        ):
                            await process_utterance(websocket, bytes(audio_buffer), config)
                            audio_buffer.clear()
                            in_speech = False
                            silence_samples = 0
                            speech_samples = 0

    except WebSocketDisconnect:
        logger.info("Client disconnected from /ws/stream")
    except Exception:
        logger.exception("Error in /ws/stream")
