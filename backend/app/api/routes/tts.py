"""TTS route — POST /api/tts."""
from __future__ import annotations

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
from pydantic import ValidationError

from app.api.deps import dep_model_manager
from app.core.vram_monitor import vram_tracker
from app.models.manager import ModelManager
from app.schemas.tts import TTSRequest, TTSResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tts", tags=["TTS"])

_VIETNAMESE_LANG_CODES = {"vi", "vietnamese", "vie"}
_SUPPORTED_REF_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
_MAX_REF_AUDIO_BYTES = 20 * 1024 * 1024  # 20 MB


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
    manager: ModelManager = Depends(dep_model_manager),  # noqa: B008
) -> TTSResponse:
    """Synthesise speech using Hybrid TTS (Pocket TTS voice cloning + Edge-TTS)."""
    # ── Check for JSON body if request is application/json ───────────────
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        try:
            body = await request.json()
        except Exception as err:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON body",
            ) from err
        if not isinstance(body, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JSON body must be an object",
            )
        try:
            parsed = TTSRequest.model_validate(body)
        except ValidationError as err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=err.errors(),
            ) from err
        text = parsed.text
        language = parsed.language
        target_language = parsed.target_language
        voice_style = parsed.voice_style

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
            # Read with size guard (20 MB cap)
            ref_chunks: list[bytes] = []
            ref_total = 0
            while chunk := await reference_audio.read(65_536):
                ref_total += len(chunk)
                if ref_total > _MAX_REF_AUDIO_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Reference audio exceeds 20 MB limit.",
                    )
                ref_chunks.append(chunk)
            ref_bytes = b"".join(ref_chunks)

            with tempfile.NamedTemporaryFile(suffix=ref_suffix, delete=False) as tmp:
                ref_audio_path = tmp.name
            async with aiofiles.open(ref_audio_path, "wb") as f:
                await f.write(ref_bytes)

        # ── Run Hybrid TTS ────────────────────────────────────────────────
        tts = await manager.get_tts()
        t0 = time.monotonic()
        try:
            tts_result = await tts.synthesize(
                text=effective_text,
                language=effective_language,
                reference_audio_path=ref_audio_path,
                voice_style=voice_style,
            )
        except ValueError as exc:
            # Language or engine not supported
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except RuntimeError as exc:
            # Edge-TTS disabled or synthesis failure
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        elapsed_ms = (time.monotonic() - t0) * 1000
        vram_tracker.record_warm_inference("tts", elapsed_ms)

        audio_array = tts_result.audio
        sample_rate = tts_result.sample_rate
        engine_used = tts_result.engine
        voice_note = tts_result.voice_note if hasattr(tts_result, "voice_note") else None

        # ── Encode as base64 WAV ───────────────────────────────────────────
        audio_b64 = _audio_to_wav_base64(audio_array, sample_rate)

        return TTSResponse(
            audio_base64=audio_b64,
            sample_rate=sample_rate,
            format="wav",
            engine=engine_used,
            voice_note=voice_note,
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
