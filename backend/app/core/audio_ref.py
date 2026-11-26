"""Reference-audio normalization for Pocket TTS voice cloning."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

REFERENCE_SAMPLE_RATE = 24_000
REFERENCE_MIN_DURATION_S = 3.0
REFERENCE_MAX_DURATION_S = 30.0
_SILENCE_PEAK_THRESHOLD = 1e-4


def _decode_with_av(source: Path) -> tuple[np.ndarray, int]:
    import av

    container = av.open(str(source))
    try:
        stream = next(s for s in container.streams if s.type == "audio")
        resampler = av.AudioResampler(
            format="fltp",
            layout="mono",
            rate=REFERENCE_SAMPLE_RATE,
        )
        chunks: list[np.ndarray] = []
        for frame in container.decode(stream):
            for resampled in resampler.resample(frame):
                chunks.append(resampled.to_ndarray().flatten())
        try:
            tail = resampler.resample(None)
        except Exception:  # noqa: BLE001
            tail = None
        if tail:
            for resampled in tail:
                chunks.append(resampled.to_ndarray().flatten())
    finally:
        container.close()

    if not chunks:
        raise ValueError("Reference audio contains no readable audio frames.")
    return np.concatenate(chunks).astype(np.float32), REFERENCE_SAMPLE_RATE


def _decode_with_soundfile(source: Path) -> tuple[np.ndarray, int]:
    data, sample_rate = sf.read(str(source), dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    audio = np.asarray(data, dtype=np.float32)
    if sample_rate != REFERENCE_SAMPLE_RATE:
        import librosa

        audio = librosa.resample(
            audio,
            orig_sr=sample_rate,
            target_sr=REFERENCE_SAMPLE_RATE,
        ).astype(np.float32)
    return audio, REFERENCE_SAMPLE_RATE


def normalize_reference_audio(source: str | Path) -> tuple[Path, float]:
    """Decode any supported audio file into a mono 24 kHz PCM WAV temp file."""
    source_path = Path(source)
    if not source_path.is_file():
        raise ValueError("Reference audio file is missing.")

    decoded: tuple[np.ndarray, int] | None = None
    try:
        decoded = _decode_with_av(source_path)
    except Exception:  # noqa: BLE001
        try:
            decoded = _decode_with_soundfile(source_path)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("Unsupported or corrupted reference audio.") from exc
    audio, sample_rate = decoded

    if audio.size == 0:
        raise ValueError("Reference audio contains no readable audio samples.")

    peak = float(np.max(np.abs(audio)))
    if peak < _SILENCE_PEAK_THRESHOLD:
        raise ValueError("Reference audio is silent. Please record your voice again.")
    if peak > 0:
        audio = (audio / peak) * 0.95

    max_samples = int(REFERENCE_MAX_DURATION_S * sample_rate)
    if audio.size > max_samples:
        audio = audio[:max_samples]

    duration = float(audio.size / sample_rate)
    if duration < REFERENCE_MIN_DURATION_S:
        raise ValueError(
            f"Reference audio is too short ({duration:.1f}s). "
            f"Record at least {REFERENCE_MIN_DURATION_S:.0f} seconds."
        )

    fd, output_name = tempfile.mkstemp(prefix="tts_ref_", suffix=".wav")
    os.close(fd)
    output_path = Path(output_name)
    try:
        sf.write(
            str(output_path),
            audio,
            sample_rate,
            format="WAV",
            subtype="PCM_16",
        )
    except Exception:
        output_path.unlink(missing_ok=True)
        raise

    return output_path, duration
