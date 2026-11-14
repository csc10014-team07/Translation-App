#!/usr/bin/env python3
"""
Smoke test for the Translation-App backend. Standard library only.

Usage (server already running):
    python scripts/smoke_test.py --base http://localhost:8000
    python scripts/smoke_test.py --base http://192.168.1.10:8000 --audio my_voice.m4a

Prints one PASS/FAIL line per check with latency. Exit code 1 if any FAIL.
Paste the whole output to the person helping you debug.
"""
import argparse
import base64
import io
import json
import math
import struct
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import wave

RESULTS = []


def http(method, url, body=None, headers=None, timeout=180):
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data, status = r.read(), r.status
    except urllib.error.HTTPError as e:
        data, status = e.read(), e.code
    except Exception as e:  # connection refused, timeout, ...
        return None, f"{type(e).__name__}: {e}", time.monotonic() - t0
    return status, data, time.monotonic() - t0


def as_json(data):
    try:
        return json.loads(data)
    except Exception:
        return None


def record(name, ok, secs, note=""):
    RESULTS.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name:<46} {secs:6.1f}s  {note}")


def post_json(url, payload):
    return http("POST", url, json.dumps(payload).encode(), {"Content-Type": "application/json"})


def post_form(url, fields):
    return http("POST", url, urllib.parse.urlencode(fields).encode(),
                {"Content-Type": "application/x-www-form-urlencoded"})


def post_file(url, field, filename, content, mime, extra=None):
    boundary = uuid.uuid4().hex
    parts = []
    for k, v in (extra or {}).items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; '
                  f'filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n').encode() + content + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return http("POST", url, b"".join(parts),
                {"Content-Type": f"multipart/form-data; boundary={boundary}"})


def sine_wav(seconds=2.0, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 220 * i / rate)))
                          for i in range(int(seconds * rate)))
        w.writeframes(frames)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--prefix", default="/api")
    ap.add_argument("--audio", help="optional real recording (e.g. a .m4a from the phone)")
    ap.add_argument("--save-audio", action="store_true", help="save TTS results as smoke_tts_*.wav")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--any-engine", action="store_true",
                    help="do not fail when the translation engine is not the local TranslateGemma model")
    a = ap.parse_args()
    base, api = a.base.rstrip("/"), a.base.rstrip("/") + a.prefix

    # 1. health and metrics
    s, d, t = http("GET", f"{base}/health", timeout=a.timeout)
    j = as_json(d) if isinstance(d, bytes) else None
    record("GET /health", s == 200 and bool(j), t, str(d)[:80] if s != 200 else f"keys={list(j or {})}")
    if s is None:
        print("\nCannot reach the server. Is uvicorn running and is the URL right?")
        sys.exit(1)
    s, d, t = http("GET", f"{api}/metrics", timeout=a.timeout)
    j = as_json(d) if isinstance(d, bytes) else None
    note = ""
    if isinstance(j, dict):
        note = "in_vram=" + str(j.get("models") or j.get("in_vram") or j.get("status") or "?")[:70]
    record("GET /metrics", s == 200, t, note)

    # 2. translate
    s, d, t = post_json(f"{api}/translate", {"text": "Hôm nay trời đẹp quá.", "target_language": "en"})
    j = as_json(d) if isinstance(d, bytes) else None
    out = (j or {}).get("translated_text", "")
    engine = (j or {}).get("engine_used")
    local = engine is None or "translategemma" in str(engine).lower() or a.any_engine
    note = (repr(out[:60]) + f" engine={engine or '?'}") if s == 200 else str(d)[:100]
    if s == 200 and not local:
        note += "  <-- NOT the local model (online/other fallback)"
    record("translate vi->en (local model)", s == 200 and bool(out.strip()) and local, t, note)
    s, d, t = post_json(f"{api}/translate", {"text": "Mày đi đâu đấy?", "target_language": "en",
                                              "context": "casual talk between close friends"})
    j = as_json(d) if isinstance(d, bytes) else None
    out = (j or {}).get("translated_text", "")
    engine = (j or {}).get("engine_used")
    local = engine is None or "translategemma" in str(engine).lower() or a.any_engine
    note = (repr(out[:60]) + f" engine={engine or '?'}") if s == 200 else str(d)[:100]
    if s == 200 and not local:
        note += "  <-- NOT the local model (online/other fallback)"
    record("translate with context (local model)", s == 200 and bool(out.strip()) and local, t, note)
    s, d, t = post_json(f"{api}/translate", {"text": "   ", "target_language": "en"})
    record("translate empty text -> 422", s == 422, t, f"got {s}")

    # 3. TTS
    for lang in ("en", "fr"):
        s, d, t = post_form(f"{api}/tts", {"text": "Hello, this is a test.", "language": lang})
        j = as_json(d) if isinstance(d, bytes) else None
        ok = s == 200 and bool((j or {}).get("audio_base64"))
        note = f"engine={(j or {}).get('engine', '-')} fmt={(j or {}).get('format', '-')}" if ok else str(d)[:100]
        record(f"tts {lang}", ok, t, note)
        if ok and a.save_audio:
            with open(f"smoke_tts_{lang}.{(j or {}).get('format', 'wav')}", "wb") as f:
                f.write(base64.b64decode(j["audio_base64"]))
    for lang in ("zh", "vi"):
        s, d, t = post_form(f"{api}/tts", {"text": "Xin chao", "language": lang})
        record(f"tts {lang} (400 now; 200 if edge-tts added)", s in (400, 200), t, f"got {s}")

    # 4. ASR
    s, d, t = post_file(f"{api}/asr", "audio", "synthetic.wav", sine_wav(), "audio/wav")
    record("asr synthetic wav (pipeline only)", s == 200, t, str(d)[:100] if s != 200 else "ok (text is meaningless)")
    if a.audio:
        ext = a.audio.rsplit(".", 1)[-1].lower()
        mime = {"m4a": "audio/mp4", "mp3": "audio/mpeg", "wav": "audio/wav"}.get(ext, "application/octet-stream")
        with open(a.audio, "rb") as f:
            s, d, t = post_file(f"{api}/asr", "audio", f"recording.{ext}", f.read(), mime)
        j = as_json(d) if isinstance(d, bytes) else None
        record(f"asr real file (.{ext})", s == 200, t, repr(str((j or {}).get('text', ''))[:70]) if s == 200 else str(d)[:120])
    s, d, t = post_file(f"{api}/asr", "audio", "x.txt", b"hello", "text/plain")
    record("asr bad extension -> 415/422", s in (415, 422, 400), t, f"got {s}")

    # 5. concurrency: two translations at once
    out = [None, None]

    def worker(i):
        out[i] = post_json(f"{api}/translate", {"text": f"Câu thử số {i + 1}: trời hôm nay đẹp.", "target_language": "en"})

    t0 = time.monotonic()
    th = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for x in th:
        x.start()
    for x in th:
        x.join()
    ok = all(r and r[0] == 200 for r in out)
    record("2 translations at once", ok, time.monotonic() - t0, "" if ok else str([r[0] for r in out]))

    failed = RESULTS.count(False)
    print(f"\n{len(RESULTS) - failed}/{len(RESULTS)} passed.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()