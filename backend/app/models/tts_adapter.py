"""TTS adapter wrapping Pocket TTS."""
from __future__ import annotations

import gc
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import torch

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_VIETNAMESE_LANG_CODES = {"vi", "vietnamese", "vie", "tiếng việt"}
_DEFAULT_SAMPLE_RATE = 24_000


def _is_vietnamese(language: str) -> bool:
    """Return True if *language* refers to Vietnamese."""
    return language.strip().lower() in _VIETNAMESE_LANG_CODES

# Map language names/codes to Pocket TTS language identifiers
_POCKET_TTS_LANGUAGE_MAP = {
    "en": "english",
    "english": "english",
    "eng": "english",
    "fr": "french",
    "french": "french",
    "fra": "french",
    "de": "german",
    "german": "german",
    "deu": "german",
    "pt": "portuguese",
    "portuguese": "portuguese",
    "por": "portuguese",
    "it": "italian",
    "italian": "italian",
    "ita": "italian",
    "es": "spanish",
    "spanish": "spanish",
    "spa": "spanish",
    "nl": "dutch",
    "dutch": "dutch",
    "nld": "dutch",
}


def _map_language_to_pocket_tts(language: str) -> str:
    """Map a language identifier to Pocket TTS language code."""
    lang = language.strip().lower()
    return _POCKET_TTS_LANGUAGE_MAP.get(lang, "english")


class TTSAdapter:
    """
    Thin wrapper around Pocket TTS for voice synthesis.

    Vietnamese is explicitly **not supported** — calling :meth:`synthesize`
    with ``language="vi"`` (or any Vietnamese variant) raises a
    ``ValueError``.

    The adapter uses the Pocket TTS high-level API which supports:
    - CPU and GPU inference
    - Voice cloning
    - Multiple languages: english, french, german, portuguese, italian, spanish, dutch
    """

    def __init__(self) -> None:
        self._model = None
        self._device: str = "cpu"
        self._loaded: bool = False
        self._model_language: str = "english"

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def load(self, model_language: str | None = None, device: str = "cpu") -> None:
        """
        Load the Pocket TTS model to *device*.

        Args:
            model_language: Target language for the model (e.g., "english", "french").
                           If None, defaults to "english".
            device:   ``"cuda"`` or ``"cpu"``.
        """
        self._device = device
        self._model_language = model_language or "english"
        logger.info("Loading Pocket TTS model (language=%s) to %s ...", self._model_language, device)
        t0 = time.monotonic()

        try:
            from pocket_tts import TTSModel

            self._model = TTSModel.load_model(language=self._model_language)
            if device == "cuda" and torch.cuda.is_available():
                self._model.to("cuda")
            self._loaded = True
            logger.info("Loaded Pocket TTS via pocket_tts package.")
        except ImportError:
            raise ImportError(
                "pocket_tts package is required. Please install it with: pip install pocket-tts"
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to load Pocket TTS model: {exc}") from exc

        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info("TTS model loaded in %.0f ms", elapsed_ms)

    def unload(self) -> None:
        """Free the model entirely from memory."""
        logger.info("Unloading Pocket TTS model ...")
        if self._model is not None:
            del self._model
            self._model = None
        self._loaded = False
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Pocket TTS model unloaded.")

    def unload_to_cpu(self) -> None:
        """Move model weights to CPU RAM, keeping them in Python for fast reload."""
        if self._model is None or self._device == "cpu":
            return
        logger.info("Moving Pocket TTS model to CPU RAM ...")
        if hasattr(self._model, "to"):
            self._model.to("cpu")
        self._device = "cpu"
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def load_to_gpu(self, device: str = "cuda") -> None:
        """Move model weights from CPU RAM back to GPU."""
        if self._model is None or self._device == device:
            return
        logger.info("Moving Pocket TTS model to %s ...", device)
        if hasattr(self._model, "to"):
            self._model.to(device)
        self._device = device

    # ── Inference ──────────────────────────────────────────────────────────

    def synthesize(
        self,
        text: str,
        language: str,
        reference_audio_path: str | None = None,
        reference_text: str | None = None,
    ) -> tuple[np.ndarray, int]:
        """
        Synthesize speech for *text*.

        Args:
            text:                   Text to synthesize.
            language:               Target spoken language.
            reference_audio_path:   Path to a reference WAV for voice cloning (optional).
            reference_text:         Transcript of *reference_audio_path* (optional).

        Returns:
            A tuple ``(audio_array, sample_rate)`` where *audio_array* is a
            1-D float32 NumPy array and *sample_rate* is typically 24 000.

        Raises:
            ValueError: If *language* is Vietnamese.
            RuntimeError: If the model has not been loaded.
        """
        if _is_vietnamese(language):
            raise ValueError(
                "TTS is not supported for Vietnamese target language. "
                "Vietnamese output is text-only."
            )

        if not self._loaded or self._model is None:
            raise RuntimeError("TTSAdapter.load() must be called before synthesize().")

        logger.debug("Synthesizing %d chars in language '%s' ...", len(text), language)
        t0 = time.monotonic()

        # Map language to Pocket TTS language code
        pocket_lang = _map_language_to_pocket_tts(language)

        # Get voice state for reference audio if provided
        voice_state = None
        if reference_audio_path:
            try:
                voice_state = self._model.get_state_for_audio_prompt(reference_audio_path)
                logger.info("Using voice cloning from reference audio: %s", reference_audio_path)
            except Exception as exc:
                logger.warning("Could not use reference audio for voice cloning: %s", exc)
                # Fall back to default voice
                pass

        # Generate audio
        if voice_state is not None:
            audio_tensor = self._model.generate_audio(voice_state, text)
        else:
            audio_tensor = self._model.generate_audio(text)

        # Convert tensor to numpy array
        if isinstance(audio_tensor, torch.Tensor):
            audio_array = audio_tensor.detach().cpu().numpy()
        else:
            audio_array = np.array(audio_tensor, dtype=np.float32)

        # Ensure float32
        audio_array = audio_array.astype(np.float32)

        # Get sample rate from model
        sample_rate = self._model.sample_rate

        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info("TTS synthesis completed in %.0f ms, sr=%d", elapsed_ms, sample_rate)
        return audio_array, sample_rate

    @property
    def is_loaded(self) -> bool:
        """True if the model has been loaded (regardless of device)."""
        return self._loaded
