"""VRAM monitoring utilities."""
import logging
import time
from collections import defaultdict
from typing import Any

import torch

logger = logging.getLogger(__name__)


def get_vram_info() -> dict[str, float]:
    """
    Return current VRAM usage statistics for the default CUDA device.

    Returns:
        A dict with keys ``used_mb``, ``free_mb``, and ``total_mb``.
        All values are floats (MiB).  If CUDA is unavailable every value
        is 0.0.
    """
    if not torch.cuda.is_available():
        return {"used_mb": 0.0, "free_mb": 0.0, "total_mb": 0.0}

    props = torch.cuda.get_device_properties(0)
    total_bytes: int = props.total_memory
    # PyTorch tracks *allocated* (used by tensors) separately from *reserved*
    # (cached by the allocator).  We report the allocator-reserved amount as
    # "used" so that the number reflects actual driver-level commitment.
    reserved_bytes: int = torch.cuda.memory_reserved(0)
    allocated_bytes: int = torch.cuda.memory_allocated(0)

    used_mb = reserved_bytes / 1024 ** 2
    total_mb = total_bytes / 1024 ** 2
    free_mb = total_mb - used_mb
    allocated_mb = allocated_bytes / 1024 ** 2

    return {
        "used_mb": round(used_mb, 1),
        "free_mb": round(free_mb, 1),
        "total_mb": round(total_mb, 1),
        "allocated_mb": round(allocated_mb, 1),
    }


class VRAMTracker:
    """
    Lightweight in-process metrics store for model cold-start and warm-inference
    latencies, plus periodic VRAM snapshots.
    """

    def __init__(self) -> None:
        self._cold_starts: dict[str, list[float]] = defaultdict(list)
        self._warm_inferences: dict[str, list[float]] = defaultdict(list)
        self._vram_snapshots: list[dict[str, Any]] = []

    # ── Recording helpers ──────────────────────────────────────────────────

    def record_cold_start(self, model_name: str, latency_ms: float) -> None:
        """Record a cold-start (model load) latency measurement."""
        self._cold_starts[model_name].append(latency_ms)
        logger.debug("Cold-start recorded: model=%s latency=%.1f ms", model_name, latency_ms)

    def record_warm_inference(self, model_name: str, latency_ms: float) -> None:
        """Record a warm-inference (model already in VRAM) latency measurement."""
        self._warm_inferences[model_name].append(latency_ms)
        logger.debug("Warm inference recorded: model=%s latency=%.1f ms", model_name, latency_ms)

    def snapshot_vram(self, label: str = "") -> None:
        """Take a VRAM snapshot and store it with an optional label."""
        snap = get_vram_info()
        snap["label"] = label
        snap["ts"] = time.time()
        self._vram_snapshots.append(snap)

    # ── Aggregation ────────────────────────────────────────────────────────

    def get_metrics(self) -> dict[str, Any]:
        """
        Return all recorded metrics plus current VRAM state.

        Returns:
            A nested dict with keys:
            - ``current_vram``: result of :func:`get_vram_info`
            - ``cold_starts``: per-model lists of load latencies (ms)
            - ``warm_inferences``: per-model lists of inference latencies (ms)
            - ``vram_snapshots``: list of historical VRAM readings
        """

        def _summarise(times: list[float]) -> dict[str, float]:
            if not times:
                return {}
            return {
                "count": len(times),
                "min_ms": round(min(times), 1),
                "max_ms": round(max(times), 1),
                "avg_ms": round(sum(times) / len(times), 1),
                "last_ms": round(times[-1], 1),
            }

        return {
            "current_vram": get_vram_info(),
            "cold_starts": {
                model: _summarise(latencies)
                for model, latencies in self._cold_starts.items()
            },
            "warm_inferences": {
                model: _summarise(latencies)
                for model, latencies in self._warm_inferences.items()
            },
            "vram_snapshots": self._vram_snapshots[-20:],  # keep last 20
        }


# Module-level singleton used by the model manager and metrics route.
vram_tracker = VRAMTracker()
