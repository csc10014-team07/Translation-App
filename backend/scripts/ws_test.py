#!/usr/bin/env python3
"""
Send a WAV file to the Translation-App streaming endpoint and print every event.

    pip install websockets
    python scripts/ws_test.py --wav sample.wav                       # ws://localhost:8000/ws/stream
    python scripts/ws_test.py --wav sample.wav --url ws://192.168.1.10:8000/ws/stream --odd --fast

Audio must be 16 kHz, mono, 16-bit PCM. Convert with:
    ffmpeg -i input.m4a -ar 16000 -ac 1 -sample_fmt s16 sample.wav

Checks: ready event, asr_final text, translation events, tts_audio, no error events,
connection stays open. Exit code 1 if a check fails. Paste the whole output when asking for help.
"""
import argparse
import asyncio
import json
import sys
import time
import wave

try:
    import websockets
except ImportError:
    sys.exit("Missing package: pip install websockets")

RATE, WIDTH = 16000, 2


def load_pcm(path):
    with wave.open(path, "rb") as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (RATE, 1, WIDTH):
            sys.exit("WAV must be 16000 Hz, mono, 16-bit. Convert: "
                     "ffmpeg -i in.m4a -ar 16000 -ac 1 -sample_fmt s16 sample.wav")
        return w.readframes(w.getnframes())


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", required=True)
    ap.add_argument("--url", default="ws://localhost:8000/ws/stream")
    ap.add_argument("--api-key", default="", help="appended as ?api_key= (for later API-key support)")
    ap.add_argument("--source", default="vi")
    ap.add_argument("--target", default="en")
    ap.add_argument("--chunk-ms", type=int, default=100)
    ap.add_argument("--fast", action="store_true", help="do not pace chunks in real time")
    ap.add_argument("--odd", action="store_true", help="make the first chunk odd-length (tests byte alignment)")
    ap.add_argument("--silence-s", type=float, default=1.0, help="trailing silence so the VAD ends the utterance")
    ap.add_argument("--timeout", type=float, default=120.0)
    a = ap.parse_args()

    pcm = load_pcm(a.wav) + b"\x00" * int(a.silence_s * RATE * WIDTH)
    url = a.url + (("&" if "?" in a.url else "?") + "api_key=" + a.api_key if a.api_key else "")
    step = int(RATE * WIDTH * a.chunk_ms / 1000) // 2 * 2
    t0 = time.monotonic()
    events, errors, closed = [], [], []

    def log(kind, detail=""):
        print(f"{time.monotonic() - t0:7.2f}s  {kind:<14} {detail}")

    async with websockets.connect(url, max_size=64 * 1024 * 1024) as ws:
        async def receiver():
            try:
                async for raw in ws:
                    if isinstance(raw, bytes):
                        log("binary", f"{len(raw)} bytes")
                        continue
                    msg = json.loads(raw)
                    kind = msg.get("type") or msg.get("event") or "?"
                    events.append(msg)
                    text = msg.get("text") or msg.get("message") or ""
                    extra = " (audio)" if "audio" in kind or msg.get("audio_base64") else ""
                    log(kind, (str(text)[:90] + extra) if (text or extra) else "")
                    if kind == "error":
                        errors.append(msg)
                    if kind == "stopped":
                        return
            except websockets.ConnectionClosed:
                pass
            # Reached when the server closed the socket before sending "stopped".
            closed.append(ws.close_code)
            log("CLOSED", f"by server, code={ws.close_code}")

        async def sender():
            try:
                await ws.send(json.dumps({"action": "start", "source_lang": a.source, "target_lang": a.target,
                                          "context_preset": "", "custom_context": "", "clone_voice": False}))
                pos, first = 0, True
                while pos < len(pcm):
                    size = step + 1 if (a.odd and first) else step
                    await ws.send(pcm[pos:pos + size])
                    pos, first = pos + size, False
                    await asyncio.sleep(0 if a.fast else a.chunk_ms / 1000)
                log("sent-all", f"{len(pcm)} bytes")
                await ws.send(json.dumps({"action": "stop"}))
            except websockets.ConnectionClosed:
                pass  # the receiver reports the close

        send_task = asyncio.create_task(sender())
        try:
            await asyncio.wait_for(receiver(), timeout=a.timeout)
        except asyncio.TimeoutError:
            log("TIMEOUT", f"no 'stopped' within {a.timeout:.0f}s")
        finally:
            send_task.cancel()

    def has(name):
        return any((m.get("type") or m.get("event")) == name for m in events)

    asr = next((m.get("text") for m in reversed(events) if (m.get("type") or m.get("event")) == "asr_final"), "")
    checks = [
        ("ready event", has("ready")),
        ("asr_final with text", bool(str(asr).strip())),
        ("translation event", has("trans_final") or has("trans_delta")),
        ("tts_audio event (optional)", has("tts_audio") or None),
        ("no error events", not errors),
        ("connection not dropped early", not closed),
        ("stopped event", has("stopped")),
    ]
    print()
    bad = 0
    for name, ok in checks:
        label = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
        bad += ok is False
        print(f"[{label}] {name}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    asyncio.run(main())