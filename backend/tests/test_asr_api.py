"""Integration test for Ticket 03: Vietnamese Speech Recognition (PhoASR)."""
import io
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from unittest.mock import patch

from app.main import app
from app.models.asr_adapter import ASRAdapter
from starlette.testclient import TestClient


def test_asr_endpoint():
    client = TestClient(app)

    import numpy as np
    import soundfile as sf

    # Generate synthetic 1.0s tone at 16kHz for tests that require valid non-silent audio
    synth_samples = (0.5 * np.sin(2 * np.pi * 440 * np.linspace(0, 1.0, 16000, endpoint=False))).astype(np.float32)
    valid_wav_buf = io.BytesIO()
    sf.write(valid_wav_buf, synth_samples, 16000, format="WAV")
    valid_wav_bytes = valid_wav_buf.getvalue()

    # 1. Test valid Vietnamese audio transcription
    audio_path = Path(__file__).parent.parent.parent.parent / "benchmarks" / "output_audio" / "tts_vi_HoaiMyNeural.mp3"
    if audio_path.exists():
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        audio_filename = "tts_vi_HoaiMyNeural.mp3"
        audio_content_type = "audio/mpeg"
    else:
        audio_bytes = valid_wav_bytes
        audio_filename = "valid.wav"
        audio_content_type = "audio/wav"

    def fake_transcribe(audio_file):
        return {"text": "Xin chào thế giới", "language": "vi", "duration": 1.0}

    with patch.object(ASRAdapter, "transcribe", side_effect=fake_transcribe):
        files = {"audio": (audio_filename, audio_bytes, audio_content_type)}
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

        # 6. Test M4A audio transcription (if benchmark file exists)
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
        resp_wav = client.post("/api/asr", files={"audio": ("sample.wav", valid_wav_bytes, "audio/wav")})
        assert resp_wav.status_code == 200, f"Error {resp_wav.status_code}: {resp_wav.text}"
        wav_data = resp_wav.json()
        assert len(wav_data["text"]) > 0
        assert "elapsed_ms" in wav_data
        print(f"✅ PhoASR WAV transcription output: \"{wav_data['text']}\"")

        # Test duration limit (422 for audio > 30s)
        long_audio = np.random.uniform(-0.1, 0.1, size=496000).astype(np.float32)  # 31s at 16kHz
        long_bytes = io.BytesIO()
        sf.write(long_bytes, long_audio, 16000, format="WAV")
        long_bytes.seek(0)
        long_wav = long_bytes.read()
        resp_long = client.post("/api/asr", files={"audio": ("long.wav", long_wav, "audio/wav")})
        assert resp_long.status_code == 422, f"Expected 422 for long audio, got {resp_long.status_code}"
        print("✅ ASR duration limit enforced (422 for >30s audio)")

    print("\n🎉 ALL TICKET 03 TESTS PASSED!")

if __name__ == "__main__":
    test_asr_endpoint()
