"""
Model Lifecycle Manager — manages loading of AI models.

 PhoASR (Whisper-small, FP16) is always resident on GPU.
 Gemma   (GGUF Q5_K_M, 4b) is loaded at startup and stays resident.
 Pocket TTS (CPU only) loads models lazily per language on CPU.

No VRAM eviction: all GPU models stay loaded once started.
"""
from __future__ import annotations

import asyncio
import logging
import time

from app.core.config import settings
from app.core.vram_monitor import get_vram_info, vram_tracker
from app.models.asr_adapter import ASRAdapter
from app.models.translation_adapter import TranslationAdapter
from app.models.tts_adapter import TTSAdapter

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Centralised manager for the AI models used by the Translation App.

    Usage
    -----
    Instantiate once at application startup, call :meth:`startup`, then use
    :meth:`get_asr`, :meth:`get_translation`, and :meth:`get_tts` in route
    handlers.
    """

    def __init__(self) -> None:
        self._asr = ASRAdapter()
        self._translation = TranslationAdapter()
        self._tts = TTSAdapter()

        self._in_vram: set[str] = set()

        self._gpu_lock: asyncio.Lock = asyncio.Lock()

        self._device: str = settings.effective_device()

    # ── Startup / shutdown ─────────────────────────────────────────────────

    async def startup(self) -> None:
        """
        Load PhoASR and Gemma to the GPU.
        """
        logger.info("ModelManager startup: loading models...")

        # Load PhoASR
        vram_before = get_vram_info()
        logger.info("VRAM before PhoASR load: %s", vram_before)
        t0 = time.monotonic()
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._asr.load(settings.PHOASR_MODEL_ID, self._device),
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        vram_tracker.record_cold_start("phoasr", elapsed_ms)
        self._in_vram.add("phoasr")
        vram_after = get_vram_info()
        logger.info("VRAM after PhoASR load: %s", vram_after)

        # Load Gemma after PhoASR
        logger.info("Loading Gemma...")
        vram_before = get_vram_info()
        logger.info("VRAM before Gemma load: %s", vram_before)
        vram_tracker.snapshot_vram("before_load_gemma")
        t0 = time.monotonic()
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._translation.load(
                settings.GEMMA_GGUF_PATH,
                settings.GEMMA_N_CTX,
                settings.GEMMA_N_GPU_LAYERS,
            ),
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        vram_tracker.record_cold_start("gemma", elapsed_ms)
        self._in_vram.add("gemma")
        vram_after = get_vram_info()
        logger.info("VRAM after Gemma load: %s", vram_after)
        vram_tracker.snapshot_vram("after_load_gemma")

        logger.info("ModelManager startup complete.")

    async def shutdown(self) -> None:
        """Unload all models gracefully."""
        logger.info("ModelManager shutdown: unloading all models...")
        async with self._gpu_lock:
            if "gemma" in self._in_vram:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._translation.unload
                )
                self._in_vram.discard("gemma")

            if "phoasr" in self._in_vram:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._asr.unload
                )
                self._in_vram.discard("phoasr")
        # TTS models are on CPU and managed independently
        await asyncio.get_event_loop().run_in_executor(
            None, self._tts.unload
        )
        logger.info("ModelManager shutdown complete.")

    # ── Public accessors ───────────────────────────────────────────────────

    async def get_asr(self) -> ASRAdapter:
        """Return the ASR adapter, ready for inference."""
        if not self._asr.is_loaded:
            raise RuntimeError("ASR model is not loaded. Was startup() called?")
        return self._asr

    async def get_translation(self) -> TranslationAdapter:
        """Return the Gemma translation adapter."""
        return self._translation

    async def get_tts(self) -> TTSAdapter:
        """Return the Pocket TTS adapter."""
        return self._tts

    # ── Status ─────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """
        Return a snapshot of which models are currently resident.
        """
        return {
            "in_vram": sorted(self._in_vram),
            "device": self._device,
            "vram_info": get_vram_info(),
        }


# Module-level singleton
_manager_instance: ModelManager | None = None


def get_model_manager() -> ModelManager:
    """Return (and lazily create) the singleton ModelManager."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ModelManager()
    return _manager_instance
