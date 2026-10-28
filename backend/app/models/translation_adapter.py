"""Translation (and OCR) adapter wrapping TranslateGemma-4b-it Q5_K_M via llama-cpp-python."""
from __future__ import annotations

import gc
import logging
import threading
import time
from typing import Any

import torch

logger = logging.getLogger(__name__)

_MAX_CONTEXT_CHARS = 500  # truncation limit for user-supplied context

# Language mapping for TranslateGemma:
# Maps supported target language codes and names used by the app to (canonical_name, iso_code).
LANGUAGE_MAPPING: dict[str, tuple[str, str]] = {
    # Vietnamese (source default, or target)
    "vi": ("Vietnamese", "vi"),
    "vietnamese": ("Vietnamese", "vi"),
    "tiếng việt": ("Vietnamese", "vi"),
    "tieng viet": ("Vietnamese", "vi"),
    "vie": ("Vietnamese", "vi"),

    # English
    "en": ("English", "en"),
    "english": ("English", "en"),

    # Chinese
    "zh": ("Chinese (Simplified)", "zh"),
    "chinese": ("Chinese (Simplified)", "zh"),
    "chinese (simplified)": ("Chinese (Simplified)", "zh"),
    "simplified chinese": ("Chinese (Simplified)", "zh"),

    # Japanese
    "ja": ("Japanese", "ja"),
    "japanese": ("Japanese", "ja"),

    # Korean
    "ko": ("Korean", "ko"),
    "korean": ("Korean", "ko"),

    # French
    "fr": ("French", "fr"),
    "french": ("French", "fr"),

    # German
    "de": ("German", "de"),
    "german": ("German", "de"),

    # Spanish
    "es": ("Spanish", "es"),
    "spanish": ("Spanish", "es"),

    # Portuguese
    "pt": ("Portuguese", "pt"),
    "portuguese": ("Portuguese", "pt"),

    # Russian
    "ru": ("Russian", "ru"),
    "russian": ("Russian", "ru"),

    # Italian
    "it": ("Italian", "it"),
    "italian": ("Italian", "it"),
}


def _resolve_language(lang: str) -> tuple[str, str]:
    """Resolve language name or code to (canonical_name, iso_code)."""
    normalized = lang.strip().lower()
    if normalized in LANGUAGE_MAPPING:
        return LANGUAGE_MAPPING[normalized]
    return lang.strip().title(), normalized


def _truncate_context(context: str) -> str:
    """Truncate *context* to at most ``_MAX_CONTEXT_CHARS`` characters."""
    if len(context) > _MAX_CONTEXT_CHARS:
        logger.debug(
            "Context truncated from %d to %d chars to avoid token overflow.",
            len(context),
            _MAX_CONTEXT_CHARS,
        )
        return context[:_MAX_CONTEXT_CHARS]
    return context


class TranslationAdapter:
    """
    Wraps ``llama-cpp-python`` (``Llama``) for text translation and OCR using
    the TranslateGemma-4b-it Q5_K_M GGUF model.

    TranslateGemma follows the official prompt format:
    - User turn only (no system role).
    - Explicit source and target language names and codes.
    - Optional context injected directly into the user prompt.
    - Greedy decoding (temperature=0.0 / do_sample=False) per model card recommendation.
    Inference calls are protected by a lock for thread-safety.
    """

    def __init__(self) -> None:
        self._llm: Any | None = None  # llama_cpp.Llama
        self._loaded: bool = False
        self._lock = threading.Lock()

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def load(self, gguf_path: str, n_ctx: int, n_gpu_layers: int) -> None:
        """
        Instantiate the Llama model from a GGUF file.

        Args:
            gguf_path:     Path to the ``.gguf`` weight file.
            n_ctx:         Context window size in tokens.
            n_gpu_layers:  Number of transformer layers to offload to GPU.
                           Use ``-1`` for all layers.
        """
        from llama_cpp import Llama  # type: ignore[import]

        logger.info(
            "Loading TranslateGemma GGUF from '%s' (n_ctx=%d, n_gpu_layers=%d) …",
            gguf_path,
            n_ctx,
            n_gpu_layers,
        )
        t0 = time.monotonic()

        self._llm = Llama(
            model_path=gguf_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=False,
        )
        self._loaded = True

        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info("TranslateGemma GGUF loaded in %.0f ms", elapsed_ms)

    def unload(self) -> None:
        """
        Free the model from memory.

        Deletes the Python object, runs ``gc.collect()``, and calls
        ``torch.cuda.empty_cache()`` to release any fragmented VRAM.
        """
        logger.info("Unloading TranslateGemma model …")
        if self._llm is not None:
            del self._llm
            self._llm = None
        self._loaded = False
        gc.collect()
        torch.cuda.empty_cache()
        logger.info("TranslateGemma model unloaded.")

    # ── Core helpers ───────────────────────────────────────────────────────

    def _call_llm(
        self,
        system_prompt: str | None,
        user_message: str,
        temperature: float = 0.0,
        top_k: int = 64,
        top_p: float = 0.95,
    ) -> str:
        """
        Run a chat-completion call via llama-cpp-python.

        Args:
            system_prompt: Optional instruction / role description. For TranslateGemma
                           translation, no system role is used (pass None). OCR retains
                           its system prompt.
            user_message:  The text the model should act on.
            temperature:   Sampling temperature (0.0 = greedy decoding per model card).
            top_k:         Top-k sampling cutoff.
            top_p:         Top-p nucleus sampling cutoff.

        Returns:
            The model's response string, stripped of leading/trailing whitespace.

        Raises:
            RuntimeError: If the model is not loaded.
        """
        if not self._loaded or self._llm is None:
            raise RuntimeError(
                "TranslationAdapter.load() must be called before inference."
            )

        with self._lock:
            messages: list[dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_message})

            response = self._llm.create_chat_completion(
                messages=messages,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                max_tokens=2048,
            )
            return response["choices"][0]["message"]["content"].strip()

    # ── Public API ─────────────────────────────────────────────────────────

    def translate(
        self,
        text: str,
        target_language: str,
        context: str = "",
    ) -> str:
        """
        Translate Vietnamese *text* to *target_language* using TranslateGemma 4B.

        Args:
            text:            Vietnamese source text.
            target_language: Target language name or code (e.g. ``"English"`` or ``"en"``).
            context:         Optional style / meaning context supplied by the user.
                             Truncated to ``_MAX_CONTEXT_CHARS`` characters before
                             injection into the user turn.

        Returns:
            The translated string.
        """
        source_name, source_code = ("Vietnamese", "vi")
        target_name, target_code = _resolve_language(target_language)

        context = _truncate_context(context.strip())

        prompt_lines = [
            f"You are a professional {source_name} ({source_code}) to {target_name} ({target_code}) translator. "
            f"Your goal is to accurately convey the meaning and nuances of the original {source_name} text "
            f"while adhering to {target_name} grammar, vocabulary, and cultural sensitivities. "
            f"Produce only the {target_name} translation, without any additional explanations or commentary."
        ]

        if context:
            prompt_lines.append(
                f"\nContext to guide the translation style, tone, and terminology:\n---\n{context}\n---"
            )

        prompt_lines.append(
            f"\nPlease translate the following {source_name} text into {target_name}:\n\n{text}"
        )

        user_prompt = "\n".join(prompt_lines)

        logger.debug(
            "Translating %d chars from %s (%s) to %s (%s) (context=%s) …",
            len(text),
            source_name,
            source_code,
            target_name,
            target_code,
            "yes" if context else "no",
        )
        t0 = time.monotonic()
        result = self._call_llm(None, user_prompt, temperature=0.0)
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info("Translation completed in %.0f ms", elapsed_ms)
        return result

    def ocr_to_vietnamese(self, image_base64: str, context: str = "") -> str:
        """
        Extract Vietnamese text from a base64-encoded image.

        Args:
            image_base64: Base64-encoded image data (PNG / JPEG / etc.).
            context:      Optional context to hint at the domain or style of the
                          document (e.g. ``"medical report"``).  Truncated to
                          ``_MAX_CONTEXT_CHARS`` characters.

        Returns:
            Extracted Vietnamese text as a plain string.
        """
        context = _truncate_context(context.strip())

        context_hint = (
            f"\nAdditional context about the document: {context}" if context else ""
        )

        system_prompt = (
            "You are an expert OCR system specialized in Vietnamese text extraction.\n"
            "Rules:\n"
            "- Extract ALL text visible in the provided image.\n"
            "- Output ONLY the extracted text, preserving the original layout as much as possible.\n"
            "- Do not translate or modify the text.\n"
            "- Do not add explanations or descriptions."
            + context_hint
        )

        user_message = (
            f"Please extract all Vietnamese text from this base64-encoded image:\n{image_base64}"
        )

        logger.debug("Running OCR on image (base64 length=%d) …", len(image_base64))
        t0 = time.monotonic()
        result = self._call_llm(system_prompt, user_message)
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info("OCR completed in %.0f ms", elapsed_ms)
        return result

    @property
    def is_loaded(self) -> bool:
        """True if the GGUF model is currently loaded."""
        return self._loaded
