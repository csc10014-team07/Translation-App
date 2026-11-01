"""ASR Adapter wrapping Qualcomm PhoASR-whisper-small."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import torch
from transformers import pipeline

from app.core.config import settings

logger = logging.getLogger(__name__)


def load_audio_file(audio_path: str | Path, target_sr: int = 16000) -> tuple[np.ndarray, float]:
    """
    Ingest audio file in WAV, MP3, M4A, FLAC, OGG, or WebM format,
    normalize to mono float32, and resample to target_sr (16 kHz).

    Returns:
        tuple of (audio_samples, duration_seconds)

    Raises:
        ValueError: If audio is corrupted, empty, or silent.
    """
    path_str = str(audio_path)
    audio_data: np.ndarray | None = None

    # First attempt decoding via PyAV (supports WAV, MP3, M4A/AAC, FLAC, OGG, WebM)
    try:
        import av

        container = av.open(path_str)
        try:
            resampler = av.AudioResampler(format="fltp", layout="mono", rate=target_sr)
            frames = []
            for frame in container.decode(audio=0):
                for rf in resampler.resample(frame):
                    frames.append(rf.to_ndarray().flatten())
            if frames:
                audio_data = np.concatenate(frames).astype(np.float32)
        finally:
            container.close()
    except Exception as av_err:
        logger.debug("PyAV decode failed (%s), attempting soundfile fallback", av_err)
        try:
            data, sr = sf.read(path_str)
            if data.ndim > 1:
                data = data.mean(axis=1)
            if sr != target_sr:
                target_len = int(len(data) * target_sr / sr)
                data = np.interp(
                    np.linspace(0, len(data), target_len, endpoint=False),
                    np.arange(len(data)),
                    data,
                ).astype(np.float32)
            audio_data = data.astype(np.float32)
        except Exception as sf_err:
            raise ValueError(f"Unreadable audio content: {sf_err}") from sf_err

    if audio_data is None or len(audio_data) == 0:
        raise ValueError("Audio file is empty or contains no readable audio data.")

    # Check for silent audio (all zeros or near-zero amplitude)
    if float(np.abs(audio_data).max()) < 1e-4:
        raise ValueError("Audio is silent or contains no detectable speech.")

    duration = round(float(len(audio_data) / target_sr), 2)
    return audio_data, duration


class ASRAdapter:
    """High-accuracy Vietnamese ASR adapter using PhoASR-whisper-small."""

    def __init__(self, device: str | None = None) -> None:
        self.device = device or settings.effective_device()
        self.model_id = settings.PHOASR_MODEL_ID
        self._pipe = None

    def load(self) -> None:
        """Load PhoASR pipeline onto target device."""
        if self._pipe is None:
            logger.info("Loading PhoASR (%s) onto %s...", self.model_id, self.device)
            device_arg = 0 if self.device.startswith("cuda") else -1
            self._pipe = pipeline(
                "automatic-speech-recognition",
                model=self.model_id,
                device=device_arg,
            )
            logger.info("PhoASR ready.")

    def transcribe(self, audio_path: str | Path) -> dict[str, Any]:
        """
        Transcribe audio file into Vietnamese text.

        Returns:
            dict with 'text', 'language', and 'duration'.
        """
        self.load()
        data, duration = load_audio_file(audio_path, target_sr=16000)

        generate_kwargs = {
            "task": "transcribe",
            "language": "vi",
        }
        res = self._pipe(data, generate_kwargs=generate_kwargs)
        text = res.get("text", "").strip()

        return {
            "text": text,
            "language": "vi",
            "duration": duration,
            "word_timestamps": None,
        }

    def unload(self) -> None:
        """Free pipeline memory."""
        self._pipe = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("PhoASR unloaded.")

