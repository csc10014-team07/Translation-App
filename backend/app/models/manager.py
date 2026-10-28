"""
Model Lifecycle Manager — serialises GPU swaps and enforces the VRAM budget.

VRAM budget
-----------
- PhoASR  (Whisper-small, FP16)  : ~1.5 GB — always resident
- Gemma   (GGUF Q5_K_M, 4b)     : ~4.5 GB — load on demand
- Pocket TTS (CPU/GPU)          : ~1.0 GB — load on demand

Gemma and Pocket TTS must **never** both be in VRAM simultaneously (combined
would exceed 8 GB).  An ``asyncio.Lock`` serialises every model-swap so that
concurrent API calls cannot accidentally trigger a double-load race.

CPU-RAM cache
-------------
When a large model is evicted from the GPU it is moved to CPU RAM (via
``model.to("cpu")`` / ``pin_memory``), keeping its weights in Python objects.
This avoids repeated disk I/O and makes the next VRAM-load significantly
faster.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Literal

import torch

from app.core.config import settings
from app.core.vram_monitor import get_vram_info, vram_tracker
from app.models.asr_adapter import ASRAdapter
from app.models.translation_adapter import TranslationAdapter
from app.models.tts_adapter import TTSAdapter

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Centralised manager for the three AI models used by the Translation App.

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

        # VRAM-residency tracking
        self._in_vram: set[str] = set()   # models currently on GPU
        self._in_ram: set[str] = set()    # models cached in CPU RAM

        # Serialise all GPU swaps — held only during the swap, not inference
        self._gpu_lock: asyncio.Lock = asyncio.Lock()

        self._device: str = settings.effective_device()

    # ── Startup / shutdown ─────────────────────────────────────────────────

    async def startup(self) -> None:
        """
        Load PhoASR to the GPU.  Called once from the FastAPI ``lifespan``
        startup hook.
        """
        logger.info("ModelManager startup: loading PhoASR …")
        vram_before = get_vram_info()
        logger.info("VRAM before PhoASR load: %s", vram_before)

        t0 = time.monotonic()
        # Run the synchronous load in a thread pool to avoid blocking the event loop
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._asr.load(settings.PHOASR_MODEL_ID, self._device),
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        vram_tracker.record_cold_start("phoasr", elapsed_ms)

        self._in_vram.add("phoasr")
        vram_after = get_vram_info()
        logger.info("VRAM after PhoASR load: %s", vram_after)
        logger.info("ModelManager startup complete.")

    async def shutdown(self) -> None:
        """Unload all models gracefully."""
        logger.info("ModelManager shutdown: unloading all models …")
        async with self._gpu_lock:
            if "gemma" in self._in_vram or "gemma" in self._in_ram:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._translation.unload
                )
                self._in_vram.discard("gemma")
                self._in_ram.discard("gemma")

            if "tts" in self._in_vram or "tts" in self._in_ram:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._tts.unload
                )
                self._in_vram.discard("tts")
                self._in_ram.discard("tts")

            if "phoasr" in self._in_vram:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._asr.unload_to_cpu
                )
                self._in_vram.discard("phoasr")
        logger.info("ModelManager shutdown complete.")

    # ── Public accessors ───────────────────────────────────────────────────

    async def get_asr(self) -> ASRAdapter:
        """Return the (always-resident) ASR adapter, ready for inference."""
        if not self._asr.is_loaded:
            raise RuntimeError("ASR model is not loaded. Was startup() called?")
        return self._asr

    async def get_translation(self) -> TranslationAdapter:
        """
        Return the Gemma translation adapter, loading it to the GPU if needed.
        Evicts TTS from VRAM first if required.
        """
        await self._ensure_large_model("gemma")
        return self._translation

    async def get_tts(self) -> TTSAdapter:
        """
        Return the Pocket TTS adapter, loading it to the GPU if needed.
        Evicts Gemma from VRAM first if required.
        """
        await self._ensure_large_model("tts")
        return self._tts

    # ── Internal VRAM management ───────────────────────────────────────────

    async def _ensure_large_model(
        self, model_name: Literal["gemma", "tts"]
    ) -> None:
        """
        Guarantee that *model_name* is resident in VRAM.

        If the *other* large model is currently in VRAM it is first moved to
        CPU RAM.  The ``_gpu_lock`` is held for the duration of the swap so
        that concurrent requests cannot trigger a race condition.

        Args:
            model_name: Either ``"gemma"`` or ``"tts"``.
        """
        if model_name in self._in_vram:
            # Already resident — no swap needed.
            return

        async with self._gpu_lock:
            # Re-check under the lock; another coroutine may have loaded it.
            if model_name in self._in_vram:
                return

            other = "tts" if model_name == "gemma" else "gemma"

            # ── Step 1: evict the other large model if it is in VRAM ───────
            if other in self._in_vram:
                vram_before = get_vram_info()
                logger.info(
                    "Evicting '%s' from VRAM to load '%s'. VRAM before: %s",
                    other,
                    model_name,
                    vram_before,
                )
                vram_tracker.snapshot_vram(f"before_evict_{other}")

                if other == "gemma":
                    # llama-cpp does not support CPU offload at runtime;
                    # we fully unload and reload from disk / RAM cache.
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._translation.unload
                    )
                else:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._tts.unload_to_cpu
                    )
                    self._in_ram.add(other)

                self._in_vram.discard(other)

                vram_after = get_vram_info()
                logger.info("VRAM after evicting '%s': %s", other, vram_after)
                vram_tracker.snapshot_vram(f"after_evict_{other}")

            # ── Step 2: load the requested model ──────────────────────────
            vram_before = get_vram_info()
            logger.info(
                "Loading '%s' to VRAM. VRAM before: %s",
                model_name,
                vram_before,
            )
            vram_tracker.snapshot_vram(f"before_load_{model_name}")

            t0 = time.monotonic()

            if model_name == "gemma":
                if "gemma" in self._in_ram:
                    # Weights already in CPU RAM — just move back to GPU.
                    # llama-cpp doesn't support this natively, so we reload.
                    logger.info("Gemma weights in CPU RAM — reloading to GPU …")
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._translation.load(
                        settings.GEMMA_GGUF_PATH,
                        settings.GEMMA_N_CTX,
                        settings.GEMMA_N_GPU_LAYERS,
                    ),
                )
                self._in_ram.discard("gemma")
            else:
                if "tts" in self._in_ram:
                    # Weights already on CPU — move back to GPU (fast path).
                    logger.info("TTS weights in CPU RAM — moving to GPU …")
                    await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self._tts.load_to_gpu(self._device)
                    )
                    self._in_ram.discard("tts")
                else:
                    # First-ever load from disk.
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self._tts.load(settings.POCKET_TTS_LANGUAGE, self._device),
                    )

            elapsed_ms = (time.monotonic() - t0) * 1000
            vram_tracker.record_cold_start(model_name, elapsed_ms)
            self._in_vram.add(model_name)

            vram_after = get_vram_info()
            logger.info(
                "Loaded '%s' in %.0f ms. VRAM after: %s",
                model_name,
                elapsed_ms,
                vram_after,
            )
            vram_tracker.snapshot_vram(f"after_load_{model_name}")

    # ── Status ─────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """
        Return a snapshot of which models are currently resident.

        Returns:
            Dict with keys ``in_vram``, ``in_ram``, ``device``, and
            ``vram_info``.
        """
        return {
            "in_vram": sorted(self._in_vram),
            "in_ram": sorted(self._in_ram),
            "device": self._device,
            "vram_info": get_vram_info(),
        }


# Module-level singleton — imported by the dependency injector
_manager_instance: ModelManager | None = None


def get_model_manager() -> ModelManager:
    """Return (and lazily create) the singleton :class:`ModelManager`."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ModelManager()
    return _manager_instance
