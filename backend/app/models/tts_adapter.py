"""TTS adapter wrapping Pocket TTS."""
from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

import numpy as np
import torch

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_VIETNAMESE_LANG_CODES = {"vi", "vietnamese", "vie", "tiếng việt"}

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
}

_SUPPORTED_POCKET_TTS_LANGUAGES = {"english", "french", "german", "portuguese", "italian", "spanish"}


def _is_vietnamese(language: str) -> bool:
    """Return True if *language* refers to Vietnamese."""
    return language.strip().lower() in _VIETNAMESE_LANG_CODES


def _map_language_to_pocket_tts(language: str) -> str:
    """Map a language identifier to Pocket TTS language code."""
    lang = language.strip().lower()
    return _POCKET_TTS_LANGUAGE_MAP.get(lang, lang)


class TTSAdapter:
    """
    Thin wrapper around Pocket TTS for voice synthesis.

    Maintains one Pocket TTS model per language, loaded lazily on CPU.
    Voice states for default voices are cached per language.
    Uses per-language locks for thread-safe loading and synthesis.
    """

    def __init__(self) -> None:
        self._models: dict[str, torch.nn.Module] = {}
        self._voice_states: dict[str, torch.Tensor] = {}
        # Create locks for each supported language upfront
        self._load_locks: dict[str, threading.Lock] = {
            lang: threading.Lock() for lang in _SUPPORTED_POCKET_TTS_LANGUAGES
        }
        self._synth_locks: dict[str, threading.Lock] = {
            lang: threading.Lock() for lang in _SUPPORTED_POCKET_TTS_LANGUAGES
        }

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def _ensure_model_loaded(self, pocket_lang: str) -> torch.nn.Module:
        """Load Pocket TTS model for *pocket_lang* if not already loaded."""
        if pocket_lang not in self._models:
            lock = self._load_locks[pocket_lang]
            with lock:
                if pocket_lang not in self._models:
                    logger.info("Loading Pocket TTS model for language=%s on CPU...", pocket_lang)
                    from pocket_tts import TTSModel
                    self._models[pocket_lang] = TTSModel.load_model(language=pocket_lang)
                    logger.info("Pocket TTS model loaded for language=%s.", pocket_lang)
        return self._models[pocket_lang]

    def _get_voice_state(self, pocket_lang: str) -> torch.Tensor:
        """Get or create cached voice state for the default voice of *pocket_lang*."""
        if pocket_lang not in self._voice_states:
            model = self._ensure_model_loaded(pocket_lang)
            from pocket_tts.default_parameters import get_default_voice_for_language
            voice_name = get_default_voice_for_language(pocket_lang)
            self._voice_states[pocket_lang] = model.get_state_for_audio_prompt(voice_name)
            logger.debug("Cached voice state for language=%s.", pocket_lang)
        return self._voice_states[pocket_lang]

    def load(self, model_language: str | None = None, device: str = "cpu") -> None:
        """
        Pre-load a specific language model (optional).
        Models are loaded lazily by default; device is ignored.
        """
        if model_language:
            pocket_lang = _map_language_to_pocket_tts(model_language)
            if pocket_lang in _SUPPORTED_POCKET_TTS_LANGUAGES:
                self._ensure_model_loaded(pocket_lang)

    def unload(self) -> None:
        """Free all models from memory."""
        logger.info("Unloading all Pocket TTS models...")
        self._models.clear()
        self._voice_states.clear()
        logger.info("All Pocket TTS models unloaded.")

    def unload_to_cpu(self) -> None:
        """No-op for Pocket TTS (always on CPU)."""
        pass

    def load_to_gpu(self, device: str = "cuda") -> None:
        """No-op for Pocket TTS (always on CPU)."""
        pass

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
            ValueError: If *language* is Vietnamese or not supported by Pocket TTS,
                       or if reference audio cannot be used.
            RuntimeError: If model loading fails.
        """
        if _is_vietnamese(language):
            raise ValueError(
                "TTS is not supported for Vietnamese target language. "
                "Vietnamese output is text-only."
            )

        pocket_lang = _map_language_to_pocket_tts(language)
        
        if pocket_lang not in _SUPPORTED_POCKET_TTS_LANGUAGES:
            raise ValueError(
                f"TTS is not supported for language '{language}'. "
                f"Supported languages: {sorted(_SUPPORTED_POCKET_TTS_LANGUAGES)}"
            )

        model = self._ensure_model_loaded(pocket_lang)
        synth_lock = self._synth_locks[pocket_lang]

        logger.debug("Synthesizing %d chars in language '%s'...", len(text), language)

        with synth_lock:
            # Use reference audio for voice cloning if provided
            if reference_audio_path:
                try:
                    voice_state = model.get_state_for_audio_prompt(reference_audio_path)
                except Exception as exc:
                    raise ValueError(f"Could not use reference audio: {exc}") from exc
            else:
                voice_state = self._get_voice_state(pocket_lang)

            audio_tensor = model.generate_audio(voice_state, text)

            if isinstance(audio_tensor, torch.Tensor):
                audio_array = audio_tensor.detach().cpu().numpy()
            else:
                audio_array = np.array(audio_tensor, dtype=np.float32)

            audio_array = audio_array.astype(np.float32)
            sample_rate = model.sample_rate

            logger.info("TTS synthesis completed, sr=%d", sample_rate)
            return audio_array, sample_rate

    @property
    def is_loaded(self) -> bool:
        """True if at least one model has been loaded."""
        return len(self._models) > 0
