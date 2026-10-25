"""Pydantic schemas for ASR responses."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ASRResponse(BaseModel):
    """Response returned by the ``POST /api/asr`` endpoint."""

    text: str = Field(..., description="Transcribed Vietnamese text.")
    language_detected: str = Field(
        ..., description="ISO 639-1 language code of the transcribed audio."
    )
    word_timestamps: list[dict] | None = Field(
        default=None,
        description=(
            "Word-level timing information, if available. "
            "Each entry typically has ``word``, ``start``, and ``end`` keys."
        ),
    )
