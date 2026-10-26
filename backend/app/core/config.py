"""Application configuration using pydantic-settings."""
import logging
from functools import lru_cache

import torch
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


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
    QWEN_TTS_MODEL_ID: str = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"

    # ── Compute device ─────────────────────────────────────────────────────
    DEVICE: str = "cuda"

    # ── Gemma llama-cpp options ────────────────────────────────────────────
    GEMMA_N_CTX: int = 4096
    GEMMA_N_GPU_LAYERS: int = -1  # -1 = all layers on GPU

    # ── Audio constraints ──────────────────────────────────────────────────
    MAX_AUDIO_DURATION_S: float = 60.0

    # ── Server options ─────────────────────────────────────────────────────
    API_PREFIX: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def effective_device(self) -> str:
        """Return 'cuda' if CUDA is available, otherwise fall back to 'cpu'."""
        if self.DEVICE == "cuda" and not torch.cuda.is_available():
            logger.warning(
                "CUDA requested but not available — falling back to CPU. "
                "Inference will be significantly slower."
            )
            return "cpu"
        return self.DEVICE


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return Settings()


# Convenience singleton for direct import
settings: Settings = get_settings()
