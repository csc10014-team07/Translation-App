"""Pydantic schemas for ASR responses."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ASRResponse(BaseModel):
    """Response returned by the ``POST /api/asr`` endpoint."""

    text: str = Field(..., description="Transcribed Vietnamese text.")
    language_detected: str = Field(
        ..., description="ISO 639-1 language code of the transcribed audio."
    )
    duration: float | None = Field(
        default=None,
        description="Audio duration in seconds.",
    )
    elapsed_ms: float = Field(
        default=0.0,
        description="Processing latency in milliseconds.",
    )
    word_timestamps: list[dict] | None = Field(
        default=None,
        description=(
            "Word-level timing information, if available. "
            "Each entry typically has ``word``, ``start``, and ``end`` keys."
        ),
    )

