"""ASR route — POST /api/asr."""
from __future__ import annotations

import asyncio
import logging
import tempfile
import time
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.api.deps import dep_model_manager
from app.core.vram_monitor import vram_tracker
from app.models.manager import ModelManager
from app.schemas.asr import ASRResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/asr", tags=["ASR"])

_SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"}
_MAX_AUDIO_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB hard cap


@router.post(
    "",
    response_model=ASRResponse,
    summary="Transcribe Vietnamese audio",
    description=(
        "Upload an audio file (WAV, MP3, FLAC, OGG, M4A, WebM) and receive "
        "a Vietnamese transcription.  Audio is automatically resampled to 16 kHz."
    ),
)
async def transcribe_audio(
    audio: UploadFile,
    manager: ModelManager = Depends(dep_model_manager),
) -> ASRResponse:
    """Transcribe a Vietnamese audio file using PhoASR-Whisper-small."""

    # ── Validate file type ─────────────────────────────────────────────────
    suffix = Path(audio.filename or "audio.wav").suffix.lower()
    if suffix not in _SUPPORTED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported audio format '{suffix}'. "
                f"Supported: {sorted(_SUPPORTED_AUDIO_EXTENSIONS)}"
            ),
        )

    # ── Read upload (with size guard) ──────────────────────────────────────
    chunks: list[bytes] = []
    total = 0
    while chunk := await audio.read(65_536):
        if total + len(chunk) > _MAX_AUDIO_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Audio file exceeds 100 MB limit.",
            )
        total += len(chunk)
        chunks.append(chunk)
    raw_bytes = b"".join(chunks)
    if len(raw_bytes) < 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Audio file is empty or too short to be processed.",
        )

    # ── Save to a temp file ────────────────────────────────────────────────
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name

    try:
        async with aiofiles.open(tmp_path, "wb") as f:
            await f.write(raw_bytes)

        # ── Check duration before transcribing ────────────────────────────────
        from app.core.config import settings
        from app.models.asr_adapter import load_audio_file

        # Load audio to get duration (avoids wasted transcription if too long)
        try:
            audio_data, duration = await asyncio.get_event_loop().run_in_executor(
                None, load_audio_file, tmp_path, 16000
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        if duration > settings.MAX_AUDIO_DURATION_S:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Audio exceeds maximum duration of {settings.MAX_AUDIO_DURATION_S} seconds.",
            )

        # ── Run ASR ────────────────────────────────────────────────────────
        asr = await manager.get_asr()
        t0 = time.monotonic()
        result: dict = await asyncio.get_event_loop().run_in_executor(
            None, asr.transcribe, tmp_path
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        vram_tracker.record_warm_inference("phoasr", elapsed_ms)

        return ASRResponse(
            text=result["text"],
            language_detected=result.get("language", "vi"),
            duration=result.get("duration"),
            elapsed_ms=round(elapsed_ms, 2),
            word_timestamps=result.get("word_timestamps") or None,
        )

    except HTTPException:
        raise
    except FileNotFoundError as exc:
        logger.error("Temp audio file not found: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error during ASR.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        err_msg = str(exc)
        exc_type = type(exc).__name__
        if (
            "Format not recognised" in err_msg
            or "LibsndfileError" in exc_type
            or "SoundFileError" in exc_type
            or "AVError" in exc_type
            or "InvalidDataError" in exc_type
            or "corrupted" in err_msg.lower()
            or "Error opening" in err_msg
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unreadable audio content: {err_msg}",
            ) from exc
        logger.exception("Unexpected error during ASR")
        raise HTTPException(status_code=500, detail="ASR failed. See server logs.") from exc
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            pass

