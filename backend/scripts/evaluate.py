#!/usr/bin/env python3
"""
CLI Evaluation and Benchmark Runner for Translation-App.

Evaluates:
- Speech Recognition (PhoASR): WER, CER, RTF, Latency.
- Machine Translation (TranslateGemma): BLEU (sentence/corpus), chrF++, Latency.
- Context-Aware Presets: Pronoun and domain terminology compliance.
- Text-to-Speech (Edge-TTS): success rate, latency, RTF, optional PhoASR round-trip.
- System VRAM and Performance Footprint.

Outputs:
1. Live ASCII summary table on Terminal.
2. Structured Markdown report (default: backend/benchmarks/reports/benchmark_report.md).
3. Detailed JSON results (default: backend/benchmarks/reports/benchmark_results.json).
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

# Ensure backend root is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from benchmarks.dataset_loader import (  # noqa: E402
    MIN_EVAL_SAMPLES,
    get_context_dataset,
    get_fleurs_asr_dataset,
    get_flores_dataset,
    get_tts_samples,
)
from benchmarks.metrics import (  # noqa: E402
    calculate_cer,
    calculate_corpus_bleu,
    calculate_sentence_bleu,
    calculate_sentence_chrf,
    calculate_wer,
    evaluate_context_preset_sample,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("evaluate")


def format_progress_bar(current: int, total: int, width: int = 30) -> str:
    """Render a clean text progress bar."""
    if total <= 0:
        return "[------------------------------] 0%"
    fraction = min(1.0, current / total)
    filled = int(width * fraction)
    bar = "=" * filled + "-" * (width - filled)
    percent = int(fraction * 100)
    return f"[{bar}] {current}/{total} ({percent}%)"


def _resample_audio(audio: np.ndarray, source_sr: int, target_sr: int = 16000) -> np.ndarray:
    """Convert TTS output to mono float32 at the ASR sample rate."""
    samples = np.asarray(audio, dtype=np.float32)
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    samples = samples.flatten()
    if source_sr == target_sr or samples.size == 0:
        return samples
    try:
        import librosa

        return librosa.resample(samples, orig_sr=source_sr, target_sr=target_sr).astype(np.float32)
    except Exception:
        duration = samples.size / source_sr
        target_count = max(1, int(round(duration * target_sr)))
        old_x = np.linspace(0.0, duration, num=samples.size, endpoint=False)
        new_x = np.linspace(0.0, duration, num=target_count, endpoint=False)
        return np.interp(new_x, old_x, samples).astype(np.float32)


class BenchmarkRunner:
    """Orchestrates running evaluation suites on AI models."""

    def __init__(self, limit: int = MIN_EVAL_SAMPLES, tts_round_trip: bool = True) -> None:
        self.limit = limit
        self.tts_round_trip = tts_round_trip
        self._translation_adapter: Any | None = None
        self._translation_skip_reason = "model_not_ready"
        self._asr_adapter: Any | None = None
        self._asr_skip_reason = "model_not_ready"
        self._tts_adapter: Any | None = None
        self._tts_skip_reason = "model_not_ready"
        self.results: dict[str, Any] = {
            "timestamp": datetime.datetime.now().isoformat(),
            "summary": {},
            "datasets": {},
            "details": {},
            "hardware": {},
        }

    def _vram_info(self) -> dict[str, Any]:
        """Return a VRAM snapshot without failing evaluation on CPU-only hosts."""
        try:
            from app.core.vram_monitor import get_vram_info

            return get_vram_info()
        except Exception as exc:
            logger.debug("VRAM info unavailable: %s", exc)
            return {}

    def _get_translation_adapter(self) -> Any | None:
        """Load TranslateGemma once and reuse it across MT and context suites."""
        if self._translation_adapter is not None:
            return self._translation_adapter
        try:
            from app.models.translation_adapter import TranslationAdapter

            adapter = TranslationAdapter()
            adapter.load()
            backend_info = adapter.backend_info()
            self.results["hardware"]["translation"] = backend_info
            if (
                backend_info.get("device_requested", "").startswith("cuda")
                and backend_info.get("device_actual") == "cpu"
            ):
                logger.warning(
                    "TranslateGemma is running on CPU (%s)",
                    backend_info.get("fallback_reason"),
                )
            if adapter._llm is None:
                self._translation_skip_reason = "model_not_ready"
                return None
            self._translation_adapter = adapter
            self._translation_skip_reason = ""
            return adapter
        except Exception as err:
            self._translation_skip_reason = str(err)
            logger.warning("Could not load TranslateGemma: %s", err)
            return None

    def _get_asr_adapter(self) -> Any | None:
        """Load PhoASR once and reuse it across ASR samples."""
        if self._asr_adapter is not None:
            return self._asr_adapter
        try:
            from app.models.asr_adapter import ASRAdapter

            adapter = ASRAdapter()
            adapter.load()
            self._asr_adapter = adapter
            self._asr_skip_reason = ""
            return adapter
        except Exception as err:
            self._asr_skip_reason = str(err)
            logger.warning("Could not load PhoASR: %s", err)
            return None

    def _get_tts_adapter(self) -> Any | None:
        """Load the hybrid TTS adapter once for the TTS suite."""
        if self._tts_adapter is not None:
            return self._tts_adapter
        try:
            from app.models.tts_adapter import TTSAdapter

            self._tts_adapter = TTSAdapter()
            self._tts_skip_reason = ""
            return self._tts_adapter
        except Exception as err:
            self._tts_skip_reason = str(err)
            logger.warning("Could not initialise TTS: %s", err)
            return None

    def evaluate_translation(self, samples: list[dict[str, str]]) -> dict[str, Any]:
        """Benchmark TranslateGemma on translation samples."""
        print(f"\n--- [1/4] Benchmarking Machine Translation ({len(samples)} samples) ---")
        vram_before = self._vram_info()
        if not samples:
            return {
                "status": "skipped",
                "reason": "no_translation_samples",
                "vram_before": vram_before,
                "vram_after": self._vram_info(),
            }

        adapter = self._get_translation_adapter()
        if adapter is None:
            reason = self._translation_skip_reason or "model_not_ready"
            print(f"  [SKIP] TranslateGemma not ready: {reason}")
            return {
                "status": "skipped",
                "reason": reason,
                "vram_before": vram_before,
                "vram_after": self._vram_info(),
            }

        sentence_bleu_scores: list[float] = []
        chrf_scores: list[float] = []
        latencies: list[float] = []
        references: list[str] = []
        hypotheses: list[str] = []
        item_details = []

        total = len(samples)
        for i, sample in enumerate(samples, 1):
            src = sample["source"]
            ref = sample["reference"]

            t0 = time.perf_counter()
            error: str | None = None
            try:
                hyp = adapter.translate(
                    text=src,
                    target_language="vi",
                    source_language="en",
                    context_preset="General",
                )
            except Exception as e:
                logger.debug("Translation error: %s", e)
                hyp = ""
                error = str(e)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            bleu = calculate_sentence_bleu(ref, hyp)
            chrf = calculate_sentence_chrf(ref, hyp)

            sentence_bleu_scores.append(bleu)
            chrf_scores.append(chrf)
            latencies.append(elapsed_ms)
            references.append(ref)
            hypotheses.append(hyp)

            item = {
                "source": src,
                "reference": ref,
                "hypothesis": hyp,
                "bleu": round(bleu, 2),
                "chrf": round(chrf, 2),
                "latency_ms": round(elapsed_ms, 1),
            }
            if error:
                item["error"] = error
            item_details.append(item)

            print(f"\r  Progress: {format_progress_bar(i, total)}", end="", flush=True)

        print()
        corpus_bleu = calculate_corpus_bleu(references, hypotheses)
        avg_sentence_bleu = (
            sum(sentence_bleu_scores) / len(sentence_bleu_scores) if sentence_bleu_scores else 0.0
        )
        avg_chrf = sum(chrf_scores) / len(chrf_scores) if chrf_scores else 0.0
        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0

        print(f"  -> Corpus BLEU:             {corpus_bleu:.2f}")
        print(f"  -> Average sentence BLEU:   {avg_sentence_bleu:.2f}")
        print(f"  -> Average chrF++:          {avg_chrf:.2f}")
        print(f"  -> Average Latency:         {avg_lat:.1f} ms/sentence")

        return {
            "status": "success",
            "samples_count": len(samples),
            "corpus_bleu": round(corpus_bleu, 2),
            "avg_sentence_bleu": round(avg_sentence_bleu, 2),
            "avg_chrf": round(avg_chrf, 2),
            "avg_latency_ms": round(avg_lat, 1),
            "vram_before": vram_before,
            "vram_after": self._vram_info(),
            "items": item_details,
        }

    def evaluate_context_presets(self, test_set: list[dict[str, Any]]) -> dict[str, Any]:
        """Benchmark TranslateGemma context presets compliance."""
        print(f"\n--- [2/4] Benchmarking Context-Aware Presets ({len(test_set)} samples) ---")
        vram_before = self._vram_info()
        if not test_set:
            return {
                "status": "skipped",
                "reason": "no_context_samples",
                "vram_before": vram_before,
                "vram_after": self._vram_info(),
            }

        adapter = self._get_translation_adapter()
        if adapter is None:
            reason = self._translation_skip_reason or "model_not_ready"
            print(f"  [SKIP] TranslateGemma not ready: {reason}")
            return {
                "status": "skipped",
                "reason": reason,
                "vram_before": vram_before,
                "vram_after": self._vram_info(),
            }

        passed_count = 0
        preset_scores: dict[str, list[float]] = {}
        preset_passes: dict[str, list[bool]] = {}
        item_details = []

        total = len(test_set)
        for i, item in enumerate(test_set, 1):
            preset = item.get("preset", "General")
            src = item["source"]
            ref = item.get("reference", "")
            req_kw = item.get("required_keywords", [])
            forb_kw = item.get("forbidden_keywords", [])

            t0 = time.perf_counter()
            error: str | None = None
            try:
                hyp = adapter.translate(
                    text=src,
                    target_language=item.get("target_lang", "vi"),
                    source_language=item.get("source_lang", "en"),
                    context_preset=preset,
                )
            except Exception as exc:
                logger.warning("Context sample %s failed: %s", item.get("id"), exc)
                hyp = ""
                error = str(exc)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            eval_res = evaluate_context_preset_sample(
                preset=preset,
                hypothesis=hyp,
                required_keywords=req_kw,
                forbidden_keywords=forb_kw,
            )
            score = eval_res["score"]
            if eval_res["passed"]:
                passed_count += 1

            preset_scores.setdefault(preset, []).append(score)
            preset_passes.setdefault(preset, []).append(bool(eval_res["passed"]))

            detail = {
                "id": item.get("id"),
                "preset": preset,
                "source": src,
                "reference": ref,
                "hypothesis": hyp,
                "passed": eval_res["passed"],
                "required_coverage": round(eval_res["required_coverage"], 3),
                "found_required": eval_res["found_required"],
                "found_forbidden": eval_res["found_forbidden"],
                "latency_ms": round(elapsed_ms, 1),
            }
            if error:
                detail["error"] = error
            item_details.append(detail)
            print(f"\r  Progress: {format_progress_bar(i, total)}", end="", flush=True)

        print()
        acc = (passed_count / total * 100.0) if total > 0 else 0.0
        print(f"  -> Context Compliance Accuracy: {acc:.2f}% ({passed_count}/{total} passed)")
        for p in preset_passes:
            p_acc = sum(preset_passes[p]) / len(preset_passes[p]) * 100.0
            print(f"     - Preset [{p}]: {p_acc:.1f}%")

        return {
            "status": "success",
            "total_tested": total,
            "passed_count": passed_count,
            "overall_accuracy_percent": round(acc, 2),
            "per_preset_accuracy": {
                p: round(sum(passes) / len(passes) * 100.0, 1)
                for p, passes in preset_passes.items()
            },
            "per_preset_score": {
                p: round(sum(scores) / len(scores), 3) for p, scores in preset_scores.items()
            },
            "vram_before": vram_before,
            "vram_after": self._vram_info(),
            "items": item_details,
        }

    def evaluate_asr(self, samples: list[dict[str, Any]]) -> dict[str, Any]:
        """Benchmark PhoASR on speech samples."""
        print(f"\n--- [3/4] Benchmarking Speech Recognition (PhoASR) ({len(samples)} samples) ---")
        vram_before = self._vram_info()
        if not samples:
            print("  [SKIP] No audio samples found for ASR testing.")
            return {
                "status": "skipped",
                "reason": "no_audio_samples",
                "vram_before": vram_before,
                "vram_after": self._vram_info(),
            }

        adapter = self._get_asr_adapter()
        if adapter is None:
            return {
                "status": "skipped",
                "reason": self._asr_skip_reason or "model_not_ready",
                "vram_before": vram_before,
                "vram_after": self._vram_info(),
            }

        wer_scores: list[float] = []
        cer_scores: list[float] = []
        rtf_scores: list[float] = []
        item_details = []
        references_verified = True

        total = len(samples)
        for i, sample in enumerate(samples, 1):
            audio_path = sample["audio_path"]
            ref = sample.get("reference", "")
            reference_verified = bool(sample.get("reference_verified", False))
            references_verified = references_verified and reference_verified

            t0 = time.perf_counter()
            error: str | None = None
            try:
                res = adapter.transcribe(audio_path)
            except Exception as exc:
                logger.warning("ASR sample %s failed: %s", audio_path, exc)
                res = {}
                error = str(exc)
            inference_s = time.perf_counter() - t0
            hyp = res.get("text", "")
            duration_s = res.get("duration", 1.0) or 1.0

            detail = {
                "audio": Path(audio_path).name,
                "duration_s": round(duration_s, 2),
                "inference_s": round(inference_s, 3),
                "rtf": None,
                "reference": ref,
                "reference_verified": reference_verified,
                "hypothesis": hyp,
                "wer": None,
                "cer": None,
            }
            if error:
                detail["error"] = error
            else:
                detail["rtf"] = round(inference_s / duration_s, 3)
                rtf_scores.append(inference_s / duration_s)
                if ref:
                    wer = calculate_wer(ref, hyp)
                    cer = calculate_cer(ref, hyp)
                    wer_scores.append(wer)
                    cer_scores.append(cer)
                    detail["wer"] = round(wer * 100.0, 2)
                    detail["cer"] = round(cer * 100.0, 2)
            item_details.append(detail)
            print(f"\r  Progress: {format_progress_bar(i, total)}", end="", flush=True)

        print()
        avg_wer = (sum(wer_scores) / len(wer_scores) * 100.0) if wer_scores else None
        avg_cer = (sum(cer_scores) / len(cer_scores) * 100.0) if cer_scores else None
        avg_rtf = (sum(rtf_scores) / len(rtf_scores)) if rtf_scores else 0.0

        wer_text = f"{avg_wer:.2f}%" if avg_wer is not None else "N/A"
        cer_text = f"{avg_cer:.2f}%" if avg_cer is not None else "N/A"
        print(f"  -> Average WER: {wer_text}")
        print(f"  -> Average CER: {cer_text}")
        print(f"  -> Average RTF: {avg_rtf:.2f}x")

        return {
            "status": "success",
            "samples_count": len(samples),
            "scored_count": len(wer_scores),
            "references_verified": references_verified,
            "avg_wer_percent": round(avg_wer, 2) if avg_wer is not None else None,
            "avg_cer_percent": round(avg_cer, 2) if avg_cer is not None else None,
            "avg_rtf": round(avg_rtf, 3),
            "vram_before": vram_before,
            "vram_after": self._vram_info(),
            "items": item_details,
        }

    async def _evaluate_tts_async(
        self,
        adapter: Any,
        samples: list[dict[str, Any]],
        asr_adapter: Any | None,
    ) -> dict[str, Any]:
        """Run asynchronous TTS synthesis and optional ASR round-trip scoring."""
        latencies: list[float] = []
        rtf_scores: list[float] = []
        audio_durations: list[float] = []
        wer_scores: list[float] = []
        cer_scores: list[float] = []
        successes = 0
        item_details = []

        total = len(samples)
        for i, sample in enumerate(samples, 1):
            text = sample.get("text", "")
            language = sample.get("language", "vi")
            t0 = time.perf_counter()
            error: str | None = None
            detail: dict[str, Any] = {
                "id": sample.get("id"),
                "text": text,
                "engine": None,
                "audio_duration_s": None,
                "latency_ms": None,
                "rtf": None,
                "hypothesis": None,
                "wer": None,
                "cer": None,
            }
            try:
                result = None
                last_error: Exception | None = None
                for attempt in range(5):
                    try:
                        result = await adapter.synthesize(text=text, language=language)
                        break
                    except Exception as exc:
                        last_error = exc
                        if attempt < 4:
                            await asyncio.sleep(0.5 * (attempt + 1))
                if result is None:
                    raise last_error or RuntimeError("TTS synthesis failed")
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                audio = np.asarray(result.audio, dtype=np.float32)
                sample_rate = int(result.sample_rate)
                if audio.size == 0 or sample_rate <= 0:
                    raise ValueError("TTS returned empty audio")
                duration_s = float(audio.shape[0]) / float(sample_rate)
                if duration_s <= 0:
                    raise ValueError("TTS returned invalid audio duration")
                successes += 1
                latencies.append(elapsed_ms)
                audio_durations.append(duration_s)
                rtf_scores.append((elapsed_ms / 1000.0) / duration_s)
                detail.update(
                    {
                        "engine": getattr(result, "engine", None),
                        "voice_note": getattr(result, "voice_note", None),
                        "audio_duration_s": round(duration_s, 3),
                        "latency_ms": round(elapsed_ms, 1),
                        "rtf": round((elapsed_ms / 1000.0) / duration_s, 3),
                    }
                )

                if asr_adapter is not None:
                    audio16 = _resample_audio(audio, sample_rate, 16000)
                    asr_res = asr_adapter.transcribe_array(
                        audio16,
                        duration=round(len(audio16) / 16000, 2),
                    )
                    hyp = asr_res.get("text", "")
                    wer = calculate_wer(text, hyp)
                    cer = calculate_cer(text, hyp)
                    wer_scores.append(wer)
                    cer_scores.append(cer)
                    detail.update(
                        {
                            "hypothesis": hyp,
                            "wer": round(wer * 100.0, 2),
                            "cer": round(cer * 100.0, 2),
                        }
                    )
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                error = str(exc)
                detail["latency_ms"] = round(elapsed_ms, 1)
                logger.warning("TTS sample %s failed: %s", sample.get("id"), exc)
            if error:
                detail["error"] = error
            item_details.append(detail)
            print(f"\r  Progress: {format_progress_bar(i, total)}", end="", flush=True)

        print()
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        avg_rtf = sum(rtf_scores) / len(rtf_scores) if rtf_scores else 0.0
        avg_wer = sum(wer_scores) / len(wer_scores) * 100.0 if wer_scores else None
        avg_cer = sum(cer_scores) / len(cer_scores) * 100.0 if cer_scores else None
        success_rate = (successes / total * 100.0) if total else 0.0

        print(f"  -> Synthesis success:     {success_rate:.2f}% ({successes}/{total})")
        print(f"  -> Average latency:       {avg_latency:.1f} ms/sentence")
        print(f"  -> Average RTF:           {avg_rtf:.2f}x")
        if avg_wer is not None:
            print(f"  -> Round-trip WER:        {avg_wer:.2f}%")
            print(f"  -> Round-trip CER:        {avg_cer:.2f}%")
        else:
            print("  -> Round-trip WER/CER:    N/A (PhoASR unavailable)")

        return {
            "status": "success" if successes else "failed",
            "samples_count": total,
            "success_count": successes,
            "success_rate_percent": round(success_rate, 2),
            "round_trip_scored_count": len(wer_scores),
            "avg_latency_ms": round(avg_latency, 1),
            "avg_rtf": round(avg_rtf, 3),
            "avg_audio_duration_s": round(sum(audio_durations) / len(audio_durations), 3)
            if audio_durations
            else None,
            "avg_wer_percent": round(avg_wer, 2) if avg_wer is not None else None,
            "avg_cer_percent": round(avg_cer, 2) if avg_cer is not None else None,
            "vram_before": self._vram_info(),
            "vram_after": self._vram_info(),
            "items": item_details,
        }

    def evaluate_tts(self, samples: list[dict[str, Any]]) -> dict[str, Any]:
        """Benchmark Vietnamese TTS synthesis and optional ASR round-trip."""
        print(f"\n--- [4/4] Benchmarking Text-to-Speech (Edge-TTS) ({len(samples)} samples) ---")
        vram_before = self._vram_info()
        if not samples:
            print("  [SKIP] No TTS text samples found.")
            return {
                "status": "skipped",
                "reason": "no_tts_samples",
                "vram_before": vram_before,
                "vram_after": self._vram_info(),
            }

        adapter = self._get_tts_adapter()
        if adapter is None:
            reason = self._tts_skip_reason or "tts_not_ready"
            print(f"  [SKIP] TTS not ready: {reason}")
            return {
                "status": "skipped",
                "reason": reason,
                "vram_before": vram_before,
                "vram_after": self._vram_info(),
            }

        asr_adapter = self._get_asr_adapter() if self.tts_round_trip else None
        if asr_adapter is None and self.tts_round_trip:
            print("  [WARN] PhoASR unavailable; TTS will run without round-trip scoring.")
        result = asyncio.run(self._evaluate_tts_async(adapter, samples, asr_adapter))
        result["round_trip_enabled"] = self.tts_round_trip and asr_adapter is not None
        result["vram_before"] = vram_before
        result["vram_after"] = self._vram_info()
        return result

    def print_ascii_summary(self) -> None:
        """Print an ASCII summary table on terminal."""
        print("\n" + "=" * 78)
        print("                  EVALUATION BENCHMARK SUMMARY REPORT")
        print("=" * 78)
        header = f"{'Module / Task':<24} | {'Metric':<18} | {'Score':<14} | {'Status'}"
        print(header)
        print("-" * 78)

        # MT
        mt_res = self.results["details"].get("translation", {})
        if mt_res.get("status") == "success":
            print(f"{'TranslateGemma (MT)':<24} | {'BLEU (corpus)':<18} | {mt_res['corpus_bleu']:<14} | {'COMPLETED'}")
            print(f"{'TranslateGemma (MT)':<24} | {'chrF++':<18} | {mt_res['avg_chrf']:<14} | {'COMPLETED'}")
        else:
            print(f"{'TranslateGemma (MT)':<24} | {'BLEU (corpus)':<18} | {'N/A':<14} | {mt_res.get('status', 'SKIPPED')}")

        # Context Presets
        ctx_res = self.results["details"].get("context_presets", {})
        if ctx_res.get("status") == "success":
            print(
                f"{'Context Presets':<24} | {'Accuracy':<18} | "
                f"{ctx_res['overall_accuracy_percent']}%{'':<8} | {'COMPLETED'}"
            )
        else:
            print(f"{'Context Presets':<24} | {'Accuracy':<18} | {'N/A':<14} | {ctx_res.get('status', 'SKIPPED')}")

        # ASR
        asr_res = self.results["details"].get("asr", {})
        if asr_res.get("status") == "success":
            wer = asr_res.get("avg_wer_percent")
            wer_text = f"{wer}%" if wer is not None else "N/A"
            print(f"{'PhoASR (Speech)':<24} | {'WER':<18} | {wer_text:<14} | {'COMPLETED'}")
            print(f"{'PhoASR (Speech)':<24} | {'RTF':<18} | {asr_res['avg_rtf']}x{'':<9} | {'COMPLETED'}")
        else:
            print(f"{'PhoASR (Speech)':<24} | {'WER':<18} | {'N/A':<14} | {asr_res.get('status', 'SKIPPED')}")

        # TTS
        tts_res = self.results["details"].get("tts", {})
        if tts_res.get("status") == "success":
            success = f"{tts_res.get('success_rate_percent', 0)}%"
            print(f"{'Edge-TTS (Speech)':<24} | {'Success rate':<18} | {success:<14} | {'COMPLETED'}")
            wer = tts_res.get("avg_wer_percent")
            wer_text = f"{wer}%" if wer is not None else "N/A"
            print(f"{'Edge-TTS (Speech)':<24} | {'Round-trip WER':<18} | {wer_text:<14} | {'COMPLETED'}")
        else:
            print(f"{'Edge-TTS (Speech)':<24} | {'Success rate':<18} | {'N/A':<14} | {tts_res.get('status', 'SKIPPED')}")

        print("=" * 78)

    def export_reports(self, md_path: Path, json_path: Path) -> None:
        """Export evaluation results to Markdown and JSON files."""
        md_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.parent.mkdir(parents=True, exist_ok=True)

        self.results["summary"] = {
            name: {"status": detail.get("status"), "reason": detail.get("reason")}
            for name, detail in self.results["details"].items()
        }

        # 1. Export JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        # 2. Export Markdown
        lines = [
            "# Báo Cáo Đánh Giá Hệ Thống (Benchmark Evaluation Report)",
            "",
            f"- **Thời gian chạy**: `{self.results['timestamp']}`",
            "- **Môi trường**: Linux / Multimodal Translation System",
            "",
            "## 1. Bảng Tổng Hợp Chỉ Số",
            "",
            "| Module | Chỉ Số (Metric) | Kết Quả | Trạng Thái |",
            "| :--- | :--- | :--- | :--- |",
        ]
        translation_hw = self.results.get("hardware", {}).get("translation")
        if translation_hw:
            lines.insert(
                4,
                f"- **TranslateGemma backend**: requested=`{translation_hw.get('device_requested')}`, "
                f"actual=`{translation_hw.get('device_actual')}`, "
                f"gpu_offload=`{translation_hw.get('gpu_offload')}`, "
                f"supported=`{translation_hw.get('gpu_offload_supported')}`, "
                f"n_gpu_layers=`{translation_hw.get('n_gpu_layers')}`, "
                f"reason=`{translation_hw.get('fallback_reason') or 'none'}`",
            )

        def _status(detail: dict[str, Any]) -> str:
            if detail.get("status") == "success":
                return "Hoàn tất"
            if detail.get("status") == "skipped":
                return f"Bỏ qua: {detail.get('reason', 'không rõ')}"
            return str(detail.get("status", "N/A"))

        mt = self.results["details"].get("translation", {})
        if mt.get("status") == "success":
            lines.append(
                f"| **TranslateGemma (MT)** | BLEU (corpus) | **{mt['corpus_bleu']}** | {_status(mt)} |"
            )
            lines.append(
                f"| | BLEU trung bình câu | **{mt['avg_sentence_bleu']}** | {_status(mt)} |"
            )
            lines.append(f"| | chrF++ | **{mt['avg_chrf']}** | {_status(mt)} |")
            lines.append(f"| | Độ trễ trung bình | **{mt['avg_latency_ms']} ms** | {_status(mt)} |")
        else:
            lines.append(f"| **TranslateGemma (MT)** | - | - | {_status(mt)} |")

        ctx = self.results["details"].get("context_presets", {})
        if ctx.get("status") == "success":
            lines.append(
                f"| **Context Presets** | Độ chính xác ngữ cảnh | **{ctx['overall_accuracy_percent']}%** | {_status(ctx)} |"
            )
            for preset, accuracy in ctx.get("per_preset_accuracy", {}).items():
                lines.append(f"| | {preset} | **{accuracy}%** | {_status(ctx)} |")
        else:
            lines.append(f"| **Context Presets** | - | - | {_status(ctx)} |")

        asr = self.results["details"].get("asr", {})
        if asr.get("status") == "success":
            wer = asr.get("avg_wer_percent")
            cer = asr.get("avg_cer_percent")
            lines.append(
                f"| **PhoASR (Speech)** | Word Error Rate (WER) | "
                f"**{wer if wer is not None else 'N/A'}** | {_status(asr)} |"
            )
            lines.append(
                f"| | Character Error Rate (CER) | "
                f"**{cer if cer is not None else 'N/A'}** | {_status(asr)} |"
            )
            lines.append(f"| | Real-Time Factor (RTF) | **{asr['avg_rtf']}x** | {_status(asr)} |")
        else:
            lines.append(f"| **PhoASR (Speech)** | - | - | {_status(asr)} |")

        tts = self.results["details"].get("tts", {})
        if tts.get("status") == "success":
            lines.append(
                f"| **Edge-TTS (Speech)** | Tỷ lệ tổng hợp thành công | "
                f"**{tts.get('success_rate_percent')}%** | {_status(tts)} |"
            )
            lines.append(
                f"| | Độ trễ trung bình | **{tts.get('avg_latency_ms')} ms** | {_status(tts)} |"
            )
            lines.append(f"| | Real-Time Factor (RTF) | **{tts.get('avg_rtf')}x** | {_status(tts)} |")
            tts_wer = tts.get("avg_wer_percent")
            lines.append(
                f"| | Round-trip WER (PhoASR) | "
                f"**{tts_wer if tts_wer is not None else 'N/A'}** | {_status(tts)} |"
            )
        else:
            lines.append(f"| **Edge-TTS (Speech)** | - | - | {_status(tts)} |")

        lines.extend(["", "## 2. Nguồn Dữ Liệu", ""])
        for name, meta in self.results.get("datasets", {}).items():
            if isinstance(meta, dict):
                source = meta.get("source", "unknown")
                returned = meta.get("returned_pairs", meta.get("returned_samples", meta.get("returned_rows")))
                available = meta.get("available_pairs", meta.get("available_samples", meta.get("available_rows")))
                meets = meta.get("meets_requirement")
                lines.append(
                    f"- **{name}**: source=`{source}`, returned=`{returned}`, "
                    f"available=`{available}`, meets_100=`{meets}`, "
                    f"license=`{meta.get('license', 'N/A')}`"
                )
                for key in ("preset_counts", "error"):
                    if meta.get(key):
                        lines.append(f"  - {key}: `{meta[key]}`")
            else:
                lines.append(f"- **{name}**: `{meta}`")

        lines.extend(["", "## 3. Ghi Chú & Khuyến Nghị", ""])
        insufficient = [
            name
            for name, meta in self.results.get("datasets", {}).items()
            if isinstance(meta, dict) and not meta.get("meets_requirement", False)
        ]
        if insufficient:
            lines.append(
                f"- Các bộ dữ liệu chưa đạt tối thiểu {MIN_EVAL_SAMPLES} mẫu: "
                f"{', '.join(insufficient)}."
            )
        if (
            translation_hw
            and translation_hw.get("device_requested", "").startswith("cuda")
            and translation_hw.get("device_actual") == "cpu"
        ):
            lines.append(
                "- TranslateGemma đang chạy trên CPU dù đã yêu cầu CUDA "
                f"(`{translation_hw.get('fallback_reason')}`). "
                "Cần build `llama-cpp-python` với CUDA để tận dụng GPU."
            )
        if asr.get("status") == "success" and not asr.get("references_verified", False):
            lines.append(
                "- WER/CER ASR dùng reference thủ công chưa được xác minh với audio; "
                "chỉ xem là chỉ báo tạm thời."
            )
        if tts.get("status") == "success" and tts.get("round_trip_enabled"):
            lines.append(
                "- TTS WER/CER là round-trip qua PhoASR, không phải điểm MOS; "
                "chỉ phản ánh mức độ giữ nội dung sau tổng hợp."
            )
        elif tts.get("status") == "success":
            lines.append("- TTS không chạy round-trip PhoASR; chỉ đo tổng hợp, latency và RTF.")
        lines.append(
            "- QED trong Context có license research-only; cần ghi rõ khi công bố kết quả."
        )
        skipped = [
            name
            for name, detail in self.results["details"].items()
            if detail.get("status") != "success"
        ]
        if skipped:
            lines.append(f"- Các module chưa chạy được: {', '.join(skipped)}.")
        lines.append(
            "- Nếu mô hình chưa nạp weights, chạy `python backend/scripts/download_models.py` để bổ sung weights."
        )
        lines.append(f"- Xem chi tiết từng câu kiểm thử tại: `{json_path.name}`.")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"\n[OK] Markdown report saved: {md_path}")
        print(f"[OK] JSON results saved:    {json_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Translation-App Multimodal Pipeline")
    parser.add_argument(
        "--module",
        choices=["all", "mt", "asr", "context", "tts"],
        default="all",
        help="Module to evaluate: all, mt, asr, context, tts (default: all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=MIN_EVAL_SAMPLES,
        help=f"Number of test samples per module (default: {MIN_EVAL_SAMPLES})",
    )
    parser.add_argument(
        "--no-tts-round-trip",
        action="store_true",
        help="Skip PhoASR round-trip scoring for TTS (faster on CPU-only hosts)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Only display console output, do not write report files",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="backend/benchmarks/reports/benchmark_report.md",
        help="Path for output Markdown report",
    )
    parser.add_argument(
        "--json-output",
        type=str,
        default="backend/benchmarks/reports/benchmark_results.json",
        help="Path for output JSON file",
    )
    args = parser.parse_args()

    runner = BenchmarkRunner(limit=args.limit, tts_round_trip=not args.no_tts_round_trip)

    # Machine Translation (FLORES-200)
    if args.module in ("all", "mt"):
        mt_samples, mt_meta = get_flores_dataset(limit=args.limit)
        runner.results["datasets"]["translation"] = mt_meta
        runner.results["details"]["translation"] = runner.evaluate_translation(mt_samples)

    # Context presets (curated + online corpora)
    if args.module in ("all", "context"):
        ctx_data, ctx_meta = get_context_dataset(limit=args.limit)
        runner.results["datasets"]["context"] = ctx_meta
        runner.results["details"]["context_presets"] = runner.evaluate_context_presets(ctx_data)

    # ASR (PhoASR / FLEURS)
    if args.module in ("all", "asr"):
        asr_samples, asr_meta = get_fleurs_asr_dataset(limit=args.limit)
        runner.results["datasets"]["asr"] = asr_meta
        runner.results["details"]["asr"] = runner.evaluate_asr(asr_samples)

    # TTS (Edge-TTS + optional PhoASR round-trip)
    if args.module in ("all", "tts"):
        tts_samples, tts_meta = get_tts_samples(limit=args.limit)
        runner.results["datasets"]["tts"] = tts_meta
        runner.results["details"]["tts"] = runner.evaluate_tts(tts_samples)

    runner.print_ascii_summary()

    if not args.no_save:
        md_file = Path(args.output).resolve()
        json_file = Path(args.json_output).resolve()
        runner.export_reports(md_file, json_file)


if __name__ == "__main__":
    main()
