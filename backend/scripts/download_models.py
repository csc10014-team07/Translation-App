#!/usr/bin/env python3
"""
Model download helper script.

Downloads the required model weights into local storage:
1. PhoASR-whisper-small -> models/phoasr
2. TranslateGemma 4B GGUF (Q5_K_M) -> models/gemma/translategemma-4b-it.Q5_K_M.gguf
3. Pocket TTS models -> installed via pip (pocket-tts package handles automatic download)
"""
import argparse
import os
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


def download_pocket_tts_info() -> None:
    """
    Pocket TTS models are automatically downloaded by the pocket-tts package.
    No manual download needed. Just install with: pip install pocket-tts
    """
    print("\n[3/3] Pocket TTS models are handled automatically by the pocket-tts package.")
    print("       No manual download required.")
    print("       To use: pip install pocket-tts")


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
        help="Skip Pocket TTS info message",
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
        download_pocket_tts_info()

    print("\n[Done] All requested models downloaded or configured successfully.")


if __name__ == "__main__":
    main()
