"""ASR adapter wrapping PhoASR-Whisper-small via HuggingFace Transformers."""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

logger = logging.getLogger(__name__)

_SAMPLE_RATE = 16_000  # Whisper expects 16 kHz input


class ASRAdapter:
    """
    Thin wrapper around ``WhisperProcessor`` + ``WhisperForConditionalGeneration``
    for Vietnamese speech recognition using PhoASR-whisper-small.

    Lifecycle
    ---------
    1. Call :meth:`load` once at startup (device = CUDA).
    2. Use :meth:`transcribe` for inference — the model stays in VRAM permanently.
    3. Inference calls are protected by a lock for thread-safety.
    """

    def __init__(self) -> None:
        self._processor: WhisperProcessor | None = None
        self._model: WhisperForConditionalGeneration | None = None
        self._device: str = "cpu"
        self._loaded: bool = False
        self._lock = threading.Lock()

    # ── Public API ─────────────────────────────────────────────────────────

    def load(self, model_id: str, device: str) -> None:
        """
        Load PhoASR Whisper model to *device* in FP16.

        Args:
            model_id: HuggingFace model ID, e.g. ``"Qualcomm-AI-Research/PhoASR-whisper-small"``.
            device:   ``"cuda"`` or ``"cpu"``.
        """
        logger.info("Loading ASR model '%s' to %s …", model_id, device)
        t0 = time.monotonic()

        self._processor = WhisperProcessor.from_pretrained(model_id)
        self._model = WhisperForConditionalGeneration.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        )
        self._model.eval()
        self._model.to(device)
        self._device = device
        self._loaded = True

        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info("ASR model loaded in %.0f ms", elapsed_ms)

    def transcribe(self, audio_path: str) -> dict:
        """
        Transcribe a Vietnamese audio file.

        The audio is resampled to 16 kHz if necessary.  Language is forced
        to Vietnamese (``vi``) so the model never auto-detects the wrong
        language.

        Args:
            audio_path: Absolute or relative path to the audio file.

        Returns:
            A dict with keys:
            - ``text``            – transcribed string
            - ``language``        – always ``"vi"``
            - ``word_timestamps`` – list of word-level timing dicts (may be empty)

        Raises:
            RuntimeError: If the model has not been loaded yet.
            FileNotFoundError: If *audio_path* does not exist.
        """
        if not self._loaded or self._model is None or self._processor is None:
            raise RuntimeError("ASRAdapter.load() must be called before transcribe().")

        audio_path_obj = Path(audio_path)
        if not audio_path_obj.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.debug("Transcribing '%s' …", audio_path)

        with self._lock:
            t0 = time.monotonic()

            # ── Load and resample ──────────────────────────────────────────────
            try:
                audio, orig_sr = librosa.load(str(audio_path_obj), sr=None, mono=True)
            except Exception as exc:
                raise ValueError(f"Failed to load audio '{audio_path}': {exc}") from exc

            if orig_sr != _SAMPLE_RATE:
                audio = librosa.resample(audio, orig_sr=orig_sr, target_sr=_SAMPLE_RATE)

            # ── Feature extraction ─────────────────────────────────────────────
            inputs = self._processor(
                audio,
                sampling_rate=_SAMPLE_RATE,
                return_tensors="pt",
            )
            input_features = inputs.input_features.to(
                self._device,
                dtype=torch.float16 if self._device == "cuda" else torch.float32,
            )

            # ── Forced Vietnamese decoding ─────────────────────────────────────
            forced_decoder_ids = self._processor.get_decoder_prompt_ids(
                language="vi", task="transcribe"
            )

            with torch.no_grad():
                predicted_ids = self._model.generate(
                    input_features,
                    forced_decoder_ids=forced_decoder_ids,
                )

            text: str = self._processor.batch_decode(
                predicted_ids, skip_special_tokens=True
            )[0].strip()

            elapsed_ms = (time.monotonic() - t0) * 1000
            logger.info("Transcription completed in %.0f ms, text length=%d", elapsed_ms, len(text))

            return {
                "text": text,
                "language": "vi",
                "word_timestamps": [],  # full timestamp support requires return_timestamps=True
            }

    # ── VRAM lifecycle ─────────────────────────────────────────────────────

    def unload(self) -> None:
        """Free the model and clear CUDA cache."""
        logger.info("Unloading ASR model...")
        if self._model is not None:
            del self._model
            self._model = None
        if self._processor is not None:
            del self._processor
            self._processor = None
        self._loaded = False
        torch.cuda.empty_cache()
        logger.info("ASR model unloaded.")

    def unload_to_cpu(self) -> None:
        """Move model weights to CPU RAM (keeps them in Python for fast reload)."""
        if self._model is not None and self._device != "cpu":
            logger.info("Moving ASR model to CPU …")
            self._model.to("cpu")
            self._device = "cpu"
            torch.cuda.empty_cache()

    def load_to_gpu(self, device: str = "cuda") -> None:
        """Move model weights back to GPU."""
        if self._model is not None and self._device != device:
            logger.info("Moving ASR model to %s …", device)
            self._model.to(
                device,
                dtype=torch.float16 if device == "cuda" else torch.float32,
            )
            self._device = device

    @property
    def is_loaded(self) -> bool:
        """True if the model weights have been loaded (regardless of device)."""
        return self._loaded
