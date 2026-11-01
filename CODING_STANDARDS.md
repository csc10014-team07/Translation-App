# Coding Standards & Seam Review Guidelines

This document governs code quality, architecture patterns, and review expectations across the repository.

---

## 1. Automated Guardrails (Mechanical Rules)

All mechanical syntax, formatting, and typing rules are deterministically enforced by tools:
- **Linter**: `python -m ruff check backend` (configured via `pyproject.toml`).
- **Pre-commit**: Automated hook via `.git/hooks/pre-commit` or `python scripts/check.py`.
- **TypeScript Typecheck**: `npm run typecheck` (`tsc --noEmit`) in `mobile/`.

*Rule*: No PR or commit should introduce ruff errors or unresolved TypeScript type errors.

---

## 2. Architecture & Seam Review Standards (Judgement Calls)

### A. Vertical Slice Completeness
- When implementing a feature or seam ticket:
  - Backend route handlers, services, and schemas must match client interfaces.
  - New client service wrappers (e.g. `StreamClient` in `mobile/src/services/stream.ts`) **must be wired** into state management (`store/translationStore.ts`) and active screens (`TranslationScreen.tsx`).
  - Do not leave client services orphaned or unconsumed.

### B. Domain Configuration & No Magic Numbers
- Digital signal processing (DSP), voice activity detection (VAD), and network constants must live in configuration dataclasses (e.g. `VADSettings` in `stream.py` or `app/core/config.py`).
- Route handlers must not hardcode magic numbers (such as sample rates, RMS thresholds, buffer byte lengths, or timeout seconds).

### C. Cross-Platform Portability
- Launchers, utility scripts, and setup wizards must support cross-platform execution (Windows, Linux / Google Colab, macOS):
  - Binary downloads (e.g. `cloudflared`) must detect `sys.platform` and select the appropriate architecture archive/executable.
  - File paths must use `pathlib.Path` rather than hardcoded forward/back-slashes.
  - Windows terminal stdout encoding (`cp1252`) must be handled safely (use `sys.stdout.reconfigure(encoding="utf-8")` or ASCII status badges).

### D. Device & VRAM Abstraction
- All AI model inference must pass through the `ModelManager` and device abstraction layer (`vram_monitor.py` / `hardware.py`).
- PyTorch CUDA device compatibility must be respected: GPUs with Compute Capability < 7.5 (such as Quadro P3200 `sm_61`) must transparently route to CPU inference to avoid runtime crashes.

### E. Test Coverage at Pre-Agreed Seams
- Every new API route or adapter must have corresponding integration tests in `backend/tests/`.
- Tests must clean up temporary files in `finally:` blocks.
