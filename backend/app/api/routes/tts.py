"""TTS route — POST /api/tts."""
from __future__ import annotations

import asyncio
import base64
import io
import logging
import tempfile
import time
from pathlib import Path

import aiofiles
import numpy as np
import soundfile as sf
from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status

from app.api.deps import dep_model_manager
from app.core.vram_monitor import vram_tracker
from app.models.manager import ModelManager
from app.schemas.tts import TTSResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tts", tags=["TTS"])

_VIETNAMESE_LANG_CODES = {"vi", "vietnamese", "vie"}
_SUPPORTED_REF_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


def _is_vietnamese(language: str) -> bool:
    return language.strip().lower() in _VIETNAMESE_LANG_CODES


def _audio_to_wav_base64(audio_array: np.ndarray, sample_rate: int) -> str:
    """Encode a float32 NumPy audio array as a base64 WAV string."""
    buf = io.BytesIO()
    sf.write(buf, audio_array, sample_rate, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


@router.post(
    "",
    response_model=TTSResponse,
    summary="Synthesise speech with Hybrid TTS (Edge-TTS + Pocket TTS)",
    description=(
        "Synthesise speech from text. When translating to an international language with reference audio provided, "
        "Pocket TTS on CPU clones the user's voice timbre (0MB GPU VRAM). When translating to Vietnamese or when "
        "reference audio is omitted, Edge-TTS generates studio-quality native speech."
    ),
)
async def synthesise_speech(
    request: Request,
    text: str = Form(default=""),
    language: str | None = Form(default=None),
    target_language: str | None = Form(default=None),
    voice_style: str | None = Form(default=None),
    reference_audio: UploadFile | None = None,
    reference_text: str | None = Form(default=None),
    manager: ModelManager = Depends(dep_model_manager),  # noqa: B008
) -> TTSResponse:
    """Synthesise speech using Hybrid TTS (Pocket TTS voice cloning + Edge-TTS)."""
    # ── Check for JSON body if request is application/json ───────────────
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        try:
            body = await request.json()
            if isinstance(body, dict):
                text = body.get("text", text)
                language = body.get("language", language)
                target_language = body.get("target_language", target_language)
                voice_style = body.get("voice_style", voice_style)
                reference_text = body.get("reference_text", reference_text)
        except Exception as err:  # noqa: BLE001
            logger.debug("Failed to decode JSON payload: %s", err)

    # ── Validate text and language ─────────────────────────────────────────
    effective_text = (text or "").strip()
    if not effective_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Text to synthesise must not be empty.",
        )

    effective_language = (language or target_language or "").strip()
    if not effective_language:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Field 'language' or 'target_language' must be specified.",
        )

    ref_audio_path: str | None = None

    try:
        # ── Save reference audio if provided ───────────────────────────────
        if reference_audio is not None and reference_audio.filename:
            ref_suffix = Path(reference_audio.filename).suffix.lower()
            if ref_suffix not in _SUPPORTED_REF_AUDIO_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Unsupported reference audio format '{ref_suffix}'. Allowed formats: {_SUPPORTED_REF_AUDIO_EXTENSIONS}",
                )
            with tempfile.NamedTemporaryFile(suffix=ref_suffix, delete=False) as tmp:
                ref_audio_path = tmp.name
            ref_bytes = await reference_audio.read()
            async with aiofiles.open(ref_audio_path, "wb") as f:
                await f.write(ref_bytes)

        # ── Run Hybrid TTS ────────────────────────────────────────────────
        tts = await manager.get_tts()
        t0 = time.monotonic()
        tts_result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: tts.synthesize(
                text=effective_text,
                language=effective_language,
                reference_audio_path=ref_audio_path,
                reference_text=reference_text,
                voice_style=voice_style,
            ),
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        vram_tracker.record_warm_inference("tts", elapsed_ms)

        audio_array, sample_rate = tts_result[0], tts_result[1]
        engine_used = getattr(tts_result, "engine", "edge_tts")

        # ── Encode as base64 WAV ───────────────────────────────────────────
        audio_b64 = _audio_to_wav_base64(audio_array, sample_rate)

        return TTSResponse(
            audio_base64=audio_b64,
            sample_rate=sample_rate,
            format="wav",
            engine=engine_used,
            elapsed_ms=round(elapsed_ms, 2),
        )

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.exception("TTS synthesis failed")
        raise HTTPException(
            status_code=500, detail=f"TTS synthesis failed: {exc}"
        ) from exc
    finally:
        if ref_audio_path:
            try:
                Path(ref_audio_path).unlink(missing_ok=True)
            except OSError:
                pass
