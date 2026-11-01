"""Model Manager singleton orchestrating PhoASR, TranslateGemma, RapidOCR, and Hybrid TTS."""
from __future__ import annotations

import logging

from app.core.config import settings
from app.models.asr_adapter import ASRAdapter
from app.models.ocr_adapter import OCRAdapter, get_ocr_adapter
from app.models.translation_adapter import TranslationAdapter
from app.models.tts_adapter import TTSAdapter

logger = logging.getLogger(__name__)


class ModelManager:
    """Singleton model coordinator managing lifecycle, memory, and inference dispatch."""

    def __init__(self) -> None:
        self.device = settings.effective_device()
        self._asr: ASRAdapter | None = None
        self._translation: TranslationAdapter | None = None
        self._ocr: OCRAdapter | None = None
        self._tts: TTSAdapter | None = None
        self._is_started: bool = False

    async def startup(self) -> None:
        """Initialize core models at server boot."""
        if not self._is_started:
            logger.info("Initializing ModelManager on %s...", self.device)
            # Preload translation & OCR adapters lazily or eagerly
            self._translation = TranslationAdapter()
            self._ocr = get_ocr_adapter()
            self._tts = TTSAdapter()
            self._asr = ASRAdapter(device=self.device)
            self._is_started = True
            logger.info("ModelManager startup complete.")

    async def shutdown(self) -> None:
        """Unload models and release hardware memory."""
        logger.info("Shutting down ModelManager...")
        if self._asr is not None:
            self._asr.unload()
            self._asr = None
        self._translation = None
        self._ocr = None
        self._tts = None
        self._is_started = False
        logger.info("ModelManager shutdown complete.")

    async def get_asr(self) -> ASRAdapter:
        """Return the active ASR adapter."""
        if self._asr is None:
            self._asr = ASRAdapter(device=self.device)
        return self._asr

    async def get_translation(self) -> TranslationAdapter:
        """Return the active Translation adapter."""
        if self._translation is None:
            self._translation = TranslationAdapter()
        return self._translation

    async def get_ocr(self) -> OCRAdapter:
        """Return the active OCR adapter."""
        if self._ocr is None:
            self._ocr = get_ocr_adapter()
        return self._ocr

    async def get_tts(self) -> TTSAdapter:
        """Return the active TTS adapter."""
        if self._tts is None:
            self._tts = TTSAdapter()
        return self._tts


_manager_instance: ModelManager | None = None


def get_model_manager() -> ModelManager:
    """Return singleton ModelManager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ModelManager()
    return _manager_instance
