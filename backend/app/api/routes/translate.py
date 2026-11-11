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
    summary="Translate text between supported languages",
    description=(
        "Translate text from *source_language* (default: Vietnamese) to *target_language* "
        "using Gemma 3 4B. An optional *context* field can be supplied to guide style and tone."
    ),
)
async def translate_text(
    body: TranslateRequest,
    manager: ModelManager = Depends(dep_model_manager),
) -> TranslateResponse:
    """Translate source text → target language, optionally guided by context."""

    if not body.text or not body.text.strip():
        raise HTTPException(status_code=422, detail="'text' must not be empty.")
    if not body.target_language or not body.target_language.strip():
        raise HTTPException(status_code=422, detail="'target_language' must not be empty.")

    source_lang = (body.source_language or "vi").strip()
    target_lang = body.target_language.strip()

    try:
        translation_adapter = await manager.get_translation()
        t0 = time.monotonic()
        translated, engine = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: translation_adapter.translate_with_engine(
                text=body.text.strip(),
                target_language=target_lang,
                source_language=source_lang,
                context=body.context or "",
                context_preset=body.context_preset or "",
                custom_context=body.custom_context or "",
            ),
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        vram_tracker.record_warm_inference("gemma", elapsed_ms)

        return TranslateResponse(
            translated_text=translated,
            source_language=source_lang,
            target_language=target_lang,
            engine_used=engine,
            elapsed_ms=round(elapsed_ms, 2),
        )

    except HTTPException:
        raise
    except RuntimeError as exc:
        logger.warning("Translation model not loaded or inference failed: %s", exc)
        raise HTTPException(status_code=503, detail="Translation service unavailable.") from exc
    except Exception as exc:
        logger.exception("Translation failed")
        raise HTTPException(status_code=500, detail="Translation failed. See server logs.") from exc

