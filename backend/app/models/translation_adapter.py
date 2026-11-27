"""Translation Adapter wrapping TranslateGemma 4B GGUF with context."""
from __future__ import annotations

import logging
import threading
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
    "pt": "Portuguese", "portuguese": "Portuguese",
    "ru": "Russian", "russian": "Russian",
    "it": "Italian", "italian": "Italian",
}


def _neutralize_turn_tokens(value: str) -> str:
    """Prevent user text from creating extra Gemma chat turns."""
    return value.replace("<start_of_turn>", "< start_of_turn >").replace(
        "<end_of_turn>", "< end_of_turn >"
    )


class TranslationAdapter:
    """Context-aware translation adapter using TranslateGemma 4B GGUF."""

    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path or self._resolve_model_path()
        self.device = settings.effective_device()
        self._llm = None
        self._ocr = None
        self._lock = threading.Lock()
        self._load_lock = threading.Lock()
        self._actual_device = "unloaded"
        self._n_gpu_layers = 0
        self._gpu_offload_supported: bool | None = None
        self._fallback_reason = ""
        self._llama_system_info = ""

    @staticmethod
    def _supports_gpu_offload(llama_cpp_module) -> bool:
        checker = getattr(llama_cpp_module, "llama_supports_gpu_offload", None)
        if checker is None:
            return False
        try:
            return bool(checker())
        except Exception:
            return False

    @staticmethod
    def _read_llama_system_info(llama_cpp_module) -> str:
        get_info = getattr(llama_cpp_module, "llama_print_system_info", None)
        if get_info is None:
            return ""
        try:
            raw = get_info()
            if isinstance(raw, bytes):
                return raw.decode("utf-8", errors="replace")
            return str(raw)
        except Exception:
            return ""

    def backend_info(self) -> dict:
        """Return the requested and actual llama.cpp backend configuration."""
        return {
            "device_requested": self.device,
            "device_actual": self._actual_device,
            "gpu_offload": self._actual_device == "cuda" and self._n_gpu_layers != 0,
            "gpu_offload_supported": self._gpu_offload_supported,
            "n_gpu_layers": self._n_gpu_layers,
            "fallback_reason": self._fallback_reason,
            "llama_cpp_system_info": self._llama_system_info,
        }

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
        """Load llama-cpp model once, even when called concurrently."""
        if self._llm is not None:
            return
        with self._load_lock:
            if self._llm is not None:
                return
            self._load_model()

    def _load_model(self) -> None:
        """Load the model; caller must hold ``_load_lock``."""
        if self._llm is not None:
            return
        if not self.model_path or not Path(self.model_path).exists():
            self._actual_device = "unavailable"
            self._fallback_reason = "model_not_found"
            logger.error("TranslateGemma GGUF not found: %s", self.model_path)
            return

        try:
            import llama_cpp
            from llama_cpp import Llama
        except Exception as exc:
            self._actual_device = "unavailable"
            self._fallback_reason = "llama_cpp_unavailable"
            logger.error("Failed to load llama-cpp-python: %s", exc)
            self._llm = None
            return

        self._gpu_offload_supported = self._supports_gpu_offload(llama_cpp)
        self._llama_system_info = self._read_llama_system_info(llama_cpp)

        requested_gpu = self.device.startswith("cuda")
        n_gpu = int(settings.GEMMA_N_GPU_LAYERS) if requested_gpu else 0

        if requested_gpu and n_gpu != 0 and not self._gpu_offload_supported:
            self._fallback_reason = "llama_cpp_cpu_only"
            logger.warning(
                "TranslateGemma GPU offload requested, but this llama-cpp-python build "
                "has no CUDA support. Running on CPU; install a CUDA-enabled build to use the GPU."
            )
            n_gpu = 0
        elif requested_gpu and n_gpu == 0:
            self._fallback_reason = "gpu_layers_disabled"
            logger.warning("TranslateGemma GPU requested but GEMMA_N_GPU_LAYERS=0; running on CPU.")
        elif not requested_gpu:
            self._fallback_reason = "cpu_requested" if settings.DEVICE == "cpu" else "cuda_unavailable"

        logger.info("Loading TranslateGemma GGUF: %s (n_gpu_layers=%s)...", self.model_path, n_gpu)
        try:
            self._llm = Llama(
                model_path=str(self.model_path),
                n_ctx=settings.GEMMA_N_CTX,
                n_gpu_layers=n_gpu,
                verbose=False,
            )
        except Exception as exc:
            if n_gpu == 0:
                self._actual_device = "unavailable"
                self._fallback_reason = "model_load_failed"
                logger.error("Failed to load TranslateGemma: %s", exc)
                self._llm = None
                return
            logger.warning("GPU Llama load failed (%s). Falling back to CPU...", exc)
            self._fallback_reason = "gpu_load_failed"
            n_gpu = 0
            try:
                self._llm = Llama(
                    model_path=str(self.model_path),
                    n_ctx=min(settings.GEMMA_N_CTX, 2048),
                    n_gpu_layers=0,
                    verbose=False,
                )
            except Exception as cpu_exc:
                self._actual_device = "unavailable"
                self._fallback_reason = "model_load_failed"
                logger.error("CPU fallback also failed: %s", cpu_exc)
                self._llm = None
                return

        self._n_gpu_layers = n_gpu
        self._actual_device = "cuda" if n_gpu != 0 else "cpu"
        logger.info(
            "TranslateGemma loaded on %s (n_gpu_layers=%s, offload_supported=%s).",
            self._actual_device,
            self._n_gpu_layers,
            self._gpu_offload_supported,
        )

    def build_prompt(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: str = "",
        context_preset: str = "",
        custom_context: str = "",
    ) -> str:
        src_name = _neutralize_turn_tokens(
            LANGUAGE_NAMES.get(source_lang.lower(), source_lang)
        )
        tgt_name = _neutralize_turn_tokens(
            LANGUAGE_NAMES.get(target_lang.lower(), target_lang)
        )
        safe_text = _neutralize_turn_tokens(text)

        # Match preset if given
        preset_info = ""
        free_context = ""
        preset_candidate = (context_preset or "").strip()
        if preset_candidate:
            for k, v in CONTEXT_PRESETS.items():
                if k.lower() == preset_candidate.lower() or k.lower() in preset_candidate.lower():
                    preset_info = v
                    break
            if not preset_info:
                # Preserve unknown preset values as free-form context instead of
                # silently dropping them (callers may send free text here).
                free_context = preset_candidate
        elif context:
            for k, v in CONTEXT_PRESETS.items():
                if k.lower() in context.lower():
                    preset_info = v
                    break

        parts = []
        if preset_info:
            parts.append(preset_info)
        if custom_context and custom_context.strip():
            parts.append(_neutralize_turn_tokens(custom_context.strip()))
        if free_context:
            parts.append(_neutralize_turn_tokens(free_context))
        if context and context.strip() and not preset_info:
            extra = context.strip()
            if extra not in free_context:
                parts.append(_neutralize_turn_tokens(extra))

        combined_context = " | ".join(parts).strip()
        if not combined_context:
            combined_context = "General natural translation, maintaining accurate tone and terminology."

        return (
            f"<start_of_turn>user\n"
            f"You are a professional {src_name} to {tgt_name} translator. "
            f"Your goal is to accurately convey the meaning and nuances of the original text while adhering to {tgt_name} grammar, vocabulary, and cultural sensitivities.\n"
            f"Context requirement: {combined_context}.\n"
            f"Produce only the {tgt_name} translation, without any additional explanations or commentary.\n\n"
            f"{safe_text}<end_of_turn>\n"
            f"<start_of_turn>model\n"
        )

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
        """Translate text with context awareness using local TranslateGemma model."""
        from app.core.config import settings

        self.load()
        if self._llm is None:
            if not settings.ALLOW_ONLINE_FALLBACK:
                logger.warning("TranslateGemma model not loaded and online fallback is disabled")
            raise RuntimeError("TranslateGemma model is not loaded. Please verify GEMMA_GGUF_PATH.")

        prompt = self.build_prompt(
            text=text,
            source_lang=source_language,
            target_lang=target_language,
            context=context,
            context_preset=context_preset,
            custom_context=custom_context,
        )

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
            raise RuntimeError("TranslateGemma returned empty response")
        except Exception as e:
            logger.warning("Gemma inference error: %s", e)
            if not settings.ALLOW_ONLINE_FALLBACK:
                logger.warning("Online fallback is disabled (ALLOW_ONLINE_FALLBACK=false)")
            raise RuntimeError(f"Translation failed: {e}") from e

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

