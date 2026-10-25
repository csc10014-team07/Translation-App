"""Pydantic schemas for TTS requests and responses."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TTSRequest(BaseModel):
    """Request body (JSON) for the ``POST /api/tts`` endpoint."""

    text: str = Field(..., description="Text to synthesise into speech.", min_length=1)
    language: str = Field(
        ...,
        description=(
            "Spoken language of *text* (e.g. 'English', 'French'). "
            "Vietnamese is **not** supported and will be rejected with HTTP 400."
        ),
    )
    reference_text: str | None = Field(
        default=None,
        description="Transcript of the reference audio clip for voice cloning.",
    )


class TTSResponse(BaseModel):
    """Response returned by the ``POST /api/tts`` endpoint."""

    audio_base64: str = Field(
        ..., description="Base64-encoded audio data in *format* encoding."
    )
    sample_rate: int = Field(
        ..., description="Sample rate of the synthesised audio in Hz."
    )
    format: str = Field(default="wav", description="Audio container format.")
