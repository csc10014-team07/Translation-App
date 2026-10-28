"""TTS route — POST /api/tts."""
from __future__ import annotations

import asyncio
import base64
import io
import logging
import tempfile
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

import aiofiles
from app.api.deps import dep_model_manager
from app.core.vram_monitor import vram_tracker
from app.models.manager import ModelManager
from app.schemas.tts import TTSResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tts", tags=["TTS"])

_SUPPORTED_REF_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


def _audio_to_wav_base64(audio_array: np.ndarray, sample_rate: int) -> str:
    """Encode a float32 NumPy audio array as a base64 WAV string."""
    buf = io.BytesIO()
    sf.write(buf, audio_array, sample_rate, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


@router.post(
    "",
    response_model=TTSResponse,
    summary="Synthesise speech (non-Vietnamese only)",
    description=(
        "Convert text to speech using Pocket TTS. "
        "Vietnamese is **not** supported and will return HTTP 400. "
        "An optional reference audio clip can be supplied for voice cloning."
    ),
)
async def synthesise_speech(
    text: str = Form(..., description="Text to synthesise."),
    language: str = Form(..., description="Spoken language (e.g. 'English', 'French')."),
    reference_audio: UploadFile | None = None,
    reference_text: str | None = Form(default=None, description="Transcript of the reference audio."),
    manager: ModelManager = Depends(dep_model_manager),
) -> TTSResponse:
    """Synthesise non-Vietnamese speech, optionally with voice cloning."""
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Text must not be empty.",
        )

    ref_audio_path: str | None = None

    try:
        # ── Save reference audio if provided ───────────────────────────────
        if reference_audio is not None:
            ref_suffix = Path(reference_audio.filename or "ref.wav").suffix.lower()
            if ref_suffix not in _SUPPORTED_REF_AUDIO_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Unsupported reference audio format '{ref_suffix}'.",
                )
            with tempfile.NamedTemporaryFile(suffix=ref_suffix, delete=False) as tmp:
                ref_audio_path = tmp.name
            ref_bytes = await reference_audio.read()
            async with aiofiles.open(ref_audio_path, "wb") as f:
                await f.write(ref_bytes)

        # ── Run TTS ────────────────────────────────────────────────────────
        tts = await manager.get_tts()
        t0 = time.monotonic()
        audio_array, sample_rate = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: tts.synthesize(
                text=text,
                language=language,
                reference_audio_path=ref_audio_path,
                reference_text=reference_text,
            ),
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        vram_tracker.record_warm_inference("tts", elapsed_ms)

        # ── Encode as base64 WAV ───────────────────────────────────────────
        audio_b64 = _audio_to_wav_base64(audio_array, sample_rate)

        return TTSResponse(
            audio_base64=audio_b64,
            sample_rate=sample_rate,
            format="wav",
        )

    except HTTPException:
        raise
    except ValueError as exc:
        # Catches the "Vietnamese not supported" guard inside TTSAdapter
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.exception("TTS synthesis failed: %s", exc)
        raise HTTPException(
            status_code=500, detail="TTS synthesis failed. See server logs."
        ) from exc
    finally:
        if ref_audio_path:
            Path(ref_audio_path).unlink(missing_ok=True)
