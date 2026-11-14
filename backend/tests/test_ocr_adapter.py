"""Tests for Seam 2: OCRAdapter and Auto-Language Detection."""
from __future__ import annotations

import io

from app.models.ocr_adapter import detect_language, get_ocr_adapter
from PIL import Image, ImageDraw


def test_detect_language_vietnamese():
    assert detect_language("Quán cà phê sữa đá Sài Gòn") == "vi"
    assert detect_language("Thông báo quan trọng về việc bảo trì") == "vi"


def test_detect_language_english():
    assert detect_language("Special iced milk coffee: 35,000 VND") == "en"
    assert detect_language("System maintenance in progress. Do not unplug power.") == "en"


def test_detect_language_japanese():
    assert detect_language("いらっしゃいませ。コーヒーをお楽しみください。") == "ja"
    assert detect_language("カフェ・オ・レ") == "ja"


def test_detect_language_chinese():
    assert detect_language("欢迎光临咖啡店") == "zh"
    assert detect_language("请在柜台结账") == "zh"


def test_detect_language_empty():
    assert detect_language("") == "en"
    assert detect_language("   ") == "en"


def test_ocr_adapter_extract_sample_menu():
    adapter = get_ocr_adapter()
    adapter.load()

    # Create a synthetic Vietnamese menu image
    img = Image.new("RGB", (500, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((30, 40), "QUAN CA PHE SAI GON", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    text, _lang, boxes = adapter.extract_text(img_bytes)
    assert isinstance(text, str)
    assert len(text) > 0
    assert "QUAN" in text.upper() or "PHE" in text.upper() or "CA" in text.upper()
    assert isinstance(boxes, list)
    assert len(boxes) > 0


def test_ocr_adapter_extract_empty_blank_image():
    adapter = get_ocr_adapter()
    # Blank white image with no text
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    text, _lang, boxes = adapter.extract_text(buf.getvalue())
    assert text == ""
    assert boxes == []
