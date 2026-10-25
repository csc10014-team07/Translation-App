"""
FastAPI application entry point for the Translation App backend.

Startup sequence
----------------
1. ModelManager is created (singleton).
2. PhoASR is loaded to the GPU.
3. VRAM usage is logged.

Shutdown sequence
-----------------
1. All models are unloaded gracefully.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import asr, metrics, ocr, translate, tts
from app.core.config import settings
from app.core.vram_monitor import get_vram_info
from app.models.manager import get_model_manager

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle startup and shutdown events."""
    manager = get_model_manager()
    logger.info("=== Translation App starting up ===")
    logger.info("Device: %s", settings.effective_device())
    logger.info("VRAM at boot: %s", get_vram_info())

    await manager.startup()
    logger.info("All startup models loaded. VRAM: %s", get_vram_info())

    yield  # ← application runs here

    logger.info("=== Translation App shutting down ===")
    await manager.shutdown()
    logger.info("Shutdown complete.")


# ── Application factory ────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="Translation App API",
        description=(
            "Vietnamese Translation App backend — ASR (PhoASR), "
            "Translation & OCR (Gemma 3 4B), TTS (Qwen3-TTS)."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS (allow all origins for development) ───────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ────────────────────────────────────────────────────────────
    prefix = settings.API_PREFIX
    application.include_router(asr.router, prefix=prefix)
    application.include_router(ocr.router, prefix=prefix)
    application.include_router(translate.router, prefix=prefix)
    application.include_router(tts.router, prefix=prefix)
    application.include_router(metrics.router, prefix=prefix)

    # ── Health check ───────────────────────────────────────────────────────
    @application.get("/health", tags=["Health"])
    async def health() -> dict:
        """Quick liveness probe — returns 200 when the app is running."""
        return {"status": "ok", "vram": get_vram_info()}

    return application


app = create_app()
