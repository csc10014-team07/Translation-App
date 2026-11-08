"""Application configuration using pydantic-settings."""
import logging
from functools import lru_cache

import torch
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _resolve_effective_device(device_setting: str) -> str:
    """Evaluate and cache effective device availability with fallback to CPU."""
    if device_setting.startswith("cuda"):
        if not torch.cuda.is_available():
            logger.warning("CUDA requested but torch.cuda.is_available() is False — falling back to CPU.")
            return "cpu"
        try:
            # Parse device index if specified (e.g., "cuda:1")
            device_index = 0
            if ":" in device_setting:
                parts = device_setting.split(":")
                if parts[1].isdigit():
                    device_index = int(parts[1])
            # Test kernel execution on the specified device (catches older compute capability mismatch)
            t = torch.tensor([1.0], device=f"cuda:{device_index}")
            _ = t * 2
            return device_setting
        except Exception as e:
            logger.warning(
                f"CUDA device {device_setting} test failed ({e}) — falling back to CPU."
            )
            return "cpu"
    return device_setting


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.

    All fields have sensible defaults so the app runs without a .env file,
    but production deployments should always set GEMMA_GGUF_PATH explicitly.
    """

    # ── Model identifiers / paths ──────────────────────────────────────────
    MODELS_DIR: str = "./models"
    PHOASR_MODEL_ID: str = "Qualcomm-AI-Research/PhoASR-whisper-small"
    GEMMA_GGUF_PATH: str = "./models/gemma/translategemma-4b-it.Q5_K_M.gguf"

    # ── Compute device ─────────────────────────────────────────────────────
    DEVICE: str = "cuda"

    # ── Gemma llama-cpp options ────────────────────────────────────────────
    GEMMA_N_CTX: int = 4096
    GEMMA_N_GPU_LAYERS: int = -1  # -1 = all layers on GPU

    # ── Audio constraints ──────────────────────────────────────────────────
    MAX_AUDIO_DURATION_S: float = 30.0

    # ── Online fallback ────────────────────────────────────────────────────
    ALLOW_ONLINE_FALLBACK: bool = False

    # ── TTS options ────────────────────────────────────────────────────────
    EDGE_TTS_ENABLED: bool = True

    # ── Server options ─────────────────────────────────────────────────────
    API_PREFIX: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def effective_device(self) -> str:
        """Return 'cuda' if CUDA is actually available and executable, otherwise fall back to 'cpu'."""
        return _resolve_effective_device(self.DEVICE)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return Settings()


# Convenience singleton for direct import
settings: Settings = get_settings()
