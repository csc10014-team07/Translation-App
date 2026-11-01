"""Comprehensive Integration and Contract Tests for Ticket 04: Hybrid TTS & Voice Cloning."""
import base64
import io
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pytest
import soundfile as sf
import torch
from app.main import app
from starlette.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _create_sample_wav(duration_s: float = 2.0, sr: int = 16000) -> bytes:
    """Generate a valid in-memory PCM WAV audio file for testing."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    # Generate a simple harmonic signal mimicking human speech range (220 Hz fundamental)
    signal = 0.5 * np.sin(2 * np.pi * 220 * t) + 0.25 * np.sin(2 * np.pi * 440 * t)
    buf = io.BytesIO()
    sf.write(buf, signal.astype(np.float32), sr, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return buf.read()


def test_english_tts_form(client):
    """Test standard English speech synthesis via multipart form data."""
    form_data = {
        "text": "Welcome to our context-aware translation application.",
        "language": "English",
    }
    resp = client.post("/api/tts", data=form_data)
    assert resp.status_code == 200, f"Error {resp.status_code}: {resp.text}"
    data = resp.json()

    assert "audio_base64" in data
    assert data["format"] == "wav"
    assert data["sample_rate"] > 0
    assert data.get("engine") in ("edge_tts", "pocket_tts")
    assert "elapsed_ms" in data

    audio_bytes = base64.b64decode(data["audio_base64"])
    audio_arr, sr = sf.read(io.BytesIO(audio_bytes))
    dur = len(audio_arr) / sr
    assert dur > 0.5, f"Synthesized audio duration should be > 0.5s, got {dur:.2f}s"
    print(f"✅ English TTS output generated: {dur:.2f}s audio ({data['engine']})")


def test_vietnamese_tts_edge(client):
    """Test Vietnamese speech synthesis natively handled by Edge-TTS."""
    form_data = {
        "text": "Xin chào, hệ thống dịch thuật đã sẵn sàng phục vụ bạn.",
        "language": "Vietnamese",
    }
    resp = client.post("/api/tts", data=form_data)
    assert resp.status_code == 200, f"Error {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data["engine"] == "edge_tts"
    assert data["format"] == "wav"
    assert data["sample_rate"] == 24000

    audio_bytes = base64.b64decode(data["audio_base64"])
    audio_arr, sr = sf.read(io.BytesIO(audio_bytes))
    dur = len(audio_arr) / sr
    assert dur > 0.5
    print(f"✅ Vietnamese TTS output generated: {dur:.2f}s audio ({data['engine']})")


def test_voice_cloning_with_reference_audio(client):
    """Test zero-shot cross-lingual voice cloning using Pocket TTS on CPU when reference audio is provided."""
    wav_bytes = _create_sample_wav(duration_s=2.5, sr=16000)

    files = {
        "reference_audio": ("speaker_sample.wav", wav_bytes, "audio/wav"),
    }
    form_data = {
        "text": "This audio is generated using personal voice cloning on CPU.",
        "language": "English",
        "reference_text": "Sample speech reference for voice cloning timbre.",
    }

    resp = client.post("/api/tts", data=form_data, files=files)
    assert resp.status_code == 200, f"Error {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data["engine"] == "pocket_tts"
    assert data["format"] == "wav"
    assert data["sample_rate"] == 24000

    audio_bytes = base64.b64decode(data["audio_base64"])
    audio_arr, sr = sf.read(io.BytesIO(audio_bytes))
    dur = len(audio_arr) / sr
    assert dur > 0.5, f"Synthesized audio duration should be > 0.5s, got {dur:.2f}s"
    print(f"✅ Voice cloning TTS output generated: {dur:.2f}s audio ({data['engine']})")


def test_tts_json_payload(client):
    """Test POST /api/tts with JSON body and target_language alias."""
    payload = {
        "text": "Testing JSON payload submission for speech synthesis.",
        "target_language": "English",
        "voice_style": "female",
    }
    resp = client.post("/api/tts", json=payload)
    assert resp.status_code == 200, f"Error {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "audio_base64" in data
    assert data["format"] == "wav"
    print(f"✅ TTS JSON payload handled successfully: {data['engine']}")


def test_voice_style_selection(client):
    """Test voice style selection (male vs female neural voices)."""
    form_data = {
        "text": "Chào buổi sáng, chúc bạn một ngày làm việc hiệu quả.",
        "language": "vi",
        "voice_style": "male",
    }
    resp = client.post("/api/tts", data=form_data)
    assert resp.status_code == 200, f"Error {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["engine"] == "edge_tts"
    print("✅ Vietnamese male voice selection verified.")


def test_tts_validation_empty_text(client):
    """Test that empty or whitespace-only text returns HTTP 422."""
    resp = client.post("/api/tts", data={"text": "   ", "language": "English"})
    assert resp.status_code == 422, f"Expected 422 for empty text, got {resp.status_code}"


def test_tts_validation_missing_language(client):
    """Test that missing language and target_language returns HTTP 422."""
    resp = client.post("/api/tts", data={"text": "Hello world"})
    assert resp.status_code == 422, f"Expected 422 for missing language, got {resp.status_code}"


def test_tts_unsupported_audio_format(client):
    """Test that uploading an unsupported audio container for reference_audio returns HTTP 415."""
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00"
    files = {
        "reference_audio": ("malicious.exe", fake_exe, "application/octet-stream"),
    }
    resp = client.post(
        "/api/tts",
        data={"text": "Hello world", "language": "English"},
        files=files,
    )
    assert resp.status_code == 415, f"Expected 415 for unsupported format, got {resp.status_code}"


def test_zero_vram_overhead(client):
    """Verify that TTS synthesis operates with 0MB GPU VRAM overhead."""
    if not torch.cuda.is_available():
        pytest.skip("CUDA not available, testing on CPU natively.")

    vram_before = torch.cuda.memory_allocated()

    form_data = {
        "text": "Verifying that text to speech does not allocate any GPU VRAM.",
        "language": "English",
    }
    resp = client.post("/api/tts", data=form_data)
    assert resp.status_code == 200

    vram_after = torch.cuda.memory_allocated()
    diff_mb = (vram_after - vram_before) / (1024 * 1024)
    assert diff_mb == 0.0, f"TTS should consume 0MB GPU VRAM, but allocated {diff_mb:.2f} MB"
    print(f"✅ Zero GPU VRAM overhead confirmed: {diff_mb:.2f} MB added.")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
