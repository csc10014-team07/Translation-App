"""TTS Adapter providing Hybrid Voice-Cloning and Natural Neural Speech."""
from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

class TTSResult(tuple):
    """Tuple of (audio_array: np.ndarray, sample_rate: int) with metadata attributes."""
    audio: np.ndarray
    sample_rate: int
    engine: str

    def __new__(cls, audio: np.ndarray, sample_rate: int, engine: str = "edge_tts"):
        obj = super().__new__(cls, (audio, sample_rate))
        obj.audio = audio
        obj.sample_rate = sample_rate
        obj.engine = engine
        return obj


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


class TTSAdapter:
    """Hybrid TTS adapter: Pocket TTS (CPU Voice Cloning) + Edge-TTS (Native Vietnamese & Neutral)."""

    def __init__(self) -> None:
        self._pocket_model = None

    def _load_pocket_tts(self):
        if self._pocket_model is None:
            try:
                from pocket_tts import TTSModel
                logger.info("Loading Pocket TTS model on CPU (0MB VRAM)...")
                self._pocket_model = TTSModel.load_model()
                logger.info("Pocket TTS loaded successfully on CPU.")
            except Exception as e:  # noqa: BLE001
                logger.warning("Could not load Pocket TTS: %s", e)
                self._pocket_model = None
        return self._pocket_model

    def _resolve_edge_voice(self, language: str, voice_style: str | None = None) -> str:
        """Resolve the appropriate Edge-TTS voice based on language and voice_style."""
        lang_key = language.strip().lower()
        if voice_style:
            style_key = voice_style.strip().lower()
            if "neural" in style_key:
                return voice_style.strip()
            if style_key in ("male", "nam", "boy", "man"):
                return EDGE_VOICES_MALE.get(lang_key, "en-US-GuyNeural")
            if style_key in ("female", "nu", "girl", "woman"):
                return EDGE_VOICES_FEMALE.get(lang_key, "en-US-JennyNeural")
        return EDGE_VOICES_FEMALE.get(lang_key, "en-US-JennyNeural")

    def _synthesize_edge_tts(
        self, text: str, language: str, voice_style: str | None = None
    ) -> TTSResult:
        """Synthesize using Edge-TTS asynchronously converted to synchronous array."""
        import edge_tts

        voice = self._resolve_edge_voice(language, voice_style)

        async def _run() -> tuple[np.ndarray, int]:
            comm = edge_tts.Communicate(text, voice)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
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
        return TTSResult(audio_arr, sr, engine="edge_tts")

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

        When target language is non-Vietnamese and reference audio is provided,
        Pocket TTS on CPU clones the user's voice timbre into the target language.
        When target language is Vietnamese or reference audio is omitted,
        Edge-TTS generates studio-quality native speech.

        Returns:
            TTSResult: Tuple of (audio_array: np.ndarray, sample_rate: int) with .engine attribute
        """
        lang_lower = language.strip().lower()
        is_vietnamese = lang_lower in ("vi", "vietnamese", "vie")

        # Vietnamese is synthesized via Edge-TTS (native neural voice)
        if is_vietnamese:
            return self._synthesize_edge_tts(text, "vi", voice_style=voice_style)

        # Non-Vietnamese: use Pocket TTS if reference audio is provided or explicitly preferred
        use_pocket = (
            (reference_audio_path is not None and Path(reference_audio_path).exists())
            or (preferred_engine and preferred_engine.lower() == "pocket_tts")
            or (voice_style and voice_style.lower() == "pocket_tts")
        )

        if use_pocket:
            pocket = self._load_pocket_tts()
            if pocket is not None:
                try:
                    state = None
                    if reference_audio_path and Path(reference_audio_path).exists():
                        try:
                            state = pocket.get_state_for_audio_prompt(str(reference_audio_path))
                            logger.info("Pocket TTS voice cloning active from user reference audio.")
                        except Exception as e:  # noqa: BLE001
                            logger.info(
                                "Custom cloning gated by HuggingFace (%s), using default voice 'alba'.", e
                            )
                            state = pocket.get_state_for_audio_prompt("alba")
                    else:
                        state = pocket.get_state_for_audio_prompt("alba")

                    audio_tensor = pocket.generate_audio(state, text, max_tokens=250)
                    audio_np = audio_tensor.squeeze().cpu().numpy().astype(np.float32)
                    return TTSResult(audio_np, pocket.sample_rate, engine="pocket_tts")
                except Exception as e:  # noqa: BLE001
                    logger.warning("Pocket TTS synthesis failed (%s), falling back to Edge-TTS.", e)

        # Standard studio-quality synthesis via Edge-TTS
        return self._synthesize_edge_tts(text, language, voice_style=voice_style)
