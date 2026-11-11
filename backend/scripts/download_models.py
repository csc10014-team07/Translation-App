#!/usr/bin/env python3
"""
Model download helper script.

Downloads the required model weights into local storage / cache:
1. PhoASR-whisper-small -> models/phoasr
2. TranslateGemma 4B GGUF (Q5_K_M) -> models/gemma/translategemma-4b-it.Q5_K_M.gguf
3. Pocket TTS (multi-language checkpoints) -> Hugging Face cache (~/.cache/huggingface/hub/)
"""
import argparse
import shutil
import sys
from pathlib import Path

try:
    from huggingface_hub import hf_hub_download, snapshot_download
except ImportError:
    print(
        "ERROR: huggingface_hub is required to download models.\n"
        "Please run: pip install huggingface_hub"
    )
    sys.exit(1)

POCKET_TTS_SUPPORTED_LANGUAGES = [
    "english",
    "french",
    "german",
    "spanish",
    "portuguese",
    "italian",
    "dutch",
]


def download_phoasr(target_dir: Path) -> None:
    """Download PhoASR-whisper-small model files."""
    model_id = "Qualcomm-AI-Research/PhoASR-whisper-small"
    print(f"\n[1/3] Downloading PhoASR ({model_id}) to {target_dir}...")
    target_dir.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=model_id,
        local_dir=str(target_dir),
        local_dir_use_symlinks=False,
        resume_download=True,
    )
    print(f"PhoASR download complete: {target_dir}")


def download_gemma_gguf(target_file: Path) -> None:
    """Download TranslateGemma 4B GGUF (Q5_K_M quantization)."""
    repo_id = "mradermacher/translategemma-4b-it-GGUF"
    filename = "translategemma-4b-it.Q5_K_M.gguf"
    target_dir = target_file.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[2/3] Downloading TranslateGemma 4B GGUF ({filename}) from {repo_id}...")
    if target_file.exists() and target_file.stat().st_size > 1024 * 1024 * 100:
        print(f"File already exists: {target_file} ({target_file.stat().st_size / (1024*1024):.1f} MB)")
        return

    try:
        downloaded_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=str(target_dir),
            local_dir_use_symlinks=False,
            resume_download=True,
        )
        downloaded_p = Path(downloaded_path)
        if downloaded_p.resolve() != target_file.resolve():
            shutil.move(str(downloaded_p), str(target_file))
        print(f"TranslateGemma GGUF ready at: {target_file}")
    except Exception as exc:
        print(
            f"Failed to auto-download TranslateGemma GGUF: {exc}\n"
            "If gated or restricted, you can manually download the Q5_K_M GGUF from:\n"
            f"  https://huggingface.co/{repo_id}\n"
            f"and place it at: {target_file}"
        )


def download_pocket_tts(languages: list[str]) -> None:
    """Pre-download Pocket TTS model checkpoints into local cache for specified languages."""
    print(f"\n[3/3] Pre-downloading Pocket TTS models for languages: {', '.join(languages)}...")
    try:
        from pocket_tts import TTSModel
    except ImportError:
        print(
            "WARNING: pocket-tts is not installed. Run `pip install pocket-tts` to use Pocket TTS."
        )
        return

    for lang in languages:
        lang_normalized = lang.strip().lower()
        if lang_normalized not in POCKET_TTS_SUPPORTED_LANGUAGES:
            print(
                f"  Skipping unsupported Pocket TTS language '{lang}'. "
                f"Available: {', '.join(POCKET_TTS_SUPPORTED_LANGUAGES)}"
            )
            continue
        try:
            print(f"  --> Downloading/caching Pocket TTS for '{lang_normalized}'...")
            TTSModel.load_model(language=lang_normalized)
            print(f"  Pocket TTS for '{lang_normalized}' ready.")
        except Exception as exc:
            print(f"  Failed to download Pocket TTS for '{lang_normalized}': {exc}")

    print("Pocket TTS pre-download complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download AI models for Translation App")
    parser.add_argument(
        "--models-dir",
        type=str,
        default="./models",
        help="Target base directory for model weights (default: ./models)",
    )
    parser.add_argument(
        "--skip-gemma",
        action="store_true",
        help="Skip downloading Gemma GGUF file",
    )
    parser.add_argument(
        "--skip-phoasr",
        action="store_true",
        help="Skip downloading PhoASR Whisper model",
    )
    parser.add_argument(
        "--skip-tts",
        action="store_true",
        help="Skip pre-downloading Pocket TTS models",
    )
    parser.add_argument(
        "--tts-languages",
        nargs="+",
        default=["english"],
        help=(
            "List of languages to pre-download for Pocket TTS (e.g. english french german or 'all'). "
            f"Supported: {', '.join(POCKET_TTS_SUPPORTED_LANGUAGES)}. Default: english"
        ),
    )
    args = parser.parse_args()

    base_dir = Path(args.models_dir).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    print(f"Models storage directory: {base_dir}")

    phoasr_dir = base_dir / "phoasr"
    gemma_file = base_dir / "gemma" / "translategemma-4b-it.Q5_K_M.gguf"

    if not args.skip_phoasr:
        download_phoasr(phoasr_dir)

    if not args.skip_gemma:
        download_gemma_gguf(gemma_file)

    if not args.skip_tts:
        # Determine languages to download
        tts_langs = args.tts_languages
        if any(item.lower() == "all" for item in tts_langs):
            tts_langs = POCKET_TTS_SUPPORTED_LANGUAGES
        download_pocket_tts(tts_langs)

    print("\n[Done] All requested models downloaded or configured successfully.")


if __name__ == "__main__":
    main()
