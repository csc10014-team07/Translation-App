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
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import asr, metrics, ocr, stream, translate, tts
from app.core.config import settings
from app.core.vram_monitor import get_vram_info
from app.models.manager import get_model_manager
from app.schemas.health import HealthResponse

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
    try:
        import av  # noqa: F401
    except ImportError:
        logger.warning(
            "PyAV (av) is not installed. Decoding .m4a and other mobile audio formats requires PyAV."
        )
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
            "Context-Aware Translation (TranslateGemma-4B), OCR (RapidOCR), "
            "and Hybrid TTS (Pocket TTS voice cloning / Edge-TTS)."
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

    # ── API Key Middleware (enforced only when API_KEY is set) ──────────────
    @application.middleware("http")
    async def api_key_middleware(request, call_next):
        if settings.API_KEY:
            if request.url.path not in ("/health", "/docs", "/redoc", "/openapi.json"):
                api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
                if api_key != settings.API_KEY:
                    from starlette.responses import JSONResponse
                    return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
        return await call_next(request)

    # ── Routers ────────────────────────────────────────────────────────────
    prefix = settings.API_PREFIX
    application.include_router(asr.router, prefix=prefix)
    application.include_router(ocr.router, prefix=prefix)
    application.include_router(translate.router, prefix=prefix)
    application.include_router(tts.router, prefix=prefix)
    application.include_router(metrics.router, prefix=prefix)
    application.include_router(stream.router)  # /ws/stream root path


    # ── Health check ───────────────────────────────────────────────────────
    @application.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health() -> HealthResponse:
        """Quick liveness probe — returns 200 with status, device, VRAM, and model status."""
        from app.models.manager import get_model_manager

        vram_info = get_vram_info()
        manager = get_model_manager()
        model_status = manager.get_status() if manager._is_started else {}
        return HealthResponse(
            status="ok",
            device=settings.effective_device(),
            vram=vram_info,
            vram_allocated_mb=vram_info.get("allocated_mb", 0.0),
            vram_total_mb=vram_info.get("total_mb", 0.0),
            models_loaded=model_status.get("models_loaded", {}),
        )

    return application


app = create_app()
