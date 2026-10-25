"""Translation route — POST /api/translate."""
from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import dep_model_manager
from app.core.vram_monitor import vram_tracker
from app.models.manager import ModelManager
from app.schemas.translate import TranslateRequest, TranslateResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/translate", tags=["Translation"])


@router.post(
    "",
    response_model=TranslateResponse,
    summary="Translate Vietnamese text",
    description=(
        "Translate Vietnamese text to a target language using Gemma 3 4B. "
        "An optional *context* field can be supplied to guide style and tone."
    ),
)
async def translate_text(
    body: TranslateRequest,
    manager: ModelManager = Depends(dep_model_manager),
) -> TranslateResponse:
    """Translate Vietnamese → target language, optionally guided by context."""

    if not body.text.strip():
        raise HTTPException(status_code=422, detail="'text' must not be empty.")
    if not body.target_language.strip():
        raise HTTPException(status_code=422, detail="'target_language' must not be empty.")

    try:
        translation_adapter = await manager.get_translation()
        t0 = time.monotonic()
        translated: str = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: translation_adapter.translate(
                text=body.text,
                target_language=body.target_language,
                context=body.context,
            ),
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        vram_tracker.record_warm_inference("gemma", elapsed_ms)

        return TranslateResponse(
            translated_text=translated,
            source_language="vi",
            target_language=body.target_language,
        )

    except Exception as exc:
        logger.exception("Translation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Translation failed. See server logs.") from exc
