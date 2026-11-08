"""OCR route — POST /api/ocr (Two-Stage Multimodal Image Translation)."""
from __future__ import annotations

import asyncio
import io
import logging
import time
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from PIL import Image

from app.api.deps import dep_model_manager
from app.core.vram_monitor import vram_tracker
from app.models.manager import ModelManager
from app.schemas.ocr import OCRResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ocr", tags=["OCR"])

_SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
_MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post(
    "",
    response_model=OCRResponse,
    summary="Extract and translate text from an image",
    description=(
        "Upload an image file (PNG, JPEG, WebP, BMP, TIFF) to extract text regions "
        "via RapidOCR on CPU (0MB VRAM), automatically detect the language, and "
        "produce a context-aware translation via TranslateGemma."
    ),
)
async def ocr_image(
    image: UploadFile = File(...),  # noqa: B008
    target_language: str | None = Form(None),
    source_language: str | None = Form(None),
    context_preset: str = Form("General"),
    custom_context: str = Form(""),
    manager: ModelManager = Depends(dep_model_manager),  # noqa: B008
) -> OCRResponse:
    """Run two-stage image translation: RapidOCR extraction + TranslateGemma context translation."""
    t0 = time.monotonic()

    # ── 1. Validate file extension ─────────────────────────────────────────
    suffix = Path(image.filename or "image.png").suffix.lower()
    if suffix not in _SUPPORTED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported image format '{suffix}'. "
                f"Supported: {sorted(_SUPPORTED_IMAGE_EXTENSIONS)}"
            ),
        )

    # ── 2. Read bytes and guard size ───────────────────────────────────────
    chunks: list[bytes] = []
    total = 0
    while chunk := await image.read(65_536):
        if total + len(chunk) > _MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image file exceeds 20 MB limit.",
            )
        total += len(chunk)
        chunks.append(chunk)
    image_bytes = b"".join(chunks)

    if len(image_bytes) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image file is empty or too small.",
        )

    # ── 3. Validate image integrity ────────────────────────────────────────
    try:
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            pil_img.verify()
    except Exception as exc:
        logger.warning("Invalid or corrupted image uploaded: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid or corrupted image: {exc}",
        ) from exc

    # ── 4. Stage 1: RapidOCR extraction on CPU ─────────────────────────────
    try:
        ocr = await manager.get_ocr()
        extracted_text, detected_lang, boxes = await asyncio.get_event_loop().run_in_executor(
            None, ocr.extract_text, image_bytes
        )
    except Exception as exc:
        logger.exception("RapidOCR extraction failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR extraction failed: {exc}",
        ) from exc

    # ── 5. Stage 2: Context-Aware Translation ──────────────────────────────
    resolved_target = (target_language or "").strip()
    if not resolved_target:
        # Auto-resolve target language based on detected source language
        resolved_target = "en" if detected_lang.lower() == "vi" else "vi"
    
    # Use explicit source_language if provided, otherwise use detected language
    resolved_source = (source_language or "").strip() or detected_lang

    translated_text = ""
    if extracted_text.strip():
        try:
            translation = await manager.get_translation()
            raw_res = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: translation.translate(
                    text=extracted_text,
                    source_language=resolved_source,
                    target_language=resolved_target,
                    context_preset=context_preset,
                    custom_context=custom_context,
                ),
            )
            translated_text = raw_res[0] if isinstance(raw_res, tuple) else raw_res
        except Exception as exc:  # noqa: BLE001
            logger.warning("Stage 2 translation failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Translation service unavailable: {exc}",
            ) from exc

    # Determine backward-compatible vietnamese_text for mobile client
    if detected_lang.lower() == "vi":
        vietnamese_text = extracted_text
    elif resolved_target.lower() == "vi":
        vietnamese_text = translated_text
    else:
        vietnamese_text = extracted_text or translated_text

    elapsed_ms = (time.monotonic() - t0) * 1000
    vram_tracker.record_warm_inference("rapidocr", elapsed_ms)

    return OCRResponse(
        extracted_text=extracted_text,
        detected_language=detected_lang or "en",
        target_language=resolved_target,
        translated_text=translated_text,
        boxes=boxes,
        elapsed_ms=round(elapsed_ms, 2),
        vietnamese_text=vietnamese_text,
    )
