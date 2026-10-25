"""Pydantic schemas for translation requests and responses."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TranslateRequest(BaseModel):
    """Request body for the ``POST /api/translate`` endpoint."""

    text: str = Field(..., description="Vietnamese source text to translate.", min_length=1)
    target_language: str = Field(
        ...,
        description="Target language name (e.g. 'English', 'French', 'Japanese').",
        min_length=1,
    )
    context: str = Field(
        default="",
        description=(
            "Optional style or domain context to guide the translation. "
            "Truncated to 500 characters if longer."
        ),
    )


class TranslateResponse(BaseModel):
    """Response returned by the ``POST /api/translate`` endpoint."""

    translated_text: str = Field(..., description="Translated text in the target language.")
    source_language: str = Field(
        default="vi",
        description="Source language (always Vietnamese for this app).",
    )
    target_language: str = Field(..., description="Target language of the translation.")
