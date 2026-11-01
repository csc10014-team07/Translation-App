"""Integration test for Ticket 06: Real-Time Streaming WebSocket Pipeline."""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import soundfile as sf
from app.main import app
from starlette.testclient import TestClient


def test_websocket_streaming_pipeline():
    client = TestClient(app)

    print("--- 1. Testing WebSocket Handshake & Direct Text Streaming ---")
    with client.websocket_connect("/ws/stream") as ws:
        # Step 1: Initial Handshake
        init_msg = ws.receive_json()
        assert init_msg["type"] == "ready"
        assert init_msg.get("event") == "ready"
        print(f"✅ Handshake received: {init_msg}")

        # Step 2: Configure session
        ws.send_json({
            "action": "start",
            "source_lang": "vi",
            "target_lang": "en",
            "context_preset": "Casual",
            "custom_context": "At a friendly coffee shop",
            "clone_voice": False,
        })
        cfg_msg = ws.receive_json()
        assert cfg_msg["type"] == "config_updated"
        assert cfg_msg.get("event") == "config_updated"
        print(f"✅ Config updated: {cfg_msg['config']}")

        # Step 3: Test direct text translation & token streaming
        ws.send_json({
            "action": "translate_text",
            "text": "Cho tôi một ly cà phê sữa đá.",
        })

        asr_msg = ws.receive_json()
        assert asr_msg["type"] == "asr_final"
        assert asr_msg.get("event") == "asr_final"
        print(f"✅ Input text acknowledged: \"{asr_msg['text']}\"")

        # Streamed token deltas
        deltas = []
        while True:
            msg = ws.receive_json()
            if msg["type"] == "trans_start":
                assert msg.get("event") == "trans_start"
                continue
            elif msg["type"] == "trans_delta":
                assert msg.get("event") == "trans_delta"
                assert "delta" in msg and "token" in msg
                deltas.append(msg["delta"])
            elif msg["type"] == "trans_final":
                assert msg.get("event") == "trans_final"
                print(f"✅ Token streaming completed. Full translation: \"{msg['text']}\"")
                print(f"   Received {len(deltas)} progressive tokens.")
                break

        # TTS Audio
        tts_msg = ws.receive_json()
        assert tts_msg["type"] == "tts_audio"
        assert tts_msg.get("event") == "tts_audio"
        assert len(tts_msg["audio_b64"]) > 100
        print(f"✅ TTS Audio received ({tts_msg['format']}) - {len(tts_msg['audio_b64'])} bytes.")

        # Step 4: Test PCM Audio Frame Streaming with VAD
        print("\n--- 2. Testing Binary 16kHz PCM Audio Streaming with VAD ---")
        audio_path = Path(__file__).parent.parent.parent.parent / "benchmarks" / "output_audio" / "tts_vi_HoaiMyNeural.mp3"
        data, sr = sf.read(str(audio_path))
        if data.ndim > 1:
            data = data.mean(axis=1)
        if sr != 16000:
            target_samples = int(len(data) * 16000 / sr)
            data = np.interp(
                np.linspace(0, len(data), target_samples, endpoint=False),
                np.arange(len(data)),
                data,
            )

        # Convert to 16-bit PCM bytes
        pcm_int16 = (np.clip(data, -1.0, 1.0) * 32767).astype(np.int16)
        raw_pcm_bytes = pcm_int16.tobytes()

        # Stream in 200ms chunks (6400 bytes per chunk at 16kHz 16-bit)
        chunk_size = 6400
        for i in range(0, len(raw_pcm_bytes), chunk_size):
            chunk = raw_pcm_bytes[i : i + chunk_size]
            ws.send_bytes(chunk)

        # Send 500ms of silence to trigger VAD pause boundary (16000 samples/sec * 2 bytes = 32000 bytes/sec -> 16000 bytes)
        silence_chunk = (np.zeros(8000, dtype=np.int16)).tobytes()
        ws.send_bytes(silence_chunk)

        # Receive VAD-triggered events (asr_interim and asr_final)
        first_event = ws.receive_json()
        if first_event["type"] == "asr_interim":
            assert first_event.get("event") == "asr_interim"
            print(f"✅ VAD interim speech activity detected: {first_event}")
            vad_asr_msg = ws.receive_json()
        else:
            vad_asr_msg = first_event

        assert vad_asr_msg["type"] == "asr_final"
        assert vad_asr_msg.get("event") == "asr_final"
        print(f"✅ VAD ASR transcribed: \"{vad_asr_msg['text']}\" in {vad_asr_msg.get('elapsed_ms')}ms")

        # Receive trans_start and deltas
        stream_started = ws.receive_json()
        assert stream_started["type"] == "trans_start"
        assert stream_started.get("event") == "trans_start"

        stream_deltas = []
        while True:
            m = ws.receive_json()
            if m["type"] == "trans_delta":
                assert m.get("event") == "trans_delta"
                assert "delta" in m and "token" in m
                stream_deltas.append(m["delta"])
            elif m["type"] == "trans_final":
                assert m.get("event") == "trans_final"
                print(f"✅ Live Translation: \"{m['text']}\"")
                break

        # Receive TTS
        vad_tts_msg = ws.receive_json()
        assert vad_tts_msg["type"] == "tts_audio"
        assert vad_tts_msg.get("event") == "tts_audio"
        print(f"✅ Live TTS Audio received: format={vad_tts_msg['format']}")

        # Clean Stop and drain remaining stream events
        ws.send_json({"action": "stop"})
        while True:
            msg = ws.receive_json()
            print(f"Received stream event: {msg.get('type')}")
            if msg.get("type") == "stopped":
                assert msg.get("event") == "stopped"
                break
        print("✅ WebSocket session stopped cleanly.")

    print("\n🎉 ALL TICKET 06 REAL-TIME STREAMING TESTS PASSED!")

if __name__ == "__main__":
    test_websocket_streaming_pipeline()
