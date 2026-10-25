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
from app.core.config import settings
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
        total += len(chunk)
        if total > _MAX_AUDIO_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Audio file exceeds 100 MB limit.",
            )
        chunks.append(chunk)
    raw_bytes = b"".join(chunks)

    # ── Save to a temp file ────────────────────────────────────────────────
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name

    try:
        async with aiofiles.open(tmp_path, "wb") as f:
            await f.write(raw_bytes)

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
            word_timestamps=result.get("word_timestamps") or None,
        )

    except FileNotFoundError as exc:
        logger.error("Temp audio file not found: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error during ASR.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error during ASR: %s", exc)
        raise HTTPException(status_code=500, detail="ASR failed. See server logs.") from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)
