"""Translation Adapter wrapping TranslateGemma 4B GGUF with context and multi-tier fallbacks."""
from __future__ import annotations

import json
import logging
import threading
import urllib.request
from collections.abc import Generator
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

CONTEXT_PRESETS = {
    "Formal": "Văn phong lịch sự, chuẩn mực kinh doanh. Sử dụng từ ngữ trang trọng, xưng hô tôn trọng đối tác.",
    "Friendly": "Văn phong tự nhiên, thân thiện, gần gũi như bạn bè trò chuyện hàng ngày, sử dụng từ ngữ đời thường.",
    "Casual": "Văn phong tự nhiên, gần gũi, thoải mái như bạn bè trò chuyện hàng ngày, sử dụng từ ngữ đời thường.",
    "IT": "Bối cảnh công nghệ thông tin và kỹ thuật. Giữ nguyên các thuật ngữ chuyên ngành quốc tế (API, Deploy, Bug, Framework, v.v.), giải thích mạch lạc.",
    "Technical": "Bối cảnh công nghệ thông tin và kỹ thuật. Giữ nguyên các thuật ngữ chuyên ngành quốc tế (API, Deploy, Bug, Framework, v.v.), giải thích mạch lạc.",
    "Medical": "Văn phong học thuật, khoa học, chính xác tuyệt đối về mặt thuật ngữ y khoa, nghiên cứu.",
    "Travel": "Diễn đạt ngắn gọn, thực tế, nhã nhặn cho tình huống giao tiếp ở sân bay, khách sạn, nhà hàng, hỏi đường.",
    "General": "Dịch tự nhiên, trung tính theo đúng ngữ nghĩa phổ thông nhất.",
}

LANGUAGE_NAMES = {
    "en": "English", "english": "English",
    "vi": "Vietnamese", "vietnamese": "Vietnamese",
    "ja": "Japanese", "japanese": "Japanese",
    "zh": "Chinese", "chinese": "Chinese",
    "ko": "Korean", "korean": "Korean",
    "fr": "French", "french": "French",
    "de": "German", "german": "German",
    "es": "Spanish", "spanish": "Spanish",
}

MY_MEMORY_MAP = {
    "vi": "vi-VN", "vietnamese": "vi-VN",
    "en": "en-US", "english": "en-US",
    "ja": "ja-JP", "japanese": "ja-JP",
    "zh": "zh-CN", "chinese": "zh-CN",
    "ko": "ko-KR", "korean": "ko-KR",
    "fr": "fr-FR", "french": "fr-FR",
    "de": "de-DE", "german": "de-DE",
    "es": "es-ES", "spanish": "es-ES",
}


class TranslationAdapter:
    """Context-aware translation adapter using TranslateGemma 4B GGUF."""

    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path or self._resolve_model_path()
        self.device = settings.effective_device()
        self._llm = None
        self._ocr = None
        self._lock = threading.Lock()

    def _resolve_model_path(self) -> Path | None:
        candidates = [
            Path(settings.GEMMA_GGUF_PATH),
            Path("d:/APP test/models/gemma/translategemma-4b-it.Q5_K_M.gguf"),
            Path("./models/gemma/translategemma-4b-it.Q5_K_M.gguf"),
            Path("/content/models/gemma/translategemma-4b-it.Q5_K_M.gguf"),
        ]
        for p in candidates:
            if p.exists():
                return p.resolve()
        return None

    def load(self) -> None:
        """Load llama-cpp model if not already loaded."""
        if self._llm is None and self.model_path and self.model_path.exists():
            try:
                from llama_cpp import Llama
                n_gpu = settings.GEMMA_N_GPU_LAYERS if self.device.startswith("cuda") else 0
                logger.info("Loading TranslateGemma GGUF: %s (n_gpu=%s)...", self.model_path, n_gpu)
                try:
                    self._llm = Llama(
                        model_path=str(self.model_path),
                        n_ctx=settings.GEMMA_N_CTX,
                        n_gpu_layers=n_gpu,
                        verbose=False,
                    )
                except Exception as e:
                    logger.warning("GPU Llama load failed (%s). Falling back to CPU...", e)
                    self._llm = Llama(
                        model_path=str(self.model_path),
                        n_ctx=min(settings.GEMMA_N_CTX, 2048),
                        n_gpu_layers=0,
                        verbose=False,
                    )
                logger.info("TranslateGemma loaded successfully.")
            except Exception as exc:
                logger.error("Failed to load llama-cpp-python: %s", exc)
                self._llm = None

    def build_prompt(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: str = "",
        context_preset: str = "",
        custom_context: str = "",
    ) -> str:
        src_name = LANGUAGE_NAMES.get(source_lang.lower(), source_lang)
        tgt_name = LANGUAGE_NAMES.get(target_lang.lower(), target_lang)

        # Match preset if given
        preset_info = ""
        preset_candidate = (context_preset or "").strip()
        if preset_candidate:
            for k, v in CONTEXT_PRESETS.items():
                if k.lower() == preset_candidate.lower() or k.lower() in preset_candidate.lower():
                    preset_info = v
                    break
        elif context:
            for k, v in CONTEXT_PRESETS.items():
                if k.lower() in context.lower():
                    preset_info = v
                    break

        parts = []
        if preset_info:
            parts.append(preset_info)
        if custom_context and custom_context.strip():
            parts.append(custom_context.strip())
        if context and context.strip() and not preset_info:
            parts.append(context.strip())

        combined_context = " | ".join(parts).strip()
        if not combined_context:
            combined_context = "General natural translation, maintaining accurate tone and terminology."

        return (
            f"<start_of_turn>user\n"
            f"You are a professional {src_name} to {tgt_name} translator. "
            f"Your goal is to accurately convey the meaning and nuances of the original text while adhering to {tgt_name} grammar, vocabulary, and cultural sensitivities.\n"
            f"Context requirement: {combined_context}.\n"
            f"Produce only the {tgt_name} translation, without any additional explanations or commentary.\n\n"
            f"{text}<end_of_turn>\n"
            f"<start_of_turn>model\n"
        )

    def _query_ollama(self, prompt: str) -> str | None:
        try:
            payload = json.dumps({
                "model": "gemma2:2b",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3},
            }).encode("utf-8")
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return res.get("response", "").strip().strip('"')
        except Exception:
            return None

    def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "vi",
        context: str = "",
        context_preset: str = "",
        custom_context: str = "",
        return_details: bool = False,
    ) -> str | tuple[str, str]:
        """Translate text with context awareness and multi-tier fallbacks."""
        self.load()
        prompt = self.build_prompt(
            text=text,
            source_lang=source_language,
            target_lang=target_language,
            context=context,
            context_preset=context_preset,
            custom_context=custom_context,
        )

        # Tier 1: TranslateGemma 4B GGUF
        if self._llm is not None:
            try:
                with self._lock:
                    output = self._llm(
                        prompt,
                        max_tokens=512,
                        temperature=0.3,
                        top_p=0.9,
                        stop=["<end_of_turn>", "\n\nUser:"],
                    )
                ans = output["choices"][0]["text"].strip().strip('"')
                if ans:
                    return (ans, "translategemma-4b") if return_details else ans
            except Exception as e:
                logger.warning("Gemma inference error: %s", e)

        # Tier 2: Ollama probe
        ollama_ans = self._query_ollama(prompt)
        if ollama_ans:
            return (ollama_ans, "ollama:gemma2") if return_details else ollama_ans

        # Tier 3: Neural Translator fallback (guarantees real translation)
        try:
            from deep_translator import MyMemoryTranslator
            src_c = MY_MEMORY_MAP.get(source_language.lower(), "vi-VN")
            tgt_c = MY_MEMORY_MAP.get(target_language.lower(), "en-US")
            res = MyMemoryTranslator(source=src_c, target=tgt_c).translate(text)
            if res:
                return (res, "mymemory") if return_details else res
        except Exception as e:
            logger.warning("MyMemory fallback error: %s", e)

        fallback = f"[{target_language}] {text}"
        return (fallback, "fallback:degraded") if return_details else fallback

    def translate_with_engine(
        self,
        text: str,
        target_language: str,
        source_language: str = "vi",
        context: str = "",
        context_preset: str = "",
        custom_context: str = "",
    ) -> tuple[str, str]:
        """Translate text and always return (translated_text, engine_used)."""
        res = self.translate(
            text=text,
            target_language=target_language,
            source_language=source_language,
            context=context,
            context_preset=context_preset,
            custom_context=custom_context,
            return_details=True,
        )
        if isinstance(res, tuple):
            return res
        return res, "unknown"

    def translate_stream(
        self,
        text: str,
        target_language: str,
        source_language: str = "vi",
        context: str = "",
        context_preset: str = "",
        custom_context: str = "",
    ) -> Generator[str, None, None]:
        """Stream translation tokens generator."""
        self.load()
        prompt = self.build_prompt(
            text=text,
            source_lang=source_language,
            target_lang=target_language,
            context=context,
            context_preset=context_preset,
            custom_context=custom_context,
        )

        if self._llm is not None:
            try:
                self._lock.acquire()
                try:
                    for chunk in self._llm(
                        prompt,
                        max_tokens=512,
                        temperature=0.3,
                        top_p=0.9,
                        stop=["<end_of_turn>", "\n\nUser:"],
                        stream=True,
                    ):
                        token = chunk["choices"][0]["text"]
                        yield token
                finally:
                    self._lock.release()
                return
            except Exception as e:
                logger.warning("Streaming LLM error: %s", e)

        # Fallback to single yield if streaming not supported
        full = self.translate(
            text=text,
            target_language=target_language,
            source_language=source_language,
            context=context,
            context_preset=context_preset,
            custom_context=custom_context,
        )
        if isinstance(full, tuple):
            yield full[0]
        else:
            yield full

