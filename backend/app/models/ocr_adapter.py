"""OCR Adapter wrapping RapidOCR on CPU with Auto-Language Detection."""
from __future__ import annotations

import logging
import tempfile
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def detect_language(text: str) -> str:
    """Heuristic / frequency auto-language detector for Vietnamese, English, Chinese, Japanese."""
    if not text.strip():
        return "en"

    # Vietnamese specific diacritic characters
    vi_chars = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")
    lower = text.lower()
    if any(c in vi_chars for c in lower):
        return "vi"

    # Japanese Hiragana / Katakana
    for char in text:
        cp = ord(char)
        if (0x3040 <= cp <= 0x309F) or (0x30A0 <= cp <= 0x30FF):
            return "ja"

    # Chinese CJK Unified Ideographs
    for char in text:
        cp = ord(char)
        if 0x4E00 <= cp <= 0x9FFF:
            return "zh"

    return "en"


class OCRAdapter:
    """Two-Stage OCR adapter using RapidOCR on CPU."""

    def __init__(self) -> None:
        self._engine = None
        self._lock = threading.Lock()

    def load(self) -> None:
        """Load RapidOCR engine."""
        if self._engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                logger.info("Loading RapidOCR on CPU (ONNX Runtime, 0MB VRAM)...")
                self._engine = RapidOCR()
                logger.info("RapidOCR ready.")
            except ImportError:
                logger.error("rapidocr-onnxruntime is not installed.")
                self._engine = None

    def extract_text(self, image_input: bytes | str | Path) -> tuple[str, str, list[Any]]:
        """
        Extract text and detect language from an image.

        Returns:
            Tuple of (extracted_text, detected_language, bounding_boxes)
        """
        self.load()
        if self._engine is None:
            raise RuntimeError("RapidOCR engine is not available. Please verify rapidocr-onnxruntime is installed.")

        temp_path = None
        if isinstance(image_input, (bytes, bytearray)):
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False, mode='wb') as tmp:
                tmp.write(image_input)
                temp_path = tmp.name
            img_path = temp_path
        else:
            img_path = str(image_input)

        try:
            with self._lock:
                result, _ = self._engine(img_path)
            if not result:
                return "", "en", []

            lines = [item[1] for item in result]
            boxes = [item[0] for item in result]
            full_text = " ".join(lines).strip()
            lang = detect_language(full_text)
            return full_text, lang, boxes
        finally:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)


_ocr_singleton: OCRAdapter | None = None


def get_ocr_adapter() -> OCRAdapter:
    global _ocr_singleton
    if _ocr_singleton is None:
        _ocr_singleton = OCRAdapter()
    return _ocr_singleton
