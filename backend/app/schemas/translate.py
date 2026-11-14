from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class TranslateRequest(BaseModel):
    """Request body for the ``POST /api/translate`` endpoint."""

    text: str = Field(..., description="Source text to translate.", min_length=1)
    target_language: str = Field(
        ...,
        description="Target language name or code (e.g. 'English', 'French', 'Japanese', 'en').",
        min_length=1,
    )
    source_language: str = Field(
        default="vi",
        description="Source language (default: 'vi').",
    )
    context_preset: str | None = Field(
        default="",
        description="Context preset name (e.g. Formal, Friendly/Casual, Technical, Medical, Travel).",
    )
    custom_context: str | None = Field(
        default="",
        description="Custom context notes to guide the translation.",
    )
    context: str | None = Field(
        default="",
        description="Direct or legacy style context string for backward compatibility.",
    )

    @field_validator("text", "target_language")
    @classmethod
    def validate_non_whitespace(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be empty or whitespace only.")
        return v.strip()


class TranslateResponse(BaseModel):
    """Response returned by the ``POST /api/translate`` endpoint."""

    translated_text: str = Field(..., description="Translated text in the target language.")
    source_language: str = Field(
        default="vi",
        description="Source language (e.g. 'vi').",
    )
    target_language: str = Field(..., description="Target language of the translation.")
    engine_used: str = Field(
        default="translategemma-4b",
        description="Inference engine or fallback used (translategemma-4b, ollama:gemma2, mymemory, etc.).",
    )
    elapsed_ms: float = Field(
        default=0.0,
        description="Latency in milliseconds for the translation call.",
    )

