"""OCR Schemas for request and response data models."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OCRResponse(BaseModel):
    """Response returned by POST /api/ocr."""

    extracted_text: str = Field(..., description="Raw text extracted by RapidOCR.")
    detected_language: str = Field(
        default="en",
        description="Auto-detected language of extracted text (vi, en, zh, ja, etc.).",
    )
    target_language: str = Field(
        default="en",
        description="Target language for translation.",
    )
    translated_text: str = Field(
        default="",
        description="Context-aware translated text produced by TranslateGemma.",
    )
    boxes: list[Any] = Field(
        default_factory=list,
        description="Bounding box coordinates for detected text regions.",
    )
    elapsed_ms: float = Field(
        default=0.0,
        description="Total processing latency in milliseconds.",
    )
    vietnamese_text: str = Field(
        default="",
        description="Legacy field providing Vietnamese text for mobile client compatibility.",
    )
