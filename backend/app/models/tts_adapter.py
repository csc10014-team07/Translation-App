"""TTS Adapter providing Hybrid Voice-Cloning and Natural Neural Speech."""
from __future__ import annotations

import asyncio
import logging
import tempfile
import threading
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from app.core.config import settings

logger = logging.getLogger(__name__)

# Pocket TTS supported languages (verified from package)
POCKET_TTS_LANGUAGES = {"en", "fr", "de", "es", "pt", "it", "english", "french", "german", "spanish", "portuguese", "italian"}

# Edge TTS language to voice mapping
EDGE_VOICES_FEMALE = {
    "vi": "vi-VN-HoaiMyNeural", "vietnamese": "vi-VN-HoaiMyNeural", "vie": "vi-VN-HoaiMyNeural",
    "en": "en-US-JennyNeural", "english": "en-US-JennyNeural",
    "ja": "ja-JP-NanamiNeural", "japanese": "ja-JP-NanamiNeural",
    "zh": "zh-CN-XiaoxiaoNeural", "chinese": "zh-CN-XiaoxiaoNeural",
    "ko": "ko-KR-SunHiNeural", "korean": "ko-KR-SunHiNeural",
    "fr": "fr-FR-DeniseNeural", "french": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural", "german": "de-DE-KatjaNeural",
    "es": "es-ES-ElviraNeural", "spanish": "es-ES-ElviraNeural",
}

EDGE_VOICES_MALE = {
    "vi": "vi-VN-NamMinhNeural", "vietnamese": "vi-VN-NamMinhNeural", "vie": "vi-VN-NamMinhNeural",
    "en": "en-US-GuyNeural", "english": "en-US-GuyNeural",
    "ja": "ja-JP-KeitaNeural", "japanese": "ja-JP-KeitaNeural",
    "zh": "zh-CN-YunxiNeural", "chinese": "zh-CN-YunxiNeural",
    "ko": "ko-KR-InJoonNeural", "korean": "ko-KR-InJoonNeural",
    "fr": "fr-FR-HenriNeural", "french": "fr-FR-HenriNeural",
    "de": "de-DE-KillianNeural", "german": "de-DE-KillianNeural",
    "es": "es-ES-AlvaroNeural", "spanish": "es-ES-AlvaroNeural",
}

EDGE_VOICES = EDGE_VOICES_FEMALE

class TTSResult(tuple):
    """Tuple of (audio_array: np.ndarray, sample_rate: int) with metadata attributes."""
    audio: np.ndarray
    sample_rate: int
    engine: str
    voice_note: str

    def __new__(cls, audio: np.ndarray, sample_rate: int, engine: str = "edge_tts", voice_note: str = "") -> TTSResult:
        obj = super().__new__(cls, (audio, sample_rate))
        obj.audio = audio
        obj.sample_rate = sample_rate
        obj.engine = engine
        obj.voice_note = voice_note
        return obj


class TTSAdapter:
    """Hybrid TTS adapter: Pocket TTS (CPU Voice Cloning) + Edge-TTS (Native Vietnamese & Neutral)."""

    def __init__(self) -> None:
        self._pocket_models: dict[str, Any] = {}
        self._pocket_load_locks: dict[str, threading.Lock] = {}
        self._pocket_inference_lock = threading.Lock()
        # Pre-create locks for all Pocket TTS languages
        for lang in POCKET_TTS_LANGUAGES:
            self._pocket_load_locks[lang] = threading.Lock()

    def _load_pocket_tts(self, language: str) -> Any:
        """Load Pocket TTS model for a specific language."""
        lang_key = language.strip().lower()
        if lang_key not in self._pocket_models:
            lock = self._pocket_load_locks.get(lang_key, threading.Lock())
            with lock:
                # Double-check after acquiring lock
                if lang_key not in self._pocket_models:
                    try:
                        from pocket_tts import TTSModel
                        logger.info("Loading Pocket TTS model for %s on CPU (0MB VRAM)...", lang_key)
                        model = TTSModel.load_model(language=lang_key)
                        self._pocket_models[lang_key] = model
                        logger.info("Pocket TTS loaded successfully for %s on CPU.", lang_key)
                    except Exception as e:  # noqa: BLE001
                        logger.warning("Could not load Pocket TTS for %s: %s", lang_key, e)
                        self._pocket_models[lang_key] = None
        return self._pocket_models.get(lang_key)

    def _get_pocket_voice_state(self, model: Any, reference_audio_path: str | Path | None) -> tuple[dict[str, Any], str]:
        """Get the voice state for Pocket TTS, either from reference audio or default."""
        if reference_audio_path is not None:
            ref_path = Path(reference_audio_path)
            if ref_path.exists():
                try:
                    state = model.get_state_for_audio_prompt(str(reference_audio_path))
                    logger.info("Pocket TTS voice cloning active from user reference audio.")
                    return state, "voice cloned from reference audio"
                except Exception as e:  # noqa: BLE001
                    logger.warning("Pocket TTS cloning failed (%s), using default voice.", e)
                    # Fall back to default voice
                    voice_name = "alba"
                    return model.get_state_for_audio_prompt(voice_name), f"cloning failed ({e}), using default voice '{voice_name}'"
        # No reference audio, use default voice
        voice_name = "alba"
        return model.get_state_for_audio_prompt(voice_name), f"using default voice '{voice_name}'"

    def _get_default_pocket_voice_for_language(self, language: str) -> str:
        """Get the default voice name for a Pocket TTS language."""
        try:
            from pocket_tts import default_parameters
            return default_parameters.get_default_voice_for_language(language)
        except Exception:  # noqa: BLE001
            return "alba"

    def _resolve_edge_voice(self, language: str, voice_style: str | None = None) -> tuple[str, str]:
        """Resolve the appropriate Edge-TTS voice based on language and voice_style.
        
        Returns:
            tuple of (voice_name, voice_note)
        """
        lang_key = language.strip().lower()
        voice_note = ""
        
        if voice_style:
            style_key = voice_style.strip().lower()
            if "neural" in style_key:
                return voice_style.strip(), f"explicit voice: {voice_style}"
            if style_key in ("male", "nam", "boy", "man"):
                voice = EDGE_VOICES_MALE.get(lang_key, "en-US-GuyNeural")
                voice_note = f"male voice: {voice}"
                return voice, voice_note
            if style_key in ("female", "nu", "girl", "woman"):
                voice = EDGE_VOICES_FEMALE.get(lang_key, "en-US-JennyNeural")
                voice_note = f"female voice: {voice}"
                return voice, voice_note
        
        voice = EDGE_VOICES_FEMALE.get(lang_key, "en-US-JennyNeural")
        voice_note = f"default voice: {voice}"
        return voice, voice_note

    def _is_edge_language_supported(self, language: str) -> bool:
        """Check if a language is supported by Edge-TTS."""
        lang_key = language.strip().lower()
        # All languages that have entries in EDGE_VOICES_FEMALE or EDGE_VOICES_MALE are supported
        supported = set(EDGE_VOICES_FEMALE.keys()) | set(EDGE_VOICES_MALE.keys())
        return lang_key in supported

    def _synthesize_edge_tts(
        self, text: str, language: str, voice_style: str | None = None
    ) -> TTSResult:
        """Synthesize using Edge-TTS asynchronously with timeout."""
        if not settings.EDGE_TTS_ENABLED:
            raise RuntimeError("Edge-TTS is disabled (EDGE_TTS_ENABLED=false)")
        
        if not self._is_edge_language_supported(language):
            lang_key = language.strip().lower()
            raise ValueError(f"Unknown Edge-TTS language: {language} (lang_key: {lang_key})")
        
        import aiohttp
        import edge_tts

        voice, voice_note = self._resolve_edge_voice(language, voice_style)

        async def _run() -> tuple[np.ndarray, int]:
            connector = aiohttp.TCPConnector(limit=10, force_close=True, limit_per_host=5)
            
            comm = edge_tts.Communicate(
                text, 
                voice, 
                connector=connector,
                connect_timeout=10,
                receive_timeout=20
            )
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, mode='wb') as tmp:
                tmp_path = tmp.name
            try:
                await comm.save(tmp_path)
                data, sr = sf.read(tmp_path)
                if data.ndim > 1:
                    data = data.mean(axis=1)
                return data.astype(np.float32), sr
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        audio_arr, sr = asyncio.run(_run())
        return TTSResult(audio_arr, sr, engine="edge_tts", voice_note=voice_note)

    def synthesize(
        self,
        text: str,
        language: str = "English",
        reference_audio_path: str | Path | None = None,
        voice_style: str | None = None,
        preferred_engine: str | None = None,
    ) -> TTSResult:
        """
        Synthesize speech from text.

        For Pocket TTS supported languages (en/fr/de/es/pt/it), use Pocket TTS on CPU
        with voice cloning when reference audio is provided.
        For other languages, use Edge-TTS for native neural speech.

        Returns:
            TTSResult: Tuple of (audio_array: np.ndarray, sample_rate: int) with .engine and .voice_note attributes
        Raises:
            ValueError: If the requested engine is not available or language is unsupported
            RuntimeError: If Edge-TTS is disabled but required, or synthesis fails
        """
        lang_lower = language.strip().lower()
        is_vietnamese = lang_lower in ("vi", "vietnamese", "vie")
        
        # Check if explicit engine requested
        if preferred_engine:
            preferred_lower = preferred_engine.lower()
            if preferred_lower == "pocket_tts":
                if lang_lower not in POCKET_TTS_LANGUAGES:
                    raise ValueError(f"Pocket TTS does not support language: {language}")
                return self._synthesize_pocket_tts(text, language, reference_audio_path, voice_style)
            elif preferred_lower == "edge_tts":
                if not settings.EDGE_TTS_ENABLED:
                    raise RuntimeError("Edge-TTS is disabled (EDGE_TTS_ENABLED=false)")
                if not self._is_edge_language_supported(language):
                    raise ValueError(f"Unknown Edge-TTS language: {language}")
                return self._synthesize_edge_tts(text, language, voice_style)
        
        # Vietnamese always uses Edge-TTS
        if is_vietnamese:
            if not settings.EDGE_TTS_ENABLED:
                raise RuntimeError("Edge-TTS is disabled (EDGE_TTS_ENABLED=false)")
            if not self._is_edge_language_supported(language):
                raise ValueError(f"Unknown Edge-TTS language: {language}")
            return self._synthesize_edge_tts(text, language, voice_style)
        
        # Pocket TTS languages: use Pocket TTS if reference audio is provided
        if lang_lower in POCKET_TTS_LANGUAGES:
            if reference_audio_path is not None:
                ref_path = Path(reference_audio_path) if reference_audio_path else None
                if ref_path is not None and ref_path.exists():
                    return self._synthesize_pocket_tts(text, language, reference_audio_path, voice_style)
        
        # Default: use Edge-TTS for all other cases
        if not settings.EDGE_TTS_ENABLED:
            raise RuntimeError("Edge-TTS is disabled (EDGE_TTS_ENABLED=false)")
        if not self._is_edge_language_supported(language):
            raise ValueError(f"Unknown Edge-TTS language: {language}")
        return self._synthesize_edge_tts(text, language, voice_style)

    def _synthesize_pocket_tts(
        self,
        text: str,
        language: str,
        reference_audio_path: str | Path | None,
        voice_style: str | None,
    ) -> TTSResult:
        """Synthesize using Pocket TTS with per-language model loading."""
        # Load Pocket TTS for this language
        model = self._load_pocket_tts(language)
        if model is None:
            raise RuntimeError(f"Pocket TTS model failed to load for {language}")
        
        voice_note = ""
        try:
            with self._pocket_inference_lock:
                # Get voice state
                state, state_note = self._get_pocket_voice_state(model, reference_audio_path)
                voice_note = state_note
                
                # Handle voice_style override
                if voice_style and voice_style.lower() != "pocket_tts":
                    # Try to use the specified voice as audio conditioning
                    try:
                        state = model.get_state_for_audio_prompt(voice_style)
                        voice_note = f"voice style: {voice_style}"
                    except Exception as e:  # noqa: BLE001
                        logger.warning("Voice style '%s' not recognized, using default: %s", voice_style, e)
                        voice_note = f"voice style '{voice_style}' not recognized, using default"
                
                # Generate audio with the voice state
                audio_tensor = model.generate_audio(state, text, max_tokens=250)
                audio_np = audio_tensor.squeeze().cpu().numpy().astype(np.float32)
                
                return TTSResult(audio_np, model.sample_rate, engine="pocket_tts", voice_note=voice_note)
        except Exception as e:  # noqa: BLE001
            logger.warning("Pocket TTS synthesis failed for %s: %s", language, e)
            raise RuntimeError(f"Pocket TTS synthesis failed: {e}") from e
