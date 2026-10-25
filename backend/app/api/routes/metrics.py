"""Metrics route — GET /api/metrics."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import dep_model_manager
from app.core.vram_monitor import vram_tracker
from app.models.manager import ModelManager

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get(
    "",
    summary="VRAM usage and model latency metrics",
    description=(
        "Returns current VRAM usage, which models are in VRAM/RAM, "
        "and aggregated cold-start / warm-inference latency statistics."
    ),
)
async def get_metrics(
    manager: ModelManager = Depends(dep_model_manager),
) -> dict:
    """Aggregate VRAM, model status, and latency metrics into a single response."""
    return {
        "model_status": manager.get_status(),
        "latency_metrics": vram_tracker.get_metrics(),
    }
