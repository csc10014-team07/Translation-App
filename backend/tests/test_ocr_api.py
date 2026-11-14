"""Integration tests for Seam 1: POST /api/ocr Two-Stage Multimodal Image Translation."""
from __future__ import annotations

import io
from unittest.mock import patch

from app.main import app
from PIL import Image, ImageDraw
from starlette.testclient import TestClient

client = TestClient(app)


def test_ocr_two_stage_vietnamese_menu():
    """Test OCR extraction of Vietnamese menu and translation to English."""
    img = Image.new("RGB", (600, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((30, 30), "QUAN CA PHE SAI GON", fill=(0, 0, 0))
    draw.text((30, 80), "Ca phe sua da dac biet: 35.000 VND", fill=(0, 0, 0))
    draw.text((30, 130), "Tra dao cam sa: 45.000 VND", fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    files = {"image": ("menu.png", buf.getvalue(), "image/png")}
    data = {"target_language": "en", "context_preset": "Travel"}
    with patch("app.models.translation_adapter.TranslationAdapter.translate", return_value="Coffee with milk and ice"):
        resp = client.post("/api/ocr", files=files, data=data)

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()

    assert "extracted_text" in body
    assert len(body["extracted_text"]) > 0
    assert "detected_language" in body
    assert "target_language" in body
    assert body["target_language"] == "en"
    assert "translated_text" in body
    assert len(body["translated_text"]) > 0
    assert "boxes" in body
    assert isinstance(body["boxes"], list)
    assert len(body["boxes"]) > 0
    assert "elapsed_ms" in body
    assert body["elapsed_ms"] >= 0
    # Backward compatibility with mobile app
    assert "vietnamese_text" in body
    assert len(body["vietnamese_text"]) > 0


def test_ocr_two_stage_english_notice():
    """Test OCR extraction of English notice and translation to Vietnamese."""
    img = Image.new("RGB", (600, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((30, 30), "WARNING: SERVER MAINTENANCE", fill=(0, 0, 0))
    draw.text((30, 80), "Do not disconnect the power supply.", fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    files = {"image": ("notice.png", buf.getvalue(), "image/png")}
    data = {"target_language": "vi", "context_preset": "Technical"}
    with patch("app.models.translation_adapter.TranslationAdapter.translate", return_value="Cảnh báo: Bảo trì máy chủ"):
        resp = client.post("/api/ocr", files=files, data=data)

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()

    assert "extracted_text" in body
    assert len(body["extracted_text"]) > 0
    assert body["detected_language"] == "en"
    assert body["target_language"] == "vi"
    assert len(body["translated_text"]) > 0
    assert len(body["boxes"]) > 0
    assert "vietnamese_text" in body
    assert len(body["vietnamese_text"]) > 0


def test_ocr_blank_image():
    """Test OCR on a blank image with no text."""
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    files = {"image": ("blank.png", buf.getvalue(), "image/png")}
    resp = client.post("/api/ocr", files=files)

    assert resp.status_code == 200
    body = resp.json()
    assert body["extracted_text"] == ""
    assert body["translated_text"] == ""
    assert body["boxes"] == []


def test_ocr_unsupported_format():
    """Test uploading an unsupported file format."""
    files = {"image": ("document.pdf", b"%PDF-1.4 dummy content", "application/pdf")}
    resp = client.post("/api/ocr", files=files)
    assert resp.status_code == 415


def test_ocr_corrupted_image():
    """Test uploading a corrupted or empty image file."""
    files = {"image": ("corrupted.png", b"not an actual image content", "image/png")}
    resp = client.post("/api/ocr", files=files)
    assert resp.status_code == 422
