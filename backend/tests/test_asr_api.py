"""Integration test for Ticket 03: Vietnamese Speech Recognition (PhoASR)."""
import io
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.main import app
from starlette.testclient import TestClient


def test_asr_endpoint():
    client = TestClient(app)

    # 1. Test valid Vietnamese audio transcription
    audio_path = Path(__file__).parent.parent.parent.parent / "benchmarks" / "output_audio" / "tts_vi_HoaiMyNeural.mp3"
    assert audio_path.exists(), f"Audio file not found at {audio_path}"

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    files = {"audio": ("tts_vi_HoaiMyNeural.mp3", audio_bytes, "audio/mpeg")}
    resp = client.post("/api/asr", files=files)
    assert resp.status_code == 200, f"Error {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "text" in data
    assert len(data["text"]) > 0
    assert "elapsed_ms" in data
    assert data["elapsed_ms"] >= 0
    assert "language_detected" in data
    assert data["language_detected"] == "vi"
    print(f"✅ PhoASR transcription output: \"{data['text']}\"")
    print(f"   Detected language: {data.get('language_detected')}")
    print(f"   Elapsed ms: {data.get('elapsed_ms')}")

    # 2. Test Unsupported file type (HTTP 415)
    files_unsupported = {"audio": ("test.txt", b"plain text is not audio", "text/plain")}
    resp_unsupported = client.post("/api/asr", files=files_unsupported)
    assert resp_unsupported.status_code == 415
    print("✅ Unsupported audio format correctly rejected with HTTP 415.")

    # 3. Test Empty audio validation (HTTP 422)
    files_empty = {"audio": ("empty.wav", b"", "audio/wav")}
    resp_empty = client.post("/api/asr", files=files_empty)
    assert resp_empty.status_code == 422
    print("✅ Empty audio correctly rejected with HTTP 422.")

    # 4. Test Silent audio validation (HTTP 422)
    import numpy as np
    import soundfile as sf
    silence_buf = io.BytesIO()
    sf.write(silence_buf, np.zeros(16000, dtype=np.float32), 16000, format="WAV")
    silence_bytes = silence_buf.getvalue()
    resp_silent = client.post("/api/asr", files={"audio": ("silent.wav", silence_bytes, "audio/wav")})
    assert resp_silent.status_code == 422, f"Expected 422 for silent audio, got {resp_silent.status_code}"
    print("✅ Silent audio correctly rejected with HTTP 422.")

    # 5. Test Corrupted audio validation (HTTP 422)
    corrupted_bytes = b"RIFF" + b"\xff" * 300
    resp_corrupt = client.post("/api/asr", files={"audio": ("corrupt.wav", corrupted_bytes, "audio/wav")})
    assert resp_corrupt.status_code == 422, f"Expected 422 for corrupted audio, got {resp_corrupt.status_code}"
    print("✅ Corrupted audio correctly rejected with HTTP 422.")

    # 6. Test M4A audio transcription
    m4a_path = Path(__file__).parent.parent.parent.parent / "benchmarks" / "output_audio" / "sample.m4a"
    if m4a_path.exists():
        with open(m4a_path, "rb") as f:
            m4a_bytes = f.read()
        resp_m4a = client.post("/api/asr", files={"audio": ("sample.m4a", m4a_bytes, "audio/mp4")})
        assert resp_m4a.status_code == 200, f"Error {resp_m4a.status_code}: {resp_m4a.text}"
        m4a_data = resp_m4a.json()
        assert len(m4a_data["text"]) > 0
        assert "elapsed_ms" in m4a_data
        print(f"✅ PhoASR M4A transcription output: \"{m4a_data['text']}\"")

    # 7. Test WAV audio transcription
    wav_path = Path(__file__).parent.parent.parent.parent / "benchmarks" / "output_audio" / "sample.wav"
    if not wav_path.exists() and audio_path.exists():
        import soundfile as sf
        from app.models.asr_adapter import load_audio_file
        data_16k, _ = load_audio_file(audio_path, target_sr=16000)
        sf.write(str(wav_path), data_16k, 16000, format="WAV")

    if wav_path.exists():
        with open(wav_path, "rb") as f:
            wav_bytes = f.read()
        resp_wav = client.post("/api/asr", files={"audio": ("sample.wav", wav_bytes, "audio/wav")})
        assert resp_wav.status_code == 200, f"Error {resp_wav.status_code}: {resp_wav.text}"
        wav_data = resp_wav.json()
        assert len(wav_data["text"]) > 0
        assert "elapsed_ms" in wav_data
        print(f"✅ PhoASR WAV transcription output: \"{wav_data['text']}\"")

    print("\n🎉 ALL TICKET 03 TESTS PASSED!")

if __name__ == "__main__":
    test_asr_endpoint()
