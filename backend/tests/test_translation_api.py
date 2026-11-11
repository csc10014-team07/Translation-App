"""Integration test for Ticket 02: Context-Aware Translation API."""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from unittest.mock import patch

from app.main import app
from app.models.translation_adapter import TranslationAdapter
from starlette.testclient import TestClient


def test_translate_endpoints():
    client = TestClient(app)

    def fake_translate(text, target_language, source_language=None, context=None, context_preset=None, custom_context=""):
        return f"Translated: {text}", "translategemma-4b"

    with patch.object(TranslationAdapter, "translate_with_engine", side_effect=fake_translate):
        # 1. Test Casual / Friendly Translation with new context_preset field
        payload_casual = {
            "text": "Chào bạn, hôm nay thế nào?",
            "target_language": "English",
            "source_language": "vi",
            "context_preset": "Friendly",
        }
        resp1 = client.post("/api/translate", json=payload_casual)
        assert resp1.status_code == 200, f"Error {resp1.status_code}: {resp1.text}"
        data1 = resp1.json()
        assert "translated_text" in data1
        assert data1["source_language"] == "vi"
        assert data1["target_language"] == "English"
        assert "engine_used" in data1, "Response missing engine_used"
        assert "elapsed_ms" in data1, "Response missing elapsed_ms"
        assert isinstance(data1["elapsed_ms"], (int, float))
        assert data1["elapsed_ms"] > 0
        print(f"✅ Casual Translation output: \"{data1['translated_text']}\" (engine: {data1['engine_used']}, elapsed: {data1['elapsed_ms']:.1f}ms)")

        # 2. Test Technical IT Translation with custom_context
        payload_tech = {
            "text": "Cần refactor lại API và deploy lên server ngay chiều nay.",
            "target_language": "English",
            "context_preset": "Technical",
            "custom_context": "Production incident review",
        }
        resp2 = client.post("/api/translate", json=payload_tech)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert "engine_used" in data2
        assert "elapsed_ms" in data2
        print(f"✅ Technical Translation output: \"{data2['translated_text']}\" (engine: {data2['engine_used']})")

        # 3. Test Backward Compatibility with legacy context field
        payload_legacy = {
            "text": "Xin chào thế giới",
            "target_language": "English",
            "context": "Formal",
        }
        resp3 = client.post("/api/translate", json=payload_legacy)
        assert resp3.status_code == 200
        data3 = resp3.json()
        assert "engine_used" in data3
    assert "elapsed_ms" in data3

    # 4. Test Empty / Whitespace text validation
    resp_empty = client.post("/api/translate", json={"text": "", "target_language": "English"})
    assert resp_empty.status_code == 422
    resp_whitespace = client.post("/api/translate", json={"text": "   ", "target_language": "English"})
    assert resp_whitespace.status_code == 422

    # 5. Test Empty / Whitespace target_language validation
    resp_empty_lang = client.post("/api/translate", json={"text": "Hello", "target_language": ""})
    assert resp_empty_lang.status_code == 422
    resp_ws_lang = client.post("/api/translate", json={"text": "Hello", "target_language": "  "})
    assert resp_ws_lang.status_code == 422

    print("\n🎉 ALL TICKET 02 INTEGRATION TESTS PASSED!")

if __name__ == "__main__":
    test_translate_endpoints()

