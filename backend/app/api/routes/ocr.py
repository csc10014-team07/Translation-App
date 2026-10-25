"""OCR route — POST /api/ocr."""
from __future__ import annotations

import asyncio
import base64
import logging
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.deps import dep_model_manager
from app.core.vram_monitor import vram_tracker
from app.models.manager import ModelManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ocr", tags=["OCR"])

_SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
_MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


class OCRResponse(BaseModel):
    """Response for the OCR endpoint."""

    vietnamese_text: str


@router.post(
    "",
    response_model=OCRResponse,
    summary="Extract Vietnamese text from an image",
    description=(
        "Upload an image file (PNG, JPEG, BMP, TIFF, WebP) and receive the "
        "Vietnamese text extracted via Gemma 3 4B OCR."
    ),
)
async def ocr_image(
    image: UploadFile,
    manager: ModelManager = Depends(dep_model_manager),
) -> OCRResponse:
    """Run OCR on an uploaded image and return extracted Vietnamese text."""

    # ── Validate extension ─────────────────────────────────────────────────
    suffix = Path(image.filename or "image.png").suffix.lower()
    if suffix not in _SUPPORTED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported image format '{suffix}'. "
                f"Supported: {sorted(_SUPPORTED_IMAGE_EXTENSIONS)}"
            ),
        )

    # ── Read and base64-encode ─────────────────────────────────────────────
    chunks: list[bytes] = []
    total = 0
    while chunk := await image.read(65_536):
        total += len(chunk)
        if total > _MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image file exceeds 20 MB limit.",
            )
        chunks.append(chunk)
    image_bytes = b"".join(chunks)
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    # ── Run OCR via Gemma ──────────────────────────────────────────────────
    try:
        translation = await manager.get_translation()
        t0 = time.monotonic()
        vietnamese_text: str = await asyncio.get_event_loop().run_in_executor(
            None, translation.ocr_to_vietnamese, image_b64
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        vram_tracker.record_warm_inference("gemma", elapsed_ms)

        return OCRResponse(vietnamese_text=vietnamese_text)

    except Exception as exc:
        logger.exception("OCR failed: %s", exc)
        raise HTTPException(status_code=500, detail="OCR failed. See server logs.") from exc
